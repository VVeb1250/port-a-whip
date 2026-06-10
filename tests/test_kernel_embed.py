"""Tier-2 embedding fallback tests.

Two layers: (1) the route() wiring is tested with a FAKE embed_fn so it runs
everywhere (deterministic, no model); (2) the real ONNX path is tested only when
`embed.available()` — skipped on machines without the model/libs."""

import pytest

from portaw.kernel import embed
from portaw.kernel.ranking import Capability, RouteConfig, route

_CAPS = [
    Capability(name="secure-agent", text="secret leak credential scan permissions", ctype="set"),
    Capability(name="efficiency", text="codegraph navigate callers tokens", ctype="set"),
]


def _fake_embed(scores):
    """Build an embed_fn returning fixed {name: cosine} regardless of prompt."""
    return lambda prompt, caps: dict(scores)


# --- route() wiring (no model needed) ---

def test_embed_fn_not_called_when_tier1_hits():
    calls = []

    def spy(prompt, caps):
        calls.append(prompt)
        return {}

    # a lexical hit on "credential" → tier-1 returns something → embed_fn skipped (lazy)
    hits = route("scan for a credential leak", _CAPS, embed_fn=spy)
    assert hits and hits[0].cap.name == "secure-agent"
    assert calls == []  # heavy model never consulted on a lexical hit


def test_embed_fn_fires_only_when_tier1_empty():
    # a prompt with NO lexical overlap → tier-1 empty → fallback supplies the hit
    hits = route("ความปลอดภัย", _CAPS, embed_fn=_fake_embed({"secure-agent": 0.51}))
    assert [h.cap.name for h in hits] == ["secure-agent"]
    assert hits[0].score == pytest.approx(0.51)


def test_embed_fallback_unknown_name_ignored():
    hits = route("xxxxxx", _CAPS, embed_fn=_fake_embed({"ghost": 0.9}))
    assert hits == []  # a name not in the corpus is dropped, not crashed on


def test_no_embed_fn_is_pure_tfidf():
    # default path unchanged → parity with the existing tier-1 behavior
    assert route("ความปลอดภัย", _CAPS) == []


# --- availability guard (no model needed) ---

def test_available_false_on_missing_dir(tmp_path):
    assert embed.available(tmp_path / "no-model") is False


def test_make_embedder_none_when_unavailable(tmp_path):
    assert embed.make_embedder(tmp_path / "no-model") is None


def test_embed_scores_empty_when_unavailable(tmp_path):
    assert embed.embed_scores("hi", _CAPS, md=tmp_path / "no-model") == {}


def test_embed_scores_empty_on_empty_corpus(tmp_path):
    assert embed.embed_scores("hi", [], md=tmp_path / "no-model") == {}


# --- real ONNX path (skipped if model/libs absent) ---

_HAVE_MODEL = embed.available()


@pytest.mark.skipif(not _HAVE_MODEL, reason="embedding model/libs not installed")
def test_real_crosslingual_match():
    # Thai prompt, English corpus → lexical tier-1 scores 0, semantic tier-2 matches
    fn = embed.make_embedder()
    assert fn is not None
    caps = [
        Capability(name="secure-agent", text="detect secret credential leaks and scan permissions", ctype="set"),
        Capability(name="design", text="frontend visual polish layout components", ctype="set"),
    ]
    hits = route("สแกนหาความลับที่รั่วไหล", caps, embed_fn=fn)  # "scan for leaked secrets"
    assert hits and hits[0].cap.name == "secure-agent"
