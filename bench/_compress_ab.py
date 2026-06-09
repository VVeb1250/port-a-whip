"""Deterministic command-output compression A/B: raw vs rtk vs headroom.

Method mirrors how rtk's own 26.3% was derived: command-level paired
raw-vs-compressed, tiktoken (cl100k) on what would enter context. NO ccusage,
NO fresh sessions, zero cache noise. Completeness is a manual eyeball on the
saved artifacts (a compressor that drops needed detail is not a win).

Usage:
  py bench/_compress_ab.py capture <repo>     # run cmds, save raw + rtk outputs
  py bench/_compress_ab.py headroom <venv_py>  # add headroom lane on saved raw
  py bench/_compress_ab.py report              # tiktoken table
"""
import subprocess, sys, os, pathlib, json

OUT = pathlib.Path(__file__).parent / "out" / "compress"
OUT.mkdir(parents=True, exist_ok=True)

# bulky-output commands rtk-class compressors target. {name: argv}
# git/diff/log/status/ls = rtk's strong suits; pytest = bulky test output.
CMDS = {
    "git_log_stat":  ["git", "log", "--stat", "-15"],
    "git_diff":      ["git", "diff", "HEAD~8", "--", "."],
    "git_status":    ["git", "status"],
    "pytest_v":      ["py", "-m", "pytest", "tests/", "-v", "--no-header"],
    "ls_recursive":  ["git", "ls-files"],
    "grep_todo":     ["git", "grep", "-n", "-E", "TODO|FIXME"],
}


def _run(argv, cwd):
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=300, encoding="utf-8", errors="replace")
        return (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return f"<run error: {e}>"


def capture(repo):
    repo = os.path.abspath(repo)
    for name, argv in CMDS.items():
        raw = _run(argv, repo)
        (OUT / f"{name}.raw.txt").write_text(raw, encoding="utf-8")
        # rtk-compressed: prepend rtk to the command
        rtk = _run(["rtk", *argv], repo)
        (OUT / f"{name}.rtk.txt").write_text(rtk, encoding="utf-8")
        print(f"captured {name}: raw {len(raw)} chars / rtk {len(rtk)} chars")


def headroom(venv_py):
    """Compress each saved .raw.txt with headroom via the venv python."""
    script = r'''
import sys, pathlib
inp = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
import headroom
out = None
for fn in ("compress","optimize","process","compress_text"):
    f = getattr(headroom, fn, None)
    if callable(f):
        try:
            r = f(inp)
            out = r if isinstance(r, str) else getattr(r, "text", None) or getattr(r, "content", None) or str(r)
            break
        except Exception as e:
            sys.stderr.write(f"{fn} failed: {e}\n")
if out is None:
    sys.stderr.write("NO_COMPRESS_FN; attrs=" + ",".join(d for d in dir(headroom) if not d.startswith("_")) + "\n")
    sys.exit(3)
sys.stdout.write(out)
'''
    sp = OUT / "_hr_one.py"
    sp.write_text(script, encoding="utf-8")
    for raw in sorted(OUT.glob("*.raw.txt")):
        name = raw.name[:-8]
        p = subprocess.run([venv_py, str(sp), str(raw)], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        if p.returncode == 0 and p.stdout:
            (OUT / f"{name}.headroom.txt").write_text(p.stdout, encoding="utf-8")
            print(f"headroom {name}: {len(p.stdout)} chars")
        else:
            print(f"headroom {name} FAILED: {p.stderr.strip()[:200]}")


def report():
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    def tk(p): return len(enc.encode(p.read_text(encoding="utf-8"), disallowed_special=())) if p.exists() else None
    rows = []
    tot = {"raw": 0, "rtk": 0, "headroom": 0}
    for name in CMDS:
        r = tk(OUT / f"{name}.raw.txt")
        k = tk(OUT / f"{name}.rtk.txt")
        h = tk(OUT / f"{name}.headroom.txt")
        rows.append((name, r, k, h))
        for key, v in (("raw", r), ("rtk", k), ("headroom", h)):
            if v: tot[key] += v
    print(f"\n{'command':<16}{'raw':>9}{'rtk':>9}{'rtk%':>7}{'headroom':>10}{'hr%':>7}")
    for name, r, k, h in rows:
        kp = f"{100*(1-k/r):.1f}" if (r and k) else "-"
        hp = f"{100*(1-h/r):.1f}" if (r and h) else "-"
        print(f"{name:<16}{r or '-':>9}{k or '-':>9}{kp:>7}{h or '-':>10}{hp:>7}")
    R, K, H = tot["raw"], tot["rtk"], tot["headroom"]
    print("-"*58)
    kp = f"{100*(1-K/R):.1f}" if R and K else "-"
    hp = f"{100*(1-H/R):.1f}" if R and H else "-"
    print(f"{'TOTAL':<16}{R:>9}{K:>9}{kp:>7}{H:>10}{hp:>7}")
    print(json.dumps({"raw": R, "rtk": K, "headroom": H,
                      "rtk_pct": kp, "headroom_pct": hp}))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "capture": capture(sys.argv[2])
    elif cmd == "headroom": headroom(sys.argv[2])
    else: report()
