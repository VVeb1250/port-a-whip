"""Unit tests for B1 bench pure logic (no subprocess / no ccusage)."""

import pytest

from portaw.bench import CcusageError, Session, diff, find_session

_RAW = {
    "period": "017df266-1e64-4f84-9c2e-71d71dbe97d5",
    "agent": "claude",
    "metadata": {"lastActivity": "2026-06-05"},
    "totalCost": 32.74,
    "totalTokens": 1000,
    "inputTokens": 100,
    "cacheCreationTokens": 200,
    "cacheReadTokens": 600,
    "outputTokens": 100,
}


def _session(period: str, total: int, cost: float = 1.0) -> Session:
    return Session(
        period=period,
        agent="claude",
        last_activity="2026-06-05",
        total_cost=cost,
        tokens={
            "totalTokens": total,
            "inputTokens": total // 10,
            "cacheCreationTokens": total // 5,
            "cacheReadTokens": total // 2,
            "outputTokens": total // 10,
        },
    )


def test_from_raw_parses_all_token_keys():
    s = Session.from_raw(_RAW)
    assert s.period.startswith("017df266")
    assert s.agent == "claude"
    assert s.last_activity == "2026-06-05"
    assert s.tokens["totalTokens"] == 1000
    assert s.tokens["cacheReadTokens"] == 600


def test_from_raw_defaults_missing_fields_to_zero():
    s = Session.from_raw({"period": "abc"})
    assert s.tokens["totalTokens"] == 0
    assert s.total_cost == 0.0
    assert s.last_activity == ""


def test_diff_positive_saved_when_treated_uses_fewer():
    base = _session("baseline0", 1000, cost=2.0)
    treat = _session("treated00", 400, cost=0.8)
    d = diff(base, treat)
    assert d["tokens"]["totalTokens"]["saved"] == 600
    assert d["tokens"]["totalTokens"]["pct"] == 60.0
    assert d["cost"]["saved"] == 1.2


def test_diff_negative_saved_when_treated_uses_more():
    base = _session("baseline0", 400)
    treat = _session("treated00", 1000)
    d = diff(base, treat)
    assert d["tokens"]["totalTokens"]["saved"] == -600
    assert d["tokens"]["totalTokens"]["pct"] == -150.0


def test_diff_zero_baseline_yields_zero_pct_not_crash():
    base = _session("baseline0", 0)
    treat = _session("treated00", 100)
    d = diff(base, treat)
    assert d["tokens"]["totalTokens"]["pct"] == 0.0


def test_find_session_matches_unique_prefix():
    sessions = [_session("aaaa1111", 1), _session("bbbb2222", 2)]
    assert find_session(sessions, "bbbb").period == "bbbb2222"


def test_find_session_no_match_raises():
    with pytest.raises(CcusageError, match="no session matching"):
        find_session([_session("aaaa1111", 1)], "zzzz")


def test_find_session_ambiguous_prefix_raises():
    sessions = [_session("aaaa1111", 1), _session("aaaa2222", 2)]
    with pytest.raises(CcusageError, match="ambiguous"):
        find_session(sessions, "aaaa")
