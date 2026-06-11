"""install_set / remove_set integration on a tmp host config (monkeypatched)."""

import json

import pytest

import portaw.sets.install as install_mod
import portaw.sets.state as state_mod
from portaw.config import HostConfig


@pytest.fixture(autouse=True)
def tmp_state(tmp_path, monkeypatch):
    """Every test gets an isolated state.json — never the real ~/.paw ledger."""
    monkeypatch.setattr(state_mod, "state_path", lambda: tmp_path / "state.json")


@pytest.fixture
def tmp_host(tmp_path, monkeypatch):
    """Redirect host_config to a tmp claude.json so real config is never touched."""
    hc = HostConfig("claude-code", tmp_path / "claude.json", "json", ("mcpServers",))
    monkeypatch.setattr(install_mod, "host_config", lambda hid: hc)
    return hc


def test_install_context_quality_patches_one_mcp(tmp_host):
    res = install_mod.install_set("context-quality", "claude-code")
    assert [t for t, _ in res.patched] == ["context7"]
    assert res.skipped == []
    assert res.mcp_count_after == 1
    assert res.ceiling_warning is None
    data = json.loads(tmp_host.path.read_text())
    assert data["mcpServers"]["context7"]["command"] == "npx"


def test_install_is_idempotent_second_run_skips(tmp_host):
    install_mod.install_set("context-quality", "claude-code")
    res2 = install_mod.install_set("context-quality", "claude-code")
    assert res2.patched == []
    assert res2.skipped == ["context7"]


def test_install_force_repatches(tmp_host):
    install_mod.install_set("context-quality", "claude-code")
    res = install_mod.install_set("context-quality", "claude-code", force=True)
    assert [t for t, _ in res.patched] == ["context7"]


def test_install_secure_agent_zero_mcp_all_manual_shim(tmp_host):
    res = install_mod.install_set("secure-agent", "claude-code")
    assert res.patched == [] and res.skipped == []
    # 4 non-MCP tools, each with >=1 install step → shim steps present
    tools = {s.tool for s in res.shim_steps}
    assert tools == {"nah", "gitleaks", "osv-scanner", "infisical"}
    assert res.mcp_count_after == 0
    assert not tmp_host.path.exists()  # nothing patched → no config written


def test_install_preserves_user_other_servers(tmp_host):
    tmp_host.path.write_text(json.dumps({"mcpServers": {"mine": {"command": "x"}}, "theme": "dark"}))
    install_mod.install_set("context-quality", "claude-code")
    data = json.loads(tmp_host.path.read_text())
    assert data["theme"] == "dark"
    assert data["mcpServers"]["mine"] == {"command": "x"}
    assert "context7" in data["mcpServers"]


def test_remove_unpatches_mcp(tmp_host):
    install_mod.install_set("context-quality", "claude-code")
    res = install_mod.remove_set("context-quality", "claude-code")
    assert [t for t, _ in res.removed] == ["context7"]
    data = json.loads(tmp_host.path.read_text())
    assert "context7" not in data["mcpServers"]


def test_install_efficiency_starter_cc_installs_codegraph_skips_semble_alt(tmp_host):
    res = install_mod.install_set("efficiency-starter", "claude-code")
    patched = [t for t, _ in res.patched]
    assert "codegraph" in patched          # CC anchor
    assert "semble" not in patched         # semble anchored to codex/gemini
    assert "semble" in res.alt_skipped     # reported, not silently dropped
    data = json.loads(tmp_host.path.read_text())
    assert "semble" not in data["mcpServers"]  # NOT written to CC config


def test_install_efficiency_starter_codex_installs_semble_skips_codegraph(tmp_path, monkeypatch):
    hc = HostConfig("codex", tmp_path / "config.toml", "toml", ("mcp_servers",))
    monkeypatch.setattr(install_mod, "host_config", lambda hid: hc)
    res = install_mod.install_set("efficiency-starter", "codex")
    patched = [t for t, _ in res.patched]
    assert "semble" in patched             # load-all-host anchor
    assert "codegraph" not in patched      # CC-anchored → alt on codex
    assert "codegraph" in res.alt_skipped
    import tomllib
    doc = tomllib.loads(hc.path.read_text(encoding="utf-8"))
    assert "semble" in doc["mcp_servers"]
    assert "codegraph" not in doc["mcp_servers"]


def test_remove_skips_tool_anchored_to_other_host(tmp_host):
    """semble is anchored to codex/gemini — if the user put it in their CC config
    themselves, removing efficiency-starter on CC must NOT delete it (paw never
    installed it here; symmetric with install_set's alt_skipped)."""
    install_mod.install_set("efficiency-starter", "claude-code")
    data = json.loads(tmp_host.path.read_text())
    data["mcpServers"]["semble"] = {"command": "semble", "args": ["mcp"]}  # user's own
    tmp_host.path.write_text(json.dumps(data))

    res = install_mod.remove_set("efficiency-starter", "claude-code")
    removed = [t for t, _ in res.removed]
    assert "codegraph" in removed and "semble" not in removed
    after = json.loads(tmp_host.path.read_text())
    assert "semble" in after["mcpServers"]  # user's manual install survives


def test_resolve_host_rejects_unknown():
    with pytest.raises(ValueError, match="unknown host"):
        install_mod.resolve_host("emacs")


# --- install-state ledger + drift detection (#2) ---

def test_install_records_state_and_remove_clears_it(tmp_host):
    install_mod.install_set("context-quality", "claude-code")
    managed = state_mod.managed_tools("claude-code")
    assert "context7" in managed
    assert managed["context7"]["set"] == "context-quality"
    assert managed["context7"]["entry"]["command"] == "npx"

    install_mod.remove_set("context-quality", "claude-code")
    assert state_mod.managed_tools("claude-code") == {}
    assert state_mod.installed_sets("claude-code") == {}


def test_skipped_already_present_does_not_claim_ownership(tmp_host):
    """A server the USER already had must not enter paw's ledger."""
    tmp_host.path.write_text(json.dumps({"mcpServers": {"context7": {"command": "user-own"}}}))
    res = install_mod.install_set("context-quality", "claude-code")
    assert res.skipped == ["context7"]
    assert state_mod.managed_tools("claude-code") == {}


def test_check_drift_reports_orphan_and_drift(tmp_host):
    from portaw.sets.patcher import get_entry

    install_mod.install_set("context-quality", "claude-code")
    live = lambda t: get_entry(tmp_host, t)  # noqa: E731
    assert state_mod.check_drift("claude-code", live) == []  # fresh install = clean

    # user tunes the entry outside paw → drift
    data = json.loads(tmp_host.path.read_text())
    data["mcpServers"]["context7"]["env"] = {"TUNED": "1"}
    tmp_host.path.write_text(json.dumps(data))
    findings = state_mod.check_drift("claude-code", live)
    assert [(t, k) for t, k, _ in findings] == [("context7", "drift")]

    # user deletes the entry outside paw → orphaned record
    data["mcpServers"].pop("context7")
    tmp_host.path.write_text(json.dumps(data))
    findings = state_mod.check_drift("claude-code", live)
    assert [(t, k) for t, k, _ in findings] == [("context7", "orphaned")]


def test_state_load_tolerates_garbage(tmp_path, monkeypatch):
    monkeypatch.setattr(state_mod, "state_path", lambda: tmp_path / "garbage.json")
    (tmp_path / "garbage.json").write_text("{ not json", encoding="utf-8")
    assert state_mod.load_state() == {}
    state_mod.record_install("claude-code", "s", {"t": {"command": "c"}})  # recovers
    assert "t" in state_mod.managed_tools("claude-code")
