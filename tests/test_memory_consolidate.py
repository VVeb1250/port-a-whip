"""Consolidation tests — merge / promote / archive, pure, fixed clock."""

from datetime import date

from portaw.memory import store
from portaw.memory.consolidate import (
    ConsolidationConfig,
    consolidate,
    maybe_consolidate,
    merge_duplicates,
    promote,
)
from portaw.memory.schema import MemoryEntry

TODAY = date(2026, 6, 10)
FRESH = "2026-06-10"
OLD = "2026-01-01"


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    kw.setdefault("last_seen", FRESH)
    return MemoryEntry.new("lesson", body, **kw)


def test_merge_duplicates_sums_recurrence():
    a = _lesson("same body", recurrence=2)
    b = _lesson("same body", recurrence=3)  # same id
    merged, count = merge_duplicates([a, b])
    assert count == 1 and len(merged) == 1 and merged[0].recurrence == 5


def test_promote_project_lesson_after_enough_recurrence():
    cfg = ConsolidationConfig(promote_min_recurrence=3)
    e = _lesson("repo quirk", applicability="project:paw", recurrence=3)
    assert promote(e, cfg).applicability == "universal"


def test_promote_leaves_low_recurrence_project_lesson():
    cfg = ConsolidationConfig(promote_min_recurrence=3)
    e = _lesson("repo quirk", applicability="project:paw", recurrence=1)
    assert promote(e, cfg).applicability == "project:paw"


def test_consolidate_archives_stale_keeps_pinned():
    cfg = ConsolidationConfig(archive_activation=0.15)
    stale = _lesson("old note", last_seen=OLD, recurrence=1)
    pinned_stale = _lesson("pinned old", last_seen=OLD, recurrence=1, pinned=True)
    fresh = _lesson("fresh note", last_seen=FRESH, recurrence=5)
    res = consolidate([stale, pinned_stale, fresh], today=TODAY, cfg=cfg)
    kept_bodies = [e.body for e in res.kept]
    arch_bodies = [e.body for e in res.archived]
    assert "old note" in arch_bodies
    assert "pinned old" in kept_bodies and "fresh note" in kept_bodies


def test_consolidate_handles_equal_activation_without_crash():
    # two entries with identical recurrence + last_seen → equal activation.
    # regression for [sweep-tuple-sort]: must sort by key only, never compare entries.
    a = _lesson("alpha", recurrence=2, last_seen=FRESH)
    b = _lesson("beta", recurrence=2, last_seen=FRESH)
    res = consolidate([a, b], today=TODAY)
    assert len(res.kept) == 2


def test_consolidate_kept_sorted_by_activation_desc():
    hi = _lesson("hi", recurrence=10, last_seen=FRESH)
    lo = _lesson("lo", recurrence=1, last_seen=FRESH)
    res = consolidate([lo, hi], today=TODAY)
    assert res.kept[0].body == "hi"


# --- maybe_consolidate (the SessionStart opportunistic trigger) ---

def test_maybe_consolidate_runs_once_then_respects_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    store.save_lessons([_lesson("keep me", recurrence=5)])

    res = maybe_consolidate(today=TODAY)
    assert res is not None and [e.body for e in res.kept] == ["keep me"]
    assert (tmp_path / "mem" / ".last-consolidate").exists()
    assert maybe_consolidate(today=TODAY) is None  # within interval → skip


def test_maybe_consolidate_archives_stale_to_archive_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    store.save_lessons([
        _lesson("stale never-proven", last_seen=OLD, recurrence=1, confidence=0.5),
        _lesson("fresh", recurrence=5),
    ])
    res = maybe_consolidate(today=TODAY)
    assert res is not None and [e.body for e in res.archived] == ["stale never-proven"]
    assert [e.body for e in store.load_lessons()] == ["fresh"]
    archived = store._read_jsonl(store.archive_path())
    assert [e.body for e in archived] == ["stale never-proven"]


def test_maybe_consolidate_never_raises(monkeypatch):
    def boom():
        raise OSError("nope")

    monkeypatch.setattr(store, "global_dir", boom)
    assert maybe_consolidate(today=TODAY) is None


# --- effectiveness feedback (#8: misses → distrust + decay) ---

def test_effectiveness_accumulates_misses_and_decays_confidence():
    bad = _lesson("wrong fix", confidence=0.8, recurrence=5)
    good = _lesson("fine fix", confidence=0.8)
    pinned = _lesson("pinned fix", confidence=0.8, pinned=True)
    res = consolidate([bad, good, pinned], today=TODAY,
                      effectiveness={bad.id: 2, pinned.id: 4})
    assert res.weakened_count == 1                       # pinned exempt
    by_id = {e.id: e for e in res.kept}
    assert by_id[bad.id].misses == 2
    assert by_id[bad.id].confidence < 0.8                # one decay step
    assert by_id[good.id].misses == 0 and by_id[good.id].confidence == 0.8
    assert by_id[pinned.id].misses == 0


def test_maybe_consolidate_feeds_observation_misses_and_consumes(tmp_path, monkeypatch):
    import json as _json

    from portaw.memory import observations

    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    bad = _lesson("python → use py", confidence=0.9, recurrence=3)
    store.save_lessons([bad])
    obs_path = tmp_path / "mem" / "observations.jsonl"
    obs_path.write_text(_json.dumps({
        "sig": "command not found|python", "count": 5,
        "first_seen": "2026-06-01", "last_seen": FRESH,
        "lesson_id": bad.id, "linked_at_count": 2,       # 3 misses post-link
    }) + "\n", encoding="utf-8")

    res = maybe_consolidate(today=TODAY)
    assert res is not None and res.weakened_count == 1
    out = store.load_lessons()[0]
    assert out.misses == 3 and out.confidence < 0.9
    # ledger consumed: same misses never decay twice
    assert observations.load()["command not found|python"]["linked_at_count"] == 5

    (tmp_path / "mem" / ".last-consolidate").unlink()    # force a second pass
    res2 = maybe_consolidate(today=TODAY)
    assert res2 is not None and res2.weakened_count == 0  # nothing new → no decay


def test_distrusted_lesson_stops_injecting():
    from portaw.memory.gate import trusted

    popular_wrong = _lesson("popular wrong fix", confidence=0.9, recurrence=10, misses=3)
    assert not trusted(popular_wrong)                    # misses beat recurrence+confidence
    scoped_wrong = _lesson("stack wrong fix", applicability="stack:django", misses=3)
    assert not trusted(scoped_wrong)                     # scope does not shield it
    pinned_wrong = _lesson("human says keep", misses=10, pinned=True)
    assert trusted(pinned_wrong)                         # human override wins
    fresh = _lesson("ok fix", confidence=0.9, misses=2)
    assert trusted(fresh)                                # below the distrust cap
