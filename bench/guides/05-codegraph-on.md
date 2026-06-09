# Bench session 05 — code-intel TREATED (codegraph ON)

You are a FRESH agent with no prior context. Do EXACTLY this, then STOP.

## Precondition (user did this)
`portaw install efficiency-starter --host claude-code` patched codegraph, AND the
index is BUILT: `codegraph init -i` then `codegraph status -j` shows
`initialized:true`. WITHOUT a built index codegraph is dead and you'd measure
nothing. Run in the SAME repo+commit as session 04.

## Tool constraint
Answer via the **codegraph MCP tools** (`codegraph_explore` / context / callers /
callees / impact). Do NOT fall back to grep+read unless codegraph genuinely lacks
the answer — and if you do, note it (that's a capability finding).

## Workload (identical to 04 — do in order, no commentary)
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
- Confirm repo+commit MATCHES session 04.
- Y/N you answered all 5, and whether codegraph alone sufficed (completeness +
  capability gate — codegraph should answer 2 & 3 that grep struggles with).
- "codegraph trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials. Same model, cold cache, same repo+commit.
