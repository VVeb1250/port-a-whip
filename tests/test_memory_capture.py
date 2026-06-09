"""Capture + integrity-gate tests — pure, store isolated via monkeypatch."""

from portaw.memory import store
from portaw.memory.capture import (
    FailureSignal,
    capture,
    classify_text,
    infer_applicability,
    to_lesson,
)
from portaw.memory.gate import GateConfig, accepts, enters_hot
from portaw.memory.schema import MemoryEntry

TODAY = "2026-06-10"


# --- gate ---

def test_project_write_needs_confirm():
    e = MemoryEntry.new("project", "decision", "project", applicability="project:paw")
    assert not accepts(e, confirmed=False).ok
    assert accepts(e, confirmed=True).ok


def test_universal_lesson_needs_high_confidence_or_recurrence():
    weak = MemoryEntry.new("lesson", "x", "global", applicability="universal",
                           confidence=0.5, recurrence=1)
    assert not accepts(weak).ok
    strong_conf = MemoryEntry.new("lesson", "y", "global", applicability="universal",
                                  confidence=0.8, recurrence=1)
    assert accepts(strong_conf).ok
    recurred = MemoryEntry.new("lesson", "z", "global", applicability="universal",
                               confidence=0.5, recurrence=2)
    assert accepts(recurred).ok


def test_stack_lesson_accepted_without_universal_bar():
    e = MemoryEntry.new("lesson", "x", "global", applicability="stack:django",
                        confidence=0.5)
    assert accepts(e).ok


def test_enters_hot_threshold():
    cfg = GateConfig(hot_confidence=0.6)
    assert enters_hot(MemoryEntry.new("lesson", "a", "global", confidence=0.7), cfg)
    assert not enters_hot(MemoryEntry.new("lesson", "b", "global", confidence=0.3), cfg)
    assert enters_hot(MemoryEntry.new("lesson", "c", "global", confidence=0.1, pinned=True), cfg)


# --- classify / applicability ---

def test_classify_detects_env_and_stack():
    env, stack = classify_text("running python on windows path failed")
    assert env and stack == ""
    env2, stack2 = classify_text("django migration conflict in models")
    assert stack2 == "django"


def test_infer_applicability_env_is_universal():
    sig = FailureSignal(trigger="used python on windows", fix="use py")
    assert infer_applicability(sig, "paw") == "universal"


def test_infer_applicability_framework_is_stack():
    sig = FailureSignal(trigger="django migration ordering", fix="add dependency")
    assert infer_applicability(sig, "paw") == "stack:django"


def test_infer_applicability_default_is_project():
    sig = FailureSignal(trigger="this repo auth flow quirk", fix="call refresh first")
    assert infer_applicability(sig, "paw") == "project:paw"


def test_explicit_stack_overrides_keyword_guess():
    sig = FailureSignal(trigger="generic thing", fix="do x", stack="rust")
    assert infer_applicability(sig, "paw") == "stack:rust"


# --- to_lesson ---

def test_to_lesson_builds_compressed_body_and_anchors():
    sig = FailureSignal(trigger="forgot await", fix="add await", symbols=("fetch",),
                        confidence=0.6)
    e = to_lesson(sig, "paw", TODAY)
    assert e.body == "forgot await → add await"
    assert e.type == "lesson" and e.scope == "global"
    assert e.anchors.symbols == ("fetch",) and e.source == "hook"


# --- capture (store isolated) ---

def test_capture_stores_accepted_lesson(monkeypatch):
    saved = {}
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "save_lessons", lambda entries: saved.update(e=entries))
    sig = FailureSignal(trigger="used python", fix="use py", env_level=True, confidence=0.8)
    res = capture(sig, "paw", today=TODAY)
    assert res.stored and res.verdict.ok
    assert saved["e"][0].body == "used python → use py"


def test_capture_rejects_weak_universal_without_storing(monkeypatch):
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "save_lessons",
                        lambda entries: (_ for _ in ()).throw(AssertionError("must not save")))
    sig = FailureSignal(trigger="used python", fix="use py", env_level=True, confidence=0.4)
    res = capture(sig, "paw", today=TODAY)
    assert not res.stored and not res.verdict.ok
