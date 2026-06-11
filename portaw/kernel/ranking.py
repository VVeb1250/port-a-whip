"""Capability ranking — generalized from the author's skill-router (do NOT rebuild).

Ported core: TF-IDF cosine (tier-1) + curated hybrid layer (intent-phrase boost,
conflict pruning, prerequisite fan-out). Generalized from "skills" to typed
`Capability` documents so the same engine ranks skill / mcp-tool / instruction /
lesson (paw's 4 capability types). PURE + no I/O — registry.py supplies the
corpus, adapters supply the prompt. Tuning lives in an injectable RouteConfig
(was module globals) so tests pin behaviour.

tier-2 multilingual embedding fallback = Phase 3 (skill-router's embed.py port);
this module is the lexical tier-1 that fires on every prompt at ~ms cost.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, replace

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")

_STOP = set(
    """the a an and or but if then else for to of in on at by with from into
as is are was were be been being this that these those it its do does did have has
had not no can will would should could may might must your you i we they he she them
how what why when where which who whom use used using make made get got need want via
please help fix add new code file files project run create update check""".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase 3+ char alnum tokens, stopwords dropped."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP]


@dataclass(frozen=True)
class Capability:
    """One routable item. `text` = the searchable corpus (name + desc + triggers)."""

    name: str
    text: str
    ctype: str          # "set" | "skill" | "mcp-tool" | "instruction" | "lesson"
    invoke: str = ""    # how to use it (e.g. "portaw install X", "/skill", "Read path")
    desc: str = ""      # short human blurb for the inject line
    requires: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteConfig:
    cosine_min: float = 0.16      # absolute confidence floor
    rel_min: float = 0.5          # keep within this fraction of top score
    max_results: int = 3
    name_weight: int = 3          # repeat name tokens → name matches rank higher
    intent_bonus: float = 0.34    # boost when a curated intent phrase hits
    neighbor_factor: float = 0.3  # discount for fan-out prerequisites


@dataclass(frozen=True)
class Hit:
    score: float
    cap: Capability


def _doc_tokens(cap: Capability, cfg: RouteConfig) -> list[str]:
    return tokenize(cap.name) * cfg.name_weight + tokenize(cap.text)


def _tfidf(prompt: str, caps: list[Capability], cfg: RouteConfig) -> dict[str, Hit]:
    """TF-IDF cosine of prompt vs each capability doc. Unpruned dict {name: Hit}."""
    docs = [_doc_tokens(c, cfg) for c in caps]
    n = len(docs)
    df: dict[str, int] = {}
    for d in docs:
        for t in set(d):
            df[t] = df.get(t, 0) + 1
    idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}

    def vec(tokens: list[str]) -> tuple[dict[str, float], float]:
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        v = {t: (c / len(tokens)) * idf.get(t, 0) for t, c in tf.items() if t in idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return v, norm

    qv, qn = vec(tokenize(prompt))
    scored: dict[str, Hit] = {}
    if not qv:
        return scored
    for cap, d in zip(caps, docs, strict=True):
        dv, dn = vec(d)
        dot = sum(qv[t] * dv.get(t, 0) for t in qv)
        cos = dot / (qn * dn)
        if cos >= cfg.cosine_min:
            if cap.name not in scored or cos > scored[cap.name].score:
                scored[cap.name] = Hit(cos, cap)
    return scored


def _apply_intent(
    prompt: str, scored: dict[str, Hit], caps: list[Capability],
    intent_map: dict[str, list[str]], cfg: RouteConfig,
) -> None:
    """Boost/inject capabilities whose curated intent phrase is a prompt substring."""
    if not intent_map:
        return
    pl = prompt.lower()
    by_name = {c.name: c for c in caps}
    for phrase, names in intent_map.items():
        if phrase in pl:
            for nm in names:
                if nm in scored:
                    scored[nm] = replace(scored[nm], score=scored[nm].score + cfg.intent_bonus)
                elif nm in by_name:
                    scored[nm] = Hit(cfg.intent_bonus, by_name[nm])


def _prune_conflicts(ranked: list[Hit]) -> list[Hit]:
    """Drop a capability if a higher-ranked one declares it conflicting."""
    out: list[Hit] = []
    blocked: set[str] = set()
    for h in ranked:
        if h.cap.name in blocked:
            continue
        out.append(h)
        blocked.update(h.cap.conflicts_with)
    return out


def _fanout_fill(primary: list[Hit], caps: list[Capability], cfg: RouteConfig) -> list[Hit]:
    """Fill SPARE slots with prerequisites of primary matches (never displace)."""
    if len(primary) >= cfg.max_results:
        return primary
    by_name = {c.name: c for c in caps}
    have = {h.cap.name for h in primary}
    extra: list[Hit] = []
    for h in primary:
        for req in h.cap.requires:
            if req in have or any(req == e.cap.name for e in extra):
                continue
            if req in by_name:
                extra.append(Hit(h.score * cfg.neighbor_factor, by_name[req]))
    room = cfg.max_results - len(primary)
    return primary + extra[:room]


def route(
    prompt: str,
    caps: list[Capability],
    cfg: RouteConfig | None = None,
    intent_map: dict[str, list[str]] | None = None,
    embed_fn: Callable[[str, list[Capability]], dict[str, float]] | None = None,
) -> list[Hit]:
    """Hybrid route: TF-IDF + intent boost + (tier-2 semantic fallback) + conflict
    prune + prerequisite fan-out.

    Empty intent_map + no embed_fn → identical to pure TF-IDF tier-1 (the default
    everywhere; parity-pinned). `embed_fn` is the OPTIONAL tier-2: it fires ONLY
    when tier-1 found nothing (lazy — the heavy model never runs on a lexical hit),
    catching paraphrase / cross-lingual prompts. Returns ranked Hits (≤ max_results),
    or [] when nothing clears the floor."""
    cfg = cfg or RouteConfig()
    scored = _tfidf(prompt, caps, cfg)
    _apply_intent(prompt, scored, caps, intent_map or {}, cfg)
    if not scored and embed_fn is not None:
        by_name = {c.name: c for c in caps}
        scored = {
            nm: Hit(sc, by_name[nm])
            for nm, sc in embed_fn(prompt, caps).items()
            if nm in by_name
        }
    if not scored:
        return []
    ranked = sorted(scored.values(), key=lambda h: -h.score)
    ranked = _prune_conflicts(ranked)
    top = ranked[0].score
    primary = [h for h in ranked if h.score >= top * cfg.rel_min][: cfg.max_results]
    return _fanout_fill(primary, caps, cfg)
