"""Capture + integrity-gate tests — pure, store isolated via monkeypatch."""

from portaw.memory import store
from portaw.memory.capture import (
    FailureSignal,
    capture,
    classify_text,
    infer_applicability,
    to_lesson,
)
from portaw.memory.gate import GateConfig, accepts, enters_hot, trusted
from portaw.memory.schema import RELATED, MemoryEntry

TODAY = "2026-06-10"


# --- gate ---

def test_project_write_needs_confirm():
    e = MemoryEntry.new("project", "decision", "project", applicability="project:paw")
    assert not accepts(e, confirmed=False).ok
    assert accepts(e, confirmed=True).ok


def test_lessons_always_storable_so_recurrence_can_accumulate():
    # storage is permissive — a rejected lesson would never recur (deadlock).
    weak = MemoryEntry.new("lesson", "x", "global", applicability="universal",
                           confidence=0.5, recurrence=1)
    assert accepts(weak).ok


def test_universal_lesson_trusted_only_when_proven():
    # the blast-radius bar lives at injection, not storage.
    weak = MemoryEntry.new("lesson", "x", "global", applicability="universal",
                           confidence=0.5, recurrence=1)
    assert not trusted(weak)
    strong_conf = MemoryEntry.new("lesson", "y", "global", applicability="universal",
                                  confidence=0.8, recurrence=1)
    assert trusted(strong_conf)
    recurred = MemoryEntry.new("lesson", "z", "global", applicability="universal",
                               confidence=0.5, recurrence=2)
    assert trusted(recurred)


def test_narrow_scope_and_pinned_always_trusted():
    stack = MemoryEntry.new("lesson", "x", "global", applicability="stack:django",
                            confidence=0.4)
    pinned = MemoryEntry.new("lesson", "y", "global", applicability="universal",
                             confidence=0.1, pinned=True)
    assert trusted(stack) and trusted(pinned)


def test_enters_hot_threshold():
    cfg = GateConfig(hot_confidence=0.6)
    assert enters_hot(MemoryEntry.new("lesson", "a", "global", confidence=0.7), cfg)
    assert not enters_hot(MemoryEntry.new("lesson", "b", "global", confidence=0.3), cfg)
    assert enters_hot(MemoryEntry.new("lesson", "c", "global", confidence=0.1, pinned=True), cfg)


# --- classify / applicability ---

def test_classify_detects_env_and_stack():
    env, stack = classify_text("running python on windows path failed")
    assert env and stack == ""
    env2, stack2 = classify_text("django migration conflict in models")
    assert stack2 == "django"


def test_infer_applicability_env_is_universal():
    sig = FailureSignal(trigger="used python on windows", fix="use py")
    assert infer_applicability(sig, "paw") == "universal"


def test_infer_applicability_framework_is_stack():
    sig = FailureSignal(trigger="django migration ordering", fix="add dependency")
    assert infer_applicability(sig, "paw") == "stack:django"


def test_infer_applicability_default_is_project():
    sig = FailureSignal(trigger="this repo auth flow quirk", fix="call refresh first")
    assert infer_applicability(sig, "paw") == "project:paw"


def test_explicit_stack_overrides_keyword_guess():
    sig = FailureSignal(trigger="generic thing", fix="do x", stack="rust")
    assert infer_applicability(sig, "paw") == "stack:rust"


# --- to_lesson ---

def test_to_lesson_builds_compressed_body_and_anchors():
    sig = FailureSignal(trigger="forgot await", fix="add await", symbols=("fetch",),
                        confidence=0.6)
    e = to_lesson(sig, "paw", TODAY)
    assert e.body == "forgot await → add await"
    assert e.type == "lesson" and e.scope == "global"
    assert e.anchors.symbols == ("fetch",) and e.source == "hook"


# --- capture (store isolated) ---

def _isolate(monkeypatch, tmp_path, saved):
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")  # lockfile → tmp
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "save_lessons", lambda entries: saved.update(e=entries))


