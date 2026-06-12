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
from portaw.memory.schema import (
    CAUSED_BY,
    CONTRADICTS,
    SUPERSEDED_BY,
    Anchors,
    MemoryEntry,
)

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


# --- typed edges (memoir half) ---

def test_recall_suppresses_superseded_when_replacement_present():
    new = _lesson("use py launcher on windows", trigger_terms=("python", "windows", "py"))
    old = _lesson(
        "use python3 on windows", trigger_terms=("python", "windows")
    ).with_relation(SUPERSEDED_BY, new.id)
    ids = [h.entry.id for h in recall("python on windows", [old, new], today=TODAY)]
    assert new.id in ids and old.id not in ids  # stale lesson retired by its replacement


def test_recall_keeps_superseded_when_replacement_ineligible():
    # replacement is scoped to a stack absent from context → don't silently hide the old one
    new = _lesson("use py launcher", applicability="stack:django", trigger_terms=("python", "py"))
    old = _lesson("use python3", trigger_terms=("python",)).with_relation(SUPERSEDED_BY, new.id)
    hits = recall(
        "python problem", [old, new],
        ctx=RetrievalContext(stacks=frozenset({"react"})), today=TODAY,
    )
    assert old.id in [h.entry.id for h in hits]


def test_recall_drops_weaker_side_of_contradiction():
    hi = _lesson("await fix", trigger_terms=("await",), confidence=0.95)
    lo = _lesson(
        "await opposite", trigger_terms=("await",), confidence=0.1
    ).with_relation(CONTRADICTS, hi.id)
    ids = [h.entry.id for h in recall("await problem", [hi, lo], today=TODAY)]
    assert hi.id in ids and lo.id not in ids


def test_recall_fans_out_to_related_root_cause():
    # the cause shares no word with the prompt → it can only ride in via the edge
    cause = _lesson("rebuild native module after node upgrade", trigger_terms=("node", "rebuild"))
    symptom = _lesson(
        "segfault on import", trigger_terms=("segfault", "import")
    ).with_relation(CAUSED_BY, cause.id)
    ids = [h.entry.id for h in recall("segfault on import", [symptom, cause], today=TODAY)]
    assert symptom.id in ids and cause.id in ids       # root cause pulled in 1-hop
    assert ids.index(symptom.id) < ids.index(cause.id)  # and it rides below its parent
