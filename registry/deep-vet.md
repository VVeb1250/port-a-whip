# Deep-vet — backlog → curated sets

> Pass 1 (2026-06-05) over candidate-backlog.md (~205 verified). Output = decisions, not raw shortlist.
> **Curation-stage gate** (pre-runtime): pass ต้อง (a) ลด token **หรือ** เพิ่ม quality, (b) N1-safe (≤2-3 active MCP/set, count def), (c) compat (ไม่ชน tool อื่นใน set), (d) maturity (drop <3★ solo stale เว้นแต่ concept unique).
> **Runtime gate (§10)** = ตอน build set จริง: token-delta จาก session log + install health-check. ทำไม่ได้ตอน vet — แยกชั้น.
> Decision tag: **CURATE** (เข้า set) / **BUILD-KIT** (paw ใช้สร้างเอง ไม่ curate) / **DELIVERY** (กลไก ไม่ใช่ candidate) / **CORE-DEP** / **DROP** / **DEFER**.

---

## 0. Non-set classifications (แยกก่อน — ไม่ใช่ candidate ใน set)

| item | tag | เหตุผล | ป้อนเข้า |
|---|---|---|---|
| **mcp2cli** | DELIVERY | "96-99% schema token saved" = แก้ MCP ceiling ที่ราก. ไม่ใช่ tool ใน set แต่เป็น *วิธีส่ง* MCP → CLI | spec `delivery: code-exec` field (Phase 4); วัดคู่ code-exec |
| **ccusage** (15.6k★) | BUILD-KIT | parse `~/.claude` JSONL → token/cost diff 2 run | **B1 bench** — wrap |
| **agentevals** (609★) | BUILD-KIT | trajectory eval strict/subset match (deterministic, offline, no-LLM) | **§10 eval gate** — wrap |
| **CC native OTel** | BUILD-KIT | `CLAUDE_CODE_ENABLE_TELEMETRY=1` → OTLP GenAI semconv | **B3 budget** — first-party |
| **rulesync** (1.1k★) | CORE-DEP? | author-once → 20+ host rule file = ตรง paw cross-host vision เป๊ะ | instruction-capability impl (Phase 3); vet เป็น dep ไม่ใช่ set entry |
| **agents.md** (22k★) | CORE-DEP? | AGENTS.md open format (Linux Foundation) = normalize target ของ instruction inject | instruction schema |
| **Graphiti / mem0 / agent-file** | DEFER (learn-from) | temporal KG / local-first store / portable .af format | L3 Phase 3 — port idea, อย่า rebuild |

---

## 1. CURATE — proposed sets (N1-checked, compat-checked)

> rule: นับ MCP def ต่อ set. CLI/hook = 0 def (ฟรีต่อ ceiling). prefer CLI เมื่อ equivalent.

### S1. `efficiency-starter` (EXISTS, registry/sets.json) — ✅ anchor LOCKED 2026-06-05
- **codegraph** (MCP, lazy-load `CODEGRAPH_MCP_TOOLS` subset) + **rtk** (non-MCP proxy/hook).
- **+ ast-grep** (non-MCP CLI, ฟรีต่อ ceiling) — structural search layer ระหว่าง rg↔codegraph. compat_note: ชน codegraph "find usages" บางส่วน → trigger_terms แยก (ast-grep=rewrite/structural, codegraph=semantic-graph).
- ~~BLOCKER~~ **RESOLVED**: rtk paired-bench รันแล้ว (rtk-gain instrumentation = command-level paired raw-vs-compressed, ดีกว่า 2-session diff เพราะ zero cache noise). **MEASURED: 26.3% mixed real / 35.6K saved / 320 cmds.** profile: ชนะหนัก bulk/structured (diff 74.9%, ls 68-87%), อ่อน read 7.8%/grep 10.6% (เจือจาง mix). vendor "60-90%" = best-case-per-command จริง แต่ mixed-session = 26.3%.
- **anchor decision: NO SWAP.** rivals (context-mode 16.4k★/lean-ctx/snip/ecotokens) ★ สูงกว่าก็จริง แต่ไม่มีตัวไหน self-report reproducible command-level number — rtk มี (rtk gain). lock rtk จนกว่า rival จะแสดงเลขที่วัดได้เทียบบน workload เดียวกัน.
- MCP count: 1 (codegraph). ✅ N1-safe.

