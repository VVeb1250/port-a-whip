# Candidate Backlog — harness-quality capabilities

> Status board สำหรับ deep-vet ทีเดียว. ไม่ใช่ commitment — แค่ shortlist ที่ "น่าสนใจ".
> เกณฑ์ผ่านเข้า set = ลด token **หรือ** เพิ่ม context quality (spec §1, §5). vet ตาม §10 gate ก่อนเข้า `sets.json`.
> Type: `MCP` | `non-MCP` (CLI/hook) | `skill` (CC-only, portability ต่ำ) | `paw-built` (feature ของ paw เอง).
> Leverage: H/M/L. นับ MCP เท่านั้นต่อ N1 ceiling (≤2-3 active server/set).
> _last updated: 2026-06-05_

---

## A. External tools (curate เข้า set)

| # | candidate | harness ช่อง | type | lev | ↓tok / ↑qual | overlap / note | set ปลายทาง |
|---|---|---|---|---|---|---|---|
| A1 | **Context7** | Knowledge | MCP | **H** | ↑qual | "most impactful MCP for code quality" — live version docs, ฆ่า hallucination. ไม่ชน codegraph (docs ภายนอก vs โค้ดในเครื่อง) | **set ใหม่ `context-quality`** |
| A2 | **ast-grep** | Tools/Observation (search) | non-MCP | M-H | ↓tok | structural search/rewrite, middle layer (rg=exact ↔ codegraph=semantic). stateless. ชนบางส่วน codegraph "find usages" → ต้อง compat_notes | **+ efficiency-starter** (ฟรีต่อ ceiling) |
| A3 | **Playwright MCP** | Observation (UI) | MCP | M | ↓tok | a11y snapshot แทน screenshot = token ต่ำ. niche web/frontend | **set ใหม่ `frontend-verify`** |
| A4 | **GitHub MCP** | Knowledge (code search) | MCP | M | ↑qual | "search code outperforms context dumping". อาจคู่ Context7 ใน context-quality (ระวัง ceiling 2 MCP) | context-quality? |
| A5 | **Perplexity MCP** | Knowledge (error research) | MCP | L-M | ↑qual | research error/alt approach. overlap Context7 บางส่วน (docs vs web) | TBD |
| A6 | **ripgrep + fd + tokei** (file-search bundle) | Observation (search) | non-MCP | M | ↓tok | netresearch/file-search-skill รวมไว้แล้ว. rg base ของ CC อยู่แล้ว → ค่าเพิ่มน้อยบน CC | low-priority |
| A7 | **mgrep / semantic grep** | Observation (search) | non-MCP/MCP | L | ↓tok | semantic layer — **น่าจะ redundant กับ codegraph** (ทั้งคู่ semantic). vet overlap ก่อน | likely-drop |

## B. paw-built features (differentiator — ไม่ใช่ bundle ของคนอื่น)

| # | feature | harness ช่อง | lev | ทำอะไร | phase |
|---|---|---|---|---|---|
| B1 | `portaw bench <set>` | (eval) | **H** | auto token-delta profiler on/off จาก session log → ป้อน §10 gate, ฆ่า vibes | 2 |
| B2 | **set overlap-linter** | (curation) | M-H | static check 2 tool ใน set trigger_terms ทับกันไหม → N1 overlap-test อัตโนมัติ = curation aid | 1-2 |
| B3 | `portaw budget` | Observation | **H** | โชว์ idle tool-def token cost ต่อ host ของ set ที่ลง (honest §10 number — ทำ cost ที่มองไม่เห็นให้เห็น) | 2 |
| B4 | `portaw router test "<prompt>"` | (router) | M | dry-run: router จะแนะอะไร → tune threshold, debug "เงียบเมื่อไม่มั่นใจ" | 1-2 |
| B5 | `portaw perms` allowlist manager | **Permissions** | M-H | gen/audit allow-list (`mcp__<tool>__*`) ต่อ set — ช่อง Permissions ที่ไม่มีใครครอบ | 1-2 |
| B6 | **doctor** health/drift/permission | Observation/Permissions | M | codegraph-link pattern: health-gate (`status -j`), drift (`--print-config` vs live), allow-list check | 1 (speced) |
| B7 | lesson relevance injector | Knowledge (L3) | **H** | core ของ L3 — relevance inject แทน always-on (−73% tokens) | 3 |
| B8 | confidence-decay on recurrence | Knowledge (L3) | M | แก้ staleness ("confidently wrong"): mistake ไม่ recur N session → decay; recur → bump (xN counter substrate) | 3 |
| B9 | router-driven JIT install | Action/Tools | H (ambitious) | ลง tool เมื่อ route เจอ → ตัด idle overhead จริง (architectural option ใหม่ ไม่ฟรีจาก eager-install) | 4? |
| B10 | sandbox / network-allowlist enabler | **Permissions** | M-H | recommend/enable Bubblewrap (Linux) / Seatbelt (macOS) — **off by default** ใน CC — + egress `network=none`+allowlist ต่อ set. ป้องกัน supply-chain (Shai-Hulud npm 2025 จง AI agent) | 2-4 |
| B11 | set lockfile + `portaw update` | (safety) | M | pin version + lockfile (Q2) — latest break เงียบ = ขัด vision | 1-2 |
| B12 | config backup/restore | (safety) | S | `portaw config backup/restore` — มี backup-before-write แล้ว, เพิ่ม restore command | 1-2 |

---

## harness coverage หลังเติม backlog

| ช่อง | ปัจจุบัน (codegraph+rtk) | candidate เติม |
|---|---|---|
| Tools | rtk | A2 ast-grep |
| Knowledge | codegraph | **A1 Context7** (H), A4 GitHub, B7 lesson |
| Observation | codegraph (static) | A3 Playwright, B3 budget, B6 doctor |
| Action | rtk | A2, B9 JIT |
| **Permissions** | **ว่าง** | **B5 perms, B10 sandbox** ← ช่องที่ paw differentiate ได้ |

## top picks ตอน deep-vet (เรียง leverage)
1. **A1 Context7** — set ใหม่, ↑quality สูงสุด, anti-hallucination
2. **A2 ast-grep** — +efficiency-starter, overlap-test กับ codegraph = curation จริงตัวอย่าง
3. **B5/B10 Permissions** — ช่องว่างที่ไม่มีคู่แข่งครอบ = differentiator
4. **B1/B3 bench/budget** — ทำให้ §10 "no vibes" รันได้จริง

---

## C. Sub-agent scout results (2026-06-05, 5 parallel agents — verified URLs)

> เก็บเฉพาะตัว verified + maturity บอกตรง. HIGH-overlap / stale / <3★ ตัดออกหรือ flag. deep-vet §10 ก่อนเข้า set.

### C-Observation (สิ่งที่ agent เห็น runtime)
| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **difftastic** ⭐ | non-MCP CLI | syntax-aware diff (tree-sitter), `GIT_EXTERNAL_DIFF` drop-in | ↑qual+↓tok ซ่อน reformat noise | **25.4k★** Y | low (semantic-diff ≠ ast-grep/codegraph) | github.com/Wilfred/difftastic |
| **Sentry MCP** | MCP | ดึง issue/stack-trace + Seer root-cause | ↑qual อ่าน trace จริงแทนเดา | 714★ Y official | low | github.com/getsentry/sentry-mcp |
| build-output-tools-mcp | MCP | รัน build/test → summarize ผ่าน small LLM | ↓tok 85% (3017→458 tok) | solo low★ Y | low | github.com/jgordley/build-output-tools-mcp |
| mcp-test-runner | MCP | runner รวม (pytest/jest/go/rust…) → parsed pass/fail | ↑qual structured ไม่ scroll stdout | 16★ Y | low | github.com/privsim/mcp-test-runner |
| coverctl | MCP+CLI | coverage gap ranked, in-session | ↑qual self-remediate | new 0★ Y | low (ช่อง coverage ว่าง) | github.com/felixgeelhaar/coverctl |
| diffchunk | MCP | chunk/nav diff ใหญ่ jump เฉพาะ hunk | ↓tok diff เกิน context | 8★ Y | low | github.com/peteretelej/diffchunk |
| Tach `tach test` | non-MCP CLI | changed files → dep graph → affected pytest only | ↓tok | est. Y | **HIGH = codegraph-affected skill** | github.com/gauge-sh/tach |

### C-Action (วิธี agent ลงมือ token-lean)
| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **Serena** ⭐ | MCP | LSP symbol-level retrieve+edit ("replace symbol body") 30+ lang | ↓tok edit symbol ไม่ rewrite ทั้งไฟล์ | **24.9k★** Y | low (edit-side complement codegraph read-side) | github.com/oraios/serena |
| **Morph Fast Apply** | MCP | lazy-edit marker → fast model merge 10.5k tok/s | ↓tok 40-60% vs full rewrite | hosted Y (paid key) | low | morphllm.com/mcp |
| codemod.com | MCP+CLI | codemod engine + YAML workflow + registry | ↑qual deterministic multi-file; ↓tok | 1.0k★ Y | JSSG=ast-grep based แต่ workflow/registry distinct | github.com/codemod-com/codemod |
| OpenRewrite | non-MCP CLI | lossless-semantic-tree mass refactor, 5000+ recipe | ↑qual compiler-accurate; ↓tok 1 recipe | 3.5k★ Y | low (CLI, no tool-def) | github.com/openrewrite/rewrite |
| Desktop Commander | MCP | terminal ctrl + process + `edit_block` surgical | ↓tok targeted replace <20% file | 6.1k★ Y | edit overlaps Serena; exec=differentiator | github.com/wonderwhy-er/DesktopCommanderMCP |
| mcp-shell (sonirico) | MCP | secure exec allowlist-only, no shell-interp, audit | ↑qual block injection, bounded output | 81★ Y | low | github.com/sonirico/mcp-shell |
| Filesystem MCP (official) | MCP | line-edit + **dry-run diff preview**, multi-read | ↓tok selective edit + dry-run safety | ref Y | edit overlaps; value=official lean | github.com/modelcontextprotocol/servers (src/filesystem) |
| _dropped:_ Comby (stale 2022), OHM-MCP (2★), persistent-shell (1★) | | | | | | |

