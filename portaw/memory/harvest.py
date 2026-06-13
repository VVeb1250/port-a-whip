"""Harvest a curated mistakes-index.md into global lessons (§13, the reflection path).

The 2026-06-10 dogfood finding: the Bash failure→fix detector (detect.py) yields ~0
signals on real transcripts — real corrections are cross-tool, far apart, or one-off
blobs. So the high-value capture path is the human-CURATED mistakes index: already
compressed (`trigger → fix`), severity-rated, recurrence-counted, cross-project. This
harvester parses that index into lesson MemoryEntries — the analog of seed.py's ADR
harvest, but it produces global *lessons* (not project-memory). Pure parsing; the
caller persists and may re-key by id to stay idempotent across re-runs.

Index line grammar (mirrors the author's mistakes-index.md):

    - [HIGH] [py-await] ลืม `await` ใน async → ได้ coroutine → เพิ่ม `await` (x1, 2026-05-29)
    - [MED] [bash-wsl] PS hook → WSL ตี path ผิด → git-bash full path (x4, 2026-06-10) →detail
      ^sev    ^id      ^------------------ body (trigger → fix) ----------------^  ^meta    ^detail
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from portaw.kernel.ranking import tokenize
from portaw.memory.capture import classify_text
from portaw.memory.schema import Anchors, MemoryEntry

# severity tag → injection confidence (HIGH = proven-painful, LOW = minor note).
# Honest by construction: a LOW note must still earn universal trust via recurrence.
_SEV_CONFIDENCE = {"HIGH": 0.9, "MED": 0.7, "LOW": 0.5}

# a section header naming a language/framework → stack:<x> applicability
_STACK_SECTIONS = {
    "python", "golang", "rust", "kotlin", "swift", "flutter", "dart", "react",
    "vue", "angular", "svelte", "django", "fastapi", "flask", "rails", "spring",
    "typescript", "javascript", "node", "nextjs",
}
# a section whose name implies env/shell-level → recurs across every project → universal
_ENV_SECTION_RE = re.compile(r"command|shell|windows|bash|powershell|terminal", re.IGNORECASE)

_HEADER = re.compile(r"^#{2,4}\s+(.+?)\s*$")
_BULLET = re.compile(
    r"^-\s*\[(?P<sev>HIGH|MED|LOW)\]\s*\[(?P<id>[A-Za-z0-9_-]+)\]\s*(?P<text>.+)$"
)
_META = re.compile(r"\s*\(x(?P<n>\d+)(?:\s*,\s*(?P<date>[0-9-]+))?\)\s*$")
_DETAIL = re.compile(r"\s*→\s*detail\s*$", re.IGNORECASE)
_CODE = re.compile(r"`([^`]+)`")


def _section_stack(section: str) -> str:
    """A language/framework section name → its stack key (else '')."""
    for tok in tokenize(section):
        if tok in _STACK_SECTIONS:
            return tok
    return ""


def _applicability(section: str, body: str, project_id: str | None) -> str:
    """Map (section, body) → an applicability tag (§2.1). Section header wins; then
    the body keyword heuristic; env/shell → universal. An unclassified lesson is
    project-scoped ONLY when the caller named a real project — otherwise it falls to
    `universal`. A placeholder project_id (the old `curated` default) would orphan the
    lesson forever: no live host_context ever derives that name, so it could never
    surface. Universal is the safe default — the trust gate still withholds an
    unproven one, so it can't spam, but it CAN surface once it earns confidence."""
    stack = _section_stack(section)
    if stack:
        return f"stack:{stack}"
    env_kw, stack_kw = classify_text(body)
    if stack_kw:
        return f"stack:{stack_kw}"
    if env_kw or _ENV_SECTION_RE.search(section):
        return "universal"
    return f"project:{project_id}" if project_id else "universal"


def parse_line(
    line: str, section: str, project_id: str | None, today: str, detail_ref_base: str = ""
) -> MemoryEntry | None:
    """One index bullet → one lesson MemoryEntry. None if the line isn't a mistake bullet."""
    m = _BULLET.match(line.strip())
    if not m:
        return None
    sev, mid, text = m.group("sev"), m.group("id"), m.group("text").strip()

    has_detail = bool(_DETAIL.search(text))
    text = _DETAIL.sub("", text).strip()          # strip trailing "→detail" marker first
    recurrence, last_seen = 1, today
    meta = _META.search(text)
    if meta:
        recurrence = int(meta.group("n"))
        last_seen = meta.group("date") or today
        text = text[: meta.start()].strip()        # then strip "(xN, date)" meta

    body = text[:200]                              # R8: keep it a one-liner
    if not body:
        return None

    codes = _CODE.findall(text)
    terms = tuple(
        dict.fromkeys([mid, *[c for c in codes if 2 < len(c) < 20], *tokenize(body)])
    )[:8]
    symbols = tuple(c for c in codes if " " not in c and 2 < len(c) < 30)[:3]
    detail_ref = f"{detail_ref_base}#{mid}" if has_detail and detail_ref_base else ""

    return MemoryEntry.new(
        "lesson", body, "global",
        detail_ref=detail_ref,
        trigger_terms=terms,
        anchors=Anchors(symbols=symbols),
        applicability=_applicability(section, body, project_id),
        provenance="estimated",                    # curated reflection, honest floor
        confidence=_SEV_CONFIDENCE[sev],
        recurrence=recurrence,
        last_seen=last_seen,
        source="user",                             # the human-curated index = a vouch
    )


def harvest_mistakes_file(
    path: Path | str,
    *,
    project_id: str | None = None,
    today: str | None = None,
    detail_ref_base: str | None = None,
) -> list[MemoryEntry]:
    """Parse a mistakes-index.md into lessons. Empty list if the file is absent/empty.

    detail_ref_base: base for `→detail` pointers; defaults to a sibling
    `mistakes-detail.md` when one exists (so a recalled lesson can expand)."""
    p = Path(path)
    if not p.is_file():
        return []
    today = today or date.today().isoformat()
    if detail_ref_base is None:
        sibling = p.with_name("mistakes-detail.md")
        detail_ref_base = sibling.as_posix() if sibling.exists() else ""

    section = ""
    out: list[MemoryEntry] = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        h = _HEADER.match(line)
        if h:
            section = h.group(1).strip()
            continue
        entry = parse_line(line, section, project_id, today, detail_ref_base)
        if entry is not None:
            out.append(entry)
    return out


def default_mistakes_file(root: Path | str | None = None) -> Path:
    """The author's curated gold source. Post single-source migration (2026-06-11)
    it lives OUTSIDE the auto-loaded rules dir; the old location is the fallback
    so a pre-migration setup keeps working."""
    base = Path(root) if root is not None else Path.home()
    new = base / ".claude" / "mistakes" / "mistakes-index.md"
    old = base / ".claude" / "rules" / "mistakes-index.md"
    return new if new.exists() or not old.exists() else old
