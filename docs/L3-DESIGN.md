# L3 Memory — Design (port-a-whip Phase 3)

> Source-of-truth for the lesson + project memory layer. Crystallized over the
> 2026-06-10 design session. Frame: **maximum context quality per injected token.**
> Read [NEXT-SESSION.md](../NEXT-SESSION.md) §"honesty knife" + CLAUDE.md Phase-3 first.

---

## 0. One-line identity

paw L3 = a **high-precision, compressed, silence-biased, self-tuning recall layer**
that injects *negative knowledge* (and project rationale) at the exact moment of
relevance — with **all machinery off the per-prompt context budget**.

It is **NOT** general agent memory (jcode does intra-host general memory better),
**NOT** a RAG engine, **NOT** a cloud service. The two non-negotiable axes:
**cross-host portability + mistake-surfacing.** Drift off these → paw is redundant.

---

## 1. The governing principle (why every decision below)

The only tokens that cost anything are the tokens **injected into context per prompt.**
Everything else (store, index, consolidation, embedding) must live OFF that budget.

**Asymmetry that governs all tuning:** a *false-inject* (irrelevant/verbose memory →
context rot) costs MORE than a *false-silence* (a missed lesson). Evidence: ETH study —
naive auto-generated CLAUDE.md = −3% task success / +20% cost. So the design is
deliberately **biased toward silence, compression, and high-confidence-only.**
The failure mode to fear is "injected noise," not "missed a note."

Four jobs, in priority:
1. **Precision** — inject only what's relevant (no noise tokens).
2. **Compactness** — each entry is tiny (R8).
3. **Silence** — inject *nothing* when nothing is relevant (the common case).
4. **Off-budget machinery** — store/index/consolidate never touch the prompt budget.

---

## 2. Memory types & scope

| type | scope | store | promote? | why |
|---|---|---|---|---|
| **lesson-memory** | **GLOBAL** | `~/.paw/memory/lessons/` | ✅ yes | mistakes recur across projects; env/lang-level ones are universal |
| **project-memory** | **PROJECT** | `<repo>/.paw/memory/` | ❌ no | decisions/rationale are repo-specific |
| ~~preference~~ | — | — | — | **deferred** → AGENTS.md / rulesync (reuse, don't rebuild) |

### 2.1 Lesson applicability is a spectrum, not binary (R12)

A global lesson store does NOT mean every lesson fires everywhere. Each lesson carries
an **applicability tag**:

| tag | example | retrieval-eligible when |
|---|---|---|
| `universal` | `py` not `python`, PS 5.1 no `??` | always |
| `stack:<x>` | React useEffect cleanup; Django migration | current project uses that stack |
| `project:<id>` | this repo's odd auth flow | only in that repo |

- New-lesson default tag = inferred (env-level mistake → `universal`; framework term →
  `stack:`; else `project:`).
- **Auto-promote** (reuse the existing `promote` skill pattern: project-instinct →
  global): a `project:A` lesson that recurs in `project:B` → promote scope up to
  `stack`/`universal`. This is exactly how "similar projects share mistakes."
- **Cross-project dedup is free**: the same mistake from two repos = ONE entry, bumped
  recurrence, promoted scope (handled by the consolidation pass, §6).

### 2.2 Safety scales with blast radius (R3 / SSGM)

Global lessons have a large poison radius (one wrong `universal` lesson pollutes every
project). So the write/confirm bar scales with scope:
`project` < `stack` < `universal` — universal writes need the highest
confidence + recurrence. Ties to the integrity gate (§7).

---

## 3. Retrieval — hybrid, anchored to what the agent touches

2026 consensus: stop arguing graph-vs-vector; **fuse them** (vector = semantic
entry-point, graph = multi-hop relational). paw already owns both halves.

```
retrieval(prompt, edit-target) =
    structural:  path + symbol match against the CURRENT edit target   ← 0-token floor
  ⊕ semantic:    kernel  ( TF-IDF tier-1  →  embedding tier-2 )
  + IF codegraph present (CC, indexed):  graph multi-hop neighbor       ← present-only bonus

rank = relevance × confidence × ACT-R_activation(recency × frequency)
```

**Key insight:** the retrieval trigger is "agent is editing file F / symbol S" — and
F+S are *already in context*. So anchoring on path+symbol and matching the current edit
target is **zero-index, zero-init-token, host-agnostic, and precise enough** (file+symbol
is exactly the relevance unit for "a lesson about this code"). The structural half of
the hybrid is satisfied for free.

### 3.1 Anchor backbone — weighted (paw axis: token + performance)

| anchor | init tok | setup | retrieval tok | precision | multi-hop | cross-host | anti-stale | role |
|---|---|---|---|---|---|---|---|---|
| **symbol-name** | 5 | 5 | 5 | 3.5 | 1 | 5 | 3 | **primary** |
| **path** | 5 | 5 | 5 | 2 | 1 | 5 | 4 | **primary** |
| LSP live | 5 | 3 | 3 | 5 | 4 | 3 | 5 | future optional |
| codegraph node | 4 | 2 | 4 | 5 | 5 | 2 | 4 | **bonus when present** |
| vector-only | 3 | 4 | 3 | 2.5 | 1 | 4 | 3 | semantic half only |
| graphify node | **1** | 2 | 3 | 4 | 5 | 4 | 3 | **dropped** (init token) |

Resolution:
- **PRIMARY (mandatory, zero-setup, every host) = `path` + `symbol-name`.**
- **ENRICHMENT (present-only, never required) = codegraph multi-hop** (CC, if indexed).
- **DROP `graphify` as backbone** — LLM-driven init = massive token on big repos;
  multi-hop gain doesn't beat symbol+path for code-memory. (Fine as a trial tool, not a
  memory dependency.)
