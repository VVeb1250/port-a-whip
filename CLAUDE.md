# port-a-whip (paw) 🐾

**Curated sets + capability router + lesson-memory** for coding agents.
NOT a general installer/registry (Smithery/mcpm do that). For curated sets, paw patches host config itself — 0 runtime dep, no Smithery, no daemon. Adds only what no one else does.

> Source of truth = `port-a-whip-spec.md` (v0.3). This file = build-facing summary. Spec wins on conflict.

## Author
whipforaweep

## What paw is / isn't
- **isn't**: a general MCP installer/registry (Smithery/mcpm/MCPDog already do cross-host install + 6,000+ tools). a startup (not competing). a runtime dependent on Smithery/mcpm (rejected: Smithery=Node+vendor+remote, mcpm=daemon violates no-daemon ethos).
- **is**: 3 unique layers; for curated sets it patches host config directly (0 dep) —
  1. **Curated sets** — bundles (MCP + non-MCP) vetted to be quality + actually compatible together. One-command install whole set.
  2. **Capability router** — per-prompt: which skill/tool/instruction to surface. token-lean.
  3. **Lesson-memory** — capture mistakes, surface relevant ones across hosts. The durable moat (vendors won't build portability — anti-incentive).
- One criterion for everything: **reduce tokens OR improve context quality.** These are ONE axis, not two: token budget is the #1 performance lever (Anthropic: token usage ≈ 80% of perf variance), so wasted tokens (context rot, idle tool-defs, dup context) are the costliest failure mode. paw cuts *waste* → frees attention budget. Not "fewer tokens = better" but "no wasted tokens = budget left for work."

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
- L1 install = parse (stdlib json / tomllib + tomlkit write) → merge dict → backup → write. NOT string-edit (avoids JSON pitfalls). Read mcpm/MCPDog source as edge-case reference (free, not a dep). NO Smithery/mcpm runtime dep, no daemon, offline-capable.

## Set schema (registry/sets.json)
> LIVE: first set `efficiency-starter` (codegraph + rtk) written to [registry/sets.json](registry/sets.json) — schema_version 0.3.0, real verified refs. Illustrative shape below; real file has `config_source`, `setup_shim`, `self_installs`, `host_support`, granular `verified` flags.
```json
{
  "set-name": "efficiency-starter",
  "description": "who it's for + how it saves tokens",
  "token_profile": { "<host>": "delta_pct before/after, net of always-on schema overhead" },
  "mcp":     [ { "tool": "codegraph", "ref": "@colbymchenry/codegraph", "version": "x.y.z", "mcp_config": { "command": "npx", "args": ["-y", "@colbymchenry/codegraph"], "env": {} } } ],
  "non_mcp": [ { "tool": "rtk", "kind": "hook|proxy|wrapper", "install": ["vetted shell step"] } ],
  "compat_notes": "what conflicts, install-order caveats",
  "verified": { "date": "...", "hosts": ["claude-code", "codex"] }
}
```
- MCP install → **patcher = DEFAULT**: paw self-patches host config (CC/Gemini `mcpServers` JSON, Codex `[mcp_servers.<name>]` TOML). Backup first, parse-validate before write. Dict-merge — preserve user's OTHER servers. Edges: create config file if absent; create `[mcp_servers]`/`mcpServers` parent if absent; idempotent on re-install.
- **shim = per-tool RESIDUE** (what patch can't do): post-install build steps (e.g. `codegraph init -i` index build — without it codegraph is DEAD) + non-MCP installs (`rtk init -g`). Scope to chosen host/project. pin version; NO shell=True for community strings (RCE — see security).
- **DECISION (2026-06-05, advisor-vetted): do NOT delegate config-patching to a tool's own installer even when it self-installs.** Both anchor tools (codegraph, rtk) ship installers, but delegating = runs vendor code, no uniform backup/rollback/`portaw remove`, codegraph's installer is interactive + patches ALL hosts (can't host-scope). Config entry is uniform `{command,args,env}`; per-installer adapter is bespoke = MORE work as registry grows. Patcher stays default (long tail of bare MCP servers = command+args, no installer). Use codegraph's `install --print-config {host}` only to FETCH the canonical block; paw still owns the write.
- `token_profile` per-host (CC lazy-loads → ~0 idle; Codex/Gemini load all → real overhead). Ship vendor-claimed numbers flagged UNVERIFIED; paw's own bench = Phase 2.
- **set-size ceiling** (N1): ≤ ~2-3 active MCP servers/set (load-all hosts; 50 tools ≈ 72K token defs; accuracy drops past 2-3 servers). Count MCP only (non-MCP hooks don't add defs). Fine lever: per-server env `tool_subset` (e.g. `CODEGRAPH_MCP_TOOLS`) trims unused defs WITHOUT dropping the server.
- **schema fields** (N1/N2): `env`/`tool_subset` per MCP tool; `trigger_terms` per set+capability (router match; set `description` stays who+how, trigger_terms = what+when); `delivery: mcp-config|code-exec` (default mcp-config; code-exec = Phase 4 filesystem-wrapper, needs sandbox — hook only, not built).
- **set-entry eval gate** (N3, MVP deterministic): (1) token delta from session log + (2) install **health-check** (not parse-only — `codegraph status -j → initialized:true` + hook responds, codegraph-link style). pass@1 task-success = OPTIONAL per set (real success needs agent-driving harness or LLM-judge = deferred; forcing it → flaky → gate gets disabled). Heavy eval (20-query × LLM-judge × human-cal + trajectory) = Phase 2.

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
├── portaw/                # package (import name); CLI command = `portaw`
│   ├── main.py            # Click CLI
│   ├── sets/              # L1: set load + install orchestration
│   │   ├── loader.py      # parse sets.json
│   │   ├── patcher.py     # patch host config (json/toml) — MCP, 0 dep
│   │   └── shim.py        # run non-MCP install steps
│   ├── kernel/            # L2-3: portable
│   │   ├── ranking.py     # TF-IDF + embedding relevance
│   │   └── registry.py    # capability registry (4 types)
│   ├── adapters/          # per-host inject + (later) lesson capture
│   │   ├── base.py
│   │   ├── claude_code.py # UserPromptSubmit
│   │   ├── codex.py       # UserPromptSubmit (TOML)
│   │   └── gemini.py      # BeforeAgent (settings.json)
│   ├── config.py          # detect host; locate + parse host config (json/toml)
│   └── commands/          # sets, install, remove, doctor, router
├── registry/
│   └── sets.json          # curated sets (NOT per-tool registry)
├── tests/
├── pyproject.toml
├── CLAUDE.md
└── port-a-whip-spec.md    # source of truth (v0.3)
```

## CLI commands
```bash
portaw sets                 # list curated sets
portaw sets show <set>      # detail + token profile + compat notes
portaw install <set>        # install whole set (MCP patcher + non-MCP shim)
portaw install <set> --host X
portaw remove <set>         # remove whole set
portaw doctor               # env + host detect + host config parse-valid?
portaw router enable        # install router hook into current host
portaw router status        # host + tier
```
> No `portaw install <single-tool>` as the main path — single tools → use Smithery directly. paw sells sets + layers.

> **Pending manual/controlled runs** (A/B benches, live dogfood, real installs that
> paw can't auto-run) → [DOGFOOD-PENDING.md](DOGFOOD-PENDING.md). Check it before
> declaring an anchor/set "verified".

> **COLD START? Read [NEXT-SESSION.md](NEXT-SESSION.md) FIRST** — handoff with the
> paw thesis, the "what is a good harness" frame, the honesty rules (don't relearn
> them the hard way), the principled lines drawn, current state, and prioritized tasks.

## Roadmap
### Phase 1 — Sets + Claude Code (MVP)
- [x] set schema (v0.3.0) + curated sets in registry/sets.json (refs verified): `efficiency-starter` (codegraph+rtk), `secure-agent` (nah+gitleaks+osv-scanner+infisical, 0 MCP def — Permissions differentiator), `context-quality` (Context7, 2-def — anti-hallucination). All have `trigger_terms`.
- [x] **B1 bench** (build-kit, wraps ccusage): `portaw bench list/ab/how` → token-delta diff 2 sessions for §10 gate. portaw/bench.py + tests/test_bench.py (8 pass). Windows npx via shell=True (fixed literal, no injection). VERDICT rtk-vs-peers RESOLVED via rtk-gain instrumentation (see anchor line below).
- [x] **capture codegraph config + rtk hook entry → `config_block_confirmed` 2026-06-05.** codegraph via `codegraph install --print-config <id>` (id = claude|codex|gemini|cursor, NOT claude-code). **DRIFT FIXED**: actual command = bare `codegraph` binary + `type:stdio` + `["serve","--mcp"]` (was wrongly `npx -y @colbymchenry/codegraph`); cursor adds `--path ${workspaceFolder}`. Stored in `mcp_config` + new `mcp_config_per_host`. rtk hook from live settings.json: PreToolUse/matcher Bash/`rtk hook claude` → new `hook_entry` field. install step now `rtk init -g --auto-patch` (or `--no-patch` for paw-applied).
- [x] **`portaw install/remove <set>`** → patcher (sets/patcher.py: json+toml dict-merge, backup, re-parse validate, parent/file-absent edges, idempotent) + install orchestrator (sets/install.py: N1 ceiling warn, host resolve). Shim = PRINTED manual steps (no silent vendor-exec = 0 RCE surface). sets/loader.py loads registry. tests/test_patcher.py + test_install.py.
- [x] **`portaw verify <set>`** = §10 health-check half (sets/healthcheck.py: shutil.which probe per tool, mcp `health_binary` opt, config-only allowed). Pairs with B1 bench (delta) = §10 MVP gate complete (deterministic, offline). agentevals trajectory = still Phase 2.
- [x] **`portaw doctor`** + host detection (detects claude-code/codex live, parse-validates each config, registry load check)
- [x] **`portaw sets list/show`** (real, reads registry)
- [x] **rtk paired-bench RUN → anchor LOCKED 2026-06-05** — used rtk-gain instrumentation (command-level paired raw-vs-compressed, beats session-diff = zero cache noise). **26.3% mixed real / 35.6K saved / 320 cmds**; strong bulk/structured (diff 74.9%, ls 68-87%), weak read 7.8%/grep 10.6%. NO SWAP (rivals don't self-report reproducible numbers; rtk does). In sets.json `rtk_anchor_decision` + deep-vet §1/§4. OPTIONAL Phase-2: peer head-to-head A/B (bench/rtk-ab-workload.md ready).
- [x] **ranking engine** ported from skill-router → `kernel/ranking.py` (generalized skill→Capability: TF-IDF tier-1 + intent-boost + conflict-prune + prereq fan-out, injectable RouteConfig, pure). `kernel/registry.py` builds Capabilities from sets.json (trigger_terms = intent_map). tests/test_ranking.py (9). tier-2 multilingual embed = Phase 3.
- [x] **router adapter** → `adapters/router.py`: `portaw router run` (hook entry, error→exit0 safe), `router test/enable/disable/status`. enable patches host settings.json UserPromptSubmit (backup+idempotent), CC+Gemini. tests/test_router.py (13). Verified live: secret→secure-agent, navigate→efficiency-starter, docs→context-quality, unrelated→silent.
- [x] **pypi BUILD-READY** (MIT): LICENSE + pyproject (SPDX license, sdist ships /registry, wheel force-includes only sets.json). `py -m build` → wheel+sdist, `twine check` PASSED, clean-venv install verified (portaw --version/sets/router/verify all work). **NOT uploaded** (alpha: L3 not built; name claim + 0.3.0 upload irreversible). Upload when Phase-1 closes: `twine upload dist/*` (needs PyPI token). TestPyPI rehearsal: `twine upload -r testpypi dist/*`.
  - **REBUILT 2026-06-08** (was STALE at 3 sets): fresh wheel+sdist now ship all **6 sets** (sets.json verified in wheel at portaw/registry/sets.json), `twine check` PASSED, clean-venv smoke PASSED. Still alpha-HOLD (no upload). **Bug fixed in this rebuild:** `verify` crashed (`shutil.which(None)`) on any non-MCP **skill** with `health_binary: null` (browser-harness, AND latent for impeccable) — `entry.get("health_binary", tool)` returns None when key is present-but-null (default only fires when key absent). healthcheck.py `_probe_non_mcp` now mirrors `_probe_mcp`: null binary → `config-only` (skill, gate passes). +2 regression tests (test_healthcheck.py), suite 71→73.

### Phase 2 — Portable router + token-vetted sets
- [x] **Codex adapter (UserPromptSubmit, TOML)** 2026-06-06; **real Codex router LIVE 2026-06-10** — `adapters/router.py` now host-dispatched via `_WIRING` table (path/fmt/event per host). Codex = `~/.codex/config.toml` array-of-tables `[[hooks.UserPromptSubmit]]`→`[[…hooks]]` `{type,command,command_windows}` via tomlkit (reuses patcher's backup+tomllib round-trip validate). **Stdin/output contract verified identical across all 3 hosts** (JSON envelope, prompt under `prompt`; out = `hookSpecificOutput.additionalContext`) — only `hookEventName` + config file differ. `run_hook(host=)` emits per-host event; wired command carries `--host` (CC stays bare marker for back-compat). **LIVE-PROBED against a copy of the real ~/.codex/config.toml**: 6 mcp_servers + all top-level keys (notify/persistent_instructions/…) preserved, idempotent, disable drops empty event table clean. **REAL CONFIG NOW PATCHED:** `portaw router enable --host codex` wrote the hook to `~/.codex/config.toml` with backup `config.toml.paw-bak-20260610T080120Z`; `portaw router status --host codex` => `wired=True`; `portaw doctor` parses the TOML; byte-stdin smoke of `portaw router run --host codex` emits `hookEventName=UserPromptSubmit` + `additionalContext`. **HOST-TURN VERIFIED:** fresh Codex session saw the injected `paw router:` block and suggested `secure-agent` + `design-quality`; event inferred consistent with `UserPromptSubmit` (not printed in visible block). tests/test_router.py 21 (was 13).
- [x] **Gemini adapter (BeforeAgent, settings.json)** 2026-06-06 — same `_WIRING` dispatch; Gemini = `~/.gemini/settings.json` JSON, event `BeforeAgent` (NOT UserPromptSubmit), `hooks.BeforeAgent[].hooks[].{type,command}`. Schema-verified (docs) + unit-tested. ⚠️ **NOT live-verified** — Gemini CLI not installed on this box (only `~/.gemini/antigravity/`, no settings.json). Build+test parity with Codex; dogfood when a Gemini host exists (mirrors how skill-router staged build→dogfood).
- [x] **token metric protocol → profile every set (per-host)** 2026-06-06 — `token_profile` schema **v2** (sets.json 0.3.1): per-host `{provenance, delta_pct, idle_def_tokens, sample, note}`. Provenance enum (machine-readable, encodes the rtk-over-claim lesson): `measured | calculated | vendor-claimed | estimated | neutral`. Two numbers: `delta_pct` (runtime tokens saved) + `idle_def_tokens` (load-all idle def cost; 0 on CC). Set provenance = weakest link. **3 sets migrated**: secure-agent=`neutral` (0 defs, CLOSED); context-quality=`calculated` **927 tok** load-all idle (tiktoken cl100k on real Context7 def JSON: resolve-library-id 611 + query-docs 316; 0 on CC, CLOSED); efficiency-starter=rtk `measured` 26.3% + codegraph `vendor-claimed`/`estimated` PENDING (`bench/codegraph-workload.md` A/B + def-tokenize, marked not fabricated). Protocol = method+schema, NO new CLI (bench --how/--ab + bench/*-workload.md cover it). `sets show` renders v2. Detail: deep-vet §5.
- [~] more recommended sets — **design-quality + web-research DRAFTED** 2026-06-06. design-quality: impeccable anchor /skill + figtree-cli /CLI, non-MCP=N1-free, ↑quality anti-slop (open-design=skills-source deferred). web-research: **Fetch-MCP keyless anchor** (1 def, HTML→md, verify PASS) + opt-in ladder (SearXNG/Scrapling/exa/firecrawl). **THE LINE: curate research PRIMITIVES agent composes (search→fetch→extract, auditable) ≠ answer-product connectors (perplexity/notion/slack = REJECTED, Smithery territory).** exa-IN/perplexity-OUT = primitive-vs-answer-product NOT paid-vs-free (advisor-corrected: both are paid SaaS APIs; the split is composability+source-audit, consistent w/ context-quality anti-halluc axis). optional configs UNVERIFIED→DRAFT. routes live (slop/figma→design-quality, scrape/research→web-research). **browser-automation DRAFTED → registry 2026-06-08 (set #6)**: anchor browser-harness (browser-use/browser-harness, MIT 14.5k★, skill+CDP, 0 MCP def, self-healing, cross-host CC+Codex), capability-class framed lean-vs-heavy (vs playwright-MCP 47 def); neutral idle, delta_pct null (honest — not a token-saver); install agent-driven (setup-prompt→install.md) NOT install-tested, Gemini unverified; router live (browser prompt 0.243). cand triage = deep-vet §6/§7.
- [x] **efficiency-starter host-conditional anchor** 2026-06-06 — code-intel splits by host: **CC=codegraph** (idle free on lazy-load + richer: callers/callees/impact) / **Codex+Gemini=semble** (509 vs codegraph 1615 idle tok CALCULATED = 68% leaner on load-all). New `host_anchor` field (tool→host[]) threaded through healthcheck (`alt` status, non-fatal) + install (`alt_skipped`, skips other-host tool) + CLI. codex/gemini token_profile now `calculated` 509 (was estimated). N1: 1 code-intel MCP/host (XOR) + rtk. 71 tests (was 67: +2 healthcheck host-cond, +2 install host-cond). **codegraph index BUILT for port-a-whip itself** (21 files/283 nodes) → codegraph_explore live for this repo.

### Phase 3 — Lesson-memory (durable moat)
> Design crystallized in [docs/L3-DESIGN.md](docs/L3-DESIGN.md) (R1-R12 + anchor weighting + scope + build-order). Built 2026-06-10 (164 tests; kernel-unify + inject live).
- [x] **L3 core BUILT (Phase 1-6, `portaw/memory/`)** — lesson + project memory, recall works end-to-end:
  - schema (content-hash id = free cross-project dedup, R8 compressed body) + store (jsonl, global `~/.paw/memory` + project `.paw/memory`, atomic, malformed-tolerant, upsert-bump, archive)
  - retrieval = HYBRID reusing the ONE kernel (`kernel.route`, semantic) + anchor overlap (path/symbol, zero-setup structural; codegraph node = present-only bonus) + ACT-R activation rank (recency×frequency); applicability filter (universal/stack/project); **silence-default**
  - injection = silence-biased, per-type threshold (lesson low / project high), budget cap, pinned-first; **wired into `adapters/router.py`** (memory injects alongside set hits, fail-safe)
  - capture = `FailureSignal` → applicability auto-tag → integrity gate (§7, scope-scaled bar) → upsert; cross-host `paw_lesson` contract (`run_capture_hook`, safe-by-construction)
  - consolidate = async "dream": merge/promote/decay-archive (extends mistakes-sweep ethos); seed = ADR-harvest v1 (confirm-gated)
  - CLI: `portaw memory add/list/recall/capture/capture-hook/consolidate/init`
- [x] **WIRED LIVE on this box** 2026-06-10: `memory capture-hook` into CC Stop event (settings.json, coexists w/ mistake-learning) + NL transcript→FailureSignal detector (`memory/detect.py`, Bash fail→fix, Jaccard-gated, 0 noise on real transcript).
- [x] **kernel-unify + INJECT LIVE** 2026-06-10 (`integration/skill-router.py`): the author's live UserPromptSubmit hook now (1) delegates ranking to paw's canonical `kernel.ranking.route` — ONE ranker in the live path, inline copy = zero-paw fallback (pinned by `tests/test_skill_router_parity.py`, 14/14 real-corpus parity); (2) surfaces paw L3 memory (+sets) via `router.paw_block` through that ONE hook (no second competing hook → no double-fire). Memory inject is now LIVE end-to-end (capture→store→recall→inject). Deploy = edit `integration/skill-router.py` then copy over (~/.claude/hooks/* is nah-protected; `nah trust` does NOT clear the hard self-protection — copy from your own shell). 164 tests (incl. parity).
- [ ] **port capture to Codex/Gemini live** (router portability now proven/wired on Codex; memory capture is separate and still unproven: Stop-event name + transcript format need live confirmation per host) + cross-host lesson sync
- [ ] embedding tier-2 (lazy, reuse skill-router model) — floor ships TF-IDF+anchor; embedding = opt-in upgrade
- runtime deps unchanged (click + tomlkit); memory adds NO mandatory per-project setup (`.paw/memory` dir only)
- ⚠️ L3 axis is NON-NEGOTIABLE = **cross-host portability + mistake-surfacing** (NOT general agent memory). jcode (host) already does intra-host general memory better — paw is redundant if it drifts off these 2 axes. See [registry/deep-vet.md](registry/deep-vet.md) §7.
- [x] **DOGFOOD 2026-06-10 (full trial, all 3 layers).** L1 install/verify (secure-agent 4/4 health PASS), L2 router live (CC via skill-router bridge + Codex via its own hook, live-fire confirmed), L3 inject live. Fixed 2 dogfood bugs: `memory add --pin` was never wired to the entry; manual adds now default `confidence=0.9` = trusted (a deliberate human assertion clears the universal bar without `--pin`; auto `hook`/`agent` lessons still must earn it). ⚠️ **Capture DETECTOR yields 0 on real transcripts** — Bash fail→fix is too narrow (real fixes are cross-tool / >4 calls apart / long one-offs). So **manual `memory add` is the proven capture path**, and the next high-value build = a **`mistakes-index.md`→lessons harvester** (the user's curated index is the gold source; analogous to `seed.py`'s ADR harvest). port-a-whip's own project-memory seeded with 7 principled lines (`.paw/memory/project.jsonl`, travels with the repo).
- **Per-project setup** (running paw *on* a repo): (1) **codegraph** — `codegraph index` (code-nav, CC idle-free) or the `codegraph-link` skill; (2) **paw project-memory** — `portaw memory init --confirm` harvests `docs/adr/*`, else `portaw memory add --type project` manually. graphify/obsidian = trial-only (token-heavy at init), skip. paw's global router + lesson-memory need NO per-project setup (just the `.paw/memory` dir, auto-created).

### Phase 4 — GUI/app (CANDIDATE only, build AFTER L3)
- [ ] `portaw ui` — explicit subcommand (NOT no-arg default), **stateless, NO daemon**: pick set → token_profile + config **diff** preview → apply → exit. Guardrails: **no-daemon · no-host (never free-claude-code-style web agent UI) · explicit-subcommand**. Native TUI/exe > web (daemon risk). Off paw's token/quality axis (= human config-UX) → only pays off wrapping the MOAT, never before L3. Rationale + the rejected forms (no-arg→GUI, localhost-web-host) in [registry/deep-vet.md](registry/deep-vet.md) §7.

## Stack
- Python 3.11+, Click 8.x
- config patching: stdlib `json` + `tomllib` (read) + `tomlkit` (TOML write, preserves comments) — only non-stdlib dep
- ranking: TF-IDF + multilingual embedding (lean)
- No daemon, no Smithery/mcpm runtime dep — runs, patches, exits. Offline-capable.
- Node 18+ only needed at *set runtime* if a set's tool runs via npx (not a paw dep)

## Security
- non-MCP install: NO shell=True for community sets — RCE vector. hash/signature verify before community sets (Phase 4).
- env: `.env` + `${VAR}` ref, never plaintext secret in config
- MCP source = curated sets only (reviewed before entry), not arbitrary registry → small surface
- patch config: backup before write + parse-validate before write (avoid corrupt config)

## Known issues / TODOs
- ✅ VERIFIED 2026-06-05: Codex key = `[mcp_servers.<name>]` (command/args + `[mcp_servers.<name>.env]`). tomlkit 0.15 round-trip preserves header/inline/env comments on merge; tomllib re-reads clean. EDGE: patcher must create `[mcp_servers]` parent table if absent (fresh config) before sub-assign — else KeyError. (alt path exists: `codex mcp add` CLI, but self-patch keeps 0-dep + uniform across hosts.)
- Gemini `BeforeAgent` inject field read from docs, not yet tested live
- config.py must handle multi-format (CC/Gemini JSON + Codex TOML); merge into existing config without clobbering user's other servers
- Cursor/OpenCode: native already strong (Cursor self-optimizes); set-install only, router static. Low priority.
- need to source/vet the non-MCP (rtk-class) tools for first set

## Harness-quality refinements (2026-06-05, 5 research rounds — see spec §15)
- **Router scope** (correction): router fixes Gap-B (discoverability) + tool-selection accuracy, NOT token-overhead on load-all hosts (defs load from config at startup; router injects on top, can't unload). Overhead → set-size ceiling + code-exec + native lazy-load. Do NOT reorder roadmap L2>L1. Router-driven JIT install = a NEW option (not free from eager-install) — named only, not committed.
- **Capability entry** = `what+when`+`trigger_terms`; registry holds metadata only (name/desc/trigger), inject = JIT pointer (3-tier progressive disclosure); retrieval = TF-IDF+embedding fused + rerank.
- **skill complements MCP** (not either/or): skill = workflow (0 idle token), MCP = primitive (portable, load-all). Router prefers skill/instruction over mcp-tool when equivalent.
- **No sub-agent capability type**: multi-agent ≈ 15× tokens + loses on coding (paw's domain). If ever added: needs contract (objective/output-format/tool-guidance/boundaries) + breadth-first-only gate.
- **L3 = procedural memory** (validated moat: survey shows no one does mistake-surfacing). substrate already exists (author's mistake-learning hook: xN counter/tier/FIXED-archive/sweep = extract+consolidate+decay). Phase 3 = add retrieval layer (relevance-rank, multi-scope tag, rerank). Risk: **staleness** — high-confidence stale lesson = "confidently wrong" → confidence-decay tied to recurrence. always-on index ≈ 26K vs relevance ≈ 7K tokens (−73%).
- **ref impl: `codegraph-link` skill** = working reference for paw L1/doctor: health-gate (`status -j`, not file-presence), drift check (`--print-config` vs live), idempotent managed-block write+unlink (markers), permission/allow-list report. Reuse for `doctor` + instruction-capability + `portaw remove`.
