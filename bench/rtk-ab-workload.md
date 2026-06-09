# rtk A/B bench — ready-to-run workload

Goal: get the HARD number for `efficiency-starter`'s rtk anchor — does rtk
actually cut tokens, and by how much vs its peers (context-mode / lean-ctx /
snip / ecotokens)? `portaw bench` does the math; this file is the controlled
workload so the comparison is valid.

> Why a fixed workload: `bench ab` diffs two Claude sessions. If the two runs
> do different work, the delta is noise. Vary ONLY the tool; keep the task byte-identical.

## Protocol

1. Pick a repo with real build/test output (a Rust or TS project is ideal —
   rtk compresses `cargo test` / `tsc` / `pytest` / `git` output hardest).

2. **Run A — rtk OFF.** Disable the rtk PreToolUse hook (comment it out in the
   host settings, or run a Claude session in a profile without it). In a FRESH
   session, paste the workload below verbatim. Let it finish.

3. **Run B — rtk ON.** Re-enable rtk (`rtk init -g` installs the hook). In
   another FRESH session, paste the SAME workload verbatim. Let it finish.

4. Diff:
   ```
   portaw bench list --agent claude        # find the two session ids (newest two)
   portaw bench ab <A_id> <B_id>           # A = off (baseline), B = on (treated)
   ```
   Positive `saved` on totalTokens / inputTokens / cacheCreationTokens = rtk win.
   (rtk compresses command OUTPUT, which re-enters context as input/cache — that's
   where the delta lands, not outputTokens.)

5. **Peer comparison:** repeat Run B with each rival in turn, same workload.
   Lowest treated-total wins the anchor slot. Record in `registry/deep-vet.md` §1 S1 / §6.
   Rival lanes: context-mode, lean-ctx, snip, ecotokens, and **headroom**
   (chopratejas — claims 60-95% vs rtk's measured 26.3%; run it in proxy/lib form
   so it stays 0-idle-def like rtk = fair head-to-head. Note headroom adds a
   Python+model dep + latency; weigh the compression ratio AGAINST that, not in
   isolation — a leaner tool that compresses slightly less can still win on net).

## Workload (paste verbatim into a fresh Claude session)

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

Each step produces bulky command output — exactly what rtk-class compressors
target. Identical steps both runs ⇒ the only variable is the tool ⇒ valid A/B.

## Caveats

- Same model both runs (ccusage tags model; mixing Opus/Sonnet skews tokens).
- Same repo state both runs (commit or stash first so git output matches).
- Cache warmth differs run-to-run; do 2-3 pairs and average if the delta is small.
- This measures token spend, not task quality. A tool that saves tokens but
  drops needed detail is NOT a win — sanity-check both runs reached step 6.
