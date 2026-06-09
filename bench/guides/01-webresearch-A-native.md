# Bench session 01 — web-research LANE A (native WebFetch, baseline)

You are a FRESH agent with no prior context. Do EXACTLY the steps below, nothing
more, then STOP and report. This is one controlled trial — keep it byte-identical
to the other trials.

## Tool constraint
Use your built-in **native web-fetch** tool (its DEFAULT behavior). Do NOT use any
`fetch` MCP server, Scrapling, curl, or any other fetch path. If a Fetch MCP tool
is offered, ignore it — this lane measures native only.

## Steps
1. Create the output dir if missing: `bench/out/` (relative to repo root).
2. For EACH of these 3 URLs, in order, fetch it with the native tool and SAVE the
   tool's verbatim returned content to the matching file:
   - `https://peps.python.org/pep-0008/` → save return to `bench/out/native-1.md`
   - `https://docs.python.org/3/library/json.html` → `bench/out/native-2.md`
   - `https://raw.githubusercontent.com/pallets/click/main/README.md` → `bench/out/native-3.md`
   Save the RAW tool output you received (what entered your context), not a re-summary.
3. From ONLY those fetched contents, answer in order (completeness gate):
   1. PEP 8: max line length it recommends + what it says about breaking lines
      before/after a binary operator.
   2. json module: the parameters of `json.dumps()` + one sentence each.
   3. click README: one-sentence self-description + the pip install command shown.
4. Do NOT fetch any other URL. Do NOT edit code files.

## Report then STOP
- Confirm all 3 files written: `bench/out/native-1.md`, `-2.md`, `-3.md`.
- State whether you fully answered all 3 questions (Y/N each). If any N, say which
  page lacked the info — this is the completeness gate; a lane that can't answer is
  disqualified regardless of token count.
- Tell the user: "Lane A trial done — run `portaw bench list --agent claude` to
  grab this session id." Then STOP.

> Repeat this exact guide in 2 more fresh sessions (3 trials total). Cold cache:
> new session each, >5 min apart if back-to-back. Same model all trials.
