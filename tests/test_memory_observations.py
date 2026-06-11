"""Observation ledger + evidence-confidence (the runtime evidence loop, 2026-06-11).

Step 1 ledger: signature normalization + count/link/effectiveness queries.
Step 2 nudge: tool-hook records failures, nudges un-lessoned repeats, dedups.
Step 3 confidence: reinforce on recurrence (saturating), decay stale seeds.
Step 4 report: `memory observations` surfaces capture candidates + leaky lessons.
"""

import json

from click.testing import CliRunner

import portaw.memory.observations as obs
import portaw.memory.sessionlog as sessionlog
import portaw.memory.store as store
from portaw.adapters.memory_hooks import run_tool_hook
from portaw.main import cli
from portaw.memory import confidence
from portaw.memory.schema import MemoryEntry


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    kw.setdefault("confidence", 0.9)
    kw.setdefault("last_seen", "2026-06-10")
    return MemoryEntry.new("lesson", body, **kw)


def _wire(monkeypatch, tmp_path, lessons=()):
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    monkeypatch.setattr(store, "load_lessons", lambda: list(lessons))
    monkeypatch.setattr(store, "load_project", lambda root=None: [])
    monkeypatch.setattr(sessionlog, "_dir", lambda: tmp_path / "session")
    (tmp_path / "mem").mkdir(parents=True, exist_ok=True)


# --- Step 1: signature ---

def test_signature_groups_by_program_and_error():
    s1 = obs.signature("python x.py", "bash: python: command not found")
    s2 = obs.signature("python other.py", "bash: python: command not found")
    assert s1 == s2 == "command not found|python"


def test_signature_distinguishes_programs():
    a = obs.signature("python x", "x: command not found")
    b = obs.signature("node y", "y: command not found")
    assert a != b


def test_signature_empty_when_no_error():
    assert obs.signature("python x.py", "ran fine, all good") == ""


def test_signature_basename_only():
    s = obs.signature("/usr/bin/python x", "python: command not found")
    assert s == "command not found|python"


# --- Step 1: ledger record/queries ---

def test_record_bumps_count(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    obs.record("python x", "python: command not found", today="2026-06-11")
    r = obs.record("python y", "python: command not found", today="2026-06-12")
    assert r["count"] == 2 and r["first_seen"] == "2026-06-11" and r["last_seen"] == "2026-06-12"


def test_record_none_when_not_a_failure(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    assert obs.record("python x", "everything ok") is None


def test_record_links_lesson_and_snapshots_count(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    obs.record("python x", "python: command not found")
    r = obs.record("python x", "python: command not found", lesson_id="abc123")
    assert r["lesson_id"] == "abc123" and r["linked_at_count"] == 2


def test_uncovered_repeats(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    for _ in range(3):
        obs.record("foo", "foo: command not found")
    obs.record("bar", "bar: command not found")  # only once
    reps = obs.uncovered_repeats(min_count=2)
    assert [r["sig"] for r in reps] == ["command not found|foo"]


def test_recurring_despite_lesson(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    obs.record("foo", "foo: command not found", lesson_id="L1")  # linked at count 1
    obs.record("foo", "foo: command not found")                  # recurs after lesson
    leaks = obs.recurring_despite_lesson()
    assert len(leaks) == 1 and obs.linked_misses(leaks[0]) == 1


# --- Step 2: tool-hook nudge ---

def _bash(stderr, sid="s1", cmd="python x.py"):
    return json.dumps({"session_id": sid, "tool_name": "Bash",
                       "tool_input": {"command": cmd},
                       "tool_response": {"stderr": stderr}})


def test_nudge_fires_on_second_uncovered_hit(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path, lessons=[])  # no lessons → uncovered
    p = _bash("zoxide: command not found", sid="n1", cmd="zoxide query x")
    assert run_tool_hook(p) is None                 # first hit: count 1, no nudge
    out = run_tool_hook(p)                           # second hit: nudge
    assert out is not None and "no lesson" in out and "command not found|zoxide" in out


def test_nudge_dedups_within_session(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path, lessons=[])
    p = _bash("zoxide: command not found", sid="n2", cmd="zoxide query x")
    run_tool_hook(p)
    assert run_tool_hook(p) is not None              # 2nd → nudge
    assert run_tool_hook(p) is None                  # 3rd → already nudged this session


def test_fuzzy_token_match_is_not_coverage(tmp_path, monkeypatch):
    # the py lesson shares "command not found" with a foobar error but is NOT about
    # foobar → must stay un-lessoned → nudge on repeat, never linked to the py lesson.
    lesson = _lesson("use py not python on windows", trigger_terms=("python",))
    _wire(monkeypatch, tmp_path, lessons=[lesson])
    p = _bash("foobar: command not found", sid="fz", cmd="foobar --x")
    assert run_tool_hook(p) is None                          # 1st: not covered, count 1
    out = run_tool_hook(p)                                    # 2nd: nudge, NOT py inject
    assert out is not None and "no lesson" in out and "use py" not in out
    assert obs.load()["command not found|foobar"].get("lesson_id") == ""


def test_covered_error_records_link_no_nudge(tmp_path, monkeypatch):
    lesson = _lesson("use py not python on windows", trigger_terms=("python",))
    _wire(monkeypatch, tmp_path, lessons=[lesson])
    out = run_tool_hook(_bash("python: command not found", sid="n3"))
    assert out is not None and "use py not python" in out   # lesson injected, not a nudge
    r = obs.load()["command not found|python"]
    assert r["lesson_id"] == lesson.id                      # ledger linked the cover


# --- Step 3: confidence evolution ---

def test_reinforced_saturates_upward():
    c = 0.7
    seq = [c := confidence.reinforced(c) for _ in range(3)]
    assert seq[0] > 0.7 and seq[-1] < confidence.CEILING
    assert all(b > a for a, b in zip([0.7, *seq], seq, strict=False))  # monotonic up
    # MED 0.70 crosses the 0.75 trusted bar within ~2 confirmed recurrences
    assert confidence.reinforced(confidence.reinforced(0.7)) > 0.75


def test_reinforced_never_reaches_one():
    c = 0.5
    for _ in range(100):
        c = confidence.reinforced(c)
    assert c <= confidence.CEILING < 1.0


def test_decayed_moves_toward_neutral_both_sides():
    assert confidence.NEUTRAL < confidence.decayed(0.9) < 0.9
    assert 0.3 < confidence.decayed(0.3) < confidence.NEUTRAL


def test_bumped_reinforces_confidence():
    e = _lesson("x", confidence=0.7, recurrence=1)
    b = e.bumped(last_seen="2026-06-11")
    assert b.recurrence == 2 and b.confidence > 0.7


# --- Step 4: report CLI ---

def test_observations_command_reports(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    for _ in range(3):
        obs.record("ghx", "ghx: command not found")
    res = CliRunner().invoke(cli, ["memory", "observations"])
    assert res.exit_code == 0
    assert "command not found|ghx" in res.output and "×3" in res.output


def test_observations_empty(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path)
    res = CliRunner().invoke(cli, ["memory", "observations"])
    assert res.exit_code == 0 and "no observations" in res.output
