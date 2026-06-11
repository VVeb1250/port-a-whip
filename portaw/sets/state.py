"""Install-state ledger — the record of what paw ITSELF installed, per host.

Without it, remove/doctor re-derive everything from the registry: if the
registry changes between install and remove, paw orphans servers it wrote —
and doctor cannot tell "paw-managed" from "user's own" entries, so it can't
report drift. state.json stores the canonical entry paw wrote per tool, which
makes three things cheap: precise removal, drift detection (live config vs
what paw wrote), and orphan detection (recorded but gone from the config).

Lives at ~/.paw/state.json (sibling of the memory store). CLI-paced writes
only (install/remove commands) — no hook writers, so no lock needed.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


def state_path() -> Path:
    return Path.home() / ".paw" / "state.json"


def load_state() -> dict:
    """Full ledger: {"installs": {host: {set: {"date", "tools": {tool: entry}}}}}.
    {} on any error — a broken ledger must never block install/remove."""
    try:
        raw = json.loads(state_path().read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def record_install(host: str, set_name: str, entries: dict[str, dict],
                   *, today: str | None = None) -> None:
    """Record the canonical config entries paw just wrote for `set_name` on `host`.
    Merges over an existing record (re-install/--force refreshes the snapshot)."""
    if not entries:
        return
    state = load_state()
    sets_for_host = state.setdefault("installs", {}).setdefault(host, {})
    rec = sets_for_host.setdefault(set_name, {"tools": {}})
    rec["date"] = today or date.today().isoformat()
    rec["tools"].update(entries)
    save_state(state)


def record_remove(host: str, set_name: str, tools: list[str]) -> None:
    """Drop removed tools from the record; drop the set when nothing remains."""
    state = load_state()
    sets_for_host = state.get("installs", {}).get(host, {})
    rec = sets_for_host.get(set_name)
    if not rec:
        return
    for t in tools:
        rec.get("tools", {}).pop(t, None)
    if not rec.get("tools"):
        sets_for_host.pop(set_name, None)
    save_state(state)


def installed_sets(host: str) -> dict[str, dict]:
    """set name → record for this host ({} when nothing paw-managed)."""
    return load_state().get("installs", {}).get(host, {})


def managed_tools(host: str) -> dict[str, dict]:
    """tool → {"set": name, "entry": canonical-config} across all sets on host."""
    out: dict[str, dict] = {}
    for set_name, rec in installed_sets(host).items():
        for tool, entry in rec.get("tools", {}).items():
            out[tool] = {"set": set_name, "entry": entry}
    return out


def check_drift(host: str, live_entry_fn) -> list[tuple[str, str, str]]:
    """Compare every paw-managed tool against the live host config.

    `live_entry_fn(tool) -> dict | None` reads the current config entry.
    Returns (tool, kind, detail): kind = "orphaned" (recorded but gone from the
    config — removed outside paw) or "drift" (live entry differs from what paw
    wrote — maybe deliberate user tuning, so report, never auto-fix)."""
    findings: list[tuple[str, str, str]] = []
    for tool, info in sorted(managed_tools(host).items()):
        try:
            live = live_entry_fn(tool)
        except Exception as e:
            findings.append((tool, "unreadable", str(e)))
            continue
        if live is None:
            findings.append(
                (tool, "orphaned",
                 f"paw installed it (set {info['set']}) but it is gone from the config"))
        elif live != info["entry"]:
            findings.append(
                (tool, "drift",
                 "live entry differs from what paw wrote (user-tuned? registry update?)"))
    return findings
