"""Patcher tests — pure merges + file round-trips on tmp paths (never real config)."""

import json

import pytest
import tomllib

from portaw.config import HostConfig
from portaw.sets.patcher import (
    PatchError,
    build_entry,
    has_json,
    has_toml,
    is_installed,
    merge_json,
    merge_toml,
    patch_host,
    remove_json,
    remove_toml,
    unpatch_host,
)

_ENTRY = {"command": "npx", "args": ["-y", "@upstash/context7-mcp"], "env": {}}
_KEY = ("mcpServers",)


# ---- build_entry ----

def test_build_entry_extracts_command_args_drops_empty_env():
    tool = {"tool": "context7", "mcp_config": {"command": "npx", "args": ["-y", "x"], "env": {}}}
    e = build_entry(tool)
    assert e == {"command": "npx", "args": ["-y", "x"]}


def test_build_entry_keeps_nonempty_env():
    tool = {"tool": "t", "mcp_config": {"command": "c", "args": [], "env": {"K": "v"}}}
    assert build_entry(tool)["env"] == {"K": "v"}


def test_build_entry_missing_command_raises():
    with pytest.raises(PatchError, match="no mcp_config.command"):
        build_entry({"tool": "t", "mcp_config": {"args": []}})


# ---- JSON pure ----

def test_merge_json_preserves_other_servers_and_is_immutable():
    original = {"mcpServers": {"existing": {"command": "old"}}, "other": 1}
    out = merge_json(original, _KEY, "context7", _ENTRY)
    assert out["mcpServers"]["existing"] == {"command": "old"}  # untouched
    assert out["mcpServers"]["context7"] == _ENTRY
    assert out["other"] == 1
    assert "context7" not in original["mcpServers"]  # input not mutated


def test_merge_json_creates_parent_when_absent():
    out = merge_json({}, _KEY, "context7", _ENTRY)
    assert out["mcpServers"]["context7"] == _ENTRY


def test_remove_json_is_noop_when_absent():
    cfg = {"mcpServers": {"a": {}}}
    assert remove_json(cfg, _KEY, "missing") == cfg


def test_remove_json_deletes_target_only():
    cfg = {"mcpServers": {"a": {"command": "x"}, "b": {"command": "y"}}}
    out = remove_json(cfg, _KEY, "a")
    assert "a" not in out["mcpServers"]
    assert out["mcpServers"]["b"] == {"command": "y"}


def test_has_json():
    cfg = {"mcpServers": {"a": {}}}
    assert has_json(cfg, _KEY, "a")
    assert not has_json(cfg, _KEY, "z")
    assert not has_json({}, _KEY, "a")


# ---- TOML pure (Codex [mcp_servers.<name>]) ----

def test_merge_toml_creates_nested_table_and_validates():
    out = merge_toml("", "codegraph", {"command": "npx", "args": ["-y", "cg"]})
    parsed = tomllib.loads(out)
    assert parsed["mcp_servers"]["codegraph"]["command"] == "npx"
    assert parsed["mcp_servers"]["codegraph"]["args"] == ["-y", "cg"]


def test_merge_toml_preserves_existing_server():
    base = 'foo = 1\n[mcp_servers.keep]\ncommand = "k"\nargs = []\n'
    out = merge_toml(base, "new", {"command": "n", "args": []})
    parsed = tomllib.loads(out)
    assert parsed["foo"] == 1
    assert parsed["mcp_servers"]["keep"]["command"] == "k"
    assert parsed["mcp_servers"]["new"]["command"] == "n"


def test_merge_toml_writes_env_subtable():
    out = merge_toml("", "t", {"command": "c", "args": [], "env": {"API": "x"}})
    assert tomllib.loads(out)["mcp_servers"]["t"]["env"] == {"API": "x"}


def test_remove_toml_and_has_toml():
    base = merge_toml("", "a", {"command": "c", "args": []})
    assert has_toml(base, "a")
    out = remove_toml(base, "a")
    assert not has_toml(out, "a")


# ---- file round-trips (tmp only) ----

def _json_host(tmp_path) -> HostConfig:
    return HostConfig("claude-code", tmp_path / "claude.json", "json", ("mcpServers",))


def _toml_host(tmp_path) -> HostConfig:
    return HostConfig("codex", tmp_path / "config.toml", "toml", ("mcp_servers",))


def test_patch_host_json_creates_file_no_backup(tmp_path):
    hc = _json_host(tmp_path)
    backup = patch_host(hc, "context7", _ENTRY)
    assert backup is None  # fresh file
    data = json.loads(hc.path.read_text())
    assert data["mcpServers"]["context7"] == _ENTRY
    assert is_installed(hc, "context7")


def test_patch_host_json_backs_up_existing(tmp_path):
    hc = _json_host(tmp_path)
    hc.path.write_text(json.dumps({"mcpServers": {"old": {"command": "o"}}, "keep": 9}))
    backup = patch_host(hc, "context7", _ENTRY)
    assert backup is not None and backup.exists()
    data = json.loads(hc.path.read_text())
    assert data["keep"] == 9 and "old" in data["mcpServers"] and "context7" in data["mcpServers"]


def test_patch_host_rejects_corrupt_existing_json(tmp_path):
    hc = _json_host(tmp_path)
    hc.path.write_text("{ not json ")
    with pytest.raises(PatchError, match="not valid JSON"):
        patch_host(hc, "context7", _ENTRY)


def test_patch_and_unpatch_toml_round_trip(tmp_path):
    hc = _toml_host(tmp_path)
    patch_host(hc, "codegraph", {"command": "npx", "args": ["-y", "cg"]})
    assert is_installed(hc, "codegraph")
    unpatch_host(hc, "codegraph")
    assert not is_installed(hc, "codegraph")


def test_unpatch_absent_file_returns_none(tmp_path):
    hc = _json_host(tmp_path)
    assert unpatch_host(hc, "anything") is None
