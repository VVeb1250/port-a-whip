"""CLI curation commands (pin/rm) + the capture-command registration regression.

The 2026-06-11 `memory pin` insert silently swallowed `@memory.command("capture")`
— the command vanished from the CLI with zero test noise. These tests pin command
REGISTRATION (cheap, catches any future decorator-eating edit) and the pin/rm flows.
"""


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

    expected = {"recall", "list", "add", "pin", "rm", "export", "capture", "enable", "disable",
                "status", "capture-hook", "session-hook", "tool-hook",
                "inject-enable", "inject-disable", "consolidate", "init", "harvest"}
    assert expected <= set(memory.commands)


def test_export_groups_and_marks(monkeypatch):
    state = [
        _lesson("use py not python", pinned=True, recurrence=34),
        _lesson("django thing", applicability="stack:django"),
    ]
    _patch_store(monkeypatch, state)
    res = CliRunner().invoke(cli, ["memory", "export"])
    assert res.exit_code == 0
    out = res.output
    assert "GENERATED" in out                      # never mistaken for a source
    assert "## universal" in out and "## stack:django" in out
    assert "★" in out and "×34" in out


def test_export_to_file(monkeypatch, tmp_path):
    _patch_store(monkeypatch, [_lesson("x y z")])
    f = tmp_path / "lessons.md"
    res = CliRunner().invoke(cli, ["memory", "export", "--out", str(f)])
    assert res.exit_code == 0
    assert "x y z" in f.read_text(encoding="utf-8")


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


def _patch_project_store(monkeypatch, state):
    monkeypatch.setattr(store, "load_project", lambda root=None: list(state))
    monkeypatch.setattr(store, "save_project",
                        lambda entries, root=None: (state.clear(), state.extend(entries)))


def _project(body, **kw):
    kw.setdefault("scope", "project")
    kw.setdefault("applicability", "project:x")
    return MemoryEntry.new("project", body, **kw)


def test_rm_and_pin_reach_project_store(monkeypatch):
    state = [_project("decision: tomlkit for TOML writes")]
    _patch_project_store(monkeypatch, state)
    runner = CliRunner()
    short = state[0].id[:6]

    res = runner.invoke(cli, ["memory", "pin", short, "--store", "project"])
    assert res.exit_code == 0 and state[0].pinned is True

    res = runner.invoke(cli, ["memory", "rm", short, "--store", "project"])
    assert res.exit_code == 0 and state == []


def test_add_project_rejects_explicit_applicability(monkeypatch):
    """--applicability with --type project was silently overridden — now it refuses."""
    res = CliRunner().invoke(
        cli, ["memory", "add", "x", "--type", "project", "--applicability", "stack:python"])
    assert res.exit_code != 0
    assert "lessons only" in res.output


def test_verify_renders_alt_status_and_passes_host(monkeypatch):
    """KeyError 'alt' regression: verify crashed on host-anchored tools (live bug)."""
    import portaw.sets.healthcheck as hc_mod
    from portaw.sets.healthcheck import SetHealth, ToolHealth

    seen = {}

    def fake_check(set_name, host=None):
        seen["host"] = host
        return SetHealth(set_name, (
            ToolHealth("codegraph", "mcp", "ok", "on PATH"),
            ToolHealth("semble", "mcp", "alt", "host-anchored to codex/gemini"),
        ))

    monkeypatch.setattr(hc_mod, "check_set", fake_check)
    res = CliRunner().invoke(cli, ["verify", "efficiency-starter", "--host", "codex"])
    assert res.exit_code == 0                    # alt never fails the gate
    assert "alt" in res.output and "PASS" in res.output
    assert seen["host"] == "codex"


def test_consolidate_archives_before_overwriting_store(monkeypatch):
    """Crash-safety order: if append_archive fails, the store must be UNTOUCHED
    (reverse order would have already dropped the archived lessons forever)."""
    stale = _lesson("stale thing", confidence=0.5, last_seen="2020-01-01")
    state = [stale]
    _patch_store(monkeypatch, state)

    def boom(entries):
        raise OSError("disk full")

    monkeypatch.setattr(store, "append_archive", boom)
    res = CliRunner().invoke(cli, ["memory", "consolidate"])
    assert res.exit_code != 0           # the failure surfaces
    assert state == [stale]             # store not overwritten — nothing lost
