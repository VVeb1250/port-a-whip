"""Router adapter — rank a prompt against the capability registry, inject top hits.

Two roles:
  • run_hook(): the hook ENTRYPOINT. Reads the host's prompt-submit JSON from
    stdin, ranks, emits `additionalContext`. Safe-by-construction: ANY error →
    no output, exit 0 (never blocks a prompt) — same contract as skill-router.
  • enable()/status(): wire `portaw router run` into the host's hook config
    (backup + idempotent), or report wiring state.

All three tier-1 hosts share ONE contract (verified 2026-06-06):
  • stdin = JSON envelope with the user text under key ``prompt`` (CC, Codex, and
    Gemini all carry session_id/transcript_path/cwd/hook_event_name + prompt).
  • output = ``hookSpecificOutput.additionalContext`` (plain-text dev context).
Only two things differ per host → the ``_WIRING`` table below:
  • event name: CC + Codex = ``UserPromptSubmit``; Gemini = ``BeforeAgent``.
  • config file + format: CC/Gemini JSON settings.json; Codex TOML config.toml
    (array-of-tables ``[[hooks.UserPromptSubmit]]`` → ``[[…hooks]]``).
"""

from __future__ import annotations

import json
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import tomlkit

from portaw.config import HostId
from portaw.kernel.ranking import Hit, RouteConfig, route
from portaw.kernel.registry import build_capabilities, build_intent_map

_MIN_PROMPT_LEN = 8
_ROUTER_CMD = "portaw router run"  # marker substring used for idempotent enable


@dataclass(frozen=True)
class Wiring:
    """Where a host keeps its prompt-submit hook + which event fires it."""

    path: Path
    fmt: str    # "json" | "toml"
    event: str  # "UserPromptSubmit" | "BeforeAgent"


# Hooks live in settings.json (CC/Gemini) or config.toml (Codex) — NOT the
# MCP-server config (that's config.py / the patcher). Kept mutable so tests can
# redirect a host's path to a tmp file via monkeypatch.setitem.
_WIRING: dict[str, Wiring] = {
    "claude-code": Wiring(Path.home() / ".claude" / "settings.json", "json", "UserPromptSubmit"),
    "gemini": Wiring(Path.home() / ".gemini" / "settings.json", "json", "BeforeAgent"),
    "codex": Wiring(Path.home() / ".codex" / "config.toml", "toml", "UserPromptSubmit"),
}


def _wiring(host: HostId) -> Wiring:
    if host not in _WIRING:
        raise ValueError(f"router enable unsupported for host '{host}' (claude-code/codex/gemini)")
    return _WIRING[host]


def default_command(host: HostId) -> str:
    """Hook command to wire. CC stays the bare marker (back-compat); other hosts
    carry --host so run_hook emits that host's hookEventName."""
    return _ROUTER_CMD if host == "claude-code" else f"{_ROUTER_CMD} --host {host}"


# ----------------------------------------------------------------- ranking glue

def route_prompt(prompt: str, cfg: RouteConfig | None = None) -> list[Hit]:
    """Rank a prompt against the live capability registry."""
    return route(prompt, build_capabilities(), cfg, build_intent_map())


def format_context(hits: list[Hit]) -> str:
    lines = ["\U0001f43e paw router:"]
    for h in hits:
        lines.append(f"• {h.cap.name} — {h.cap.desc} · {h.cap.invoke}")
    return "\n".join(lines)


def memory_block(prompt: str) -> str:
    """L3 recall for the live hook (prompt-only — no edit-target). Safe → '' on any error."""
    try:
        from portaw.memory.inject import memory_context
        from portaw.memory.store import load_lessons, load_project

        entries = load_lessons() + load_project()
        if not entries:
            return ""
        return memory_context(prompt, entries)
    except Exception:
        return ""


# ----------------------------------------------------------------- hook entry

def run_hook(stdin_text: str | None = None, host: HostId = "claude-code") -> str | None:
    """Process one prompt-submit event. Returns the JSON to print (or None = silent).

    Input is identical across hosts (JSON envelope, prompt under ``prompt``); only
    the emitted ``hookEventName`` is host-specific (Gemini = BeforeAgent)."""
    raw = stdin_text
    if raw is None:
        raw = sys.stdin.buffer.read().decode("utf-8", "ignore") if not sys.stdin.isatty() else ""
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError:
        payload = {}
    prompt = (payload.get("prompt") or "").strip()
    if len(prompt) < _MIN_PROMPT_LEN or prompt.startswith("/"):
        return None
    hits = route_prompt(prompt)
    blocks = [b for b in (format_context(hits) if hits else "", memory_block(prompt)) if b]
    if not blocks:
        return None
    event = _WIRING[host].event if host in _WIRING else "UserPromptSubmit"
    out = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": "\n".join(blocks),
        }
    }
    return json.dumps(out, ensure_ascii=False)


# ----------------------------------------------------------------- file helpers

