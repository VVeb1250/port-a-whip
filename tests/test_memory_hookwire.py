"""Capture-hook wiring (Stop event) — isolated to a tmp settings.json."""

import json

from portaw.adapters import router
from portaw.adapters.router import Wiring
from portaw.memory import hookwire


def _redirect(monkeypatch, tmp_path):
    p = tmp_path / "settings.json"
    # router table event is UserPromptSubmit; hookwire overrides it to Stop.
    monkeypatch.setitem(router._WIRING, "claude-code", Wiring(p, "json", "UserPromptSubmit"))
    return p


def test_enable_capture_wires_stop_event(monkeypatch, tmp_path):
    p = _redirect(monkeypatch, tmp_path)
    changed, _ = hookwire.enable_capture("claude-code")
    assert changed
    settings = json.loads(p.read_text(encoding="utf-8"))
    cmds = [
        h["command"]
        for b in settings["hooks"]["Stop"] for h in b["hooks"]
    ]
    assert any("portaw memory capture-hook" in c for c in cmds)


def test_enable_capture_idempotent(monkeypatch, tmp_path):
    _redirect(monkeypatch, tmp_path)
    assert hookwire.enable_capture("claude-code")[0] is True
    assert hookwire.enable_capture("claude-code")[0] is False  # already wired


def test_status_and_disable(monkeypatch, tmp_path):
    _redirect(monkeypatch, tmp_path)
    hookwire.enable_capture("claude-code")
    assert hookwire.capture_status("claude-code")["wired"] is True
    assert hookwire.disable_capture("claude-code") is True
    assert hookwire.capture_status("claude-code")["wired"] is False


def test_capture_hook_coexists_with_router_hook(monkeypatch, tmp_path):
    p = _redirect(monkeypatch, tmp_path)
    # router on UserPromptSubmit, capture on Stop — same file, neither clobbers
    router.enable("claude-code")
    hookwire.enable_capture("claude-code")
    settings = json.loads(p.read_text(encoding="utf-8"))
    assert "UserPromptSubmit" in settings["hooks"] and "Stop" in settings["hooks"]
    router_cmds = [h["command"] for b in settings["hooks"]["UserPromptSubmit"] for h in b["hooks"]]
    stop_cmds = [h["command"] for b in settings["hooks"]["Stop"] for h in b["hooks"]]
    assert any("router run" in c for c in router_cmds)
    assert any("memory capture-hook" in c for c in stop_cmds)
