# Bench session 10 — set install-tests (DRAFT → verified)

NOT an A/B — no token measurement, no session isolation. This is a single session
that installs each set on a real host and confirms the health-gate passes. Goal:
flip `verified.status` for these sets from DRAFT to verified in registry/sets.json.

You may run all three in one session. For each: install → run the printed manual
shim steps → `portaw verify` → record the result.

## A. design-quality (impeccable = keyless, the testable anchor)
```
npx impeccable skills install
# then on a REAL frontend file/dir:
npx impeccable detect src/      # or the /impeccable audit slash command
portaw verify design-quality
```
- Confirm impeccable installed + actually flags real slop on a frontend.
- figtree-cli is OPTIONAL (needs FIGMA_TOKEN in .env, NEVER hardcode) — skip unless
  you work from Figma. `portaw verify` will report figtree "missing" if not
  installed; that's expected, not a failure of the keyless core.
- Result → sets.json design-quality `verified.status` DRAFT → verified (note
  impeccable verified, figtree optional/untested).

## B. secure-agent (4 CLI/hook tools, 0 MCP)
```
portaw install secure-agent --host claude-code   # prints manual shim steps
# run the printed installs: nah, gitleaks, osv-scanner, infisical
portaw verify secure-agent
```
- Gate PASSES when nah/gitleaks/osv-scanner/infisical resolve on PATH.
- nah is Claude-Code-only today; on other hosts the 3 CLIs still verify.
- Result → sets.json secure-agent `verified.hosts`.

## C. context-quality (Context7 MCP)
```
portaw install context-quality --host claude-code   # patches Context7 MCP
portaw verify context-quality
```
- Context7 has no health_binary → `verify` reports it config-only (gate passes);
  to truly confirm, open a fresh session and check the `mcp__context7__*` tools
  appear + answer a "latest API for <lib>" question.
- Result → sets.json context-quality `verified.hosts`.

## Report
For each set: installed? verify gate PASS/FAIL? what (if anything) was missing?
Then update each set's `verified` block in registry/sets.json accordingly.

> SECURITY: install steps run vendor CLIs (curated, pinned). Never paste a secret
> in plaintext — Figma/any token goes in .env as ${VAR}. Don't pair secure-agent's
> nah with `--dangerously-skip-permissions` (bypasses the guard).
