"""Confidence as a learned quantity, not a frozen severity seed (2026-06-11).

Old model: confidence = severity map (HIGH 0.9 / MED 0.7 / LOW 0.5), fixed forever.
A HIGH that never actually recurs stayed overconfident; a MED that kept biting
stayed under the trusted-gate bar (0.75) and never injected. Severity is only the
PRIOR now — the starting guess. Evidence moves it:

  • a confirmed real recurrence  → reinforce (saturating toward 1, never reaching).
  • a long stretch with no hit    → decay toward neutral (it may be stale/wrong).

Two distinct axes, deliberately NOT double-counted: ``activation`` (retrieval.py) =
recency×frequency = "how HOT right now"; ``confidence`` = "how PROVEN-correct". Both
are fed by recurrence, but confidence SATURATES (asymptotic) while activation may
grow — so frequency raising both is bounded, not a runaway. Pure functions; callers
persist the result. The bump callers (Stop hook, consolidate) apply ``reinforced``.
"""

from __future__ import annotations

NEUTRAL = 0.5
REINFORCE_ALPHA = 0.15   # each confirmed recurrence closes 15% of the gap to 1.0
DECAY_BETA = 0.10        # each stale step pulls 10% of the way back toward neutral
CEILING = 0.99           # never assert certainty (honesty: evidence ≠ proof)


def reinforced(confidence: float, *, alpha: float = REINFORCE_ALPHA) -> float:
    """One confirmed recurrence: move a fraction of the remaining gap toward 1.0.

    Saturating — repeated real hits raise trust with diminishing returns and never
    reach certainty. A MED 0.70 → 0.745 → 0.78 … crosses the 0.75 trusted bar after
    ~2 confirmed recurrences, which is exactly the §2.2 'proven by recurrence' rule
    expressed as a smooth curve instead of a hard step."""
    c = _clamp(confidence)
    return min(CEILING, c + (1.0 - c) * _clamp01(alpha))


def decayed(confidence: float, *, beta: float = DECAY_BETA) -> float:
    """No recent evidence: ease back toward neutral (a once-HIGH lesson that stopped
    happening loses its overconfidence). Pulls toward NEUTRAL from either side; never
    crosses it (decay expresses doubt, not disproof)."""
    c = _clamp(confidence)
    return c + (NEUTRAL - c) * _clamp01(beta)


def _clamp(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else float(x)


def _clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else float(x)
