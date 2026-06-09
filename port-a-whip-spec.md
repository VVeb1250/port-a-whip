# 🐾 port-a-whip — Product Spec & Concept

**version:** 0.3-draft
**author:** whipforaweep
**status:** direction locked (1.5 — layer + curated sets), ready for build planning
**supersedes:** 0.2 (router + own installer) → installer redundant, paw stands on existing installers. See §13.

---

## 1. Vision

> "Claude — and any coding agent — should be smarter and cheaper than what the vendor ships, the moment setup finishes."

port-a-whip ไม่ใช่ installer ตัวใหม่ และไม่ใช่ marketplace — **มี 5 เจ้าทำ install/config ข้าม host แล้ว** (Smithery, mcpm, MCPDog, …) แต่ paw **ไม่พึ่งตัวไหนเป็น runtime dep** (Smithery=Node+vendor+remote, mcpm=daemon ขัด ethos) — สำหรับ set ที่ curated แล้ว paw **patch config เอง 0 dep** (รู้ tool ล่วงหน้า ไม่ต้อง discovery) แล้วเติม **เฉพาะสิ่งที่ยังไม่มีใครทำ**:

1. **Curated sets** — ชุด tool (MCP + non-MCP) ที่ vet แล้วว่า**คุณภาพดี + เข้ากันจริง** ลงทั้งชุดทีเดียว
2. **Capability router** — บอกว่างานนี้ควรใช้ tool/skill ตัวไหน (per-prompt, token-lean)
3. **Lesson-memory** — จำว่า agent เคยพลาดอะไร แล้ว surface ข้าม host

เกณฑ์เดียวที่ทุกอย่างต้องผ่าน:
> **ลด token ที่ต้องใช้ หรือเพิ่มคุณภาพของข้อมูลที่ agent ได้รับ**

> **ทำไมเกณฑ์นี้ = แกนเดียว ไม่ใช่ 2 เป้าแยก:** token budget คือ performance lever อันดับ 1 (Anthropic multi-agent: token usage อธิบาย ~80% ของ performance variance). ∴ token ที่เสียเปล่า — context rot, idle tool-def, context ซ้ำ — = failure mode แพงสุด. paw **ตัด waste → คืน attention budget** ให้งาน productive. ลด cost กับเพิ่ม quality จึงเป็นเรื่องเดียวกันผ่านกลไกตัด waste — ไม่ใช่ "token น้อย = ดี" แต่ "token ไม่เสียเปล่า = budget เหลือทำงาน".

ไม่ใช่ startup ไม่แข่งใคร — เป้าหมาย: ให้คนอื่นได้ของดีที่รวมมาแล้ว setup ไม่ยุ่งยาก โดย**ไม่ reinvent ของที่มี**

---

## 2. Problem Statement

### 2.1 อะไร solved แล้ว (paw ไม่แตะ)

| solved | โดยใคร |
|---|---|
| install MCP ข้าม host, patch config, backup, OS paths | Smithery CLI, mcpm.sh, MCPDog, unified-mcp-manager |
| registry MCP รายตัว (6,000+) | Smithery |
| ราย tool ship installer ข้าม host เอง | เช่น codegraph (รองรับ 8 host) |
| host self-optimize token | Cursor Dynamic Context (−46.9%), Claude Code ToolSearch lazy-load |

→ **paw ไม่สร้าง general installer + registry แข่ง Smithery** (reinvent ชัด) แต่ **patch config สำหรับ set ที่ curated เอง ≠ general installer** — set แคบ รู้ tool ล่วงหน้า ไม่ต้อง discovery → ~150 บรรทัด stdlib ไม่ใช่การ reinvent Smithery (verify §15)

### 2.2 อะไร**ยังไม่มีใครทำ** (= paw)

**Gap A — ไม่มี "set" ที่ vet ว่าเข้ากัน**
registry คัด tool **รายตัว** ต้องรู้ชื่อ gem ก่อนถึงหาเจอ ไม่มีใครบอกว่า "ชุดนี้ใช้ด้วยกันแล้วดี ไม่ชนกัน" → user ต้องลองเอง เสียเวลา ลงชนกัน

