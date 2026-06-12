# 🐾 port-a-whip (paw)

**Curated sets + capability router + lesson-memory** for coding agents — Claude Code, Codex, Gemini CLI. Zero runtime dependency.

```bash
pip install port-a-whip        # not yet on PyPI (alpha-HOLD); build from source for now
portaw install efficiency-starter
```

> **Status: alpha (v0.3, Phase 1-3 built, 346 tests).** L1-L3 all live on Claude Code + Codex; Gemini wired but not live-verified. L3 now carries typed memoir edges, a wake-pack project digest, and git-backed cross-host sync. Source of truth → [port-a-whip-spec.md](port-a-whip-spec.md).

## What it is

Three layers, one criterion — *reduce tokens OR improve context quality*:

1. **Curated sets** — bundles (MCP + non-MCP) vetted to be quality **and** actually compatible together. One command installs the whole set.
2. **Capability router** — per-prompt, surfaces which skill / tool / instruction to use. Token-lean (TF-IDF + optional multilingual embedding).
3. **Lesson-memory** — captures mistakes, surfaces relevant ones across hosts. The durable moat (no host/vendor remembers *your* errors).

## What it isn't

A general MCP installer/registry — Smithery / mcpm / MCPDog already do cross-host install + thousands of tools. paw adds only what they don't: vetted *combos*, non-MCP tools, per-prompt routing, cross-host lessons. For single tools, use Smithery directly.

paw patches host config itself (JSON / TOML) — no Smithery, no daemon, offline-capable.

## Commands

```bash
# Sets (L1)
portaw sets list                 # browse 6 curated sets
portaw sets show <set>           # tools + token profile + compat notes
portaw install <set> [--host X]  # patch MCP config (backup+validate) + show manual shim
portaw remove <set> [--host X]   # un-patch config
portaw verify <set>              # health-check: are tools reachable on PATH?
portaw doctor                    # env + host detect + config parse-valid?

# Bench (B1 token-delta)
portaw bench list                # recent sessions (ccusage)
portaw bench ab <base> <treat>   # diff two session ids
portaw bench how                 # A/B protocol

# Router (L2)
portaw router test <prompt>      # dry-run: what would the router inject?
portaw router enable [--host X]  # wire hook into host config
portaw router disable [--host X]
portaw router status [--host X]

# Memory (L3)
portaw memory add <body> [--type lesson|project] [--pin] [--trigger X]
portaw memory list [--type X]
portaw memory recall <prompt> [--symbol X] [--path X] [--embed]
portaw memory pin <id> [--unpin]
portaw memory rm <id>
portaw memory link <src> <rel> <dst>   # typed memoir edge (superseded_by|contradicts|caused_by|related), cross-store
portaw memory export [--out file.md]
portaw memory capture --trigger X --fix Y [--symbol X]
portaw memory consolidate [--dry-run] [--every session|N]  # dream: merge/promote/decay + auto-supersede (OFF by default)
portaw memory sync [--init <private-remote>]  # git-backed cross-host lesson sync (content-hash fold)
portaw memory init [--confirm]         # seed project-memory from docs/adr/*
portaw memory harvest [--confirm]      # harvest mistakes-index.md → lessons
portaw memory enable [--host X]        # wire capture hook (Stop event)
portaw memory inject-enable session|tool|all   # live-inject surfaces (SessionStart pins + wake-pack, PostToolUse recall)
portaw memory inject-disable session|tool|all
```

## Curated sets (6)

| Set | MCP | non-MCP | Token profile | Why |
|-----|-----|---------|---------------|-----|
| **efficiency-starter** | codegraph + semble (host-conditional) | rtk | rtk measured −26.3% / codegraph vendor-claimed | code-nav cuts grep/read calls; rtk compresses shell output |
| **secure-agent** | nah + gitleaks + osv-scanner + infisical | — | neutral (0 MCP defs) | Permissions differ from registries — 0 idle tokens |
| **context-quality** | Context7 | — | calculated 927 tok idle (load-all); 0 on CC | anti-hallucination: current docs on demand |
| **design-quality** | figtree-cli | impeccable (/skill) | neutral (non-MCP) | anti-slop design review |
| **web-research** | Fetch-MCP (keyless) | SearXNG / Scrapling / exa / firecrawl (opt-in ladder) | Fetch 1 def | research primitives agent composes (search→fetch→extract, auditable) |
| **browser-automation** | — | browser-harness (/skill + CDP) | neutral (0 MCP defs) | self-healing browser via CDP, lean vs playwright-MCP (47 defs) |

## Host support

| Host | Inject event | Tier | Live? | paw value |
|------|-------------|------|-------|-----------|
| Claude Code | `UserPromptSubmit` | 1 | ✅ router + memory | low (native strong) |
| Codex CLI | `UserPromptSubmit` | 1 | ✅ router; memory capture unproven | **high** (native weak) |
| Gemini CLI | `BeforeAgent` | 1 | ⚠️ wired, not live-verified | **high** |
| Cursor / OpenCode | static only | 2 | — | low (Cursor self-optimizes −46.9%) |

## Architecture

