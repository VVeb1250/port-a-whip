"""healthcheck tests — monkeypatch PATH resolution (no real binaries needed)."""

import portaw.sets.healthcheck as hc


def _fake_which(present: set[str]):
    return lambda b: (f"/usr/bin/{b}" if b in present else None)


def test_secure_agent_all_present_passes(monkeypatch):
    monkeypatch.setattr(hc.shutil, "which", _fake_which({"nah", "gitleaks", "osv-scanner", "infisical"}))
    h = hc.check_set("secure-agent")
    assert h.ok
    assert all(t.status == "ok" for t in h.tools)


def test_secure_agent_one_missing_fails_gate(monkeypatch):
    monkeypatch.setattr(hc.shutil, "which", _fake_which({"nah", "gitleaks", "infisical"}))  # no osv-scanner
    h = hc.check_set("secure-agent")
    assert not h.ok
    missing = [t.tool for t in h.tools if t.status == "missing"]
    assert missing == ["osv-scanner"]


def test_context_quality_mcp_without_health_binary_is_config_only(monkeypatch):
    monkeypatch.setattr(hc.shutil, "which", _fake_which(set()))
    h = hc.check_set("context-quality")
    # context7 has no health_binary → config-only, NOT missing → gate still passes
    assert h.ok
    assert h.tools[0].tool == "context7"
    assert h.tools[0].status == "config-only"


def test_efficiency_starter_codegraph_probes_declared_binary(monkeypatch):
    monkeypatch.setattr(hc.shutil, "which", _fake_which({"codegraph", "rtk", "ast-grep"}))
    h = hc.check_set("efficiency-starter")  # default host = claude-code
    by_tool = {t.tool: t for t in h.tools}
    assert by_tool["codegraph"].status == "ok"  # health_binary: codegraph
    assert by_tool["rtk"].status == "ok"
    assert by_tool["ast-grep"].status == "ok"
    assert by_tool["semble"].status == "alt"  # anchored to codex/gemini, not CC
    assert h.ok  # semble absence on CC does NOT fail the gate


def test_efficiency_starter_on_load_all_host_requires_semble_not_codegraph(monkeypatch):
    # codex host: semble is the anchor (must be present), codegraph is the alt
    monkeypatch.setattr(hc.shutil, "which", _fake_which({"semble", "rtk", "ast-grep"}))
    h = hc.check_set("efficiency-starter", host="codex")
    by_tool = {t.tool: t for t in h.tools}
    assert by_tool["semble"].status == "ok"
    assert by_tool["codegraph"].status == "alt"  # CC-anchored → alternate on codex
    assert h.ok  # codegraph absence on codex does NOT fail the gate


def test_efficiency_starter_load_all_host_missing_semble_fails(monkeypatch):
    monkeypatch.setattr(hc.shutil, "which", _fake_which({"codegraph", "rtk"}))  # no semble
    h = hc.check_set("efficiency-starter", host="gemini")
    by_tool = {t.tool: t for t in h.tools}
    assert by_tool["semble"].status == "missing"  # required anchor on gemini, absent
    assert not h.ok


def test_efficiency_starter_missing_codegraph_binary(monkeypatch):
    monkeypatch.setattr(hc.shutil, "which", _fake_which({"rtk"}))
    h = hc.check_set("efficiency-starter")
    by_tool = {t.tool: t for t in h.tools}
    assert by_tool["codegraph"].status == "missing"
    assert not h.ok


def test_non_mcp_skill_null_health_binary_is_config_only(monkeypatch):
    # browser-harness has health_binary: null (skill, no PATH binary). Must NOT
    # crash shutil.which(None); report config-only and pass the gate. Regression
    # for the 2026-06-08 verify crash.
    monkeypatch.setattr(hc.shutil, "which", _fake_which(set()))
    h = hc.check_set("browser-automation")
    by_tool = {t.tool: t for t in h.tools}
    assert by_tool["browser-harness"].status == "config-only"
    assert h.ok  # a skill we cannot PATH-probe never fails the gate


def test_design_quality_skill_tools_do_not_crash(monkeypatch):
    # impeccable (skill, health_binary null) + figtree-cli (real binary). Mixed.
    monkeypatch.setattr(hc.shutil, "which", _fake_which({"figtree"}))
    h = hc.check_set("design-quality")
    by_tool = {t.tool: t for t in h.tools}
    assert by_tool["impeccable"].status == "config-only"  # null binary → no crash
    assert by_tool["figtree-cli"].status == "ok"  # health_binary: figtree on PATH
    assert h.ok
