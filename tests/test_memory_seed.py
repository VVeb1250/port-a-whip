"""ADR-harvest seeding tests — tmp_path, no network."""

from portaw.memory.seed import harvest_adr_file, harvest_adrs


def _write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def test_harvest_adr_parses_title_and_decision(tmp_path):
    p = tmp_path / "0001-use-postgres.md"
    _write(p, "# ADR-001: Use PostgreSQL\n\n## Decision\nWe use Postgres for ACID guarantees.\n")
    e = harvest_adr_file(p)
    assert e is not None
    assert e.body == "Use PostgreSQL → We use Postgres for ACID guarantees."
    assert e.type == "project" and e.scope == "project"
    assert e.anchors.paths and e.anchors.paths[0].endswith("0001-use-postgres.md")


def test_harvest_strips_adr_number_prefix(tmp_path):
    p = tmp_path / "adr.md"
    _write(p, "# 12. Adopt event sourcing\n\nsome context line\n")
    e = harvest_adr_file(p)
    assert e.body.startswith("Adopt event sourcing")


def test_harvest_adrs_skips_template_and_readme(tmp_path):
    _write(tmp_path / "README.md", "# Readme\n")
    _write(tmp_path / "template.md", "# Template\n")
    _write(tmp_path / "0002-real.md", "# Real decision\n\n## Decision\ndo the thing\n")
    out = harvest_adrs(tmp_path)
    assert [e.body for e in out] == ["Real decision → do the thing"]


def test_harvest_absent_dir_returns_empty(tmp_path):
    assert harvest_adrs(tmp_path / "nope") == []
