"""Outcome-aware demotion for the skill-router (integration/ source of truth).

Covers router_log.demotion (aggregate the settled log -> blacklist/soft-demote
sets) and skill-router.apply_outcome (hard-drop blacklisted, soft-penalise
chronic-ignored, re-cut to the confidence floor). Loads the hyphen-named
integration files by path, like the parity test."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEG = ROOT / "integration"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _skill(n):
    return {"name": n, "desc": n, "tier": "cmd", "kind": "slash", "path": ""}


def test_demotion_blacklist_and_chronic_ignored(tmp_path, monkeypatch):
    rl = _load("rl_src", INTEG / "router_log.py")
    log = tmp_path / "log.jsonl"
    recs = [{"suggested": ["noisy"], "outcome": "ignored"} for _ in range(6)]
    recs.append({"suggested": ["good"], "outcome": "used"})      # has a use -> never demoted
    recs.append({"suggested": ["good"], "outcome": "ignored"})
    recs.append({"suggested": ["pendingone"], "outcome": None})  # unsettled -> not counted
    log.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
    monkeypatch.setattr(rl, "LOG_PATH", str(log))

    graph = {"demote": {"blacklist": ["caveman"], "min_suggested": 6, "penalty": 0.5}}
    blacklist, demote, penalty = rl.demotion(graph)

    assert blacklist == {"caveman"}
    assert "noisy" in demote          # 6 ignored, 0 used, >= min_suggested
    assert "good" not in demote       # any use ever clears it
    assert "pendingone" not in demote  # outcome None not aggregated
    assert penalty == 0.5


def test_demotion_below_threshold_not_demoted(tmp_path, monkeypatch):
    rl = _load("rl_src2", INTEG / "router_log.py")
    log = tmp_path / "log.jsonl"
    recs = [{"suggested": ["meh"], "outcome": "ignored"} for _ in range(5)]  # 5 < min 6
    log.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
    monkeypatch.setattr(rl, "LOG_PATH", str(log))
    _, demote, _ = rl.demotion({"demote": {"min_suggested": 6}})
    assert "meh" not in demote


def test_demotion_failsafe_missing_log(tmp_path, monkeypatch):
    rl = _load("rl_src3", INTEG / "router_log.py")
    monkeypatch.setattr(rl, "LOG_PATH", str(tmp_path / "absent.jsonl"))
    blacklist, demote, penalty = rl.demotion({})
    assert demote == set()
    assert blacklist == set()
    assert penalty == rl.DEMOTE_PENALTY


def test_apply_outcome_blacklist_hard_drop_and_soft_penalty():
    sr = _load("sr_src", INTEG / "skill-router.py")
    results = [(0.40, _skill("caveman")), (0.40, _skill("noisy")), (0.40, _skill("keep"))]
    out = sr.apply_outcome(results, {"caveman"}, {"noisy"}, 0.5)
    names = [s["name"] for _c, s in out]
    assert "caveman" not in names           # hard cut
    assert names[0] == "keep"               # un-penalised stays on top
    assert "noisy" in names                 # 0.40*0.5=0.20 >= COSINE_MIN -> survives, demoted


def test_apply_outcome_weak_demoted_match_drops():
    sr = _load("sr_src2", INTEG / "skill-router.py")
    # weak match 0.20 demoted *0.5 = 0.10 < COSINE_MIN(0.16) -> dropped
    out = sr.apply_outcome([(0.20, _skill("weak"))], set(), {"weak"}, 0.5)
    assert out == []


def test_apply_outcome_noop_when_no_sets():
    sr = _load("sr_src3", INTEG / "skill-router.py")
    results = [(0.30, _skill("a"))]
    assert sr.apply_outcome(results, set(), set(), 1.0) is results
