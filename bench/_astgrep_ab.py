"""Deterministic A/B for the ast-grep structural rung (efficiency-starter, item #12).

Two mechanisms, measured with tiktoken cl100k (same encoder both lanes => relative
delta valid; absolute is a proxy). No ccusage, no fresh session, no cache noise.

MECHANISM 1 — precision: a text grep for `NAME(` matches comments/strings/substrings
(e.g. `reroute(`, a docstring mention); ast-grep `NAME($$$A)` matches only the call
SHAPE. Lane A = text-grep hit lines that enter context; Lane B = ast-grep call-site
lines. (On a clean repo the gap is small — reported honestly, not inflated.)

MECHANISM 2 — codemod: rename `NAME(` -> `NEW(` repo-wide.
  Lane A (grep->read->edit loop) token cost, bracketed:
    - LOWER bound  = grep hit lines + a tight +/-CTX window around each hit + edit echo
    - UPPER bound  = grep hit lines + FULL content of every affected file + edit echo
    (a real agent lands between: it reads more than a tight window to edit safely)
  Lane B (ast-grep --rewrite -U) = the single unified diff. Fully measured.

Usage: py bench/_astgrep_ab.py [NAME] [NEW] [--lang python] [--root portaw] [--ctx 3]
Default: route -> route_v2 over portaw/ (python).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import tiktoken

ENC = tiktoken.get_encoding("cl100k_base")


def _astgrep() -> str:
    """Resolve a real ast-grep executable (subprocess can't launch the .CMD/.ps1 shim)."""
    for c in ("ast-grep", "sg"):
        p = shutil.which(c)
        if p and p.lower().endswith(".exe"):
            return p
    cand = Path(os.environ.get("APPDATA", "")) / "npm/node_modules/@ast-grep/cli/ast-grep.exe"
    if cand.exists():
        return str(cand)
    return "ast-grep"


ASTGREP = _astgrep()


def toks(text: str) -> int:
    return len(ENC.encode(text))


def run(cmd: list[str]) -> str:
    if cmd and cmd[0] == "ast-grep":
        cmd = [ASTGREP] + cmd[1:]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return (p.stdout or "") + (p.stderr or "")


def text_grep(name: str, root: Path) -> list[tuple[Path, int, str]]:
    """Mimic an agent's `grep -n 'name('`: literal substring over file TEXT."""
    needle = name + "("
    hits: list[tuple[Path, int, str]] = []
    for f in sorted(root.rglob("*.py")):
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if needle in line:
                hits.append((f, i, line))
    return hits


def main(argv: list[str]) -> int:
    name = argv[0] if len(argv) > 0 and not argv[0].startswith("--") else "route"
    new = argv[1] if len(argv) > 1 and not argv[1].startswith("--") else "route_v2"
    lang = "python"
    root = Path("portaw")
    ctx = 3
    for i, a in enumerate(argv):
        if a == "--lang":
            lang = argv[i + 1]
        elif a == "--root":
            root = Path(argv[i + 1])
        elif a == "--ctx":
            ctx = int(argv[i + 1])

    pat = f"{name}($$$A)"
    print(f"# ast-grep A/B  symbol={name!r}  rename->{new!r}  root={root}  lang={lang}\n")

    # ---- MECHANISM 1: precision (search output that enters context) ----
    grep_hits = text_grep(name, root)
    laneA1 = "\n".join(f"{f}:{ln}:{txt}" for f, ln, txt in grep_hits)
    laneB1 = run(["ast-grep", "run", "-p", pat, str(root), "-l", lang])
    a1, b1 = toks(laneA1), toks(laneB1)
    print("## Mechanism 1 — precision (find call sites)")
    print(f"Lane A  text-grep '{name}(' : {len(grep_hits)} hit-lines = {a1} tok")
    print(f"Lane B  ast-grep '{pat}'    : {b1} tok")
    if a1:
        print(f"  delta = {100*(a1-b1)/a1:+.1f}% (B vs A)\n")

    # ---- MECHANISM 2: codemod (rename across files) ----
    affected = sorted({f for f, _, _ in grep_hits})
    grep_out = laneA1
    # edit echo: each hit -> old line + new line emitted in an Edit block (~2x the line)
    edit_echo = "\n".join(f"{txt}\n{txt.replace(name + '(', new + '(')}" for _, _, txt in grep_hits)
    # tight windows
    windows: list[str] = []
    for f in affected:
        lines = f.read_text(encoding="utf-8").splitlines()
        hit_lns = [ln for ff, ln, _ in grep_hits if ff == f]
        keep: set[int] = set()
        for ln in hit_lns:
            keep.update(range(max(1, ln - ctx), min(len(lines), ln + ctx) + 1))
        windows.append("\n".join(lines[i - 1] for i in sorted(keep)))
    laneA2_lower = grep_out + "\n" + "\n".join(windows) + "\n" + edit_echo
    full = "\n".join(f.read_text(encoding="utf-8") for f in affected)
    laneA2_upper = grep_out + "\n" + full + "\n" + edit_echo
    # NO -U/-A: print the preview diff only (do NOT mutate the repo). This is what
    # the agent reviews; -U would apply in place and emit near-zero output.
    laneB2 = run(["ast-grep", "run", "-p", pat, str(root), "-l", lang,
                  "--rewrite", f"{new}($$$A)"])
    a2lo, a2hi, b2 = toks(laneA2_lower), toks(laneA2_upper), toks(laneB2)
    print("## Mechanism 2 — codemod (rename across files)")
    print(f"affected files = {len(affected)}, edit sites = {len(grep_hits)}")
    print(f"Lane A  grep->read->edit  LOWER (tight +/-{ctx} windows) = {a2lo} tok")
    print(f"Lane A  grep->read->edit  UPPER (full files)            = {a2hi} tok")
    print(f"Lane B  ast-grep --rewrite (one preview diff)           = {b2} tok")
    if a2lo:
        print(f"  delta vs LOWER = {100*(a2lo-b2)/a2lo:+.1f}%   vs UPPER = {100*(a2hi-b2)/a2hi:+.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
