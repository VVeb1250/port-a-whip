"""Ranking engine tests — pure, synthetic corpus (ported skill-router behaviour)."""

from portaw.kernel.ranking import Capability, RouteConfig, route, tokenize

_CFG = RouteConfig()


def _cap(name, text, **kw):
    return Capability(name=name, text=text, ctype="set", **kw)


CORPUS = [
    _cap("secure-agent", "security secret leak vulnerability permission guard"),
    _cap("efficiency", "code navigation grep search shell output compression token"),
    _cap("docs", "library api reference documentation version package framework"),
]


def test_tokenize_drops_stopwords_and_short():
    assert tokenize("How do I use the API key") == ["api", "key"]


def test_route_matches_relevant_capability():
    hits = route("scan for leaked secret and vulnerability", CORPUS, _CFG)
    assert hits and hits[0].cap.name == "secure-agent"


def test_route_silent_on_unrelated():
    assert route("the capital of france is paris", CORPUS, _CFG) == []


def test_route_respects_max_results():
    cfg = RouteConfig(max_results=1, cosine_min=0.0, rel_min=0.0)
    hits = route("code api security", CORPUS, cfg)
    assert len(hits) == 1


def test_intent_boost_injects_zero_tfidf_match():
    # prompt shares NO lexical token with the cap's text, but an intent phrase hits.
    caps = [_cap("blast", "dependency impact analysis")]
    imap = {"blast radius": ["blast"]}
    hits = route("estimate the blast radius before push", caps, _CFG, intent_map=imap)
    assert hits and hits[0].cap.name == "blast"


def test_intent_boost_raises_existing_score():
    caps = [_cap("sec", "security scan")]
    base = route("security scan now", caps, _CFG)[0].score
    boosted = route("security scan now", caps, _CFG, intent_map={"scan now": ["sec"]})[0].score
    assert boosted > base


def test_conflict_prune_drops_lower_ranked():
    caps = [
        _cap("a", "alpha alpha alpha", conflicts_with=("b",)),
        _cap("b", "alpha"),
    ]
    cfg = RouteConfig(cosine_min=0.0, rel_min=0.0)
    names = [h.cap.name for h in route("alpha", caps, cfg)]
    assert "a" in names and "b" not in names  # a outranks a→ blocks b


def test_fanout_fills_spare_slot_with_prerequisite():
    caps = [
        _cap("main", "alpha beta", requires=("setup",)),
        _cap("setup", "gamma delta"),  # no lexical overlap → only arrives via fan-out
    ]
    cfg = RouteConfig(cosine_min=0.0, rel_min=0.0, max_results=3)
    names = [h.cap.name for h in route("alpha beta", caps, cfg)]
    assert "main" in names and "setup" in names


def test_fanout_never_displaces_real_match_when_full():
    caps = [
        _cap("m1", "alpha", requires=("setup",)),
        _cap("m2", "alpha"),
        _cap("m3", "alpha"),
        _cap("setup", "zzz"),
    ]
    cfg = RouteConfig(cosine_min=0.0, rel_min=0.0, max_results=3)
    names = [h.cap.name for h in route("alpha", caps, cfg)]
    assert "setup" not in names and len(names) == 3
