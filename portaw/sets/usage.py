"""Usage evidence from host transcripts — the idle-def killer input.

Claude Code transcripts record every MCP tool call as ``mcp__<server>__<tool>``.
A streaming string-level scan over recently-modified transcript files yields
per-server, per-tool observed call counts — the evidence for the two cheapest
token levers there are:

  (a) a server paying idle def tokens with ZERO observed use in the window
      → remove it, or scope it per-project instead of globally;
  (b) tools of a busy server that are never called
      → trim them via the server's tool-subset env when it offers one.

Counts are real tool_use INVOCATIONS (parsed events, not string mentions — a
raw grep also counts the tool definitions every session re-records, which is
the cost, not the use). Still evidence for ranking idle-vs-hot, not a billing
meter — exact token accounting stays `portaw bench`'s job.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from pathlib import Path

_CALL_RE = re.compile(r"mcp__([\w-]+)__([\w-]+)")
_DEFAULT_DAYS = 30


def transcripts_root() -> Path:
    return Path.home() / ".claude" / "projects"


def _count_tool_uses(line: str, out: dict[str, Counter]) -> None:
    """Count only real tool_use events. A raw regex over the whole line counts
    tool DEFINITIONS too (every server's full tool list rides in transcripts each
    session — live run showed identical ×104 counts across all of a server's
    tools), which is exactly the wrong signal: defs are the COST, calls are the
    use. Parse the line and walk message.content for type=tool_use items."""
    import json

    try:
        obj = json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return
    content = obj.get("message", {}).get("content") if isinstance(obj, dict) else None
    if not isinstance(content, list):
        return
    for item in content:
        if isinstance(item, dict) and item.get("type") == "tool_use":
            m = _CALL_RE.fullmatch(str(item.get("name") or ""))
            if m:
                out.setdefault(m.group(1), Counter())[m.group(2)] += 1


def scan_transcripts(root: Path | None = None, *, days: int = _DEFAULT_DAYS,
                     ) -> dict[str, Counter]:
    """server → Counter(tool → invocation count) from transcripts modified within
    `days`. Streaming line reads (transcripts can be huge) with a cheap substring
    prefilter before the JSON parse; any unreadable file is skipped — evidence
    gathering must never crash a report."""
    root = root or transcripts_root()
    cutoff = time.time() - days * 86400
    out: dict[str, Counter] = {}
    try:
        files = list(root.rglob("*.jsonl"))
    except OSError:
        return out
    for f in files:
        try:
            if f.stat().st_mtime < cutoff:
                continue
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"tool_use"' in line and "mcp__" in line:
                        _count_tool_uses(line, out)
        except OSError:
            continue
    return out


def usage_report(host: str = "claude-code", *, days: int = _DEFAULT_DAYS,
                 root: Path | None = None) -> list[str]:
    """Human-readable usage lines: hot tools per server, idle paw-managed servers
    flagged with their install date (so a token A/B has its 'since' anchor)."""
    from portaw.sets import state

    counts = scan_transcripts(root, days=days)
    managed = state.managed_tools(host)
    installed = state.installed_sets(host)
    install_date = {tool: installed.get(info["set"], {}).get("date", "?")
                    for tool, info in managed.items()}

    lines = [f"MCP usage (last {days}d, tool_use events in transcripts):"]
    servers = sorted(set(counts) | set(managed))
    if not servers:
        lines.append("  (nothing observed and nothing paw-managed)")
        return lines
    for server in servers:
        c = counts.get(server)
        tag = f" [paw: {managed[server]['set']}, installed {install_date[server]}]" \
            if server in managed else ""
        if not c:
            lines.append(f"  ✗ {server}{tag}: 0 calls — paying idle def tokens for "
                         f"nothing; consider `portaw remove` or a tool-subset env")
            continue
        total = sum(c.values())
        top = ", ".join(f"{t} ×{n}" for t, n in c.most_common(5))
        lines.append(f"  ✓ {server}{tag}: {total} calls across {len(c)} tools — {top}")
        never_hint = len(c) == 1 and total > 10
        if never_hint:
            lines.append(f"      one tool carries all traffic — if {server} exposes a "
                         f"tool-subset env, trimming the rest cuts idle defs")
    return lines
