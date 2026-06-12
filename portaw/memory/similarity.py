"""Embedding similarity over memory entries — seeds the memoir edge layer.

When a new lesson lands, a paraphrase of an existing one is invisible to the
content-hash id (different words → different id → no dedup) and often to TF-IDF
(synonyms score ~0). This module finds those semantic near-neighbours so capture
can link them with a `related` edge — turning what ICM does as fuzzy-dedup into
an EDGE-builder for our memoir layer instead (we never fold bodies; the
content-hash id is identity, so association beats mutation).

OPTIONAL + fail-safe by construction: embedding is the lazy tier-2 (kernel.embed);
if it is unavailable, `related_ids` returns [] and capture proceeds with no edges
— exactly today's behaviour. Never raises: a similarity hiccup must never block a
lesson write. Pure except the default encode path (deferred to kernel.embed).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from portaw.memory.schema import SUPERSEDED_BY, MemoryEntry

# similarity bands (MiniLM cosine). Auto-capture only ever seeds `related` — an
# additive edge (recall fan-out can ADD context, never suppress) — so the band is
# deliberately permissive at the low end and capped below near-identity at the top
# (a ~1.0 paraphrase is the same lesson; linking it adds nothing).
DEFAULT_RELATED_LO = 0.55
DEFAULT_RELATED_HI = 0.97
DEFAULT_TOP = 3

# an encoder maps texts → one L2-normalized vector each (cosine = dot product).
EncodeFn = Callable[[Sequence[str]], Sequence[Sequence[float]]]


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    # strict: a dim mismatch is a bug, not something to silently truncate — it
    # raises, the caller's try/except catches it, and we degrade to no edges.
    return sum(float(x) * float(y) for x, y in zip(a, b, strict=True))


# supersede detection (consolidation only — a SUPPRESSIVE edge, so the bar is higher
# than `related` and gated hard: see supersede_pairs). 0.90 ≈ "the same lesson, reworded".
DEFAULT_SUPERSEDE_HI = 0.90


def _resolve_encoder(encode_fn: EncodeFn | None) -> EncodeFn | None:
    """Default to the lazy tier-2 encoder; None when embedding is unavailable."""
    if encode_fn is not None:
        return encode_fn
    from portaw.kernel import embed

    return embed.encode if embed.available() else None


def _anchor_share(a: MemoryEntry, b: MemoryEntry) -> bool:
    """Do two entries point at the same code? (shared symbol or path, host-agnostic)."""
    from portaw.memory.anchors import _norm_path

    a_syms = {s.lower() for s in (*a.anchors.symbols, *a.anchors.codegraph_nodes)}
    b_syms = {s.lower() for s in (*b.anchors.symbols, *b.anchors.codegraph_nodes)}
    if a_syms & b_syms:
        return True
    a_paths = {_norm_path(p) for p in a.anchors.paths}
    b_paths = {_norm_path(p) for p in b.anchors.paths}
    return bool(a_paths & b_paths)


def supersede_pairs(
    entries: list[MemoryEntry],
    *,
    hi: float = DEFAULT_SUPERSEDE_HI,
    encode_fn: EncodeFn | None = None,
) -> list[tuple[str, str]]:
    """(old_id, new_id) pairs to link OLD `superseded_by` NEW — the suppressive edge
    consolidation is allowed to seed (capture never is, §7 / R13 poison-safety).

    A pair qualifies ONLY when every guard holds, so an auto-supersede can never
    silence a still-good lesson:
      cosine ≥ hi            (basically the same lesson reworded)
      strictly newer         (new.last_seen > old.last_seen — the tiebreak; equal → skip)
      no confidence regress  (new.confidence ≥ old.confidence)
      same target            (shared anchor OR identical applicability)
      old not pinned         (human always-on outranks any auto signal)
      not already linked      (idempotent)
    [] when embedding is unavailable or nothing qualifies. Never raises."""
    try:
        enc = _resolve_encoder(encode_fn)
        if enc is None or len(entries) < 2:
            return []
        vecs = enc([e.searchable_text for e in entries])
        pairs: list[tuple[str, str]] = []
        n = len(entries)
        for i in range(n):
            for j in range(i + 1, n):
                a, b = entries[i], entries[j]
                if _dot(vecs[i], vecs[j]) < hi:
                    continue
                old, new = _order_by_recency(a, b)
                if old is None:  # equal/missing last_seen → can't tell which is newer
                    continue
                if (
                    new.confidence < old.confidence
                    or old.pinned
                    or not (_anchor_share(old, new) or old.applicability == new.applicability)
                    or new.id in old.targets(SUPERSEDED_BY)
                ):
                    continue
                pairs.append((old.id, new.id))
        return pairs
    except Exception:
        return []


def _order_by_recency(
    a: MemoryEntry, b: MemoryEntry
) -> tuple[MemoryEntry | None, MemoryEntry | None]:
    """(old, new) by last_seen; (None, None) if equal or unknown (no safe direction)."""
    if not a.last_seen or not b.last_seen or a.last_seen == b.last_seen:
        return None, None
    return (a, b) if a.last_seen < b.last_seen else (b, a)


def related_ids(
    entry: MemoryEntry,
    others: list[MemoryEntry],
    *,
    lo: float = DEFAULT_RELATED_LO,
    hi: float = DEFAULT_RELATED_HI,
    top: int = DEFAULT_TOP,
    encode_fn: EncodeFn | None = None,
) -> list[tuple[str, float]]:
    """Ids of entries semantically near `entry` (cosine in [lo, hi)), best first.

    [] when there is nothing to compare, embedding is unavailable, or anything
    goes wrong. Vectors are already L2-normalized, so cosine is a plain dot."""
    candidates = [o for o in others if o.id != entry.id]
    if not candidates:
        return []
    try:
        if encode_fn is None:
            from portaw.kernel import embed

            if not embed.available():
                return []
            encode_fn = embed.encode
        vecs = encode_fn([entry.searchable_text, *[o.searchable_text for o in candidates]])
        q = vecs[0]
        scored = [
            (o.id, _dot(q, vecs[i + 1])) for i, o in enumerate(candidates)
        ]
        hits = [(cid, s) for cid, s in scored if lo <= s < hi]
        hits.sort(key=lambda x: -x[1])
        return hits[:top]
    except Exception:
        return []
