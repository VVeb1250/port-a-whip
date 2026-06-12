# Handoff → next session (port-a-whip / paw)

> Read this FIRST (cold start), then `CLAUDE.md` (full state), `registry/deep-vet.md` §6
> (candidate decisions), `DOGFOOD-PENDING.md` (controlled runs). Repo is codegraph-indexed
> — use `codegraph_explore` instead of grep/read loops.

---

## Part 1 — The concepts to KEEP (don't relearn these the hard way)

### What paw IS (one-line identity)
paw curates **quality tool SETS + a capability router + lesson-memory** for coding agents
(Claude Code, Codex, Gemini, Aider). ONE curation criterion:

> **a tool earns a place only if it REDUCES TOKENS or IMPROVES CONTEXT QUALITY.**

paw is **NOT a general installer** (that's Smithery/mcpm). Every "just install X because it's
handy" is the Smithery line — hold it. **"Useful to the user" ≠ "on-thesis."** A set earns its
place via the token/quality lever, never via "I want it." Cross this line and paw becomes a
generic installer with no reason to exist.

### What a GOOD HARNESS is (the frame paw serves)
5 components — paw fills the gaps hosts leave:
1. **Tools** — what the agent can DO (MCP/CLI). paw curates the lean ones.
2. **Knowledge** — what it KNOWS (codegraph=in-repo, Context7=lib docs, web-research=open web). Three non-overlapping surfaces.
3. **Observation** — what it SEES (tool output). rtk compresses it.
4. **Action** — how it acts (hooks, exec).
5. **Permissions** — what it's ALLOWED (the gap NO registry covers → secure-agent set: nah/gitleaks/osv/infisical).

paw's layers map on: **L1 sets** (Tools+Knowledge+Permissions), **L2 router** (right tool at right
prompt), **L3 lesson-memory** (the durable MOAT).

### N1 ceiling (hard constraint behind every set decision)
- Load-all hosts (**Codex/Gemini**) load EVERY MCP tool-def at startup → idle token cost. **CC lazy-loads** → idle ≈ 0.
- Keep **≤2-3 active MCP servers per set** on load-all hosts. **Count MCP defs only** — CLI/hook/skill = 0 def = FREE.
- Prefer CLI/hook over MCP when capability is equivalent. Why secure-agent + design-quality are "N1-free."
- **Host-conditional anchors** resolve the tension: efficiency-starter = codegraph on CC / semble on load-all (509<1615 idle).

### The honesty knife (token_profile v2 — the rtk-over-claim lesson, encoded)
Provenance enum, machine-readable, **set provenance = weakest link**:
| provenance | means |
|---|---|
| `measured` | paw ran an A/B (ccusage / rtk-gain) on the canonical workload |
| `calculated` | tiktoken cl100k on the **verbatim live MCP def JSON** — a real count, NOT rule-of-thumb |
| `vendor-claimed` | vendor docs, flagged, never laundered into "measured" |
| `estimated` | reasoned, no measurement — the honest floor |
| `neutral` | provably 0 (no MCP defs by construction) |

Two opposing numbers: `delta_pct` (runtime saved, +) vs `idle_def_tokens` (always-on load-all cost, 0 on CC). A set can save at runtime AND cost idle — record both.

### Honesty rules that BIT (live by them)
1. **Never fake `calculated` from paraphrased text.** WebFetch summarizes → no clean verbatim def. Only tokenize def JSON captured exactly. Else mark `estimated`.
2. **Never launder "didn't find it" into "confirmed false."** Absence of evidence ≠ proof. Decision can be safe; certainty wording must not over-reach.
3. **cheapest-idle ≠ most-additive.** Fetch MCP is leanest BUT duplicates CC's native WebFetch. A lean tool re-doing a native capability is not a win. Verify additivity, not just idle cost.
4. **Bench rivals, don't believe claims.** semble (98%) and headroom (60-95%) out-claim the measured anchors (codegraph / rtk 26.3%). Neither swapped on the claim.

### The principled LINE (reuse the reasoning, not just the verdict)
**web-research = research PRIMITIVES the agent composes (search→fetch→extract, sources auditable)
≠ answer-product connectors (perplexity-class) that synthesize with opaque sourcing.** Why exa is IN
(optional) and perplexity OUT — even though BOTH are paid SaaS APIs. The split is
**primitive-vs-answer-product, NOT paid-vs-free.** Consistent with context-quality's anti-hallucination
axis (auditable > black-box). When a discriminator can't cleanly separate two candidates, articulate the
REAL line — don't inherit "the drop-list said so."