**Gap B — รู้ว่ามี capability แต่ไม่รู้จะใช้ตอนไหน**
user สะสม skill/tool/rule เพียบ แต่ agent ไม่หยิบมาใช้เอง → capability ตายคาเครื่อง

**Gap C — ทำผิดซ้ำข้ามเซสชัน + ข้าม host**
agent ลืมหลังปิด session ไม่มี host/registry ไหนจำ mistake. host จำ code (RAG) ได้ แต่ไม่จำว่ามึงเคยพลาดอะไร

**Gap D — ของ non-MCP คุณภาพดีไม่มีที่รวม**
rtk-class (CLI proxy / hook / wrapper) ไม่ใช่ MCP server → ไม่มีวันอยู่ใน registry MCP ใดๆ โดยนิยาม → ของดีพวกนี้กระจัดกระจาย

### 2.3 ทำไม Gap พวกนี้ durable

vendor/host **จะไม่สร้าง portability + lesson-memory** — เพราะมันคือ anti-incentive (ช่วย user พก state ไปหาคู่แข่ง = ทำลาย lock-in ตัวเอง) ยิ่งใช้นาน lesson ยิ่งเยอะ = ค่าของ paw compound. Gap A/D = curation judgement ซึ่ง index อัตโนมัติแทนไม่ได้

---

## 3. Target Users

### Primary: power user ที่อยากได้ของดี setup ง่าย ไม่อยากลองเอง
- ใช้ Claude Code / Codex / Gemini CLI ทำงานจริง
- อยากได้ token efficiency แต่ไม่รู้จะเลือก/ผสม tool ไหน
- ลง "ชุดที่คนคัดมาแล้วว่าเข้ากัน" ทีเดียวจบ

### Secondary: คนใช้หลาย agent
- สลับ host แล้วอยากให้ capability + lesson ตามไป
- อยากได้ของ non-MCP คุณภาพ (rtk-class) ที่ registry ไม่มี

### ไม่ใช่ target:
- คนที่อยากได้ MCP รายตัวเฉพาะ → ใช้ Smithery ตรงๆ ดีกว่า
- Enterprise / web users / Cursor ในฐานะ dynamic-routing target (ดู §6)

---

## 4. Architecture — 3 ชั้น

```
┌─────────────────────────────────────────────────────────────┐
│ ชั้น 3 — Lesson-memory (unique, durable)                     │
│   capture mistake (Stop hook) → relevance inject ข้าม host   │
├─────────────────────────────────────────────────────────────┤
│ ชั้น 2 — Capability router (unique)                          │
│   kernel: ranking (TF-IDF + embedding) + capability registry │
│   per-prompt suggest: skill / tool / instruction / lesson    │
├─────────────────────────────────────────────────────────────┤
│ ชั้น 1 — Curated sets (unique curation, thin code)           │
│   set = bundle ที่ vet แล้ว (MCP + non-MCP) เข้ากันจริง       │
│   install: paw patch config เอง (JSON/TOML) + shim (non-MCP) │
│   0 runtime dep — ไม่พึ่ง Smithery/mcpm                       │
└─────────────────────────────────────────────────────────────┘
```
> patch config = parse (stdlib json / tomllib + tomlkit) → merge dict → backup → write. ไม่ string-edit เอง → JSON pitfall หาย. อ่าน source mcpm/MCPDog เป็น reference จัด edge case (ฟรี ไม่ใช่ dep)

- **kernel** (ชั้น 2-3, portable Python): reuse skill-router + mistake hook ที่ author มีอยู่ → generalize + portable + เพิ่ม capability types
- **set layer** (ชั้น 1): curation เป็น content + thin orchestration เรียก installer ที่มี
- **adapter** (per host): inject path + file ที่เขียน — contract tier-1 เกือบเหมือน → adapter บาง

---

## 5. Sets — แนวคิดหลักชั้น 1

**set = ชุด tool ที่คัดมาว่าคุณภาพดี + ใช้ด้วยกันแล้วเข้ากัน (ไม่ชนกัน)**
ต่างจาก registry: registry คัดราย tool, paw คัด **combo ที่ test ร่วมกันแล้ว**