- **LSP = deferred** optional rung (never-stale + compiler-accurate, but server-per-host
  friction + live-only).
- **graphify/codegraph/obsidian are NOT dependencies.** Memory works with zero of them;
  they are pure upgrades when a project happens to run them.

### 3.2 Anchor record (tiered, graceful-degrade)

```jsonc
anchors: {
  codegraph_nodes: [...],   // best: precise + multi-hop — CC + indexed only
  symbols: [...],           // portable: function/class names as strings — every host
  paths: [...],             // coarsest but most stable — greppable everywhere
}
```
Retrieval uses whatever exists. With codegraph → full graph mode. Without → path+symbol
+ semantic (degraded but functional, cross-host moat intact).

### 3.3 Embedding — what & where

`embedding` = **tier-2 of the semantic half** of the kernel. It matches a prompt to a
lesson when the *meaning* aligns but the *words* don't (e.g. prompt "async function
returns a coroutine" → lesson "forgot `await`"), and across languages (Thai lesson ↔
English prompt). TF-IDF (tier-1) catches lexical overlap; embedding catches paraphrase
+ cross-lingual.

- **Decision: lazy / optional, NOT a hard runtime dep.** Floor = TF-IDF + anchor (ships
  with zero model). Embedding = opt-in upgrade.
- **For this environment: ON** — the user's skill-router already loads a multilingual
  embedding model (tier-2); paw reuses that model rather than adding a dep. High value
  here because the user is Thai/English bilingual.
- Shipped default for others: OFF.

---

## 4. Entry schema

```jsonc
{
  id,
  type: "lesson" | "project",
  body,                          // COMPRESSED one-liner — see R8
  detail_ref,                    // pointer to full writeup (cold tier, expand on recall)
  trigger_terms: [...],          // router match (reuse Capability shape)
  anchors: { codegraph_nodes:[], symbols:[], paths:[] },   // §3.2
  applicability: "universal" | "stack:<x>" | "project:<id>",  // lessons; §2.1
  provenance,                    // measured | calculated | vendor | estimated | neutral
  confidence,                    // 0..1
  recurrence, last_seen,         // ACT-R activation substrate (§5)
  scope: "global" | "project",
  source: "hook" | "user" | "agent",
}
```

