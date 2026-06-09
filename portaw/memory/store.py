"""Memory persistence — jsonl, no-daemon, offline.

Two stores (scope split, §2):
  GLOBAL  ~/.paw/memory/lessons.jsonl     lessons (cross-project, the moat)
  PROJECT <root>/.paw/memory/project.jsonl project decisions/rationale

I/O boundary only — schema.py holds the pure record, callers pass entries.
Reads are malformed-tolerant (skip bad lines, never crash a recall). Writes are
atomic (temp + os.replace) so a crash never corrupts the store. Cold-tier detail
md lives under <store>/details/<id>.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from portaw.memory.schema import MemoryEntry

_LESSONS_FILE = "lessons.jsonl"
_PROJECT_FILE = "project.jsonl"


class MemoryStoreError(RuntimeError):
    """store dir unwritable / path resolution failure."""


def global_dir() -> Path:
    """~/.paw/memory — global lesson store."""
    return Path.home() / ".paw" / "memory"


def project_dir(root: Path | str | None = None) -> Path:
    """<root>/.paw/memory — project store. Default root = cwd."""
    base = Path(root) if root is not None else Path.cwd()
    return base / ".paw" / "memory"


def _read_jsonl(path: Path) -> list[MemoryEntry]:
    """Load entries, skipping malformed lines (tolerant — never crash recall)."""
    if not path.exists():
        return []
    entries: list[MemoryEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(MemoryEntry.from_raw(json.loads(line)))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue  # one bad line must not poison the whole store
    return entries


def _write_jsonl(path: Path, entries: list[MemoryEntry]) -> None:
    """Atomic write: serialize to a temp file in the same dir, then os.replace."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise MemoryStoreError(f"cannot create store dir {path.parent}: {e}") from e
    body = "\n".join(json.dumps(e.to_raw(), ensure_ascii=False) for e in entries)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(body + ("\n" if body else ""), encoding="utf-8")
    os.replace(tmp, path)  # atomic on same filesystem (Windows + POSIX)


# --- lessons (global) ---

def lessons_path() -> Path:
    return global_dir() / _LESSONS_FILE


def load_lessons() -> list[MemoryEntry]:
    return _read_jsonl(lessons_path())


def save_lessons(entries: list[MemoryEntry]) -> None:
    _write_jsonl(lessons_path(), entries)


# --- project ---

def project_path(root: Path | str | None = None) -> Path:
    return project_dir(root) / _PROJECT_FILE


def load_project(root: Path | str | None = None) -> list[MemoryEntry]:
    return _read_jsonl(project_path(root))


def save_project(entries: list[MemoryEntry], root: Path | str | None = None) -> None:
    _write_jsonl(project_path(root), entries)


# --- upsert (dedup by content-hash id; bump recurrence on collision) ---

def upsert(
    entries: list[MemoryEntry], entry: MemoryEntry, *, last_seen: str
) -> list[MemoryEntry]:
    """Return a NEW list with `entry` added, or its existing twin bumped.

    Dedup key = id (content hash). Pure — caller persists the result. This is the
    free cross-project dedup: same body → same id → recurrence++ instead of a dup.
    """
    out: list[MemoryEntry] = []
    found = False
    for e in entries:
        if e.id == entry.id:
            out.append(e.bumped(last_seen=last_seen))
            found = True
        else:
            out.append(e)
    if not found:
        out.append(entry)
    return out


# --- cold-tier detail (optional full writeup) ---

def detail_path(entry_id: str, scope_dir: Path) -> Path:
    return scope_dir / "details" / f"{entry_id}.md"


def write_detail(entry_id: str, scope_dir: Path, markdown: str) -> Path:
    """Persist a full writeup for an entry (loaded only on explicit recall)."""
    p = detail_path(entry_id, scope_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(markdown, encoding="utf-8")
    return p
