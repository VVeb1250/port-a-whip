"""Session inject-log — one lesson injects ONCE per session (dedup across surfaces).

With multiple inject surfaces (SessionStart pins, prompt recall, tool-hook anchor/
error recall) the same lesson would otherwise re-inject every time it stays
relevant — pure context rot, the inject is already IN the conversation. This log
remembers what each session has seen. ``reset`` exists for SessionStart(compact):
compaction summarizes earlier injects away, so the slate is wiped and pins re-fire.

Tolerant by construction: any I/O error degrades to "nothing seen" (worst case a
duplicate inject, never a crash or a lost prompt). Files live under
~/.paw/session/<id>.json and are pruned after ``_TTL_DAYS``.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

_TTL_DAYS = 2
_SANITIZE = re.compile(r"[^A-Za-z0-9_-]")


def _dir() -> Path:
    return Path.home() / ".paw" / "session"


def _path(session_id: str) -> Path:
    sid = _SANITIZE.sub("_", session_id or "default")[:64] or "default"
    return _dir() / f"{sid}.json"


def seen(session_id: str) -> set[str]:
    """Entry ids already injected in this session ({} on any error)."""
    try:
        raw = json.loads(_path(session_id).read_text(encoding="utf-8"))
        return set(raw.get("ids", []))
    except (OSError, ValueError):
        return set()


def mark(session_id: str, ids: list[str] | set[str]) -> None:
    """Record ids as injected (merge + write; opportunistically prunes old logs)."""
    if not ids:
        return
    try:
        from portaw.memory.store import locked

        p = _path(session_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        # locked: parallel hooks in ONE session merge-write the same log — an
        # unlocked read-merge-write drops the other surface's mark (→ re-inject).
        with locked(p):
            merged = sorted(seen(session_id) | set(ids))
            p.write_text(json.dumps({"ids": merged, "ts": time.time()}), encoding="utf-8")
        _prune()
    except OSError:
        pass  # a failed mark = at worst one duplicate inject later


def reset(session_id: str) -> None:
    """Wipe the log (SessionStart source=compact — earlier injects got summarized)."""
    try:
        _path(session_id).unlink(missing_ok=True)
    except OSError:
        pass


def _prune(now: float | None = None) -> None:
    """Drop logs older than the TTL (sessions are short-lived; the dir must not grow)."""
    cutoff = (now or time.time()) - _TTL_DAYS * 86400
    try:
        for f in _dir().glob("*.json"):
            try:
                if f.stat().st_mtime < cutoff:
                    f.unlink(missing_ok=True)
            except OSError:
                continue
    except OSError:
        pass
