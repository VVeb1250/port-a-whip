"""Transcript usage evidence (#1) — scan window, counting, idle-server flagging."""

import json
import os
import time

from portaw.sets import state as state_mod
from portaw.sets.usage import scan_transcripts, usage_report


def _write_transcript(path, calls, *, age_days=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": c, "input": {}}]}}) for c in calls]
    path.write_text("\n".join(lines), encoding="utf-8")
    if age_days:
        past = time.time() - age_days * 86400
        os.utime(path, (past, past))


def test_definition_mentions_are_not_counted(tmp_path):
    """A server's tool list rides in every transcript (definitions) — those
    mentions are the COST, not usage, and must not count as calls."""
    p = tmp_path / "p" / "s.jsonl"
    p.parent.mkdir(parents=True)
    defs_line = json.dumps({"type": "system", "tools": [
        {"name": "mcp__codegraph__codegraph_explore"},
        {"name": "mcp__codegraph__codegraph_search"},
    ]})
    p.write_text(defs_line + "\n", encoding="utf-8")
    assert scan_transcripts(tmp_path) == {}


def test_scan_counts_per_server_and_tool(tmp_path):
    _write_transcript(tmp_path / "p1" / "s1.jsonl", [
        "mcp__codegraph__codegraph_explore",
        "mcp__codegraph__codegraph_explore",
        "mcp__codegraph__codegraph_search",
        "mcp__context7__query-docs",
    ])
    counts = scan_transcripts(tmp_path)
    assert counts["codegraph"]["codegraph_explore"] == 2
    assert counts["codegraph"]["codegraph_search"] == 1
    assert counts["context7"]["query-docs"] == 1


def test_scan_excludes_files_outside_window(tmp_path):
    _write_transcript(tmp_path / "old.jsonl",
                      ["mcp__stale__tool"], age_days=60)
    _write_transcript(tmp_path / "new.jsonl", ["mcp__fresh__tool"])
    counts = scan_transcripts(tmp_path, days=30)
    assert "fresh" in counts and "stale" not in counts


def test_scan_missing_root_returns_empty(tmp_path):
    assert scan_transcripts(tmp_path / "nope") == {}


def test_report_flags_idle_paw_managed_server(tmp_path):
    # paw installed context7, but transcripts show zero calls → idle-def flag
    state_mod.record_install("claude-code", "context-quality",
                             {"context7": {"command": "npx"}}, today="2026-06-08")
    _write_transcript(tmp_path / "t.jsonl", ["mcp__codegraph__codegraph_explore"])
    lines = "\n".join(usage_report(root=tmp_path))
    assert "✗ context7" in lines and "idle def tokens" in lines
    assert "installed 2026-06-08" in lines              # the A/B 'since' anchor
    assert "✓ codegraph" in lines and "codegraph_explore ×1" in lines


def test_report_with_nothing_observed(tmp_path):
    lines = usage_report(root=tmp_path / "empty")
    assert any("nothing observed" in ln for ln in lines)
