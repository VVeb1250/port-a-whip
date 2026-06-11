"""L2 outcome feedback loop (#4) — suggested/used ledger, demotion, conversion.

Real-store paths run against the conftest-isolated tmp paw-home.
"""

import json

from portaw.adapters import router as r
from portaw.adapters.memory_hooks import run_tool_hook
from portaw.memory import outcomes

_PROMPT = "scan staged diff for leaked secret credentials"


def _payload(sid=""):
    p = {"prompt": _PROMPT}
    if sid:
        p["session_id"] = sid
    return json.dumps(p)


# --- ledger primitives ---

def test_mark_and_load_roundtrip():
    outcomes.mark_suggested(["secure-agent", "web-research"])
    outcomes.mark_suggested(["secure-agent"])
    outcomes.mark_used("secure-agent")
    recs = outcomes.load()
    assert recs["secure-agent"]["suggested"] == 2
    assert recs["secure-agent"]["used"] == 1
    assert recs["web-research"]["suggested"] == 1


def test_demotion_requires_threshold_and_zero_uses():
    for _ in range(outcomes.DEMOTE_MIN_SUGGESTED):
        outcomes.mark_suggested(["ignored-set", "converted-set"])
    outcomes.mark_used("converted-set")
    assert outcomes.demoted_names() == {"ignored-set"}
    outcomes.forget("ignored-set")
    assert outcomes.demoted_names() == set()


def test_parse_install_target():
    assert outcomes.parse_install_target("portaw install secure-agent") == "secure-agent"
    assert outcomes.parse_install_target("cd x; portaw install web-research --host codex") \
        == "web-research"
    assert outcomes.parse_install_target("portaw remove secure-agent") is None
    assert outcomes.parse_install_target("") is None


# --- router integration ---

def test_run_hook_records_suggestion():
    out = r.run_hook(stdin_text=_payload())
    assert out is not None and "secure-agent" in out
    assert outcomes.load()["secure-agent"]["suggested"] == 1


def test_demoted_set_stops_surfacing_until_conversion():
    for _ in range(outcomes.DEMOTE_MIN_SUGGESTED):
        outcomes.mark_suggested(["secure-agent"])
    assert r.run_hook(stdin_text=_payload()) is None      # demoted → silent

    outcomes.mark_used("secure-agent")                    # any conversion clears it
    assert r.run_hook(stdin_text=_payload()) is not None


def test_bash_install_counts_as_conversion():
    payload = json.dumps({
        "session_id": "conv", "tool_name": "Bash",
        "tool_input": {"command": "portaw install secure-agent"},
        "tool_response": {"stdout": "ok", "stderr": ""},
    })
    run_tool_hook(payload)
    assert outcomes.load()["secure-agent"]["used"] == 1
