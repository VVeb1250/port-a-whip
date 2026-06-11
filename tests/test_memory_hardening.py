"""Hardening regressions — the 2026-06-11 audit fixes.

Each test pins one found bug: pinned-not-always-on, anchor suffix false-positive,
upsert dropping a pin, store read crash, archive eating HIGH-confidence lessons,
budget break skipping cheaper items, embed cache ignoring the model dir, and the
harvest reword-twin duplicate.
"""

from datetime import date

from click.testing import CliRunner

import portaw.memory.store as store
from portaw.kernel import embed
from portaw.kernel.ranking import Capability
from portaw.main import cli
from portaw.memory.anchors import AnchorQuery, overlap
from portaw.memory.consolidate import consolidate
from portaw.memory.inject import InjectConfig, select
from portaw.memory.retrieval import Scored, recall
from portaw.memory.schema import Anchors, MemoryEntry

TODAY = date(2026, 6, 10)


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    kw.setdefault("last_seen", TODAY.isoformat())
    return MemoryEntry.new("lesson", body, **kw)


# --- pinned = always-on (recall floor must not silence it) ---

def test_pinned_bypasses_recall_floor():
    pinned = _lesson("use py not python", pinned=True, confidence=0.9)
    plain = _lesson("unrelated note about css", confidence=0.9)
    hits = recall("the capital of france", [pinned, plain], today=TODAY)
    assert [h.entry.body for h in hits] == ["use py not python"]


def test_pinned_recall_then_select_injects_on_any_prompt():
    pinned = _lesson("use py not python", pinned=True, confidence=0.9)
    out = select(recall("totally unrelated prompt", [pinned], today=TODAY))
    assert [s.entry.body for s in out] == ["use py not python"]


# --- anchor path match needs a component boundary ---

def test_overlap_path_no_bare_suffix_false_positive():
    a = Anchors(paths=("b.py",))
    assert overlap(a, AnchorQuery(paths=("ab.py",))) == 0.0       # not a boundary
    assert overlap(a, AnchorQuery(paths=("repo/b.py",))) == 1.0   # boundary match


# --- upsert merges pin + confidence (sticky, never silently dropped) ---

def test_upsert_bump_keeps_incoming_pin_and_max_confidence():
    old = _lesson("dup body", confidence=0.5)
    incoming = _lesson("dup body", pinned=True, confidence=0.9)
    out = store.upsert([old], incoming, last_seen="2026-06-11")
    assert len(out) == 1
    assert out[0].pinned is True
    assert out[0].confidence == 0.9
    assert out[0].recurrence == 2


def test_upsert_bump_never_unpins():
    old = _lesson("dup body", pinned=True)
    out = store.upsert([old], _lesson("dup body"), last_seen="2026-06-11")
    assert out[0].pinned is True


# --- store reads never crash a recall ---

def test_read_jsonl_tolerates_invalid_utf8(tmp_path):
    p = tmp_path / "lessons.jsonl"
    p.write_bytes(b"\xff\xfe garbage \x00\n")
    assert store._read_jsonl(p) == []


def test_read_jsonl_tolerates_unreadable_dir_path(tmp_path):
    # a directory at the store path raises OSError on read → degrade to empty
    p = tmp_path / "lessons.jsonl"
    p.mkdir()
    assert store._read_jsonl(p) == []


# --- consolidation must not archive a vouched HIGH lesson ---

def test_consolidate_protects_high_confidence_from_archive():
    stale_high = _lesson("py-command lesson", last_seen="2026-01-01", confidence=0.9)
    stale_low = _lesson("minor note", last_seen="2026-01-01", confidence=0.5)
    res = consolidate([stale_high, stale_low], today=TODAY)
    kept = {e.body for e in res.kept}
    assert "py-command lesson" in kept
    assert "minor note" not in kept


# --- inject budget: an oversized item must not block cheaper lower-ranked ones ---

def test_budget_skips_oversized_but_keeps_cheaper_following():
    big = _lesson("x " * 300, confidence=0.9)
    small = _lesson("short fix", confidence=0.9)
    scored = [
        Scored(score=0.9, entry=big, relevance=0.9, anchor=0, activation=1, base=0.9),
        Scored(score=0.5, entry=small, relevance=0.5, anchor=0, activation=1, base=0.5),
    ]
    out = select(scored, InjectConfig(max_tokens=20))
    assert [s.entry.body for s in out] == ["short fix"]


# --- embed corpus cache is keyed by model dir too ---

def test_embed_signature_differs_per_model_dir(tmp_path):
    caps = [Capability(name="a", text="b", ctype="set")]
    s1 = embed._signature(caps, tmp_path / "m1")
    s2 = embed._signature(caps, tmp_path / "m2")
    assert s1 != s2


# --- harvest --confirm: a reworded index line replaces its stale twin ---

_INDEX_V1 = "## X\n- [HIGH] [py-command] `python` fails → use `py` (x3, 2026-06-01)\n"
_INDEX_V2 = "## X\n- [HIGH] [py-command] `python`/`python3` not found → use `py` only (x3, 2026-06-01)\n"


def _patch_store(monkeypatch, state):
    monkeypatch.setattr(store, "load_lessons", lambda: list(state))
    monkeypatch.setattr(store, "save_lessons",
                        lambda entries: (state.clear(), state.extend(entries)))


def test_harvest_rewording_replaces_stale_twin(tmp_path, monkeypatch):
    state: list[MemoryEntry] = []
    _patch_store(monkeypatch, state)
    idx = tmp_path / "mistakes-index.md"
    runner = CliRunner()

    idx.write_text(_INDEX_V1, encoding="utf-8")
    r1 = runner.invoke(cli, ["memory", "harvest", "--file", str(idx), "--confirm"])
    assert r1.exit_code == 0 and len(state) == 1
    first_id = state[0].id

    # pin it store-side, then reword the index line and re-harvest
    state[0] = MemoryEntry.from_raw({**state[0].to_raw(), "pinned": True})
    idx.write_text(_INDEX_V2, encoding="utf-8")
    r2 = runner.invoke(cli, ["memory", "harvest", "--file", str(idx), "--confirm"])
    assert r2.exit_code == 0
    assert len(state) == 1                      # replaced, NOT duplicated
    assert state[0].id != first_id              # new content-hash id
    assert state[0].pinned is True              # store-side pin survives the rekey
    assert state[0].recurrence == 3


def test_harvest_rerun_same_index_is_idempotent(tmp_path, monkeypatch):
    state: list[MemoryEntry] = []
    _patch_store(monkeypatch, state)
    idx = tmp_path / "mistakes-index.md"
    idx.write_text(_INDEX_V1, encoding="utf-8")
    runner = CliRunner()
    runner.invoke(cli, ["memory", "harvest", "--file", str(idx), "--confirm"])
    runner.invoke(cli, ["memory", "harvest", "--file", str(idx), "--confirm"])
    assert len(state) == 1 and state[0].recurrence == 3
