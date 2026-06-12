"""Gold-set recall evaluator — the L3 retrieval-QUALITY gate.

Unit tests prove the edge MECHANICS (suppress/contradict/fan-out); they cannot
prove that the RIGHT lesson surfaces for a realistic prompt and that junk stays
silent on the REAL corpus. This harness closes that gap: it runs `recall` over
the live lesson store for a set of `query -> expected/forbidden` cases and scores

  hit-rate   : an expected lesson surfaced in the top-K (recall did its job)
  clean-rate : no forbidden lesson surfaced (silence-default held, no context rot)
  tokens     : size of the inject block recall would emit (the cost side)

Matching is by body SUBSTRING, not content-hash id, so the gold file is portable
across machines/stores (ids differ per box; the lesson TEXT is stable enough).

Deterministic by default (TF-IDF tier-1, no ONNX) so it is a reproducible CI gate.
`--embed` additionally fuses the live MiniLM (the path the real hook uses).

Usage:
  py bench/_eval_recall.py                      # run gold set, print report
  py bench/_eval_recall.py --k 5 --min-pass 0.8 # tune top-K + gate threshold
  py bench/_eval_recall.py --embed              # also fuse real MiniLM
  py bench/_eval_recall.py --json               # machine-readable
Exit code != 0 when pass-rate < --min-pass (regression gate).

FINDING (2026-06-13, first real run, 28 unpinned lessons): TF-IDF 75% / clean 100%.
The misses are short, Thai-dominant lessons whose few English/code tokens score below
the per-prompt floor (lesson_min 0.12) — they never surface. Embedding does NOT rescue
them because tier-2 fires only on a tier-1 TOTAL miss, while a weak tier-1 hit of the
WRONG lesson keeps tier-2 dormant. The actionable lever this harness now measures:
let tier-2 engage when tier-1's TOP score is weak (not only when empty). Clean-rate is
already 100% (silence-default holds), so the headroom is pure recall, not precision.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from portaw.memory import store
from portaw.memory.anchors import AnchorQuery
from portaw.memory.inject import InjectConfig, approx_tokens, format_memory, select
from portaw.memory.retrieval import recall

GOLD = Path(__file__).with_name("_recall_goldset.jsonl")


def _load_cases() -> list[dict]:
    cases = []
    for line in GOLD.read_text("utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            cases.append(json.loads(line))
    return cases


def _embed_fn():
    """Route-level embed (str, caps) -> {cap_id: score}, mirroring the live hook.
    None when ONNX is unavailable — the eval then runs pure TF-IDF."""
    from portaw.kernel import embed

    if not embed.available():
        return None
    from portaw.kernel.ranking import route  # noqa: F401  (embed wires through route)

    def fn(text, caps):
        # cosine of the query against each capability's searchable text
        from portaw.memory.similarity import _dot

        vecs = embed.encode([text, *[c.text for c in caps]])
        q = vecs[0]
        return {c.name: max(0.0, _dot(q, vecs[i + 1])) for i, c in enumerate(caps)}

    return fn


def run(k: int, use_embed: bool, include_pinned: bool = False) -> dict:
    lessons = store.load_lessons()
    try:
        lessons += store.load_project(Path.cwd())
    except Exception:
        pass
    # pinned lessons are an ALWAYS-ON channel delivered ONCE at SessionStart (session-
    # hook), and the per-prompt path dedupes whatever that channel already showed. This
    # harness measures the PER-PROMPT recall channel, so by default it excludes pinned —
    # otherwise the few pinned universals fill max_items every prompt and crowd out the
    # very match each case is probing (a measurement artifact, not the live behaviour).
    if not include_pinned:
        lessons = [e for e in lessons if not e.pinned]
    embed_fn = _embed_fn() if use_embed else None

    results = []
    t0 = time.perf_counter()
    for c in _load_cases():
        q = c.get("anchors") or {}
        aq = AnchorQuery.from_context(paths=q.get("paths"), symbols=q.get("symbols"))
        scored = recall(c["query"], lessons, query=aq, embed_fn=embed_fn)
        # the REAL silence gate: pinned-first, per-type threshold, trusted, budget —
        # exactly what the live hook emits. raw recall[:k] would bypass it.
        top = select(scored, InjectConfig(max_items=k))
        bodies = [s.entry.body.lower() for s in top]
        expect = [e.lower() for e in c.get("expect", [])]
        forbid = [f.lower() for f in c.get("forbid", [])]

        hit = (not expect) or any(any(sub in b for b in bodies) for sub in expect)
        surfaced_forbidden = [f for f in forbid if any(f in b for b in bodies)]
        clean = not surfaced_forbidden
        # a case tagged embed:true needs cross-language semantics (e.g. an English query
        # over a Thai lesson) — TF-IDF cannot bridge it, so it is only REQUIRED to pass
        # under --embed. Under pure TF-IDF it is reported but does not fail the gate.
        embed_only = c.get("embed", False)
        skipped = embed_only and not embed_fn
        # silence case (expect == []) passes only when nothing forbidden surfaced
        ok = (hit and clean) or skipped
        results.append({
            "id": c["id"], "ok": ok, "hit": hit, "clean": clean, "skipped": skipped,
            "surfaced": len(top), "tokens": approx_tokens(format_memory(top)),
            "leaked": surfaced_forbidden,
        })
    elapsed = time.perf_counter() - t0

    n = len(results)
    passed = sum(r["ok"] for r in results)
    return {
        "cases": n,
        "passed": passed,
        "pass_rate": passed / n if n else 0.0,
        "hit_rate": sum(r["hit"] for r in results) / n if n else 0.0,
        "clean_rate": sum(r["clean"] for r in results) / n if n else 0.0,
        "avg_tokens": round(sum(r["tokens"] for r in results) / n, 1) if n else 0.0,
        "elapsed_s": round(elapsed, 3),
        "lessons": len(lessons),
        "embed": embed_fn is not None,
        "results": results,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--min-pass", type=float, default=0.7)  # baseline ~0.75 TF-IDF; gate sits below
    ap.add_argument("--embed", action="store_true")
    ap.add_argument("--include-pinned", action="store_true",
                    help="keep always-on pinned lessons in the per-prompt pool (default: excluded)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    rep = run(a.k, a.embed, a.include_pinned)
    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(f"lessons={rep['lessons']}  embed={rep['embed']}  k={a.k}  "
              f"({rep['elapsed_s']}s)")
        for r in rep["results"]:
            mark = "SKIP" if r["skipped"] else ("PASS" if r["ok"] else "FAIL")
            why = "" if r["ok"] else (
                f"  leaked={r['leaked']}" if r["leaked"] else "  (expected lesson not in top-K)")
            if r["skipped"]:
                why = "  (embed-only case; run --embed to require it)"
            print(f"  {mark}  {r['id']:24} surfaced={r['surfaced']} "
                  f"tok={r['tokens']}{why}")
        print(f"\npass {rep['passed']}/{rep['cases']} = {rep['pass_rate']:.0%}  "
              f"hit={rep['hit_rate']:.0%}  clean={rep['clean_rate']:.0%}  "
              f"avg_inject_tok={rep['avg_tokens']}")

    return 0 if rep["pass_rate"] >= a.min_pass else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
