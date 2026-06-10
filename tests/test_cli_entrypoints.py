"""CLI hook entrypoints — exercise the actual `cli` path (stdin → stdout).

Regression for the missing `import sys` in main.py: unit tests called run_hook()
directly and never hit the CLI wrapper's `sys.stdout.buffer.write`, so the live
router silently emitted nothing. These drive the real Click command with stdin.
"""

import json

from click.testing import CliRunner

from portaw.main import cli
from portaw.memory import store


def test_router_run_emits_for_matching_prompt():
    runner = CliRunner()
    payload = json.dumps({"prompt": "scan the staged diff for leaked secrets and vulnerabilities"})
    res = runner.invoke(cli, ["router", "run"], input=payload)
    assert res.exit_code == 0
    assert "paw router" in res.output  # empty here == the missing-import regression


def test_router_run_injects_memory(monkeypatch):
    from portaw.memory.schema import MemoryEntry

    e = MemoryEntry.new("lesson", "forgot await on async call", "global",
                        trigger_terms=("async", "await"))
    monkeypatch.setattr(store, "load_lessons", lambda: [e])
    monkeypatch.setattr(store, "load_project", lambda: [])
    runner = CliRunner()
    payload = json.dumps({"prompt": "my async function returns a coroutine somehow"})
    res = runner.invoke(cli, ["router", "run"], input=payload)
    assert res.exit_code == 0 and "paw memory" in res.output and "forgot await" in res.output


def test_capture_hook_cli_stores(monkeypatch):
    saved = {}
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "save_lessons", lambda e: saved.update(e=e))
    runner = CliRunner()
    payload = json.dumps({"paw_lesson": {"trigger": "used python", "fix": "use py", "env": True,
                                         "confidence": 0.8}})
    res = runner.invoke(cli, ["memory", "capture-hook"], input=payload)
    assert res.exit_code == 0
    assert saved and saved["e"][0].body == "used python → use py"
