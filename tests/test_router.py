"""Router adapter tests — registry routing, hook I/O, settings wiring (tmp only)."""

import json

import pytest

import portaw.adapters.router as r
from portaw.kernel.registry import build_capabilities, build_intent_map

# ---- registry ----

def test_registry_builds_one_capability_per_set():
    caps = build_capabilities()
    names = {c.name for c in caps}
    assert {"efficiency-starter", "secure-agent", "context-quality"} <= names
    assert all(c.ctype == "set" and c.invoke.startswith("portaw install") for c in caps)


def test_intent_map_from_trigger_terms_skips_short():
    imap = build_intent_map()
    assert "vulnerability" in imap and "secure-agent" in imap["vulnerability"]
    assert all(len(k) >= 4 for k in imap)  # "cve", "api" filtered


# ---- route_prompt (real registry) ----

def test_route_prompt_secret_hits_secure_agent():
    hits = r.route_prompt("scan staged diff for leaked secret credentials")
    assert hits and hits[0].cap.name == "secure-agent"


def test_route_prompt_silent_on_unrelated():
    assert r.route_prompt("what time is it in tokyo") == []


# ---- hook I/O ----

def test_run_hook_emits_additional_context():
    payload = json.dumps({"prompt": "find all callers of this function in the codebase"})
    out = r.run_hook(stdin_text=payload)
    assert out is not None
    parsed = json.loads(out)
    assert parsed["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "paw router" in parsed["hookSpecificOutput"]["additionalContext"]


def test_run_hook_emits_host_specific_event_for_gemini():
    payload = json.dumps({"prompt": "find all callers of this function in the codebase"})
    out = r.run_hook(stdin_text=payload, host="gemini")
    assert json.loads(out)["hookSpecificOutput"]["hookEventName"] == "BeforeAgent"


def test_default_command_threads_host_except_claude_code():
    assert r.default_command("claude-code") == "portaw router run"
    assert r.default_command("codex") == "portaw router run --host codex"
    assert r.default_command("gemini") == "portaw router run --host gemini"


def test_run_hook_silent_on_short_prompt():
    assert r.run_hook(stdin_text=json.dumps({"prompt": "hi"})) is None


def test_run_hook_silent_on_slash_command():
    assert r.run_hook(stdin_text=json.dumps({"prompt": "/install something here"})) is None


def test_run_hook_tolerates_garbage_stdin():
    assert r.run_hook(stdin_text="not json at all {{{") is None


# ---- install-aware routing + session dedup (#5/#6) ----

def test_format_context_switches_installed_set_to_usage_pointer():
    hits = r.route_prompt("scan staged diff for leaked secret credentials")
    assert hits and hits[0].cap.name == "secure-agent"
    out = r.format_context(hits, installed={"secure-agent": ["gitleaks"]})
    assert "installed ✓" in out and "gitleaks" in out
    assert "portaw install secure-agent" not in out
    # not installed → install pointer unchanged
    out2 = r.format_context(hits, installed={})
    assert "portaw install secure-agent" in out2


def test_run_hook_uses_state_ledger_for_installed(monkeypatch):
    import portaw.sets.state as state_mod

    monkeypatch.setattr(state_mod, "installed_sets",
                        lambda host: {"secure-agent": {"tools": {"gitleaks": {}}}})
    payload = json.dumps({"prompt": "scan staged diff for leaked secret credentials"})
    out = r.run_hook(stdin_text=payload)
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "installed ✓" in ctx and "portaw install secure-agent" not in ctx


def test_run_hook_dedups_set_suggestion_within_session(tmp_path, monkeypatch):
    import portaw.memory.sessionlog as sessionlog

    monkeypatch.setattr(sessionlog, "_dir", lambda: tmp_path / "session")
    payload = json.dumps({"prompt": "scan staged diff for leaked secret credentials",
                          "session_id": "dedup1"})
    out1 = r.run_hook(stdin_text=payload)
    assert out1 is not None and "secure-agent" in out1
    assert r.run_hook(stdin_text=payload) is None    # same session → silent
    # a different session still gets the suggestion
    other = json.dumps({"prompt": "scan staged diff for leaked secret credentials",
                        "session_id": "dedup2"})
    assert r.run_hook(stdin_text=other) is not None


# ---- enable / disable / status: JSON hosts (CC, Gemini) ----

@pytest.fixture
def tmp_cc(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setitem(r._WIRING, "claude-code", r.Wiring(path, "json", "UserPromptSubmit"))
    return path


@pytest.fixture
def tmp_gemini(tmp_path, monkeypatch):
    path = tmp_path / "gemini-settings.json"
    monkeypatch.setitem(r._WIRING, "gemini", r.Wiring(path, "json", "BeforeAgent"))
    return path


@pytest.fixture
def tmp_codex(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    monkeypatch.setitem(r._WIRING, "codex", r.Wiring(path, "toml", "UserPromptSubmit"))
    return path


def test_enable_creates_hook_and_is_idempotent(tmp_cc):
    changed, backup = r.enable("claude-code")
    assert changed and backup is None  # fresh file
    data = json.loads(tmp_cc.read_text())
    cmds = [h["command"] for b in data["hooks"]["UserPromptSubmit"] for h in b["hooks"]]
    assert "portaw router run" in cmds
    # second enable = no-op
    changed2, _ = r.enable("claude-code")
    assert changed2 is False


def test_enable_preserves_existing_settings_and_backs_up(tmp_cc):
    tmp_cc.write_text(json.dumps({"theme": "dark", "hooks": {"UserPromptSubmit": [
        {"hooks": [{"type": "command", "command": "other-hook"}]}
    ]}}))
    changed, backup = r.enable("claude-code")
    assert changed and backup is not None and backup.exists()
    data = json.loads(tmp_cc.read_text())
    assert data["theme"] == "dark"
    cmds = [h["command"] for b in data["hooks"]["UserPromptSubmit"] for h in b["hooks"]]
    assert "other-hook" in cmds and "portaw router run" in cmds


def test_status_reflects_wiring(tmp_cc):
    assert r.status("claude-code")["wired"] is False
    r.enable("claude-code")
    assert r.status("claude-code")["wired"] is True


def test_disable_removes_only_router_block(tmp_cc):
    tmp_cc.write_text(json.dumps({"hooks": {"UserPromptSubmit": [
        {"hooks": [{"type": "command", "command": "keep-me"}]}
    ]}}))
    r.enable("claude-code")
    assert r.disable("claude-code") is True
    data = json.loads(tmp_cc.read_text())
    cmds = [h["command"] for b in data["hooks"]["UserPromptSubmit"] for h in b["hooks"]]
    assert cmds == ["keep-me"]


def test_disable_drops_empty_event_key_json(tmp_cc):
    """Parity with the TOML path: last router block gone → no empty event list left."""
    r.enable("claude-code")
    assert r.disable("claude-code") is True
    data = json.loads(tmp_cc.read_text())
    assert "hooks" not in data  # only block was ours → whole key dropped


def test_gemini_enable_uses_beforeagent_event_and_host_command(tmp_gemini):
    changed, _ = r.enable("gemini")
    assert changed
    data = json.loads(tmp_gemini.read_text())
    assert "UserPromptSubmit" not in data["hooks"]  # gemini = BeforeAgent only
    cmds = [h["command"] for b in data["hooks"]["BeforeAgent"] for h in b["hooks"]]
    assert cmds == ["portaw router run --host gemini"]
    assert r.status("gemini")["event"] == "BeforeAgent"
    assert r.enable("gemini")[0] is False  # idempotent


# ---- enable / disable / status: TOML host (Codex) ----

# Mirrors the user's real ~/.codex/config.toml shape so the merge is exercised
# against neighbours it must preserve (advisor #2).
_REAL_CODEX = '''#:schema https://developers.openai.com/codex/config-schema.json
approval_policy = "on-request"
web_search = "live"

notify = ["terminal-notifier", "-title", "Codex ECC"]

persistent_instructions = "Follow AGENTS.md"

[mcp_servers.codegraph]
command = "codegraph"
args = ["serve", "--mcp"]
'''


def test_codex_enable_writes_array_of_tables_and_preserves_neighbours(tmp_codex):
    import tomllib
    tmp_codex.write_text(_REAL_CODEX, encoding="utf-8")
    changed, backup = r.enable("codex")
    assert changed and backup is not None and backup.exists()
    doc = tomllib.loads(tmp_codex.read_text(encoding="utf-8"))  # round-trips
    # neighbours survive
    assert doc["notify"] == ["terminal-notifier", "-title", "Codex ECC"]
    assert doc["persistent_instructions"] == "Follow AGENTS.md"
    assert doc["mcp_servers"]["codegraph"]["command"] == "codegraph"
    # hook wired with windows override
    entry = doc["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert entry["type"] == "command"
    assert entry["command"] == "portaw router run --host codex"
    assert entry["command_windows"] == "portaw router run --host codex"


def test_codex_enable_idempotent_and_status(tmp_codex):
    tmp_codex.write_text(_REAL_CODEX, encoding="utf-8")
    r.enable("codex")
    assert r.status("codex") == {
        "host": "codex", "event": "UserPromptSubmit", "wired": True, "exists": True,
        "settings": str(tmp_codex),
    }
    assert r.enable("codex")[0] is False  # second enable = no-op


def test_codex_enable_on_fresh_file(tmp_codex):
    import tomllib
    changed, backup = r.enable("codex")
    assert changed and backup is None  # created fresh
    doc = tomllib.loads(tmp_codex.read_text(encoding="utf-8"))
    assert doc["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"].endswith("--host codex")


def test_codex_disable_removes_only_router_keeps_neighbour_block(tmp_codex):
    import tomllib
    # pre-existing non-router hook block must survive disable
    seed = _REAL_CODEX + '''
[[hooks.UserPromptSubmit]]
[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "keep-me-audit"
'''
    tmp_codex.write_text(seed, encoding="utf-8")
    r.enable("codex")
    assert r.disable("codex") is True
    doc = tomllib.loads(tmp_codex.read_text(encoding="utf-8"))
    cmds = [h["command"] for b in doc["hooks"]["UserPromptSubmit"] for h in b["hooks"]]
    assert cmds == ["keep-me-audit"]  # router block gone, neighbour kept
    assert doc["mcp_servers"]["codegraph"]["command"] == "codegraph"


def test_codex_disable_drops_empty_event_table(tmp_codex):
    import tomllib
    tmp_codex.write_text(_REAL_CODEX, encoding="utf-8")
    r.enable("codex")
    assert r.disable("codex") is True
    doc = tomllib.loads(tmp_codex.read_text(encoding="utf-8"))
    assert "hooks" not in doc  # only block was ours → whole table dropped
    assert doc["notify"]  # neighbours still intact


def test_enable_rejects_unknown_host():
    with pytest.raises(ValueError, match="unsupported"):
        r.enable("aider")  # type: ignore[arg-type]
