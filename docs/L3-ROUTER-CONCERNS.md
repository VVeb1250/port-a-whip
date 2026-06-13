  # L1-L3 open concerns (alpha, 2026-06-13)

  > Frozen opinion from session 2026-06-13. Re-evaluate — trust code, not guess.

  ## Critical

  ### Capture DETECTOR ≈ dead  — [decided + widened 2026-06-13]
  Bash fail→fix narrow, yields 0 on real transcripts. Moat not self-sustaining.
  - memory/detect.py _ERR_PATTERNS: command-not-found, Traceback, error:, fatal:
  - Real failures: "exit code 1", "non-zero" — none matched before
  - DONE: widened _ERR_PATTERNS ("exit code"/"exit status"/"non-zero"/"error:"). SAFE —
    the false-LESSON filter is the fail→fix near-variant pairing (Jaccard ≥ min_overlap)
    downstream, not this list; a wider list catches MORE real failures, never invents
    lessons. +2 tests (test_memory_detect).
  - DECISION: detector = best-effort FLOOR; proven capture path = manual `memory add` +
    `memory harvest`. The deep limit isn't the markers — agents rarely retry a near-
    identical command in real transcripts, so the PAIRING itself rarely fires. Not chasing
    NL detection (poison risk).

  ### Recall silent failure on empty RetrievalContext  — [CONFIRMED + mitigated 2026-06-13]
  Empty stacks/project_id drops stack:/project: lessons silently. Looks like ranking miss, is context bug.
  - context.py host_context() from cwd markers
  - Empty ctx → scoped lessons dead, no error
  - HIT LIVE in the gold-set harness: a bare RetrievalContext() scored 75% while the
    real-ctx run scored 100% — the misses were ALL scoped lessons filtered pre-rank.
  - DONE runtime diagnostic: `context.scoped_drop_report(entries, ctx)` names tag→count of
    scoped lessons this ctx makes ineligible. Surfaced two ways: `memory recall --explain`
    (stderr) and the live hook via `PAW_DEBUG=1` (off by default — a per-prompt hook must
    not spam). +6 tests (test_memory_context).
  - FOUND VIA --explain → SYSTEMIC BUG FIXED 2026-06-13: `stack:pytest` lessons were
    permanently DEAD (no marker derives "pytest"). Root cause = the capture classifier's
    `_STACK_KEYWORDS` (pytest/react/django/jest/cargo…) was a DIFFERENT vocabulary from the
    `STACK_MARKERS` values `detect_stacks` emits (python/typescript/rust…) — so MOST stack:*
    tags the capture path minted were eligible nowhere, and every pytest run re-minted one.
    Fix: `_STACK_KEYWORDS` is now a map keyword→canonical-stack (pytest→python, react→
    typescript…), values pinned ⊆ STACK_MARKERS by a test. 3 live `stack:pytest` lessons
    retagged → `stack:python` (backup made); they now inject correctly in this python repo.
  - SIBLING in PROJECT store, found via live SessionStart fire 2026-06-13: 7 of 11 project
    lessons were tagged `project:project` (a literal placeholder scope leaked into applicability
    by an OLD seed path; current `memory add` is correct → `project:{cwd.name}`). host_context
    derives `port-a-whip`, never `project` → those 7 paw decisions were eligible NOWHERE, so the
    wake-pack could only draw from the 4 correctly-tagged ones. Retagged → `project:port-a-whip`
    (backup made); all 11 eligible now. NOTE: project memory is repo-scoped by design — a
    SessionStart fired OUTSIDE the repo finds no project store (pins are global → still fire),
    which looks like a digest miss but is correct scoping. Test the digest from inside the repo.

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

  ### Router demotion silent  — [RESOLVED 2026-06-13]
  5 suggestion 0 conversion → set gone. No signal.
  - DONE: `router status` now lists demoted sets + the `router outcomes --forget <name>`
    undo. First live run already surfaced efficiency-starter + context-quality demoted
    (suggested ≥5, never converted) — previously invisible.

  ### Injection threshold tuning  — [evidence 2026-06-13, gold-set]
  - Pinned: 300 tok SessionStart. General: 400 tok, 5 items.
  - 26 entries growing. Universal pool (16) competitive.
  - Are items injecting? or floor too high?
  - gold-set answer: items DO inject (proven universal / stack / project lessons surface,
    avg ~32 inject-tok) and silence holds (clean 100%, off-topic + unproven-universal
    correctly withheld). Floor is NOT too high for trusted entries. The only non-surface
    is the trust gate withholding unproven universals — by design, not a tuning miss.

  ### Session dedup fidelity  — [RESOLVED 2026-06-13]
  Seen IDs in L3 sessionlog. Log rotate/clear → repeat N turns.
  - DONE: per-id ttl dedup. Each id stores its inject timestamp; `seen` counts only ids
    within `_DEDUP_TTL_S` (1 day). Bounds the file (stale ids drop on next write instead
    of living for the file's whole life) and lets a lesson re-surface a day later (its
    earlier inject has scrolled out → re-showing is help, not rot). Legacy `{"ids":[…]}`
    still reads (folded in at file mtime). +7 tests (test_memory_sessionlog).

  ## Minor

  ### Entry metadata quality uneven  — [tooled 2026-06-13]
  Old entries: empty symbols/paths, no trigger_terms. Recall = f(metadata).
  - DONE: `memory health` reports the unevenness (lessons missing terms/symbols/paths +
    WEAK = body-only-recall count) and `--backfill` derives trigger_terms FROM THE BODY
    (derivation only, never invented → can't poison; backup first). Real store: 28 lessons,
    1 weak → backfilled. Symbols/paths stay organic (can't be invented safely). `health.py`,
    +7 tests.

  ### Project memory as dead artifact in repo
  .paw/memory/project.jsonl in VCS. Clone without paw → noise.
  - Accept: paw reads it

  ### Embed tier-2 silent misses  — [RESOLVED 2026-06-13]
  ONNX missing → silent TF-IDF floor, no error.
  - DONE: `lazy_embedder` warns once per process to stderr when tier-2 is wanted but
    unavailable — gated on `PAW_DEBUG` (PAW_DEBUG check FIRST so the hot path never pays
    `available()`; keeps it lazy when not debugging). Names WHY (model files vs libs) + the
    `[embed]` extra. Pairs with the #4 PAW_DEBUG channel.
  - POSITIVE half added 2026-06-13 (live fire couldn't tell MiniLM from floor): `memory recall
    --explain` now prints a `retrieval tier:` line — TF-IDF-only / +MiniLM-wired / requested-but-
    unavailable. The earlier #17 warning only spoke on FAILURE, so a working embed and a forgotten
    `--embed` flag looked identical (a TF-IDF score is indistinguishable from an embed cosine).
    Root cause the live test actually hit: CLI recall wires `embed_fn` ONLY under `--embed`; the
    test ran `--explain` alone → pure floor. The tier line makes that unmissable.

  ## Not concerns (fine)

  - Silence-default injection: 5 pinned visible, not overwhelming
  - Router no spam: demotion gates work
  - L3 anchor: zero-setup matching works
  - State drift: doctor catches

  ## Open question

  > portaw ui — build now (tracks schema churn) or wait Phase-1 close? Owner leaning wait.