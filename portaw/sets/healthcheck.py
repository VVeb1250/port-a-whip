"""§10 deterministic gate — install health-check (the half B1 bench doesn't cover).

spec §10 MVP gate = (1) token delta [B1 bench] + (2) install health-check. This
is (2): after installing a set, is each tool ACTUALLY reachable — not just
written to config? Mirrors the codegraph-link health-gate (check real state,
not file presence).

Deterministic + offline: resolves each tool's binary on PATH (shutil.which).
No LLM, no network. Trajectory / pass@1 / LLM-judge = Phase 2 (agentevals),
out of scope here by design (heavy dep + needs run fixtures).

Per-tool a set entry MAY declare `health_binary` to override the probe target.
Defaults: non-MCP → the tool name; MCP → its `health_binary` if given, else the
tool is config-only (runtime-fetched via npx) and reported as such.

A set entry MAY also declare `host_anchor` (a host id or list) for a
host-conditional tool — e.g. efficiency-starter uses codegraph on Claude Code but
semble on load-all hosts. A tool whose anchor excludes the target host is the
OTHER host's alternate: reported as `alt` (informational, never fails the gate),
not probed on PATH. With no host given, the target defaults to claude-code.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Literal

from portaw.config import HostId
from portaw.sets.loader import get_set

Status = Literal["ok", "missing", "config-only", "alt"]
_DEFAULT_HOST = "claude-code"


@dataclass(frozen=True)
class ToolHealth:
    tool: str
    kind: Literal["mcp", "non_mcp"]
    status: Status
    detail: str


@dataclass(frozen=True)
class SetHealth:
    set_name: str
    tools: tuple[ToolHealth, ...]

    @property
    def ok(self) -> bool:
        """Gate passes when no tool is outright missing (config-only/alt allowed)."""
        return all(t.status != "missing" for t in self.tools)


def _which(binary: str) -> str | None:
    return shutil.which(binary)


def _anchor_hosts(entry: dict) -> set[str] | None:
    """Hosts a tool is anchored to, or None when unanchored (required everywhere)."""
    ha = entry.get("host_anchor")
    if ha is None:
        return None
    return {ha} if isinstance(ha, str) else set(ha)


def _probe_non_mcp(entry: dict) -> ToolHealth:
    tool = entry["tool"]
    # key ABSENT -> default to tool name (probe by name). key PRESENT-but-null
    # -> a skill (impeccable/browser-harness): no PATH binary to probe, installed
    # via the host's skill mechanism. Report config-only (never fails the gate),
    # mirroring _probe_mcp's null handling.
    binary = entry.get("health_binary", tool)
    if not binary:
        return ToolHealth(
            tool, "non_mcp", "config-only",
            "skill / no binary to probe (installed via host skill mechanism)",
        )
    path = _which(binary)
    if path:
        return ToolHealth(tool, "non_mcp", "ok", f"{binary} → {path}")
    return ToolHealth(tool, "non_mcp", "missing", f"{binary} not on PATH (run install steps)")


def _probe_mcp(entry: dict) -> ToolHealth:
    tool = entry["tool"]
    binary = entry.get("health_binary")
    if not binary:
        return ToolHealth(
            tool, "mcp", "config-only",
            "no static probe (runtime-fetched via npx); config patch only",
        )
    path = _which(binary)
    if path:
        return ToolHealth(tool, "mcp", "ok", f"{binary} → {path}")
    return ToolHealth(tool, "mcp", "missing", f"{binary} not on PATH")


def check_set(set_name: str, host: HostId | None = None) -> SetHealth:
    """Probe every tool in a set for reachability on `host` (default claude-code).

    Host-conditional tools (`host_anchor` excluding the target) are reported as
    `alt` and not probed — they belong to the OTHER host's stack. Pure-ish (PATH only).
    """
    target = host or _DEFAULT_HOST
    cs = get_set(set_name)
    tools: list[ToolHealth] = []
    for m in cs.mcp:
        anchors = _anchor_hosts(m)
        if anchors is not None and target not in anchors:
            tools.append(ToolHealth(
                m["tool"], "mcp", "alt",
                f"host-anchored to {sorted(anchors)} — alternate on {target}",
            ))
            continue
        tools.append(_probe_mcp(m))
    for nm in cs.non_mcp:
        anchors = _anchor_hosts(nm)
        if anchors is not None and target not in anchors:
            tools.append(ToolHealth(
                nm["tool"], "non_mcp", "alt",
                f"host-anchored to {sorted(anchors)} — alternate on {target}",
            ))
            continue
        tools.append(_probe_non_mcp(nm))
    return SetHealth(cs.name, tuple(tools))
