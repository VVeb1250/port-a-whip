"""Router outcome ledger — did a suggestion actually get USED? (L2 feedback loop)

The router was fire-and-forget: it never learned that a suggestion kept being
ignored. This ledger counts, per capability, how often it was suggested and how
often it converted (its `portaw install <set>` actually ran — visible in the
Bash PostToolUse hook, the one surface paw already watches). A capability
suggested many times with zero conversions is DEMOTED: the router stops
surfacing it (noise) until evidence changes or the user resets it.

Same philosophy as the L3 observation ledger — evidence over static ranking —
and the same storage stance: machine-local jsonl, tolerant reads, store lock
around read-modify-write, every public call fail-safe (a broken ledger must
never break routing).
"""

from __future__ import annotations

import json
import re
from datetime import date

from portaw.memory import store

_FILE = "router-outcomes.jsonl"
_CAP = 200

DEMOTE_MIN_SUGGESTED = 5   # ignored this many times with 0 uses → stop suggesting

_INSTALL_RE = re.compile(r"\bportaw\s+install\s+([A-Za-z0-9][\w-]*)")


def _path():
    return store.global_dir() / _FILE


def load() -> dict[str, dict]:
    """name → record. {} on any error (routing must never crash here)."""
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
            if isinstance(r, dict) and r.get("name"):
                out[r["name"]] = r
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
    return out


def _save(records: dict[str, dict]) -> None:
    recs = list(records.values())
    if len(recs) > _CAP:
        recs.sort(key=lambda r: (r.get("used", 0), r.get("suggested", 0)), reverse=True)
        recs = recs[:_CAP]
    store._write_jsonl_raw(_path(), [json.dumps(r, ensure_ascii=False) for r in recs])


def mark_suggested(names: list[str], *, today: str | None = None) -> None:
    """Count an emission (call AFTER dedup/demotion filtering). Fail-safe no-op."""
    if not names:
        return
    try:
        today = today or date.today().isoformat()
        with store.locked(_path()):
            records = load()
            for n in names:
                r = records.setdefault(n, {"name": n, "suggested": 0, "used": 0})
                r["suggested"] = int(r.get("suggested", 0)) + 1
                r["last_suggested"] = today
            _save(records)
    except Exception:
        pass


def mark_used(name: str, *, today: str | None = None) -> None:
    """A suggestion converted (its install command ran). Fail-safe no-op."""
    try:
        today = today or date.today().isoformat()
        with store.locked(_path()):
            records = load()
            r = records.setdefault(name, {"name": name, "suggested": 0, "used": 0})
            r["used"] = int(r.get("used", 0)) + 1
            r["last_used"] = today
            _save(records)
    except Exception:
        pass


def demoted_names() -> set[str]:
    """Capabilities the router should stop surfacing: suggested ≥ threshold,
    converted never. Any use ever clears it. {} on any error."""
    try:
        return {
            n for n, r in load().items()
            if int(r.get("used", 0)) == 0
            and int(r.get("suggested", 0)) >= DEMOTE_MIN_SUGGESTED
        }
    except Exception:
        return set()


def forget(name: str) -> bool:
    """Reset one capability's counters (un-demote). True if it existed."""
    try:
        with store.locked(_path()):
            records = load()
            if name not in records:
                return False
            del records[name]
            _save(records)
        return True
    except Exception:
        return False


def parse_install_target(command: str) -> str | None:
    """`portaw install <set> …` anywhere in a Bash command → the set name."""
    m = _INSTALL_RE.search(command or "")
    return m.group(1) if m else None
