# Bench guides — per-session runbook (don't get lost)

> **Setup once:** paw must be installed for the `portaw` command to exist —
> `py -m pip install -e .` from the repo root (done 2026-06-08). If `portaw` is
> still "not recognized" (Scripts dir not on PATH), use the PATH-independent form
> **`py -m portaw ...`** from the repo root instead — identical behavior.


Each numbered file is ONE fresh session's job. The agent in that session has NO
memory of anything else — the file is fully self-contained. You drive by pasting,
into a FRESH session:

> Follow `bench/guides/NN-*.md` exactly. Do only what it says, then stop and report.

Then come BACK to your controlling session (this one, with context) to run the
diff/aggregation steps below. Tick each guide in the table as you finish it.

## Order (by leverage)

| # | Guide | Session type | Needs |
|---|---|---|---|
| 01 | webresearch-A-native | fresh ×3 | nothing (native WebFetch) |
| 02 | webresearch-B-fetch | fresh ×3 | `portaw install web-research` first |
| 03 | webresearch-C-scrapling | fresh ×3 | `pip install "scrapling[all]" && scrapling install` |
| 04 | codegraph-off (baseline) | fresh ×3 | codegraph + semble removed from host |
| 05 | codegraph-on | fresh ×3 | `portaw install efficiency-starter` + `codegraph init -i` |
| 06 | semble | fresh ×3 | `uv tool install semble` + semble in host cfg |
| 07 | compressor-off (baseline) | fresh ×3 | rtk hook disabled, no headroom |
| 08 | rtk-on | fresh ×3 | rtk hook installed |
| 09 | headroom-on | fresh ×3 | `pip install headroom-ai` (proxy/lib form, NOT MCP); rtk off |
| 10 | installs | single session | per-set install + verify (no isolation needed) |

web-research (01-03) = the priority blocker (set #5). Do those first.

**Each A/B group shares ONE baseline:** code-intel = 04 baseline vs 05/06 treated;
output-compression = 07 baseline vs 08/09 treated. Run all lanes of a group in the
SAME repo + commit/state, same model, or the diff is noise.

## The validity rules (READ — these are WHY the numbers are trustworthy)

paw's honesty knife: a number you can't defend is worse than no number. Two levers,
very different validity:

1. **idle_def_tokens (already done, calculated):** tiktoken on the verbatim MCP
   def JSON. HIGH validity — deterministic, exact. NOT re-measured here.
2. **delta_pct (runtime, what these guides measure):** NOISY. ccusage session-diff
   has cache noise (paw dropped it for rtk in favor of command-level instrumenting)
   + agent non-determinism (n=1 = anecdote). Defensible ONLY with:
   - **Same model every run.** Mixing Opus/Sonnet skews tokens → invalid.
   - **≥3 trials per lane.** Report MEDIAN + range, never a single point. If the
     range is wider than the delta between lanes, the result is INCONCLUSIVE — say so.
   - **Cold cache.** Fresh session each trial; if back-to-back, wait >5 min (prompt
     cache TTL) so trial 2 doesn't read trial 1's cache.
   - **Completeness gate FIRST.** A lane that answered fewer/worse = DISQUALIFIED
     before you look at tokens. Fewer tokens by dropping needed content is NOT a win.

3. **web-research uses a HIGHER-validity primary measure** (guides 01-03): each lane
   SAVES the fetched content to `bench/out/<lane>-<url#>.md`, then
   `py bench/_count_tokens.py bench/out/*.md` tokenizes EXACTLY what entered context
   — deterministic, no ccusage/cache/side-model confound. ccusage is the secondary
   cross-check only. (codegraph/semble/rtk/headroom have no clean per-return artifact
   — their saving is "avoided tool-calls across a loop" — so for 04-08 ccusage
   multi-trial IS the lever; treat as directional, report range.)

## Aggregation / diff (run in THIS controlling session, after the fresh runs)

ccusage diff (all benches):
```
portaw bench list --agent claude        # newest session ids
portaw bench ab <baseline_id> <treated_id>
```
web-research deterministic (PRIMARY for 01-03):
```
py bench/_count_tokens.py bench/out/native-*.md     # lane A total
py bench/_count_tokens.py bench/out/fetch-*.md       # lane B total
py bench/_count_tokens.py bench/out/scrapling-*.md   # lane C total
```
Per lane: take the MEDIAN of 3 trials. Compare lanes ONLY after all passed the
completeness gate.

## Where results land (+ provenance honesty)

- `registry/sets.json` → the set's `token_profile.hosts.claude-code`:
  - `delta_pct` = the measured saving (+ = saved).
  - `provenance` = **`measured`** ONLY if ≥3 trials + stable range + completeness
    passed. Otherwise **`estimated`** with a note "n=1, directional". Do NOT write
    `measured` off a single run — that's the exact over-claim paw forbids.
- Note the run + verdict in `registry/deep-vet.md` (the set's section).
- web-research decision is PRE-MADE: if Fetch (B) ≤ native (A) on CC → demote Fetch
  on CC, lead with Scrapling/exa. See `bench/web-research-workload.md`.

## Bench-specific protocol docs (the guides condense these)
- web-research → `bench/web-research-workload.md`
- codegraph + semble → `bench/codegraph-workload.md`
- rtk + headroom → `bench/rtk-ab-workload.md`
