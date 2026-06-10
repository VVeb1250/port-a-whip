"""Failure→fix detector — turn a CC transcript into FailureSignals (§13, the hard part).

Conservative + Bash-focused on purpose: the §13 risk is noise, and a false lesson
poisons the global store. So this only fires on a clear, structured pattern — a
Bash command that errored, then a LATER Bash command that succeeded and shares a
significant token (the same script/file/target) — and emits a LOW-confidence
signal, leaving the integrity gate + cross-project recurrence to decide whether it
earns universal scope. Generic NL detection (non-Bash, multi-step) is deliberately
out of scope until this floor proves itself. Pure: parse + detect take data/paths.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from portaw.memory.capture import FailureSignal

# error markers in a tool result → the command failed
_ERR_PATTERNS: list[tuple[str, str]] = [
    ("command not found", "command not found"),
    ("not recognized as", "command not found"),
    ("no such file", "no such file"),
    ("cannot find", "no such file"),
    ("traceback (most recent", "traceback"),
    ("permission denied", "permission denied"),
    ("fatal:", "fatal"),
    (": error", "error"),
]
_FILEISH = re.compile(r"[./\\]")
_WORD = re.compile(r"[A-Za-z0-9_.\-/\\]{3,}")
_INLINE = re.compile(r"(?:^|\s)-[ce](?:\s|$)")  # `py -c "..."` / `node -e` = inline blob
_MAX_CMD = 150  # longer = a one-off blob, not a reusable corrective command
_SHELL_NOISE = {
    "the", "and", "run", "cd", "ls", "cat", "echo", "git", "sudo", "&&", "||",
    "rm", "cp", "mv", "for", "out", "txt", "log", "tmp", "set", "get",
}


@dataclass(frozen=True)
class ToolCall:
    tool: str
    command: str
    result: str
    is_error: bool


def _text_of(content) -> str:
    """tool_result content may be a string or a list of text blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content if isinstance(b, dict)
        )
    return ""


def parse_transcript(path: Path | str) -> list[ToolCall]:
    """Parse a CC .jsonl transcript into ordered Bash ToolCalls (tolerant)."""
    p = Path(path)
    if not p.exists():
        return []
    uses: dict[str, dict] = {}        # tool_use_id → {tool, command}
    order: list[str] = []
    results: dict[str, ToolCall] = {}
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else obj
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                tid = item.get("id", "")
                inp = item.get("input") or {}
                uses[tid] = {"tool": item.get("name", ""),
                             "command": inp.get("command", "") if isinstance(inp, dict) else ""}
                order.append(tid)
            elif item.get("type") == "tool_result":
                tid = item.get("tool_use_id", "")
                u = uses.get(tid)
                if u is None:
                    continue
                text = _text_of(item.get("content"))
                is_err = bool(item.get("is_error")) or _err_tag(text) != ""
                results[tid] = ToolCall(u["tool"], u["command"], text, is_err)
    return [results[t] for t in order if t in results and results[t].tool == "Bash"]


def _err_tag(text: str) -> str:
    low = text.lower()
    for needle, tag in _ERR_PATTERNS:
        if needle in low:
            return tag
    return ""


def _sig_tokens(command: str) -> set[str]:
    """Significant tokens (filenames/scripts/targets) — what links a fail to its fix."""
    out: set[str] = set()
    for tok in _WORD.findall(command):
        t = tok.strip("-").lower()
        if len(t) < 3 or t in _SHELL_NOISE:
            continue
        out.add(t)
    return out


def _anchors(command: str) -> tuple[list[str], list[str]]:
    """Split command tokens into (paths, symbols) for anchoring."""
    paths, symbols = [], []
    for tok in _WORD.findall(command):
        if _FILEISH.search(tok):
            paths.append(tok)
        elif len(tok) >= 3 and tok.lower() not in _SHELL_NOISE:
            symbols.append(tok)
    return paths, symbols


def _reusable(command: str) -> bool:
    """A short, non-inline command — the kind a corrective lesson is about."""
    return bool(command) and len(command) <= _MAX_CMD and not _INLINE.search(command)


def detect_signals(calls: list[ToolCall], *, max_gap: int = 4,
                   confidence: float = 0.45, min_overlap: float = 0.34) -> list[FailureSignal]:
    """Pair an errored Bash call with a later succeeding NEAR-VARIANT (high token
    overlap). Inline `-c/-e` blobs and long one-offs are skipped, and the fix must
    share a Jaccard ≥ min_overlap of significant tokens — so `python x → py x` fires
    but two unrelated long probes that merely share a generic token do not."""
    signals: list[FailureSignal] = []
    used: set[int] = set()
    for i, c in enumerate(calls):
        if not c.is_error or not _reusable(c.command):
            continue
        fail_tokens = _sig_tokens(c.command)
        if not fail_tokens:
            continue
        for j in range(i + 1, min(i + 1 + max_gap, len(calls))):
            if j in used:
                continue
            nxt = calls[j]
            if nxt.is_error or not _reusable(nxt.command):
                continue
            fix_tokens = _sig_tokens(nxt.command)
            union = fail_tokens | fix_tokens
            if not union or len(fail_tokens & fix_tokens) / len(union) < min_overlap:
                continue
            tag = _err_tag(c.result) or "failed"
            paths, symbols = _anchors(nxt.command)
            signals.append(FailureSignal(
                trigger=f"{c.command} ({tag})",
                fix=nxt.command,
                paths=tuple(paths[:3]),
                symbols=tuple(symbols[:3]),
                confidence=confidence,
            ))
            used.add(j)
            break
    return signals


def from_transcript(path: Path | str) -> list[FailureSignal]:
    """CC transcript → failure→fix signals. [] on a missing/empty/clean transcript."""
    return detect_signals(parse_transcript(path))