### C-Permissions/Security (ช่องที่ codegraph+rtk ว่างสนิท = differentiator)
| candidate | type | what | why | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **nah** ⭐ | hook PreToolUse | action-aware permission guard, deterministic classifier; project override **tighten-only** | ↑safety แยก `rm dist/` vs `rm ~/.bashrc`; supply-chain-safe config; no LLM ms-latency | 449★ MIT Y | low (net-new = B5) | github.com/manuelschipper/nah |
| **microsandbox** ⭐ | service/MCP | libkrun microVM local sandbox, <200ms, MCP built-in | ↑safety hardware isolation, offline, CC/Codex/Gemini support | ~5k★ Apache Y | MED (แกร่งกว่า Bubblewrap plan = B10) | github.com/microsandbox/microsandbox |
| **Snyk Agent Scan** (ex mcp-scan) | non-MCP CLI | scan installed MCP/skill หา tool-poisoning/rug-pull/injection + proxy constrain | ↑safety threat class ใหม่ (untrusted MCP tool) paw ยังไม่กัน | 2.5k★ Apache Y | low | github.com/snyk/agent-scan |
| **Socket** | service/CLI | behavioral supply-chain scan npm/pip/cargo malware ตอน install | ↑safety กัน agent รัน `npm i` โดน Shai-Hulud-class | high adoption Y | low (net-new) | socket.dev |
| TruffleHog | CLI/hook | secret scan + live verify 800+ type | ↑safety pre-commit/push agent ไม่ commit key | 18k★ Y | low | github.com/trufflesecurity/trufflehog |
| landrun | non-MCP CLI | wrap process ใน Landlock sandbox (no root/container) | ↑safety lightest local primitive | 2.2k★ MIT Y | HIGH (Landlock cluster = B10) | github.com/Zouuup/landrun |
| pipelock | service proxy | AI-agent firewall: egress/DLP/SSRF/injection, allowlist-only | ↑safety fail-closed no-exfil | 690★ Y | MED (elaborate egress plan) | github.com/luckyPipewrench/pipelock |

### C-Knowledge/Memory
| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **mcp2cli** ⭐⭐ | non-MCP CLI | MCP/OpenAPI/GraphQL → runtime CLI, tool discover on-demand | ↓tok **"96-99% schema token saved/turn"** — โจมตี MCP ceiling ตรงๆ | 2.2k★ MIT Y | low (= แก้ N1 ตรงราก) | github.com/knowsuchagency/mcp2cli |
| **mcpdoc** (langchain) | MCP | feed llms.txt docs ผ่าน `fetch_docs` (bring-your-own, auditable) | ↓tok+↑qual เฉพาะ URL อนุมัติ ไม่ใช่ opaque RAG | 998★ Y | low vs Context7 (BYO ≠ registry) | github.com/langchain-ai/mcpdoc |
| **Graphiti** (getzep) | MCP | temporal KG memory, fact มี validity window + provenance | ↑qual "what was true when" | **27k★** Y | low vs paw lesson (temporal angle to port) | github.com/getzep/graphiti |
| AWS OpenAPI MCP | MCP | OpenAPI spec → MCP tool concise desc | ↓tok "70-75% reduction" | awslabs Y | low vs Context7 | awslabs.github.io/mcp (openapi-mcp-server) |
| codemap (JordanCoin) | non-MCP CLI | project-brain compact arch stubs, byte budget | ↓tok stub vs full source | 583★ Y | MED vs codegraph (stub vs graph, complement) | github.com/JordanCoin/codemap |
| agent-file (.af) | format/skill | serialize/version/share stateful agent memory | ↑qual cross-host checkpoint (เข้า paw portability) | letta-ai Y | low (format paw adopt ได้) | github.com/letta-ai/agent-file |
| OpenMemory/mem0, Letta, agentmemory | MCP | persistent fact/self-edit/benchmarked memory | ↑qual | 53k/13-21k/5.9k★ Y | MED vs paw lesson (learn-from, port local-first store) | github.com/mem0ai/mem0 |

### C-rtk-class (non-MCP token-killer — paw's UNIQUE category; peers/rivals ของ rtk เอง)
| candidate | type | what | save | maturity | host | URL |
|---|---|---|---|---|---|---|
| **context-mode** ⭐ | hook+CLI | route blob ใหญ่ออก context, คืน ref เล็ก | **98% session** (315KB→5.4KB) | **16.4k★** Y | CC/Gemini/Codex/Cursor/+15 | github.com/mksglu/context-mode |
| **snip** ⭐ | CLI-proxy+hook | Go rtk-alt, declarative YAML filter (no recompile) | 60-90% (cargo test 99.2%) | 289★ Y | CC/Cursor/Copilot/Gemini/Codex/Aider/+ | github.com/edouard-claude/snip |
| **ecotokens** | hook Pre+Post | zero-config shell+native compressor + USD TUI | **93.8% over 19.9k runs** (hard telemetry) | 15★ Y Rust | CC/Gemini/Qwen/Codex/+ | github.com/hansipie/ecotokens |
| lean-ctx | CLI/hook(+MCP) | context-OS binary: cache read, compress shell, route | up to 99% (cached re-read 13 tok vs 2000) | 2.4k★ Y | CC/Cursor/Copilot/Codex/Gemini/+ | github.com/yvgude/lean-ctx |
| chop | hook PreToolUse | compress 52+ command output inline | 50-90% (git status 95%) | 31★ Y | CC/Codex/Gemini | github.com/AgusRdz/chop |
| token-reducer | CLI/hook plugin | local hybrid-RAG retrieve only relevant code | 90-98% | 26★ Y | CC | github.com/Madhan230205/token-reducer |
| delegated-code-writer | skill | offload bulk code → Haiku, Claude review | $ play (Haiku 5-10× cheaper) | anthropic/skills Y | CC | github.com/anthropics/skills |

---

## STRATEGIC FLAGS (จาก scout)

1. **mcp2cli = strategic** — "96-99% schema token saved" แก้ MCP ceiling (N1) ที่ราก. อาจเปลี่ยน paw delivery: แทน install MCP ตรง → wrap เป็น CLI. ทับแนวคิด code-exec delivery (D2/`delivery` field) → vet คู่กัน
2. **rtk มี peer เยอะ + ดาวสูงกว่า** (context-mode 16.4k★, lean-ctx 2.4k★, snip 289★) — efficiency-starter ใช้ rtk เป็น anchor; ต้อง **benchmark rtk vs พวกนี้** (B1) ก่อน lock. อาจสลับ anchor หรือ positioning rtk ใหม่. = curation judgement สำคัญ
3. **Permissions ช่องเติมได้จริง** — nah (449★ hook) + microsandbox + Snyk-scan + Socket = stack ครบ (permission guard / sandbox / MCP-audit / dep-defense). ยืนยัน B5/B10 ทำได้ ไม่ใช่แค่ไอเดีย
4. **threat class ใหม่ paw ยังไม่กัน:** MCP tool-poisoning (Snyk/Cisco/Pangea scan) + dep supply-chain (Socket). spec §12 ครอบแค่ community-set hash-verify → ขยาย
5. **memory to port ไม่ rebuild:** Graphiti (temporal) + agent-file (.af portable format) + mem0 local-first = learn-from สำหรับ L3 Phase 3 (อย่า reinvent)
6. **overlap ต้อง drop:** Tach (= codegraph-affected), landrun cluster (เลือก 1-2), Comby (stale)

---

## D. Sub-agent scout wave 2 (2026-06-05, 6 agents — domain sets + instruction type + workflow + self-obs)

> ช่องบาง/ยังไม่แตะ. domain set = แนวทาง "recommended sets" (spec §13). **anchor ที่ token-lean per set เน้น bold.**

### D-DevOps/Infra set
| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **k8sgpt** ⭐ | CLI(+MCP) | SRE-analyzer triage cluster → problem+fix focused | ↓tok diagnosis ไม่ dump cluster; JSON+anonymize | **7.8k★** CNCF Y | low | github.com/k8sgpt-ai/k8sgpt |
| **Infracost** ⭐ | CLI(+agent-skills) | cloud cost breakdown จาก TF/CDK ก่อน deploy | ↑qual $/resource structured; official CC skill | **12.3k★** Y | low (FinOps unique) | github.com/infracost/infracost |
| grafana/mcp-grafana | MCP | query Loki/Prometheus + dashboard/incident | ↑qual structured LogQL/PromQL | 3.1k★ Y | low | github.com/grafana/mcp-grafana |
| containers/kubernetes-mcp-server | MCP | native Go K8s API (ไม่ใช่ kubectl wrapper) | ↑qual typed resource state | 1.2k★ Y | low (เลือก 1 k8s server) | github.com/containers/kubernetes-mcp-server |
| hashicorp/terraform-mcp-server | MCP | official TF registry + HCP workspace | ↑qual real schema | official Y | MED (docs ทับ Context7; ใช้แค่ workspace ops) | github.com/hashicorp/terraform-mcp-server |
| homeport/dyff + helm-diff | CLI | semantic YAML diff / helm upgrade delta | ↓tok เฉพาะที่เปลี่ยน | 1.7k/2.7k★ Y | low | github.com/homeport/dyff |
| kubeconform + kube-linter | CLI | manifest schema-validate / best-practice lint | ↑qual JSON pass/fail offline | 3.1k/3k★ Y | low | github.com/yannh/kubeconform |
| _flag:_ zereight/gitlab-mcp | MCP | GitLab CI control | ⚠️ **100+ tool-def = blow budget** read-only subset เท่านั้น | 1.4k★ | HIGH | github.com/zereight/gitlab-mcp |

### D-Data/DB/Analytics set
| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **bytebase/dbhub** ⭐ | MCP | 2-tool gateway PG/MySQL/SQLite/MSSQL, read-only | ↓tok "token-efficient" 2 tool แทน 4 server; guardrail | 2.9k★ Y | subsume single-DB | github.com/bytebase/dbhub |
| crystaldba/postgres-mcp | MCP | PG perf + index tuning (EXPLAIN/hypopg) | ↑qual structured analysis | 2.85k★ Y | pair dbhub (PG tuning) | github.com/crystaldba/postgres-mcp |
| **xo/usql** | CLI | universal SQL client (psql-like, dozens driver) | ↓tok `-c --csv/json` compact, 0 tool-def | **10k★** Y | low (CLI) | github.com/xo/usql |
| motherduck-mcp | MCP | DuckDB/MotherDuck OLAP, capped 1024 row/50k char | ↓tok bounded payload | 487★ Y official | low | github.com/motherduckdb/mcp-server-motherduck |
| qdrant-mcp | MCP | vector store/find 2-tool | ↓tok minimal def, ranked hits | 1.4k★ Y | MED (overlap mem0 ถ้าใช้เป็น memory) | github.com/qdrant/mcp-server-qdrant |
| ariga/atlas | CLI | declarative schema migration (TF-for-DB) | ↑qual compact HCL/SQL diff + lint destructive | 8.5k★ Y | low | github.com/ariga/atlas |
| sqlite-utils / jupyter-mcp | CLI/MCP | CSV/JSON in-mem query / live kernel | ↓tok result rows / ↑qual cell output | 2.1k/1.1k★ Y | jupyter partial vs NotebookEdit | github.com/simonw/sqlite-utils |

