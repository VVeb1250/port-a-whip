# Pending manual / controlled runs (กันลืม)

> Things that NEED a human-driven run (controlled A/B, live dogfood, real install) —
> they can't be auto-backgrounded because they require fresh sessions, a host paw
> can't drive, or real usage over days. Each item = why + exact steps + where the
> result lands. Tick when done.
>
> Last updated 2026-06-12. Most-leverage first.
>
> **▶ COPY-PASTE SHEET: `bench/RUN-PROMPTS.md`** — one ready-to-paste block per
> remaining run (groups A-F), with per-block SETUP + trials + report-back. Open it,
> copy a block into a FRESH session. Backed by:
> **▶ TURNKEY RUNBOOK: `bench/guides/` (numbered, one md per fresh session).** Start
> at `bench/guides/00-INDEX.md` (order + the VALIDITY RULES + diff/aggregation +
> where results land). To run: paste into a FRESH session "Follow
> `bench/guides/NN-*.md` exactly, then stop and report." Items 1/2/3/6/7 below map
> to those guides. **Validity honesty:** idle-def numbers = solid (calculated);
> runtime delta via ccusage = NOISY → guides require ≥3 trials + completeness gate +
> same model, and web-research uses deterministic `bench/_count_tokens.py` as the
> primary measure. A single ccusage diff = `estimated`, NOT `measured`.

---

## 1. [~] semble vs codegraph — ROP 3-lane run DONE 2026-06-09 (capability decided; clean token-delta still open)

