"""Session inject-log tests — per-id ttl dedup + legacy back-compat (isolated _dir)."""

import json

from portaw.memory import sessionlog

SID = "sess-1"


def test_mark_then_seen_within_ttl():
    sessionlog.mark(SID, ["a", "b"], now=1000.0)
    assert sessionlog.seen(SID, now=1000.0) == {"a", "b"}


def test_id_expires_after_dedup_ttl():
    sessionlog.mark(SID, ["a"], now=1000.0)
    # just inside the ttl → still seen; past it → forgotten (may re-inject)
    assert sessionlog.seen(SID, now=1000.0 + sessionlog._DEDUP_TTL_S - 1) == {"a"}
    assert sessionlog.seen(SID, now=1000.0 + sessionlog._DEDUP_TTL_S + 1) == set()


def test_mark_drops_expired_ids_on_write():
    sessionlog.mark(SID, ["old"], now=1000.0)
    # a much later mark must not carry the expired id forward (bounds the file)
    later = 1000.0 + sessionlog._DEDUP_TTL_S + 10
    sessionlog.mark(SID, ["new"], now=later)
    raw = json.loads(sessionlog._path(SID).read_text(encoding="utf-8"))
    assert set(raw["seen"]) == {"new"}


def test_marks_merge_across_surfaces():
    sessionlog.mark(SID, ["a"], now=1000.0)
    sessionlog.mark(SID, ["b"], now=1001.0)
    assert sessionlog.seen(SID, now=1001.0) == {"a", "b"}


def test_legacy_ids_list_still_reads():
    # an old-format log written before per-id timestamps
    p = sessionlog._path(SID)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"ids": ["x", "y"], "ts": 1000.0}), encoding="utf-8")
    assert sessionlog.seen(SID, now=1000.5) == {"x", "y"}
    # and they expire by the same ttl
    assert sessionlog.seen(SID, now=1000.0 + sessionlog._DEDUP_TTL_S + 1) == set()


def test_reset_wipes_log():
    sessionlog.mark(SID, ["a"], now=1000.0)
    sessionlog.reset(SID)
    assert sessionlog.seen(SID, now=1000.0) == set()


def test_seen_empty_when_no_log():
    assert sessionlog.seen("never-marked") == set()
