"""Consolidation — the async "dream" pass (R2). Runs OFF the prompt budget.

Between sessions: merge duplicates, promote a recurring project lesson toward a
wider scope (the `promote` pattern), and archive stale low-activation entries so
the store never bloats. Append-only RAG grows without bound; a consolidated store
does not. Pure — the caller persists `kept` and appends `archived`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from portaw.memory.confidence import NEUTRAL, decayed
from portaw.memory.retrieval import RetrievalConfig, activation
from portaw.memory.schema import SUPERSEDED_BY, MemoryEntry


@dataclass(frozen=True)
class ConsolidationConfig:
    promote_min_recurrence: int = 3    # a project lesson recurred this much → widen scope
    archive_activation: float = 0.15   # below this (and unpinned) → archived as stale
    decay_activation: float = 0.5      # below this → a never-proven seed's confidence eases down
    protect_confidence: float = 0.9    # a vouched-this-strongly lesson never auto-archives
    activation_cfg: RetrievalConfig = RetrievalConfig()


@dataclass
class ConsolidationResult:
    kept: list[MemoryEntry]
    archived: list[MemoryEntry]
    merged_count: int
    promoted_count: int
    weakened_count: int = 0       # lessons hit by the effectiveness signal this pass
    superseded_count: int = 0     # stale lessons retired by a newer twin (R13 edge)


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
        # union typed edges so a merge never drops a relation either side recorded
        rels = tuple({(r.rel, r.target): r for r in (*cur.relations, *e.relations)}.values())
        by_id[e.id] = replace(
            cur,
            recurrence=cur.recurrence + e.recurrence,
            confidence=max(cur.confidence, e.confidence),
            last_seen=max(cur.last_seen, e.last_seen),
            pinned=cur.pinned or e.pinned,
            relations=rels,
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


def apply_effectiveness(
    entries: list[MemoryEntry], new_misses: dict[str, int],
) -> tuple[list[MemoryEntry], int]:
    """Feed the observation ledger's effectiveness signal back into the lessons.

    `new_misses` = lesson id → recurrences observed AFTER that lesson existed
    (observations.recurring_despite_lesson). Such a lesson's fix is not working:
    accumulate the misses on the entry (the trusted() gate distrusts at a cap)
    and ease confidence down one decay step. Pinned is exempt — human override."""
    out: list[MemoryEntry] = []
    weakened = 0
    for e in entries:
        m = new_misses.get(e.id, 0)
        if m > 0 and not e.pinned:
            e = replace(e, misses=e.misses + m, confidence=decayed(e.confidence))
            weakened += 1
        out.append(e)
    return out, weakened


def apply_supersedes(
    entries: list[MemoryEntry], pairs: list[tuple[str, str]],
) -> tuple[list[MemoryEntry], int]:
    """Write `old superseded_by new` edges (R13). The suppressive edge consolidation
    is allowed to seed — detection + guards live in similarity.supersede_pairs; this
    only applies the verdict. Both endpoints must exist; idempotent (with_relation
    dedups). Recall then suppresses the old entry whenever the new one is eligible."""
    ids = {e.id for e in entries}
    edges: dict[str, str] = {old: new for old, new in pairs if old in ids and new in ids}
    out: list[MemoryEntry] = []
    count = 0
    for e in entries:
        new = edges.get(e.id)
        if new is not None:
            linked = e.with_relation(SUPERSEDED_BY, new)
            if linked is not e:
                count += 1
            out.append(linked)
        else:
            out.append(e)
    return out, count


def consolidate(
    entries: list[MemoryEntry],
    *,
    today: date | None = None,
    cfg: ConsolidationConfig | None = None,
    effectiveness: dict[str, int] | None = None,
    supersedes: list[tuple[str, str]] | None = None,
) -> ConsolidationResult:
    """merge → supersede → promote → weaken-ineffective → archive-stale. Pure; caller
    saves kept + appends archived (and consumes the effectiveness misses it passed)."""
    today = today or date.today()
    cfg = cfg or ConsolidationConfig()

    merged, merged_count = merge_duplicates(entries)

    # seed the suppressive supersede edges BEFORE promote/archive — a retired lesson
    # is then suppressed at recall, stops getting bumped, and decays out on its own.
    superseded_count = 0
    if supersedes:
        merged, superseded_count = apply_supersedes(merged, supersedes)

    promoted_count = 0
    promoted: list[MemoryEntry] = []
    for e in merged:
        p = promote(e, cfg)
        if p != e:
            promoted_count += 1
        promoted.append(p)

    weakened_count = 0
    if effectiveness:
        # before the archive sweep: a weakened entry that drops below the protect
        # bar becomes archivable — exactly the fate a not-working lesson deserves
        promoted, weakened_count = apply_effectiveness(promoted, effectiveness)

    kept: list[MemoryEntry] = []
    archived: list[MemoryEntry] = []
    for e in promoted:
        act = activation(e, today, cfg.activation_cfg)
        protected = e.pinned or e.confidence >= cfg.protect_confidence
        if not protected and act < cfg.archive_activation:
            archived.append(e)
            continue
        # a seed that never proved itself (recurrence 1) yet has gone stale eases its
        # confidence toward neutral — kills the "frozen 0.9 that never recurred"
        # overconfidence without touching pinned or recurrence-proven lessons.
        if (not e.pinned and e.recurrence <= 1
                and act < cfg.decay_activation and e.confidence > NEUTRAL):
            e = replace(e, confidence=decayed(e.confidence))
        kept.append(e)
    # sort by activation ONLY (never compare the entry — see [sweep-tuple-sort])
    kept.sort(key=lambda e: activation(e, today, cfg.activation_cfg), reverse=True)
    return ConsolidationResult(kept, archived, merged_count, promoted_count,
                               weakened_count, superseded_count)


# --- opportunistic trigger (the "async" in the async dream pass) ---

_MARKER = ".last-consolidate"
_DREAM_CONFIG = "dream.json"
AUTO_INTERVAL_DAYS = 7
SESSION = 0  # interval_days value meaning "every session boundary"


def dream_interval() -> int:
    """User-chosen dream cadence in days (0 = every session boundary).

    Read from <global>/dream.json; missing/garbled → AUTO_INTERVAL_DAYS. The
    cadence is a user preference, not code — survives upgrades, syncs nowhere."""
    import json

    from portaw.memory import store

    try:
        raw = json.loads((store.global_dir() / _DREAM_CONFIG).read_text("utf-8"))
        return max(0, int(raw["interval_days"]))
    except Exception:
        return AUTO_INTERVAL_DAYS


def set_dream_interval(days: int) -> None:
    """Persist the cadence (0 = every session). Raises on an unwritable store."""
    import json

    from portaw.memory import store

    d = store.global_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / _DREAM_CONFIG).write_text(
        json.dumps({"interval_days": max(0, int(days))}), encoding="utf-8"
    )


def maybe_consolidate(
    *, interval_days: int | None = None, today: date | None = None,
) -> ConsolidationResult | None:
    """Run the dream pass at most once per cadence — the SessionStart hook calls
    this so the store actually gets consolidated (decay/archive never fired when
    the pass was manual-only). Cadence = explicit arg → dream.json → weekly
    default; 0 = every session boundary (marker check skipped). Marker-file
    mtime = last run. None = skipped or failed (a hook trigger must never raise)."""
    import time

    from portaw.memory import store

    try:
        if interval_days is None:
            interval_days = dream_interval()
        marker = store.global_dir() / _MARKER
        if interval_days > SESSION:  # every-session mode never rate-limits
            try:
                if time.time() - marker.stat().st_mtime < interval_days * 86400:
                    return None
            except OSError:
                pass  # no marker yet → first run

        # effectiveness signal: lessons whose error kept recurring after they
        # existed. Gathered OUTSIDE the lessons lock (separate file, own lock).
        misses: dict[str, int] = {}
        consumed_sigs: list[str] = []
        try:
            from portaw.memory import observations

            for r in observations.recurring_despite_lesson():
                lid = r.get("lesson_id", "")
                if lid:
                    misses[lid] = misses.get(lid, 0) + observations.linked_misses(r)
                    consumed_sigs.append(r["sig"])
        except Exception:
            misses, consumed_sigs = {}, []  # signal is optional, pass still runs

        # supersede detection runs OUTSIDE the lock (embedding is slow; a read/write
        # race only risks an edge to a just-changed id, which apply_supersedes drops).
        # Off by default — opt-in, fail-safe: embedding unavailable → no pairs.
        supersedes: list[tuple[str, str]] = []
        try:
            from portaw.memory.similarity import supersede_pairs

            supersedes = supersede_pairs(store.load_lessons())
        except Exception:
            supersedes = []

        with store.locked(store.lessons_path()):
            res = consolidate(store.load_lessons(), today=today,
                              effectiveness=misses, supersedes=supersedes)
            # archive FIRST (crash between the writes = duplicate, never loss)
            store.append_archive(res.archived)
            store.save_lessons(res.kept)
        if consumed_sigs:
            # mark the misses as consumed AFTER the save landed — a crash before
            # this re-applies the same decay next run (bounded), never loses it
            from portaw.memory import observations

            observations.consume(consumed_sigs)
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
        return res
    except Exception:
        return None