### S2. `secure-agent` — ⭐ DIFFERENTIATOR (Permissions ช่องว่างที่ registry อื่นไม่ครอบ)
- **nah** (449★ PreToolUse hook, deterministic classifier, tighten-only override) — permission guard. 0 def.
- **gitleaks** (27.5k★ CLI) — secret guard pre-commit (`gitleaks stdin`). 0 def.
- **osv-scanner** (Google CLI, AGENTS.md+llms.txt agent-aware) — multi-lang dep audit. 0 def.
- **+ Infisical CLI** (27.2k★, `infisical run` inject secret as env → agent ไม่เห็น raw token). 0 def.
- optional **microsandbox** (~5k★ libkrun microVM <200ms) — hardware isolation, off-by-default ใน CC.
- MCP count: **0** (ทั้ง set เป็น CLI/hook). ✅✅ N1-free, ลงทุก host ได้. = paw ครอบ threat-class ที่ codegraph+rtk ว่างสนิท.
- compat: gitleaks ⊕ detect-secrets เลือก 1 (ggshield ถ้าต้อง active-validation). nah ⊕ landrun/microsandbox = guard layer ต่างกัน (รวมได้).

### S3. `context-quality` — ↑quality (anti-hallucination)
- **Context7** (MCP, "most impactful MCP for code quality", live version docs).
- compat: GitHub-code-search ก็ ↑quality แต่ GitHub MCP = **87 tools = Massive** → ❌ อย่าใส่ทั้งก้อน. ถ้าต้อง search_code → **BUILD thin 1-2 tool wrapper** (gap flag 19).
- MCP count: 1. ✅ N1-safe. (เพิ่ม mcpdoc/BYO-llms.txt ได้ถ้าอยาก auditable docs.)

### S4. `git-productivity` — CLI-heavy (flag 17)
- **gtr** (git-worktree-runner, 1.6k★ CLI, Claude/Codex/Gemini adapter) — AI-native worktree, parallel agent ไม่ต้อง stash. 0 def.
- **git-absorb** (5.6k★ CLI) — auto-fixup → ancestor commit. 0 def.
- **difftastic** (25.4k★) + **delta** (31k★) — AST-diff / display. 0 def.
- **cyanheads/git-mcp** (28-tool MCP) = **CC-only** (lazy-load) หรือ subset; บน load-all host ⚠️ 28 def → ใช้ CLI แทน. flag: ปกติ git CLI พอ → MCP เฉพาะถ้าต้อง structured-JSON multi-verbosity.
- MCP count: 0 (CLI path) หรือ 1 (CC + git-mcp). ✅

### S5. `lang-tooling` — pre-adoption play (flag 13-14)
- **mcpls** (39★ MCP) — 1 install bridge pyright/rust-analyzer/tsserver/gopls/clangd. category <50★ = paw bundle ก่อน market ตื่น.
- per-lang anchor ถ้าลึก: Go = **mcp-gopls** (87★) ดีสุดในหมวด; Python/TS/Rust = mcpls bridge.
- **BUILD-OPS** (thin MCP ~30 LOC, JSON output พร้อม): ruff(47.8k★) / clippy(built-in) / biome(24.9k★) / oxc(21.4k★). = paw ship เองเป็น set entry.
- MCP count: 1 (mcpls). ✅ — **subsume many-lang ใน 1 def** = N1-friendly สุด.

### S6. `web-research` — leanest only (E2)
- **Fetch MCP** (official, 1 tool, free, HTML→markdown). 1 def.
- **+ SearXNG** (856★, 2-tool, self-host = no API key) — best-free search. 2 def.
- หรือ **SerpAPI** (1 tool, paid) ถ้าอยาก multi-engine 1 def.
- ❌ Firecrawl(18)/Apify(18)/GitHub(87)/Playwright(47) = Heavy/Massive → drop จาก default set.
- MCP count: ≤3 def. ✅ (borderline — เลือก Fetch+SearXNG หรือ Fetch+SerpAPI).

### S7. `api-dev` — CLI sweep (E4, flag 22)
- **Hurl** (19k★ CLI) REST test + JSON report. **grpcurl** (12.7k★) gRPC. **Prism** (5k★) OpenAPI mock+validate. ทั้งหมด 0 def.
- GraphQL → **Apollo MCP** (4-tool, schema-search) = rare MCP>CLI. 4 def.
- secret → Infisical CLI (ใช้ร่วม S2).
- MCP count: 0 (CLI) หรือ 1×4-def (Apollo ถ้าทำ GraphQL). ✅