### L3 design decisions (stable defaults, NOT a gag order — see re-open rule)
> **Re-open rule:** these are recorded so you don't relearn them the hard way — NOT a ban on new thinking. Re-open a decision when (a) the owner changes direction, or (b) new evidence appears that wasn't on the table when it was decided. The discipline: answer the ORIGINAL rationale first (it's written here for a reason), then move — don't silently forget it, don't silently obey it.
- lesson = GLOBAL store + applicability tag (universal/stack/project) + auto-promote on cross-project recurrence; project = project-scoped; preference DEFERRED.
- anchor backbone weighted → **path+symbol = primary** (zero-setup, every host); codegraph = present-only multi-hop bonus; **graphify DROPPED** (LLM init token too high); embedding = lazy/optional.
- "better than RAG" = structured+tiered+consolidated+graph-anchored recall, NOT a vector engine. RAG-Anything REJECTED (cloud-API + framework swallows the layer + doc≠code domain).
- ⚠️ **L3 hard lines = cross-host portability + no-API/no-daemon/no-cloud** (don't move). **Scope broadened 2026-06-13** (owner): mistake-surfacing is one job, not the only one — also decision grounding, memory connection (typed edges), lifting weak/local models. NOT a hosted general-memory service. The line is the deps (no server/cloud), not the breadth.

---

## Part 2 — Current state (2026-06-13)

- **6 sets** in `registry/sets.json` (schema 0.3.1): efficiency-starter, secure-agent, context-quality, design-quality (DRAFT), web-research (DRAFT, CC measured), browser-automation (DRAFT).
- **346 tests pass** (216 base+hardening + 130 memoir-edges/wake-pack/sync/evidence-loops). Router L2 live (CC + Codex; Gemini built, never fired live). token_profile v2 across all sets.
- **R13 memoir edges (2026-06-13):** typed `relations` (superseded_by/contradicts/caused_by/related) reshape recall (suppress/contradict-drop/fan-out, no-op legacy); capture seeds only additive `related` (poison-safe); suppressive edges only from consolidation (`supersede_pairs` 6 guards) or `memory link`. Wake-pack project digest at SessionStart (≤150 tok, anti-hallucination). Dream cadence user-set, OFF default. ⚠️ all R13 tests use injected encoder → real-ONNX dogfood = DOGFOOD-PENDING #13.
- **All 3 layers built + dogfooded.** L3 = `portaw/memory/` (schema/store/retrieval/capture/harvest/detect/consolidate). Inject LIVE end-to-end via `integration/skill-router.py` (kernel-unify: ONE ranker, paw_block surfaces memory+sets).
- **paw INSTALLED editable** (`pip install -e .`) → `portaw` on PATH; fallback `py -m portaw`. PyPI wheel REBUILT @ 6 sets (twine PASS), **alpha-HOLD (no upload)**.
- codegraph index built for this repo. semble + tiktoken installed (measurement only, NOT runtime deps — runtime stays click + tomlkit).
- **Hardening audit round 2 (2026-06-11):** pinned bypasses recall floor; `memory recall` derives RetrievalContext; upsert merges pin+max-confidence; `memory pin/--unpin/list`; harvest preserves store pins + replaces reworded twin; store reads never crash; anchor path match needs `/` boundary; consolidate protects conf≥0.9; inject budget skips oversized item; embed cache keyed on model dir.

---

## Part 3 — LIVE next-actions (prioritized; done items live in CLAUDE.md roadmap)

### A. Single-source migration (user-gated) — THE next action
Replace the auto-loaded mistakes-index with paw L3:
1. pin 4 HIGH universals (py-command, path-backslash, ps-null-coalesce, bash-wsl)
2. `memory harvest --confirm` (real store)
3. `memory inject-enable all`
4. copy `integration/skill-router.py` over (user shell — `~/.claude/hooks/*` is nah hard-protected)
5. user disables mistakes-index auto-load in `~/.claude/CLAUDE.md`

> Known cost to fix later: on a full tier-1 miss the live CC process can load TWO MiniLM copies
> (skill-router's hooks/embed.py + portaw.kernel.embed) — unify like kernel-unify did for TF-IDF.
> ⚠️ `nah trust "…skill-router.py"` may still be set on this box — `nah forget` to re-tighten after deploying.

### B. Cross-host capture (the portability moat proof)
- Codex router = **LIVE-VERIFIED** (config.toml patched, status wired=True, host-turn proof). Gemini router = schema/unit only.
- **Do NOT overclaim L3 capture:** capture Stop `_STOP_EVENT` is best-guess for Codex/Gemini — verify event name + transcript format live BEFORE enabling memory capture there.

### C. Remaining controlled/key-blocked runs → `DOGFOOD-PENDING.md` (8 items)
semble-vs-codegraph A/B · headroom-vs-rtk A/B · codegraph runtime delta · skill-router v2 dogfood ·
Gemini/Codex router live-fire · design-quality install-test · secure-agent/context-quality install-test ·
web-research A/B + live def-dumps. **New:** bench symbol+path-anchor precision vs codegraph multi-hop
(is the multi-hop bonus worth its setup? expect ~80/20 for the zero-setup floor).

### D. Set verification (DRAFT → verified)
- web-research: load-all-host value (Fetch 259-idle buys a digest-fetch they lack natively) — calculated, not yet live A/B; per-host --print-config; optional-MCP def-token counts (need keys).
- browser-automation: install-test end-to-end (agent-driven setup-prompt→install.md, NOT yet run); Gemini support unverified.

### E. Phase-3 prior-art (before extending L3)
Study, don't rebuild: headroom `learn` (failed-session→CLAUDE.md), OpenViking (tiered load-on-demand context DB), claude-mem. deep-vet §6. Do NOT rebuild the author's mistake-learning hook on CC — port to Codex/Gemini instead.

---

## Part 4 — Environment constraints (load-bearing)
- **Windows: `py` only** (NEVER python/python3). PowerShell syntax, `\` paths. NO `??` null-coalesce in PS 5.1 (use if/else).
- **Bash tool CWD resets between calls** — `cd /c/Users/VVeb1250/.claude/port-a-whip && ...` each time (rtk hook mangles backslash → use forward-slash absolute).
- **Secrets via env `${VAR}`/.env, NEVER plaintext** (FIGMA_TOKEN/EXA_API_KEY/FIRECRAWL_API_KEY). Never string-edit config — parse→merge→validate. **No `shell=True` on community strings** (RCE — paw install steps are curated/pinned/printed-manual).
- **Caveman mode full** (drop articles/filler; code/commits/security normal). Use advisor before substantive work + before declaring done.
