"""MemoryEntry / Anchors schema tests — pure, no I/O."""

from portaw.memory.schema import Anchors, MemoryEntry, make_id


def test_make_id_stable_for_same_normalized_body():
    a = make_id("lesson", "use py not python")
    b = make_id("lesson", "  USE   PY   not Python ")  # whitespace + case differ
    assert a == b  # normalized → same id → free dedup


def test_make_id_differs_by_type_and_body():
    assert make_id("lesson", "x") != make_id("project", "x")
    assert make_id("lesson", "x") != make_id("lesson", "y")


def test_new_derives_content_hash_id():
    e = MemoryEntry.new("lesson", "use py not python", "global")
    assert e.id == make_id("lesson", "use py not python")
    assert e.type == "lesson" and e.scope == "global"


def test_roundtrip_to_raw_from_raw_preserves_all_fields():
    e = MemoryEntry.new(
        "lesson", "trigger -> fix", "global",
        trigger_terms=("python", "windows"),
        anchors=Anchors(symbols=("run_build",), paths=("a/b.py",)),
        applicability="stack:windows", confidence=0.9, recurrence=3, pinned=True,
    )
    back = MemoryEntry.from_raw(e.to_raw())
    assert back == e


def test_anchors_is_empty():
    assert Anchors().is_empty()
    assert not Anchors(paths=("x.py",)).is_empty()


def test_bumped_increments_recurrence_and_is_immutable():
    e = MemoryEntry.new("lesson", "x", "global", recurrence=1)
    b = e.bumped(last_seen="2026-06-10")
    assert b.recurrence == 2 and b.last_seen == "2026-06-10"
    assert e.recurrence == 1 and e.last_seen == ""  # original untouched


def test_searchable_text_includes_body_triggers_symbols():
    e = MemoryEntry.new(
        "lesson", "forgot await", "global",
        trigger_terms=("async",), anchors=Anchors(symbols=("fetch_user",)),
    )
    txt = e.searchable_text
    assert "forgot await" in txt and "async" in txt and "fetch_user" in txt
