"""Injection — silence-biased, per-type threshold, budget cap (R9/R11).

The governing rule: a false-inject (noise → context rot) costs more than a
false-silence. So this layer is biased toward emitting NOTHING. Negative-knowledge
lessons (high ROI) clear a low threshold; project decisions (lower ROI) need a
high one and fire mostly when about to be contradicted. Pinned universal lessons
are injected first; everything is capped to a small per-prompt token budget.
Selection + formatting are pure; ``memory_context`` is the thin store-backed entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from portaw.memory.anchors import AnchorQuery
from portaw.memory.gate import trusted
from portaw.memory.retrieval import (
    RetrievalConfig,
    RetrievalContext,
    Scored,
    recall,
)
from portaw.memory.schema import MemoryEntry


@dataclass(frozen=True)
class InjectConfig:
    lesson_min: float = 0.12    # low — negative knowledge is cheap + high-ROI
    project_min: float = 0.45   # high — only fire decisions on a strong match
    max_tokens: int = 400       # hard per-prompt budget (R9 inject-size, not pool)
    max_items: int = 5


def approx_tokens(text: str) -> int:
    """Cheap token estimate (~4 chars/token) — for budgeting, not billing."""
    return max(1, len(text) // 4)


def _passes(s: Scored, cfg: InjectConfig) -> bool:
    floor = cfg.project_min if s.entry.type == "project" else cfg.lesson_min
    return s.base >= floor


def select(scored: list[Scored], cfg: InjectConfig | None = None) -> list[Scored]:
    """Pinned-first, then per-type-gated, capped by item count AND token budget."""
    cfg = cfg or InjectConfig()
    # untrusted universal lessons (unproven, large blast radius) never inject — they
    # are stored so recurrence can accumulate, but stay silent until proven (§2.2).
    ordered = (
        [s for s in scored if s.entry.pinned]
        + [s for s in scored if not s.entry.pinned and _passes(s, cfg) and trusted(s.entry)]
    )
    out: list[Scored] = []
    seen: set[str] = set()
    budget = cfg.max_tokens
    for s in ordered:
        if len(out) >= cfg.max_items:
            break
        if s.entry.id in seen:
            continue
        cost = approx_tokens(s.entry.body)
        if cost > budget:
            continue  # this one doesn't fit — a cheaper lower-ranked one still may
        out.append(s)
        seen.add(s.entry.id)
        budget -= cost
    return out


def session_select(
    entries: list[MemoryEntry],
    *,
    ctx: "RetrievalContext | None" = None,
    max_tokens: int = 300,
    max_items: int = 8,
) -> list[MemoryEntry]:
    """The SessionStart pinned tier: which entries inject ONCE at session start.

    PINNED-ONLY by doctrine — injecting unpinned entries with no prompt to be
    relevant to is exactly the false-inject the silence bias exists to prevent.
    Pinned = the human said "always-on"; eligibility (stack/project) still filters
    so a pin for another stack stays quiet. Budget-capped like select()."""
    from portaw.memory.retrieval import RetrievalContext, is_eligible

    ctx = ctx or RetrievalContext()
    out: list[MemoryEntry] = []
    budget = max_tokens
    for e in entries:
        if len(out) >= max_items:
            break
        if not e.pinned or not is_eligible(e, ctx):
            continue
        cost = approx_tokens(e.body)
        if cost > budget:
            continue  # this one doesn't fit — a cheaper later pin still may
        out.append(e)
        budget -= cost
    return out


def format_session(selected: list[MemoryEntry]) -> str:
    """SessionStart pin block. Empty selection → empty string (silent)."""
    if not selected:
        return ""
    lines = ["\U0001f4a1 paw memory (session pins):"]
    for e in selected:
        rec = f" (×{e.recurrence})" if e.recurrence > 1 else ""
        lines.append(f"• ★ {e.body}{rec}")
    return "\n".join(lines)


def format_memory(selected: list[Scored]) -> str:
    """Compact inject block (R8 one-liners). Empty selection → empty string."""
    if not selected:
        return ""
    lines = ["\U0001f4a1 paw memory:"]
    for s in selected:
        tag = "★ " if s.entry.pinned else ""  # ★ pinned
        rec = f" (×{s.entry.recurrence})" if s.entry.recurrence > 1 else ""
        lines.append(f"• {tag}{s.entry.body}{rec}")
    return "\n".join(lines)


def memory_context(
    prompt: str,
    entries: list[MemoryEntry],
    *,
    query: AnchorQuery | None = None,
    ctx: RetrievalContext | None = None,
    inject_cfg: InjectConfig | None = None,
    retrieval_cfg: RetrievalConfig | None = None,
    embed_fn=None,
    exclude: set[str] | None = None,
    today: date | None = None,
) -> str:
    """recall → select → format. '' when silent. Pure over the entries it's given.

    `exclude` = ids this session already injected (the dedup log) — an entry the
    conversation already contains must not re-inject."""
    scored = recall(prompt, entries, query=query, ctx=ctx,
                    cfg=retrieval_cfg, embed_fn=embed_fn, today=today)
    if exclude:
        scored = [s for s in scored if s.entry.id not in exclude]
    return format_memory(select(scored, inject_cfg))
