"""Cross-host lesson sync (#7) — pure merge semantics + real-git round trip.

Integration tests drive two simulated machines (two tmp global_dirs) against
one local bare repo as the remote — full fetch/merge/push without network.
"""

import shutil
import subprocess

import pytest

from portaw.memory import store
from portaw.memory.gate import trusted
from portaw.memory.schema import MemoryEntry
from portaw.memory.sync import (
    QUARANTINE_CAP,
    SyncError,
    init_sync,
    merge_remote,
    sync,
)

GIT = shutil.which("git") is not None


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    kw.setdefault("confidence", 0.9)
    kw.setdefault("last_seen", "2026-06-12")
    return MemoryEntry.new("lesson", body, **kw)


# --- pure merge ---

def test_merge_imports_new_entry_quarantined():
    remote = [_lesson("remote wisdom", confidence=0.95)]
    combined, imported, merged = merge_remote([], remote)
    assert (imported, merged) == (1, 0)
    e = combined[0]
    assert e.source == "sync" and e.confidence == QUARANTINE_CAP
    assert not trusted(e)            # universal + capped + rec 1 → must earn it locally
    assert trusted(e.bumped(last_seen="2026-06-13"))  # one local recurrence re-trusts


def test_merge_same_id_folds_fieldwise_max():
    local = [_lesson("shared", confidence=0.6, recurrence=5, misses=1, last_seen="2026-06-10")]
    remote = [_lesson("shared", confidence=0.8, recurrence=3, misses=2,
                      last_seen="2026-06-12", pinned=True)]
    combined, imported, merged = merge_remote(local, remote)
    assert (imported, merged) == (0, 1)
    e = combined[0]
    assert e.recurrence == 5 and e.misses == 2 and e.confidence == 0.8
    assert e.last_seen == "2026-06-12" and e.pinned is True
    assert e.source != "sync"        # known id = already vouched locally, no quarantine


def test_merge_is_idempotent():
    local = [_lesson("a", recurrence=4)]
    remote = [_lesson("a", recurrence=4), _lesson("b")]
    once, imp1, _ = merge_remote(local, remote)
    twice, imp2, mrg2 = merge_remote(once, remote)
    assert imp1 == 1 and (imp2, mrg2) == (0, 0)      # re-sync never inflates
    assert sorted(e.body for e in twice) == ["a", "b"]


def test_sync_requires_init(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    with pytest.raises(SyncError, match="not initialized"):
        sync()


# --- real git round trip (two machines, one bare remote) ---

@pytest.mark.skipif(not GIT, reason="git not on PATH")
def test_two_machine_round_trip(tmp_path, monkeypatch):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)],
                   check=True, capture_output=True)
    mem_a, mem_b = tmp_path / "a", tmp_path / "b"

    # machine A: capture a lesson, init, push
    monkeypatch.setattr(store, "global_dir", lambda: mem_a)
    store.save_lessons([_lesson("use py not python", recurrence=3)])
    init_sync(str(bare))
    res_a = sync()
    assert res_a.pushed

    # machine B: fresh box, pulls A's lesson (quarantined), adds its own
    monkeypatch.setattr(store, "global_dir", lambda: mem_b)
    store.save_lessons([_lesson("git commit -F not -m on PS5.1")])
    init_sync(str(bare))
    res_b = sync()
    assert res_b.pushed and res_b.imported == 1
    bodies_b = {e.body: e for e in store.load_lessons()}
    assert set(bodies_b) == {"use py not python", "git commit -F not -m on PS5.1"}
    assert bodies_b["use py not python"].source == "sync"
    assert bodies_b["use py not python"].confidence == QUARANTINE_CAP
    assert bodies_b["use py not python"].recurrence == 3   # evidence travels

    # machine A: second sync receives B's lesson despite diverged history
    monkeypatch.setattr(store, "global_dir", lambda: mem_a)
    res_a2 = sync()
    assert res_a2.pushed and res_a2.imported == 1
    bodies_a = {e.body for e in store.load_lessons()}
    assert bodies_a == {"use py not python", "git commit -F not -m on PS5.1"}

    # steady state: nothing new in either direction
    res_a3 = sync()
    assert res_a3.imported == 0 and res_a3.merged == 0 and res_a3.pushed


@pytest.mark.skipif(not GIT, reason="git not on PATH")
def test_machine_local_files_never_travel(tmp_path, monkeypatch):
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)],
                   check=True, capture_output=True)
    mem = tmp_path / "m"
    monkeypatch.setattr(store, "global_dir", lambda: mem)
    store.save_lessons([_lesson("travels")])
    (mem / "observations.jsonl").write_text('{"sig":"x","count":9}\n', encoding="utf-8")
    (mem / "lessons-archive.jsonl").write_text("{}\n", encoding="utf-8")
    init_sync(str(bare))
    assert sync().pushed
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=str(mem), capture_output=True, text=True,
    ).stdout.split()
    assert "lessons.jsonl" in tracked
    assert "observations.jsonl" not in tracked       # machine-local stays local
    assert "lessons-archive.jsonl" not in tracked