```
port-a-whip/
├── portaw/                    # package; CLI = `portaw`
│   ├── main.py                # Click CLI (6 groups; memory group = 21 commands)
│   ├── config.py              # detect host; locate + parse config (json/toml)
│   ├── bench.py               # B1 token-delta bench (ccusage wrapper)
│   ├── sets/                  # L1: set load + install orchestration
│   │   ├── loader.py          # parse sets.json
│   │   ├── patcher.py         # patch host config (json+toml dict-merge, backup)
│   │   ├── install.py         # orchestrator (N1 ceiling, host resolve, shim)
│   │   ├── healthcheck.py     # §10 health-gate (binary probe, host-cond anchors)
│   │   ├── state.py           # ~/.paw/state.json ledger — what paw wrote per host
│   │   └── usage.py           # real tool_use evidence from transcripts (idle-def flag)
│   ├── kernel/                # L2: portable ranking (also used by L3)
│   │   ├── ranking.py         # TF-IDF tier-1 + intent-boost + conflict-prune
│   │   ├── registry.py        # capability registry (built from sets.json)
│   │   └── embed.py           # tier-2 multilingual MiniLM (opt-in, lazy, fail-safe)
│   ├── adapters/              # per-host inject
│   │   ├── router.py          # UserPromptSubmit/BeforeAgent hook + paw_block inject
│   │   └── memory_hooks.py    # SessionStart pinned / PostToolUse recall
│   └── memory/                # L3: lesson + project memory
│       ├── schema.py          # content-hash id, MemoryEntry, typed Relation edges
│       ├── store.py           # jsonl (global ~/.paw + project .paw), atomic upsert, link()
│       ├── retrieval.py       # hybrid: TF-IDF + anchor + ACT-R + edge reshape (suppress/contradict/fan-out)
│       ├── similarity.py      # embedding near-neighbours → seed memoir edges (fail-safe)
│       ├── inject.py          # silence-biased, per-type threshold, budget cap + wake-pack digest
│       ├── capture.py         # FailureSignal → gate → upsert (+ additive related-edge seeding)
│       ├── detect.py          # NL transcript→FailureSignal detector
│       ├── gate.py            # integrity gate (scope-scaled bar)
│       ├── confidence.py      # confidence decay tied to recurrence + misses
│       ├── outcomes.py        # L3 effectiveness loop (misses → distrust)
│       ├── observations.py    # raw signal staging
│       ├── anchors.py         # zero-setup structural (path/symbol)
│       ├── context.py         # host-context derivation
│       ├── consolidate.py     # async dream (OFF by default): merge/promote/decay + auto-supersede
│       ├── harvest.py         # mistakes-index.md → lessons harvester
│       ├── sync.py            # git-backed cross-host lesson sync (content-hash fold)
│       ├── seed.py            # ADR→project-memory
│       ├── hookwire.py        # wire capture/inject hooks into host config
│       └── sessionlog.py      # session-transcript parser
├── registry/
│   └── sets.json              # 6 curated sets (NOT per-tool registry)
├── integration/
│   └── skill-router.py        # author's live hook bridge (kernel-unify)
├── tests/                     # 346 tests
├── docs/
│   └── L3-DESIGN.md           # L3 design (R1-R13 incl. memoir edges)
├── pyproject.toml
├── CLAUDE.md                  # build-facing summary
└── port-a-whip-spec.md        # source of truth (v0.3)
```

## Stack

- Python 3.11+, Click 8.x, tomlkit (TOML write, preserves comments)
- Ranking: TF-IDF + optional ONNX MiniLM embedding (opt-in `[embed]` extra, lazy + fail-safe)
- Storage: JSONL (atomic writes, malformed-tolerant)
- No daemon, no Smithery/mcpm runtime dep — runs, patches, exits. Offline-capable.
- Node 18+ only needed at *set runtime* if a set's tool runs via npx (not a paw dep)

## Roadmap

### Phase 1 — Sets + Claude Code ✅
Set schema, 6 curated sets, patcher (json+toml dict-merge), shim, health-check, doctor, B1 bench, ranking engine, router adapter, PyPI build-ready.

### Phase 2 — Portable router + token-vetted sets ✅
Codex adapter (TOML, live-verified), Gemini adapter (JSON, wired), token metric protocol v2, host-conditional anchors (codegraph/semble XOR), 2 more sets (design-quality, web-research), browser-automation (set #6).

### Phase 3 — Lesson-memory ✅
L3 core built (346 tests): schema, store, hybrid retrieval, silence-biased inject, capture + gate, consolidate, mistakes-index harvester, embedding tier-2, kernel-unify (live inject via skill-router bridge), dogfood (all 3 layers live).

**Memoir edges + connection layer (R13):** typed `relations` between entries (superseded_by / contradicts / caused_by / related) reshape recall — suppress superseded, drop the weaker contradiction side, 1-hop fan-out from survivors (no-op on legacy data). Capture seeds only additive `related` edges (poison-safe); suppressive edges come only from consolidation (`supersede_pairs`, 6 guards) or manual `memory link`. **Wake-pack**: SessionStart injects a high-confidence project-memory digest (≤150 tok) for anti-hallucination grounding on short-context / weak-local models. Dream cadence is user-set and **OFF by default**.

**Evidence loops** (all 3 layers learn): L1 state ledger + `doctor --usage` (real `tool_use`, not mentions); L2 outcome loop (suggested ≥5 + used 0 → demoted); L3 effectiveness (`misses ≥3` → distrust even at high confidence). L3 sync = git-backed, content-hash fold, imports quarantined until local recurrence.

### Phase 3 remaining
- [ ] Capture hook port to Codex/Gemini (Stop event name + transcript format need live confirmation)
- [ ] Real-ONNX + live-transcript dogfood of memoir edges (all R13 tests use injected encoder → DOGFOOD-PENDING #13)

### Phase 4 — GUI (candidate)
- [ ] `portaw ui` — stateless TUI, explicit subcommand, no daemon

## Security

- non-MCP install: NO `shell=True` for community strings — RCE vector
- env: `.env` + `${VAR}` ref, never plaintext secret in config
- MCP source = curated sets only (reviewed before entry) → small surface
- patch config: backup before write + parse-validate before write (avoid corrupt config)

## By whipforaweep
