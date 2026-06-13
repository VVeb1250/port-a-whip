"""Metadata health — recall is f(metadata), so empty fields = quietly weak recall.

Old/auto-captured entries often carry empty trigger_terms or anchors. The body is
always in ``searchable_text`` so such an entry isn't invisible, but it ranks on the
body alone — no symbol anchor (kills structural overlap), no curated terms (weaker
lexical signal). This module REPORTS that unevenness (observability) and offers a
SAFE backfill: derive trigger_terms from the entry's own body. Derivation only —
it never invents a term the body doesn't contain, so it can't poison recall.
"""

from __future__ import annotations

from dataclasses import replace

from portaw.kernel.ranking import tokenize
from portaw.memory.schema import MemoryEntry

_MAX_TERMS = 8


def metadata_report(entries: list[MemoryEntry]) -> dict:
    """Counts of entries missing each recall-feeding field (+ the weak-entry ids)."""
    lessons = [e for e in entries if e.type == "lesson"]
    no_terms = [e for e in lessons if not e.trigger_terms]
    no_symbols = [e for e in lessons if not e.anchors.symbols]
    no_paths = [e for e in lessons if not e.anchors.paths]
    # "weak" = a lesson the kernel can only see through its body (no terms, no symbols)
    weak = [e for e in lessons if not e.trigger_terms and not e.anchors.symbols]
    return {
        "lessons": len(lessons),
        "no_trigger_terms": len(no_terms),
        "no_symbols": len(no_symbols),
        "no_paths": len(no_paths),
        "weak": len(weak),
        "weak_ids": [e.id for e in weak],
        "backfillable": [e.id for e in no_terms],  # body → terms is always possible
    }


def backfill_trigger_terms(entries: list[MemoryEntry]) -> tuple[list[MemoryEntry], int]:
    """Derive trigger_terms from the body for lessons that have none. Returns
    (new_entries, changed_count). Pure — caller persists. Derivation only: terms
    come straight from the body's own tokens, never invented."""
    out: list[MemoryEntry] = []
    changed = 0
    for e in entries:
        if e.type == "lesson" and not e.trigger_terms:
            terms = tuple(dict.fromkeys(tokenize(e.body)))[:_MAX_TERMS]
            if terms:
                e = replace(e, trigger_terms=terms)
                changed += 1
        out.append(e)
    return out, changed


def format_report(rep: dict) -> str:
    if not rep["lessons"]:
        return "no lessons stored."
    lines = [
        f"metadata health — {rep['lessons']} lessons:",
        f"  missing trigger_terms : {rep['no_trigger_terms']}  (backfillable from body)",
        f"  missing symbols       : {rep['no_symbols']}",
        f"  missing paths         : {rep['no_paths']}",
        f"  WEAK (no terms+symbols, body-only recall): {rep['weak']}",
    ]
    if rep["backfillable"]:
        lines.append("  → `portaw memory health --backfill` fills trigger_terms from each body.")
    return "\n".join(lines)
