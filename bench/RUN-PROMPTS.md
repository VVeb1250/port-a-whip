# RUN-PROMPTS — copy-paste sheet for the remaining DOGFOOD runs

> Open this file, copy a **PASTE** block into a **FRESH** Claude Code session, let it
> run, then come BACK to your controlling session (the one with paw context) to
> aggregate. One block = one fresh session's job. The guides it points to are fully
> self-contained — the fresh agent needs nothing but the block.
>
> **Why fresh + why ×3:** runtime token deltas are NOISY (cache + agent
> non-determinism). A number is only `measured` with **same model · ≥3 trials ·
> cold cache · completeness-gate-first**. n=1 = `estimated`, say so. Full validity
> rules: `bench/guides/00-INDEX.md`.
>
> **Setup once (controlling shell, repo root):** `py -m pip install -e .` (done
> 2026-06-08). If `portaw` not on PATH → use `py -m portaw ...` everywhere.
>
> Status legend: ☐ not started · ◐ partial · ✅ done. Tick as you go.

---

## ✅ A. Code-intel A/B — codegraph vs semble vs grep (DOGFOOD #1 + #3) — RESOLVED 2026-06-09

> ROP 3-repo run: token-delta not isolable -> decided on CAPABILITY (codegraph 5/5 incl callers/impact;
> semble search-only). Clean number then CLOSED via external vendor benches: codegraph 59% fewer
> tokens/70% fewer calls (7-repo median, 64% worse on whole-file = matches paw proxy); semble 98% on
> search-retrieval only. sets.json + deep-vet §6 updated. A paw-owned `measured` label would still need
> discipline-isolated sessions (low value). Prompts kept for that optional re-run.


Closes efficiency-starter `delta_pct` on CC + the host-conditional anchor. **One
shared baseline (04) for both treated lanes (05, 06).** Same repo + same commit for
all 9 runs, same model.

**Pick a target repo first** (non-trivial, NOT port-a-whip itself ideally — a repo
with real call-graphs). Note its commit SHA; use it for every run.

### A0 — baseline: grep/read only (guide 04) — run ×3
Setup (controlling shell): remove codegraph **and** semble from the host MCP config
(`portaw remove efficiency-starter` or hand-edit), confirm neither `mcp__codegraph__*`
nor semble tools load.
```
Follow bench/guides/04-codegraph-off.md exactly. Do only what it says, then stop and report the session id + answers.
```

### A1 — treated: codegraph (guide 05) — run ×3
Setup: `portaw install efficiency-starter` then `codegraph init -i` in the target
repo; confirm `codegraph status -j` → `initialized:true`.
```
Follow bench/guides/05-codegraph-on.md exactly. Do only what it says, then stop and report the session id + answers.
```

### A2 — treated: semble (guide 06) — run ×3
Setup: `uv tool install semble` (done) + add semble to host MCP cfg (remove
codegraph first — XOR, N1 ceiling). Confirm semble tools load.
```
Follow bench/guides/06-semble.md exactly. Do only what it says, then stop and report the session id + answers.
```

**Aggregate (controlling session):**
```
portaw bench list --agent claude          # grab the 9 ids
portaw bench ab <A0_id> <A1_id>           # grep→codegraph, per trial
portaw bench ab <A0_id> <A2_id>           # grep→semble, per trial
```
Median of 3 per lane. **Completeness gate first:** can semble even answer the
callers/impact questions, or only search-shaped ones? A lane that can't answer =
disqualified before tokens. → write `registry/sets.json` efficiency-starter
`token_profile.hosts.claude-code` (codegraph delta_pct, flip vendor-claimed→measured
only if ≥3 stable) + `code_intel_anchor_by_host`; note in `deep-vet.md` §1/§6.

---

## ✅ B. Output-compression A/B — rtk vs headroom (DOGFOOD #2) — RESOLVED 2026-06-09

> Reframed: rtk + headroom are COMPLEMENTARY layers (rtk=PreToolUse hook, headroom=API-proxy),
> stack additively (real 1-month: rtk 88% / headroom +12%). paw local deterministic: rtk 63.5%
> git-heavy (bench/_compress_ab.py). headroom blocked on Windows (no wheel + Rust build).
> rtk stays anchor; headroom = optional API-proxy rung. sets.json + deep-vet §6 updated.
> Prompts below kept for a future isolated-session ccusage cross-check.


Challenge rtk's measured 26.3% against headroom's claimed 60-95%. Both non-MCP,
0 idle def → fair head-to-head. **Shared baseline (07).** Same workload + repo state
for all 9 runs, same model.

### B0 — baseline: no compressor (guide 07) — run ×3
Setup: disable rtk hook (`rtk` PreToolUse off in host settings), no headroom.
```
Follow bench/guides/07-compressor-off.md exactly. Do only what it says, then stop and report the session id.
```

### B1 — treated: rtk (guide 08) — run ×3
Setup: rtk hook ON (`rtk init -g` / confirm PreToolUse Bash → `rtk hook claude`).
```
Follow bench/guides/08-rtk-on.md exactly. Do only what it says, then stop and report the session id.
```

