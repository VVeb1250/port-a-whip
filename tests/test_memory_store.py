"""Memory store tests — isolated to tmp_path (never touches real ~/.paw)."""

import json

from portaw.memory import store
from portaw.memory.schema import Anchors, MemoryEntry


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    return MemoryEntry.new("lesson", body, **kw)


def test_load_missing_store_returns_empty(tmp_path):
    assert store.load_project(tmp_path) == []


def test_save_then_load_roundtrip(tmp_path):
    entries = [
        _lesson("use py not python", scope="project", trigger_terms=("python",)),
        _lesson("forgot await", scope="project", anchors=Anchors(symbols=("f",))),
    ]
    store.save_project(entries, tmp_path)
    loaded = store.load_project(tmp_path)
    assert loaded == entries


def test_read_skips_malformed_lines(tmp_path):
    p = store.project_path(tmp_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    good = MemoryEntry.new("lesson", "good", "project")
    p.write_text(
        "\n".join(["{ broken json", "", json.dumps(good.to_raw())]),
        encoding="utf-8",
    )
    loaded = store.load_project(tmp_path)
    assert len(loaded) == 1 and loaded[0].body == "good"


def test_write_is_atomic_no_tmp_left(tmp_path):
    store.save_project([_lesson("x", scope="project")], tmp_path)
    leftover = list(store.project_dir(tmp_path).glob("*.tmp"))
    assert leftover == []


def test_upsert_adds_new_entry():
    e = _lesson("new lesson")
    out = store.upsert([], e, last_seen="2026-06-10")
    assert out == [e]


def test_upsert_bumps_existing_twin_not_duplicate():
    e = _lesson("dup body", recurrence=1)
    twin = _lesson("dup body")  # same id (same body)
    out = store.upsert([e], twin, last_seen="2026-06-10")
    assert len(out) == 1
    assert out[0].recurrence == 2 and out[0].last_seen == "2026-06-10"


def test_upsert_is_pure_does_not_mutate_input():
    e = _lesson("dup body", recurrence=1)
    original = [e]
    store.upsert(original, _lesson("dup body"), last_seen="2026-06-10")
    assert original[0].recurrence == 1  # untouched


def test_global_and_project_paths_distinct(tmp_path):
    assert store.lessons_path().name == "lessons.jsonl"
    assert store.project_path(tmp_path).name == "project.jsonl"
    assert ".paw" in str(store.project_path(tmp_path))


def test_write_detail_creates_md(tmp_path):
    sd = store.project_dir(tmp_path)
    p = store.write_detail("abc123", sd, "# full writeup")
    assert p.exists() and p.read_text(encoding="utf-8") == "# full writeup"
    assert p.name == "abc123.md"
