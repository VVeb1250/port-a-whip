# web-research A/B bench — ready-to-run workload (3 lanes)

Goal: get the HARD number (or an honest demotion) for **web-research** set #5 on
Claude Code. Blocks DRAFT → verified (DOGFOOD-PENDING #8).

> ⚠ BASELINE IS NOT "raw HTML". CC's native `WebFetch` already does
> URL → markdown → small-model **digest**, so nothing on CC emits a raw-HTML dump
> to beat. The old "Fetch clean-md vs raw-HTML" framing was a STRAWMAN — running
> it would either kill the set or rig a hollow win. The REAL question is
> **digested-answer (native) vs direct/targeted content (Fetch / Scrapling)**, and
> plain Fetch may LOSE to native WebFetch on CC. Measure honestly; the set's
> differentiated lever is **targeted/semantic extract**, not plain fetch.

> Why a fixed URL set: `bench ab` diffs two sessions. If the lanes fetch different
> pages or ask different questions, the delta is noise. Vary ONLY the fetch tool;
> keep URLs + questions byte-identical across all three lanes.

## The three lanes

| Lane | Tool | What enters main context |
|---|---|---|
| **A (baseline)** | native `WebFetch` DEFAULT behavior | a small-model **digest** of each page (you don't control length) |
| **B** | **Fetch MCP** (`uvx mcp-server-fetch`) | up to `max_length` chars of page-as-markdown |
| **C** | **Scrapling** targeted extract (CLI) | only the css-selected slice (`extract fetch --css-selector`) |

Lane A is what the user gets for FREE on CC. B and C must BEAT it (fewer tokens
into context AND the answer still complete) to justify the set on CC.

## Fixed inputs (identical every lane)

URLs (stable, content-heavy, low-JS so all three tools can read them):
```
https://peps.python.org/pep-0008/
https://docs.python.org/3/library/json.html
https://raw.githubusercontent.com/pallets/click/main/README.md
```
Task (paste verbatim, same in all 3 lanes):
```
Using ONLY the three URLs below, answer in order, no commentary between:
  https://peps.python.org/pep-0008/
  https://docs.python.org/3/library/json.html
  https://raw.githubusercontent.com/pallets/click/main/README.md
1. PEP 8: what is the max line length it recommends, and what does it say about
   breaking lines before/after a binary operator?
2. json module: list the parameters of json.dumps() and one sentence each.
3. click README: what does the project describe itself as, in one sentence, and
   what is the pip install command shown?
Stop after step 3. Do not fetch any other URL. Do not edit files.
```
The questions force the agent to actually pull each page's content — same work
every lane, so the only variable is the fetch tool ⇒ valid A/B.

## Setup per lane

- **A — native:** nothing to install. Ensure NO Fetch MCP server is active and
  the agent is told to use its built-in web fetch. Fresh session.
- **B — Fetch MCP:** install + patch, then fresh session:
  ```
  uvx mcp-server-fetch --help    # confirm uvx fetches it
  portaw install web-research --host claude-code   # patches Fetch MCP server
  ```
  In the run, the agent should call the `fetch` MCP tool (not native WebFetch).
- **C — Scrapling CLI:** install once, then fresh session:
  ```
  pip install "scrapling[all]" && scrapling install
  # agent runs, per URL: scrapling extract fetch '<URL>' out.md --css-selector '<sel>'
  ```
  Pick a tight selector per page (e.g. PEP body `#pep-content`, json doc
  `div[role=main]`, README raw = whole file). Same selectors if you re-run.

## Run + diff

```
portaw bench list --agent claude     # grab the three newest session ids
portaw bench ab <A_id> <B_id>        # native (baseline) → Fetch MCP (treated)
portaw bench ab <A_id> <C_id>        # native (baseline) → Scrapling (treated)
```
Positive `saved` on totalTokens / inputTokens / cacheCreationTokens = the treated
lane put LESS into context than native's digest. Negative = it LOST to native.

## Pre-decided DECISION on the result (don't re-litigate)

- **If Fetch (B) ≤ native (A) on CC** → **demote Fetch on CC**: keep it as the
  keyless anchor ONLY on load-all hosts (Codex/Gemini lack a native digest-fetch),
  and lead the CC set value with the additive rungs (C/exa). Set
  `token_profile.hosts.claude-code` = the additive-rung number, note Fetch demoted.
- **If Scrapling (C) beats native** → that targeted-extract delta IS the CC lever.
  Record it as CC `delta_pct`, provenance `measured`.
- Either way: fill CC `delta_pct` (or the demotion note) and flip
  `verified.status` DRAFT → verified once captured.

Result lands in `registry/sets.json` web-research `token_profile.hosts.claude-code`
+ `verified`; note the call in `registry/deep-vet.md` (web-research section).

## Caveats

- **Same model all three lanes** (ccusage tags model; mixing Opus/Sonnet skews tokens).
- **Completeness gate (the honesty knife):** a lane that uses fewer tokens but
  DROPS needed content (couldn't answer step 1/2/3) is NOT a win. Sanity-check all
  three lanes answered identically-correct before trusting the token delta.
- **URLs can drift** — if a page changes between lanes, re-run all three the same
  day so the content matches. Pin the click README to `main` raw (above) so it's a
  fixed byte stream, not a rendered GitHub HTML page that changes chrome.
- Measures tokens INTO the main session, not sub-model cost. Native WebFetch's
  digest runs in a cheap side model — that's exactly WHY it's a hard baseline on CC.
- This is the CC lane only. On load-all hosts (Codex/Gemini) the lever is different
  (Fetch's 259-tok idle buys a capability those hosts lack natively) — already
  `calculated`, no run needed.