### S8. domain sets (viable, anchor มี — สร้างเมื่อต้อง, flag 10)
| set | anchor (token-lean) | MCP def | note |
|---|---|---|---|
| `devops` | **k8sgpt** (7.8k★ CLI+MCP) + Infracost (12.3k★ CLI) + kubeconform CLI | low | flag: gitlab-mcp 100+ def = read-only subset เท่านั้น |
| `data-db` | **dbhub** (2-tool/4-DB) หรือ **usql** (10k★ CLI) | 2 def | dbhub subsume single-DB server |
| `frontend` | **shadcn MCP** + Figma MCP + a11y-mcp; verify = Playwright **หรือ** Chrome-DevTools (เลือก 1) | watch | ceiling: เลือก browser 1 ตัว |
| `codegen` | degit/copier/openapi-typescript/sqlc/graphql-codegen — **ทั้งหมด CLI** deterministic 0-token stamp | 0 | E6 = CLI ล้วน, N1-perfect |
| `workflow` | **Backlog.md** (CLI, state out-of-context) หรือ **spec-kit** (108k★ CLI) | 0 | ❌ Sequential-Thinking (ADD token, ↑qual only) |

---

## 2. DROP / merge (overlap หรือ stale)

| candidate | เหตุผล drop | ใช้แทน |
|---|---|---|
| Tach `tach test` | = codegraph-affected skill อยู่แล้ว | codegraph-affected |
| Comby | stale 2022 OCaml | ast-grep |
| mgrep / semantic-grep | redundant กับ codegraph (ทั้งคู่ semantic) | codegraph |
| jcodemunch-mcp | HIGH overlap codegraph (source exploration) | codegraph |
| schemats | archived 2018 | kanel / sqlc |
| HTTPie | stale 2024-12 | xh |
| landrun cluster | เลือก 1 จาก landrun/microsandbox/landlock | microsandbox (แกร่งสุด) |
| Linear ⊕ Atlassian, Qdrant ⊕ Chroma, k8s-server | exclusive — เลือกตาม stack | per-project |
| Sequential-Thinking (86k★) | ADD token ไม่ ↓ (↑qual only) | Clear-Thought (1 def/38 op) ถ้าต้อง |
| naive auto-CLAUDE.md gen (/init, llmstxt-gen) | ⚠️ ETH study −3% success/+20% cost | hand-edit + rulesync |
| Kong mcp-konnect / gateway servers | 42★ vendor / infra ไม่ใช่ agent tool | = gap → paw-build bounded MCP |

---

## 3. BUILD-OPS priority (paw-built differentiator, จาก gap-flags)

| # | build | leverage | effort | จาก |
|---|---|---|---|---|
| 1 | **B1 bench** (wrap ccusage) + **§10 eval** (wrap agentevals) | H — unblock "no vibes" gate ทันที | low (wrap) | flag 7 |
| 2 | **B5 perms** allowlist + **secure-agent set** (nah/gitleaks/osv/Infisical) | H — Permissions = ช่องว่างไม่มีคู่แข่ง | low-med | flag 3 |
| 3 | thin MCP wrapper: ruff/clippy/biome/oxc (~30 LOC ต่อตัว) | M-H — ship เป็น lang-tooling set entry | low ×4 | flag 14 |
| 4 | GitHub Code-Search-only MCP (แยก search_code ออกจาก 87-tool) | M-H — N1-perfect, fills context-quality | low | flag 19 |
| 5 | bounded MCP: api-gateway / webhook-capture / token-broker | M — empty agent-native category | med | flag 23 |
| 6 | CodeQL-lite (SARIF → rule-id+file:line+severity) / structured merge-resolution | M | med | E5/E3 gap |

---

## 4. ทันที (lock ก่อนขยับ) — STATUS 2026-06-05