### D-Frontend/Design/Mobile set
| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **Figma Dev Mode MCP** ⭐ | MCP | official: variables/components/Code-Connect → agent | ↑qual real spec แทนตี screenshot | official (paid seat) Y | low | figma.com/blog/introducing-figma-mcp-server |
| **shadcn MCP** ⭐ | MCP | official CLI: search/install registry component | ↑qual live contract "no hallucinated props" | official Y | low | ui.shadcn.com/docs/registry/mcp |
| Chrome DevTools MCP | MCP | console/network/perf/a11y ของ live page (≠Playwright) | ↓tok telemetry ไม่ใช้ screenshot | **43k★** Y | MED (browser ทับ Playwright; niche distinct) | github.com/ChromeDevTools/chrome-devtools-mcp |
| mobile-mcp | MCP | cross-platform mobile (iOS/Android/RN/Flutter) a11y-tree | ↓tok a11y tree, screenshot fallback | 5.1k★ Y | low (1 server ครบ mobile) | github.com/mobile-next/mobile-mcp |
| a11y-mcp | MCP | axe-core WCAG audit → JSON | ↓tok+↑qual structured violation | 45★ Y | low | github.com/priyankark/a11y-mcp |
| designlang + Style Dictionary | MCP+CLI | extract W3C DTCG tokens / transform pipeline | ↑qual standard token | new/industry Y | low | styledictionary.com |
| _alt:_ 21st Magic, ios-sim, mcp_flutter | MCP | UI-gen / iOS / Flutter เฉพาะทาง | — | 5k★/np m/Y | overlap shadcn/mobile-mcp | github.com/21st-dev/magic-mcp |

### D-Instruction type (เดิมว่าง 0 → เติมแล้ว)
| candidate | kind | what | ↓tok/↑qual | maturity | portability | URL |
|---|---|---|---|---|---|---|
| **openai/agents.md** ⭐ | standard | AGENTS.md open format (Linux Foundation) | ↓tok+↑qual 1 ไฟล์แทน per-tool rule | **22k★** Y | any (Codex/Cursor/Gemini/Aider) | github.com/openai/agents.md |
| **dyoshikawa/rulesync** ⭐ | generator | author once → 20+ agent rule file (CC/Cursor/Gemini/…) | ↓tok ไม่ dup per-tool, consistent | 1.1k★ Y (push วันนี้) | any (20+ target) | github.com/dyoshikawa/rulesync |
| PatrickJS/awesome-cursorrules | content | per-stack `.cursorrules` ใหญ่สุด | ↑qual stack convention | **39.9k★** Y | any (plain MD) | github.com/PatrickJS/awesome-cursorrules |
| hesreallyhim/awesome-claude-code | content | vetted CLAUDE.md/cmd/hook | ↑qual real pattern | **45.7k★** Y | CC-first MD | github.com/hesreallyhim/awesome-claude-code |
| AnswerDotAI/llms-txt | standard | /llms.txt spec + tooling | ↓tok curated MD map ไม่ crawl HTML | 2.4k★ Y | any | github.com/AnswerDotAI/llms-txt |
| steipete/agent-rules | content | cross-agent rule/knowledge | ↑qual battle-tested | 5.7k★ Y | CC+Cursor | github.com/steipete/agent-rules |
| _caveat:_ auto-gen (/init, llmstxt-gen) | generator | scan repo → CLAUDE.md | ⚠️ ETH study: naive auto-file **−3% success/+20% cost** → ต้อง hand-edit | official Y | CC | claude.com/blog/using-claude-md-files |

### D-Workflow/Orchestration set
| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **claude-task-master** ⭐ | MCP+CLI | PRD→tasks.json dep/complexity; next-task | ↓tok **core mode 7 tool (−76% def)**; state on disk | **27k★** Y | HIGH (เลือก 1 task tool) | github.com/eyaltoledano/claude-task-master |
| **Backlog.md** ⭐ | MCP+CLI | git-md task board, state OUT of context | ↓tok+↑qual fuzzy pull เฉพาะ relevant; CLI=0 def | 5.7k★ Y | HIGH | github.com/MrLesk/Backlog.md |
| **GitHub Spec Kit** | CLI | spec-driven: constitution→specify→plan→tasks | ↑qual spec artifact on disk, 0 def, multi-agent | **108k★** Y | low (planning) | github.com/github/spec-kit |
| BMAD-METHOD | CLI/agents | agile agents → PRD+arch docs | ↑qual durable docs | 48k★ Y | MED vs spec-kit | github.com/bmad-code-org/BMAD-METHOD |
| Clear Thought 1.5 | MCP | 1 tool = 38 reasoning ops | ↑qual + def-lean (1 def) | active Y | MED vs sequential-thinking | github.com/waldzellai/clearthought-onepointfive |
| Linear / Atlassian MCP | MCP | issue tracker (state out of context) | ↑qual; **exclusive เลือกตาม tracker** | official Y | many def | mcp.linear.app/mcp |
| CodeRabbit CLI + git-cliff | CLI | PR-review `--agent` JSON / changelog gen | ↓tok feed finding ไม่โหลด diff; 0 def | official/11.9k★ Y | low | coderabbit.ai/cli |
| _flag:_ Sequential Thinking (official) | MCP | reasoning scratchpad | ⚠️ **ADD tokens** (↑qual only ไม่ ↓tok) | 86k★ Y | — | modelcontextprotocol/servers (sequentialthinking) |

### D-Self-observability/cost/eval (= สร้าง paw B1/B3/§10 โดยตรง — wrap ไม่ rebuild)
| candidate | type | what | paw need | maturity | offline | URL |
|---|---|---|---|---|---|---|
| **ccusage** ⭐ | CLI | parse `~/.claude` JSONL → token/cost report multi-agent | **B1 bench** (diff 2 run) | **15.6k★** Y | yes `--offline` | github.com/ryoppippi/ccusage |
| **agentevals** ⭐ | lib | trajectory evaluator: strict/subset match + traj LLM-judge | **§10 eval gate** (deterministic, no LLM) | 609★ Y | yes (match mode) | github.com/langchain-ai/agentevals |
| **CC native OTel** | built-in | `CLAUDE_CODE_ENABLE_TELEMETRY=1` → OTLP GenAI semconv | **B3 budget** (first-party) | first-party Y | yes (self-host sink) | code.claude.com/docs/en/monitoring-usage |
| promptfoo | CLI/lib | declarative eval + LLM-judge + CI gate (OpenAI-owned MIT) | eval-gate/bench | ~80k-class Y | yes (local provider) | github.com/promptfoo/promptfoo |
| DeepEval | lib pytest | 50+ metric incl G-Eval judge, pytest CI | eval-gate | 14k★ Y | yes (local metric) | github.com/confident-ai/deepeval |
| cccost | CLI/lib | actual token incl resumed session → .usage.json | B1 bench (precise) | 20★ Y | yes | github.com/badlogic/cccost |
| Langfuse | service/lib | self-host LLM obs + eval + dataset (OTLP) | trajectory/eval | **19k★** Y | yes (docker) | github.com/langfuse/langfuse |
| claude-trace / CC-Usage-Monitor | CLI/TUI | trace viewer / live burn-rate warn | trajectory / B3 live | active/6.1k★ Y | yes | github.com/mariozechner/claude-trace |

---

## STRATEGIC FLAGS — wave 2

