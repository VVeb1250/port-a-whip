"""B1 token-delta bench — wraps ccusage (reuse, don't rebuild).

`portaw bench` answers ONE question with hard numbers, not vibes (spec §10):
how many tokens does a set/tool save? It does NOT invent numbers — it reads
the host's own session log via `ccusage` and diffs two runs.

Valid A/B requires a CONTROLLED workload: run the SAME task twice — once with
the tool off (baseline), once on — then diff the two sessions. paw supplies the
measurement; the operator supplies the identical workload. See `bench_protocol`.

Token fields (ccusage):
  totalTokens      = headline
  inputTokens      } rtk-class proxies compress command stdout → these drop
  cacheCreationTokens } (compressed output re-enters context as input/cache)
  outputTokens     = model generation (a tool rarely changes this)
  cacheReadTokens  = warm-cache reads

No new deps: stdlib subprocess + json. ccusage invoked via `npx -y ccusage`.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Literal

Agent = Literal["claude", "codex", "gemini"]

# Token keys we diff. Order = report order.
_TOKEN_KEYS = (
    "totalTokens",
    "inputTokens",
    "cacheCreationTokens",
    "cacheReadTokens",
    "outputTokens",
)


class CcusageError(RuntimeError):
    """ccusage missing or returned unparseable output."""


@dataclass(frozen=True)
class Session:
    """One ccusage session row, trimmed to what bench needs."""

    period: str  # session id (ccusage "period")
    agent: str
    last_activity: str
    total_cost: float
    tokens: dict[str, int]  # _TOKEN_KEYS → count

    @classmethod
    def from_raw(cls, raw: dict) -> Session:
        return cls(
            period=str(raw.get("period", "")),
            agent=str(raw.get("agent", "")),
            last_activity=str(raw.get("metadata", {}).get("lastActivity", "")),
            total_cost=float(raw.get("totalCost", 0.0)),
            tokens={k: int(raw.get(k, 0)) for k in _TOKEN_KEYS},
        )


def load_sessions(agent: Agent | None = None) -> list[Session]:
    """Run `ccusage session --json --offline` and parse rows.

    `agent` filters to one host (ccusage tags rows claude/codex/gemini).
    Raises CcusageError if ccusage is absent or output is malformed.
    """
    # Windows ships npx as `npx.cmd`; bare subprocess can't resolve it without the
    # shell. The command is a FIXED literal (no interpolation) → shell=True is safe.
    argv = ["npx", "-y", "ccusage@latest", "session", "--json", "--offline"]
    on_windows = os.name == "nt"
    cmd: str | list[str] = " ".join(argv) if on_windows else argv
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, check=False, shell=on_windows
        )
    except FileNotFoundError as e:  # npx not on PATH
        raise CcusageError("npx not found — install Node 18+ to use ccusage") from e
    except subprocess.TimeoutExpired as e:
        raise CcusageError("ccusage timed out after 120s") from e
    if proc.returncode != 0:
        raise CcusageError(f"ccusage exit {proc.returncode}: {proc.stderr.strip()[:200]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise CcusageError(f"ccusage output not JSON: {proc.stdout[:120]}") from e
    rows = data.get("session", [])
    sessions = [Session.from_raw(r) for r in rows]
    if agent:
        sessions = [s for s in sessions if s.agent == agent]
    return sessions


def find_session(sessions: list[Session], period_prefix: str) -> Session:
    """Match a session by period id prefix (8+ chars usually unique)."""
    hits = [s for s in sessions if s.period.startswith(period_prefix)]
    if not hits:
        raise CcusageError(f"no session matching '{period_prefix}'")
    if len(hits) > 1:
        ids = ", ".join(h.period[:8] for h in hits)
        raise CcusageError(f"ambiguous prefix '{period_prefix}' → {ids}")
    return hits[0]


def diff(baseline: Session, treated: Session) -> dict:
    """Token/cost delta baseline (off) → treated (on).

    Positive `saved` = treated used FEWER tokens. `pct` = saved / baseline.
    """
    out: dict = {"baseline": baseline.period[:8], "treated": treated.period[:8], "tokens": {}}
    for k in _TOKEN_KEYS:
        b, t = baseline.tokens[k], treated.tokens[k]
        saved = b - t
        pct = (saved / b * 100.0) if b else 0.0
        out["tokens"][k] = {"baseline": b, "treated": t, "saved": saved, "pct": round(pct, 1)}
    cost_saved = baseline.total_cost - treated.total_cost
    out["cost"] = {
        "baseline": round(baseline.total_cost, 4),
        "treated": round(treated.total_cost, 4),
        "saved": round(cost_saved, 4),
    }
    return out


def bench_protocol() -> str:
    """How to produce a VALID A/B (printed by `portaw bench --how`)."""
    return (
        "A/B bench protocol (controlled workload required):\n"
        "  1. Pick a fixed, repeatable task (e.g. a scripted set of git/test/build commands).\n"
        "  2. Run it with the tool OFF (baseline). Note the session id (ccusage period).\n"
        "  3. Run the SAME task with the tool ON (treated). Note its session id.\n"
        "  4. portaw bench --ab <baseline_id> <treated_id>\n"
        "Caveat: different workloads = invalid comparison. Keep the task identical;\n"
        "vary ONLY the tool. For proxies (rtk-class) the delta lands in input/\n"
        "cacheCreation tokens (compressed command output re-entering context)."
    )


def format_report(d: dict) -> str:
    """Human-readable diff table."""
    lines = [
        f"bench: {d['baseline']} (off) → {d['treated']} (on)",
        f"{'metric':<22}{'baseline':>14}{'treated':>14}{'saved':>14}{'pct':>8}",
    ]
    for k in _TOKEN_KEYS:
        t = d["tokens"][k]
        lines.append(
            f"{k:<22}{t['baseline']:>14,}{t['treated']:>14,}{t['saved']:>14,}{t['pct']:>7}%"
        )
    c = d["cost"]
    lines.append(f"{'cost (USD)':<22}{c['baseline']:>14}{c['treated']:>14}{c['saved']:>14}")
    return "\n".join(lines)
