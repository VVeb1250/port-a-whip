"""Capability registry — turn curated sets into routable Capabilities.

L2 corpus builder. MVP: one Capability per set (ctype="set"); its searchable
text = description + trigger_terms + each tool's purpose, so both lexical TF-IDF
and the curated intent layer fire. trigger_terms double as the intent_map
(phrase → set) — they ARE the "what+when" routing signal (spec §9).

Later (Phase 3): emit per-capability rows for the other 3 types (skill /
instruction / lesson) so the router ranks across all four. Sets first.
"""

from __future__ import annotations

from portaw.kernel.ranking import Capability
from portaw.sets.loader import load_all

_MIN_INTENT_LEN = 4  # short trigger terms ("api", "cve") → too noisy as substrings


def build_capabilities() -> list[Capability]:
    """One Capability per curated set."""
    caps: list[Capability] = []
    for s in load_all():
        purposes = " ".join(
            t.get("purpose", "") for t in (*s.mcp, *s.non_mcp)
        )
        text = " ".join([s.description, " ".join(s.trigger_terms), purposes]).strip()
        caps.append(
            Capability(
                name=s.name,
                text=text,
                ctype="set",
                invoke=f"portaw install {s.name}",
                desc=s.description[:90],
            )
        )
    return caps


def build_intent_map() -> dict[str, list[str]]:
    """trigger_terms → set name (substring intent layer). Skips ultra-short terms."""
    imap: dict[str, list[str]] = {}
    for s in load_all():
        for term in s.trigger_terms:
            t = term.lower().strip()
            if len(t) >= _MIN_INTENT_LEN:
                imap.setdefault(t, []).append(s.name)
    return imap