7. **Self-obs scout = paw build kit.** B1/B3/§10 ไม่ต้องเขียนเอง: **wrap ccusage (bench) + agentevals (eval-gate deterministic offline) + CC OTel (budget)**. ตรงกับ ethos "reuse ไม่ rebuild". = unblock §10 ทันที
8. **Instruction type (เคยว่าง) → anchor ชัด:** `agents.md` (normalize target) + `rulesync` (author-once→20+ host). **rulesync ตรงกับ paw cross-host vision เป๊ะ** — อาจเป็น core dependency ไม่ใช่แค่ candidate
9. **curation preference เกิดใหม่:** ของที่ **subsume many-tools-in-few-defs** = N1-friendly สุด → dbhub (2 tool/4 DB), task-master (core 7 tool), Clear-Thought (1 def/38 op). **ตั้งเป็นเกณฑ์ priority:** server ที่ lazy-load/consolidate def > server ที่กาง tool หมด
10. **domain set viable ครบ** — แต่ละ domain มี token-lean anchor: devops=k8sgpt, data=dbhub, frontend=Figma+shadcn, mobile=mobile-mcp, workflow=Backlog.md/spec-kit. → "recommended sets" (§13) มีของจริงเขียนได้
11. **CLI > MCP บน load-all host** ย้ำอีก: หลาย anchor เป็น CLI (usql, Infracost, spec-kit, git-cliff, atlas, ccusage) = 0 tool-def = ปลอดภัยต่อ ceiling. curation ควรเอียงไป CLI เมื่อเลือกได้
12. **exclusive pairs:** Linear⊕Atlassian (เลือกตาม tracker), Qdrant⊕Chroma, k8s server เลือก 1. drop stale: Shrimp (Aug'25), llmstxt-generator (2025)

---

## E. Wave 3 — scout results (2026-06-05, 6 parallel agents, 1 crashed)

> แต่ละ sub-section = 1 scout agent result. N1-aware: นับ tool-def ต่อ MCP server, prefer ≤5 tools.
> _last updated: 2026-06-05_

---

### E1: Language-Specific Tooling ✅

#### E1-Cross-language (LSP bridges — force-multiplier)

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **mcpls** ⭐ | MCP | Universal LSP→MCP bridge. Rust, async, auto-detect project type → spawns pyright/rust-analyzer/tsserver/gopls/clangd. Zero runtime deps | ↑qual all langs | 39★ v0.3.6 Apr 2026, 127 commits | complements codegraph (LSP=live diagnostics vs graph=static index) | github.com/bug-ops/mcpls |
| **Nreki** ⭐ | MCP | Validate AI edits in RAM via TS/gopls/pyright before disk write. Batch rollback. "patch mode" cuts output 30× | ↓tok 50%+ claim | 11★ May 2026, 424 commits, **1,418 tests** | low (pre-write validation = net-new layer) | github.com/Ruso-0/Nreki |
| mcp-lsp-bridge | MCP (Go) | 16 MCP tools across 20+ languages, config-based LSP selection | ↑qual | 29★ Aug 2025 (may be stale) | vs mcpls (Rust vs Go; mcpls more active) | github.com/rockerBOO/mcp-lsp-bridge |
| lsp-mcp-server | MCP (TS) | 29 MCP tools across 10 languages | ↑qual | 17★ no releases yet, 46 commits | vs mcpls | github.com/ProfessioneIT/lsp-mcp-server |
| Language-Server-MCP-Bridge | MCP+VS Code ext | VS Code extension bridge, 10 tools | ↑qual | 29★ Sep 2025 | VS Code-only | github.com/sehejjain/Language-Server-MCP-Bridge |
| **cocoindex-code** | MCP+CLI | AST-based code chunking (30+ lang), 70% token savings claim, MCP native | ↓tok 70% | **1.8k★** Jun 2026, Rust+Python | overlap codegraph (both AST-aware; cocoindex=chunking, codegraph=graph) | github.com/cocoindex-io/cocoindex-code |
| **probe** | CLI+MCP | ripgrep speed + tree-sitter AST semantic search, Rust | ↓tok | 628★ v0.6.0-rc324 Jun 2026 | overlap ast-grep (probe=search-first, ast-grep=rewrite-heavy) | github.com/probelabs/probe |
| jcodemunch-mcp | MCP | Token-efficient GitHub source exploration via tree-sitter | ↓tok | **1.9k★** May 2026 | **HIGH overlap codegraph** (both source exploration) | github.com/jgravelle/jcodemunch-mcp |

#### E1-Python

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **ruff** | CLI (no MCP yet) | Linter+formatter, 10-100× Flake8 speed. JSON output `--output-format json` | ↓tok (fast, single pass) | **47.8k★** Jun 2026 | **no MCP wrapper exists** — thin MCP build opportunity | github.com/astral-sh/ruff |
| **basedpyright** | CLI/LSP | Pyright fork + pylance features + stricter type inference | ↑qual | 3.4k★ May 2026 | via mcpls bridge | github.com/DetachHead/basedpyright |
| pyright | CLI/LSP | Static type checker, fast, large codebase | ↑qual | 15.5k★ May 2026 | via mcpls bridge | github.com/microsoft/pyright |
| **pytest-testmon** | CLI/pytest plugin | Incremental test runner — runs only tests affected by changed code (`.testmondata` dep DB) | ↓tok (fewer test runs) | 984★ Dec 2025 | low (complement pytest, no overlap with listed tools) | github.com/tarpas/pytest-testmon |
| code-quality-mcp | MCP | Wraps flake8+mypy+McCabe+vulture | ↑qual | 1★ ~May 2026 | too small, concept right | github.com/Javier-Morenosa/code-quality-mcp |

**Python gap:** No mature ruff MCP or mypy MCP exists. mcpls bridges pyright/basedpyright. ruff JSON output = thin MCP wrapper opportunity.

#### E1-TypeScript/JavaScript

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **oxc** ⭐ | CLI | oxlint + oxfmt + parser (all Rust). 50-100× faster than ESLint. JSON output | ↓tok (ultra-fast) | **21.4k★** Jun 2026, VoidZero | **no MCP yet** — thin MCP build opportunity. Used by Shopify/ByteDance/Preact | github.com/oxc-project/oxc |
| **biome** | CLI/LSP | Formatter+linter, Prettier/ESLint replacement. **Has `.claude/` dir + `CLAUDE.md`** (agent-aware). JSON via `--reporter=json` | ↓tok (fast, unified) | **24.9k★** May 2026 | **no MCP yet** — thin MCP build opportunity | github.com/biomejs/biome |
| **vscode-mcp** | MCP+VS Code ext | Bridges VSCode LSP diagnostics/symbols/references → MCP. Real-time, replaces slow tsc/eslint CLI | ↓tok+↑qual | 83★ Jun 2026, 224 commits | low (VS Code specific but powerful bridge) | github.com/tjx666/vscode-mcp |
| eslint-typescript-mcp | MCP | ESLint+TypeScript for Claude Code | ↑qual | 0★ Apr 2026, 10 commits | too small | github.com/w334-jpg/eslint-typescript-mcp |
| jons-mcp-typescript | MCP | vtsls+Prettier+ESLint behind MCP | ↑qual | 0★ Jun 2026 | too small | github.com/jonmmease/jons-mcp-typescript |

**TS/JS gap:** No mature biome/oxc MCP. Both have JSON output — thin MCP wrapper is trivial. vscode-mcp is strongest bridge today.

#### E1-Rust

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **cargo-nextest** | CLI | Structured test runner, JUnit XML, JSON schemas. **Has `.claude/` dir** (agent-aware). `nextest-metadata` crate for programmatic use | ↓tok (faster, structured) | **3k★** May 2026 | low (test runner, complement not overlap) | github.com/nextest-rs/nextest |
| rust-analyzer | LSP | Official Rust LSP — diagnostics, completions, goto-def | ↑qual | 16.5k★ Jun 2026 | via mcpls bridge | github.com/rust-lang/rust-analyzer |
| rust-mcp-server | MCP | clippy+rustfmt+cargo check+test | ↑qual | 1★ ~May 2025, 2 commits | too small | github.com/lh/rust-mcp-server |
| rusty-tools | MCP | clippy+cargo fmt/check/fix+rustc explain | ↑qual | 1★ Sep 2025 | too small | github.com/8agana/rusty-tools |
| rust-docsbox-mcp | MCP | clippy+rustfmt+crates.io+rustc explain+playground | ↑qual | 0★ Apr 2025, stale | too small+stale | github.com/afterrealism/rust-docsbox-mcp |

**Rust gap:** No mature clippy MCP. `cargo clippy --message-format=json` ready to wrap. mcpls bridges rust-analyzer.

#### E1-Go (strongest ecosystem of language-specific MCPs)

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **mcp-gopls** (hloiseau) ⭐ | MCP | gopls LSP exposed as MCP: analysis, tests, coverage, docs | ↑qual+↓tok | 87★ Jan 2026, Apache 2.0, 23 commits | low | github.com/hloiseau/mcp-gopls |
| **gopls-mcp** (xieyuschen) ⭐ | MCP | Fork of gopls itself → reborn as MCP. "compiler's brain, not text searcher" | ↑qual (deepest) | 56★ May 2026, **10.5k commits** inherited | low (deeper than wrapper — fork of gopls source) | github.com/xieyuschen/gopls-mcp |
| mcp-gopls (Yantrio) | MCP | gopls wrapper for Claude Code | ↑qual | 45★ | vs hloiseau (less mature) | github.com/Yantrio/mcp-gopls |
| golangci-lint-mcp | MCP | golangci-lint with **629 fix guides** | ↑qual | 1★ ~May 2026 | too small, concept novel | github.com/wavilen/golangci-lint-mcp |
| mcp-server-go-quality | MCP | golangci-lint+govulncheck+nilaway, parallel, unified `Diagnostic[]` output | ↑qual | 0★ Jun 2026 | too small, architecture solid | github.com/afshinator/mcp-server-go-quality |

**Go verdict:** Strongest language-specific MCP ecosystem. hloiseau/mcp-gopls (87★) + xieyuschen/gopls-mcp (56★) both viable. golangci-lint bridges early but architecturally sound.

#### E1-Java/Kotlin (near desert)

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| code-inspector-mcp | MCP | Detekt+Ktlint+Android Lint, parallel, quality score, auto-detect | ↑qual | 0★ Mar 2026 | only Kotlin MCP, too small | github.com/kangraemin/code-inspector-mcp |
| jdtls | LSP | Eclipse JDT Language Server (Java) | ↑qual | — | via mcpls only — **no dedicated Java MCP** | — |

**Java/Kotlin gap:** Near empty. Only path = mcpls bridging jdtls.

#### E1 Key Gaps (build opportunities)

| Gap | Why buildable | Effort |
|---|---|---|
| **ruff MCP** | ruff has `--output-format json` already | Low (~30 LOC) |
| **clippy MCP** | `cargo clippy --message-format=json` ready | Low (~30 LOC) |
| **biome MCP** | `--reporter=json` + agent-aware project (has `.claude/`) | Low (~30 LOC) |
| **oxc MCP** | oxlint JSON output exists | Low (~30 LOC) |
| All LSP bridges <50★ | mcpls is best (39★, 127 commits) — category pre-adoption, paw could bundle as set entry | — |

---

### E2: Web Research / Search / Scrape ✅

> N1 ceiling critical: each MCP tool-def ~200-500 tokens. Ranked by tool-def burden.

| rank | candidate | tools | type | ↓tok/↑qual | maturity | free? | N1 fit | URL |
|---|---|---|---|---|---|---|---|---|
| 1 | **SerpAPI MCP** | 1 | web search | ↓tok (single tool, multi-engine: Google/Bing/Yahoo/DDG/YouTube) | 141★ | paid | **Leanest** | github.com/serpapi/serpapi-mcp |
| 1 | **Fetch MCP** (official) | 1 | scraping | ↓tok (HTML→markdown, `max_length`, free) | 86.8k★ monorepo | yes | **Leanest** | github.com/modelcontextprotocol/servers (src/fetch) |
| 3 | **SearXNG MCP** ⭐ | 2 | search+fetch | ↓tok (metasearch, privacy, self-host = no API key) | 856★ | yes (self-host) | **Best free** | github.com/ihor-sokoliuk/mcp-searxng |
| 4 | **Exa MCP** | 3 (+8 deprecated, can disable) | search+fetch | ↓tok (neural search, clean, deprecated tools quarantined) | — | paid | Lean | github.com/exa-labs/exa-mcp-server |
| 5 | **Jina Reader MCP** | ~1-2 | scraping | ↓tok (thin wrapper, `fetch_url_as_markdown`) | 47★ | yes (free tier) | Lean | github.com/wong2/mcp-jina-reader |
| 6 | **Tavily MCP** | 4 | search+extract+map+crawl | ↓tok (well-scoped) | — | paid | Lean-borderline | github.com/tavily-ai/tavily-mcp |
| 7 | **GPT Researcher MCP** | 4-5 | deep research | ↓tok+↑qual (multi-source research agent) | 349★ | configurable | Lean-borderline | github.com/assafelovic/gptr-mcp |
| 8 | Brave Search MCP | 8 | search+local+video+news+summarize+LLM-context | ↓tok (LLM-context tool unique) | 1.1k★ | yes (free tier) | Medium-heavy | github.com/brave/brave-search-mcp-server |
| 9 | Browserbase MCP | 6 | cloud browser | ↓tok (JS-heavy pages, Stagehand) | 3.4k★ | paid | Medium | github.com/browserbase/mcp-server-browserbase |
| 10 | Package Registry MCP | 16 | npm/PyPI/crates.io/NuGet/Go metadata+GHSA | ↓tok (nearest to doc-discovery) | 38★ | yes | Heavy | github.com/Artmann/package-registry-mcp |
| 11 | Firecrawl MCP | 18 | scrape+batch+map+search+crawl+extract+agent | ↓tok+↑qual (LLM structured extraction, most capable) | 6.5k★ | paid | Heavy | github.com/firecrawl/firecrawl-mcp-server |
| 12 | Apify MCP | 18 | 4000+ Actors, search/fetch docs built-in | ↓tok | 1.3k★ | paid | Heavy | github.com/apify/apify-mcp-server |
| 13 | Scrapeless MCP | 20 | Google SERP+cloud browser | ↓tok | 162★ | paid | Heavy | github.com/Scrapeless-ai/scrapeless-mcp-server |
| 14 | Playwright MCP | 47+ (22 core) | full browser automation | ↑qual (a11y snapshot ≠ screenshot) | **33.5k★** | yes | **Massive** — use only if needed | github.com/microsoft/playwright-mcp |
| 15 | GitHub MCP | **87** | code search+API+repo mgmt | ↓tok (`search_code` = killer tool) | **30.4k★** | yes (rate limited) | **Massive** — `search_code` buried in 87 tools | github.com/github/github-mcp-server |

#### E2 Key Gaps

| Gap | Detail | Workaround |
|---|---|---|
| **No Stack Overflow MCP** | No dedicated error-message search against SO exists | Web-search MCP + `site:stackoverflow.com <error>` |
| **No documentation-discovery MCP** | No tool takes package name → returns docs URL. Package Registry MCP gives homepage but doesn't verify/rank docs | Web-search + `"{package} documentation"` |
| **No GitHub Code Search-only MCP** | `search_code` is the killer tool for finding code examples, but buried in 87-tool GitHub MCP | Thin 1-2 tool MCP wrapping GitHub `search/code` endpoint → **build opportunity** |
| ScrapingBee MCP | 0★, immature — drop | — |

---

### E3: Git/VCS Deep ✅

#### E3-Semantic Commit Generation

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **CommitBee** ⭐ | CLI | tree-sitter AST → symbol-level diffs → evidence-constrained prompt (~6K token budget). 7-rule self-validation, multi-LLM, 10 languages, secret scanning, local-first | ↓tok (no raw diff dump to LLM) | 4★ v0.6.0, 213 commits, 7 releases, **440 tests**, Rust | low (symbol-level commit gen unique) | github.com/Sephyi/commitbee |
| **commitizen** | CLI | Conventional Commits enforcement, auto-bump version, changelog. **Has `AGENTS.md`** | ↓tok (structured, non-AI) | **3.4k★** v4.16.3, 2.5k commits, 88 releases, Python, MIT | low (enforces schema, not LLM-based) | github.com/commitizen-tools/commitizen |
| DiffSense | CLI | Pipes staged diff to LLM with size/style flags, `--nopopup` for agents | ↓tok | 84★ v1, 85 commits, 5 releases | macOS-only, Apple Silicon only | github.com/edgeleap/diffsense |

#### E3-Blame / History Analysis

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **Hercules** | CLI | Line-level blame (RB-tree), burndown, couples co-change analysis, structural hotness. Outputs YAML/Protobuf | ↓tok (structured data, not raw blame dump) | **2.8k★** v10.7.2, 1k commits, 45 releases, Go. Dormant since 2020 but functional | low | github.com/src-d/hercules |
| **Git of Theseus** | CLI | Code age cohorts, survival curves (Kaplan-Meier), author stats. JSON output | ↓tok (structured) | **2.9k★** Python, PyPI | low | github.com/erikbern/git-of-theseus |
| cyanheads/git-mcp `git_blame`+`git_log`+`git_changelog_analyze` | MCP | Structured JSON blame/log at 3 verbosity levels | ↓tok | see below (same MCP server) | — | github.com/cyanheads/git-mcp-server |

#### E3-Worktree Management

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **git-worktree-runner (gtr)** ⭐ | CLI | One-command worktree + AI tool launch (`git gtr new feat --ai`). Auto-copies config/env. Adapters: Claude Code, Aider, Codex, Copilot, Cursor, Gemini, OpenCode | ↓tok (no stash/switch friction) | **1.6k★** v2.7.3, 105 commits, 12 releases, Shell, CodeRabbit | **N1 pick** — AI-native worktree | github.com/coderabbitai/git-worktree-runner |
| **git-wt** | CLI | `git wt` subcommand, JSON output, shell integration auto-cd, hooks, `.gitignore`-style file copy patterns | ↓tok | 529★ v0.29.0, 438 commits, 48 releases, Go, MIT | low | github.com/k1LoW/git-wt |
| wtp | CLI | Automated setup, branch tracking, smart navigation | ↓tok | 498★ Go | vs git-wt (similar) | github.com/satococoa/wtp |

#### E3-Conflict Resolution

**Gap: No mature standalone structured merge conflict resolution tool exists.** difftastic's merge-conflict mode (v0.50+) is best available. AST-based merging remains unsolved outside IDE plugins. **Build opportunity.**

#### E3-PR-from-Diff

**Gap: All tools <5★.** `pr-code-analyzer` (5★), `prghost` (3★), `pullpoet` (2★) — all single-contributor, few commits. Best approach: `git diff main...HEAD` → LLM with structured PR template.

#### E3-Git MCP Servers

| candidate | tools | type | ↓tok/↑qual | maturity | N1 fit | URL |
|---|---|---|---|---|---|---|
| **cyanheads/git-mcp-server** ⭐⭐ | 28 (full git surface) | MCP | ↓tok (structured JSON at 3 verbosity levels, STDIO+HTTP, commit signing, base-dir sandbox) | 220★ v2.15.1, 400 commits, **67 releases**, TypeScript, npm | **Production-grade** — best git MCP | github.com/cyanheads/git-mcp-server |
| mcp-server-git (official) | 12 (status, diff, commit, add, reset, log, branch, checkout, show) | MCP | ↓tok | 86.8k★ monorepo, Python, MIT | Simpler but official. uvx install | github.com/modelcontextprotocol/servers (src/git) |
| adhikasp/mcp-git-ingest | 2 (dir structure + file read) | MCP | ↓tok (read-only, clone-based repo structure ingestion) | 308★ 13 commits | Lean (2 tools only) | github.com/adhikasp/mcp-git-ingest |
| cleanDiff | 1 (diff-to-JSON MCP+CLI) | MCP+CLI | ↓tok 60-80% claim (strip context) | 0★ single commit, Go | Too early, idea compelling | github.com/hegner123/cleanDiff |
| MarcusJellinghaus/mcp-workspace | 10 (mostly filesystem, min git) | MCP | ↓tok | 47★ v0.1.12, 12 releases, Python | Filesystem-focused, `git mv` only | github.com/MarcusJellinghaus/mcp-workspace |

#### E3-Diff Analysis (beyond difftastic)

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **delta** | CLI | Syntax-highlighted diffs, side-by-side, word-level, `--navigate` mode, merge conflict + blame display | ↑qual (agent-readable diffs) | **31k★** v0.19.2, 2.2k commits, 62 releases, Rust, MIT | complement difftastic (delta=display, difftastic=AST-aware) | github.com/dandavison/delta |

#### E3-High-Utility Supporting Tools

| candidate | type | what | ↓tok/↑qual | maturity | URL |
|---|---|---|---|---|---|
| **git-absorb** | CLI | Fixup automation — auto-places staged changes into correct ancestor commits. Eliminates manual `fixup!`+rebase dance | ↓tok | **5.6k★** v0.9.0, Rust, BSD-3 | github.com/tummychow/git-absorb |
| **git-branchless** | CLI | `git undo`, `git smartlog`, `git restack`, `git sync`. In-memory operations. Agent-friendly undo/repair | ↓tok | **4.1k★** v0.11.1, Rust, alpha but functional | github.com/arxanas/git-branchless |
| **git-spice** | CLI | Stacked diff management, submit PR stacks. **Has `AGENTS.md` + `.claude/` dir** (explicit agent design) | ↓tok | 670★ v0.29.0, 58 releases, Go, GPL-3 | github.com/abhinav/git-spice |
| **git-revise** | CLI | In-memory rebase. Agent modifies commits without touching working tree. Faster than `git rebase -i` | ↓tok | 850★ v0.7.0, 12 releases, Python, MIT | github.com/mystor/git-revise |
| **gitoxide** | Lib+CLI | Pure-Rust git. `gix` crate for programmatic git without shelling out | ↓tok (API vs shell commands) | **11.5k★** v0.54.0, 15k+ commits, Apache-2/MIT | github.com/Byron/gitoxide |

#### E3 Top Picks

| # | Tool | Why |
|---|---|---|
| N1 | **cyanheads/git-mcp-server** | 28 tools, structured JSON, 67 releases, production-grade — single `npx` install covers entire git surface |
| N2 | **git-worktree-runner (gtr)** | AI-native worktree with Claude Code adapter. Parallel agent sessions without stash/switch |
| N3 | **CommitBee** | AST-level semantic commits. 440 tests. Evidence-constrained = no LLM hallucination in commit messages |
| N4 | **git-absorb** | 5.6k★ fixup automation. Agents making review fixes don't track which commit |
| N5 | **gitleaks** | 27.5k★ pre-commit secret guard — agents pipe code through `gitleaks stdin` before commit |

---

### E4: API / HTTP / Integration ✅ (re-run 2026-06-05, general-purpose agent — granted WebSearch/WebFetch/gh)

> N1 lens: count tool-defs per MCP; CLI > MCP on load-all hosts. Stars/dates verified via `gh` 2026-06-05.

#### E4-OpenAPI → tool/client gen

| candidate | tools(#defs) | type | ↓tok/↑qual | maturity | overlap | N1 | URL |
|---|---|---|---|---|---|---|---|
| **awslabs openapi-mcp-server** ⭐ | dynamic (gen from spec) | MCP | spec→typed MCP tools at runtime, bounded by spec | 9.2k★ (mono) rel 2026-06-04 v.active | generator ≠ fixed set | ⚠️ Heavy if spec big — endpoint allow-list | github.com/awslabs/mcp (src/openapi-mcp-server) |
| **openapi-mcp-generator** ⭐ | CLI (0 own def) | CLI | build-time: emit typed MCP/client → no runtime spec dump | 596★ pushed 2026-05-06 | build-time analog of AWS | Lean (output controllable) | github.com/harsha-iiiv/openapi-mcp-generator |
| **any-openapi** (snaggle-ai) | ~3 (search/explore spec) | MCP | semantic search OVER spec ไม่โหลดทั้ง spec | 894★ pushed 2026-02-21 solo (@janwilmake) | Context7-concept for arbitrary API | ⭐ Leanest (≤3) | github.com/snaggle-ai/openapi-mcp-server |
| Speakeasy | CLI (0 def) | CLI | spec→typed SDK + MCP server + contract test, build-time | 416★ OSS core rel 2026-06-02 v.active | build-time SDK/MCP gen | Lean | github.com/speakeasy-api/speakeasy |
| fastapi_mcp | dynamic | lib | expose FastAPI routes as MCP w/ auth (server-side) | 11.9k★ pushed 2025-11-24 slowing | server-side ≠ agent-side | Varies | github.com/tadata-org/fastapi_mcp |
| mcp-openapi-proxy | dynamic | MCP | proxy spec→tools low-config | 147★ **stale 2025-04** | subset of AWS server | Medium | github.com/matthewhand/mcp-openapi-proxy |

#### E4-GraphQL

| candidate | tools(#defs) | type | ↓tok/↑qual | maturity | overlap | N1 | URL |
|---|---|---|---|---|---|---|---|
| **Apollo MCP Server** ⭐ | 4 (introspect/search/validate/execute) | MCP | schema *search* + depth-bounded introspect → ไม่ dump schema. rare case MCP>CLI (schema-aware ต้อง structured) | 285★ rel v1.14 2026-05-15 vendor | none direct | ⭐ Lean (4, well-designed) | github.com/apollographql/apollo-mcp-server |
| mcp-graphql (blurrah) | ~2 (introspect, query) | MCP | generic introspect+query any endpoint | 389★ pushed 2025-09 stale-ish | generic Apollo | ⭐ Leanest (≤2) | github.com/blurrah/mcp-graphql |

#### E4-REST/HTTP test runners (agent-invocable, JSON out)

| candidate | type | ↓tok/↑qual | maturity | overlap | N1 | URL |
|---|---|---|---|---|---|---|
| **Hurl** ⭐ | CLI | plain-text HTTP test+assert, `--report-json`, clean exit code | **19.0k★** rel 8.0.1 2026-04-29 v.active | none | ⭐ Leanest | github.com/Orange-OpenSource/hurl |
| **xh** ⭐ | CLI | fast HTTPie-compat, single binary, scriptable | 7.8k★ rel 2025-12 | faster httpie | ⭐ Leanest | github.com/ducaale/xh |
| Bruno CLI | CLI | git-native `.bru`, `bru run` JSON reporter | **44.7k★** rel v3.4.2 2026-05 | heavy GUI; CLI=lean part | Leanest (CLI) | github.com/usebruno/bruno |
| restish | CLI | auto-discover API via OpenAPI links, JSON out, auth profiles | 1.3k★ rel v2.1.2 2026-06-03 | OpenAPI-aware client | Leanest | github.com/rest-sh/restish |
| httpYac | CLI | `.http` files; http+gRPC+WS+MQTT 1 runner | 839★ rel 2025-03 solo slowing | multi-protocol niche | Leanest | github.com/AnWeber/httpyac |
| HTTPie | CLI | ubiquitous JSON-first | 38.2k★ **stale 2024-12** | superseded by xh (speed) | Leanest | github.com/httpie/cli |
| posting | TUI | terminal API client, interactive | 12.0k★ rel 2026-03 | interactive = weak agent-batch | Leanest | github.com/darrenburns/posting |

#### E4-Webhook / event

| candidate | type | ↓tok/↑qual | maturity | overlap | N1 | URL |
|---|---|---|---|---|---|---|
| **Hookdeck CLI** ⭐ | MCP+CLI | forward/replay/query webhook event; CLI=0 def + optional MCP | 358★ rel v2.2.0 2026-06-03 vendor v.active | none | ⭐ Lean (CLI primary) | github.com/hookdeck/hookdeck-cli |
| smee-client | CLI | receive+forward webhook → localhost | 546★ rel v4.4.3 2025-11 | forwarding only | Leanest | github.com/probot/smee-client |
| webhook.site | self-host | capture+inspect request | 6.6k★ LTS 2023 pushed 2026-05 | inspection UI, weak agent API | Medium | github.com/webhooksite/webhook.site |

#### E4-Auth / secret injection

| candidate | type | ↓tok/↑qual | maturity | overlap | N1 | URL |
|---|---|---|---|---|---|---|
| **Infisical CLI** ⭐ | CLI | `infisical run` inject secret as env → agent ไม่เห็น raw token | **27.2k★** rel 2026-06-02 v.active | none (= paw Permissions ethos) | ⭐ Leanest | github.com/Infisical/infisical |
| Teller | CLI | multi-backend secret→env inject | 3.2k★ pushed 2026-01 slowing | overlap Infisical CLI | Leanest | github.com/tellerops/teller |
| Infisical MCP | MCP | agent-callable secret fetch | 47★ pushed 2026-04 tiny | CLI version preferred (load-all) | Lean | github.com/Infisical/infisical-mcp-server |

#### E4-gRPC

| candidate | type | ↓tok/↑qual | maturity | overlap | N1 | URL |
|---|---|---|---|---|---|---|
| **grpcurl** ⭐ | CLI | reflection gRPC call JSON in/out ("curl for gRPC") | **12.7k★** rel v1.9.3 2025-03 | none | ⭐ Leanest | github.com/fullstorydev/grpcurl |
| **buf** ⭐ | CLI | proto lint/breaking/codegen/registry, bounded output | 11.2k★ rel v1.70 2026-05 v.active | none | Leanest | github.com/bufbuild/buf |

#### E4-API mocking / contract

| candidate | type | ↓tok/↑qual | maturity | overlap | N1 | URL |
|---|---|---|---|---|---|---|
| **Prism** ⭐ | CLI | OpenAPI/Postman → mock server + request-validate, 1 cmd | 5.0k★ rel v5.15.11 2026-06-03 v.active | none | ⭐ Leanest | github.com/stoplightio/prism |
| MSW | lib | network-layer mock for JS test, in-process | 18.0k★ rel v2.14.6 2026-05 | JS-test scoped | Leanest | github.com/mswjs/msw |
| WireMock | CLI/lib | stub + record/replay HTTP standalone | 7.3k★ rel 3.13.2 2025-11 | JVM-centric | Lean | github.com/wiremock/wiremock |
| Pact (pact-js) | lib | consumer-driven contract test | 1.8k★ rel v16.5 2026-05 | contract-test niche | Lean | github.com/pact-foundation/pact-js |

#### E4-API gateway / aggregator (bounded output)

| candidate | type | maturity | note | URL |
|---|---|---|---|---|
| _flag:_ Kong mcp-konnect | MCP | 42★ single-vendor rel 2026-05 | too small, concept right (= gap below) | github.com/Kong/mcp-konnect |
| Tyk / GraphQL Hive Gateway | CLI/infra | 10.7k★ / 113★ | infra ไม่ใช่ agent tool | github.com/TykTechnologies/tyk |

#### E4 Key Gaps (build opportunities)

| capability | gap | paw build |
|---|---|---|
| **Bounded API-gateway aggregator MCP** | มีแค่ Kong 42★ vendor; ไม่มี generic capped-output | ≤5-tool MCP proxy arbitrary HTTP + truncate/paginate large body |
| **Webhook capture as agent tool** | ทั้งหมดเป็น CLI/UI; ไม่มี lean MCP capture→query→assert in-loop | thin MCP wrap smee/Hookdeck + `wait_for_event(filter)` + bounded payload |
| **OAuth token-broker for agents** | secret-CLI inject env ได้ แต่ไม่มี "agent ขอ scoped short-lived token โดยไม่เห็น" broker | token-broker MCP/CLI: agent ตั้งชื่อ provider → ได้ opaque handle → call ผ่าน proxy |
| **Spec-search-first OpenAPI** | มีแค่ any-openapi 894★ solo | harden search-over-spec explorer (Context7-style for arbitrary spec) |
| **gRPC as MCP** | grpcurl เป็น CLI-only; ไม่มี lean reflection gRPC MCP | wrap grpcurl ≤3-tool MCP (list/describe/call) |

#### E4 Top Picks (N1-biased)

| # | tool | why |
|---|---|---|
| N1 | **Hurl** (19k★ CLI) | plain-text HTTP test + JSON report + exit code; 0 def, default REST runner ทุก load-all host |
| N2 | **grpcurl** (12.7k★ CLI) | reflection gRPC over JSON; ไม่มี lean MCP เทียบ, เติม protocol gap ที่ 0 def |
| N3 | **Apollo MCP** (285★ 4-tool) | GraphQL MCP เดียวที่ design มา token-efficient (schema search + bounded introspect); rare MCP>CLI |
| N4 | **Prism** (5k★ CLI) | 1-cmd OpenAPI→mock+validate; มาตรฐาน contract/mock, CLI ฟรีบน load-all |
| N5 | **Infisical CLI** (27k★ CLI) | `infisical run` inject secret as env → API call โดยไม่เห็น raw token; แก้ secret-leak ที่ 0 def. = paw Permissions ethos |

**caution:** awslabs openapi-mcp-server + mcp-openapi-proxy register tool *dynamic จาก spec* → spec ใหญ่ = blow budget บน load-all. pair กับ endpoint allow-list หรือ prefer build-time gen (openapi-mcp-generator/Speakeasy) ให้ runtime surface bounded.

---

### E5: SAST / Security-Deep ✅

#### E5-SAST (Static Analysis)

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **Semgrep MCP** ⭐ | SAST+MCP | `semgrep mcp` built into binary: `semgrep_scan`, `semgrep_scan_with_custom_rule`, `get_abstract_syntax_tree`. Rule-based, agent writes custom rules directly | ↓tok (structured JSON findings) | **high** (widely deployed). MCP server archived Oct 2025 → now shipped in `semgrep` binary | overlaps Snyk Agent Scan (SAST); Semgrep = rule-based vs Snyk = ML + broader threat coverage | github.com/semgrep/semgrep |
| mobsfscan | Mobile SAST | JSON, SARIF 2.1.0, SonarQube, HTML | ↓tok (JSON grouped by rule, file:line, CWE) | Medium (MobSF-backed) | mobile niche complement to Semgrep | github.com/MobSF/mobsfscan |
| CodeQL CLI | SAST (semantic) | SARIF (`--format=sarifv2.1.0`), CSV, JSON | Medium-High (SARIF verbose ~KB/finding — **no bounded wrapper exists**) | High (GitHub-maintained) | overlap Semgrep (CodeQL deeper but more expensive output) | github.com/github/codeql |

**CodeQL gap:** No bounded-output wrapper exists. Post-processing SARIF → `rule-id + file:line + severity` would be low-effort but isn't built.

#### E5-Dependency Audit

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **osv-scanner** ⭐ | Dep vuln scan | Multi-language (npm/PyPI/cargo/Go/…). JSON/SARIF/CycloneDX output. **Has `AGENTS.md` + `llms.txt`** in repo — explicitly agent-aware | ↓tok (OSV-native structured advisory objects) | High (Google, Go) | universal dep audit — supersedes per-lang tools | github.com/google/osv-scanner |
| pip-audit | Python dep scan | JSON/CycloneDX output, `--fix` auto-remediate | ↓tok | High (Trail of Bits) | Python-specific; osv-scanner covers Python too | github.com/pypa/pip-audit |
| npm audit | Node.js dep scan | JSON (`npm audit --json`) | Medium (verbose advisory tree, needs `jq` filtering) | High (bundled with npm) | Node.js built-in; osv-scanner > npm audit for agent use | docs.npmjs.com |
| cargo-audit | Rust dep scan | JSON flag unconfirmed | Unknown | High (RustSec) | osv-scanner covers Rust too | github.com/rustsec/rustsec |

#### E5-SBOM + CVE Pipeline

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| **Syft** ⭐ | SBOM generation | CycloneDX/SPDX/Syft JSON from images, filesystems, dirs | ↓tok (standard SBOM schemas, bounded) | High (Anchore) | pair with Grype for CVE scan | github.com/anchore/syft |
| **Grype** ⭐ | Vuln scanner | JSON/CycloneDX/SARIF, EPSS+KEV risk scoring. Pipe Syft→Grype = SBOM→CVE pipeline | ↓tok (CVE+severity+fix structured) | High (Anchore) | pair with Syft | github.com/anchore/grype |
| **Trivy** | Multi-scanner | Container vuln + IaC misconfig + secrets + SBOM. JSON/SARIF/CycloneDX/SPDX output. Unified schema across all scanners | ↓tok (one tool, all scan types) | High (Aqua Security) | **Most comprehensive single-tool security scanner** | github.com/aquasecurity/trivy |
| cdxgen | SBOM generation | CycloneDX JSON (v1.5-1.7), SPDX 3.0.1. Multi-BOM: SBOM/HBOM/CBOM/OBOM/SaaSBOM/AI-BOM. Server mode | ↓tok | High (OWASP/CycloneDX) | broader BOM types than Syft; `cdx-audit` for vuln scan | github.com/CycloneDX/cdxgen |

#### E5-License Compliance

| candidate | type | what | ↓tok/↑qual | maturity | overlap | URL |
|---|---|---|---|---|---|---|
| license-checker | npm license audit | JSON (`--json`), `--failOn`/`--onlyAllow` for pass/fail gating | ↓tok (flat per-package license map, token-cheap) | Medium (community) | npm-only, dead-simple | github.com/davglass/license-checker |
| ORT | Polyglot license+policy+vuln pipeline | CycloneDX/SPDX SBOM via Reporter. Full pipeline: Analyzer→Scanner→Advisor→Evaluator→Reporter | Medium (pipeline stages → output large) | High (Linux Foundation), Kotlin | heavyweight but comprehensive | github.com/oss-review-toolkit/ort |
| FOSSA CLI | License+dep+vuln | SaaS-backed; results via web platform, not CLI JSON | Medium-High (needs SaaS) | High (commercial) | less agent-friendly (web platform) | github.com/fossas/fossa-cli |

#### E5-IaC Security

| candidate | type | what | ↓tok/↑qual | maturity | URL |
|---|---|---|---|---|---|
| **Checkov** ⭐ | IaC SAST | JSON/SARIF/CycloneDX/JUnit/CSV/MD. **Most format-flexible.** 1000+ policies. Terraform/CFN/K8s/ARM/Helm/Docker | ↓tok (multi-format, agent-pickable) | High (Bridgecrew/Palo Alto) | github.com/bridgecrewio/checkov |
| tfsec | Terraform SAST | JSON/SARIF/CSV/CheckStyle/JUnit | ↓tok | High (Aqua — now merged into Trivy, maintenance mode) | github.com/aquasecurity/tfsec |
| Terrascan | IaC SAST | JSON/YAML/XML (`-o json`), 500+ policies, multi-IaC | ↓tok (structured violations: rule+resource+file:line+severity) | High (Tenable) | github.com/tenable/terrascan |
| KICS | IaC SAST | JSON/SARIF/HTML/PDF/SonarQube, **20+ IaC platforms** (broadest coverage), query-based engine | ↓tok | High (Checkmarx) | github.com/Checkmarx/kics |

#### E5-Secret Detection (beyond TruffleHog)

| candidate | type | what | ↓tok/↑qual | maturity | URL |
|---|---|---|---|---|---|
| **Gitleaks** ⭐ | Secret detection | JSON/CSV/JUnit/SARIF. Fast (Go). Regex+entropy. Baseline support. 3 scan modes (git/dir/stdin). Redact flag | ↓tok (file:line:rule:secret snippet structured) | **27.5k★** feature-complete (security patches only) | github.com/gitleaks/gitleaks |
| **detect-secrets** | Secret detection+audit | JSON (`--json`), programmatic Python API. **Baseline approach: accept existing, block new.** Pre-commit hook native. 28+ built-in plugins | ↓tok (baseline workflow = only new secrets) | High (Yelp) | github.com/Yelp/detect-secrets |
| **ggshield** (GitGuardian) ⭐⭐ | Secret detection + **active validation** | 500+ secret types with vendor-specific validators. Scans AI assistant interactions (Cursor, Claude Code, Copilot). MIT | ↓tok+↑qual (validates if secrets are ACTIVE — unique) | High (GitGuardian, MIT) | github.com/GitGuardian/ggshield |
| Whispers | Secret+structured-data detection | JSON (`-o whispers.json`), YAML config, Python API. Plugin-based. Rules per severity+group | ↓tok | Medium (community) | github.com/adeptex/whispers |

#### E5-Secret Validation (active verification — "is this secret still live?")

| candidate | type | what | maturity | URL |
|---|---|---|---|---|
| **ggshield** | Detection+validation | Validates against 500+ vendor APIs. Listed above. | High | github.com/GitGuardian/ggshield |
| how2validate | Validation-only CLI | Unknown (Python CLI). Run after detection to verify findings. | Low (community, niche) | github.com/Blackplums/how2validate |
| betterleaks-cloud | Detection+validation (SaaS) | Cloud-hosted, live vendor-API validation (mostly Indian payment APIs) | Low (early stage) | github.com/AnshumanAtrey/betterleaks-cloud |

#### E5 Best-in-Category Summary

| Category | Top Pick | Reason |
|---|---|---|
| SAST (MCP-native) | **Semgrep MCP** | Only tool with official MCP server. Agent scans + writes custom rules directly |
| SBOM+CVE | **Syft+Grype** or **Trivy** | Syft→Grype = clean pipe. Trivy = swiss-army knife (all scanners, one tool) |
| IaC scanning | **Checkov** (format variety) or **Trivy** (if already using) | Checkov richest structured output options |
| Dep audit | **osv-scanner** | Multi-language, agent-aware (AGENTS.md+llms.txt in repo) |
| License | license-checker (npm) or ORT (polyglot) | license-checker dead-simple+token-cheap; ORT heavyweight but comprehensive |
| Secret detection | **Gitleaks** (speed) + **detect-secrets** (baseline workflow) | Gitleaks faster/simpler than TruffleHog; detect-secrets baseline model unique |
| Secret validation | **ggshield** | Only mature tool actively verifying secrets against vendor APIs (500+ types) |
| Container scanning | **Grype** or **Trivy** | Both output structured JSON with CVE/EPSS/KEV |

---

### E6: Scaffold / Codegen / Migration ✅

**Token thesis:** Every line an LLM re-generates that a deterministic tool could stamp out = wasted context.

#### E6-Project Scaffolders

| candidate | type | what | ↓tok | maturity | URL |
|---|---|---|---|---|---|
| **degit** | Git-tarball scaffold | `npx degit user/repo` = 0-token project clone vs LLM generating starter tree. Subdirectory cloning, caching, post-clone actions via `degit.json` | **Very High** | **7.9k★** Rich Harris (Svelte author), MIT | github.com/Rich-Harris/degit |
| plop | Micro-generator | Inquirer+Handlebars template expansion. Team encodes "the right way" once | High | **7.7k★** v4.0.5 Jan 2026, 1,012 commits, MIT | github.com/plopjs/plop |
| hygen | EJS template+file-injection | `_templates/` in repo, `skip_if` prevents dupes, `inject_before`/`inject_after` for modifying existing files | High | **5.9k★** v6.2.11, MIT. Used by Airbnb/Wix/Mercedes. Stable (last release Sep 2022) | github.com/jondot/hygen |
| create-t3-app | Stack bootstrapper | Interactive CLI → scaffolded full-stack Next.js project | Medium-High | **29k★** v7.40.0, MIT | github.com/t3-oss/create-t3-app |

#### E6-Type Generation (schema→types, deterministic)

| candidate | type | what | ↓tok | maturity | URL |
|---|---|---|---|---|---|
| **openapi-typescript** ⭐ | OpenAPI→TS types | `npx openapi-typescript spec.yaml -o types.ts` → 0 token burn on type authoring. Companion `openapi-fetch` for typed client | **Very High** | **8.2k★** 1,670 commits, 266 releases, MIT | github.com/openapi-ts/openapi-typescript |
| **graphql-codegen** ⭐ | GraphQL→typed code | One `codegen.yml` → typed hooks, resolvers, SDK. Plugin ecosystem (TS/React/Angular/Stencil) | **Very High** | **11.3k★** 8,687 commits, 2,020+ releases, MIT (The Guild) | github.com/dotansimha/graphql-code-generator |
| **sqlc** ⭐⭐ | SQL→type-safe Go/Kotlin/Python/TS | Write SQL queries → sqlc generates typesafe interfaces. Parses actual SQL at build time, no ORM runtime overhead | **Very High** | **17.8k★** v1.31.1 Apr 2026, 1,844 commits, MIT | github.com/sqlc-dev/sqlc |
| **quicktype** | JSON/JSON Schema/GraphQL→22+ languages | Paste JSON sample → typed models in TS/Go/Rust/Swift/Kotlin/C#/Python/… | High | **13.8k★** 3,776 commits, Apache-2.0 | github.com/glideapps/quicktype |
| protobuf-ts | Protobuf→TS | `protoc --ts_out` → typed messages+gRPC clients | **Very High** | 1.3k★ v2.11.1 Jun 2025, Apache-2.0 | github.com/timostamm/protobuf-ts |
| Prisma (`prisma generate`) | DB schema→typed Client | `prisma generate` from `schema.prisma` → fully typed query builder | High | **46.2k★** v7.8.0, Apache-2.0 | github.com/prisma/prisma |
| kanel | Live PG→TS types | `npx kanel` reads live DB → TS interfaces per table | Medium | 1.1k★ v3.5.1 Aug 2023, **stale-ish**, 31 open issues | github.com/kristiandupont/kanel |
| schemats | PG/MySQL→TS | **Archived** Feb 2018, 1.1k★ MIT | Drop (historical only) | github.com/sweetiq/schemats |

#### E6-Framework Migration (deterministic codemods)

| candidate | type | what | ↓tok | maturity | URL |
|---|---|---|---|---|---|
| **jscodeshift** ⭐ | AST transform runner (Meta) | Engine underlying react-codemod, vue-codemod, etc. Wraps `recast` for style-preserving AST edits | Foundation | **10k★** v17.3.0 Mar 2025, 565 commits, MIT | github.com/facebook/jscodeshift |
| **react-codemod** | React version migration | `npx codemod react/19/...` → automated React 18/19 upgrades: class→hooks, `ReactDOM.render`→`createRoot`, PropTypes removal | **Very High** | **4.4k★** 305 commits, MIT. React-team-official | github.com/reactjs/react-codemod |
| **django-upgrade** | Django Python codemods | Rewrites Django patterns to modern equivalents per version. Fixers for each Django version jump. 100% test coverage, Black-formatted | **Very High** | 1.2k★ 629 commits, 40 releases, MIT. Adam Chainz (Django core contributor) | github.com/adamchainz/django-upgrade |
| vue-codemod | Vue 2→3 migration | `npx vue-codemod -t <transform>` automates: slots, global API, composition API, Vuex, Vue Router | High | 287★ 54 forks, MIT, vuejs-official | github.com/vuejs/vue-codemod |
| Angular Schematics | Angular code gen+migration engine | `ng generate` + `ng update` execute deterministic transforms. Built into Angular CLI | High | Part of angular/angular-cli (27.2k★) | github.com/angular/angular-cli |

#### E6-Boilerplate Killers

| candidate | type | what | ↓tok | maturity | URL |
|---|---|---|---|---|---|
| **Hasura** | DB→GraphQL CRUD API | Point at PostgreSQL → instant CRUD GraphQL API with auth. Data connectors: PG/MongoDB/ClickHouse/MSSQL. V3 GA with Rust connectors | **Very High** (zero code for basic CRUD) | **32k★** v2.49.1 Jun 2026, 307 releases, Apache-2.0 | github.com/hasura/graphql-engine |
| **PostGraphile** | PG→GraphQL API | Schema introspection → full GraphQL with relations, mutations, filtering. Deeper PG integration: row-level security, computed columns, PG functions | **Very High** | **12.9k★** v5.0.3 May 2026, 16,312 commits, 138 releases, MIT | github.com/graphile/postgraphile |

#### E6-Template Engines (agent-invocable)

| candidate | type | what | ↓tok | maturity | URL |
|---|---|---|---|---|---|
| **cookiecutter** | Jinja2 templates | `cookiecutter gh:user/template` → full project from JSON-config template. 36.7k dependents. Pre/post-generate hooks in Python/shell | High | **24.9k★** v2.7.1 Mar 2026, 3,143 commits, BSD-3 | github.com/cookiecutter/cookiecutter |
| **copier** ⭐ | cookiecutter successor | Same init + `copier update` to evolve projects when template changes. Smarter overwrite handling. Templated filenames. Non-destructive by default | **Very High** (lifecycle updates = evolve not regen) | **3.4k★** v9.15.1, 2,235 commits, 68 releases, MIT | github.com/copier-org/copier |
| scaffdog | Markdown-driven scaffolding | `.md` template files with Front Matter → multi-file output. Templates ARE markdown | Medium-High | 768★ v4.1.0 Sep 2024, 2,240 commits, 94 releases, MIT | github.com/scaffdog/scaffdog |

#### E6-Migration-at-Scale

| candidate | type | what | ↓tok | maturity | URL |
|---|---|---|---|---|---|
| **ast-grep** (already listed C-Action) | AST search/lint/rewrite | YAML rule configs. Language-specific precision via tree-sitter | ↓tok | **14.3k★** v0.43.0 May 2026, 177 releases, MIT, Rust | github.com/ast-grep/ast-grep |
| comby | Structural search/replace (~every language) | `comby ':[pattern]' ':[replacement]'` — syntax-aware, not regex, not AST | ↓tok | 2.7k★ v1.8.1 Jun 2022, OCaml, Apache-2.0. **Stale** | github.com/comby-tools/comby |
| ts-morph | TS Compiler API wrapper | Programmatic TS code manipulation. Underlying engine for many JS/TS codemods. Better for code gen; jscodeshift better for migration transforms | High | **6.1k★** v28.0.0 Apr 2026, 2,344 commits, MIT | github.com/dsherret/ts-morph |

#### E6-Test Generation (deterministic from schemas/types)

| candidate | type | what | ↓tok | maturity | URL |
|---|---|---|---|---|---|
| **fast-check** | Property-based testing (JS/TS) | Generate test inputs deterministically from type arbitraries+property specs. Shrinks to minimal counterexample. Model-based state machine testing. Replayable seeds | High | **5k★** v4.8.0 May 2026, 6,669 commits, 279 releases, MIT | github.com/dubzzz/fast-check |
| TypeBox | Runtime JSON Schema→TS types | Define schemas once → compile-time TS types + runtime validators. JIT compiler 3-5× faster than Ajv | Medium-High | **6.7k★** 775 commits, 412 releases, MIT | github.com/sinclairzx81/typebox |
| Zod | Schema validation+type inference | `z.object(...)`→`z.infer<>` gives runtime parsing+compile-time types. JSON Schema conversion built in | Medium | **42.9k★** v4.4.3 May 2026, 2,925 commits, MIT | github.com/colinhacks/zod |

**Gap:** No mature tool generates full `describe/it` blocks from TS types or DB schemas at scale. **Build opportunity.**

---

### E7-E8: Deferred (priority ต่ำ)

| # | Scope | Why defer |
|---|---|---|
| E7 | Non-coding domain (docs/writing, ML notebooks, SQL-analytics agent) | Narrow paw target = coding agents first |
| E8 | RAG/embedding infra (self-host doc-RAG, embedding pipeline, reranker) | Overlap mem0/Qdrant already in C-Knowledge. Revisit if paw needs own knowledge layer |

---

## STRATEGIC FLAGS — wave 3

### Cross-cutting patterns

13. **LSP bridges = pre-adoption force-multiplier.** mcpls (39★) bridges pyright/rust-analyzer/tsserver/gopls/clangd in ONE install. Category <50★ = paw can bundle as set entry before market wakes up.
14. **Thin MCP wrappers = build-once, high leverage.** ruff (47.8k★), clippy (built-in), biome (24.9k★), oxc (21.4k★) all have JSON output → MCP wrapper ~30 LOC each. paw could build+ship as part of curated sets.
15. **Go = strongest language-specific MCP ecosystem.** hloiseau/gopls-mcp (87★) + xieyuschen/gopls-mcp (56★, fork of gopls source) = two viable options. golangci-lint MCPs architecturally solid.
16. **Java/Kotlin = MCP desert.** Only path = mcpls→jdtls. Build opportunity for Kotlin MCP (Detekt+Ktlint).
17. **git-worktree-runner = strategic for paw.** AI-native worktree with Claude Code/Codex/Gemini adapters built-in. paw L1 install could pair `gtr` + `cyanheads/git-mcp-server` as a "git-productivity" set.
18. **Nreki = architectural novelty.** In-RAM validation of AI edits before disk write. 11★ but 1,418 tests. If the approach works (50% token savings claim), this changes how agents interact with LSP — validate first, write after.
19. **No GitHub Code Search-only MCP.** `search_code` is the killer tool for finding code examples, but GitHub MCP ships 87 tools. Thin 1-2 tool MCP wrapping `search/code` endpoint = N1-perfect build opportunity.
20. **structured conflict resolution + PR-from-diff = empty categories.** No standalone tool >5★ in either. Could be paw-built differentiator (B-feature) or defer until market fills.
21. **Secret validation (ggshield) = unique capability.** Detects 500+ types AND validates if secrets are still active against vendor APIs. No other tool does both. Complements Gitleaks (speed) + detect-secrets (baseline workflow).

### N1 cross-wave ranking (tools ที่ solve ceiling ที่ราก)

| # | Tool | Why ceiling-friendly | Wave |
|---|---|---|---|
| 1 | **mcp2cli** | 96-99% schema token saved — แก้ MCP ceiling ที่ราก | C |
| 2 | **mcpls** | One install → LSP for 5+ languages. Cuts per-lang tool-def sprawl | E1 |
| 3 | **SerpAPI MCP** | 1 tool = all search engines. Leanest web-search | E2 |
| 4 | **Fetch MCP** | 1 tool, official, free. HTML→markdown | E2 |
| 5 | **osv-scanner** | Single tool covers npm/PyPI/cargo/Go dep audit | E5 |
| 6 | **Trivy** | One tool = vuln+IaC+secret+SBOM. Subsumes 4 tools into 1 | E5 |
| 7 | **cyanheads/git-mcp** | 28 tools but covers ENTIRE git surface. 1 install vs 12+ separate tools | E3 |

---

22. **E4 API: CLI sweep ทุก subcategory.** anchor เกือบทั้งหมดเป็น CLI (Hurl/xh/grpcurl/buf/Prism/Infisical) = 0 tool-def = N1-perfect บน load-all host. MCP เหมาะแค่ตอนต้อง schema-aware (Apollo GraphQL). **Infisical CLI = ตรง paw Permissions ethos** (agent ไม่เห็น raw secret) — pair กับ B5/B10 stack. OpenAPI dynamic-gen (AWS/proxy) = N1 hazard → prefer build-time gen.
23. **gateway/webhook/token-broker = empty agent-native category** (เหมือน E3 merge-resolution + GitHub-search-only) — paw-built differentiator candidate, ≤5-tool bounded MCP.

---

**สถานะ backlog:** A (~7 external core) + B (12 paw-built) + C (~30 scout wave1) + D (~50 domain/type wave2) + E (~110 scout wave3 incl E4). **รวม verified ~205.** gap-area เหลือ: E7-E8 (deferred โดยตั้งใจ), build-ops (thin MCP wrapper ruff/clippy/biome/oxc, GitHub Code-Search-only MCP, CodeQL-lite, structured merge-resolution, API-gateway/webhook/token-broker bounded MCP), LSP-bridge maturity (mcpls 39★ pre-adoption).
