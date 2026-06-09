"""Retrieval + anchor tests — pure, synthetic entries, fixed clock."""

from datetime import date

from portaw.memory.anchors import AnchorQuery, overlap
from portaw.memory.retrieval import (
    RetrievalConfig,
    RetrievalContext,
    activation,
    is_eligible,
    recall,
)
from portaw.memory.schema import Anchors, MemoryEntry

TODAY = date(2026, 6, 10)


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    kw.setdefault("last_seen", TODAY.isoformat())
    return MemoryEntry.new("lesson", body, **kw)


# --- anchors ---

def test_overlap_symbol_exact():
    a = Anchors(symbols=("fetch_user",))
    assert overlap(a, AnchorQuery(symbols=("fetch_user",))) == 1.0
    assert overlap(a, AnchorQuery(symbols=("other",))) == 0.0


def test_overlap_path_suffix_match():
    a = Anchors(paths=("a/b.py",))
    assert overlap(a, AnchorQuery(paths=("repo/a/b.py",))) == 1.0


def test_overlap_empty_anchors_is_zero():
    assert overlap(Anchors(), AnchorQuery(symbols=("x",))) == 0.0


def test_anchor_query_as_text_folds_symbols_and_paths():
    q = AnchorQuery(symbols=("run_build",), paths=("x/y.py",))
    assert "run_build" in q.as_text() and "x/y.py" in q.as_text()


# --- applicability ---

def test_universal_lesson_always_eligible():
    e = _lesson("x", applicability="universal")
    assert is_eligible(e, RetrievalContext())


def test_stack_lesson_eligible_only_for_matching_stack():
    e = _lesson("x", applicability="stack:windows")
    assert is_eligible(e, RetrievalContext(stacks=frozenset({"windows"})))
    assert not is_eligible(e, RetrievalContext(stacks=frozenset({"linux"})))


def test_project_lesson_eligible_only_in_its_project():
    e = _lesson("x", applicability="project:paw")
    assert is_eligible(e, RetrievalContext(project_id="paw"))
    assert not is_eligible(e, RetrievalContext(project_id="other"))


# --- activation ---

def test_activation_rises_with_recurrence():
    lo = _lesson("a", recurrence=1)
    hi = _lesson("b", recurrence=20)
    cfg = RetrievalConfig()
    assert activation(hi, TODAY, cfg) > activation(lo, TODAY, cfg)


def test_activation_decays_with_age():
    fresh = _lesson("a", last_seen="2026-06-10")
    stale = _lesson("b", last_seen="2026-01-01")
    cfg = RetrievalConfig()
    assert activation(fresh, TODAY, cfg) > activation(stale, TODAY, cfg)


# --- recall ---

def test_recall_matches_relevant_lesson():
    entries = [
        _lesson("forgot await on async call", trigger_terms=("async", "await")),
        _lesson("use py not python on windows", trigger_terms=("python",)),
    ]
    hits = recall("my async function returns a coroutine", entries, today=TODAY)
    assert hits and hits[0].entry.body.startswith("forgot await")


def test_recall_silent_on_unrelated():
    entries = [_lesson("use py not python", trigger_terms=("python",))]
    assert recall("the capital of france", entries, today=TODAY) == []


def test_recall_anchor_surfaces_lexically_silent_entry():
    # body shares NO word with the prompt, but the edit-target symbol matches.
    entries = [_lesson("never mutate in place here", anchors=Anchors(symbols=("apply_patch",)))]
    q = AnchorQuery(symbols=("apply_patch",))
    hits = recall("refactor this", entries, query=q, today=TODAY)
    assert hits and hits[0].entry.body.startswith("never mutate")
    assert hits[0].anchor == 1.0


def test_recall_excludes_ineligible_by_applicability():
    entries = [_lesson("django thing", applicability="stack:django", trigger_terms=("django",))]
    hits = recall("django migration issue", entries,
                  ctx=RetrievalContext(stacks=frozenset({"react"})), today=TODAY)
    assert hits == []


def test_recall_low_confidence_sinks_below_high():
    entries = [
        _lesson("await fix high", trigger_terms=("await",), confidence=0.95),
        _lesson("await fix low", trigger_terms=("await",), confidence=0.1),
    ]
    hits = recall("await problem", entries, today=TODAY)
    assert [h.entry.confidence for h in hits] == [0.95, 0.1]
