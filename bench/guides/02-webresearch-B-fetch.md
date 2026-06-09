# Bench session 02 — web-research LANE B (Fetch MCP)

You are a FRESH agent with no prior context. Do EXACTLY the steps below, then STOP
and report. Keep it byte-identical to the other lanes — only the fetch tool differs.

## Precondition (the user did this before starting you)
`portaw install web-research --host claude-code` has patched the **Fetch MCP**
server (`uvx mcp-server-fetch`). The `fetch` MCP tool must be available. If it is
NOT, stop and tell the user to install it first — do not fall back to native fetch.

## Tool constraint
Use the **`fetch` MCP tool** for every fetch. Do NOT use native web-fetch,
Scrapling, or curl. Leave `max_length` at its default (5000) — do not raise it.

## Steps
1. Create `bench/out/` if missing.
2. For EACH URL, call the `fetch` MCP tool and SAVE its verbatim return:
   - `https://peps.python.org/pep-0008/` → `bench/out/fetch-1.md`
   - `https://docs.python.org/3/library/json.html` → `bench/out/fetch-2.md`
   - `https://raw.githubusercontent.com/pallets/click/main/README.md` → `bench/out/fetch-3.md`
   Save the RAW tool return (what entered context). If a page was truncated at
   max_length, save what you got — do NOT paginate with start_index (keep it equal
   to native's single-shot; pagination would change the workload).
3. From ONLY those contents, answer in order (completeness gate):
   1. PEP 8: max line length + binary-operator line-break guidance.
   2. `json.dumps()` parameters + one sentence each.
   3. click README: one-sentence self-description + the pip install command.
4. No other URL. No editing code files.

## Report then STOP
- Confirm `bench/out/fetch-1.md`, `-2.md`, `-3.md` written.
- Y/N you fully answered each of the 3 (completeness gate). If truncation caused an
  N, say so explicitly — that is a REAL finding (Fetch's max_length lost content).
- Tell the user: "Lane B trial done — `portaw bench list --agent claude` for the id." STOP.

> 3 fresh trials total. Same model, cold cache (new session, >5 min apart).
