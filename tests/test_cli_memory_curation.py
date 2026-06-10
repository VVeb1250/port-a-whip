"""CLI curation commands (pin/rm) + the capture-command registration regression.

The 2026-06-11 `memory pin` insert silently swallowed `@memory.command("capture")`
— the command vanished from the CLI with zero test noise. These tests pin command
REGISTRATION (cheap, catches any future decorator-eating edit) and the pin/rm flows.
"""

import json

from click.testing import CliRunner

import portaw.memory.store as store
from portaw.main import cli
from portaw.memory.schema import MemoryEntry


def _lesson(body, **kw):
    kw.setdefault("scope", "global")
    kw.setdefault("confidence", 0.9)
    return MemoryEntry.new("lesson", body, **kw)


def _patch_store(monkeypatch, state):
    monkeypatch.setattr(store, "load_lessons", lambda: list(state))
    monkeypatch.setattr(store, "save_lessons",
                        lambda entries: (state.clear(), state.extend(entries)))


def test_all_memory_commands_registered():
    from portaw.main import memory

    expected = {"recall", "list", "add", "pin", "rm", "capture", "enable", "disable",
                "status", "capture-hook", "session-hook", "tool-hook",
                "inject-enable", "inject-disable", "consolidate", "init", "harvest"}
    assert expected <= set(memory.commands)


def test_pin_and_unpin_by_id_prefix(monkeypatch):
    state = [_lesson("use py not python")]
    _patch_store(monkeypatch, state)
    runner = CliRunner()
    short = state[0].id[:6]

    res = runner.invoke(cli, ["memory", "pin", short])
    assert res.exit_code == 0 and state[0].pinned is True

    res = runner.invoke(cli, ["memory", "pin", short, "--unpin"])
    assert res.exit_code == 0 and state[0].pinned is False


def test_pin_unknown_id_fails_loudly(monkeypatch):
    _patch_store(monkeypatch, [])
    res = CliRunner().invoke(cli, ["memory", "pin", "deadbeef"])
    assert res.exit_code != 0


def test_rm_removes_by_prefix(monkeypatch):
    state = [_lesson("keep me"), _lesson("drop me")]
    _patch_store(monkeypatch, state)
    drop_id = next(e.id for e in state if e.body == "drop me")

    res = CliRunner().invoke(cli, ["memory", "rm", drop_id[:8]])
    assert res.exit_code == 0
    assert [e.body for e in state] == ["keep me"]


def test_rm_unknown_id_fails_loudly(monkeypatch):
    _patch_store(monkeypatch, [_lesson("x")])
    res = CliRunner().invoke(cli, ["memory", "rm", "nope"])
    assert res.exit_code != 0
