"""MemoryEntry / Anchors schema tests — pure, no I/O."""

from portaw.memory.schema import (
    CAUSED_BY,
    RELATED,
    SUPERSEDED_BY,
    Anchors,
    MemoryEntry,
    Relation,
    make_id,
)


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
        applicability="stack:windows", confidence=0.9, recurrence=3, misses=2,
        pinned=True,
    )
    back = MemoryEntry.from_raw(e.to_raw())
    assert back == e


def test_from_raw_tolerates_pre_misses_records():
    """Records written before the misses field existed load as misses=0."""
    e = MemoryEntry.new("lesson", "old record", "global")
    raw = e.to_raw()
    del raw["misses"]
    assert MemoryEntry.from_raw(raw).misses == 0


def test_anchors_is_empty():
    assert Anchors().is_empty()
    assert not Anchors(paths=("x.py",)).is_empty()


def test_bumped_increments_recurrence_and_is_immutable():
    e = MemoryEntry.new("lesson", "x", "global", recurrence=1)
    b = e.bumped(last_seen="2026-06-10")
    assert b.recurrence == 2 and b.last_seen == "2026-06-10"
    assert e.recurrence == 1 and e.last_seen == ""  # original untouched


def test_from_raw_tolerates_pre_relations_records():
    """Records written before the relations field existed load with no edges."""
    e = MemoryEntry.new("lesson", "old record", "global")
    raw = e.to_raw()
    del raw["relations"]
    assert MemoryEntry.from_raw(raw).relations == ()


def test_relation_roundtrip_preserves_edges():
    e = MemoryEntry.new("lesson", "x", "global").with_relation(SUPERSEDED_BY, "abc123")
    back = MemoryEntry.from_raw(e.to_raw())
    assert back == e
    assert back.targets(SUPERSEDED_BY) == ("abc123",)


def test_with_relation_is_idempotent_and_immutable():
    e = MemoryEntry.new("lesson", "x", "global")
    once = e.with_relation(RELATED, "t1")
    twice = once.with_relation(RELATED, "t1")  # same edge again
    assert once.relations == (Relation(RELATED, "t1"),)
    assert twice is once  # no duplicate, returns self
    assert e.relations == ()  # original untouched


def test_with_relation_rejects_self_edge_and_unknown_type():
    e = MemoryEntry.new("lesson", "x", "global")
    assert e.with_relation(SUPERSEDED_BY, e.id) is e   # self-edge ignored
    assert e.with_relation("invented_rel", "t1") is e  # unknown type ignored


def test_targets_filters_by_rel_type():
    e = (
        MemoryEntry.new("lesson", "x", "global")
        .with_relation(CAUSED_BY, "root")
        .with_relation(RELATED, "a")
        .with_relation(RELATED, "b")
    )
    assert e.targets(CAUSED_BY) == ("root",)
    assert set(e.targets(RELATED)) == {"a", "b"}


def test_searchable_text_includes_body_triggers_symbols():
    e = MemoryEntry.new(
        "lesson", "forgot await", "global",
        trigger_terms=("async",), anchors=Anchors(symbols=("fetch_user",)),
    )
    txt = e.searchable_text
    assert "forgot await" in txt and "async" in txt and "fetch_user" in txt
