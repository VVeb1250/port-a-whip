"""Cross-host lesson sync — git-backed, no daemon (the moat-proof).

The L3 claim is cross-host PORTABILITY, but lessons lived in one machine's
~/.paw/memory. This makes that dir a git repo against a user-provided private
remote and syncs lessons.jsonl through it. The content-hash id makes the merge
conflict-free by construction: the same mistake captured on two machines IS the
same id, so merging = field-wise union — git is transport + history only, no
git-merge ever runs (the remote file is read via `git show FETCH_HEAD:…`).

Merge semantics (CRDT-style, idempotent — re-sync never inflates):
  same id   → max(recurrence), max(misses), max(confidence), latest last_seen,
              pinned OR (counts grow independently per machine; max is the safe
              idempotent bound — summing would double-count every sync).
  new id    → imported with source="sync" and confidence capped below the
              universal trusted bar. The remote is the USER'S OWN private repo
              (threat model = accidental garbage propagation, not adversary):
              the cap means an imported universal lesson must reinforce once
              locally before it injects; narrower scopes inject as usual.

Mechanics: git via subprocess list-args ONLY (no shell=True), explicit
timeouts, offline-tolerant (fetch/push failures degrade to local-commit-only).
Only lessons.jsonl travels — session logs, observations, archive and locks are
machine-local (a .gitignore written at init enforces this).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, replace

from portaw.memory.schema import MemoryEntry

QUARANTINE_CAP = 0.7   # just under the universal trusted bar (0.75): one local
#                        confirmed recurrence re-trusts an imported lesson
_GIT_TIMEOUT = 30
_BRANCH = "main"

_GITIGNORE = """\
# paw memory sync: only the lesson store travels between machines.
*
!.gitignore
!lessons.jsonl
"""


class SyncError(Exception):
    """Sync cannot proceed (not initialized / git missing / remote broken)."""


@dataclass(frozen=True)
class SyncResult:
    imported: int       # new lessons that arrived from the remote
    merged: int         # existing ids updated from remote evidence
    pushed: bool
    message: str


# ----------------------------------------------------------------- pure merge

def merge_remote(
    local: list[MemoryEntry], remote: list[MemoryEntry], *, cap: float = QUARANTINE_CAP,
) -> tuple[list[MemoryEntry], int, int]:
    """Fold remote entries into local. Returns (combined, imported, merged)."""
    by_id = {e.id: e for e in local}
    imported = merged = 0
    for r in remote:
        cur = by_id.get(r.id)
        if cur is None:
            by_id[r.id] = replace(r, source="sync", confidence=min(r.confidence, cap))
            imported += 1
            continue
        # a still-quarantined entry (source="sync", never reinforced locally) keeps
        # the cap on REMOTE confidence claims across re-syncs — otherwise the second
        # sync would launder the very confidence the first one capped. Local
        # evidence raises confidence on its own (bumped()); that path is untouched.
        r_conf = min(r.confidence, cap) if cur.source == "sync" else r.confidence
        folded = replace(
            cur,
            recurrence=max(cur.recurrence, r.recurrence),
            misses=max(cur.misses, r.misses),
            confidence=max(cur.confidence, r_conf),
            last_seen=max(cur.last_seen, r.last_seen),
            pinned=cur.pinned or r.pinned,
        )
        if folded != cur:
            merged += 1
        by_id[r.id] = folded
    return list(by_id.values()), imported, merged


# ----------------------------------------------------------------- git plumbing

def _git(args: list[str], cwd, *, check: bool = True) -> subprocess.CompletedProcess:
    try:
        cp = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
            timeout=_GIT_TIMEOUT, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError as e:
        raise SyncError("git not found on PATH — sync needs git") from e
    except subprocess.TimeoutExpired as e:
        raise SyncError(f"git {args[0]} timed out") from e
    if check and cp.returncode != 0:
        raise SyncError(f"git {' '.join(args)} failed: {cp.stderr.strip()[:300]}")
    return cp


def _commit_if_changed(d) -> bool:
    """Stage the lesson store and commit when it changed. Identity is pinned so
    sync works on boxes with no git user configured."""
    _git(["add", "-A"], d)  # .gitignore restricts this to the synced files
    if not _git(["status", "--porcelain"], d).stdout.strip():
        return False
    _git(["-c", "user.name=paw", "-c", "user.email=paw@local",
          "commit", "-m", "paw memory sync"], d)
    return True


def _tie_history(d) -> None:
    """Join our history with FETCH_HEAD via `merge -s ours` — content was already
    folded by merge_remote (our tree IS the merged truth), so this merge exists
    only to make the next push a fast-forward. `-s ours` never conflicts; failures
    (unborn HEAD, already up to date) are no-ops."""
    _git(["-c", "user.name=paw", "-c", "user.email=paw@local",
          "merge", "-s", "ours", "--allow-unrelated-histories",
          "-m", "paw sync merge", "FETCH_HEAD"], d, check=False)


def _read_remote_lessons(d) -> list[MemoryEntry]:
    """Parse lessons.jsonl out of FETCH_HEAD without touching the working tree."""
    cp = _git(["show", "FETCH_HEAD:lessons.jsonl"], d, check=False)
    if cp.returncode != 0:
        return []  # remote has no lesson store yet
    out: list[MemoryEntry] = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            import json

            out.append(MemoryEntry.from_raw(json.loads(line)))
        except Exception:
            continue  # malformed-tolerant, same stance as the local reader
    return out


# ----------------------------------------------------------------- public flow

def init_sync(remote_url: str) -> str:
    """One-time setup: turn ~/.paw/memory into a sync repo against `remote_url`
    (the user's PRIVATE repo). Idempotent — re-running updates the remote URL."""
    from portaw.memory import store

    d = store.global_dir()
    d.mkdir(parents=True, exist_ok=True)
    if not (d / ".git").exists():
        _git(["init", "-b", _BRANCH], d)
    (d / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")
    has_origin = _git(["remote"], d).stdout.split()
    if "origin" in has_origin:
        _git(["remote", "set-url", "origin", remote_url], d)
    else:
        _git(["remote", "add", "origin", remote_url], d)
    _commit_if_changed(d)
    return f"sync initialized: {d} → {remote_url}"


def sync() -> SyncResult:
    """commit local → fetch → merge (pure) → save+commit → push (one retry)."""
    from portaw.memory import store

    d = store.global_dir()
    if not (d / ".git").exists():
        raise SyncError(
            "sync not initialized — run `portaw memory sync --init <remote-url>` "
            "(a PRIVATE repo; lessons may reference your environment)")

    with store.locked(store.lessons_path()):
        _commit_if_changed(d)  # local state is never lost, whatever happens next

        fetch = _git(["fetch", "origin", _BRANCH], d, check=False)
        if fetch.returncode != 0:
            # offline / empty remote → local commit stands, try a push anyway
            pushed = _git(["push", "-u", "origin", _BRANCH], d, check=False).returncode == 0
            note = "remote unreachable or empty" if not pushed else "pushed (first sync)"
            return SyncResult(0, 0, pushed, note)

        remote = _read_remote_lessons(d)
        combined, imported, merged = merge_remote(store.load_lessons(), remote)
        if imported or merged:
            store.save_lessons(combined)
            _commit_if_changed(d)
        _tie_history(d)

        pushed = _git(["push", "-u", "origin", _BRANCH], d, check=False).returncode == 0
        if not pushed:
            # remote advanced between our fetch and push → fold once more, retry
            if _git(["fetch", "origin", _BRANCH], d, check=False).returncode == 0:
                remote = _read_remote_lessons(d)
                combined, imp2, mrg2 = merge_remote(store.load_lessons(), remote)
                imported, merged = imported + imp2, merged + mrg2
                if imp2 or mrg2:
                    store.save_lessons(combined)
                    _commit_if_changed(d)
                _tie_history(d)
                pushed = _git(["push", "-u", "origin", _BRANCH], d, check=False).returncode == 0

    msg = f"imported {imported}, merged {merged}, " + ("pushed" if pushed else "PUSH FAILED — re-run")
    return SyncResult(imported, merged, pushed, msg)