def _backup(path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = path.with_name(path.name + f".paw-bak-{ts}")
    bak.write_bytes(path.read_bytes())
    return bak


def _write(path: Path, text: str) -> Path | None:
    """Backup (if present) then write. Returns the backup path (None if fresh)."""
    backup = _backup(path) if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return backup


# ----------------------------------------------------------------- JSON wiring

def _is_wired_json(settings: dict, event: str) -> bool:
    blocks = (settings.get("hooks") or {}).get(event) or []
    return any(
        _ROUTER_CMD in (h.get("command") or "")
        for block in blocks for h in block.get("hooks", [])
    )


def _enable_json(w: Wiring, command: str) -> tuple[bool, Path | None]:
    settings: dict = {}
    if w.path.exists():
        try:
            settings = json.loads(w.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"{w.path} is not valid JSON: {e}") from e
    if _is_wired_json(settings, w.event):
        return False, None
    hooks = settings.setdefault("hooks", {})
    hooks.setdefault(w.event, []).append({"hooks": [{"type": "command", "command": command}]})
    return True, _write(w.path, json.dumps(settings, indent=2))


def _disable_json(w: Wiring) -> bool:
    settings = json.loads(w.path.read_text(encoding="utf-8"))
    blocks = (settings.get("hooks") or {}).get(w.event)
    if not blocks:
        return False
    kept = [
        b for b in blocks
        if not any(_ROUTER_CMD in (h.get("command") or "") for h in b.get("hooks", []))
    ]
    if len(kept) == len(blocks):
        return False
    settings["hooks"][w.event] = kept
    w.path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return True


# ----------------------------------------------------------------- TOML wiring (Codex)

def _is_wired_toml(text: str, event: str) -> bool:
    if not text.strip():
        return False
    arr = (tomlkit.parse(text).get("hooks") or {}).get(event)
    if not arr:
        return False
    return any(
        _ROUTER_CMD in (h.get("command") or "")
        for block in arr for h in (block.get("hooks") or [])
    )


def _enable_toml(w: Wiring, command: str) -> tuple[bool, Path | None]:
    text = w.path.read_text(encoding="utf-8") if w.path.exists() else ""
    if _is_wired_toml(text, w.event):
        return False, None
    doc = tomlkit.parse(text) if text.strip() else tomlkit.document()
    hooks = doc.get("hooks")
    if hooks is None:
        hooks = tomlkit.table(is_super_table=True)  # renders [[hooks.<event>]], not [hooks]
        doc["hooks"] = hooks
    arr = hooks.get(w.event)
    if arr is None:
        arr = tomlkit.aot()
        hooks[w.event] = arr
    block = tomlkit.table()
    inner = tomlkit.aot()
    entry = tomlkit.table()
    entry["type"] = "command"
    entry["command"] = command
    entry["command_windows"] = command  # portaw is on PATH; same string both shells
    inner.append(entry)
    block["hooks"] = inner
    arr.append(block)
    out_text = tomlkit.dumps(doc)
    try:
        tomllib.loads(out_text)  # confirm round-trip before writing
    except tomllib.TOMLDecodeError as e:  # pragma: no cover - defensive
        raise ValueError(f"patched TOML would be invalid for {w.path}: {e}") from e
    return True, _write(w.path, out_text)


def _disable_toml(w: Wiring) -> bool:
    if not w.path.exists():
        return False
    text = w.path.read_text(encoding="utf-8")
    if not text.strip():
        return False
    doc = tomlkit.parse(text)
    hooks = doc.get("hooks")
    arr = hooks.get(w.event) if hooks else None
    if not arr:
        return False
    kept = [
        b for b in arr
        if not any(_ROUTER_CMD in (h.get("command") or "") for h in (b.get("hooks") or []))
    ]
    if len(kept) == len(arr):
        return False
    if kept:
        new_arr = tomlkit.aot()
        for b in kept:
            new_arr.append(b)
        hooks[w.event] = new_arr
    else:
        del hooks[w.event]  # last router block gone → drop the empty event table
        if not hooks:
            del doc["hooks"]
    w.path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    return True


# ----------------------------------------------------------------- enable/status (dispatch)

def enable(host: HostId, command: str | None = None) -> tuple[bool, Path | None]:
    """Wire the router hook into the host's hook config. Returns (changed, backup)."""
    w = _wiring(host)
    cmd = command if command is not None else default_command(host)
    return _enable_json(w, cmd) if w.fmt == "json" else _enable_toml(w, cmd)


def disable(host: HostId) -> bool:
    """Remove the router hook block(s). Returns True if anything was removed."""
    w = _wiring(host)
    if not w.path.exists():
        return False
    return _disable_json(w) if w.fmt == "json" else _disable_toml(w)


def status(host: HostId) -> dict:
    w = _wiring(host)
    wired = False
    if w.path.exists():
        try:
            text = w.path.read_text(encoding="utf-8")
            wired = (_is_wired_json(json.loads(text or "{}"), w.event) if w.fmt == "json"
                     else _is_wired_toml(text, w.event))
        except (json.JSONDecodeError, tomlkit.exceptions.ParseError):
            wired = False
    return {"host": host, "settings": str(w.path), "event": w.event,
            "wired": wired, "exists": w.path.exists()}
