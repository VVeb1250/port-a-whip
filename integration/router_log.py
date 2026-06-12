"""Outcome-aware fire log + duplicate cooldown for skill-router v2.

Two jobs, both fail-silent (any error -> no-op, never affects routing):

1. **Cooldown** -- suppress identical back-to-back suggestions within a session.
   A different suggestion (or new session) resets it, so a genuinely new signal
   still fires; only literal repeats are muted.

2. **Outcome log** -- record every fire (privacy-safe: prompt sha8 + length, never
   raw text) as *pending*; on the next fire in the same session, settle the prior
   fire by scanning the transcript for whether any suggested skill was actually
   touched afterward (a slash invoke, a Read of its SKILL.md, or an MCP/tool call).
   "Touched" is a noisy proxy (Read-pointer skills get absorbed without an explicit
   call) -- use the log as an aggregate directional signal, not per-instance truth.

3. **Demotion** (2026-06-12) -- the aggregate read of that same settled log:
   `demotion()` returns (hard blacklist, soft-demote set) so the router can stop
   surfacing chronic noise. Mirrors paw's L2 outcome loop (portaw.memory.outcomes
   `demoted_names`: suggested >= N & used == 0) but stays SOFT for the data-driven
   set, because the "used" proxy above UNDERCOUNTS (a Read-absorbed ecc skill
   leaves no logged call). Soft = reversible score penalty; any future "used"
   clears it. Only the human-asserted blacklist (a mode toggle like `caveman`,
   never a real suggestion) is a hard cut.

State: ~/.claude/hooks/.router-state.json  (per-session pending + last signature)
Log:   ~/.claude/hooks/.router-log.jsonl   (append-only settled records)
"""
from __future__ import annotations

import hashlib
import json
import os
import time

_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(_DIR, ".router-state.json")
LOG_PATH = os.path.join(_DIR, ".router-log.jsonl")
MAX_SESSIONS = 50          # cap state file growth
MAX_LOG_BYTES = 2 * 1024 * 1024  # stop appending past 2 MB (analysis sample is plenty)

DEMOTE_MIN_SUGGESTED = 6   # suggested >= this with 0 uses -> soft-demote (config-overridable)
DEMOTE_PENALTY = 0.5       # multiply a demoted skill's score (config-overridable)


def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:8]


def signature(fired_keys, suggested) -> str:
    """Stable id of a suggestion: which signals fired + the top suggested skill."""
    top = suggested[0] if suggested else ""
    return _sha8("|".join(sorted(fired_keys)) + "::" + top)


def _load_state() -> dict:
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            st = json.load(f)
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(st: dict) -> None:
    if len(st) > MAX_SESSIONS:  # drop oldest sessions by pending ts
        items = sorted(st.items(), key=lambda kv: (kv[1] or {}).get("ts", 0))
        st = dict(items[-MAX_SESSIONS:])
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
    except OSError:
        pass


def _events_text(events) -> str:
    """User-driven text only (prompts + tool inputs); excludes assistant prose so
    the suggestion echo can't self-match as 'used'."""
    out = []
    for ev in events:
        etype = ev.get("type")
        msg = ev.get("message") if isinstance(ev.get("message"), dict) else {}
        content = msg.get("content", ev.get("content"))
        if etype == "user" and isinstance(content, str):
            out.append(content)
        elif isinstance(content, list):
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    out.append(str(b.get("name") or ""))
                    inp = b.get("input")
                    if isinstance(inp, dict):
                        for k in ("file_path", "command", "path", "pattern"):
                            v = inp.get(k)
                            if isinstance(v, str):
                                out.append(v)
                elif b.get("type") == "text" and etype == "user" and isinstance(b.get("text"), str):
                    out.append(b["text"])
    return " ".join(out).lower()


def _settle(pending: dict, events) -> bool:
    """True if any suggested skill looks used in the (post-fire) transcript."""
    names = pending.get("suggested") or []
    if not names:
        return False
    hay = _events_text(events)
    for nm in names:
        n = str(nm).lower()
        if n and (("/" + n) in hay or n in hay):
            return True
    return False


