"""Session inject-log — one lesson injects ONCE per session (dedup across surfaces).

With multiple inject surfaces (SessionStart pins, prompt recall, tool-hook anchor/
error recall) the same lesson would otherwise re-inject every time it stays
relevant — pure context rot, the inject is already IN the conversation. This log
remembers what each session has seen. ``reset`` exists for SessionStart(compact):
compaction summarizes earlier injects away, so the slate is wiped and pins re-fire.

Tolerant by construction: any I/O error degrades to "nothing seen" (worst case a
duplicate inject, never a crash or a lost prompt). Files live under
~/.paw/session/<id>.json and are pruned after ``_TTL_DAYS``.

Dedup is PER-ID ttl, not whole-file: each id carries the timestamp it was injected,
and ``seen`` only counts ids marked within ``_DEDUP_TTL_S``. This bounds the log
(stale ids drop on the next write instead of accumulating for the file's whole
life) and means a lesson relevant again a day later CAN re-surface — the inject it
made earlier has long scrolled out of the live context, so re-showing it is help,
not rot. The legacy ``{"ids":[...]}`` shape still reads (folded in at file mtime).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

_TTL_DAYS = 2
_DEDUP_TTL_S = 86400          # an id counts as "already shown" for this long (1 day)
_SANITIZE = re.compile(r"[^A-Za-z0-9_-]")


def _dir() -> Path:
    return Path.home() / ".paw" / "session"


def _path(session_id: str) -> Path:
    sid = _SANITIZE.sub("_", session_id or "default")[:64] or "default"
    return _dir() / f"{sid}.json"


def _load_seen_map(session_id: str) -> dict[str, float]:
    """{id: injected_ts}. Reads the current per-id shape AND the legacy ``ids`` list
    (folded in at the file's mtime, so an old log still dedups within its ttl)."""
    p = _path(session_id)
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, float] = {}
    legacy_ts = raw.get("ts")
    if not isinstance(legacy_ts, (int, float)):
        try:
            legacy_ts = p.stat().st_mtime
        except OSError:
            legacy_ts = time.time()
    for i in raw.get("ids", []):       # legacy list → all at the file timestamp
        out[str(i)] = float(legacy_ts)
    seen_map = raw.get("seen")          # current per-id shape (wins on overlap)
    if isinstance(seen_map, dict):
        for i, ts in seen_map.items():
            try:
                out[str(i)] = float(ts)
            except (TypeError, ValueError):
                continue
    return out


def seen(session_id: str, *, now: float | None = None) -> set[str]:
    """Entry ids injected within the dedup ttl ({} on any error or empty log)."""
    cutoff = (now or time.time()) - _DEDUP_TTL_S
    return {i for i, ts in _load_seen_map(session_id).items() if ts >= cutoff}


def mark(session_id: str, ids: list[str] | set[str], *, now: float | None = None) -> None:
    """Record ids as injected (merge + write; drops ttl-expired ids, prunes old logs)."""
    if not ids:
        return
    try:
        from portaw.memory.store import locked

        ts = now or time.time()
        cutoff = ts - _DEDUP_TTL_S
        p = _path(session_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        # locked: parallel hooks in ONE session merge-write the same log — an
        # unlocked read-merge-write drops the other surface's mark (→ re-inject).
        with locked(p):
            merged = {i: t for i, t in _load_seen_map(session_id).items() if t >= cutoff}
            for i in ids:
                merged[str(i)] = ts
            p.write_text(json.dumps({"seen": merged, "ts": ts}), encoding="utf-8")
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
