"""Install orchestration: patch MCP config (auto) + surface shim steps (manual).

Phase-1 safety stance: paw AUTO-applies the reversible, deterministic part —
patching MCP config (backup + validate + dict-merge). It does NOT silently run
vendor installers (curl|sh, pip, brew, `codegraph init`). Those are shown as a
manual checklist. Auto-exec with confirmation = later phase. This keeps the RCE
surface at zero (see CLAUDE.md security) while still doing the hard config work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from portaw.config import HostConfig, HostId, host_config
from portaw.sets.loader import CuratedSet, get_set
from portaw.sets.patcher import build_entry, is_installed, patch_host, unpatch_host


@dataclass
class ShimStep:
    tool: str
    label: str
    cmd: str
    runs_vendor_code: bool


@dataclass
class InstallResult:
    set_name: str
    host: HostId
    patched: list[tuple[str, Path | None]] = field(default_factory=list)  # (tool, backup)
    skipped: list[str] = field(default_factory=list)  # already present
    alt_skipped: list[str] = field(default_factory=list)  # host-anchored to another host
    shim_steps: list[ShimStep] = field(default_factory=list)
    mcp_count_after: int = 0
    ceiling_warning: str | None = None


@dataclass
class RemoveResult:
    set_name: str
    host: HostId
    removed: list[tuple[str, Path | None]] = field(default_factory=list)
    reverse_shim: list[ShimStep] = field(default_factory=list)


_CEILING = 3  # N1: ≤2-3 active MCP servers on load-all hosts


def _for_host(entry: dict, hid: str) -> bool:
    """True if a set entry applies to host `hid` (unanchored, or anchor includes it)."""
    ha = entry.get("host_anchor")
    if ha is None:
        return True
    return hid in ({ha} if isinstance(ha, str) else set(ha))


def _gather_shim(cs: CuratedSet, hid: str) -> list[ShimStep]:
    """All manual steps for THIS host: mcp setup_shim residue + non_mcp installs.

    Host-anchored entries for a different host are skipped (their tool isn't
    installed on this host, so its shim steps don't apply)."""
    steps: list[ShimStep] = []
    for m in cs.mcp:
        if not _for_host(m, hid):
            continue
        shim = m.get("setup_shim") or {}
        for s in shim.get("steps", []):
            steps.append(
                ShimStep(m["tool"], s.get("label", ""), s.get("cmd", ""), bool(s.get("runs_vendor_code")))
            )
    for nm in cs.non_mcp:
        if not _for_host(nm, hid):
            continue
        for s in nm.get("install", []):
            steps.append(
                ShimStep(nm["tool"], s.get("label", ""), s.get("cmd", ""), bool(s.get("runs_vendor_code")))
            )
    return steps


def _count_active_mcp(hc: HostConfig) -> int:
    """How many MCP servers currently in the host config (for ceiling check)."""
    import json

    from portaw.sets.patcher import _read  # reuse readers

    text = _read(hc.path)
    if not text.strip():
        return 0
    if hc.fmt == "json":
        cfg = json.loads(text)
        node = cfg
        for k in hc.servers_key:
            node = node.get(k, {}) if isinstance(node, dict) else {}
        return len(node) if isinstance(node, dict) else 0
    import tomlkit

    servers = tomlkit.parse(text).get("mcp_servers")
    return len(servers) if servers is not None else 0


def resolve_host(host: str | None) -> HostId:
    """Pick a host: explicit flag, else the single detected one, else error."""
    from portaw.config import detect_hosts

    if host:
        if host not in ("claude-code", "codex", "gemini"):
            raise ValueError(f"unknown host '{host}' (claude-code/codex/gemini)")
        return host  # type: ignore[return-value]
    found = detect_hosts()
    if len(found) == 1:
        return found[0]
    if not found:
        raise ValueError("no host config detected — pass --host")
    raise ValueError(f"multiple hosts detected ({', '.join(found)}) — pass --host")


def install_set(set_name: str, host: str | None, force: bool = False) -> InstallResult:
    cs = get_set(set_name)
    hid = resolve_host(host)
    hc = host_config(hid)
    res = InstallResult(set_name=cs.name, host=hid)

    for m in cs.mcp:
        name = m["tool"]
        if not _for_host(m, hid):  # host-conditional: belongs to another host's stack
            res.alt_skipped.append(name)
            continue
        if is_installed(hc, name) and not force:
            res.skipped.append(name)
            continue
        backup = patch_host(hc, name, build_entry(m))
        res.patched.append((name, backup))

    res.shim_steps = _gather_shim(cs, hid)
    res.mcp_count_after = _count_active_mcp(hc)
    if res.mcp_count_after > _CEILING:
        res.ceiling_warning = (
            f"{res.mcp_count_after} active MCP servers on {hid} (> {_CEILING}). "
            "Load-all hosts pay schema tokens per def — consider trimming or tool_subset."
        )
    return res


def remove_set(set_name: str, host: str | None) -> RemoveResult:
    cs = get_set(set_name)
    hid = resolve_host(host)
    hc = host_config(hid)
    res = RemoveResult(set_name=cs.name, host=hid)
    for m in cs.mcp:
        name = m["tool"]
        if is_installed(hc, name):
            backup = unpatch_host(hc, name)
            res.removed.append((name, backup))
    # non-MCP / shim removal is manual (we didn't auto-run installs).
    res.reverse_shim = _gather_shim(cs, hid)
    return res
