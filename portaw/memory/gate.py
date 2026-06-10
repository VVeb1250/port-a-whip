"""Integrity gate — the safety bar on what gets written (§7 / SSGM).

Evolving + cross-host memory is an attack surface (poisoning, drift). The write
bar scales with blast radius: a wrong `universal` lesson pollutes every project,
so it needs the highest confidence/recurrence; a `project` write touches one repo
but is human-authored, so it needs explicit confirmation. Pure — callers decide
what to do with the verdict.
"""

from __future__ import annotations

from dataclasses import dataclass

from portaw.memory.schema import MemoryEntry


@dataclass(frozen=True)
class GateConfig:
    hot_confidence: float = 0.6           # min confidence to sit in the hot tier
    universal_min_confidence: float = 0.75  # universal blast radius → highest bar
    universal_min_recurrence: int = 2     # …unless it has recurred (proven real)
    project_needs_confirm: bool = True     # human-confirm project-memory writes


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str


def accepts(entry: MemoryEntry, *, confirmed: bool = False,
            cfg: GateConfig | None = None) -> Verdict:
    """May this entry be WRITTEN? Storage is permissive so recurrence can accumulate
    (a rejected lesson never recurs → never learns). The universal blast-radius bar
    lives at injection (`trusted`), not here — false-inject costs more than
    false-store, and consolidation archives anything that never recurs. Project
    writes still need explicit confirm (human-authored, not auto-detected)."""
    cfg = cfg or GateConfig()
    if entry.type == "project":
        if cfg.project_needs_confirm and not confirmed:
            return Verdict(False, "project-memory write needs explicit confirm")
        return Verdict(True, "project write confirmed")
    return Verdict(True, "lesson accepted")


def trusted(entry: MemoryEntry, cfg: GateConfig | None = None) -> bool:
    """May this entry be INJECTED as-is? A universal lesson (largest blast radius)
    must be proven — high confidence OR recurrence (§2.2). Narrower scopes and
    pinned entries are trusted by construction. This is where poisoning is stopped."""
    cfg = cfg or GateConfig()
    if entry.pinned or entry.applicability != "universal":
        return True
    return (
        entry.confidence >= cfg.universal_min_confidence
        or entry.recurrence >= cfg.universal_min_recurrence
    )


def enters_hot(entry: MemoryEntry, cfg: GateConfig | None = None) -> bool:
    """Tiering helper: is this entry confident enough for the hot working set?"""
    cfg = cfg or GateConfig()
    return entry.pinned or entry.confidence >= cfg.hot_confidence
