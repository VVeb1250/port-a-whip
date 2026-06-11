"""Live-inject surface tests (P0–P3, 2026-06-11).

P0: live memory_block gets ctx + dedup (stack lessons can fire, no re-inject).
P1: SessionStart pinned tier — once per session, compact resets, eligibility holds.
P2: PostToolUse Bash — fires ONLY on a failed result, routes on the error text.
P3: PostToolUse Edit — anchor recall on the touched file, session-deduped.
"""

import json

import portaw.memory.sessionlog as sessionlog
import portaw.memory.store as store
from portaw.adapters import router
from portaw.adapters.memory_hooks import run_session_hook, run_tool_hook
from portaw.kernel import embed
from portaw.kernel.ranking import Capability
from portaw.memory.context import detect_stacks
from portaw.memory.inject import session_select
from portaw.memory.retrieval import RetrievalContext
from portaw.memory.schema import Anchors, MemoryEntry


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    kw.setdefault("confidence", 0.9)
    kw.setdefault("last_seen", "2026-06-10")
    return MemoryEntry.new("lesson", body, **kw)


def _wire(monkeypatch, tmp_path, lessons, project=()):
    """Point store + session log at tmp, return the session dir."""
    monkeypatch.setattr(store, "load_lessons", lambda: list(lessons))
    monkeypatch.setattr(store, "load_project", lambda root=None: list(project))
    monkeypatch.setattr(sessionlog, "_dir", lambda: tmp_path / "session")


# --- context detection ---

def test_detect_stacks_markers(tmp_path):
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "package.json").touch()
    assert detect_stacks(tmp_path) == frozenset({"python", "typescript"})
    assert detect_stacks(tmp_path / "nope") == frozenset()


# --- session log ---

def test_sessionlog_mark_seen_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(sessionlog, "_dir", lambda: tmp_path / "session")
    assert sessionlog.seen("s1") == set()
    sessionlog.mark("s1", ["a", "b"])
    sessionlog.mark("s1", ["c"])
    assert sessionlog.seen("s1") == {"a", "b", "c"}
    sessionlog.reset("s1")
    assert sessionlog.seen("s1") == set()


# --- P1: session_select + run_session_hook ---

def test_session_select_pinned_only_and_eligible():
    pin = _lesson("pinned env rule", pinned=True)
    pin_other_stack = _lesson("django pin", pinned=True, applicability="stack:django")
    loud = _lesson("unpinned but high conf", recurrence=30)
    out = session_select([pin, pin_other_stack, loud], ctx=RetrievalContext())
    assert [e.body for e in out] == ["pinned env rule"]  # unpinned + ineligible stay out


