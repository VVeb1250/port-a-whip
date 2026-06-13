"""Vetted-install runner — execute a curated set's shim steps WITHOUT a shell.

Curated registry sets are first-party (author-reviewed line by line), so paw
may run their install steps directly — but only via an argv list (shell=False),
never a shell string. shlex splits the vetted command into argv; no shell
metacharacter is ever interpreted, so there is no injection surface even though
the steps themselves invoke vendor installers (npm/npx/winget). Community sets
(Phase 4, untrusted) are NOT first-party and must stay print-only until
hash/signature verify — run_shim_steps refuses them.

This narrows, never widens, the §12 security line: the ban was always on
shell=True + community-submitted strings, not on running author-vetted argv.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass

# A command needing ANY of these can only work through a shell (pipe, chain,
# redirect, substitution, glob-to-shell). We never run a shell, so such a step
# is NOT auto-runnable — it stays print-only. This also rules out the
# natural-language "instruction" steps (e.g. browser-harness), which carry
# backticks/punctuation a shell would choke on too.
_SHELL_META = re.compile(r"[|&;<>$`\n()*?]")


@dataclass
class StepResult:
    tool: str
    cmd: str
    ok: bool
    code: int | None
    error: str = ""
    skipped: bool = False  # True = paw deliberately did NOT run it (needs a shell / manual)


def needs_shell(cmd: str) -> bool:
    """True if the command can only run through a shell (so argv exec can't)."""
    return bool(_SHELL_META.search(cmd))


def _argv(cmd: str) -> list[str]:
    """Split a vetted command string into argv (posix split; no shell)."""
    return shlex.split(cmd, posix=True)


def _resolve(argv: list[str]) -> list[str]:
    """Resolve argv[0] to a full path (honors PATHEXT). On Windows, wrap a
    .cmd/.bat shim through `cmd /c` so CreateProcess can launch it — still
    shell=False, still a fixed argv (no string interpolation = no injection)."""
    if not argv:
        return argv
    exe = shutil.which(argv[0])
    if exe is None:
        return argv  # let subprocess raise FileNotFoundError with the bare name
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe, *argv[1:]]
    return [exe, *argv[1:]]


def run_shim_steps(steps, *, curated: bool = True, runner=subprocess.run) -> list[StepResult]:
    """Execute each ShimStep via argv (shell=False). One result per step.

    Steps within a paw set are independent tool installs, so a failure does not
    abort the rest — each is reported on its own. `runner` is injectable for
    tests; it is called as runner(argv, shell=False)."""
    if not curated:
        raise ValueError(
            "refusing to auto-run a non-curated set — print-only until hash/sig verify (Phase 4)"
        )
    results: list[StepResult] = []
    for st in steps:
        if needs_shell(st.cmd):
            results.append(StepResult(
                st.tool, st.cmd, False, None,
                "needs a shell (pipe/chain/redirect) — run manually", skipped=True))
            continue
        argv = _argv(st.cmd)
        if not argv:
            results.append(StepResult(st.tool, st.cmd, False, None, "empty command"))
            continue
        try:
            proc = runner(_resolve(argv), shell=False)
            code = proc.returncode
            ok = code == 0
            results.append(StepResult(st.tool, st.cmd, ok, code, "" if ok else f"exit {code}"))
        except (OSError, ValueError) as e:
            results.append(StepResult(st.tool, st.cmd, False, None, str(e)))
    return results
