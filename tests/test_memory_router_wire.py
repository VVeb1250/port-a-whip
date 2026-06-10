"""Router ↔ memory wiring — memory injects alongside sets, and fails safe."""

import json

from portaw.adapters import router
from portaw.memory import store
from portaw.memory.schema import MemoryEntry


def _payload(prompt: str) -> str:
    return json.dumps({"prompt": prompt})


def test_memory_block_injects_when_store_has_match(monkeypatch):
    e = MemoryEntry.new("lesson", "forgot await on async call", "global",
                        trigger_terms=("async", "await"), confidence=0.9)
    monkeypatch.setattr(store, "load_lessons", lambda: [e])
    monkeypatch.setattr(store, "load_project", lambda: [])
    out = router.run_hook(_payload("my async function returns a coroutine"))
    assert out and "paw memory" in out and "forgot await" in out


def test_memory_block_safe_on_store_error(monkeypatch):
    def boom():
        raise OSError("disk gone")

    monkeypatch.setattr(store, "load_lessons", boom)
    monkeypatch.setattr(store, "load_project", lambda: [])
    # must not raise; falls back to '' so a set-hit (or None) still flows
    assert router.memory_block("anything at all here") == ""


def test_hook_silent_when_no_sets_and_no_memory(monkeypatch):
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "load_project", lambda: [])
    assert router.run_hook(_payload("the capital of france is paris")) is None


def test_paw_block_is_inner_text_for_external_hook(monkeypatch):
    # kernel-unify: skill-router appends this. No JSON envelope, just the block.
    e = MemoryEntry.new("lesson", "forgot await on async call", "global",
                        trigger_terms=("async", "await"), confidence=0.9)
    monkeypatch.setattr(store, "load_lessons", lambda: [e])
    monkeypatch.setattr(store, "load_project", lambda: [])
    out = router.paw_block("my async function returns a coroutine somehow")
    assert "forgot await" in out and "paw memory" in out
    assert "hookSpecificOutput" not in out  # inner text only, caller wraps


def test_paw_block_silent_on_unrelated_and_short(monkeypatch):
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "load_project", lambda: [])
    assert router.paw_block("the capital of france is paris") == ""
    assert router.paw_block("hi") == ""  # under _MIN_PROMPT_LEN


def test_paw_block_safe_on_store_error(monkeypatch):
    def boom():
        raise OSError("disk gone")

    monkeypatch.setattr(store, "load_lessons", boom)
    monkeypatch.setattr(store, "load_project", lambda: [])
    # must never raise into the external hook
    assert router.paw_block("anything at all goes here for sure") == ""
