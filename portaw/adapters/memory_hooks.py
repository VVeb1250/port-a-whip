"""L3 live-inject hooks beyond UserPromptSubmit (P1–P3, 2026-06-11).

Each host event carries a DIFFERENT signal, so each gets its own narrow surface:

  • SessionStart  → ``run_session_hook``: inject the PINNED tier once per session
    (the always-on guarantee that replaces an auto-loaded rules file 1:1).
    ``source=compact|clear`` resets the dedup log first — compaction summarized
    the earlier injects away, so pins must re-fire.
  • PostToolUse   → ``run_tool_hook``:
      Bash + a FAILED result   → error-triggered recall (the fix arrives while the
                                 mistake is happening — highest-precision surface).
      Edit/Write/MultiEdit     → anchor recall on the touched file (the structural
                                 half of retrieval; prompt-time recall can't see it).

Shared contract with run_hook: stdin = host JSON envelope, output = JSON with
``hookSpecificOutput.additionalContext``, ANY error → None (never block the host).
All surfaces share the session dedup log — one lesson injects once per session.
"""

from __future__ import annotations

import json
import re
import sys

# stderr markers that say "this Bash call actually FAILED" (tool_response carries
# no exit code on every host) — precision gate so warnings alone never trigger.
# Boundaries matter: bare `ERROR` matched inside "0 ERRORS" and `cannot ` matched
# any prose ("cannot guarantee…") — output that merely TALKS about errors must
# not fire a failure recall.
_FAIL_RE = re.compile(
    r"command not found|not recognized|No such file|Traceback|"
    r"fatal:|error:|Error:|\bERROR\b|\bdenied\b|cannot (?:find|access|open|stat)",
    re.ASCII,
)
_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_MAX_ERR_CHARS = 800  # route on the error's head — tails are stack-frame noise
_NUDGE_MIN = 2        # an un-lessoned error seen this many times → prompt to capture


def _payload(stdin_text: str | None) -> dict:
    raw = stdin_text
    if raw is None:
        raw = sys.stdin.buffer.read().decode("utf-8", "ignore") if not sys.stdin.isatty() else ""
    try:
        out = json.loads(raw) if raw.strip() else {}
        return out if isinstance(out, dict) else {}
    except ValueError:
        return {}


def _envelope(event: str, text: str) -> str:
    return json.dumps(
        {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}},
        ensure_ascii=False,
    )


# ----------------------------------------------------------------- SessionStart

def run_session_hook(stdin_text: str | None = None) -> str | None:
    """Inject eligible pinned lessons once per session. None = silent."""
    try:
        from portaw.memory import sessionlog
        from portaw.memory.context import host_context
        from portaw.memory.inject import format_session, session_select
        from portaw.memory.store import load_lessons

        p = _payload(stdin_text)
        sid = p.get("session_id") or ""
        if p.get("source") in ("compact", "clear"):
            sessionlog.reset(sid)  # earlier injects got summarized — pins re-fire

        selected = session_select(load_lessons(), ctx=host_context(p.get("cwd") or None))
        if sid:
            already = sessionlog.seen(sid)
            selected = [e for e in selected if e.id not in already]
        if not selected:
            return None
        if sid:
            sessionlog.mark(sid, [e.id for e in selected])
        return _envelope("SessionStart", format_session(selected))
    except Exception:
        return None


# ----------------------------------------------------------------- PostToolUse

def _error_text(resp) -> str:
    """Pull failure text out of a tool_response (shape varies; '' = no failure)."""
    if isinstance(resp, dict):
        parts = [str(resp.get(k) or "") for k in ("stderr", "error", "message")]
        if resp.get("is_error") or resp.get("success") is False:
            parts.append(str(resp.get("stdout") or ""))
        text = "\n".join(x for x in parts if x).strip()
    elif isinstance(resp, str):
        text = resp.strip()
    else:
        return ""
    if not text or not _FAIL_RE.search(text):
        return ""  # warnings/no signal → silent (precision over recall here)
    return text[:_MAX_ERR_CHARS]