> **LIVE:** set แรก `efficiency-starter` (codegraph + rtk) เขียนจริงแล้ว → [registry/sets.json](registry/sets.json) (schema_version 0.3.0, ref verified 2026-06-05). โครงย่อข้างล่าง; ไฟล์จริงมี `config_source`, `setup_shim`, `self_installs`, `host_support`, `verified` แบบ granular.

```json
{
  "set_name": "efficiency-starter",
  "description": "one line — ชุดนี้เหมาะกับใคร ประหยัดยังไง",
  "token_profile": { "<host>": "vendor-claimed UNVERIFIED; paw bench = Phase 2" },
  "mcp": [
    { "tool": "codegraph", "ref": "@colbymchenry/codegraph", "version": "latest",
      "config_source": "codegraph install --print-config {host}",
      "mcp_config": { "command": "npx", "args": ["-y","@colbymchenry/codegraph","serve","--mcp"], "env": {} },
      "setup_shim": { "steps": [{ "cmd": "codegraph init -i", "cwd": "{project_root}" }] } }
  ],
  "non_mcp": [
    { "tool": "rtk", "kind": "hook-proxy", "ref": "github.com/rtk-ai/rtk",
      "install": [{ "cmd": "rtk init -g" }], "host_support": ["claude-code","cursor","gemini","aider"] }
  ],
  "compat_notes": "คนละ layer ไม่ชน: codegraph=MCP context (no hook), rtk=PreToolUse (no MCP tool). intersection full-set = claude-code, gemini, cursor",
  "verified": { "schema_validated": "2026-06-05", "config_block_confirmed": false, "token_profile_benchmarked": false }
}
```

**เกณฑ์เข้า set:**
- ลด token / เพิ่ม context quality (วัดด้วย protocol §10 — ไม่ใช่ vibes)
- เข้ากับตัวอื่นใน set ได้ (ไม่ชน config / ไม่ซ้ำหน้าที่ / ไม่กิน context ทับ)
- **active-context budget** (สำคัญบน load-all host เช่น Codex/Gemini; CC lazy-load → idle ~0):
  - *coarse:* ≤ ~2-3 active MCP server/set (field data: เกิน 2-3 server → tool-selection accuracy ตก; 50 tool ≈ 72K token def). เกิน → แตก set หรือ mark host-specific. นับเฉพาะ MCP (โหลด tool-def); non-MCP (rtk hook) ไม่นับ
  - *fine (ถูกกว่า — ไม่ทิ้ง capability):* ถ้า server รองรับ env tool-subset (เช่น codegraph `CODEGRAPH_MCP_TOOLS`) → set entry ใส่ `env`/`tool_subset` ตัด tool-def ที่ไม่ใช้ออกโดยไม่ทิ้งทั้ง server
- install ได้จริง tested + pin version

**Schema additions (v0.3.x refinements):**
- `env` / `tool_subset` ต่อ MCP tool — N1 fine lever (ตัด tool-def ที่ไม่ใช้, เช่น `CODEGRAPH_MCP_TOOLS`)
- `trigger_terms` ต่อ set + capability — ให้ router match (§9). set `description` คง who+how; `trigger_terms` = what+when keywords แยก field
- `delivery: mcp-config | code-exec` (default `mcp-config`; `code-exec` = Phase 4 filesystem-wrapper, −98.7% token แต่ต้อง sandbox) — ใส่ field เผื่อ ยังไม่ build

