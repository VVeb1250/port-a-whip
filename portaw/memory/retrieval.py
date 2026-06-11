"""Memory retrieval — hybrid, reusing the ONE ranking kernel.

semantic half = kernel.route() over lesson Capabilities (same engine the L2
router uses — one kernel, no duplicate ranker). structural half = anchor overlap
against the current edit target (anchors.py). Final rank multiplies relevance by
confidence and ACT-R activation (recency × frequency, §5) so a stale or
low-confidence lesson sinks even on a strong lexical match. Pure — store.py
supplies the entries, the caller supplies prompt + edit-target.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from portaw.kernel.ranking import Capability, RouteConfig, route
from portaw.memory.anchors import AnchorQuery, overlap
from portaw.memory.schema import MemoryEntry


@dataclass(frozen=True)
class RetrievalContext:
    """Current host context — filters lesson applicability (§2.1)."""

    stacks: frozenset[str] = frozenset()
    project_id: str = ""


@dataclass(frozen=True)
class RetrievalConfig:
    anchor_weight: float = 0.6      # how much a structural hit counts vs lexical
    base_floor: float = 0.12        # below this combined base → dropped (silence)
    decay_lambda: float = 0.03      # recency half-life ≈ ln2/λ ≈ 23 days
    unknown_age_days: int = 30      # last_seen missing → treated this stale


@dataclass(frozen=True)
class Scored:
    score: float        # final = base × confidence × activation (rank order)
    entry: MemoryEntry
    relevance: float    # semantic (kernel)
    anchor: float       # structural (overlap)
    activation: float
    base: float         # relevance + anchor_weight × anchor (pre-confidence gate)


def is_eligible(entry: MemoryEntry, ctx: RetrievalContext) -> bool:
    """Applicability filter (lessons only; project entries are pre-scoped)."""
    if entry.type != "lesson":
        return True
    tag = entry.applicability
    if tag == "universal":
        return True
    if tag.startswith("stack:"):
        return tag.split(":", 1)[1] in ctx.stacks
    if tag.startswith("project:"):
        return tag.split(":", 1)[1] == ctx.project_id
    return True  # unknown tag → don't silently hide


def _days_between(iso: str, today: date) -> int:
    if not iso:
        return -1
    try:
        return (today - date.fromisoformat(iso)).days
    except ValueError:
        return -1


def activation(entry: MemoryEntry, today: date, cfg: RetrievalConfig) -> float:
    """ACT-R-style: recency decay × (1 + log frequency). Recurrence lifts, age sinks."""
    days = _days_between(entry.last_seen, today)
    if days < 0:
        days = cfg.unknown_age_days
    recency = math.exp(-cfg.decay_lambda * max(days, 0))
    freq = math.log1p(max(entry.recurrence, 0))
    return recency * (1.0 + freq)


def _lesson_caps(entries: list[MemoryEntry]) -> list[Capability]:
    """Build routable Capabilities from entries (memory owns this; kernel stays shared)."""
    return [
        Capability(name=e.id, text=e.searchable_text, ctype="lesson", desc=e.body[:90])
        for e in entries
    ]


def recall(
    prompt: str,
    entries: list[MemoryEntry],
    *,
    query: AnchorQuery | None = None,
    ctx: RetrievalContext | None = None,
    cfg: RetrievalConfig | None = None,
    route_cfg: RouteConfig | None = None,
    embed_fn: Callable[[str, list[Capability]], dict[str, float]] | None = None,
    today: date | None = None,
) -> list[Scored]:
    """Rank eligible entries for (prompt + edit-target). [] when nothing clears the floor.

    base = relevance + anchor_weight × anchor_overlap   (structural can surface a
    lexically-silent entry, like prerequisite fan-out). final = base × confidence
    × activation. Entries below base_floor are dropped → silence is the default —
    EXCEPT pinned entries: pinned = always-on tier (schema contract), so the floor
    never silences them; inject's budget is their only cap.
    """
    query = query or AnchorQuery()
    ctx = ctx or RetrievalContext()
    cfg = cfg or RetrievalConfig()
    today = today or date.today()

    eligible = [e for e in entries if is_eligible(e, ctx)]
    if not eligible:
        return []

    # fold the edit-target symbols/paths into the routing text → kernel sees them
    route_query = " ".join([prompt, query.as_text()]).strip()
    caps = _lesson_caps(eligible)
    hits = route(route_query, caps, route_cfg, embed_fn=embed_fn)
    rel_by_id = {h.cap.name: h.score for h in hits}

    scored: list[Scored] = []
    for e in eligible:
        rel = rel_by_id.get(e.id, 0.0)
        anc = overlap(e.anchors, query)
        base = rel + cfg.anchor_weight * anc
        if base < cfg.base_floor and not e.pinned:
            continue
        act = activation(e, today, cfg)
        scored.append(
            Scored(score=base * e.confidence * act, entry=e,
                   relevance=rel, anchor=anc, activation=act, base=base)
        )
    scored.sort(key=lambda s: -s.score)
    return scored
