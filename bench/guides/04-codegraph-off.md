# Bench session 04 — code-intel BASELINE (codegraph OFF, grep/read)

You are a FRESH agent with no prior context. Do EXACTLY this, then STOP. This is
the baseline lane: no code-intel tool, you must answer via grep + read.

## Precondition (user did this)
codegraph + semble are NOT active on the host (removed/disabled). All three lanes
(04/05/06) MUST run in the SAME repo at the SAME commit — note which repo+commit
you're in and tell the user so 05/06 match it.

## Tool constraint
Answer using ONLY grep/ripgrep + reading files. Do NOT use any code-graph or
semantic-search MCP. This lane deliberately pays the grep+read cost — that's the
baseline the index tools must beat.

## Workload (do in order, no commentary between)
```
Answer these about the CURRENT repo, in order:
1. How does the main entrypoint reach its core processing function? Name the call path.
2. What are all the callers of the busiest/central function in this codebase?
3. If I change that function's signature, what breaks? List the impacted symbols.
4. Where is configuration loaded and parsed? Show the relevant code.
5. Give the architecture in 5 bullets: the main layers and how they connect.
Stop after step 5. Do not edit any files.
```

## Report then STOP
- State the repo + commit hash you ran in (05/06 must use the SAME).
- Y/N you answered all 5 (completeness gate).
- "Baseline trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials. Same model, cold cache, same repo+commit every trial.
