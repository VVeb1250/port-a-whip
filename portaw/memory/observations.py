"""Observation ledger — the runtime evidence loop (2026-06-11).

The L3 store was write-once: a lesson's confidence/recurrence froze at authoring
time. But the PostToolUse Bash-failure hook already sees real errors live — and
threw each one away. This ledger keeps them cheaply (NO LLM): every failed command
is normalized to a stable error SIGNATURE and counted. That count drives the two
things a write-once store can't:

  • capture  — a repeated error with NO covering lesson is surfaced for authoring
    (closes the "hit it 3 times, never wrote it down" gap).
  • evidence — a lesson whose error keeps recurring after it exists is not working;
    one whose error stops is proven. Real signal to move confidence off its frozen
    severity seed (see confidence.py).

`signature` is pure; the store fns are tolerant jsonl I/O (any error → no-op, a
ledger must never fail a hook). Lives next to the lesson store in ~/.paw/memory.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from portaw.memory import store
from portaw.memory.detect import _err_tag  # ONE error-marker list (no dup)

_FILE = "observations.jsonl"
_PROG_CLEAN = re.compile(r"[^A-Za-z0-9_.\-]")
_CAP = 500          # max distinct signatures kept (prune count==1 oldest beyond this)


def program(command: str) -> str:
    """The command's leading token, basename-only, alnum: `/usr/bin/python x` → `python`.
    This is the discriminator that keeps `command not found|python` distinct from
    `|node`, and the token a lesson must mention to genuinely COVER the error."""
    toks = (command or "").strip().split()
    if not toks:
        return ""
    base = toks[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return _PROG_CLEAN.sub("", base).lower()


def signature(command: str, stderr: str) -> str:
    """Stable error class for counting: ``<error-tag>|<program>`` (or just the tag).

    `python x.py` and `python y.py` collapse to one `command not found|python`
    signature while a different failing program stays distinct. '' when stderr shows
    no known error (precision: we only count real failures, mirroring the P2 gate)."""
    tag = _err_tag(stderr or "")
    if not tag:
        return ""
    prog = program(command)
    return f"{tag}|{prog}" if prog else tag


def _path() -> Path:
    return store.global_dir() / _FILE


def load() -> dict[str, dict]:
    """sig → record. {} on any error (tolerant — a recall must never crash here)."""
    try:
        text = _path().read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    out: dict[str, dict] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if isinstance(r, dict) and r.get("sig"):
                out[r["sig"]] = r
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return out


def _save(records: dict[str, dict]) -> None:
    recs = list(records.values())
    if len(recs) > _CAP:  # keep the meaningful ones: high count + recently seen
        recs.sort(key=lambda r: (r.get("count", 0), r.get("last_seen", "")), reverse=True)
        recs = recs[:_CAP]
    store._write_jsonl_raw(_path(), [json.dumps(r, ensure_ascii=False) for r in recs])


def record(command: str, stderr: str, *, lesson_id: str = "",
           today: str | None = None) -> dict | None:
    """Bump the signature's count (+link a covering lesson on first sight). None when
    the command/stderr is not a recognizable failure. Tolerant: any error → None."""
    try:
        sig = signature(command, stderr)
        if not sig:
            return None
        today = today or date.today().isoformat()
        # under the store lock: parallel tool calls fire parallel PostToolUse hooks —
        # an unlocked load→save here silently drops the other hook's count.
        with store.locked(_path()):
            records = load()
            r = records.get(sig)
            if r is None:
                r = {"sig": sig, "count": 0, "first_seen": today, "last_seen": today,
                     "lesson_id": "", "linked_at_count": -1}
            r["count"] = int(r.get("count", 0)) + 1
            r["last_seen"] = today
            # link the first lesson that covers this signature, snapshotting the count
            # so "did it keep recurring AFTER the lesson existed" is measurable later.
            if lesson_id and not r.get("lesson_id"):
                r["lesson_id"] = lesson_id
                r["linked_at_count"] = r["count"]
            records[sig] = r
            _save(records)
        return r
    except Exception:
        return None


def uncovered_repeats(min_count: int = 2) -> list[dict]:
    """Signatures hit ≥min_count with NO covering lesson — capture candidates."""
    return sorted(
        (r for r in load().values()
         if not r.get("lesson_id") and int(r.get("count", 0)) >= min_count),
        key=lambda r: -int(r.get("count", 0)),
    )


def recurring_despite_lesson() -> list[dict]:
    """Signatures whose error kept firing AFTER a lesson was linked — the lesson is
    not working (wrong fix, or not surfacing). The effectiveness signal."""
    out = []
    for r in load().values():
        linked = r.get("linked_at_count", -1)
        if r.get("lesson_id") and linked >= 0 and int(r.get("count", 0)) > linked:
            out.append(r)
    return sorted(out, key=lambda r: linked_misses(r), reverse=True)


def linked_misses(r: dict) -> int:
    """Recurrences observed after the lesson was linked (0 = lesson seems to hold)."""
    linked = r.get("linked_at_count", -1)
    return int(r.get("count", 0)) - linked if linked >= 0 else 0
