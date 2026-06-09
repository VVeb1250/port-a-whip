# Bench session 08 — output-compression TREATED (rtk ON)

You are a FRESH agent with no prior context. Do EXACTLY this, then STOP.

## Precondition (user did this)
rtk hook installed + active (`rtk init -g` writes the PreToolUse/Bash hook). Same
repo + commit/stash state as session 07.

## Tool constraint
Run the commands normally — rtk's PreToolUse hook rewrites/compresses Bash output
transparently. Do not hand-trim output yourself; let the hook do it (that's what's
being measured).

## Workload (identical to 07 — do in order, no commentary)
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
- Confirm repo+commit MATCHES session 07.
- Y/N reached step 6 with the SAME information available as baseline (completeness
  gate — if rtk compressed away a count/error you needed, that's a real loss, note it).
- "rtk trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials. Same model, cold cache, identical repo state.
> Note: rtk's anchor is already LOCKED at 26.3% (rtk-gain command-level). This A/B
> exists for the head-to-head vs headroom (session 09), same baseline.
