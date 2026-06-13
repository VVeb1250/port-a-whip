# port-a-whip (paw) 🐾

**Curated sets + capability router + lesson-memory** for coding agents.
NOT a general installer/registry (Smithery/mcpm do that). For curated sets, paw patches host config itself — 0 runtime dep, no Smithery, no daemon. Adds only what no one else does.

> Source of truth = `port-a-whip-spec.md` (v0.3). This file = build-facing summary. Spec wins on conflict — EXCEPT a newer owner-decision (dated, recorded in the roadmap or a paw memory) outranks a stale spec line; when they disagree, surface the delta and fix the spec, don't silently obey the older text. Recorded decisions are re-openable when the owner changes direction OR new evidence appears that wasn't on the table when decided — but answer the original rationale first, never just forget it.

## Author
whipforaweep

## What paw is / isn't
- **isn't**: a general MCP installer/registry (Smithery/mcpm/MCPDog already do cross-host install + 6,000+ tools). a startup. a runtime dependent on Smithery/mcpm (rejected: Smithery=Node+vendor+remote, mcpm=daemon violates no-daemon ethos).
- **is**: 3 unique layers; for curated sets it patches host config directly (0 dep) —
  1. **Curated sets** — bundles (MCP + non-MCP) vetted to be quality + actually compatible together. One-command install whole set.
  2. **Capability router** — per-prompt: which skill/tool/instruction to surface. token-lean.
  3. **Lesson-memory** — capture mistakes, surface relevant ones across hosts. The durable moat (vendors won't build portability — anti-incentive).
- One criterion: **reduce tokens OR improve context quality** — ONE axis. Token budget = #1 perf lever (Anthropic: ≈80% of perf variance), so wasted tokens (context rot, idle tool-defs, dup context) = costliest failure. paw cuts *waste* → frees attention budget. Not "fewer tokens = better" but "no wasted tokens = budget left for work."

## Why these 3 (gap analysis)
| layer | why not redundant |
|---|---|
| sets | registries curate per-*tool*; no one vets *combos* that work together. non-MCP (rtk-class hook/proxy) can't live in any MCP registry by definition. |
| router | Smithery/mcpm = install/manage only. none route per-prompt relevance. |
| lesson-memory | no host/registry remembers your mistakes. hosts RAG your code, not your errors. |

## Architecture (3 layers)
```
L3 lesson-memory  : Stop hook capture → relevance inject, cross-host
L2 capability router: kernel(ranking TF-IDF+embedding) + registry(4 types)
L1 curated sets   : set = vetted compatible bundle
                    install = paw patches config (json/toml) + shim(non-MCP), 0 dep
```
- kernel (L2-3) = reuse author's skill-router + mistake hook → generalize + portable. Do NOT rebuild from scratch.
- L1 install = parse (stdlib json / tomllib + tomlkit write) → merge dict → backup → write. NOT string-edit. Read mcpm/MCPDog source as edge-case reference (free, not a dep). NO Smithery/mcpm runtime dep, no daemon, offline-capable.

## Set schema (registry/sets.json)
First set `efficiency-starter` (codegraph + rtk) live in [registry/sets.json](registry/sets.json), schema 0.3.1. Real file has `config_source`, `setup_shim`, `self_installs`, `host_support`, granular `verified` flags. Shape:
```json
{
  "set-name": "efficiency-starter",
  "description": "who it's for + how it saves tokens",
  "token_profile": { "<host>": "delta_pct before/after, net of always-on schema overhead" },
  "mcp":     [ { "tool": "codegraph", "ref": "@colbymchenry/codegraph", "version": "x.y.z", "mcp_config": { "command": "codegraph", "args": ["serve","--mcp"] } } ],
  "non_mcp": [ { "tool": "rtk", "kind": "hook|proxy|wrapper", "install": ["vetted shell step"] } ],
  "compat_notes": "what conflicts, install-order caveats",
  "verified": { "date": "...", "hosts": ["claude-code", "codex"] }
}
```
Live design rules:
- MCP install → **patcher = DEFAULT**: self-patch host config (CC/Gemini `mcpServers` JSON, Codex `[mcp_servers.<name>]` TOML). Backup → parse-validate → write. Dict-merge (preserve user's OTHER servers). Edges: create file/parent table if absent; idempotent on re-install.
- **shim = per-tool RESIDUE** (what patch can't do): post-install build steps (codegraph index — without it codegraph is DEAD) + non-MCP installs (`rtk init -g`). Scope to host/project. pin version; NO shell=True for community strings (RCE).
- **DECISION (2026-06-13, owner): shim steps of CURATED sets MAY auto-run** (`portaw install <set> --run`, confirm-gated, `-y` to skip). Exec = argv list via `shell=False` (shlex.split → `subprocess`, on Windows `.cmd`/`.bat` wrapped through `cmd /c` with a fixed argv) → **no shell metachar ever interpreted = no RCE**, even though steps invoke vendor installers (npm/npx/winget/brew). Default (no `--run`) still PRINTS. Guards: (1) **idempotent** — a non_mcp tool already on PATH is skipped; MCP `setup_shim` build steps (codegraph index) are NEVER PATH-skipped (binary present ≠ build ran); (2) **shell-requiring steps stay print-only** — any `cmd` with a pipe/chain/redirect/`$()`/backtick (e.g. `curl|sh`, the browser-harness NL instruction) is refused by `runner.needs_shell`, never run via argv; (3) **`untrusted:true` sets refused** (community/Phase-4 — until hash/sig). This NARROWS, never widens, §12: the ban was always shell=True + community strings, not author-vetted argv. [[shim-curated-autorun]] · `portaw/sets/runner.py`.
- **per-OS install (2026-06-13)**: a step's `cmd` is EITHER a string (all-OS — pip/npm/go) OR a map `{windows,macos,linux}` (winget/brew differ). `install._os_cmd` resolves against the LOCAL machine OS (`sys.platform`), not the host. A map missing the current OS → `""` → step printed "no command for <OS>", never a hard error. winget(win)/brew(mac+Linuxbrew) populated for duckdb/jq/gitleaks/infisical + rtk(winget win / curl|sh mac+linux=print-only). ⚠️ mac/Linux formulae ASSERTED not live-tested → DOGFOOD #14.
- **DECISION (2026-06-05, advisor-vetted): do NOT delegate config-patching to a tool's own installer**, even when it self-installs. Delegating = runs vendor code, no uniform backup/rollback/`portaw remove`, codegraph installer is interactive + patches ALL hosts (can't host-scope). Config entry is uniform `{command,args,env}`; per-installer adapter = bespoke = MORE work as registry grows. Use `install --print-config {host}` only to FETCH the canonical block; paw owns the write.
- `token_profile` per-host (CC lazy-loads → ~0 idle; Codex/Gemini load all → real overhead). Vendor-claimed numbers flagged UNVERIFIED.
- **set-size ceiling (N1)**: ≤ ~2-3 active MCP servers/set (load-all hosts; 50 tools ≈ 72K token defs; accuracy drops past 2-3). Count MCP only (non-MCP hooks add 0 def). Fine lever: per-server env `tool_subset` (e.g. `CODEGRAPH_MCP_TOOLS`) trims unused defs WITHOUT dropping the server.
- **schema fields (N1/N2)**: `env`/`tool_subset` per MCP tool; `trigger_terms` per set+capability (router match; `description` = who+how, trigger_terms = what+when); `delivery: mcp-config|code-exec` (default mcp-config; code-exec = Phase 4, needs sandbox).
- **set-entry eval gate (N3, MVP deterministic)**: (1) token delta from session log + (2) install health-check (not parse-only — `codegraph status -j → initialized:true` + hook responds). pass@1 task-success = OPTIONAL per set (forcing it → flaky → gate disabled). Heavy eval = Phase 2.

## Host support (verified 2026-06)
| Host | per-prompt inject | event | tier | paw value |
|---|---|---|---|---|
| Claude Code | ✅ `additionalContext` | `UserPromptSubmit` | 1 | low (native strong) |
| Codex CLI | ✅ `additionalContext` | `UserPromptSubmit` | 1 | **high** (native weak) |
| Gemini CLI | ✅ `additionalContext` | `BeforeAgent` | 1 | **high** |
| Cursor | ❌ block-only | `beforeSubmitPrompt` | 2 | low (self-optimizes −46.9%) |
| OpenCode | ⚠️ JS-plugin unconfirmed | — | 2 | set-install only |

## Target architecture (files)
```
port-a-whip/
├── portaw/                # package; CLI command = `portaw`
│   ├── main.py            # Click CLI — ALL command groups live here (lazy imports per command; no commands/ split)
│   ├── sets/              # L1: loader.py, patcher.py (json/toml, 0 dep), install.py, healthcheck.py
│   ├── kernel/            # L2-3 portable: ranking.py (TF-IDF+embed), registry.py, embed.py
│   ├── memory/            # L3: schema/store/retrieval/capture/harvest/detect/consolidate
│   ├── adapters/          # per-host inject: router.py (CC/codex/gemini wiring), memory_hooks.py
│   └── config.py          # detect host; locate+parse config (json/toml)
├── registry/sets.json     # curated sets (NOT per-tool registry)
├── integration/skill-router.py  # live CC hook bridge (kernel-unify + paw_block inject)
├── tests/  pyproject.toml  CLAUDE.md  port-a-whip-spec.md
```

## CLI commands
```bash
portaw sets [show <set>]    # list / detail (token profile + compat)
portaw install <set> [--host X]   # MCP patcher + non-MCP shim
portaw remove <set>
portaw verify <set>         # health-check (§10 gate half)
portaw doctor               # env + host detect + config parse-valid
portaw bench list/ab/how    # token-delta diff for §10 gate
portaw router enable/disable/status/run [--host X]
portaw memory add/list/recall/pin/harvest/capture-hook/consolidate/init
portaw memory inject-enable session|tool|all
```
> No `portaw install <single-tool>` main path — single tools → Smithery directly. paw sells sets + layers.

> **Pending manual/controlled runs** → [DOGFOOD-PENDING.md](DOGFOOD-PENDING.md). Check before declaring an anchor/set "verified".
> **COLD START? Read [NEXT-SESSION.md](NEXT-SESSION.md) FIRST** — thesis, honesty rules, principled lines, current state, prioritized tasks.

## Roadmap

### Phase 1 — Sets + Claude Code (MVP) ✅
- [x] schema v0.3.0 + 3 sets (efficiency-starter, secure-agent, context-quality), all `trigger_terms`.
- [x] B1 bench (`portaw bench`, wraps ccusage) → token-delta gate. portaw/bench.py (8 tests). Windows npx via fixed-literal shell=True (no injection).
- [x] codegraph+rtk config captured 2026-06-05. **codegraph = bare `codegraph serve --mcp` stdio** (NOT npx; cursor adds `--path ${workspaceFolder}`). rtk = PreToolUse/Bash `rtk hook claude`. fields `mcp_config` + `mcp_config_per_host` + `hook_entry`.
- [x] install/remove → patcher (json+toml dict-merge, backup, re-parse validate, idempotent) + orchestrator (N1 warn). shim = PRINTED by default; `--run` auto-executes curated sets via argv `shell=False` (confirm-gated, idempotent PATH-skip, refuses untrusted) — `portaw/sets/runner.py`, 7 tests. loader.py.
- [x] verify → healthcheck.py (which-probe, `health_binary` opt, config-only allowed) = §10 gate half (deterministic, offline).
- [x] doctor + host detection (CC/codex live, parse-validate, registry load).
- [x] sets list/show (reads registry).
- [x] **rtk anchor LOCKED 2026-06-05**: 26.3% mixed / 35.6K saved / 320 cmds (rtk-gain paired = zero cache noise). strong diff 74.9% / ls 68-87%, weak read 7.8% / grep 10.6%. NO SWAP (rivals don't self-report reproducible numbers). deep-vet §1/§4.
- [x] ranking engine ported skill-router → kernel/ranking.py (TF-IDF tier-1 + intent-boost + conflict-prune + prereq fan-out, pure). registry.py builds Capabilities (9 tests).
- [x] router adapter → adapters/router.py (run/test/enable/disable/status, error→exit0 safe). enable patches UserPromptSubmit (21 tests).
- [x] PyPI BUILD-READY (MIT). REBUILT 2026-06-08 @ 6 sets, twine PASS, clean-venv smoke PASS. **alpha-HOLD — NOT uploaded** (L3 not closed; name+0.3.0 claim irreversible). Upload when Phase-1 closes: `twine upload dist/*`. Fixed `verify` crash on null-binary skills.

### Phase 2 — Portable router + token-vetted sets
- [x] **Codex adapter (TOML), LIVE 2026-06-10** — `_WIRING` host-dispatch (path/fmt/event per host). Codex = `~/.codex/config.toml` `[[hooks.UserPromptSubmit]]` via tomlkit (reuses patcher backup+validate). **stdin/output contract identical across 3 hosts** (JSON envelope, out = `hookSpecificOutput.additionalContext`; only event+file differ). REAL config patched + host-turn verified (fresh Codex saw `paw router:` block). 21 tests.
- [x] **Gemini adapter (BeforeAgent, settings.json)** 2026-06-06 — same dispatch, event `BeforeAgent` (NOT UserPromptSubmit). schema+unit only. ⚠️ NOT live-verified (no Gemini on box).
- [x] **token_profile v2** (sets.json 0.3.1): per-host `{provenance, delta_pct, idle_def_tokens, sample, note}`. provenance enum `measured|calculated|vendor-claimed|estimated|neutral`; **set = weakest link**. secure-agent=neutral (0 def), context-quality=calculated 927 idle (tiktoken on real Context7 def JSON), efficiency-starter=rtk measured 26.3% + codegraph pending. deep-vet §5.
- [~] **more sets** — design-quality + web-research + browser-automation DRAFTED (sets #4-6). **THE LINE: research PRIMITIVES the agent composes (search→fetch→extract, auditable) ≠ answer-product connectors (perplexity/notion/slack = REJECTED, Smithery territory).** exa-IN/perplexity-OUT = primitive-vs-answer-product, NOT paid-vs-free. browser-automation anchor = browser-harness (0 MCP def, vs playwright-MCP 47 def). All routes live. REMAINING: install-test, Gemini support. deep-vet §6/§7.
- [x] **efficiency-starter host-conditional anchor** 2026-06-06: CC=codegraph (idle-free + richer callers/callees/impact) / Codex+Gemini=semble (509 vs 1615 idle tok = 68% leaner). `host_anchor` field through healthcheck (`alt`) + install (`alt_skipped`) + CLI. N1: 1 code-intel MCP/host XOR + rtk. 71 tests. codegraph index built for this repo.
- [x] **efficiency-starter +ast-grep** 2026-06-12: structural rung (CLI 0-def, MIT 14.5k★ v0.43.0) completes lexical(rg-native)/STRUCTURAL/graph(codegraph) triad. axis = ↓token estimated (structural precision + 1-cmd codemod vs N Edits); rtk pass-through, no collision. rejected ast-grep-mcp (idle-def for CLI-equivalent, duckdb-MCP verdict). optional_sources: gortex (graph rival, daemon+vendor-claimed, hold) + headroom (promoted visible from verified-notes). NOT install-tested → DOGFOOD-PENDING #12. 297 tests.

### Phase 3 — Lesson-memory (durable moat)
> Design = [docs/L3-DESIGN.md](docs/L3-DESIGN.md) (R1-R12 + anchor weighting + scope + build-order). Built 2026-06-10; hardened 2026-06-11 (216 tests).
- [x] **L3 core BUILT** (`portaw/memory/`) — lesson + project memory, end-to-end:
  - schema (content-hash id = free cross-project dedup) + store (jsonl, global `~/.paw/memory` + project `.paw/memory`, atomic, malformed-tolerant, upsert-bump, archive)
  - retrieval = HYBRID over the ONE kernel (`kernel.route` semantic) + anchor overlap (path/symbol = zero-setup; codegraph node = present-only bonus) + ACT-R activation (recency×freq); applicability filter (universal/stack/project); silence-default
  - injection = silence-biased, per-type threshold (lesson low / project high), budget cap, pinned-first; wired into `adapters/router.py`, fail-safe
  - capture = `FailureSignal` → applicability auto-tag → integrity gate (§7) → upsert; cross-host `paw_lesson` contract
  - consolidate = async "dream" (merge/promote/decay-archive); seed = ADR-harvest v1
- [x] **WIRED LIVE** 2026-06-10: `capture-hook` into CC Stop (coexists w/ mistake-learning) + NL transcript→FailureSignal detector (`memory/detect.py`).
- [x] **kernel-unify + INJECT LIVE** 2026-06-10 (`integration/skill-router.py`): live CC hook (1) delegates ranking to paw `kernel.ranking.route` — ONE ranker, inline = zero-paw fallback (pinned `test_skill_router_parity.py` 14/14); (2) surfaces L3 memory(+sets) via `router.paw_block` through that one hook (no double-fire). **Deploy = edit integration/skill-router.py then copy over** (`~/.claude/hooks/*` nah-hard-protected; `nah trust` does NOT clear it — copy from your own shell).
- [x] **mistakes-index.md → lessons harvester** 2026-06-10 (`memory/harvest.py`, 13 tests). The proven high-value capture path (Bash detector yields ~0; curated index = gold). Bullet `- [SEV] [id] trigger → fix (xN, date) →detail` → global lessons (sev→confidence, xN→recurrence, section→applicability, code-spans→terms/symbols). Idempotent re-key by content-hash. LIVE-VALIDATED on real Thai index (18 lessons, re-run not inflated).
- [x] **embedding tier-2** 2026-06-10 (`kernel/embed.py`, opt-in `[embed]`, 9 tests). Multilingual MiniLM ONNX from skill-router. **Lazy + optional + fail-safe** (fires ONLY on tier-1 miss; unavailable → silent TF-IDF floor; runtime deps stay click+tomlkit). Reuses author's model (`~/.claude/hooks/models` or `$PAW_EMBED_MODEL_DIR`). Injectable `embed_fn` into route()+recall() (default None → parity held). LIVE: Thai→English cross-lingual (cosine 0.592 real pair, {} below floor).
- [x] **live-inject surfaces P0-P3** 2026-06-11 (216 tests): P0 `memory_block` ctx + lazy embed + session dedup; P1 SessionStart pinned tier (`session-hook`, PINNED-ONLY, 300-tok cap — can replace auto-loaded mistakes-index 1:1); P2 PostToolUse Bash-failure recall; P3 PostToolUse Edit/Write anchor recall. Wiring `memory inject-enable session|tool|all` (CC-only v1). NOT yet enabled live.
- [x] **memoir edges + connection layer (R13)** 2026-06-13 (346 tests): typed `relations` on entries (superseded_by/contradicts/caused_by/related) — `_apply_relations` in recall does suppress-superseded → drop-contradiction → 1-hop fan-out (no-op on legacy). **Capture seeds only `related`** (additive, +reciprocal); **suppressive edges only from consolidation** (`similarity.supersede_pairs`, 6 guards) **or manual `memory link`** (cross-store: lesson→project decision) — poison-safe. Fuzzy `related` at capture via embedding band [0.55,0.97); `superseded_by` band ≥0.90. **wake-pack**: SessionStart injects a high-confidence project-memory digest (`inject.project_digest`, ≤150 tok) beside pins — anti-hallucination grounding for short-context/weak-local models. **dream cadence** user-set (`consolidate --every session|N`). ⚠️ all tests use injected encoder → real-ONNX + live-transcript dogfood = DOGFOOD-PENDING #13.
- [ ] **port capture to Codex/Gemini live** (router proven on Codex; capture is separate — Stop-event name + transcript format need live per-host confirmation) + cross-host lesson sync.
- ⚠️ **L3 hard lines = cross-host portability + no-API/no-daemon/no-cloud** (these two don't move). **Scope = anything that makes the agent smarter per injected token**: mistake-surfacing, decision grounding (anti-hallucination on short context), memory connection (typed edges / creative linking), lifting weak/local models with distilled knowledge. NOT a hosted general-memory service (that needs a server/cloud — the line is the deps, not the breadth). Broadened 2026-06-13 by owner [[l3-axis-broadened]] — superseded the old "mistake-surfacing ONLY" axis; don't reject a memory feature merely for being broader than mistakes. deep-vet §7.
- [x] **DOGFOOD 2026-06-10** (all 3 layers): L1 install/verify (secure-agent 4/4), L2 router live (CC+Codex), L3 inject live. Fixed: `memory add --pin` wiring; manual adds default `confidence=0.9` = trusted (deliberate human assertion clears universal bar; auto hook/agent lessons must still earn it). ⚠️ **Capture DETECTOR yields 0 on real transcripts** (Bash fail→fix too narrow) → **manual `memory add` + harvester = proven capture path**. project-memory seeded 7 lines (`.paw/memory/project.jsonl`, travels with repo).
- **Per-project setup** (running paw *on* a repo): (1) codegraph (`codegraph index` or codegraph-link skill); (2) paw project-memory (`portaw memory init --confirm` harvests `docs/adr/*`, else `memory add --type project`). graphify/obsidian = trial-only (token-heavy at init), skip. global router + lesson-memory need NO per-project setup.

### Phase 4 — GUI/app (CANDIDATE only, build AFTER L3)
- [ ] `portaw ui` — explicit subcommand (NOT no-arg default), **stateless, NO daemon**: pick set → token_profile + config diff preview → apply → exit. Guardrails: **no-daemon · no-host · explicit-subcommand**. Native TUI/exe > web. Off paw's token/quality axis → only pays off wrapping the MOAT, never before L3. deep-vet §7.

## Stack
- Python 3.11+, Click 8.x
- config patching: stdlib `json` + `tomllib` (read) + `tomlkit` (TOML write, preserves comments) — only non-stdlib dep
- ranking: TF-IDF + multilingual embedding (lean, embed opt-in)
- No daemon, no Smithery/mcpm runtime dep — runs, patches, exits. Offline-capable.
- Node 18+ only at *set runtime* if a set's tool runs via npx (not a paw dep)

## Security
- non-MCP install: NO shell=True, ever (RCE). Curated sets DO auto-run via `--run` but only as argv (`shell=False`, no metachar interp) — see Live design rules. Community/`untrusted` sets stay print-only; hash/signature verify gates them before auto-run (Phase 4).
- env: `.env` + `${VAR}` ref, never plaintext secret in config
- MCP source = curated sets only (reviewed before entry), not arbitrary registry → small surface
- patch config: backup + parse-validate before write (avoid corrupt config)

## Evidence loops (2026-06-12 — all 3 layers learn now)
- **L1 state ledger** `~/.paw/state.json` (sets/state.py): what paw itself wrote per host → precise remove, `doctor` drift report (orphaned/drift vs canonical), no false ownership of user servers.
- **L1 usage evidence** `doctor --usage` (sets/usage.py): real `tool_use` invocations parsed from CC transcripts (NOT string mentions — defs ride every session and are the cost, not the use) → flags idle-def servers with install date as the A/B anchor.
- **L2 outcome loop** (memory/outcomes.py): mark_suggested on emit; conversion = `portaw install <set>` seen by the Bash PostToolUse hook; suggested ≥5 + used 0 → demoted (stops surfacing; `router outcomes --forget` resets). Install-aware: installed set → usage pointer, not install pointer. Session dedup via the L3 sessionlog (`set:` namespace).
- **L3 effectiveness** (`misses` field, gate `miss_distrust=3`): error recurring AFTER a covering lesson exists → misses accumulate + confidence decays at consolidate; misses ≥3 → distrusted EVEN IF recurrence/confidence high (recurrence proves the problem, misses disprove the answer). Pinned exempt. Ledger consumed after apply (no double decay).
- **L3 sync** `portaw memory sync [--init <private-remote>]` (memory/sync.py): git-backed cross-host lesson sync. Content-hash id = conflict-free fold (field-wise max, idempotent); git = transport only (`show FETCH_HEAD:`, `merge -s ours` ties history); imports quarantined at confidence 0.7 until local recurrence (cap holds across re-syncs). Machine-local files never travel.

## Known issues / TODOs
- Gemini adapter (`BeforeAgent`) schema-verified from docs, NOT live (no Gemini host on box).
- config.py multi-format (CC/Gemini JSON + Codex TOML) — merge without clobbering user's other servers.
- Cursor/OpenCode: native strong; set-install only, router static. Low priority.
- gain ledger (#3, continuous per-set token attribution): `portaw bench gain <set>` auto-splits the host's ccusage sessions at the set's install date (before vs after) → per-session MEDIAN token delta. DIRECTIONAL only (uncontrolled windows; ≥2 sessions/side or inconclusive); for a defensible number still use `portaw bench ab` on an identical task. Never writes `measured`. `sets/gain.py`.

## Harness-quality refinements (2026-06-05, see spec §15)
- **Router scope** (correction): router fixes Gap-B (discoverability) + tool-selection accuracy, NOT token-overhead on load-all hosts (defs load at startup; router injects on top, can't unload). Overhead → set-size ceiling + code-exec + native lazy-load. Do NOT reorder roadmap L2>L1.
- **Capability entry** = `what+when`+`trigger_terms`; registry = metadata only; inject = JIT pointer (3-tier progressive disclosure); retrieval = TF-IDF+embedding fused + rerank.
- **skill complements MCP** (not either/or): skill = workflow (0 idle token), MCP = primitive (portable, load-all). Router prefers skill/instruction over mcp-tool when equivalent.
- **Sub-agent capability type = gated, not banned**: the old "≈15× tokens + loses on coding" verdict was on dated model evidence — re-measure before assuming it still holds. Gate before adding: needs contract (objective/output-format/tool-guidance/boundaries) + a breadth-first-only use (fan-out research/review, NOT serial coding) + a token-cost A/B that beats doing it inline.
- **L3 = procedural memory** (validated moat: no one does mistake-surfacing). Risk: **staleness** — high-confidence stale lesson = "confidently wrong" → confidence-decay tied to recurrence. always-on index ≈ 26K vs relevance ≈ 7K tokens (−73%).
- **ref impl: `codegraph-link` skill** = working reference for paw L1/doctor: health-gate (`status -j`, not file-presence), drift check (`--print-config` vs live), idempotent managed-block write+unlink (markers), permission/allow-list report. Reuse for `doctor` + `portaw remove`.

<!-- codegraph-link:start -->
## CodeGraph (code intelligence)

This project has a CodeGraph index (`.codegraph/`). Use it for code navigation instead of a grep/Read/Explore loop.

**Code questions** (how does X work · what calls Y · impact of changing Z · find a symbol · trace a path): answer with CodeGraph MCP directly - `codegraph_explore` is the primary one-call tool (how X works, the flow of how X reaches Y, or surveying an area; returns verbatim source grouped by file + relationship map + blast radius), `codegraph_search` to find a symbol by name, `codegraph_node` for one symbol's full source, `codegraph_callers` / `codegraph_callees` / `codegraph_impact` for call flow, `codegraph_files` for the indexed file tree, `codegraph_status` for index health. A handful of calls, usually **zero file reads**; treat returned source as authoritative (already read). The index auto-syncs on save; a warning banner names any file pending sync - Read that one directly.

**Do NOT delegate code exploration to an Explore sub-agent or a grep/Read loop when CodeGraph can answer it** - that re-derives what the index already built and costs more for the same result. For code-navigation on this project, this **overrides** the general "always use Explore / parallel agents" guidance. (Sub-agents are still right for non-code research, writing, and multi-file edits.)

**Architecture / orientation & docs / papers / images:** CodeGraph is code-only and there's no graphify graph here. Build orientation from CodeGraph itself (`codegraph_files`, then `codegraph_explore` on entry points) plus direct reads for docs. Run `/graphify` then re-run `/codegraph-link` to upgrade this block to the graphify-aware split (architecture digest + multimodal doc coverage).
<!-- codegraph-link:end -->
