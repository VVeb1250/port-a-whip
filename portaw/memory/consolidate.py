"""Consolidation — the async "dream" pass (R2). Runs OFF the prompt budget.

Between sessions: merge duplicates, promote a recurring project lesson toward a
wider scope (the `promote` pattern), and archive stale low-activation entries so
the store never bloats. Append-only RAG grows without bound; a consolidated store
does not. Pure — the caller persists `kept` and appends `archived`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from portaw.memory.retrieval import RetrievalConfig, activation
from portaw.memory.schema import MemoryEntry


@dataclass(frozen=True)
class ConsolidationConfig:
    promote_min_recurrence: int = 3    # a project lesson recurred this much → widen scope
    archive_activation: float = 0.15   # below this (and unpinned) → archived as stale
    protect_confidence: float = 0.9    # a vouched-this-strongly lesson never auto-archives
    activation_cfg: RetrievalConfig = RetrievalConfig()


@dataclass
class ConsolidationResult:
    kept: list[MemoryEntry]
    archived: list[MemoryEntry]
    merged_count: int
    promoted_count: int


def merge_duplicates(entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], int]:
    """Collapse same-id entries: sum recurrence, max confidence, latest last_seen."""
    by_id: dict[str, MemoryEntry] = {}
    merged = 0
    for e in entries:
        cur = by_id.get(e.id)
        if cur is None:
            by_id[e.id] = e
            continue
        merged += 1
        by_id[e.id] = replace(
            cur,
            recurrence=cur.recurrence + e.recurrence,
            confidence=max(cur.confidence, e.confidence),
            last_seen=max(cur.last_seen, e.last_seen),
            pinned=cur.pinned or e.pinned,
        )
    return list(by_id.values()), merged


def promote(entry: MemoryEntry, cfg: ConsolidationConfig) -> MemoryEntry:
    """A project lesson that has recurred enough widens to universal (§2.1)."""
    if (
        entry.type == "lesson"
        and entry.applicability.startswith("project:")
        and entry.recurrence >= cfg.promote_min_recurrence
    ):
        from dataclasses import replace
        return replace(entry, applicability="universal")
    return entry


def consolidate(
    entries: list[MemoryEntry],
    *,
    today: date | None = None,
    cfg: ConsolidationConfig | None = None,
) -> ConsolidationResult:
    """merge → promote → archive-stale. Pure; caller saves kept + appends archived."""
    today = today or date.today()
    cfg = cfg or ConsolidationConfig()

    merged, merged_count = merge_duplicates(entries)

    promoted_count = 0
    promoted: list[MemoryEntry] = []
    for e in merged:
        p = promote(e, cfg)
        if p != e:
            promoted_count += 1
        promoted.append(p)

    kept: list[MemoryEntry] = []
    archived: list[MemoryEntry] = []
    for e in promoted:
        act = activation(e, today, cfg.activation_cfg)
        protected = e.pinned or e.confidence >= cfg.protect_confidence
        if not protected and act < cfg.archive_activation:
            archived.append(e)
        else:
            kept.append(e)
    # sort by activation ONLY (never compare the entry — see [sweep-tuple-sort])
    kept.sort(key=lambda e: activation(e, today, cfg.activation_cfg), reverse=True)
    return ConsolidationResult(kept, archived, merged_count, promoted_count)
