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
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

from portaw.memory.schema import MemoryEntry

_LESSONS_FILE = "lessons.jsonl"
_PROJECT_FILE = "project.jsonl"
_ARCHIVE_FILE = "lessons-archive.jsonl"


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
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []  # unreadable store (perms/race) degrades to empty, not a crash
    entries: list[MemoryEntry] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(MemoryEntry.from_raw(json.loads(line)))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue  # one bad line must not poison the whole store
    return entries


def _write_jsonl_raw(path: Path, lines: list[str]) -> None:
    """Atomic write of pre-serialized jsonl lines (shared by the entry store + the
    observation ledger). pid-suffixed tmp + replace-retry → no interleave, no
    half-written file even under concurrent Stop hooks."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise MemoryStoreError(f"cannot create store dir {path.parent}: {e}") from e
    body = "\n".join(lines)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(body + ("\n" if body else ""), encoding="utf-8")
    try:
        _replace_with_retry(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)  # leftover only when replace failed


def _write_jsonl(path: Path, entries: list[MemoryEntry]) -> None:
    """Atomic write of MemoryEntries."""
    _write_jsonl_raw(path, [json.dumps(e.to_raw(), ensure_ascii=False) for e in entries])


def _replace_with_retry(tmp: Path, path: Path, attempts: int = 3) -> None:
    """os.replace is atomic, but on Windows it raises PermissionError while a
    concurrent reader holds the destination open — brief retry covers that window."""
    import time

    for i in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == attempts - 1:
                raise MemoryStoreError(f"store busy, could not replace {path}")
            time.sleep(0.05 * (i + 1))


# --- cross-process mutex (read-modify-write spans, not single writes) ---

@contextmanager
def locked(path: Path, *, timeout: float = 2.0, stale: float = 10.0) -> Iterator[None]:
    """Best-effort cross-process lock for a read-modify-write on `path`.

    The atomic single-file write below prevents CORRUPTION, but two concurrent
    hooks (parallel tool calls) doing load→modify→save still lose one writer's
    update. This O_CREAT|O_EXCL lockfile serializes that span — portable
    (Windows + POSIX, no msvcrt/fcntl). Best-effort by doctrine: a lock older
    than `stale` is broken (crashed holder), and on `timeout` we proceed
    UNLOCKED — a hook must never hang; the worst case is the pre-lock behavior.
    """
    lock = path.with_name(path.name + ".lock")
    acquired = False
    deadline = time.monotonic() + timeout
    try:
        lock.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            acquired = True
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > stale:
                    lock.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                break  # proceed unlocked — never block a hook
            time.sleep(0.02)
        except OSError:
            break  # unwritable dir etc. → unlocked, tolerant
    try:
        yield
    finally:
        if acquired:
            try:
                lock.unlink(missing_ok=True)
            except OSError:
                pass


# --- lessons (global) ---

def lessons_path() -> Path:
    return global_dir() / _LESSONS_FILE


def load_lessons() -> list[MemoryEntry]:
    return _read_jsonl(lessons_path())


def save_lessons(entries: list[MemoryEntry]) -> None:
    _write_jsonl(lessons_path(), entries)


def update_lessons(
    mutate: Callable[[list[MemoryEntry]], list[MemoryEntry]],
) -> list[MemoryEntry]:
    """load → mutate → save under the store lock (the safe span for concurrent
    hook writers). Returns what was saved. Use this from hooks; plain load/save
    stay for read-only callers and human-paced CLI flows."""
    with locked(lessons_path()):
        out = mutate(load_lessons())
        save_lessons(out)
    return out


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
    A bump also merges the incoming pin + max confidence, so re-adding a lesson
    with `--pin` actually pins it (a sticky flag, never silently dropped).
    """
    from dataclasses import replace

    out: list[MemoryEntry] = []
    found = False
    for e in entries:
        if e.id == entry.id:
            out.append(replace(
                e.bumped(last_seen=last_seen),
                pinned=e.pinned or entry.pinned,
                confidence=max(e.confidence, entry.confidence),
            ))
            found = True
        else:
            out.append(e)
    if not found:
        out.append(entry)
    return out


# --- archive (consolidation moves stale lessons here, not deletion) ---

def archive_path() -> Path:
    return global_dir() / _ARCHIVE_FILE


def append_archive(entries: list[MemoryEntry]) -> None:
    """Append archived lessons to the archive store (history, recur → revive)."""
    if not entries:
        return
    _write_jsonl(archive_path(), _read_jsonl(archive_path()) + entries)


# --- cold-tier detail (optional full writeup) ---

def detail_path(entry_id: str, scope_dir: Path) -> Path:
    return scope_dir / "details" / f"{entry_id}.md"


def write_detail(entry_id: str, scope_dir: Path, markdown: str) -> Path:
    """Persist a full writeup for an entry (loaded only on explicit recall)."""
    p = detail_path(entry_id, scope_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(markdown, encoding="utf-8")
    return p