def _covering(selected, prog: str):
    """The first selected lesson that GENUINELY covers a `prog` error — prog appears
    in its trigger_terms or body. No prog / no genuine match → None (treat as
    un-lessoned, so a fuzzy token overlap can't suppress a real capture nudge)."""
    if not prog:
        return selected[0] if selected else None
    from portaw.kernel.ranking import tokenize

    for s in selected:
        terms = {t.lower() for t in s.entry.trigger_terms} | set(tokenize(s.entry.body))
        if prog in terms:
            return s
    return None


def _nudge_block(sig: str, count: int) -> str:
    return (f"⚠️ paw: hit `{sig}` ×{count} this session with no lesson — "
            f"if you know the fix, capture it: "
            f"`portaw memory add \"<trigger> → <fix>\" --trigger <term>`")


def run_tool_hook(stdin_text: str | None = None) -> str | None:
    """PostToolUse dispatch: Bash failure → error recall (+observation ledger +
    repeat-nudge); Edit/Write → anchor recall."""
    try:
        p = _payload(stdin_text)
        tool = p.get("tool_name") or ""
        tin = p.get("tool_input") if isinstance(p.get("tool_input"), dict) else {}
        if tool == "Bash":
            return _bash_hook(p, tin)
        if tool in _EDIT_TOOLS:
            return _edit_hook(p, tin)
        return None
    except Exception:
        return None


def _recall_selected(query_prompt, query, p, sid):
    """Shared recall→dedup→evidence-filter→mark. Returns selected Scored list."""
    from portaw.memory import sessionlog
    from portaw.memory.context import host_context
    from portaw.memory.inject import select
    from portaw.memory.retrieval import recall
    from portaw.memory.store import load_lessons, load_project

    entries = load_lessons() + load_project()
    if not entries:
        return []
    # no embed_fn here: error strings + paths match lexically/structurally;
    # keeping ONNX out of the per-tool-call path is the latency budget.
    scored = recall(query_prompt, entries, query=query,
                    ctx=host_context(p.get("cwd") or None))
    already = sessionlog.seen(sid) if sid else set()
    # tool-surface is opportunistic, not the pinned tier: only entries this event
    # actually evidenced (base > 0) belong — a floor-bypassing pin would otherwise
    # ride through on every tool call.
    selected = [s for s in select([s for s in scored if s.entry.id not in already])
                if s.base > 0]
    return selected


def _bash_hook(p: dict, tin: dict) -> str | None:
    from portaw.memory import observations, sessionlog

    err = _error_text(p.get("tool_response"))
    if not err:
        return None
    sid = p.get("session_id") or ""
    selected = _recall_selected(err, None, p, sid)

    # COVERAGE must be strict: an error-recall can fuzzy-match a lesson on shared
    # generic tokens ("command not found"), so a `foobar` error must NOT count the
    # `python` lesson as its cover. A lesson covers this error only if the failing
    # program token actually appears in it — otherwise it's un-lessoned (→ nudge).
    command = str(tin.get("command") or "")
    prog = observations.program(command)
    covering = _covering(selected, prog)

    # ledger: count this failure; link the genuinely-covering lesson (if any) so its
    # effectiveness can be measured later (confidence.py / `memory observations`).
    rec = observations.record(command, err, lesson_id=covering.entry.id if covering else "")

    if covering:
        from portaw.memory.inject import format_memory
        if sid:
            sessionlog.mark(sid, [covering.entry.id])
        return _envelope("PostToolUse", format_memory([covering]))

    # no lesson covers a repeated error → nudge to capture (once per sig per session)
    if rec and not rec.get("lesson_id") and rec.get("count", 0) >= _NUDGE_MIN:
        key = f"nudge:{rec['sig']}"
        if not sid or key not in sessionlog.seen(sid):
            if sid:
                sessionlog.mark(sid, [key])
            return _envelope("PostToolUse", _nudge_block(rec["sig"], rec["count"]))
    return None


def _edit_hook(p: dict, tin: dict) -> str | None:
    from portaw.memory import sessionlog
    from portaw.memory.anchors import AnchorQuery
    from portaw.memory.inject import format_memory

    fp = str(tin.get("file_path") or tin.get("notebook_path") or "")
    if not fp:
        return None
    sid = p.get("session_id") or ""
    selected = _recall_selected("", AnchorQuery(paths=(fp,)), p, sid)
    if not selected:
        return None
    if sid:
        sessionlog.mark(sid, [s.entry.id for s in selected])
    return _envelope("PostToolUse", format_memory(selected))