**โหมด install (0 runtime dep):**
- **patcher = default** — MCP: paw patch config host เอง: parse (json/tomllib) → **dict-merge** (เก็บ server อื่นของ user) `mcpServers` (CC/Gemini) / `[mcp_servers.<name>]` (Codex TOML) → backup → parse-validate → write. edge: สร้างไฟล์ถ้าไม่มี, สร้าง parent table ถ้าไม่มี, idempotent.
- **shim = residue ราย tool** — สิ่งที่ patch ทำแทนไม่ได้: build step (`codegraph init -i` index — ไม่มี index = codegraph ตาย) + non-MCP (`rtk init -g`). pin version, ไม่ shell=True กับ community (§12).
- **DECISION (2026-06-05, advisor-vetted): ไม่ delegate การ patch config ให้ installer ของ tool แม้มันจะ self-install.** codegraph+rtk มี installer เอง แต่ delegate = รัน vendor code, ไม่มี backup/rollback/`portaw remove` เดียวกัน, installer codegraph เป็น interactive + patch **ทุก host** (scope host เดียวไม่ได้). config entry uniform `{command,args,env}`; per-installer adapter = bespoke = งานมากขึ้นตอน registry โต. patcher คุม long tail ของ bare MCP server (command+args ไม่มี installer). ใช้ `codegraph install --print-config {host}` แค่ **ดึง** block; paw เป็นคนเขียนเอง.
- ไม่พึ่ง Smithery/mcpm (offline ได้, no daemon, no vendor)

**Verified 2026-06-05:** Codex key `[mcp_servers.<name>]` (command/args + `.env` subtable) ✓. tomlkit 0.15 round-trip รักษา comment (header/inline/env) ตอน merge + tomllib re-read ผ่าน ✓. edge: ต้องสร้าง `[mcp_servers]` parent ถ้า config ใหม่.

**ของจริงเริ่มต้น:** เริ่มแค่ 1-2 set คุณภาพ (เช่น `efficiency-starter`) ที่เหลือค่อยหา + เพิ่ม recommended set ทีหลัง

---

## 6. Capability types (router — ชั้น 2)

| type | ตัวอย่าง | capture | inject | host |
|---|---|---|---|---|
| **skill** | SKILL.md | static | suggest | **Claude Code only** |
| **mcp-tool** | codegraph, git | static (set/registry) | suggest enable | portable |
| **instruction** | AGENTS.md / rule | static | inject snippet | portable |
| **lesson** | บทเรียนจาก mistake | **dynamic (Stop)** | relevance inject | portable (ชั้น 3) |

`skill` ผูก Claude Code → host อื่น route ได้แค่ mcp-tool + instruction + lesson. MCP = แกน portable แท้

> **skill *complement* MCP ไม่ใช่แทนกัน** — skill สอน workflow (progressive disclosure, 0 token idle), MCP ให้ tool primitive (portable แต่ load-all). set เดียว pair ได้ทั้งคู่. router rule: capability เท่ากัน → เสนอ skill/instruction ก่อน mcp-tool (เบากว่า)
> **ไม่เพิ่ม sub-agent/multi-agent เป็น capability type** — multi-agent ≈ 15× token (vs chat) + แพ้งาน coding (โดเมนหลัก paw). ถ้าเพิ่มภายหลัง: ต้องมี contract (objective / output-format / tool-guidance / boundaries) + gate แนะเฉพาะ breadth-first + high-value + parallelizable

---

## 7. Host support matrix (verified 2026-06)

| Host | per-prompt inject? | กลไก | event | tier |
|---|---|---|---|---|
| **Claude Code** | ✅ | command hook + `hookSpecificOutput.additionalContext` | `UserPromptSubmit` | 1 |
| **Codex CLI** | ✅ | เหมือนเป๊ะ | `UserPromptSubmit` | 1 |
| **Gemini CLI** | ✅ | field เดียวกัน | `BeforeAgent` | 1 |
| **Cursor** | ❌ block-only | `beforeSubmitPrompt` inject ไม่ได้ | — | 2 |
| **OpenCode** | ⚠️ unconfirmed | JS/TS plugin | — | 2 |

**Tier 1 — dynamic routing:** Claude Code, Codex, Gemini. contract เกือบเหมือน → kernel เดียว + adapter rename event + เลือกไฟล์เขียน (CLAUDE.md / AGENTS.md / GEMINI.md)
**Tier 2 — set install ได้ (ผ่าน Smithery) แต่ router degrade เป็น static:** Cursor (inject ไม่ได้ + self-optimize token เองแล้ว → paw เพิ่มค่าน้อย), OpenCode (คนละ model)

→ **paw เพิ่มค่าสูงสุดบน Codex/Gemini** (native optimization อ่อน) ต่ำสุดบน Cursor/Claude Code (native แข็ง)

