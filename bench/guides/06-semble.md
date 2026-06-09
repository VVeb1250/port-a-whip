# Bench session 06 — code-intel RIVAL (semble)

You are a FRESH agent with no prior context. Do EXACTLY this, then STOP. This lane
re-vets the host-conditional anchor: semble (leaner idle on load-all hosts) vs
codegraph (richer). Same workload as 04/05.

## Precondition (user did this)
`uv tool install semble` done + semble added to the host MCP config (codegraph
NOT active this session). Same repo+commit as sessions 04/05.

## Tool constraint
Answer via the **semble MCP tools** (`search` + `find_related`) only. Do NOT use
codegraph or grep+read. The point is to see how far search+similarity alone gets.

## Workload (identical to 04/05 — do in order, no commentary)
```
Answer these about the CURRENT repo, in order:
1. How does the main entrypoint reach its core processing function? Name the call path.
2. What are all the callers of the busiest/central function in this codebase?
3. If I change that function's signature, what breaks? List the impacted symbols.
4. Where is configuration loaded and parsed? Show the relevant code.
5. Give the architecture in 5 bullets: the main layers and how they connect.
Stop after step 5. Do not edit any files.
```

## Report then STOP — the THREE-axis judgement
- Confirm repo+commit MATCHES 04/05.
- **Capability gate (decisive):** could semble's search/find_related actually answer
  Q2 (all callers) and Q3 (change-impact), or only the search-shaped Q1/Q4/Q5? Be
  explicit per question. If it CANNOT do callers/impact, semble is LEANER but
  NARROWER → host-conditional anchor (semble on load-all, codegraph on CC), NOT a
  swap. This capability answer matters more than the token delta.
- Y/N completeness per question.
- "semble trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials. Same model, cold cache, same repo+commit.
> Idle-def already decided (semble 509 < codegraph 1615 tok). This run = runtime +
> capability only.
