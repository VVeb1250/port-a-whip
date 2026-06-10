# Handoff → next session (port-a-whip / paw)

> Written 2026-06-08 at the end of a good session. Read this FIRST (cold start),
> then `CLAUDE.md` (full state), `registry/deep-vet.md` §6 (candidate decisions),
> `DOGFOOD-PENDING.md` (controlled runs). The repo is indexed with codegraph —
> use `codegraph_explore` instead of grep/read loops.

---

## Part 1 — The concepts to KEEP (don't relearn these the hard way)

### What paw IS (the one-line identity)
paw curates **quality tool SETS + a capability router + lesson-memory** for coding
agents (Claude Code, Codex, Gemini, Aider). Its **ONE curation criterion**:

> **a tool earns a place only if it REDUCES TOKENS or IMPROVES CONTEXT QUALITY.**

paw is **NOT a general installer** (that's Smithery/mcpm). Every time a request
drifts toward "just install X because it's handy," that's the Smithery line — hold
it. **"Useful to the user" ≠ "on-thesis."** A set earns its place via the
token/quality lever, never via "I want it." Cross this line and paw becomes a
generic installer with no reason to exist.

### What a GOOD HARNESS is (the frame paw serves)
A coding-agent harness has **5 components** — paw exists to fill the gaps hosts
leave:
1. **Tools** — what the agent can DO (MCP/CLI). paw curates the lean ones.
2. **Knowledge** — what it KNOWS (codegraph=in-repo, Context7=lib docs, web-research=open web). Three non-overlapping knowledge surfaces.
3. **Observation** — what it SEES (tool output). rtk compresses it.
4. **Action** — how it acts (hooks, exec).
5. **Permissions** — what it's ALLOWED (the gap NO registry covers → secure-agent set: nah/gitleaks/osv/infisical).

paw's three layers map onto this: **L1 curated sets** (Tools+Knowledge+Permissions),
**L2 capability router** (right tool surfaces at the right prompt), **L3 lesson-memory**
(the durable MOAT — not built yet, Phase 3).

### N1 ceiling (the hard constraint behind every set decision)
- Load-all hosts (**Codex/Gemini**) load EVERY MCP tool-def at startup → idle token cost. **Claude Code lazy-loads** → idle ≈ 0.
- Keep **≤2-3 active MCP servers per set** on load-all hosts. **Count MCP defs only** — CLI/hook/skill = 0 def = FREE against the ceiling.
- Prefer CLI/hook over MCP when capability is equivalent. This is why secure-agent (0 MCP) and design-quality (0 MCP) are "N1-free."
- **Host-conditional anchors** resolve the tension: efficiency-starter uses codegraph on CC (idle free, richer) / semble on load-all (509<1615 idle). Same pattern available to any set.

### The honesty knife (token_profile v2 — the rtk-over-claim lesson, encoded)
Provenance enum, machine-readable, **set provenance = weakest link**:
| provenance | means |
|---|---|
| `measured` | paw ran an A/B (ccusage / rtk-gain) on the canonical workload |
| `calculated` | tiktoken cl100k on the **verbatim live MCP def JSON** the host loads — a real count, NOT a rule-of-thumb |
| `vendor-claimed` | vendor docs, flagged, never laundered into "measured" |
| `estimated` | reasoned, no measurement — the honest floor |
| `neutral` | provably 0 (no MCP defs by construction) |

Two opposing numbers: `delta_pct` (runtime saved, +) vs `idle_def_tokens` (always-on
load-all cost, 0 on CC). A set can save at runtime AND cost idle — record both.

### Honesty rules that BIT this session (live by them)
1. **Never fake `calculated` from paraphrased text.** WebFetch summarizes source → it cannot yield a clean verbatim def. Only tokenize def JSON you captured exactly (Fetch worked because Pydantic→schema is mechanical; searxng/exa did NOT). Mark `estimated`, not `calculated`.
2. **Never launder "didn't find it" into "confirmed false."** Firecrawl: "no subset switch FOUND IN README" (absence of evidence) ≠ "firecrawl has no subset" (proof). The decision can still be safe; the certainty wording must not over-reach.
3. **cheapest-idle ≠ most-additive.** Fetch MCP is the leanest anchor (259 tok) BUT duplicates CC's native WebFetch (which already does URL→md→digest). A lean tool that re-does a native capability is not a win. Verify additivity, not just idle cost, before promoting an anchor.
4. **Bench rivals, don't believe claims.** semble (98%) and headroom (60-95%) out-claim the measured anchors (codegraph / rtk 26.3%). Both are set up for A/B, neither swapped on the claim.

### The principled LINES drawn this session (reuse the reasoning, not just the verdict)
- **web-research = research PRIMITIVES the agent composes (search→fetch→extract, sources auditable) ≠ answer-product connectors (perplexity-class) that synthesize with opaque sourcing.** This is why exa is IN (optional) and perplexity is OUT — even though BOTH are paid SaaS APIs. The split is **primitive-vs-answer-product, NOT paid-vs-free.** Consistent with context-quality's anti-hallucination axis (auditable > black-box). When a discriminator can't cleanly separate two candidates, articulate the REAL line or sidestep — don't inherit "the drop-list said so."

---

## Part 2.5 — UPDATE 2026-06-10 (L3 BUILT)

**Phase 3 lesson+project memory is built** (`portaw/memory/`, 150 tests). Design =
[docs/L3-DESIGN.md](docs/L3-DESIGN.md) (R1-R12 + anchor weighting + scope + 14-step
build order — READ IT before touching L3). What landed:
- **schema/store** — jsonl, global `~/.paw/memory` + project `.paw/memory`; content-hash
  id = free cross-project dedup; atomic write; malformed-tolerant; archive file.
- **retrieval** — HYBRID reusing the ONE kernel (`kernel.route`, semantic) + anchor
  overlap (path/symbol = zero-setup structural floor; codegraph node = present-only
  bonus) + ACT-R activation (recency×frequency). Silence-default.
- **injection** — silence-biased, per-type threshold (lesson low / project high),
  budget cap, pinned-first; wired into `adapters/router.py` (memory injects alongside
  set hits, fail-safe).
- **capture/gate** — `FailureSignal` → applicability auto-tag (universal/stack/project)
  → integrity gate (scope-scaled bar §7) → upsert. Cross-host `paw_lesson` contract.
- **consolidate/seed** — async "dream" (merge/promote/decay-archive); ADR-harvest v1.
- **hook wiring** — `memory enable/disable/status` wires `capture-hook` into the Stop
  event (reuses router's generic wiring; coexists with the UserPromptSubmit router).
- **dogfood (isolated HOME) PROVED the loop**: enable → Stop(capture) → UserPromptSubmit
  (router run) injects the just-captured lesson. **Fixed a real latent bug**: `main.py`
  lacked `import sys` → the live router CLI emitted nothing (NameError swallowed by its
  safe-except); now guarded by CLI-level CliRunner tests.

**Key design decisions made this session (don't relitigate):**
- lesson = GLOBAL store + applicability tag (universal/stack/project) + auto-promote on
  cross-project recurrence; project = project-scoped; preference DEFERRED (AGENTS.md/rulesync).
- anchor backbone weighted → **path+symbol = primary** (zero-setup, every host); codegraph =
  present-only multi-hop bonus; **graphify DROPPED** (LLM init token too high); embedding =
  lazy/optional (reuse skill-router model).
- "better than RAG" = structured+tiered+consolidated+graph-anchored recall, NOT a vector engine.
- RAG-Anything REJECTED (cloud-API + framework swallows the layer + doc≠code domain).

## Part 2 — Current state (2026-06-08)

- **6 sets** in `registry/sets.json` (schema 0.3.1): efficiency-starter, secure-agent, context-quality, design-quality (DRAFT), web-research (DRAFT, CC measured), **browser-automation (NEW, DRAFT)**.
- **73 tests pass.** Router L2 live (CC + Codex adapters built+tested; Gemini built, never fired live). token_profile v2 across all sets.
- **paw INSTALLED editable** (`pip install -e .`) → `portaw` on PATH; fallback `py -m portaw` (added `portaw/__main__.py`). PyPI wheel REBUILT @ 6 sets (twine PASS, clean-venv smoke PASS), still alpha-HOLD (no upload).
- **What happened this session (2026-06-08):**
  - jcode (1jehuang, Rust HOST) vs paw analysed → NOT a dup (different layer); L3-axis warning + GUI Phase-4 candidate jotted (deep-vet §7, CLAUDE.md).
  - browser-automation set #6 drafted (anchor browser-harness, 0 MCP def, refs verified).
  - PyPI rebuilt; FIXED a `verify` crash on null-binary skills (healthcheck.py, +2 tests).
  - Built `bench/guides/` (00-INDEX + 10 numbered per-session runbooks) + `bench/web-research-workload.md` + `bench/_count_tokens.py` (deterministic tiktoken counter).
  - **web-research CC A/B RAN** (deterministic): Fetch DEMOTED on CC (truncates), Scrapling = capability rung (ceiling 84% but discovery-cost-hidden), native baseline strong. provenance `measured`.
  - **codegraph CC deterministic proxy RAN**: ~97% less on relationship/impact Qs, ~4.8x MORE on show-one-file → question-type-dependent, no blanket delta. (artifacts `bench/out/`)
- codegraph index BUILT for this repo. semble installed. tiktoken installed (measurement only, NOT a paw runtime dep — runtime deps stay click>=8.1, tomlkit>=0.13).

---

## Part 3.0 — NEXT (2026-06-10, supersedes the 2026-06-08 list below)

1. ~~**NL failure→fix detector** (`portaw/memory/detect.py`)~~ **DONE 2026-06-10.** Reads the
   CC transcript (Stop `transcript_path`), pairs an errored Bash call with a later succeeding
   NEAR-VARIANT (Jaccard ≥0.34, inline `-c/-e` blobs + >150-char one-offs skipped) → low-conf
   `FailureSignal`. Validated on a real transcript (54 Bash calls): 0 noise after tightening.
   ⚠️ **DOGFOOD FINDING 2026-06-10:** the detector yields **0 signals on 5 real transcripts**
   (incl. a 4.7MB one) → the auto-capture half is effectively inert in practice. Real fail→fix
   is usually cross-tool (Bash→Edit/PowerShell), >4 calls apart, not a near-variant, or a long
   piped one-off — all skipped. The HONEST conclusion: high-value lessons come from REFLECTION,
   not Bash command-diffing (cf. the user's `mistakes-index.md` — semantic, curated). So:
   (a) **manual `memory add` is the proven, working capture path** (conf 0.9 → trusted → injects;
   demoed live); (b) ~~**NEXT high-value build = a `mistakes-index.md` → lessons harvester**~~
   **DONE 2026-06-10** (`portaw/memory/harvest.py` + `memory harvest` CLI, 13 tests): bullet grammar
   `- [SEV] [id] trigger → fix (xN, date) →detail` → global lessons (sev→confidence, xN→recurrence,
   section→applicability, →detail→detail_ref, code-spans→terms/symbols). Idempotent re-key by
   content-hash id. LIVE on the real Thai index: 18 lessons, applicability correct, re-run not
   inflated, full harvest→recall loop proven; (c) loosen the Bash detector only if (b) proves
   insufficient — (b) works, so detector stays as-is.
2. ~~**wire into real `~/.claude`** + **kernel-unify**~~ **DONE 2026-06-10.** capture-hook wired
   into CC Stop (settings.json, coexists w/ mistake-learning). kernel-unify resolved the
   inject collision WITHOUT a second hook: the live skill-router now (a) delegates ranking to
   paw `kernel.ranking.route` (ONE ranker; inline = zero-paw fallback, pinned by
   `tests/test_skill_router_parity.py` 14/14) and (b) surfaces paw memory(+sets) via
   `router.paw_block` through that one hook. **Memory inject is LIVE end-to-end.** Source =
   `integration/skill-router.py` (edit there + copy over; `~/.claude/hooks/*` is nah hard-
   protected — `nah trust` does NOT clear it, copy from your own shell). See integration/README.
   ⚠️ `nah trust "…skill-router.py"` is still set on this box — `nah forget` to re-tighten once
   you're done deploying.
3. **Codex/Gemini live** — **Codex router is LIVE-VERIFIED 2026-06-10**:
   `portaw router enable --host codex` patched the real `~/.codex/config.toml`
   (`config.toml.paw-bak-20260610T080120Z`), `portaw router status --host codex`
   reports `wired=True`, and `portaw doctor` parse-validates the Codex TOML. The
   console hook path was smoke-tested with byte stdin:
   `portaw router run --host codex` emits `hookSpecificOutput.additionalContext`
   with `hookEventName=UserPromptSubmit`. **Host-turn proof complete:** in a fresh
   Codex session the injected `paw router:` block appeared and suggested
   `secure-agent` + `design-quality`; Codex reported the event as consistent with
   `UserPromptSubmit` (block visible after the prompt; event name not printed in
   the human-visible block).
   **Do NOT overclaim L3 capture yet:** capture Stop `_STOP_EVENT` remains
   best-guess for Codex/Gemini; verify before enabling memory capture there.
   Gemini router remains schema/unit-tested only. Cross-host = the portability
   moat proof.
4. ~~**embedding tier-2** — lazy/optional, reuse the skill-router multilingual model.~~ **DONE
   2026-06-10** (`portaw/kernel/embed.py`, opt-in `[embed]` extra, 9 tests). MiniLM ONNX ported from
   skill-router embed.py, skill-dict→Capability. Lazy (fires only on tier-1 miss) + fail-safe
   (unavailable → TF-IDF floor, runtime deps unchanged). Injectable `embed_fn` into `route()` +
   `recall()` (default None → parity 14/14 held). Reuses `~/.claude/hooks/models` (or
   `$PAW_EMBED_MODEL_DIR`). `memory recall --embed` to exercise. LIVE: Thai→English cross-lingual
   match proven (cosine 0.592 real pair, honest {} below 0.30 floor).
5. **DOGFOOD-PENDING new item** — bench symbol+path-anchor precision vs codegraph multi-hop
   (is the multi-hop bonus worth its setup? expect ~80/20 in favor of the zero-setup floor).

## Part 3 — Tasks for next session (prioritized)

1. ~~**[unblocks web-research → verified] Run the 3-lane A/B**~~ **CC LANE DONE 2026-06-08.** Result: native WebFetch (16,182 tok, complete) beats Fetch (2,858 but TRUNCATED→incomplete → **DEMOTED on CC**) and broad-Scrapling (21,025). Tight-selector Scrapling = 2,599 (~84% < native, complete) = ceiling lever real BUT hides discovery cost → **CC = capability rung, delta_pct null** (no general one-shot saver). provenance `measured`. Full writeup: deep-vet.md web-research § + sets.json CC token_profile. **STILL OPEN:** load-all-host (Codex/Gemini) value = Fetch's 259-idle buys a digest-fetch they lack natively (calculated, not yet A/B'd live); per-host --print-config for Fetch; optional-MCP def-token counts (need keys).
2. ~~**Draft browser-automation set**~~ **DONE 2026-06-08** → registry set #6. Anchor = browser-harness (browser-use/browser-harness, MIT 14.5k★, skill+CDP, 0 MCP def, self-healing, cross-host CC+Codex) > playwright-MCP (47 def, rejected). Framed lean-vs-heavy. neutral idle, delta_pct null (honest — capability-class). router surfaces live. **REMAINING (DRAFT→verified):** install-test end-to-end (install is agent-driven: setup-prompt→install.md, NOT yet run); confirm/capture real steps; Gemini support unverified. deep-vet §6 (+ §7 jcode/GUI notes).
3. ~~**PyPI: rebuild before any upload.**~~ **DONE 2026-06-08** — rebuilt fresh wheel+sdist at **6 sets** (added browser-automation), `twine check` PASSED, clean-venv smoke PASSED, wheel verified to ship sets.json. Fixed a `verify` crash on null-binary skills (healthcheck.py, +2 tests, 73 pass). **Still alpha-HOLD — NOT uploaded** (L3 not built; name+0.3.0 claim irreversible). When Phase-1 closes: `twine upload dist/*` (PyPI token); TestPyPI rehearsal first.
4. **Phase-3 L3 lesson-memory (the MOAT).** Study prior-art FIRST, don't rebuild: headroom `learn` (failed-session→CLAUDE.md), OpenViking (tiered load-on-demand context DB), claude-mem. deep-vet §6 "Phase-3 L3 prior-art." Do NOT rebuild the author's mistake-learning hook on CC — port to Codex/Gemini instead.
5. **Remaining controlled/key-blocked runs** — all in `DOGFOOD-PENDING.md` (8 items): semble-vs-codegraph A/B, headroom-vs-rtk A/B, codegraph runtime delta, skill-router v2 dogfood, Gemini/Codex router live-fire, design-quality install-test, secure-agent/context-quality install-test, web-research A/B + live def-dumps.

---

## Part 4 — Environment constraints (carry these, they're load-bearing)
- **Windows: `py` only** (NEVER python/python3). PowerShell syntax, `\` paths. NO `??` null-coalesce in PS 5.1 (use if/else).
- **Bash tool CWD resets between calls** — `cd /c/Users/VVeb1250/.claude/port-a-whip && ...` each time (rtk hook also mangles backslash paths → use forward-slash absolute).
- **Secrets via env `${VAR}`/.env, NEVER plaintext** (FIGMA_TOKEN/EXA_API_KEY/FIRECRAWL_API_KEY). Never string-edit config — parse→merge→validate (Python/ConvertTo-Json). **No `shell=True` on community strings** (RCE — paw install steps are curated/pinned/printed-manual, not auto-exec).
- **Caveman mode full** (drop articles/filler; code/commits/security normal). Use advisor before substantive work + before declaring done.