### R8 — compressed body + progressive disclosure (the single biggest lever)

Store `body` as a **caveman one-liner**: `trigger → fix` (lesson) /
`decision → rationale` (project). Full detail lives in the cold tier, expanded only when
the agent explicitly recalls it.

**Gold standard already exists** = the user's `mistakes-index.md` format:
`[SEV] [id] trigger → fix (xN, date)` ≈ **15 tokens carries a whole lesson.** paw memory
adopts this verbatim. Inject the 15-token pointer, not a 200-token prose blob.

---

## 5. Ranking & decay — ACT-R activation (R1)

Tier promotion/demotion and rank use a cognitive-model activation score, NOT raw
recurrence count:

```
activation = recency × frequency × semantic_relevance
```

(FadeMem / Priority-Decay / ACT-R; FadeMem reports −45% storage with this shape.) The
existing `xN` counter from the mistake hook supplies *frequency*; add *recency* and
*relevance*. A lesson not seen in N sessions decays out of the hot tier; recurrence bumps
it back.

---

## 6. Lifecycle — tiered working set + async consolidation

### R9 — tiers (corrected: store-size ≠ inject-size)

```
pinned always-on : ~5 entries, ~100 tok total   — only the highest-recurrence universal
                   lessons (e.g. "py not python" x33) — so cheap + high-ROI they justify
                   always-on injection
hot / warm       : relevance-gated, cap ~300–500 tok injected PER PROMPT, SILENT if no
                   match. (hot candidate POOL ≤ ~2K; what actually injects is the
                   threshold-gated subset, not the whole pool)
cold             : recall-only, loaded on explicit request
```
The earlier "always-on 2K every prompt" was wrong from a quality-per-token view — fixed
here.

### R2 — async "dream" consolidation

Anthropic shipped "Dreaming" (async hippocampal-consolidation, 2026-05-06) — validates
the direction. paw runs consolidation **offline, between sessions** (never inline):
merge duplicates, generalize specific→pattern, promote scope (§2.1), archive FIXED,
budget-bounded forget. This is the existing `mistakes-sweep` extended — append-only RAG
bloats; a consolidated store does not. **No new daemon** — paw reads codegraph/graphify
artifacts if present but runs no watcher of its own.

---

## 7. Safety — integrity gate (R3 / SSGM)

Evolving + cross-host memory is an attack surface: poisoning (an agent writes a wrong,
high-confidence lesson that propagates), drift, staleness. Gate on write:
- confidence threshold before an entry enters the hot tier,
- **human-confirm for project-memory writes** (also covers the ADR/CLAUDE.md harvest),
- provenance attached to every entry,
- write/confirm bar scales with scope (§2.2): `project` < `stack` < `universal`.

Pairs naturally with paw's `secure-agent` Permissions axis.

---

## 8. Capture & seeding

