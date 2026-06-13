"""Per-set token attribution — the install date as a built-in A/B anchor.

`portaw bench --ab` needs the operator to pick two session ids by hand. This
closes the gap the known-issues list calls out (#3 gain ledger, PARTIAL): paw
ALREADY records when it installed a set (the state ledger), so it can split the
host's own ccusage sessions at that date — sessions before vs after — and report
the per-session token delta automatically.

HONESTY (this is the whole point of paw's bench): this is DIRECTIONAL, never
`measured`. The two windows are NOT a controlled workload — they are whatever the
user happened to do before and after install — so a single number would lie. So:
  • report n sessions each side; refuse (inconclusive) below `MIN_SIDE`;
  • report the MEDIAN per-session totals (robust to one giant session), with the
    spread, so a delta smaller than the spread reads as noise, not a win;
  • label the verdict directional + tell the reader to run `bench --ab` on a
    controlled task to upgrade it to `measured`.

No new deps: reuses `bench.load_sessions` (ccusage) + `state` (install dates).
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from portaw import bench
from portaw.sets import state

MIN_SIDE = 2  # fewer sessions than this on either side → inconclusive, not a number


@dataclass(frozen=True)
class GainReport:
    set_name: str
    host: str
    agent: str
    install_date: str
    before_n: int
    after_n: int
    before_median: float
    after_median: float
    before_spread: tuple[int, int]   # (min, max) per-session totalTokens
    after_spread: tuple[int, int]
    conclusive: bool
    note: str

    @property
    def saved_per_session(self) -> float:
        return self.before_median - self.after_median

    @property
    def pct(self) -> float:
        return (self.saved_per_session / self.before_median * 100.0) if self.before_median else 0.0


def _install_date(set_name: str, host: str) -> str | None:
    rec = state.installed_sets(host).get(set_name)
    return rec.get("date") if rec else None


def _session_day(s: bench.Session) -> str:
    """ccusage lastActivity → YYYY-MM-DD (date-only compare against install date)."""
    return (s.last_activity or "")[:10]


def gain_for_set(
    set_name: str,
    *,
    host: str = "claude-code",
    agent: bench.Agent = "claude",
    sessions: list[bench.Session] | None = None,
) -> GainReport:
    """Split the host's sessions at the set's install date → directional delta.

    Raises ``bench.CcusageError`` if ccusage is unavailable, ``ValueError`` if the
    set was never installed by paw on this host (no anchor date to split on).
    """
    install_date = _install_date(set_name, host)
    if not install_date:
        raise ValueError(
            f"'{set_name}' is not paw-installed on {host} — no install date to split on. "
            f"Install it (`portaw install {set_name}`) or use `portaw bench --ab` with two "
            f"session ids."
        )
    rows = sessions if sessions is not None else bench.load_sessions(agent)
    before = [s.tokens["totalTokens"] for s in rows
              if _session_day(s) and _session_day(s) < install_date]
    after = [s.tokens["totalTokens"] for s in rows
             if _session_day(s) and _session_day(s) >= install_date]

    conclusive = len(before) >= MIN_SIDE and len(after) >= MIN_SIDE
    note = (
        f"directional only (n={len(before)} before / {len(after)} after, uncontrolled "
        f"workloads). Run `portaw bench --ab` on an identical task to upgrade to measured."
        if conclusive else
        f"INCONCLUSIVE: need ≥{MIN_SIDE} sessions each side (have {len(before)} before / "
        f"{len(after)} after). Keep using the host past the install date, then re-run."
    )
    return GainReport(
        set_name=set_name, host=host, agent=agent, install_date=install_date,
        before_n=len(before), after_n=len(after),
        before_median=median(before) if before else 0.0,
        after_median=median(after) if after else 0.0,
        before_spread=(min(before), max(before)) if before else (0, 0),
        after_spread=(min(after), max(after)) if after else (0, 0),
        conclusive=conclusive, note=note,
    )


def format_report(r: GainReport) -> str:
    lines = [
        f"gain: {r.set_name} on {r.host} (installed {r.install_date}) — agent={r.agent}",
        f"  before: n={r.before_n:<3} median {r.before_median:>12,.0f} tok/session "
        f"(range {r.before_spread[0]:,}–{r.before_spread[1]:,})",
        f"  after : n={r.after_n:<3} median {r.after_median:>12,.0f} tok/session "
        f"(range {r.after_spread[0]:,}–{r.after_spread[1]:,})",
    ]
    if r.conclusive:
        sign = "saved" if r.saved_per_session >= 0 else "ADDED"
        lines.append(f"  Δ median: {sign} {abs(r.saved_per_session):,.0f} tok/session "
                     f"({r.pct:+.1f}%) — DIRECTIONAL")
    lines.append(f"  ⚠ {r.note}")
    return "\n".join(lines)
