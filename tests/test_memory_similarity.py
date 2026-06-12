"""Similarity tests — injected encoder (unit vectors, no ONNX), pure."""

from portaw.memory.schema import Anchors, MemoryEntry
from portaw.memory.similarity import related_ids, supersede_pairs


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    return MemoryEntry.new("lesson", body, **kw)


# unit vectors so dot == cosine; second component = sqrt(1 - x^2)
_E = [1.0, 0.0]
_NEAR = [0.9, 0.4358899]    # cos 0.90 — in band
_MID = [0.6, 0.8]           # cos 0.60 — in band
_FAR = [0.2, 0.9797959]     # cos 0.20 — below lo
_TWIN = [0.99, 0.1410674]   # cos 0.99 — above hi (same lesson, no edge)


def test_related_ids_returns_in_band_neighbours_best_first():
    e, a, b, c = _lesson("new"), _lesson("a"), _lesson("b"), _lesson("c")
    def enc(_):
        return [_E, _NEAR, _MID, _FAR]  # order = [e, a, b, c]
    hits = related_ids(e, [a, b, c], encode_fn=enc)
    assert [cid for cid, _ in hits] == [a.id, b.id]   # c (0.20) below lo, dropped
    assert hits[0][1] > hits[1][1]                    # best (a) first


def test_related_ids_excludes_near_identical_above_hi():
    e, twin = _lesson("new"), _lesson("twin")
    def enc(_):
        return [_E, _TWIN]
    assert related_ids(e, [twin], encode_fn=enc) == []  # 0.99 ≥ hi → same lesson


def test_related_ids_empty_when_no_candidates():
    e = _lesson("alone")
    assert related_ids(e, [], encode_fn=lambda t: [_E]) == []


def test_related_ids_skips_self():
    e = _lesson("x")
    def enc(_):
        return [_E, _E]
    assert related_ids(e, [e], encode_fn=enc) == []  # same id filtered before encode


def test_related_ids_failsafe_on_encoder_error():
    e, a = _lesson("new"), _lesson("a")
    def boom(texts):
        raise RuntimeError("onnx exploded")
    assert related_ids(e, [a], encode_fn=boom) == []  # never raises → no edges


def test_related_ids_respects_top_cap():
    e = _lesson("new")
    others = [_lesson(f"o{i}") for i in range(5)]
    def enc(_):
        return [_E] + [[0.8, 0.6]] * 5  # all cos 0.80, in band
    assert len(related_ids(e, others, top=2, encode_fn=enc)) == 2


# --- supersede detection (consolidation-only suppressive edge) ---

_VHI = [0.95, 0.3122499]  # cos 0.95 to _E — above supersede hi


def test_supersede_pairs_links_old_to_newer_confident_twin():
    old = _lesson("use python3 on windows", applicability="universal",
                  last_seen="2026-01-01", confidence=0.6)
    new = _lesson("use py launcher on windows", applicability="universal",
                  last_seen="2026-06-10", confidence=0.7)
    def enc(_):
        return [_E, _VHI]  # order = [old, new], cos 0.95
    assert supersede_pairs([old, new], encode_fn=enc) == [(old.id, new.id)]


def test_supersede_pairs_skips_when_new_less_confident():
    old = _lesson("a", applicability="universal", last_seen="2026-01-01", confidence=0.9)
    new = _lesson("b", applicability="universal", last_seen="2026-06-10", confidence=0.4)
    def enc(_):
        return [_E, _VHI]
    assert supersede_pairs([old, new], encode_fn=enc) == []  # confidence regress → no retire


def test_supersede_pairs_skips_pinned_old():
    old = _lesson("a", applicability="universal", last_seen="2026-01-01", pinned=True)
    new = _lesson("b", applicability="universal", last_seen="2026-06-10", confidence=0.9)
    def enc(_):
        return [_E, _VHI]
    assert supersede_pairs([old, new], encode_fn=enc) == []  # human always-on protected


def test_supersede_pairs_needs_shared_anchor_or_same_applicability():
    old = _lesson("a", applicability="stack:react", last_seen="2026-01-01",
                  anchors=Anchors(symbols=("foo",)))
    new = _lesson("b", applicability="stack:django", last_seen="2026-06-10",
                  anchors=Anchors(symbols=("bar",)), confidence=0.9)
    def enc(_):
        return [_E, _VHI]
    assert supersede_pairs([old, new], encode_fn=enc) == []  # unrelated targets → no retire


def test_supersede_pairs_shared_anchor_qualifies_across_scopes():
    old = _lesson("a", applicability="stack:react", last_seen="2026-01-01",
                  anchors=Anchors(symbols=("fetch_user",)))
    new = _lesson("b", applicability="stack:django", last_seen="2026-06-10",
                  anchors=Anchors(symbols=("fetch_user",)), confidence=0.9)
    def enc(_):
        return [_E, _VHI]
    assert supersede_pairs([old, new], encode_fn=enc) == [(old.id, new.id)]


def test_supersede_pairs_skips_equal_last_seen():
    a = _lesson("a", applicability="universal", last_seen="2026-06-10")
    b = _lesson("b", applicability="universal", last_seen="2026-06-10")
    def enc(_):
        return [_E, _VHI]
    assert supersede_pairs([a, b], encode_fn=enc) == []  # no safe newer direction


def test_supersede_pairs_skips_below_hi():
    old = _lesson("a", applicability="universal", last_seen="2026-01-01")
    new = _lesson("b", applicability="universal", last_seen="2026-06-10", confidence=0.9)
    def enc(_):
        return [_E, [0.8, 0.6]]  # cos 0.80 < hi 0.90
    assert supersede_pairs([old, new], encode_fn=enc) == []


def test_supersede_pairs_failsafe_on_encoder_error():
    a = _lesson("a", last_seen="2026-01-01")
    b = _lesson("b", last_seen="2026-06-10")
    def boom(texts):
        raise RuntimeError("nope")
    assert supersede_pairs([a, b], encode_fn=boom) == []
