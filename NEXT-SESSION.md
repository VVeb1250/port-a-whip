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
