"""Patch host MCP config — the 0-dep L1 install core.

Parse → dict-merge → backup → write → re-parse validate. NEVER string-edit
(avoids JSON/TOML corruption). Preserves the user's OTHER servers. Idempotent
on re-install. Handles file-absent + parent-table-absent edges.

JSON  (Claude Code ~/.claude.json, Gemini settings.json): stdlib json.
TOML  (Codex ~/.codex/config.toml, [mcp_servers.<name>]): tomlkit write
      (preserves comments) + stdlib tomllib re-read to validate round-trip.

Merge funcs are PURE (return new structures, no mutation of inputs) so they're
unit-testable without touching disk.
"""

from __future__ import annotations

import copy
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import tomlkit

from portaw.config import HostConfig


class PatchError(RuntimeError):
    """Config unreadable, unparseable, or would-be-invalid after patch."""


# ---------------------------------------------------------------- entry shape

def build_entry(mcp_tool: dict) -> dict:
    """Extract the canonical {command, args, env?} block from a set's mcp entry."""
    cfg = mcp_tool.get("mcp_config") or {}
    command = cfg.get("command")
    if not command:
        raise PatchError(f"mcp tool '{mcp_tool.get('tool', '?')}' has no mcp_config.command")
    entry: dict = {"command": command, "args": list(cfg.get("args", []))}
    env = cfg.get("env") or {}
    if env:
        entry["env"] = dict(env)
    return entry


# ---------------------------------------------------------------- JSON (pure)

def _servers_map(node: dict, servers_key: tuple[str, ...], create: bool) -> dict | None:
    """Walk servers_key to the server map. create=False returns None if missing."""
    for k in servers_key:
        nxt = node.get(k) if isinstance(node, dict) else None
        if not isinstance(nxt, dict):
            if not create:
                return None
            nxt = {}
            node[k] = nxt
        node = nxt
    return node


def merge_json(config: dict, servers_key: tuple[str, ...], name: str, entry: dict) -> dict:
    """Return a NEW config with server `name` set to `entry` (other servers intact)."""
    out = copy.deepcopy(config)
    servers = _servers_map(out, servers_key, create=True)
    assert servers is not None  # create=True never returns None
    servers[name] = entry
    return out


def remove_json(config: dict, servers_key: tuple[str, ...], name: str) -> dict:
    """Return a NEW config with server `name` removed (no-op if absent)."""
    out = copy.deepcopy(config)
    servers = _servers_map(out, servers_key, create=False)
    if servers and name in servers:
        del servers[name]
    return out


def has_json(config: dict, servers_key: tuple[str, ...], name: str) -> bool:
    servers = _servers_map(copy.deepcopy(config), servers_key, create=False)
    return bool(servers and name in servers)


# ---------------------------------------------------------------- TOML (pure)

def merge_toml(text: str, name: str, entry: dict) -> str:
    """Codex: write [mcp_servers.<name>] preserving existing tables/comments."""
    doc = tomlkit.parse(text) if text.strip() else tomlkit.document()
    if "mcp_servers" not in doc:
        # super-table → renders children as [mcp_servers.<name>], not a bare [mcp_servers].
        doc["mcp_servers"] = tomlkit.table(is_super_table=True)
    tbl = tomlkit.table()
    tbl["command"] = entry["command"]
    tbl["args"] = entry.get("args", [])
    if entry.get("env"):
        env_tbl = tomlkit.table()
        for k, v in entry["env"].items():
            env_tbl[k] = v
        tbl["env"] = env_tbl
    doc["mcp_servers"][name] = tbl
    return tomlkit.dumps(doc)


def remove_toml(text: str, name: str) -> str:
    if not text.strip():
        return text
    doc = tomlkit.parse(text)
    servers = doc.get("mcp_servers")
    if servers is not None and name in servers:
        del servers[name]
    return tomlkit.dumps(doc)


def has_toml(text: str, name: str) -> bool:
    if not text.strip():
        return False
    doc = tomlkit.parse(text)
    servers = doc.get("mcp_servers")
    return bool(servers is not None and name in servers)


# ---------------------------------------------------------------- file ops