1. ✅ **B1-bench BUILT + rtk anchor LOCKED** — `portaw bench list/ab/how` (portaw/bench.py, wraps ccusage, 8 tests). **VERDICT rtk-vs-peers RESOLVED 2026-06-05**: rtk-gain instrumentation (command-level paired raw-vs-compressed, ดีกว่า session-diff = zero cache noise) → **26.3% mixed / 35.6K saved / 320 cmds**. anchor = NO SWAP (rivals ไม่ self-report reproducible number; rtk มี). efficiency-starter token_profile_benchmarked = partial (rtk done, codegraph Phase-2).
2. ✅ **S2 secure-agent DRAFTED → sets.json** — 0 MCP def, 4 guard (nah v0.9.0/gitleaks v8.30.1/osv-scanner v2.3.8/infisical v0.160.10), install commands verified จาก official README. criterion-note: axis = Permissions component (ไม่ over-claim token).
3. ✅ **S3 context-quality DRAFTED → sets.json** — Context7 (@upstash/context7-mcp, 56.7k★, 2 tools), API key optional via env. axis = ↑quality. N1-safe.
4. ⏳ ที่เหลือ = build เมื่อ Phase ถึง (domain sets, lang-tooling thin-wrapper, build-ops #3-6).

> next ที่ยัง unblock ไม่รอ Phase:
> - ~~รัน rtk paired-bench~~ ✅ DONE (rtk anchor locked, 26.3% measured). OPTIONAL Phase-2: peer A/B (context-mode/lean-ctx/snip/ecotokens บน workload เดียว) เพื่อ challenge anchor ด้วยเลขเทียบตรง — แต่ rtk ชนะ bar "ตัวที่วัดได้" แล้ว.
> - **§10 eval-gate** (wrap agentevals, build-ops #1 ครึ่งหลัง) — คู่กับ B1 ทำ §10 รันได้จริง.
> - **patcher/shim impl** (Phase 1 core) — ตอนนี้ 3 set มีใน registry แต่ `portaw install` ยัง stub.

## 5. Token-metric protocol (Phase-2, 2026-06-06)

`token_profile` schema v2 (sets.json 0.3.1): per-host `{provenance, delta_pct,
idle_def_tokens, sample, note}`. **Provenance moved out of prose `_note` into a
machine-readable enum** — directly encodes the rtk-over-claim lesson (a measured
number and a vendor claim must never look alike).

**Enum (honesty knife — count vs heuristic stays sharp):**
| provenance | meaning | how |
|---|---|---|
| `measured` | paw ran it | ccusage A/B (`bench --ab/--how`) on the set's canonical workload, or rtk-gain command-level instrumentation |
| `calculated` | real count, no session | tiktoken (cl100k proxy) on the **verbatim live MCP tool-def JSON** the host loads. NOT a rule-of-thumb |
| `vendor-claimed` | vendor docs, unverified | flagged, never laundered into "measured" |
| `estimated` | reasoned, no measurement | the honest floor when neither count nor A/B exists yet |
| `neutral` | provably 0 | 0 MCP tool-defs by construction (CLI/hook) — no schema cost on any host |

**Two numbers, not one** (they point opposite ways): `delta_pct` = runtime tokens
SAVED (+); `idle_def_tokens` = always-on tool-def cost on load-all hosts (0 on CC,
which lazy-loads). A set can save at runtime *and* cost idle defs — both recorded.

**Set provenance = weakest link.** efficiency-starter CC = `vendor-claimed` even
though rtk is measured, because codegraph drags it (don't let a strong component
launder an unverified one). Note spells out the per-tool mix.

**Status of the 3 shipped sets:**
- `secure-agent` → **`neutral`** all hosts (0 MCP defs). CLOSED, certain.
- `context-quality` → **`calculated`**: tiktoken on the real Context7 def JSON =
  **927 tok** load-all idle (resolve-library-id 611 + query-docs 316); 0 on CC.
  CLOSED (host tokenizer ±10-15% caveat noted).
- `efficiency-starter` → rtk **`measured`** 26.3% (CC); codegraph **`vendor-claimed`**
  + codex/gemini **`estimated`** → PENDING the A/B in `bench/codegraph-workload.md`
  (delta_pct) + a tiktoken of codegraph's 8-9 defs (idle_def_tokens). Marked, not fabricated.

**The protocol is method + schema, not new CLI surface.** `bench --how` already
documents the A/B; `bench --ab` already runs it; canonical workloads live in
`bench/<tool>-workload.md` (rtk + codegraph). No `bench profile` subcommand (YAGNI).
To profile a new set: pick its provenance class first — most sets are `neutral`
(no MCP) or `calculated` (tokenize defs); only token-SAVING tools need an A/B.

## 6. Candidate re-vet 2026-06-06 (user batch — ~28 cands) + anchor challenge

Triage vs paw criterion (↓token OR ↑quality) + N1 + "NOT a general installer".

**The field moved — 2 tools now challenge efficiency-starter's anchors on paw's OWN axis. Honesty rule: do NOT swap on vendor claims — bench them.**

### Anchor challenge A: code-intel — **semble** vs **codegraph**
- **semble** (MinishLab, 4.9k★): semantic code search MCP, 2 tools (`search`+`find_related`), claims ~98% fewer tok than grep+read, 250ms index, CPU.
- **IDLE-DEF CALCULATED 2026-06-06** (tiktoken cl100k on live schemas): **codegraph 1615 tok (8 tools) vs semble 509 tok (2+instructions) → semble 68% leaner** on load-all hosts (Codex/Gemini). On CC both lazy-load → idle ≈ 0, axis moot.
- NOT feature-equal: codegraph richer (callers/callees/**impact** for refactors, explore=verbatim source); semble = search + similarity only. **Lean vs capability.**
- VERDICT (idle axis decided, runtime PENDING): on load-all hosts semble's 1106-tok-lower idle is real IF need = search; codegraph wins when refactor-impact/call-graph needed. Candidate: **host-conditional anchor** (semble on Codex/Gemini load-all, codegraph on CC where idle free + richer wins) OR ship both as separate sets. Runtime delta (grep+read replacement) = A/B PENDING → semble lane added to `bench/codegraph-workload.md`.
- **ROP 3-LANE RUN 2026-06-09 (grep A0 / codegraph A1 / semble A2, 3 real repos: rop-algorithm Go+C++, rop-backend Go, rop-frontend Next.js; same 5-question workload; A0=3 trials/repo, A1=3, A2=2).** **Token-delta NOT isolable** — the per-lane CC sessions were not single-workload-clean (session totals 0.7M-20M tok = contaminated by other activity), so ccusage A/B was abandoned and CAPABILITY/COMPLETENESS became the decisive axis (identical outcome shape to web-research: when the clean token number can't be had honestly, judge on capability). **RESULT (consistent across all 3 repos):** (a) **codegraph = 5/5 FULLY** every trial — `callers`/`impact`/`explore` directly answer Q2 (all callers) + Q3 (signature-change impact), ~15 calls/trial. (b) **semble = SEARCH-shaped only** — Q1 entrypoint (partial/full), Q4 config (full), Q5 architecture (full) via `search`, but **Q2 callers ALWAYS PARTIAL** and **Q3 impact NOT/PARTIAL**: semble has no structural callers/callees/impact tool, `find_related` returns semantic neighbours not references ("No chunk found" on some), and it missed small/unindexed files + cross-repo config. One head-to-head: codegraph 5/5 FULLY ~15 calls vs semble 1/5 FULLY + 3/5 PARTIAL + 1/5 NOT in 23 calls (more calls, less answered). (c) **grep A0 = 5/5 FULLY but expensive** (long multi-file traces; the deterministic 2026-06-08 proxy already quantified ~97% codegraph saving on the relationship class). **VERDICT: host-conditional anchor confirmed on CAPABILITY grounds, not just idle-def** — codegraph earns CC (idle-free + the ONLY tool that answers refactor/impact/caller questions); semble's 509-idle leanness pays off ONLY where the load-all-host workload is pure discovery/search. A code-intel set that must support refactor/impact work cannot anchor on semble alone. (raw answers: `D:/Organize/ROP/<repo>/portawhip.md`.)
- **VENDOR BENCHES (external, found 2026-06-09 — provenance `vendor-claimed` but CORROBORATED by paw's own capability run + deterministic proxy, so recorded not laundered):** (a) **codegraph** (github.com/colbymchenry/codegraph): 7 codebases × 7 languages, one architecture question each, **median of 4 runs/arm** (real methodology) → **59% fewer tokens, 70% fewer tool-calls, 35% cheaper, 49% faster**; compact-mode 23% cheaper/32% faster; **include_source=true on whole files = 64% WORSE** — this caveat EXACTLY matches paw's own deterministic proxy (codegraph_explore over-returns on show-one-file = 4.8x MORE than targeted Read). "auth request flow" Q = 40+ grep/Read calls → 2-4 MCP calls (mirrors paw's ~15-calls-vs-grep-sweep). (b) **semble** (github.com/MinishLab/semble): 1250 query/doc pairs × 63 repos × 19 langs → **98% fewer tokens than grep+read, 94% recall @ 2k tokens, NDCG@10 0.854** — BUT this is SEARCH/RETRIEVAL quality only, which is EXACTLY paw's finding: semble is a superb search primitive (Q1/Q4/Q5 discovery) and the 98% applies there, NOT to callers/impact (Q2/Q3) which semble structurally cannot do. **NET: the clean runtime delta paw couldn't isolate locally (contaminated sessions) is now covered by two published vendor benches whose methodology + caveats independently agree with paw's capability run and proxy — codegraph ~59% fewer tokens/70% fewer calls on relationship/architecture Qs (loses on show-one-file), semble ~98% on search-retrieval (silent on call-graph). No isolated-session ccusage re-run needed; if a paw-OWNED `measured` number is ever wanted, it still requires discipline-isolated single-workload sessions.**
- **codegraph runtime — DETERMINISTIC proxy 2026-06-08** (tiktoken on tool-returns, port-a-whip self-index, n=1 small repo; bench/out/codeintel/). QUESTION-TYPE-DEPENDENT, two ends: (a) **relationship/impact** = codegraph callers+impact(get_set) 172 tok vs grep+read trace 6,622 = **~97% less** (its home turf; grep can't trace impact cleanly + costs 5 reads). (b) **narrow show-one-file** = codegraph_explore over-returns 3 files 2,894 tok vs targeted Read of config.py 606 = **~4.8x MORE** (explore = Read-equivalent, dumps whole files+neighbors). → codegraph's win is real+large for callers/callees/impact (use those tools), but it LOSES on show-one-symbol where Read is leaner. NO blanket delta_pct; depends on question mix. This is the deterministic into-context proxy (validity = like web-research's file-tokenize); full session ccusage A/B (tool-call-count axis + mixed operational workload) still needs fresh sessions (bench/guides/04-05). Confirms the host-conditional logic: codegraph earns CC (idle-free + crushes relationship Qs); semble's narrower search may suffice on load-all where idle matters.

### Anchor challenge B: tool-output compression — **headroom** vs **rtk**
- **headroom** (chopratejas, 11.4k★): compress tool-output/logs/files/RAG, claims **60-95%** (rtk MEASURED 26.3% mixed). lib/proxy/MCP. AST-aware (Py/JS/Go/Rust/Java/C++) + HF Kompress model. **+`learn` mines failed sessions→CLAUDE.md = RIVALS paw L3 moat.**
- Same class as rtk in proxy/lib form = **0 idle def** → head-to-head valid (both non-MCP). Architecture trade (stateable now): rtk = Rust, lean, 0-dep, fast; headroom = heavier (Python+model) but higher ceiling + does more. paw lean-ethos leans rtk; headroom higher-claim.
- VERDICT (RESOLVED 2026-06-09 — reframed): **NOT a swap/rival decision — rtk and headroom are COMPLEMENTARY layers that STACK.** Evidence: (1) a real 1-month production dual-deploy (andrewpatterson.dev/posts/token-savings-rtk-headroom) measured rtk = 1.33B tok saved (**88% of total**) at the PreToolUse-hook layer vs headroom = 189M (**+12% ADDITIVE**) at the API-proxy/session layer — explicitly "additive", different stages (command-output filtering vs session/history compression). rtk per-cmd there: file-read 66.9%, test 98.6%, lint/typecheck 100%, grep 33.6% — same shape as paw's locked rtk profile. headroom per-MODEL: Opus 53% / Sonnet 59% / Haiku 32% (the headline 60-95% is per-content best-case e.g. build-log 94%, NOT session-mixed). (2) paw's OWN deterministic local run 2026-06-09 (`bench/_compress_ab.py`, tiktoken cl100k on raw-vs-rtk command output, rop-backend git-heavy workload): git_diff 69.1%, git_log 53.5%, git_status 70.6%, TOTAL 63.5% (raw 14,643 -> rtk 5,340) — independently corroborates rtk's per-command numbers (not vendor-reported). headroom lane BLOCKED on Windows: headroom-ai ships NO Windows wheel (PyPI 0.24.0 = macOS+manylinux only, cp310-313) and its Rust native ext (maturin/cargo) fails to build without a Rust toolchain on this box (py 3.14 AND 3.12). **DECISION: rtk stays the efficiency-starter anchor** (bigger lever = 88% of real savings, standalone-EXE 0-build on Windows, reproducible). **headroom = a CANDIDATE OPTIONAL additive rung** (API-proxy layer: compresses history/RAG/JSON/build-logs rtk's hook never sees) — but its Windows install friction (no wheel + Rust build) is real dep-cost that keeps it OPTIONAL, not core, for paw's Windows-first author. headroom-`learn` (failed-session→CLAUDE.md) = separately a Phase-3 L3 prior-art (study, below).

### NEW set candidates (drafted, not yet in registry)
- **design-quality** (↑quality, NEW axis no registry curates): **impeccable** (pbakaus 1.2k★, anti-AI-slop, 24 design tells, 0 MCP def) + **open-design** (nexu-io 57k★, agent-agnostic SKILL.md/DESIGN.md platform — curate its skills not whole) + **design-extract** (figtree-cli/figmagic Figma→code). All skill/CLI = N1-free.
- **browser-automation**: **browser-harness** (browser-use, ~592 LOC, CDP-direct, self-healing, NON-MCP=0 def, cross-host CC+Codex) ANCHOR > playwright-MCP (heavy). siblings: dev-browser (skill), browserbase/skills. → **DRAFTED → registry 2026-06-08 (set #6).** refs verified (browser-use/browser-harness MIT 14.5k★ Python skill+CDP; dev-browser MIT 6.2k★ alt; browserbase/skills 3.5k★ cloud rung; browser-use/browser-use 97k★ = full framework REJECTED, runtime-class). neutral idle (0 MCP def by construction), delta_pct null (capability-class, framed lean-vs-heavy = playwright-MCP 47 def). DRAFT: install is agent-driven (setup-prompt→install.md), NOT install-tested; Gemini support unverified. router surfaces it live (browser prompt score 0.243).
- **web-research/scraping** (S6): **firecrawl** (scrape→clean md) + **Scrapling** (D4Vinci, adaptive scraper, built-in MCP, extracts targeted content→cut tok).

### web-research DRAFTED → registry 2026-06-06 (set #5) + the principled line
- **THE LINE (advisor-corrected, not inherited from drop-list):** paw curates research **PRIMITIVES the agent composes** (search→fetch→extract, sources auditable, lean) and **REJECTS answer-product connectors** (perplexity-class: synthesize answer, opaque sourcing, can't compose). Split = **primitive-vs-answer-product, NOT paid-vs-free** — this is why **exa stays IN** (composable search primitive, key-req→optional) while **perplexity stays OUT** even though both are paid SaaS search APIs. Without this articulation the exa-in/perplexity-out split would be inherited ("drop-list said so") not principled. The line also keeps the set consistent with context-quality's anti-hallucination axis (auditable sources > black-box synthesis).
- **shape:** default-on = **Fetch MCP** only (modelcontextprotocol/servers, 1 tool, no key, HTML→md, `uvx mcp-server-fetch`) = N1-trivial keyless anchor (`verify` PASS, uvx on PATH). `optional_sources` ladder opt-in by need: SearXNG (keyless search) → Scrapling (adaptive/targeted extract, CLI=0 idle) → exa (keyed semantic) → firecrawl (keyed JS-heavy, **lean scrape subset only** — NOT the full ~18-tool MCP that was correctly dropped; lean form was always allowed, so this is not an "undrop"). `rejected` block records perplexity/notion/slack + playwright-mcp-full with reasons.
- **status DRAFT:** Fetch shape from README (NOT host-verified), all optional configs UNVERIFIED, token A/B + tiktoken idle-count PENDING. provenance=`estimated`, idle_def_tokens=null on load-all (to CALCULATE before leaving DRAFT). Formalizes the firecrawl+exa pattern the ecc deep-research skill already uses, curated onto paw's axis.
- **honesty note:** user's ask reason ("I sometimes research myself like this session") = personal-utility, NOT a thesis argument. Set earns its place via the token/quality lever (clean-extract + composable+auditable), not "user wants it" — else paw → Smithery.

### web-research CC 3-lane A/B — RESULT 2026-06-08 (the honest number)
Ran the controlled A/B (bench/web-research-workload.md + bench/guides/01-03), deterministic tiktoken on saved tool-returns (bench/_count_tokens.py; n=1, content-stable; 3 fixed URLs PEP8/json-docs/click-README). **COMPLETENESS GATE is decisive, not raw tokens:**
- **native WebFetch: 16,182 tok, COMPLETE** → the strong CC baseline (confirms the redundancy flag, now MEASURED not hypothesized).
- **Fetch MCP: 2,858 tok but DISQUALIFIED** — `max_length=5000` TRUNCATED 2/3 pages (PEP8 cut before line-length+binary-op section; json params cut mid-list). Cheap because INCOMPLETE = the exact honesty trap the workload warned of. **→ Fetch DEMOTED on CC** (keep load-all-only anchor, where 259-idle buys a digest-fetch those hosts lack).
- **Scrapling broad selector (`#pep-content`): 21,025 tok, complete — LOST to native** (whole-section grab = no targeting benefit, bigger than native's digest).
- **Scrapling TIGHT oracle selectors (`#maximum-line-length,#should-...binary-operator`; dump+dumps dl): 2,599 tok, COMPLETE = ~84% < native.** Ceiling: targeted-extract lever IS real, and tight-Scrapling beats truncated-Fetch while staying complete.
- **CEILING CAVEAT (why delta_pct stays null):** the tight selectors were picked KNOWING where answers live (oracle). A real agent must fetch the page first to discover the selector (≈ one native fetch) → amortized one-shot cost > native. So the 84% is a CEILING, not operational. **CC value of web-research = targeted extract for (a) repeated/known-structure pages, (b) JS-render pages native can't read = a CAPABILITY rung, NOT a general one-shot token saver.** Recorded in sets.json CC token_profile (provenance `measured`, delta_pct null + the reasoning). Artifacts: bench/out/{native,fetch,scrapling,scraplingT}-*.md.

### Phase-3 L3 prior-art (study before building moat — field has refs now)
- **headroom `learn`** (failed-session→CLAUDE.md correction) · **OpenViking** (ByteDance context DB, file-system paradigm, L0/L1/L2 tiered load-on-demand = paw's relevance-tiering idea, BUILT) · **claude-mem** (persistent cross-session memory) · **obsidian** (folder-as-memory). Too heavy as set entries; high learning value.

### Tooling/measurement (not set entries)
- **codeburn** (token-cost TUI, parses session JSONL) = bench-layer ref, richer ccusage. **semble/headroom MCP-def tokenization method** reused from context-quality (§5).

### DROP (off-thesis, confirmed)
zapier (=general installer paw ISN'T, blows N1) · slack/notion/perplexity (SaaS connectors = Smithery territory) · quant-mind (finance domain) · notebooklm-py (niche) · RAG-anything (framework not tool) · gws/worktree family (parallelism convenience, not ↓tok/↑quality — maybe git-productivity S4 later).

### claude-code-harness ID (identity check, user asked)
process/workflow harness class (Plan→Work→Review; affaan-m/ECC = the umbrella user runs). **Different layer from paw** (paw = sets+router+memory, these = workflow-skills). Low overlap, paw niche safe. NOT a set entry.

## 7. Competitive + product decisions 2026-06-08

### jcode (1jehuang/jcode) — overlap check, user worried paw duplicates it
**jcode = a full coding-agent HOST/runtime** (Rust, 6935★, benches RAM/boot/fps AGAINST Claude Code/Codex/OpenCode/Cursor/Copilot). It is a host, NOT an add-on. Features: agent **Memory** (embed each turn→semantic vector graph→cosine retrieval, memory sideagent, auto extract/consolidate, **staleness+conflict check**), Swarm (multi-agent), UI side panels, custom terminal.

**Verdict: NOT a duplicate — different layer.** paw = meta-layer that patches host config (CC/Codex/Gemini/Aider/…); jcode = one more host paw could TARGET. Per-layer overlap:
- **L1 curated sets** (cross-host config patch) → jcode doesn't do it → CLEAN.
- **L2 capability router** (per-prompt, multi-host) → jcode doesn't do it → CLEAN.
- **L3 lesson-memory** → ⚠️ **concept-overlap only.** jcode memory = within-jcode-host, general episodic/semantic turn memory, baked in binary. paw L3 = **cross-host portable + mistake/lesson-specific procedural memory** ("vendors won't build portability — anti-incentive").
- jcode actually **validates paw's L3 thesis**: (1) memory is hot/real, (2) proves a vendor WILL build memory — but **intra-host only** → the portability gap paw bets on stays open.
- **RISK:** paw L3 is redundant IF it drifts into "general agent memory" (jcode wins on a single host). paw L3 survives ONLY on the 2 axes already in NEXT-SESSION.md: **cross-host portability** + **mistake-surfacing** (NOT general conversation memory). jcode makes this line non-negotiable.

### GUI / app-launch idea (user's, 2026-06-08) → Phase-4 CANDIDATE, with guardrails
Idea: `portaw` no-arg → launch an app (native exe OR localhost web ~free-claude-code) so users aren't stuck CLI-only.
**Verdict: good kernel (config/diff UX is a real pain), but off-axis + mistimed if built now/as-pitched.** Reasons:
1. **Off-thesis:** GUI ↓token? no. ↑context-quality? no. It improves human config-UX = a DIFFERENT axis. NEXT-SESSION.md's own "Smithery line" ("useful to user" ≠ "on-thesis") applies to paw itself here.
2. **Violates a REJECTED design decision:** "no daemon, runs-patches-exits, offline-capable" — paw rejected mcpm precisely because daemon. **localhost web app = daemon.** free-claude-code-style web host also = being a host → would CLASH with jcode/Claude Code, breaking "not a host / not a general installer".
3. **no-arg→GUI breaks CLI convention** (no-arg should print help; hurts scriptability/discoverability).
4. **Wrong phase:** L3 (the MOAT) unbuilt. A GUI over the install/config commodity layer = "a prettier Smithery". GUI only pays off once it wraps the MOAT.

**Reshaped form if pursued (Phase 4, after L3):**
- explicit `portaw ui` (NOT no-arg default), **stateless, NO daemon**: pick set → show `token_profile` + config **diff** → apply → **exit** (spawn-use-kill, keeps "runs-patches-exits").
- **Guardrails: no-daemon · no-host (never a persistent agent UI / free-claude-code web host) · explicit-subcommand only.** native TUI/exe safer than web re: daemon.
- Do NOT build before L3.
