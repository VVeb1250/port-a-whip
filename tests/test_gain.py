"""Per-set gain attribution tests — pure, no ccusage/subprocess (sessions injected)."""

import pytest

from portaw.bench import Session
from portaw.sets import gain, state


def _session(period: str, total: int, day: str) -> Session:
    return Session(
        period=period, agent="claude", last_activity=day, total_cost=1.0,
        tokens={"totalTokens": total, "inputTokens": 0, "cacheCreationTokens": 0,
                "cacheReadTokens": 0, "outputTokens": 0},
    )


def _install(tmp_path, monkeypatch, set_name="efficiency-starter", date="2026-06-05"):
    """Point the state ledger at a tmp file and record one install."""
    monkeypatch.setattr(state, "state_path", lambda: tmp_path / "state.json")
    state.record_install("claude-code", set_name, {"codegraph": {"command": "x"}}, today=date)


def test_raises_when_set_not_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "state_path", lambda: tmp_path / "state.json")
    with pytest.raises(ValueError, match="not paw-installed"):
        gain.gain_for_set("nope", sessions=[])


def test_splits_sessions_at_install_date(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, date="2026-06-05")
    sessions = [
        _session("b1", 1000, "2026-06-01"),
        _session("b2", 1200, "2026-06-03"),
        _session("a1", 600, "2026-06-06"),
        _session("a2", 800, "2026-06-08"),
    ]
    rep = gain.gain_for_set("efficiency-starter", sessions=sessions)
    assert rep.conclusive
    assert rep.before_n == 2 and rep.after_n == 2
    assert rep.before_median == 1100 and rep.after_median == 700
    assert rep.saved_per_session == 400
    assert round(rep.pct, 1) == round(400 / 1100 * 100, 1)


def test_install_day_session_counts_as_after(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, date="2026-06-05")
    sessions = [
        _session("b1", 100, "2026-06-04"),
        _session("b2", 100, "2026-06-04"),
        _session("a1", 50, "2026-06-05"),  # same day = after (>=)
        _session("a2", 50, "2026-06-07"),
    ]
    rep = gain.gain_for_set("efficiency-starter", sessions=sessions)
    assert rep.after_n == 2 and rep.before_n == 2


def test_inconclusive_below_min_side(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, date="2026-06-05")
    sessions = [
        _session("b1", 1000, "2026-06-01"),
        _session("a1", 600, "2026-06-06"),  # only 1 each side
    ]
    rep = gain.gain_for_set("efficiency-starter", sessions=sessions)
    assert not rep.conclusive
    assert "INCONCLUSIVE" in rep.note


def test_format_report_directional_label(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, date="2026-06-05")
    sessions = [
        _session("b1", 1000, "2026-06-01"), _session("b2", 1000, "2026-06-02"),
        _session("a1", 600, "2026-06-06"), _session("a2", 600, "2026-06-07"),
    ]
    rep = gain.gain_for_set("efficiency-starter", sessions=sessions)
    out = gain.format_report(rep)
    assert "DIRECTIONAL" in out and "saved 400" in out
