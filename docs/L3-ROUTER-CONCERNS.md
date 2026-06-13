  # L1-L3 open concerns (alpha, 2026-06-13)

  > Frozen opinion from session 2026-06-13. Re-evaluate — trust code, not guess.

  ## Critical

  ### Capture DETECTOR ≈ dead
  Bash fail→fix narrow, yields 0 on real transcripts. Moat not self-sustaining.
  - memory/detect.py _FAIL_RE: command-not-found, Traceback, error:, fatal:, assert, Killed, OOM
  - Real failures: "exit code 1", "tool returned non-zero" — none match
  - Fix: widen detector OR accept manual add + harvester as main path
  - Proven path: curate mistakes-index → memory harvest --confirm

  ### Recall silent failure on empty RetrievalContext  — [CONFIRMED + partly mitigated 2026-06-13]
  Empty stacks/project_id drops stack:/project: lessons silently. Looks like ranking miss, is context bug.
  - context.py host_context() from cwd markers
  - Empty ctx → scoped lessons dead, no error
  - memory recall CLI fixed (real cwd). Hook path?
  - HIT LIVE in the gold-set harness: a bare RetrievalContext() scored 75% while the
    real-ctx run scored 100% — the misses were ALL scoped lessons filtered pre-rank.
  - Mitigated for measurement: bench/_eval_recall.py now derives host_context + a
    presence-guard fails loudly on corpus drift. STILL OPEN: a runtime diagnostic when
    host_context drops scoped entries (the live hook path has no such warning yet).

  ### Harvester orphaned project-scoped lessons  — [RESOLVED 2026-06-13, bc60b0e]
  Default project_id "curated" tagged unclassified lessons `project:curated` — a name no
  host_context derives, so they were eligible nowhere. 8 live lessons were dead this way.
  - Fix: harvest default project_id None → unclassified falls to `universal` (trust gate
    still withholds unproven ones); explicit --project still scopes. 8 live lessons retagged.

  ### Gemini adapter never live-verified
  - Codex = LIVE (config.toml, host-turn proof)
  - Gemini = schema + unit only (BeforeAgent)
  - If event name or JSON differs → silent no-op

  ## Medium

  ### Router demotion silent
  5 suggestion 0 conversion → set gone. No signal.
  - router outcomes exposes, manual only
  - Fix: mention in router status

  ### Injection threshold tuning  — [evidence 2026-06-13, gold-set]
  - Pinned: 300 tok SessionStart. General: 400 tok, 5 items.
  - 26 entries growing. Universal pool (16) competitive.
  - Are items injecting? or floor too high?
  - gold-set answer: items DO inject (proven universal / stack / project lessons surface,
    avg ~32 inject-tok) and silence holds (clean 100%, off-topic + unproven-universal
    correctly withheld). Floor is NOT too high for trusted entries. The only non-surface
    is the trust gate withholding unproven universals — by design, not a tuning miss.

  ### Session dedup fidelity
  Seen IDs in L3 sessionlog. Log rotate/clear → repeat N turns.
  - Fix: ttl-based dedup

  ## Minor

  ### Entry metadata quality uneven
  Old entries: empty symbols/paths, no trigger_terms. Recall = f(metadata).
  - Organic. New add prompts for symbols.

  ### Project memory as dead artifact in repo
  .paw/memory/project.jsonl in VCS. Clone without paw → noise.
  - Accept: paw reads it

  ### Embed tier-2 silent misses
  ONNX missing → silent TF-IDF floor, no error.
  - Fix: stderr log in hook path

  ## Not concerns (fine)

  - Silence-default injection: 5 pinned visible, not overwhelming
  - Router no spam: demotion gates work
  - L3 anchor: zero-setup matching works
  - State drift: doctor catches

  ## Open question

  > portaw ui — build now (tracks schema churn) or wait Phase-1 close? Owner leaning wait.