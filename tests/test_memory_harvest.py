"""mistakes-index.md → lessons harvest tests — tmp_path, no network."""

from portaw.memory.harvest import (
    default_mistakes_file,
    harvest_mistakes_file,
    parse_line,
)

_SAMPLE = """# Mistakes Index

> Auto-loaded every session.

## CODING

### Python
- [HIGH] [py-await] forget `await` in async → got coroutine object → add `await` / `asyncio.gather()` (x1, 2026-05-29)

### General
(none yet)

## COMMANDS / SHELL (Windows)

- [HIGH] [ps-null-coalesce] `??` in PowerShell → parse error → use `if/else` (x4, 2026-06-10)
- [MED] [bash-wsl] PS hook calls bash → WSL mangles path → git-bash full path (x1, 2026-05-29) →detail

## WORKFLOW

- [MED] [graphify-save] `--update` merge then no save → loads stale graph → call `to_json()` after merge (x1, 2026-05-29) →detail

---
Detail → mistakes-detail.md | Archive → mistakes-archive.md
"""


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_parses_all_bullets_skips_noise(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    out = harvest_mistakes_file(p, today="2026-06-10")
    # 4 bullets; the "(none yet)" line and footer are NOT bullets
    assert len(out) == 4
    assert all(e.type == "lesson" and e.scope == "global" for e in out)


def test_severity_maps_to_confidence(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    assert by_term["py-await"].confidence == 0.9      # HIGH
    assert by_term["bash-wsl"].confidence == 0.7       # MED


def test_meta_recurrence_and_date_parsed(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    assert by_term["ps-null-coalesce"].recurrence == 4
    assert by_term["ps-null-coalesce"].last_seen == "2026-06-10"


def test_meta_and_detail_marker_stripped_from_body(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    body = by_term["bash-wsl"].body
    assert "→detail" not in body and "(x1" not in body
    assert body.endswith("git-bash full path")


def test_applicability_python_section_is_stack(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    assert by_term["py-await"].applicability == "stack:python"


def test_applicability_shell_section_is_universal(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    # env keywords (powershell) AND a COMMANDS/SHELL section → universal
    assert by_term["ps-null-coalesce"].applicability == "universal"


def test_applicability_workflow_falls_back_to_project(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    assert by_term["graphify-save"].applicability == "project:curated"


def test_detail_ref_points_at_sibling_when_present(tmp_path):
    _write(tmp_path / "mistakes-detail.md", "## [bash-wsl]\nfull story\n")
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    assert by_term["bash-wsl"].detail_ref.endswith("mistakes-detail.md#bash-wsl")
    # a bullet with no →detail marker gets no detail_ref
    assert by_term["py-await"].detail_ref == ""


def test_code_spans_become_trigger_terms_and_symbols(tmp_path):
    p = tmp_path / "mistakes-index.md"
    _write(p, _SAMPLE)
    by_term = {e.trigger_terms[0]: e for e in harvest_mistakes_file(p, today="2026-06-10")}
    e = by_term["py-await"]
    assert "await" in e.trigger_terms
    assert "await" in e.anchors.symbols


def test_same_body_dedups_to_same_id(tmp_path):
    # id is a content-hash of the body → two indexes with the same lesson collide
    e1 = parse_line("- [HIGH] [a] x → y (x1, 2026-01-01)", "Python", "p", "2026-01-01")
    e2 = parse_line("- [LOW] [b] x → y (x9, 2026-02-02)", "Python", "p", "2026-02-02")
    assert e1.id == e2.id  # same normalized body → free cross-source dedup


def test_absent_file_returns_empty(tmp_path):
    assert harvest_mistakes_file(tmp_path / "nope.md") == []


def test_non_bullet_line_returns_none():
    assert parse_line("just prose", "X", "p", "2026-01-01") is None
    assert parse_line("- not a tagged bullet", "X", "p", "2026-01-01") is None


def test_default_path_under_claude_rules(tmp_path):
    assert default_mistakes_file(tmp_path).as_posix().endswith(".claude/rules/mistakes-index.md")