### B2 — treated: headroom (guide 09) — run ×3
Setup: rtk OFF; `pip install headroom-ai` in **proxy/lib form, NOT MCP** (keep it
0-idle-def for fairness — per its README).
```
Follow bench/guides/09-headroom-on.md exactly. Do only what it says, then stop and report the session id.
```

**Aggregate (controlling session):**
```
portaw bench ab <B0_id> <B1_id>           # rtk ratio
portaw bench ab <B0_id> <B2_id>           # headroom ratio
```
**Sanity gate:** both must have reached the final step — a tool that dropped needed
detail is NOT a win. Weigh headroom's ratio AGAINST its heavier dep (Python +
Kompress model + latency) vs rtk lean/Rust/0-dep. → `deep-vet.md` §1 S1 / §6. Swap
anchor only if headroom wins NET (ratio minus dep cost).

---

## ✅ C. Set install-tests — design-quality / secure-agent / context-quality (DOGFOOD #6 + #7) — DONE 2026-06-08

> secure-agent PASS · context-quality PASS · design-quality verified (impeccable core;
> figtree optional; slop-catch on a real frontend still un-exercised). sets.json
> `verified` blocks updated. Prompt kept for re-runs.


NOT an A/B. Single session, no isolation. Install → run printed shim → `portaw
verify` → flip `verified.status` DRAFT→verified. Can do all three in one go.
```
Follow bench/guides/10-installs.md exactly. Install each set, run the printed manual shim steps, run portaw verify for each, then report: per set — installed? verify gate PASS/FAIL? what was missing?
```
**SECURITY:** shim runs vendor CLIs (curated/pinned). Any token (Figma) → `.env`
as `${VAR}`, NEVER plaintext. Don't pair secure-agent's nah with
`--dangerously-skip-permissions`. → update each set's `verified` block in
`registry/sets.json` from the report.

---

## ☐ D. Router live-fire — Codex / Gemini (DOGFOOD #5)  ⚠ needs that host installed

Adapters are built + unit-tested; Codex live-probed vs a config copy; **Gemini never
fired live** (CLI not on this box). This confirms the hook actually injects in a real
session. No guide file — steps are inline. **Run in your controlling session** (it's
a host-config + manual-check task, not a token bench).

**Codex** (if `codex` installed):
```
portaw router enable --host codex
```
Then start Codex, submit: `scan the staged diff for secrets`. Confirm a `paw router:`
block appears in context with `hookEventName: UserPromptSubmit`.

**Gemini** (if `gemini` CLI installed — needs `~/.gemini/settings.json`):
```
portaw router enable --host gemini
```
Then start Gemini, submit the same prompt. Confirm the `paw router:`
`additionalContext` block appears with `hookEventName: BeforeAgent` (NOT
UserPromptSubmit). → flip CLAUDE.md Phase-2 Gemini box / spec §15 "schema-verified"
→ "live". `portaw router disable --host <h>` to clean up.

---

## ◐ E. skill-router v2 dogfood — PASSIVE, no paste (DOGFOOD #4)

No fresh-session prompt. The v2 hook (in `~/.claude/hooks/`, **standalone, NOT paw**)
logs passively to `~/.claude/hooks/.router-log.jsonl`. Just **use Claude Code
normally 2-3 days**, then come back and analyze: signal-fire histogram, strength
dist, thrash nav-count, used/ignored rate, FP candidates → tune
`THRASH_MIN`/`STRENGTH`/`PRIMER_MIN` before building v3. → memory
`project_skill_router.md`. (Analyzer script still to write when data exists.)

---

## ⚠ F. web-research load-all remainder — HOST/KEY-blocked (DOGFOOD #8)

CC lane DONE (Fetch demoted on CC, Scrapling = capability rung, `measured`). What's
left can't run on this box:
- **Load-all-host value (Codex/Gemini):** does Fetch's 259-idle buy a digest-fetch
  they lack natively? Needs a Codex/Gemini host — run guides 01-02 there, OR check
  live whether native fetch digests on that host.
- **Fetch per-host `--print-config`:** capture the real block per host (currently
  canonical-README shape only).
- **Optional-MCP def-token counts (searxng / exa / firecrawl):** BLOCKED on a key or
  running instance — dump the live def JSON, then `py bench/_fetch_def_count.py`-style
  tiktoken it. Until a key exists = honest prose estimate only, NOT `calculated`.

When a host/key appears: same paste pattern as A/B (guides 01-03) on that host.

---

## Aggregation cheat-sheet (controlling session, after fresh runs)
```
portaw bench list --agent claude                 # newest ids
portaw bench ab <baseline_id> <treated_id>       # per A/B pair
py bench/_count_tokens.py bench/out/<lane>-*.md   # web-research deterministic (01-03)
```
Provenance: `measured` ONLY if ≥3 trials + stable range + completeness passed; else
`estimated` + "n=1, directional". Record verdict in `registry/deep-vet.md`, numbers
in `registry/sets.json`. Full rules: `bench/guides/00-INDEX.md`.
