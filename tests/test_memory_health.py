"""Metadata health report + safe trigger_terms backfill — pure, synthetic entries."""

from portaw.memory.health import backfill_trigger_terms, format_report, metadata_report
from portaw.memory.schema import Anchors, MemoryEntry


def _lesson(body, **kw):
    return MemoryEntry.new("lesson", body, "global", **kw)


def test_report_counts_missing_fields():
    entries = [
        _lesson("full one", trigger_terms=("alpha",), anchors=Anchors(symbols=("S",), paths=("p.py",))),
        _lesson("no terms no symbols here"),  # weak
        _lesson("terms only", trigger_terms=("beta",)),
    ]
    rep = metadata_report(entries)
    assert rep["lessons"] == 3
    assert rep["no_trigger_terms"] == 1  # only "no terms no symbols here"
    assert rep["no_symbols"] == 2        # that one + "terms only"
    assert rep["weak"] == 1              # only the one with neither terms nor symbols


def test_report_ignores_project_entries():
    proj = MemoryEntry.new("project", "a decision", "project")
    rep = metadata_report([proj])
    assert rep["lessons"] == 0


def test_backfill_derives_terms_from_body_only():
    e = _lesson("subprocess winerror launching npm shim")
    new, changed = backfill_trigger_terms([e])
    assert changed == 1
    terms = new[0].trigger_terms
    assert terms  # non-empty
    # derivation only: every term must come from the body (never invented)
    body_toks = set("subprocess winerror launching npm shim".split())
    assert all(t in body_toks for t in terms)


def test_backfill_leaves_entries_that_have_terms():
    e = _lesson("already has", trigger_terms=("kept",))
    new, changed = backfill_trigger_terms([e])
    assert changed == 0 and new[0].trigger_terms == ("kept",)


def test_backfill_skips_project_entries():
    proj = MemoryEntry.new("project", "decide x because y", "project")
    new, changed = backfill_trigger_terms([proj])
    assert changed == 0 and new[0].trigger_terms == ()


def test_format_report_mentions_backfill_when_applicable():
    rep = metadata_report([_lesson("no terms at all")])
    out = format_report(rep)
    assert "--backfill" in out


def test_format_report_empty_store():
    assert format_report(metadata_report([])) == "no lessons stored."