---

## 8. CLI commands

```
portaw sets                    ดู curated sets ทั้งหมด
portaw sets show <set>         ดูรายละเอียด + token profile + compat notes
portaw install <set>           ลงทั้ง set (MCP patcher + shim build/non-MCP)
portaw install <set> --host X  ระบุ host
portaw remove <set>            ถอดทั้ง set (un-patch config + reverse shim)
portaw doctor                  ตรวจ env + detect host + parse host config valid?
portaw router enable           ติดตั้ง router hook ลง host ปัจจุบัน
portaw router status           host ไหน + tier ไหน
```

> ไม่มี `portaw install <single-tool>` เป็นหลัก — tool เดี่ยว → Smithery/mcpm ตรงๆ. paw ขาย **set + layer**

**`portaw doctor` ตรวจ:**
```
✅ host detected (Claude Code / Codex / Gemini)
✅ host config readable + parse ได้ (JSON/TOML valid)
✅ installed set health (ไม่ใช่แค่ไฟล์มี — เช็คทำงาน: index initialized, hook responds)
✅ config drift (live entry vs `--print-config` → stale หลัง CLI upgrade?)
✅ permission/allow-list entries ครบ (เช่น `mcp__<tool>__*`)
✅ Node 18+ / npx (ถ้า set มี tool ที่รันด้วย npx)
✅ Python 3.11+ (kernel + tomllib)
✅ router hook installed? (per host)
```

