"""MemoryEntry schema — the one routable memory record.

Frozen + pure (no I/O — store.py owns persistence). Body is a COMPRESSED
one-liner (R8: `trigger → fix` / `decision → rationale`), mirroring the
mistakes-index format (~15 tokens carries a whole lesson); full detail lives in
a cold-tier md file referenced by `detail_ref`. The content-hash `id` makes
cross-project dedup free (same mistake from two repos → same id → one entry).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, replace

# applicability tags (lessons): how widely a lesson is eligible to fire (§2.1)
UNIVERSAL = "universal"

# typed edges between entries (the "memoir" half — connection makes recall smart
# without storing more). Target = a content-hash id; edges survive cross-host sync
# because ids are stable. The set is deliberately small — these are the relations
# that change RETRIEVAL, not a general knowledge graph (that's graphify territory).
SUPERSEDED_BY = "superseded_by"  # X's fix is obsolete; Y replaces it → suppress X when Y present
CONTRADICTS = "contradicts"      # X and Y disagree → never inject the pair together; flag for curation
CAUSED_BY = "caused_by"          # X is a symptom of root-cause Y → surface Y alongside X
RELATED = "related"              # soft associative link → 1-hop fan-out on recall
_REL_TYPES = frozenset({SUPERSEDED_BY, CONTRADICTS, CAUSED_BY, RELATED})


def _norm(text: str) -> str:
    """Normalize a body for hashing/dedup: lowercase, collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def make_id(etype: str, body: str) -> str:
    """Stable short content-hash id. Same (type, normalized-body) → same id."""
    h = hashlib.sha1(f"{etype}:{_norm(body)}".encode()).hexdigest()
    return h[:12]


@dataclass(frozen=True)
class Anchors:
    """Where an entry attaches, best→coarsest (graceful degrade, §3.2).

    codegraph_nodes = precise + multi-hop, CC+indexed ONLY.
    symbols         = function/class names as strings — portable, every host.
    paths           = file paths — coarsest but most stable, greppable anywhere.
    Retrieval uses whatever exists; symbols+paths are the zero-setup floor.
    """

    codegraph_nodes: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()

    def is_empty(self) -> bool:
        return not (self.codegraph_nodes or self.symbols or self.paths)

    @classmethod
    def from_raw(cls, raw: dict | None) -> Anchors:
        raw = raw or {}
        return cls(
            codegraph_nodes=tuple(raw.get("codegraph_nodes", [])),
            symbols=tuple(raw.get("symbols", [])),
            paths=tuple(raw.get("paths", [])),
        )

    def to_raw(self) -> dict:
        return {
            "codegraph_nodes": list(self.codegraph_nodes),
            "symbols": list(self.symbols),
            "paths": list(self.paths),
        }


@dataclass(frozen=True)
class Relation:
    """A typed edge from this entry to another (by content-hash id)."""

    rel: str       # one of _REL_TYPES
    target: str    # content-hash id of the other entry

    @classmethod
    def from_raw(cls, raw: dict) -> Relation:
        return cls(rel=raw["rel"], target=raw["target"])

    def to_raw(self) -> dict:
        return {"rel": self.rel, "target": self.target}


@dataclass(frozen=True)
class MemoryEntry:
    """One memory record. `body` = compressed one-liner (R8)."""

    id: str
    type: str                       # "lesson" | "project"
    body: str                       # compressed: "trigger → fix" / "decision → rationale"
    scope: str                      # "global" | "project"
    detail_ref: str = ""            # cold-tier md pointer (expand on recall)
    trigger_terms: tuple[str, ...] = ()
    anchors: Anchors = field(default_factory=Anchors)
    applicability: str = UNIVERSAL  # lessons: universal | stack:<x> | project:<id>
    provenance: str = "estimated"   # measured|calculated|vendor-claimed|estimated|neutral
    confidence: float = 0.5         # 0..1
    recurrence: int = 1             # xN — frequency substrate for ACT-R activation
    misses: int = 0                 # error recurred AFTER this lesson existed (not working)
    last_seen: str = ""             # ISO date (recency substrate)
    source: str = "user"            # "hook" | "user" | "agent" | "sync"
    pinned: bool = False            # always-on tier (only highest-ROI universal)
    relations: tuple[Relation, ...] = ()  # typed edges to other entries (memoir half)

    @property
    def searchable_text(self) -> str:
        """Corpus the kernel ranks against (body + triggers + symbols)."""
        return " ".join(
            [self.body, " ".join(self.trigger_terms), " ".join(self.anchors.symbols)]
        ).strip()

    def targets(self, rel: str) -> tuple[str, ...]:
        """Ids this entry points to via `rel` (e.g. its superseded_by targets)."""
        return tuple(r.target for r in self.relations if r.rel == rel)

    def with_relation(self, rel: str, target: str) -> MemoryEntry:
        """Return a copy with edge (rel → target) added. Idempotent; ignores a
        self-edge and any unknown rel type (silence beats a poisoned graph)."""
        if rel not in _REL_TYPES or target == self.id:
            return self
        if any(r.rel == rel and r.target == target for r in self.relations):
            return self
        return replace(self, relations=(*self.relations, Relation(rel, target)))

    def bumped(self, *, last_seen: str) -> MemoryEntry:
        """Return a copy with recurrence+1, refreshed last_seen, and confidence
        reinforced (a confirmed recurrence is evidence the lesson is real — see
        confidence.py; saturating, so repeated hits never assert certainty)."""
        from portaw.memory.confidence import reinforced

        return replace(self, recurrence=self.recurrence + 1, last_seen=last_seen,
                       confidence=reinforced(self.confidence))

    @classmethod
    def new(cls, etype: str, body: str, scope: str, **kw) -> MemoryEntry:
        """Build with a derived content-hash id (the normal construction path)."""
        return cls(id=make_id(etype, body), type=etype, body=body, scope=scope, **kw)

    @classmethod
    def from_raw(cls, raw: dict) -> MemoryEntry:
        return cls(
            id=raw["id"],
            type=raw["type"],
            body=raw["body"],
            scope=raw["scope"],
            detail_ref=raw.get("detail_ref", ""),
            trigger_terms=tuple(raw.get("trigger_terms", [])),
            anchors=Anchors.from_raw(raw.get("anchors")),
            applicability=raw.get("applicability", UNIVERSAL),
            provenance=raw.get("provenance", "estimated"),
            confidence=float(raw.get("confidence", 0.5)),
            recurrence=int(raw.get("recurrence", 1)),
            misses=int(raw.get("misses", 0)),
            last_seen=raw.get("last_seen", ""),
            source=raw.get("source", "user"),
            pinned=bool(raw.get("pinned", False)),
            relations=tuple(
                Relation.from_raw(r) for r in raw.get("relations", [])
                if isinstance(r, dict) and r.get("rel") and r.get("target")
            ),
        )

    def to_raw(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "body": self.body,
            "scope": self.scope,
            "detail_ref": self.detail_ref,
            "trigger_terms": list(self.trigger_terms),
            "anchors": self.anchors.to_raw(),
            "applicability": self.applicability,
            "provenance": self.provenance,
            "confidence": self.confidence,
            "recurrence": self.recurrence,
            "misses": self.misses,
            "last_seen": self.last_seen,
            "source": self.source,
            "pinned": self.pinned,
            "relations": [r.to_raw() for r in self.relations],
        }
