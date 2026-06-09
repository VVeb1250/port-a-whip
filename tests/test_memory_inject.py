"""Injection tests — silence-bias, per-type threshold, budget cap (R9/R11)."""

from datetime import date

from portaw.memory.inject import (
    InjectConfig,
    approx_tokens,
    format_memory,
    memory_context,
    select,
)
from portaw.memory.retrieval import Scored
from portaw.memory.schema import MemoryEntry

TODAY = date(2026, 6, 10)


def _scored(body, base, *, etype="lesson", pinned=False, recurrence=1):
    e = MemoryEntry.new(etype, body, "global", pinned=pinned, recurrence=recurrence)
    return Scored(score=base, entry=e, relevance=base, anchor=0.0, activation=1.0, base=base)


def test_select_silent_when_empty():
    assert select([]) == []


def test_lesson_passes_low_threshold_project_needs_high():
    cfg = InjectConfig(lesson_min=0.1, project_min=0.45)
    lo_lesson = _scored("lesson note", 0.2, etype="lesson")
    lo_project = _scored("project note", 0.2, etype="project")
    out = select([lo_lesson, lo_project], cfg)
    bodies = [s.entry.body for s in out]
    assert "lesson note" in bodies and "project note" not in bodies


def test_project_passes_when_strong():
    cfg = InjectConfig(project_min=0.45)
    strong = _scored("project decision", 0.6, etype="project")
    assert [s.entry.body for s in select([strong], cfg)] == ["project decision"]


def test_pinned_injected_first_even_if_low_base():
    cfg = InjectConfig(lesson_min=0.5)
    pin = _scored("pinned universal", 0.01, pinned=True)
    normal = _scored("normal", 0.9)
    out = select([normal, pin], cfg)
    assert out[0].entry.body == "pinned universal"  # pinned first regardless of base


def test_budget_cap_truncates():
    cfg = InjectConfig(max_tokens=approx_tokens("a" * 40) + 1, lesson_min=0.0)
    big = [_scored("a" * 40, 0.9), _scored("b" * 40, 0.9)]
    assert len(select(big, cfg)) == 1  # second exceeds the token budget


def test_max_items_cap():
    cfg = InjectConfig(max_items=2, lesson_min=0.0, max_tokens=10000)
    items = [_scored(f"note {i}", 0.9) for i in range(5)]
    assert len(select(items, cfg)) == 2


def test_format_empty_is_empty_string():
    assert format_memory([]) == ""


def test_format_shows_body_recurrence_and_pin():
    out = format_memory([
        _scored("use py not python", 0.9, pinned=True, recurrence=33),
    ])
    assert "use py not python" in out and "×33" in out and "★" in out


def test_memory_context_end_to_end():
    entries = [
        MemoryEntry.new("lesson", "forgot await on async", "global",
                        trigger_terms=("async", "await"), last_seen=TODAY.isoformat()),
    ]
    txt = memory_context("my async returns a coroutine", entries, today=TODAY)
    assert "forgot await" in txt


def test_memory_context_silent_on_unrelated():
    entries = [MemoryEntry.new("lesson", "x", "global", trigger_terms=("python",))]
    assert memory_context("capital of france", entries, today=TODAY) == ""
