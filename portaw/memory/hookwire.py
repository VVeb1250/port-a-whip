"""Wire the L3 capture hook into a host's Stop event.

Reuses the router's generic hook wiring (one wiring implementation, no drift):
the capture hook fires on Stop, reads a ``paw_lesson`` payload, and stores a
lesson. Same host config files as the router (CC/Gemini settings.json, Codex
config.toml) — only the event (Stop) and the command differ.
"""

from __future__ import annotations

from pathlib import Path

from portaw.adapters.router import disable_hook, enable_hook, status_hook
from portaw.config import HostId

_CAPTURE_CMD = "portaw memory capture-hook"

# Stop-event name per host. CC uses "Stop"; Codex/Gemini equivalents are best-guess
# and confirmed when those hosts are live-wired (mirrors the router's Gemini caveat).
_STOP_EVENT: dict[str, str] = {
    "claude-code": "Stop",
    "codex": "Stop",
    "gemini": "Stop",
}


def _event(host: HostId) -> str:
    return _STOP_EVENT.get(host, "Stop")


def capture_command(host: HostId) -> str:
    """CC stays the bare marker; other hosts carry --host for parity with the router."""
    return _CAPTURE_CMD if host == "claude-code" else f"{_CAPTURE_CMD} --host {host}"


def enable_capture(host: HostId) -> tuple[bool, Path | None]:
    return enable_hook(host, command=capture_command(host), event=_event(host), marker=_CAPTURE_CMD)


def disable_capture(host: HostId) -> bool:
    return disable_hook(host, event=_event(host), marker=_CAPTURE_CMD)


def capture_status(host: HostId) -> dict:
    return status_hook(host, event=_event(host), marker=_CAPTURE_CMD)


# --- live-inject surfaces (P1 SessionStart pins, P2/P3 PostToolUse) — CC-only v1:
# the SessionStart/PostToolUse payload + matcher contracts are VERIFIED on
# claude-code; other hosts get these after their contracts are live-checked.

_SESSION_CMD = "portaw memory session-hook"
_TOOL_CMD = "portaw memory tool-hook"
_TOOL_MATCHER = "Bash|Edit|Write|MultiEdit|NotebookEdit"

_INJECT_HOOKS: dict[str, tuple[str, str, str | None]] = {
    # name → (command, event, matcher)
    "session": (_SESSION_CMD, "SessionStart", None),
    "tool": (_TOOL_CMD, "PostToolUse", _TOOL_MATCHER),
}


def _inject_spec(name: str, host: HostId) -> tuple[str, str, str | None]:
    if host != "claude-code":
        raise ValueError(f"inject hook '{name}' is claude-code-only for now "
                         f"(SessionStart/PostToolUse contract unverified on '{host}')")
    if name not in _INJECT_HOOKS:
        raise ValueError(f"unknown inject hook '{name}' (session/tool)")
    return _INJECT_HOOKS[name]


def enable_inject(name: str, host: HostId = "claude-code") -> tuple[bool, Path | None]:
    cmd, event, matcher = _inject_spec(name, host)
    return enable_hook(host, command=cmd, event=event, marker=cmd, matcher=matcher)


def disable_inject(name: str, host: HostId = "claude-code") -> bool:
    cmd, event, _ = _inject_spec(name, host)
    return disable_hook(host, event=event, marker=cmd)


def inject_status(name: str, host: HostId = "claude-code") -> dict:
    cmd, event, _ = _inject_spec(name, host)
    return status_hook(host, event=event, marker=cmd)
