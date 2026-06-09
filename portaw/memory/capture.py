"""Capture — a failure→fix signal becomes a lesson (CC first; §8, Phase 0 rules).

The cross-host-ready contract is ``FailureSignal`` (a tool error + the fix that
followed). Host adapters (CC now, Codex/Gemini in Phase 6) detect signals from a
transcript and hand them here; this module is the host-agnostic pipeline:
classify applicability → build a compressed lesson → gate → upsert (dedup+bump).
Pure except ``capture`` which is the store-backed entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from portaw.kernel.ranking import tokenize
from portaw.memory.gate import GateConfig, Verdict, accepts
from portaw.memory.schema import Anchors, MemoryEntry

# env/shell-level mistakes recur across EVERY project → universal (§2.1)
_ENV_KEYWORDS = {
    "python", "python3", "py", "powershell", "pwsh", "bash", "wsl", "shell",
    "path", "backslash", "npm", "pip", "venv", "windows", "env", "chmod", "sudo",
}
# framework hint → stack:<x>
_STACK_KEYWORDS = {
    "react", "vue", "angular", "svelte", "next", "nextjs", "django", "flask",
    "fastapi", "rails", "spring", "rust", "cargo", "golang", "kotlin", "swift",
    "flutter", "dart", "pytest", "jest",
}


@dataclass(frozen=True)
class FailureSignal:
    """One detected mistake. `trigger` = what went wrong, `fix` = what to do."""

    trigger: str
    fix: str
    paths: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    stack: str = ""           # explicit framework hint (overrides keyword guess)
    env_level: bool = False   # explicit env-level flag (overrides keyword guess)
    confidence: float = 0.5
    extra_terms: tuple[str, ...] = ()


def classify_text(text: str) -> tuple[bool, str]:
    """Heuristic: (env_level, stack) from keywords. Detector may override explicitly."""
    toks = set(tokenize(text))
    stack = next((s for s in _STACK_KEYWORDS if s in toks), "")
    env_level = bool(toks & _ENV_KEYWORDS)
    return env_level, stack


def infer_applicability(signal: FailureSignal, project_id: str) -> str:
    """Map a signal to an applicability tag (§2.1). Conservative default = project."""
    env_level, stack = classify_text(f"{signal.trigger} {signal.fix}")
    stack = signal.stack or stack
    env_level = signal.env_level or env_level
    if stack:
        return f"stack:{stack}"
    if env_level:
        return "universal"
    return f"project:{project_id}"


def to_lesson(signal: FailureSignal, project_id: str,
              today: str | None = None) -> MemoryEntry:
    """Build a compressed lesson (R8: `trigger → fix`) from a signal. Pure."""
    today = today or date.today().isoformat()
    body = f"{signal.trigger} → {signal.fix}"
    applicability = infer_applicability(signal, project_id)
    terms = tuple(dict.fromkeys([*signal.extra_terms, *tokenize(signal.trigger)]))[:8]
    return MemoryEntry.new(
        "lesson", body, "global",  # lessons always live in the GLOBAL store (§2)
        trigger_terms=terms,
        anchors=Anchors(symbols=tuple(signal.symbols), paths=tuple(signal.paths)),
        applicability=applicability,
        confidence=signal.confidence,
        source="hook",
        last_seen=today,
    )


def from_payload(payload: dict) -> "FailureSignal | None":
    """Extract a signal from a host Stop-event payload (cross-host contract, §8).

    Hosts emit a structured ``paw_lesson`` field — the same shape on CC, Codex and
    Gemini — so a lesson captured anywhere flows to the one global store (the
    portability moat). Free-form transcript NL detection is a separate, iterative
    detector (§13); this structured path is the reliable floor."""
    raw = payload.get("paw_lesson") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return None
    trigger = (raw.get("trigger") or "").strip()
    fix = (raw.get("fix") or "").strip()
    if not trigger or not fix:
        return None
    return FailureSignal(
        trigger=trigger, fix=fix,
        symbols=tuple(raw.get("symbols", [])), paths=tuple(raw.get("paths", [])),
        stack=raw.get("stack", ""), env_level=bool(raw.get("env", False)),
        confidence=float(raw.get("confidence", 0.6)),
        extra_terms=tuple(raw.get("terms", [])),
    )


@dataclass
class CaptureResult:
    entry: MemoryEntry
    verdict: Verdict
    stored: bool


def capture(
    signal: FailureSignal,
    project_id: str,
    *,
    confirmed: bool = False,
    gate_cfg: GateConfig | None = None,
    today: str | None = None,
) -> CaptureResult:
    """Signal → lesson → gate → upsert into the global lesson store (dedup+bump)."""
    from portaw.memory.store import load_lessons, save_lessons, upsert

    today = today or date.today().isoformat()
    entry = to_lesson(signal, project_id, today)
    verdict = accepts(entry, confirmed=confirmed, cfg=gate_cfg)
    if not verdict.ok:
        return CaptureResult(entry=entry, verdict=verdict, stored=False)
    save_lessons(upsert(load_lessons(), entry, last_seen=today))
    return CaptureResult(entry=entry, verdict=verdict, stored=True)


def run_capture_hook(
    stdin_text: str | None = None, project_id: str | None = None
) -> CaptureResult | None:
    """Stop-hook entrypoint (all hosts). Safe-by-construction: ANY error → None.

    Same contract across CC/Codex/Gemini — the payload carries ``paw_lesson``;
    capture only writes (no context emitted), so the host differs only in cwd."""
    import json
    import sys
    from pathlib import Path

    try:
        raw = stdin_text
        if raw is None:
            raw = (
                sys.stdin.buffer.read().decode("utf-8", "ignore")
                if not sys.stdin.isatty() else ""
            )
        payload = json.loads(raw) if raw.strip() else {}
        signal = from_payload(payload)
        if signal is None:
            return None
        pid = project_id or payload.get("cwd_name") or Path.cwd().name
        return capture(signal, pid)
    except Exception:
        return None
