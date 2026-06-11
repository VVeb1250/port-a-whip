"""Anchor matching — the zero-setup structural half of retrieval (§3).

The retrieval trigger is "the agent is editing file F / symbol S" — F and S are
already in context, so matching memory anchors against the current edit target
needs no index and no init token. path + symbol are the portable floor;
codegraph nodes (when present) fold in as extra symbols. Pure, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

from portaw.memory.schema import Anchors


@dataclass(frozen=True)
class AnchorQuery:
    """What the agent is touching right now (the retrieval trigger)."""

    paths: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()

    @classmethod
    def from_context(
        cls, paths: list[str] | None = None, symbols: list[str] | None = None
    ) -> AnchorQuery:
        return cls(paths=tuple(paths or ()), symbols=tuple(symbols or ()))

    def as_text(self) -> str:
        """Fold the edit-target into routing text so the kernel sees its symbols.

        This is what lets a lesson anchored on `fetch_user` surface when the agent
        edits `fetch_user`, even if the prompt never names it lexically.
        """
        return " ".join([*self.symbols, *self.paths]).strip()

    def is_empty(self) -> bool:
        return not (self.paths or self.symbols)


def _norm_path(p: str) -> str:
    """Compare paths host-agnostically (slash + case folding for Windows)."""
    return p.replace("\\", "/").lower().strip().lstrip("./")


def overlap(anchors: Anchors, query: AnchorQuery) -> float:
    """Structural match ∈ [0,1]: did the agent touch what this entry anchors to?

    symbols + codegraph_nodes (treated as symbols) match by exact token; paths
    match by suffix (a stored `a/b.py` hits an edit target `repo/a/b.py`). Returns
    the fraction of the entry's anchors that the query satisfies (0 if no anchors).
    """
    entry_syms = {s.lower() for s in (*anchors.symbols, *anchors.codegraph_nodes)}
    entry_paths = {_norm_path(p) for p in anchors.paths}
    if not entry_syms and not entry_paths:
        return 0.0

    q_syms = {s.lower() for s in query.symbols}
    q_paths = {_norm_path(p) for p in query.paths}

    hits = 0
    total = len(entry_syms) + len(entry_paths)
    hits += len(entry_syms & q_syms)
    for ep in entry_paths:
        if any(_path_match(ep, qp) for qp in q_paths):
            hits += 1
    return hits / total if total else 0.0


def _path_match(a: str, b: str) -> bool:
    """Suffix match at a path-component boundary only — `a/b.py` hits `repo/a/b.py`,
    but `b.py` must NOT hit `ab.py` (a bare suffix would false-positive)."""
    return a == b or a.endswith("/" + b) or b.endswith("/" + a)