| memory | capture | notes |
|---|---|---|
| lesson | Stop-hook → detect failure→fix, append/bump (cross-host) | port the CC mistake hook to Codex/Gemini — do NOT rebuild on CC (author's hook runs) = the portability moat |
| project | `portaw memory add` + seed-prompt at codegraph/graphify co-init | piggyback existing init, no new mandatory setup |

### Seeding (v1 = B + ADR-harvest)

- **v1:** seed-prompt on init **+ harvest `docs/adr/*`** only (structured, low-noise,
  1 ADR = 1 entry, anchored to the node it governs).
- **v2:** add `CLAUDE.md` / `README` harvest **behind a confirm-gate** + dedup, once
  extraction is accurate (raw dump = the ETH −3%/+20% trap → extract decisions, never
  dump files).
- Memory's own mandatory per-project setup = **zero** beyond creating `.paw/memory/`.

---

## 9. The self-tuning loop (R10) — the elegant core

An injection only "earns its tokens" if it **suppresses recurrence.** Closed loop, and
**measurable** via the existing `xN` substrate:

```
lesson injected  →  mistake stops recurring (xN flat)   →  injection paid for itself ✓
lesson injected  →  mistake still recurs (xN climbs)     →  injection isn't working:
                                                            wrong content or wrong timing
                                                            →  demote / rewrite / re-anchor
```
This is the real quality-per-token metric — not vibes. Threshold is asymmetric per type
(R11): negative-knowledge lessons (high ROI, prune the search space) get a **low**
injection threshold; project-decisions (lower ROI) get a **high** threshold and fire
mostly when the agent is about to *contradict* the decision.

---

## 10. Evaluation (don't invent metrics)

- coding-agent memory bench: `rohitg00/agentmemory` → `coding-agent-life-v1` (2026-05).
- general recall: **LongMemEval** (Zep), **LOCOMO** (mem0).
- paw's own closed-loop signal: recurrence-suppression rate (§9) + injected-tokens/session.

---

## 11. Premise defense (answer the threat, don't dodge)

"Opus 4.7 1M-token flat pricing makes *stuff-it-in-context* cheaper than a memory stack
under ~500K tokens." Rebuttal:
- paw's axis is **not storage cost** — it's **attention budget / context-rot** (Anthropic:
  token usage ≈ 80% of perf variance → more tokens = worse reasoning *even when cheap*).
- 1M-flat is Claude-only; **Codex/Gemini load-all still pay idle.**
- stuffing context **doesn't solve portability** — paw's moat is cross-host. Holds.

paw memory = context-rot preventer + cross-host, NOT cheap storage.

---

## 12. Prior-art — port the algorithm, never pull the service

| source | port | reject (why) |
|---|---|---|
| Letta/MemGPT | tiered paging (Core/Recall/Archival = hot/warm/cold) | the framework/server |
| Zep/Graphiti | temporal/confidence dimension | the graph DB service |
| mem0 | extract + dedup + consolidation | hosted store |
| FadeMem | ACT-R decay formula | — |
| Anthropic "Dreaming" | async consolidation pass | (managed-only) |
| headroom `learn` | failed-session → file capture shape | — |
| RAG-Anything | (nothing) | cloud LLM+embed API, multimodal doc-RAG ≠ code-memory, framework swallows the layer |

All rejected as runtime deps for the same reason: daemon / cloud-API / service-weight
violates paw's local-first, no-daemon, offline ethos. paw assembles a lean local-first
version of the pattern these services validated.

---

## 13. Open questions (resolve before/at /plan)

- [ ] Stop-hook capture: how to reliably detect "failure→fix" from a session transcript
      cross-host (the CC mistake hook's heuristics may not port cleanly to Codex/Gemini).
- [ ] `applicability` inference: rules for auto-tagging new lessons universal/stack/project.
- [ ] hot-tier eviction: fixed activation threshold vs budget-adaptive.
- [ ] codegraph node-id reconciliation after re-index (anchor repair).

## 14. Build order (for /plan)

1. Entry store + schema (jsonl+md, `.paw/memory/`, global + project) — pure, testable.
2. Compressed-entry format + progressive disclosure (R8).
3. Retrieval: path+symbol anchor + kernel reuse + rank (relevance×confidence×ACT-R).
   codegraph multi-hop = optional path.
4. Injection via L2 router (reuse) — silence-biased, per-type threshold, budget cap.
5. Lesson Stop-hook capture (CC first) → applicability tag → store.
6. Async consolidation pass (extend mistakes-sweep): dedup, promote, decay, archive.
7. Integrity gate + confirm-on-project-write.
8. project-memory seed + ADR-harvest (v1).
9. Port capture to Codex/Gemini (the portability moat).
10. Eval harness (recurrence-suppression + LongMemEval/LOCOMO reference).
```
```
