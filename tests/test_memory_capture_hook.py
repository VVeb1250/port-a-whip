"""Cross-host capture hook — structured contract + fail-safe (Phase 6, the moat)."""

import json

from portaw.memory import store
from portaw.memory.capture import from_payload, run_capture_hook


def _payload(**lesson):
    return json.dumps({"paw_lesson": lesson, "cwd_name": "paw"})


def test_from_payload_valid():
    sig = from_payload({"paw_lesson": {"trigger": "used python", "fix": "use py", "env": True}})
    assert sig and sig.trigger == "used python" and sig.env_level is True


def test_from_payload_missing_field_returns_none():
    assert from_payload({"paw_lesson": {"trigger": "x"}}) is None  # no fix
    assert from_payload({"other": 1}) is None
    assert from_payload({}) is None


def test_run_capture_hook_stores(monkeypatch, tmp_path):
    saved = {}
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")  # lockfile → tmp
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "save_lessons", lambda e: saved.update(e=e))
    res = run_capture_hook(_payload(trigger="used python", fix="use py", env=True, confidence=0.8))
    assert len(res) == 1 and res[0].stored
    assert saved["e"][0].body == "used python → use py"
    assert saved["e"][0].applicability == "universal"


def test_run_capture_hook_safe_on_garbage():
    assert run_capture_hook("not json at all {{{") == []


def test_run_capture_hook_none_without_paw_lesson():
    assert run_capture_hook(json.dumps({"prompt": "hi"})) == []
