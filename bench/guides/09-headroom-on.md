# Bench session 09 — output-compression RIVAL (headroom)

You are a FRESH agent with no prior context. Do EXACTLY this, then STOP. Head-to-head
vs rtk (session 08), same baseline (07).

## Precondition (user did this)
headroom installed in **proxy/lib form** (`pip install headroom-ai` or per its
README) — NOT the MCP form. Keeping it 0-idle-def (like rtk) makes the head-to-head
fair. rtk hook DISABLED this session (don't stack two compressors). Same repo +
commit/stash state as 07/08.

## Tool constraint
Run the commands through headroom's compression path (per its README — proxy/wrapper
around the bulky commands). Do not also use rtk. Do not hand-trim output.

## Workload (identical to 07/08 — do in order, no commentary)
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
- Confirm repo+commit MATCHES 07/08.
- Y/N reached step 6 with needed info intact (completeness gate).
- Note any extra latency/setup headroom required — the verdict weighs ratio AGAINST
  its heavier Python+model dep, not in isolation (a leaner tool that compresses
  slightly less can still win on net).
- "headroom trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials. Same model, cold cache, identical repo state.
> Verdict lands in registry/deep-vet.md §1 S1 / §6: if headroom wins NET (ratio
> minus dep cost) reconsider the anchor; else rtk holds.
