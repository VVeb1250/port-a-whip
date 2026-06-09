"""Seeding — project-memory v1 = ADR-harvest (§8).

Reuse what the repo already wrote: `docs/adr/*.md` are structured decision
records (1 ADR = 1 decision+rationale), so harvesting them is low-noise — exactly
the v1 lever. CLAUDE.md/README harvest is deferred to v2 (behind a confirm-gate)
because raw-dumping prose is the ETH −3%/+20% trap. Harvested entries are
project-scoped and must still pass the integrity gate (confirm) before they land.
Pure parsing; the caller persists.
"""

from __future__ import annotations

import re
from pathlib import Path

from portaw.memory.schema import Anchors, MemoryEntry

_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_DECISION = re.compile(r"^#{1,3}\s*decision\s*$", re.IGNORECASE | re.MULTILINE)


def _title(text: str, fallback: str) -> str:
    m = _H1.search(text)
    title = m.group(1).strip() if m else fallback
    # strip a leading "ADR-001:" / "1." style prefix
    return re.sub(r"^(adr[-\s]?\d+[:.]?\s*|\d+[.)]\s*)", "", title, flags=re.IGNORECASE).strip()


def _decision_summary(text: str) -> str:
    """First non-empty line under a '## Decision' heading, else first body paragraph."""
    m = _DECISION.search(text)
    region = text[m.end():] if m else text
    for line in region.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            return s
    return ""


def harvest_adr_file(path: Path) -> MemoryEntry | None:
    """One ADR file → one project lesson-of-record. None if it has no usable title."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    title = _title(text, path.stem)
    if not title:
        return None
    summary = _decision_summary(text)
    body = f"{title} → {summary}" if summary else title
    body = body[:200]  # keep it a one-liner (R8)
    return MemoryEntry.new(
        "project", body, "project",
        applicability="project:harvested",
        anchors=Anchors(paths=(str(path.as_posix()),)),
        provenance="estimated",
        source="agent",
    )


def harvest_adrs(adr_dir: Path | str) -> list[MemoryEntry]:
    """Harvest every `*.md` under an ADR directory. Empty list if the dir is absent."""
    d = Path(adr_dir)
    if not d.is_dir():
        return []
    out: list[MemoryEntry] = []
    for p in sorted(d.glob("*.md")):
        if p.name.lower() in {"readme.md", "index.md", "template.md"}:
            continue
        entry = harvest_adr_file(p)
        if entry is not None:
            out.append(entry)
    return out


def default_adr_dir(root: Path | str | None = None) -> Path:
    base = Path(root) if root is not None else Path.cwd()
    return base / "docs" / "adr"