def test_session_hook_injects_once_then_dedups(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path, [_lesson("use py not python", pinned=True)])
    payload = json.dumps({"session_id": "sA", "cwd": str(tmp_path), "source": "startup"})
    out1 = run_session_hook(payload)
    assert out1 is not None and "use py not python" in out1
    assert json.loads(out1)["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert run_session_hook(payload) is None          # same session → silent


def test_session_hook_compact_resets_and_refires(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path, [_lesson("use py not python", pinned=True)])
    start = json.dumps({"session_id": "sB", "cwd": str(tmp_path), "source": "startup"})
    compact = json.dumps({"session_id": "sB", "cwd": str(tmp_path), "source": "compact"})
    assert run_session_hook(start) is not None
    assert run_session_hook(compact) is not None      # post-compact pins re-fire


def test_session_hook_silent_with_no_pins(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path, [_lesson("not pinned")])
    assert run_session_hook(json.dumps({"session_id": "sC"})) is None


# --- P2: Bash failure recall ---

def _bash_payload(stderr, sid="t1", stdout=""):
    return json.dumps({
        "session_id": sid, "tool_name": "Bash",
        "tool_input": {"command": "python x.py"},
        "tool_response": {"stdout": stdout, "stderr": stderr},
    })


def test_tool_hook_bash_failure_injects_matching_lesson(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path,
          [_lesson("use py not python on windows", trigger_terms=("python",))])
    out = run_tool_hook(_bash_payload("bash: python: command not found"))
    assert out is not None and "use py not python" in out
    assert json.loads(out)["hookSpecificOutput"]["hookEventName"] == "PostToolUse"


def test_tool_hook_bash_success_is_silent(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path,
          [_lesson("use py not python on windows", trigger_terms=("python",))])
    assert run_tool_hook(_bash_payload("", stdout="python output fine")) is None


def test_tool_hook_bash_plain_warning_is_silent(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path,
          [_lesson("use py not python on windows", trigger_terms=("python",))])
    # stderr text without a failure marker → precision gate keeps quiet
    assert run_tool_hook(_bash_payload("python will be slow today")) is None


def test_tool_hook_output_about_errors_is_silent(tmp_path, monkeypatch):
    """Output that TALKS about errors is not a failure: '0 ERRORS' summaries and
    'cannot guarantee' prose used to fire the old broad markers."""
    _wire(monkeypatch, tmp_path,
          [_lesson("use py not python on windows", trigger_terms=("python",))])
    assert run_tool_hook(_bash_payload("python lint passed: found 0 ERRORS")) is None
    assert run_tool_hook(_bash_payload("python cannot guarantee ordering here")) is None


def test_tool_hook_permission_denied_still_fires(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path,
          [_lesson("use py not python on windows", trigger_terms=("python",))])
    out = run_tool_hook(_bash_payload("python: Permission denied", sid="tperm"))
    assert out is not None


def test_tool_hook_dedups_within_session(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path,
          [_lesson("use py not python on windows", trigger_terms=("python",))])
    p = _bash_payload("bash: python: command not found", sid="t2")
    assert run_tool_hook(p) is not None
    assert run_tool_hook(p) is None                   # same session → once only


# --- P3: edit anchor recall ---

def test_tool_hook_edit_anchor_recall(tmp_path, monkeypatch):
    entry = _lesson("never hand-edit generated store files",
                    anchors=Anchors(paths=("portaw/memory/store.py",)))
    _wire(monkeypatch, tmp_path, [entry])
    payload = json.dumps({
        "session_id": "t3", "tool_name": "Edit",
        "tool_input": {"file_path": "C:\\repo\\portaw\\memory\\store.py"},
        "tool_response": {},
    })
    out = run_tool_hook(payload)
    assert out is not None and "never hand-edit" in out


def test_tool_hook_edit_unrelated_file_silent(tmp_path, monkeypatch):
    entry = _lesson("never hand-edit generated store files",
                    anchors=Anchors(paths=("portaw/memory/store.py",)))
    _wire(monkeypatch, tmp_path, [entry])
    payload = json.dumps({
        "session_id": "t4", "tool_name": "Edit",
        "tool_input": {"file_path": "C:\\repo\\other.py"}, "tool_response": {},
    })
    assert run_tool_hook(payload) is None


def test_tool_hook_pinned_does_not_ride_every_tool_call(tmp_path, monkeypatch):
    # pinned bypasses the recall floor, but the tool surface only injects
    # entries with real evidence (base > 0) — pins belong to SessionStart.
    _wire(monkeypatch, tmp_path, [_lesson("pinned rule", pinned=True)])
    payload = json.dumps({
        "session_id": "t5", "tool_name": "Edit",
        "tool_input": {"file_path": "C:\\repo\\x.py"}, "tool_response": {},
    })
    assert run_tool_hook(payload) is None


# --- P0: live memory_block context + dedup ---

def test_memory_block_stack_lesson_fires_with_cwd_marker(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").touch()
    _wire(monkeypatch, tmp_path,
          [_lesson("forgot await on async call", applicability="stack:python",
                   trigger_terms=("async", "await"))])
    out = router.memory_block("my async call returns a coroutine", str(tmp_path), "m1")
    assert "forgot await" in out
    # same session asks again → already in context → silent
    assert router.memory_block("my async call returns a coroutine", str(tmp_path), "m1") == ""


def test_memory_block_stack_lesson_ineligible_without_marker(tmp_path, monkeypatch):
    _wire(monkeypatch, tmp_path,
          [_lesson("forgot await on async call", applicability="stack:python",
                   trigger_terms=("async", "await"))])
    out = router.memory_block("my async call returns a coroutine", str(tmp_path), "m2")
    assert out == ""


def test_memory_block_without_session_id_keeps_pins_quiet(tmp_path, monkeypatch):
    # stale skill-router copy passes no session_id → no dedup log → a pin must
    # NOT ride every prompt; evidence-based hits still inject.
    pin = _lesson("pinned env rule", pinned=True)
    rel = _lesson("forgot await on async call", trigger_terms=("async", "await"))
    _wire(monkeypatch, tmp_path, [pin, rel])
    out = router.memory_block("my async call returns a coroutine", str(tmp_path), "")
    assert "forgot await" in out and "pinned env rule" not in out


# --- embed lazy wrapper ---

def test_lazy_embedder_unavailable_returns_empty(tmp_path):
    fn = embed.lazy_embedder(tmp_path / "no-model")
    assert fn("hi", [Capability(name="a", text="b", ctype="set")]) == {}


# --- wiring: PostToolUse block carries the matcher ---

def test_enable_inject_tool_writes_matcher(tmp_path, monkeypatch):
    from portaw.memory.hookwire import enable_inject

    settings = tmp_path / "settings.json"
    monkeypatch.setitem(router._WIRING, "claude-code",
                        router.Wiring(settings, "json", "UserPromptSubmit"))
    changed, _ = enable_inject("tool", "claude-code")
    assert changed is True
    cfg = json.loads(settings.read_text(encoding="utf-8"))
    block = cfg["hooks"]["PostToolUse"][0]
    assert block["matcher"] == "Bash|Edit|Write|MultiEdit|NotebookEdit"
    assert "portaw memory tool-hook" in block["hooks"][0]["command"]
    # idempotent
    assert enable_inject("tool", "claude-code")[0] is False


def test_enable_inject_rejects_non_cc_host():
    import pytest
    from portaw.memory.hookwire import enable_inject

    with pytest.raises(ValueError):
        enable_inject("session", "codex")
