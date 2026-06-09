# Bench session 07 — output-compression BASELINE (no rtk, no headroom)

You are a FRESH agent with no prior context. Do EXACTLY this, then STOP. Baseline
lane: NO output compressor active, so bulky command output enters context raw.

## Precondition (user did this)
The rtk PreToolUse hook is DISABLED and no headroom proxy is active. All three
lanes (07/08/09) MUST run in the SAME repo at the SAME commit/state — commit or
stash first so `git` output is identical across lanes. Note the repo+commit.

## Tool constraint
Just run the commands normally. No compression layer. This is the raw-output
baseline the compressors must beat.

## Workload (do in order, no commentary between)
```
Do these steps in order, no commentary between them, in the current repo:
1. Run the full test suite and report only pass/fail counts.
2. Run the linter/type-checker and report the error count.
3. git status, then git log --stat for the last 5 commits.
4. List every file changed in the last 10 commits.
5. Build the project and report success or the first error.
6. grep the codebase for "TODO" and "FIXME" and count them.
Stop after step 6.
```

## Report then STOP
- State repo + commit/stash state (08/09 must match exactly).
- Y/N you reached step 6 with real output each step (completeness gate — a run that
  errored out early isn't comparable).
- "Baseline trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials. Same model, cold cache, identical repo state every trial.