**DONE 2026-06-09** (3 real repos × grep/codegraph/semble, the 5-Q workload): token-delta NOT isolable (sessions contaminated) -> judged on CAPABILITY. **codegraph 5/5 FULLY (callers/impact/explore); semble = search-shaped only, CANNOT do Q2 callers / Q3 impact (no structural tool).** Host-conditional anchor confirmed on capability grounds. **CLEAN-NUMBER GAP CLOSED via external vendor benches (2026-06-09, corroborated):** codegraph (colbymchenry, 7 repos×7 langs, median-of-4) = 59% fewer tokens / 70% fewer calls, include_source-whole-file 64% WORSE (matches paw proxy); semble (MinishLab, 1250 pairs×63 repos) = 98% fewer tokens but SEARCH-RETRIEVAL only (silent on call-graph = paw's capability gap). Both + caveats agree with paw's own run. Written to sets.json efficiency-starter + deep-vet §6. **Only a paw-OWNED `measured` label would still need discipline-isolated single-workload sessions (low value — vendor+proxy+capability already align).**

## 1b. [ ] (superseded) semble vs codegraph — runtime A/B (anchor re-vet, finishes the decision)

**Why:** idle-def axis already DECIDED (tiktoken: codegraph 1615 tok vs semble 509 = 68% leaner on load-all hosts). Missing = the RUNTIME token saving (does semble's search match codegraph's explore on token spend + tool-call count?). This closes the host-conditional anchor in `registry/sets.json` (efficiency-starter `code_intel_anchor_by_host`).

**Steps** (full protocol in `bench/codegraph-workload.md` → "Rival lane: semble"):
1. Pick a non-trivial repo, same commit for all runs.
2. Run A — codegraph OFF (remove from host MCP cfg). Fresh session, paste the workload (the 5 trace/where-is/impact questions). Note session id.
3. Run B — codegraph ON (`codegraph init`, confirm `status -j`). Fresh session, SAME workload.
4. Run C — semble instead of codegraph (`uv tool install semble` already done; add MCP cfg). Fresh session, SAME workload.
5. `portaw bench list --agent claude` → ids; `portaw bench ab <A> <B>` and `<A> <C>`.
6. Judge 3 axes: idle (done: −1106 tok), runtime delta_pct/call-count (this), **capability** (can semble answer the callers/impact questions at all, or only search-shaped ones?).

**Result → ** `registry/sets.json` efficiency-starter `token_profile.hosts.*` (semble `delta_pct`) + confirm/adjust `code_intel_anchor_by_host`. Note in `registry/deep-vet.md` §6.

---

## 2. [x] headroom vs rtk — RESOLVED 2026-06-09 (complementary layers, not rival)

**DONE 2026-06-09:** reframed — rtk (PreToolUse hook, command-output) + headroom (API-proxy, session/history/RAG) are COMPLEMENTARY, STACK additively. Real 1-month dual-deploy (andrewpatterson.dev): rtk = 88% of savings, headroom = +12% additive; headroom per-model 32-59% (60-95% headline = per-content best-case). paw's OWN deterministic local run (bench/_compress_ab.py, tiktoken on raw-vs-rtk, rop-backend git-heavy): rtk TOTAL 63.5% (diff 69%, log 53%, status 71%) — corroborates rtk independent of vendor. headroom LANE BLOCKED on Windows (no PyPI Windows wheel — macOS+manylinux only; Rust/maturin build fails without toolchain, py3.12+3.14). **VERDICT: rtk stays anchor; headroom = optional additive API-proxy rung (Windows install friction keeps it optional, not core).** sets.json efficiency-starter (rtk_local_bench + headroom_challenge fields) + deep-vet §6 challenge B updated.

## 2b. [ ] (superseded) headroom vs rtk — tool-output compression A/B (anchor challenge)

**Why:** headroom claims 60-95%, rtk MEASURED 26.3% mixed. Same class (both non-MCP, 0 idle def) → fair head-to-head. Don't swap on the claim — bench it. Weigh ratio AGAINST headroom's heavier dep (Python + Kompress model + latency) vs rtk lean/Rust/0-dep.

**Steps** (full protocol in `bench/rtk-ab-workload.md` → step 5 + headroom lane):
1. Same fixed workload (the 6 bulky-output commands), same repo state.
2. Run B(rtk) — rtk hook ON. Fresh session, paste workload.
3. Run B(headroom) — rtk OFF, headroom in **proxy/lib form** (NOT MCP, keep it 0-idle-def for fairness). `pip install headroom-ai` (or per its README). Fresh session, SAME workload.
4. `portaw bench ab <rtk_id> <headroom_id>` — lowest treated-total wins. Sanity: both reached step 6 (a tool that drops needed detail is NOT a win).

**Result → ** `registry/deep-vet.md` §1 S1 / §6. If headroom wins NET (ratio minus dep cost), reconsider efficiency-starter anchor; else rtk holds.

---

## 3. [~] codegraph runtime delta_pct — DETERMINISTIC proxy done 2026-06-08; full ccusage pending

**Deterministic into-context proxy RAN** (tiktoken on tool-returns, port-a-whip self-index, bench/out/codeintel/): QUESTION-TYPE-DEPENDENT. callers+impact(get_set) = 172 tok vs grep+read trace 6,622 (~97% less, codegraph home turf). BUT narrow show-one-file = explore over-returns 2,894 vs targeted Read 606 (~4.8x more). → codegraph wins relationship/impact, loses show-one-symbol; no blanket delta_pct. Recorded sets.json efficiency-starter CC note + deep-vet §1 S1. STILL: full session ccusage A/B (bench/guides/04-05, fresh sessions) for the operational mixed-workload delta incl. tool-call-count axis.

(original:)

**Why:** codegraph's token saving is still `vendor-claimed` ("fewer tokens/calls"). idle-def now known (1615 load-all / 0 CC). Runtime grep+read-replacement saving = unmeasured.

**Steps:** `bench/codegraph-workload.md` Run A (off) vs Run B (on), same repo/commit. `portaw bench ab`. (This is Runs A+B of item 1 — do them together.)

**Result → ** sets.json efficiency-starter `token_profile.hosts.claude-code` codegraph `delta_pct` (flip provenance vendor-claimed → measured).

---

## 4. [ ] skill-router v2 dogfood (PRE-paw, different repo — don't forget)

**Why:** v2 cooldown+logger is live in `~/.claude/hooks/` (NOT paw — the standalone skill-router). It logs passively. Need real data to tune thresholds before building v3 reactive (Pre/PostToolUse).

**Steps:** just USE Claude Code normally 2-3 days. `~/.claude/hooks/.router-log.jsonl` fills passively. Then analyze: signal-fire histogram, strength dist, thrash nav-count dist, used/ignored rate, FP candidates → tune `THRASH_MIN`/`STRENGTH`/`PRIMER_MIN` → THEN build v3.

**Result → ** memory `project_skill_router.md`. (Analyzer script still to write when data exists.)

---

## 5. [~] Gemini + Codex router adapter — Codex router LIVE; Gemini still open

**2026-06-10 Codex proof:** `portaw` console script is on PATH (`0.3.0`);
Codex/TOML subset tests pass (`56 passed`); full suite passes (`164 passed`);
`portaw router run --host codex` emits valid hook JSON with
`hookEventName=UserPromptSubmit` and `additionalContext` when fed byte stdin;
real `~/.codex/config.toml` is now patched via
`portaw router enable --host codex` (backup `config.toml.paw-bak-20260610T080120Z`);
`portaw router status --host codex` => `wired=True`; `portaw doctor` parses
Codex TOML OK. **Fresh-session host-turn proof also passed:** Codex saw the
injected `paw router:` block and reported suggested sets `secure-agent` and
`design-quality`. The visible block did not print the event name, but its timing
is consistent with `UserPromptSubmit`. The staged-diff review had no findings
because `git diff --cached` was empty.

**Why:** Phase-2 adapters are schema-verified + unit-tested; Codex router is now
wired, CLI-hook-smoked, and live host-turn verified; **Gemini NEVER fired live**
(CLI not installed — only `~/.gemini/antigravity/`). L3 Codex/Gemini Stop capture
remains separate and unverified.

**Steps (when a Gemini/Codex host exists):**
1. Codex router: DONE. Keep dogfooding in normal use; log any false positives.
2. Codex L3 capture: do NOT enable until Stop event + transcript format are confirmed.
3. Gemini: `portaw router enable --host gemini` — patches BeforeAgent; then repeat
   the same live-fire check.

**Result → ** Codex router box is live; flip Gemini from "schema-verified" to "live"
after an actual Gemini host turn.

---

## 6. [~] design-quality set — install-tested 2026-06-08; slop-catch not exercised

**DONE 2026-06-08** (bench/guides/10-installs.md): impeccable v2.3.2 installed, `npx impeccable detect` CLI confirmed working. sets.json design-quality → `verified` (impeccable verified, figtree optional/untested). **REMAINING:** test project had no frontend `src/` → "catches real slop" NOT exercised; re-run `impeccable detect` on a real frontend to fully close. figtree-cli optional (needs FIGMA_TOKEN).

**Why:** drafted with verified install refs but NOT install-tested end-to-end. impeccable is the immediately-useful one (no API key).

**Steps:**
1. `npx impeccable skills install` → then `/impeccable audit` (or `npx impeccable detect src/`) on a real frontend.
2. (optional, Figma teams) `npm install -g figtree-cli`, set `FIGMA_TOKEN` in `.env` (NEVER hardcode), run `figtree`.
3. Confirm the tools work + the audit catches real slop.

**Result → ** sets.json design-quality `verified.status` DRAFT → verified; add `open-design` skills if worth it.

---

## 7. [x] secure-agent / context-quality — install-tested 2026-06-08 (DONE)

**DONE 2026-06-08** (bench/guides/10-installs.md): secure-agent gate PASS (nah 0.9.1 wired 9 matchers×3 events, gitleaks 8.30.1, osv-scanner 2.3.8, infisical 0.43.91 — all on PATH); context-quality Context7 MCP patched into ~/.claude.json (backup .paw-bak-20260608T122104Z), config-only gate PASS. Both sets.json `verified` blocks updated (CC host).

**Why:** both drafted + healthcheck logic exists, never installed on a real host end-to-end.

**Steps:** `portaw install secure-agent --host claude-code` (prints manual shim — run the nah/gitleaks/osv-scanner/infisical installs), then `portaw verify secure-agent`. Same for context-quality (`portaw install context-quality` patches Context7 MCP). Confirm health-gate passes.

**Result → ** sets.json each set's `verified.hosts`.

---

## 8. [~] web-research set — CC A/B DONE 2026-06-08; load-all + tokenize remain

**CC LANE DONE:** native 16,182 (complete) beats Fetch (2,858 truncated→incomplete → DEMOTED on CC) + broad-Scrapling (21,025). Tight-Scrapling 2,599 (~84%<native, complete) = ceiling lever real but hides discovery cost → CC = capability rung, delta_pct null, provenance `measured`. Writeup: deep-vet.md web-research § + sets.json CC. REMAINING: load-all-host (Codex/Gemini) live value, Fetch per-host --print-config, optional-MCP def-token counts (need keys).


**Why:** set #5. HARDENED 2026-06-07 — DONE: Fetch def captured + tiktoken'd (259 tok calculated idle, `bench/_fetch_def_count.py`); optional configs VERIFIED from READMEs (Scrapling CLI, searxng-mcp `npx -y mcp-searxng`, exa-mcp `npx -y exa-mcp-server`); firecrawl CORRECTED (MCP has no subset → lean = REST scrape endpoint). REMAINING before "verified":

**⚠ BASELINE CORRECTION (advisor 2026-06-07):** the original "Run A = WebFetch raw HTML" baseline was a STRAWMAN. CC's native WebFetch already does URL→markdown→small-model-digest — nothing on CC emits a raw-HTML dump to beat. Running the old A/B would either kill the set or rig a hollow win. The real question is **direct/targeted content vs model-digested answer**, and plain Fetch may LOSE to native WebFetch on CC.

**Steps:**
1. **A/B (controlled run) — 3 lanes, honest baseline** → **READY-TO-RUN workload: `bench/web-research-workload.md`** (created 2026-06-08: fixed 3-URL set + verbatim task + per-lane setup + the decision rule below, mirrors codegraph-workload format). Lane A = native WebFetch **default behavior** (digested). Lane B = Fetch MCP (returns up to max_length chars). Lane C = Scrapling targeted extract (`extract fetch --css-selector`). `portaw bench ab`. **Pre-decided DECISION on the result:** if Fetch ≤ native WebFetch on CC → **demote Fetch on CC** (it duplicates a native tool), keep it as the keyless anchor ONLY on load-all hosts (Codex/Gemini lack a native digest-fetch), and lead the CC set value with the additive rungs. The set's differentiated lever is targeted/semantic extract (C/exa), not plain fetch.
2. ~~tiktoken optional MCP defs~~ — TOOL COUNTS captured 2026-06-07 (searxng 2, exa 2-active+1-disabled, Scrapling-MCP 10, firecrawl 12). **Exact token counts BLOCKED on a live schema dump**: these servers need a key (exa/firecrawl) or a running instance (searxng), and WebFetch paraphrases source descriptions so it can't yield a clean `calculated` count. When a key/instance exists, dump the live def JSON and tiktoken it (same as Fetch 259). Until then = honest prose estimates only, NOT calculated numbers. (Low leverage — all opt-in, none default-on.)
3. Capture Fetch per-host `--print-config` block (currently canonical-README shape only).
4. ~~Scrapling MCP config~~ — DONE: `scrapling mcp`, 10 tools (heavy → CLI is the lean path; MCP form CC-only). In sets.json.

**Result → ** sets.json web-research CC `delta_pct` (or Fetch demotion) + optional idle counts + `verified.status` DRAFT→verified.

---

## 9. [x] data-query + doc-extract (sets #7-8) — DONE 2026-06-12 (install-tested + A/B)

**DONE 2026-06-12 on this Windows box (all self-doable, no fresh session needed):**
- **Installs:** `winget install DuckDB.cli` -> duckdb **v1.5.3** (web said v1.5.2; newer); `winget install jqlang.jq` -> jq-1.8.1; `py -m pip install "markitdown[all]"` -> markitdown **0.0.2** (NOT v0.1.6). ROOT CAUSE CORRECTED: not a py3.14 wheel gap (0.1.6 is pure py3-none-any, installs fine) — `[all]` pins `youtube-transcript-api~=1.0.0` (gone from PyPI) -> unsatisfiable -> pip SILENTLY backtracks markitdown to 0.0.2. Known upstream (microsoft/markitdown #1809 closed / #1704 / #103) -> NO new issue filed (dup). FIX = scoped extras `markitdown[docx,xlsx,pptx,pdf]` (verified resolves 0.1.6); sets.json install step switched to it. 0.0.2 converts office files fine regardless. All three `portaw verify` gates PASS (data-query, doc-extract).
- **data-query A/B** (bench/_dataquery_ab.py, deterministic tiktoken cl100k): 2.02MB/50k-row CSV = Read-whole-file **1,099,015 tok** vs duckdb schema(72)+3 queries(98/195/112) **477 tok = +99.96%**. provenance CALCULATED. Written to sets.json data-query CC note + verified.
- **doc-extract probe** (bench/_docextract_probe.py): docx (headings+table) + xlsx (sheet+10 rows) -> markitdown md preserved `#`/`##` headings, GFM table, all rows/cols. VERDICT structure-preserving = True. delta null (capability-class). DRAFT->verified.
- **WINDOWS gotcha recorded:** winget PATH change invisible to an already-spawned shell -> merge Machine+User PATH before `portaw verify`.

**Remaining (low value):** jq separately not benched (same bounded-slice mechanism); markitdown 0.1.x feature set needs Python <=3.13.

---

## Done this session (for context — NOT pending)
- ✅ codegraph index BUILT for port-a-whip (21 files/283 nodes) — `codegraph_explore` live for this repo.
- ✅ semble installed (`uv tool install semble`) — ready for items 1 + load-all hosts.
- ✅ idle-def CALCULATED (no run needed): context-quality 927, semble 509, codegraph 1615 (all tiktoken cl100k).

## 12. [x] ast-grep — DONE 2026-06-12 (install-tested + structural-rung A/B)

**DONE 2026-06-12 on this box:**
- **Install:** `npm install --global @ast-grep/cli` -> ast-grep 0.43.0. `portaw verify efficiency-starter` gate PASS (codegraph+rtk+ast-grep). test fixtures updated (+ast-grep in fake PATH), 297 pass.
- **A/B** (bench/_astgrep_ab.py, deterministic tiktoken cl100k, on the clean paw repo = conservative): (1) precision `route(` text-grep 242 tok vs ast-grep call-shape 74 tok = **+69.4%**; (2) codemod rename `--rewrite` preview diff 291 tok vs grep->read->edit loop 1,217 (tight windows) - 10,961 (full files) = **+76.1% to +97.3%**. provenance bumped estimated -> CALCULATED in sets.json _axis_note + _verified.
- **WINDOWS gotchas recorded in sets.json:** (a) npm `.CMD`/`.ps1` shim not launchable by subprocess(shell=False) -> resolve real `...\\node_modules\\@ast-grep\\cli\\ast-grep.exe`; (b) `--rewrite ... -U` APPLIES in place (mutated repo during first run; reverted) -> use `--rewrite` WITHOUT -U for preview.

**Remaining (optional):** `npx skills add ast-grep/agent-skill` rule-writing-hit-rate check (qualitative, low value).