> **ref impl:** `codegraph-link` skill (author's) = working reference สำหรับ health-gate (`status -j`), drift check (`--print-config` compare), idempotent managed-block write+unlink (marker `<!-- start --><!-- end -->`), permission report. paw `doctor` + instruction-capability write + `portaw remove` ยืมรูปแบบนี้

---

## 9. Router — kernel spec (ชั้น 2)

**flow ต่อ prompt (tier 1):**
```
1. host UserPromptSubmit/BeforeAgent hook → ส่ง prompt เข้า paw kernel (stdin)
2. ranking: TF-IDF tier-1 → embedding tier-2 (multilingual)
3. match prompt กับ capability registry (4 types)
4. top-N ที่เกี่ยว (threshold-gated — ไม่แนะทุกครั้ง)
5. emit additionalContext = suggestion สั้น token-lean
6. host inject เข้า context turn นั้น
```

**design constraint:**
- **เงียบเมื่อไม่มั่นใจ** — แนะมั่วแย่กว่าไม่แนะ (pain เดิม: skill-router แนะแล้วไม่ถูกหยิบ)
- suggestion สั้น — router ต้องไม่กิน token เกินที่ประหยัด
- threshold ปรับได้ต่อ capability type
- **capability registry entry = `what + when` + `trigger_terms`** (skill-authoring best-practice: description ต้องบอกทั้ง "ทำอะไร" + "ใช้ตอนไหน") → match แม่นขึ้น. registry เก็บแค่ metadata (name/desc/trigger) สำหรับ rank; inject = pointer JIT load เนื้อจริง (3-tier progressive disclosure)
- retrieval ที่ดี = hybrid fused: TF-IDF (≈BM25) + embedding (semantic) → **rerank pass** (ตาม mem0 production pattern)

> **scope จำกัด (สำคัญ):** router แก้ Gap-B (discoverability) + tool-selection accuracy. **ไม่แก้ token-overhead ของ load-all host** — def โหลดจาก config ตอน startup, router inject ทับ unload ไม่ได้. overhead → set-size ceiling (§5) + code-exec delivery + native lazy-load. ถ้าอยากให้ router ตัด idle overhead จริง = ต้องทำ **router-driven JIT install** (architectural option ใหม่ ไม่มาฟรีจาก eager-install)

---

## 10. Token metric protocol

**ปัญหา:** `token_impact` label = vibes = curation อ่อน. set ต้องวัดจริง

```
1. แต่ละ set/tool มี canonical task (representative การใช้จริง)
2. รัน task เดิม: มี set (on) vs ไม่มี (off)
3. วัด token จาก session log ของ host
4. เก็บ { canonical_task, delta_tokens, delta_pct, host } → auditable
```

**nuance (host-dependent):**
- Claude Code: MCP lazy-load → tool ไม่ใช้กิน ~0 → เลข honest = **net ของ always-on schema overhead**
- Codex/Gemini: โหลด tool หมด → schema overhead จริง
- ∴ token profile เก็บ **ต่อ host** ไม่ใช่ค่าเดียว

**Set-entry eval gate (MVP — deterministic, code grader ล้วน):**
ก่อน set เข้า registry ต้องผ่าน 2 ตัวที่ deterministic แท้:
1. **token delta** — วัดจาก session log (on vs off), เก็บ per-host (= protocol ข้างบน)
2. **install health-check** — ไม่ใช่แค่ parse-valid แต่เช็ค *ทำงานจริง* (codegraph-link style: `codegraph status -j → initialized:true` + non-MCP hook responds)

> **pass@1 task-success = OPTIONAL ต่อ set ไม่ใช่ hard gate.** เหตุผล: "task success" ของจริงต้องมี test harness ขับ agent (infra cost) หรือ LLM-judge (= heavy path, defer §10-Phase2). บังคับ pass@1 = ลักลอบเอา cost พวกนี้เข้า + assertion ผูก output format → flaky → คนปิด gate → eval moat เน่า ("slow/flaky evals don't get run"). set author ที่เขียน assertion เบา-ไม่ flaky ได้ (query fixture repo ได้ node ที่รู้คำตอบ) → เพิ่มเองได้
> **heavy eval = Phase 2** (ตอน registry โตพอจะคุ้ม): ~20 canonical queries × multi-pass LLM-judge (rubric 0.0–1.0) × human-calibration + **trajectory eval** (tool-choice / redundant step / recovery). + **flywheel:** lesson capture (L3) → กลายเป็น regression eval = วงเดียว ไม่สร้าง 2 pipeline

---

## 11. Open Questions — locked

| Q | คำถาม | คำตอบ |
|---|---|---|
| Q1 | env var | prompt ตอน install → `.env` → `${VAR}` ref. ปฏิเสธ plaintext ใน config |
| Q2 | version | **pin** + lockfile + update. latest break เงียบ = ขัด vision |
| Q3 | registry long-term | sets bundled (Phase 1-3) → remote fetch (Phase 4) |
| Q4 | lesson scope | ทั้ง project + global — router relevance ตัดสิน ไม่ใช่ scope flag แข็ง |
| Q5 | lesson format | benchmark ก่อน ship (instruction format = baseline) |

---

## 12. Security

- non-MCP install: **ห้าม shell=True กับ community-submitted** — RCE vector
- **hash/signature verify** ก่อน install — บังคับก่อนเปิด community sets (Phase 4)
- env: ไม่เขียน plaintext secret ลง config — `.env` + `${VAR}`
- MCP source = curated set เท่านั้น (ไม่ใช่ arbitrary registry) → review เองก่อนเข้า set → surface เล็ก
- patch config: backup ก่อนเขียนเสมอ + parse-validate ก่อน write (กัน corrupt)
- no daemon, no vendor dep — รันแล้วจบ

---

## 13. Roadmap

```
Phase 1 — Sets + Claude Code (MVP)
├── set schema + 1-2 curated set (efficiency-starter)
├── portaw install <set> → patch config เอง (json/toml) + shim (non-MCP), 0 dep
├── kernel ranking engine ดึงจาก skill-router (host-agnostic)
├── Claude Code router adapter (wrap UserPromptSubmit hook ที่มี)
├── portaw doctor + host detection
└── pypi publish

Phase 2 — Portable router + token-vetted sets
├── Codex adapter (UserPromptSubmit — verified ✅)
├── Gemini adapter (BeforeAgent — verified ✅)
├── token metric protocol → ติด profile ทุก set
└── เพิ่ม recommended sets

Phase 3 — Lesson-memory (durable moat)
├── lesson capability: Stop hook capture → relevance inject
├── port mistake-learning ไป Codex/Gemini (ไม่ rebuild บน CC)
├── upgrade always-on → relevance-ranked
└── cross-host lesson sync

Phase 4 — (หารือทีหลัง)
├── community set submissions (+ review + hash verify)
├── remote set registry
└── Cursor/OpenCode static fallback (ถ้าคุ้ม — native แข็งแล้ว)
```

---

## 14. Changelog 0.2 → 0.3

| 0.2 | 0.3 | เหตุผล |
|---|---|---|
| paw build general installer + registry แข่ง | **patch config เอง 0 dep** สำหรับ set ที่ curated | general installer solved 5 เจ้า → ไม่แข่ง. แต่ set แคบ patch เอง ง่ายกว่าแบก dep (Smithery=vendor+Node, mcpm=daemon) |
| ขายราย tool | ขาย **sets** (combo ที่ vet ว่าเข้ากัน) | registry คัดราย tool แล้ว gap = combo-level curation |
| ไม่นับ non-MCP | **non-MCP set** (rtk-class) | registry MCP ไม่ครอบ hook/proxy โดยนิยาม = gap จริง |
| Cursor = tier 2 (inject) | tier 2 + **native self-optimize → paw เพิ่มค่าน้อย** | Cursor Dynamic Context −46.9% |
| installer เป็น Phase 1-2 | **lesson-memory ขึ้นเป็น durable moat** | vendor จะไม่ทำ portability/memory (anti-incentive) |

---

## 15. ค้างทำต่อ

- [x] verify Codex MCP TOML key (`[mcp_servers.<name>]`) + tomlkit round-trip (2026-06-05) ✓
- [x] **Codex+Gemini router HOOK wiring** (2026-06-06) — Codex `[[hooks.UserPromptSubmit]]` AOT, Gemini `hooks.BeforeAgent[]` JSON. stdin/output contract verified identical to CC across all 3 (JSON envelope, `prompt` key; out `hookSpecificOutput.additionalContext`); only `hookEventName`+config-file differ → single `_WIRING` dispatch in `adapters/router.py`. Codex LIVE-probed vs real config.toml copy; Gemini schema-verified+unit-tested only (CLI not installed → no live run). tests 21.
- [ ] ออกแบบ set schema final + เลือก tool ชุดแรกที่ vet ว่าเข้ากัน
- [x] **canonical task ต่อ set + token-metric protocol** (2026-06-06) — `token_profile` v2 (provenance enum `measured|calculated|vendor-claimed|estimated|neutral` + `delta_pct`/`idle_def_tokens`). most sets ไม่ต้อง A/B: `neutral` (0 MCP def) หรือ `calculated` (tiktoken บน def JSON จริง — context-quality = 927 tok). canonical A/B workload เฉพาะ token-SAVING tool: `bench/rtk-ab-workload.md` + `bench/codegraph-workload.md`. detail: deep-vet §5.
- [ ] หา + list ของ non-MCP คุณภาพ (rtk-class) ที่จะใส่ set
- [ ] benchmark lesson format (Q5) ก่อน Phase 3

**harness-quality research (2026-06-05, 5 รอบ — Anthropic tool/context/code-exec/skills/multi-agent + mem0 memory + eval survey):**
- [x] N1 set-size ceiling (§5) — coarse ≤2-3 MCP server + fine env tool-subset
- [x] N2 capability `what+when`+`trigger_terms` (§5 schema, §9) + registry metadata-only + rerank
- [x] N3 deterministic eval gate (§10) — token delta + install health-check; pass@1 optional; heavy eval → Phase 2
- [x] N4 vision framing (§1) — token budget = lever #1, ตัด waste
- [x] N5 sub-agent = ไม่เพิ่มเป็น type (§6 note); skill *complement* MCP
- [ ] DEFER (schema-hook ใส่แล้ว, build ทีหลัง): code-exec delivery (`delivery` field), L3+eval flywheel, trajectory/LLM-judge eval (Phase 2), relevance-ranked + confidence-decay lesson (Phase 3), router-driven JIT install (option naming เฉยๆ)
- คำเตือน staleness (L3): high-confidence stale lesson = "confidently wrong" → confidence-decay ผูก recurrence (xN counter = substrate)