def _append_log(record: dict) -> None:
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_LOG_BYTES:
            return
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def gate(session_id, prompt, fired_keys, strength, primer, suggested, events) -> bool:
    """Settle the prior fire, log it, and decide whether THIS fire is a duplicate.

    Returns True if the caller should SUPPRESS output (identical back-to-back
    suggestion). Best-effort: on any error returns False (never suppresses)."""
    try:
        sid = str(session_id or "_")
        st = _load_state()
        sess = st.get(sid) if isinstance(st.get(sid), dict) else {}

        # 1. settle the previous pending fire (now that a turn has passed)
        pending = sess.get("pending")
        if isinstance(pending, dict):
            pending["outcome"] = "used" if _settle(pending, events) else "ignored"
            _append_log(pending)

        sig = signature(fired_keys, suggested)

        # 2. cooldown: identical consecutive suggestion -> suppress, keep state
        if sig == sess.get("last_sig"):
            sess["pending"] = None  # nothing shown -> nothing to settle next time
            st[sid] = sess
            _save_state(st)
            return True

        # 3. fresh suggestion: record as pending, advance signature
        sess["last_sig"] = sig
        sess["ts"] = time.time()
        sess["pending"] = {
            "ts": time.time(),
            "session": _sha8(sid),
            "plen": len(prompt or ""),
            "phash": _sha8(prompt or ""),
            "fired": list(fired_keys),
            "strength": round(float(strength), 3),
            "primer": bool(primer),
            "suggested": list(suggested),
            "outcome": None,
        }
        st[sid] = sess
        _save_state(st)
        return False
    except Exception:
        return False


def aggregate() -> dict:
    """Tally the SETTLED log into {name: [suggested, used]}. {} on any error.

    Only records with a settled outcome ('used'/'ignored') count — a still-pending
    fire (outcome None) hasn't been judged yet and is skipped so it can't inflate
    the ignored side before its turn passes."""
    agg: dict[str, list] = {}
    try:
        if not os.path.exists(LOG_PATH):
            return agg
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                outcome = r.get("outcome")
                if outcome not in ("used", "ignored"):
                    continue
                for nm in (r.get("suggested") or []):
                    a = agg.setdefault(nm, [0, 0])
                    a[0] += 1
                    if outcome == "used":
                        a[1] += 1
    except OSError:
        pass
    return agg


def demotion(graph) -> tuple[set, set, float]:
    """Outcome-aware suppression sets for the router. Returns (blacklist, demote, penalty).

    - blacklist (HARD cut): names listed in skill-graph.json `demote.blacklist`.
      Human-asserted noise (a mode toggle like `caveman` that is active-by-default
      and is never a legitimate suggestion). Dropped outright.
    - demote (SOFT, reversible): data-driven — suggested >= min_suggested AND used == 0
      in the settled log. The caller multiplies the score by `penalty`, so a demoted
      skill only surfaces on a strong match and any future logged 'used' clears it.
      Soft on purpose: the 'used' proxy undercounts Read-absorbed skills, so the log
      alone must never permanently kill a candidate.

    Fail-safe: any error -> ([], [], default penalty) so routing is never affected."""
    cfg = (graph.get("demote") if isinstance(graph, dict) else None) or {}
    blacklist = set(cfg.get("blacklist") or [])
    try:
        min_sug = int(cfg.get("min_suggested", DEMOTE_MIN_SUGGESTED))
    except (TypeError, ValueError):
        min_sug = DEMOTE_MIN_SUGGESTED
    try:
        penalty = float(cfg.get("penalty", DEMOTE_PENALTY))
    except (TypeError, ValueError):
        penalty = DEMOTE_PENALTY
    demote: set = set()
    try:
        for nm, (sug, used) in aggregate().items():
            if used == 0 and sug >= min_sug and nm not in blacklist:
                demote.add(nm)
    except Exception:
        pass
    return blacklist, demote, penalty
