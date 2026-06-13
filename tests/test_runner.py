"""run_shim_steps — argv exec (shell=False), curated gate, per-step results."""

from dataclasses import dataclass

import pytest

from portaw.sets.runner import _argv, needs_shell, run_shim_steps


@dataclass
class _Step:
    tool: str
    label: str
    cmd: str
    runs_vendor_code: bool = True


class _Proc:
    def __init__(self, code):
        self.returncode = code


def _ok_runner(calls):
    def run(argv, shell=False):
        calls.append((argv, shell))
        return _Proc(0)
    return run


def test_argv_splits_without_shell():
    assert _argv("winget install DuckDB.cli") == ["winget", "install", "DuckDB.cli"]


def test_runner_never_uses_shell():
    calls = []
    run_shim_steps([_Step("jq", "x", "jq --version")], runner=_ok_runner(calls))
    assert len(calls) == 1
    _argv_passed, shell = calls[0]
    assert shell is False  # the §12 guarantee: argv only, no shell string


def test_each_step_runs_and_reports_ok():
    calls = []
    steps = [_Step("a", "", "tool-a x"), _Step("b", "", "tool-b y")]
    res = run_shim_steps(steps, runner=_ok_runner(calls))
    assert [r.tool for r in res] == ["a", "b"]
    assert all(r.ok for r in res)


def test_failure_does_not_abort_remaining_steps():
    def run(argv, shell=False):
        return _Proc(1 if argv[0].endswith("a") or argv == ["tool-a", "x"] else 0)

    res = run_shim_steps([_Step("a", "", "tool-a x"), _Step("b", "", "tool-b y")], runner=run)
    assert res[0].ok is False and res[0].code == 1
    assert res[1].ok is True  # second step still ran


def test_oserror_is_captured_not_raised():
    def run(argv, shell=False):
        raise FileNotFoundError("no such tool")

    res = run_shim_steps([_Step("x", "", "ghost-tool")], runner=run)
    assert res[0].ok is False
    assert "no such tool" in res[0].error


def test_non_curated_set_refused():
    with pytest.raises(ValueError, match="non-curated"):
        run_shim_steps([_Step("x", "", "tool")], curated=False, runner=_ok_runner([]))


def test_empty_command_reported_not_crashing():
    res = run_shim_steps([_Step("x", "", "   ")], runner=_ok_runner([]))
    assert res[0].ok is False
    assert "empty" in res[0].error


@pytest.mark.parametrize("cmd", [
    "curl -fsSL https://x/install.sh | sh",   # pipe
    "a && b",                                  # chain
    "echo x > file",                           # redirect
    "do-a; do-b",                              # sequence
    "pip install $(cat req)",                  # substitution
    "Read `install.md` and follow steps",      # NL instruction w/ backtick
    "npm install foo*",                        # glob
])
def test_needs_shell_flags_shell_only_commands(cmd):
    assert needs_shell(cmd) is True


@pytest.mark.parametrize("cmd", [
    "winget install DuckDB.cli",
    "npm install -g figtree-cli",
    "go install github.com/google/osv-scanner/v2/cmd/osv-scanner@latest",
    'pip install markitdown[docx,xlsx]',
])
def test_simple_installs_not_flagged(cmd):
    assert needs_shell(cmd) is False


def test_shell_step_is_skipped_never_executed():
    calls = []
    steps = [_Step("rtk", "", "curl -fsSL https://x | sh"), _Step("jq", "", "jq install")]
    res = run_shim_steps(steps, runner=_ok_runner(calls))
    assert res[0].skipped is True and res[0].ok is False
    assert res[1].ok is True
    # the shell-requiring step never reached the runner
    assert all("curl" not in argv[0] for argv, _ in calls)
