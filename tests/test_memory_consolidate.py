"""Consolidation tests — merge / promote / archive, pure, fixed clock."""

from datetime import date

from portaw.memory.consolidate import (
    ConsolidationConfig,
    consolidate,
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
