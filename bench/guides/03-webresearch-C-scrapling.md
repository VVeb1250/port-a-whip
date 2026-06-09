# Bench session 03 — web-research LANE C (Scrapling targeted extract)

You are a FRESH agent with no prior context. Do EXACTLY the steps below, then STOP
and report. Only the fetch tool differs from the other lanes.

## Precondition (the user did this before starting you)
`pip install "scrapling[all]" && scrapling install` is done. The `scrapling` CLI
must be on PATH. If not, stop and tell the user — do not fall back to another tool.

## Tool constraint
Use the **Scrapling CLI** targeted extract for every fetch. This lane's whole point
is pulling ONLY the relevant slice via a css-selector (fewer tokens than a full
page). Do NOT use native fetch or the Fetch MCP.

## Steps
1. Create `bench/out/` if missing.
2. Extract each URL into its file with a TIGHT selector (these selectors are fixed —
   reuse them every trial so the workload is identical):
   ```
   scrapling extract fetch 'https://peps.python.org/pep-0008/' bench/out/scrapling-1.md --css-selector '#pep-content'
   scrapling extract fetch 'https://docs.python.org/3/library/json.html' bench/out/scrapling-2.md --css-selector 'section#module-json'
   scrapling extract get 'https://raw.githubusercontent.com/pallets/click/main/README.md' bench/out/scrapling-3.md
   ```
   (URL 3 is raw markdown with no HTML structure → plain `get`, no selector.)
   If a selector returns empty (site markup changed), fall back to `extract fetch
   '<URL>' <file>` with NO selector and NOTE it in your report — a changed selector
   invalidates the trial's targeting, the user must re-pick it.
3. From ONLY the extracted files, answer in order (completeness gate):
   1. PEP 8: max line length + binary-operator line-break guidance.
   2. `json.dumps()` parameters + one sentence each.
   3. click README: one-sentence self-description + the pip install command.
4. No other URL. No editing code files.

## Report then STOP
- Confirm `bench/out/scrapling-1.md`, `-2.md`, `-3.md` written + which selector each
  used (flag any fallback).
- Y/N you fully answered each of the 3. If a tight selector dropped needed content
  (e.g. couldn't find a json.dumps param), that's a REAL finding — targeted extract
  traded completeness for tokens. Say so.
- Tell the user: "Lane C trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials total. Same model, cold cache.