def _backup(path: Path) -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    bak = path.with_name(path.name + f".paw-bak-{ts}")
    bak.write_bytes(path.read_bytes())
    return bak


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _guard_unchanged(path: Path, before_text: str) -> None:
    """The host (e.g. a running Claude Code) rewrites its own config; if the file
    changed between our read and our write, writing would silently destroy the
    host's update — refuse instead of clobbering.

    Compares CONTENT, not mtime: mtime granularity is coarse on some filesystems
    (a read + sub-tick rewrite can share one st_mtime_ns), so an mtime guard
    silently misses the race. Content also avoids false positives (a touch that
    leaves the data identical is no clobber risk). Reads the file directly rather
    than via _read so a monkeypatched/instrumented _read can't re-trigger here."""
    try:
        current = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return  # unreadable now → let the write attempt surface the real error
    if current != before_text:
        raise PatchError(
            f"{path} changed while patching (is the host running?) — re-run the command"
        )


def get_entry(hc: HostConfig, name: str) -> dict | None:
    """The live config entry for server `name` (None when absent) — the read side
    of drift detection: state.py compares this against what paw wrote."""
    text = _read(hc.path)
    if not text.strip():
        return None
    try:
        if hc.fmt == "json":
            node: object = json.loads(text)
            for k in hc.servers_key:
                node = node.get(k, {}) if isinstance(node, dict) else {}
            entry = node.get(name) if isinstance(node, dict) else None
        else:
            entry = tomllib.loads(text).get("mcp_servers", {}).get(name)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError) as e:
        raise PatchError(f"existing {hc.path} is not valid {hc.fmt}: {e}") from e
    return dict(entry) if isinstance(entry, dict) else None


def is_installed(hc: HostConfig, name: str) -> bool:
    """Is server `name` already present in this host's config?"""
    text = _read(hc.path)
    try:
        if hc.fmt == "json":
            config = json.loads(text) if text.strip() else {}
            return has_json(config, hc.servers_key, name)
        return has_toml(text, name)
    except (json.JSONDecodeError, tomlkit.exceptions.ParseError) as e:
        # name the file — a bare JSONDecodeError reads like a paw bug, not a
        # corrupt host config the user can act on
        raise PatchError(f"existing {hc.path} is not valid {hc.fmt}: {e}") from e


def patch_host(hc: HostConfig, name: str, entry: dict) -> Path | None:
    """Install/overwrite server `name`. Backup first (if file exists), validate after.

    Returns the backup path (None if config file was created fresh).
    """
    text = _read(hc.path)
    if hc.fmt == "json":
        try:
            config = json.loads(text) if text.strip() else {}
        except json.JSONDecodeError as e:
            raise PatchError(f"existing {hc.path} is not valid JSON: {e}") from e
        # ensure_ascii=False: the user's config may carry non-ASCII (paths, notes) —
        # escaping it to \uXXXX churns every such line on each patch.
        out_text = json.dumps(
            merge_json(config, hc.servers_key, name, entry), indent=2, ensure_ascii=False
        )
        try:
            json.loads(out_text)  # validate
        except json.JSONDecodeError as e:  # pragma: no cover - defensive
            raise PatchError(f"patched JSON would be invalid: {e}") from e
    else:
        try:
            out_text = merge_toml(text, name, entry)
            tomllib.loads(out_text)  # stdlib re-read confirms round-trip
        except (tomlkit.exceptions.ParseError, tomllib.TOMLDecodeError) as e:
            raise PatchError(f"TOML patch invalid for {hc.path}: {e}") from e

    try:
        _guard_unchanged(hc.path, text)
        backup = _backup(hc.path) if hc.path.exists() else None
        hc.path.parent.mkdir(parents=True, exist_ok=True)
        hc.path.write_text(out_text, encoding="utf-8")
        return backup
    except OSError as e:
        raise PatchError(f"Cannot write {hc.path}: {e}") from e


def unpatch_host(hc: HostConfig, name: str) -> Path | None:
    """Remove server `name`. Backup first. True no-op (no rewrite) if absent —
    a rewrite would reformat the whole config for nothing."""
    text = _read(hc.path)
    if not text.strip():
        return None
    if hc.fmt == "json":
        try:
            config = json.loads(text)
        except json.JSONDecodeError as e:
            raise PatchError(f"existing {hc.path} is not valid JSON: {e}") from e
        if not has_json(config, hc.servers_key, name):
            return None
        out_text = json.dumps(
            remove_json(config, hc.servers_key, name), indent=2, ensure_ascii=False
        )
    else:
        if not has_toml(text, name):
            return None
        out_text = remove_toml(text, name)
    try:
        _guard_unchanged(hc.path, text)
        backup = _backup(hc.path) if hc.path.exists() else None
        hc.path.parent.mkdir(parents=True, exist_ok=True)
        hc.path.write_text(out_text, encoding="utf-8")
        return backup
    except OSError as e:
        raise PatchError(f"Cannot write {hc.path}: {e}") from e
