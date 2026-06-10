"""kernel-unify guard: the live skill-router's inline fallback must stay
behaviour-identical to paw's canonical kernel.

The author's ~/.claude/hooks/skill-router.py delegates ranking to
portaw.kernel.ranking.route but keeps an inline TF-IDF copy as a zero-paw
fallback. If the two ever diverge, a paw-down prompt would silently rank skills
differently than a paw-up one. This test pins them: _inline_route ==
_kernel_route over a battery that exercises the lexical tier AND the hybrid
layers (intent boost, conflict prune, prerequisite fan-out) on the real corpus.

Skips cleanly when the author's hook / live index aren't present (any other
paw install), so it never fails CI for non-author users.
"""

import importlib.util
import json
from pathlib import Path

import pytest

HOOKS = Path.home() / ".claude" / "hooks"
HOOK = HOOKS / "skill-router.py"
GRAPH = HOOKS / "skill-graph.json"
INDEX = HOOKS / ".skill-index.json"

# battery: plain lexical hits, intent_map phrases, fan-out trigger, no-match
PROMPTS = [
    "scan the staged diff for leaked secrets",
    "what is the blast radius of this change",
    "which tests should i run after my change",
    "what tests are impacted after this commit",
    "track mistakes i keep making",
    "i keep making the same mistake here",
    "wire codegraph into this repo",
    "link codegraph for this project",
    "build a knowledge graph of the code",
    "find all callers of this function",
    "the capital of france is paris",
    "help me refactor this messy module before the review",
    "review my git commit changes before i push",
    "debug this traceback crash in the runtime",
]


def _load_hook():
    spec = importlib.util.spec_from_file_location("skill_router_live", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _keys(res):
    # the routing contract: which skills, in what order, at what score
    return [(s["name"], round(c, 9)) for c, s in res]


@pytest.mark.skipif(not (HOOK.exists() and INDEX.exists()),
                    reason="author's live skill-router / index not present")
def test_inline_route_equals_kernel_route():
    pytest.importorskip("portaw")
    mod = _load_hook()
    if not (hasattr(mod, "_inline_route") and hasattr(mod, "_kernel_route")):
        pytest.skip("live hook predates kernel-unify (copy build/skill-router.unified.py over it)")

    skills = json.loads(INDEX.read_text(encoding="utf-8")).get("skills", [])
    graph = json.loads(GRAPH.read_text(encoding="utf-8")) if GRAPH.exists() else {}
    if not skills or not graph.get("graph"):
        pytest.skip("empty live corpus or graph")

    for p in PROMPTS:
        inline = _keys(mod._inline_route(p, skills, graph))
        kernel = _keys(mod._kernel_route(p, skills, graph))
        assert inline == kernel, f"inline≠kernel for {p!r}:\n  inline={inline}\n  kernel={kernel}"