def test_capture_stores_accepted_lesson(monkeypatch, tmp_path):
    saved = {}
    _isolate(monkeypatch, tmp_path, saved)
    sig = FailureSignal(trigger="used python", fix="use py", env_level=True, confidence=0.8)
    res = capture(sig, "paw", today=TODAY)
    assert res.stored and res.verdict.ok
    assert saved["e"][0].body == "used python → use py"


def test_capture_stores_weak_universal_so_it_can_recur(monkeypatch, tmp_path):
    saved = {}
    _isolate(monkeypatch, tmp_path, saved)
    sig = FailureSignal(trigger="used python", fix="use py", env_level=True, confidence=0.4)
    res = capture(sig, "paw", today=TODAY)
    # stored (so recurrence can accumulate) but not yet trusted for injection
    assert res.stored and res.verdict.ok
    assert saved["e"][0].applicability == "universal"


def test_capture_seeds_related_edge_to_similar_existing(monkeypatch, tmp_path):
    from portaw.kernel import embed

    existing = MemoryEntry.new("lesson", "used python3 → use py launcher", "global",
                               applicability="universal", last_seen=TODAY)
    saved = {}
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    monkeypatch.setattr(store, "load_lessons", lambda: [existing])
    monkeypatch.setattr(store, "save_lessons", lambda entries: saved.update(e=entries))
    # fake embed: new lesson sits at cos 0.90 to the existing one → in the related band
    monkeypatch.setattr(embed, "available", lambda *a, **k: True)
    monkeypatch.setattr(embed, "encode", lambda texts: [[1.0, 0.0], [0.9, 0.4358899]])

    sig = FailureSignal(trigger="ran python", fix="use py", env_level=True, confidence=0.8)
    res = capture(sig, "paw", today=TODAY)
    assert res.stored
    new = saved["e"][-1]  # appended after the existing one
    assert existing.id in new.targets(RELATED)  # auto-seeded associative edge


def test_capture_seeds_reciprocal_related_edge(monkeypatch, tmp_path):
    from portaw.kernel import embed

    existing = MemoryEntry.new("lesson", "used python3 → use py launcher", "global",
                               applicability="universal", last_seen=TODAY)
    saved = {}
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    monkeypatch.setattr(store, "load_lessons", lambda: [existing])
    monkeypatch.setattr(store, "save_lessons", lambda entries: saved.update(e=entries))
    monkeypatch.setattr(embed, "available", lambda *a, **k: True)
    monkeypatch.setattr(embed, "encode", lambda texts: [[1.0, 0.0], [0.9, 0.4358899]])

    sig = FailureSignal(trigger="ran python", fix="use py", env_level=True, confidence=0.8)
    res = capture(sig, "paw", today=TODAY)
    by_id = {e.id: e for e in saved["e"]}
    # new → old (seeded) AND old → new (reciprocal) — the association is navigable both ways
    assert by_id[existing.id].id in by_id[res.entry.id].targets(RELATED)
    assert res.entry.id in by_id[existing.id].targets(RELATED)


def test_capture_seeds_no_edge_when_embed_unavailable(monkeypatch, tmp_path):
    from portaw.kernel import embed

    existing = MemoryEntry.new("lesson", "some other lesson", "global", last_seen=TODAY)
    saved = {}
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "mem")
    monkeypatch.setattr(store, "load_lessons", lambda: [existing])
    monkeypatch.setattr(store, "save_lessons", lambda entries: saved.update(e=entries))
    monkeypatch.setattr(embed, "available", lambda *a, **k: False)  # tier-2 off

    sig = FailureSignal(trigger="ran python", fix="use py", env_level=True, confidence=0.8)
    res = capture(sig, "paw", today=TODAY)
    assert res.stored
    assert saved["e"][-1].relations == ()  # embed off → exactly today's behaviour
