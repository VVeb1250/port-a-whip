"""embed-unify guard: the skill-router embed.py routes its ONNX encode through
paw's ONE shared session instead of loading a second MiniLM.

Two MiniLM sessions in one process (skill-semantic search + paw memory-recall
tier-2) is the waste this closes. embed.py now delegates `_encode` to
`portaw.kernel.embed.encode` when paw is importable, keeping `_encode_inline` as
the zero-paw fallback (mirrors the router's _kernel_route/_inline_route).

Two layers, like the kernel-unify guards:
  • the committed deploy source (integration/embed.py) must HAVE the seam — pinned
    always, since it ships in the repo;
  • on the author's box (live hook deployed + model present) the delegated encode
    and paw's own encode produce IDENTICAL vectors — proof it is the same session,
    not two copies that happen to agree. Skips cleanly pre-deploy / non-author.
"""

import importlib.util
from pathlib import Path

import pytest

INTEGRATION_EMBED = Path(__file__).resolve().parent.parent / "integration" / "embed.py"
LIVE_EMBED = Path.home() / ".claude" / "hooks" / "embed.py"


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(not INTEGRATION_EMBED.exists(),
                    reason="run from the repo (integration/ is not packaged)")
def test_committed_source_has_unify_seam():
    mod = _load(INTEGRATION_EMBED, "skill_router_embed_src")
    # the inline fallback exists AND the public _encode (delegating entry) is what
    # the corpus/search code still calls — the seam is wired, not half-renamed.
    assert hasattr(mod, "_encode_inline") and callable(mod._encode_inline)
    assert hasattr(mod, "_encode") and callable(mod._encode)


@pytest.mark.skipif(not LIVE_EMBED.exists(), reason="author's live embed.py not present")
def test_live_delegated_encode_matches_paw_encode():
    pytest.importorskip("portaw")
    pytest.importorskip("numpy")
    from portaw.kernel import embed as paw

    mod = _load(LIVE_EMBED, "skill_router_embed_live")
    if not hasattr(mod, "_encode_inline"):
        pytest.skip("live embed.py predates embed-unify (copy integration/embed.py over it)")
    if not paw.available(mod.MODEL_DIR):
        pytest.skip("embedding model/libs not installed")

    import numpy as np

    texts = ["scan for leaked secrets", "นำทางในโค้ด"]
    delegated = mod._encode(texts)              # routes through paw's shared session
    direct = paw.encode(texts, mod.MODEL_DIR)   # paw's own entry, same session
    assert np.allclose(delegated, direct, atol=1e-6)
