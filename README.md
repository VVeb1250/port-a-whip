# 🐾 port-a-whip (paw)

> Curated sets + capability router + lesson-memory for **coding agents** — Claude Code, Codex, Gemini CLI. Zero runtime dependency.

```bash
pip install port-a-whip
portaw install efficiency-starter
```

> **Status: pre-alpha (v0.3, design + scaffold).** Spec is source of truth → [port-a-whip-spec.md](port-a-whip-spec.md). CLI shell runs; install/router bodies are Phase-1 stubs.

## What it is

Three layers, one criterion — *reduce tokens OR improve context quality*:

1. **Curated sets** — bundles (MCP + non-MCP) vetted to be quality **and** actually compatible together. One command installs the whole set into your host's config.
2. **Capability router** — per-prompt, surfaces which skill / tool / instruction to use. Token-lean.
3. **Lesson-memory** — captures mistakes, surfaces relevant ones across hosts.

## What it isn't

A general MCP installer/registry — Smithery / mcpm / MCPDog already do cross-host install + thousands of tools. paw adds only what they don't: vetted *combos*, non-MCP tools, per-prompt routing, cross-host lessons. For single tools, use Smithery directly.

paw patches host config itself (JSON `mcpServers` / Codex TOML `[mcp_servers.<name>]`) — no Smithery, no daemon, offline-capable.

## Commands

```bash
portaw sets list                 # browse curated sets
portaw sets show <set>           # tools + token profile + compat notes
portaw install <set> [--host X]  # patcher (MCP config) + shim (index build / non-MCP)
portaw remove <set>              # un-patch config + reverse shim
portaw doctor                    # env + host detect + config parse-valid?
portaw router enable | status    # capability router
```

## First set: `efficiency-starter`

| Layer | Tool | Does |
|---|---|---|
| MCP | [codegraph](https://github.com/colbymchenry/codegraph) | pre-indexed local code graph — fewer tokens, fewer tool calls |
| non-MCP | [rtk](https://github.com/rtk-ai/rtk) | PreToolUse hook, compresses shell output 60–90% |

Different layers, no hook collision. Full-set hosts: claude-code, gemini, cursor.

## Host support

| Host | per-prompt inject | tier |
|---|---|---|
| Claude Code | ✅ `UserPromptSubmit` | 1 |
| Codex CLI | ✅ `UserPromptSubmit` | 1 |
| Gemini CLI | ✅ `BeforeAgent` | 1 |
| Cursor / OpenCode | ⚠️ static only | 2 |

## By whipforaweep
