# codegraph A/B bench — ready-to-run workload

Goal: get the HARD number for the **codegraph** half of `efficiency-starter`.
codegraph's claim is "fewer tokens, fewer tool calls" (vendor, unverified) — it
replaces a grep+read exploration loop (dozens of calls, each dumping file text
into context) with one indexed `codegraph_explore` call returning only the
relevant symbols. The token win, if real, lands in **inputTokens /
cacheCreationTokens** (avoided file dumps), and in **fewer tool round-trips**.

> Why a fixed workload: `bench ab` diffs two sessions. If the two runs explore
> the code differently, the delta is noise. Vary ONLY codegraph; keep the task
> byte-identical and run both in the SAME repo at the SAME commit.

## Two provenance levers (run whichever you need)

1. **idle_def_tokens (load-all hosts, calculated — no session needed):** capture
   codegraph's live MCP tool-def JSON (8-9 tools: explore/search/callers/callees/
   impact/node/files/status) and tiktoken it, exactly as `context-quality` was
   measured (see registry/deep-vet.md "Token-metric protocol"). This is the
   always-on cost on Codex/Gemini and is a COUNT, not an A/B.
2. **delta_pct (the savings, measured — needs the A/B below):** the runtime
   token saving from answering via the index instead of grep+read.

## Protocol (delta_pct)

1. Pick a non-trivial repo (≥ a few hundred symbols) so exploration is real.
   Build the index first: `codegraph init -i` (without it codegraph is dead).

2. **Run A — codegraph OFF.** Remove codegraph from the host MCP config
   (`portaw remove efficiency-starter`, or disable just the server). FRESH
   session, paste the workload below verbatim. The agent MUST use grep/read.

3. **Run B — codegraph ON.** Re-install (`portaw install efficiency-starter`),
   confirm `codegraph status -j → initialized:true`. FRESH session, SAME
   workload verbatim. The agent should answer via `codegraph_explore`.

4. Diff:
   ```
   portaw bench list --agent claude     # newest two session ids
   portaw bench ab <A_id> <B_id>        # A = off (baseline), B = on (treated)
   ```
   Positive `saved` on totalTokens / inputTokens / cacheCreationTokens = codegraph
   win (avoided file dumps re-entering context). Also note the tool-call count
   drop (codegraph collapses a read loop into 1-3 calls) — that's the second axis.

## Workload (paste verbatim into a fresh session)

```
Answer these about the CURRENT repo, in order, no commentary between them:
1. How does the main entrypoint reach its core processing function? Name the call path.
2. What are all the callers of the busiest/central function in this codebase?
3. If I change that function's signature, what breaks? List the impacted symbols.
4. Where is configuration loaded and parsed? Show the relevant code.
5. Give the architecture in 5 bullets: the main layers and how they connect.
Stop after step 5. Do not edit any files.
```

Each step is a "trace / where-is / impact" question — codegraph's home turf, and
exactly the kind of question that costs a grep+read agent dozens of file-dumping
calls. Identical steps both runs ⇒ the only variable is codegraph ⇒ valid A/B.

## Rival lane: semble (anchor challenge, deep-vet §6)

`semble` (MinishLab) does code search via the same "answer from an index, not
grep+read" idea, claiming ~98% fewer tokens. **Idle-def already CALCULATED**
(tiktoken cl100k, live schemas, 2026-06-06): codegraph 1615 tok (8 tools) vs
**semble 509 tok (2 tools) → semble 68% leaner** on load-all hosts; on CC both
lazy-load → idle ≈ 0. But codegraph is RICHER (callers/callees/impact/explore);
semble = search + find_related only.

To finish the re-vet, run the workload above a THIRD time with semble installed
instead of codegraph (Run C), same repo+commit. Then judge on three axes, not one:
1. **idle_def_tokens** (load-all hosts) — already decided: semble −1106 tok.
2. **delta_pct / call-count** (runtime) — this A/B (does semble's search match
   codegraph's explore on token spend + round-trips?).
3. **capability** — can semble answer steps 2-3 (callers / refactor-impact) at all,
   or only the search-shaped ones? If it can't, it's leaner but NARROWER — a
   host-conditional anchor (semble on Codex/Gemini, codegraph on CC), not a swap.

## Caveats

- Same model both runs (ccusage tags model; mixing Opus/Sonnet skews tokens).
- Same repo + commit both runs (the graph and the files must match).
- Index must be BUILT and `initialized:true` for Run B, else you measure a dead tool.
- Measures token spend + call count, not answer quality. Sanity-check Run B's
  answers are at least as correct as Run A's — a tool that saves tokens but
  returns worse answers is NOT a win.
- idle_def_tokens (lever 1) is the load-all-host cost; delta_pct (lever 2) is the
  CC-relevant runtime saving. Record both per host in `registry/sets.json`
  `token_profile.hosts.<host>` with provenance `calculated` / `measured`.
