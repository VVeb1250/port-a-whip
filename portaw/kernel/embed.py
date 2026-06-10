"""Semantic tier-2 — multilingual sentence embeddings (optional, lazy).

Tier-1 (kernel.ranking) is lexical TF-IDF — fast, fires on every prompt. It misses
PARAPHRASE and CROSS-LINGUAL matches: a Thai / CJK / Cyrillic prompt against
English capability + lesson docs scores ~0 lexically. This module is the tier-2
fallback the router falls through to ONLY when tier-1 finds nothing — a
multilingual MiniLM (ONNX) embeds prompt + corpus into one semantic space, so an
any-language prompt can match an English doc.

OPTIONAL by construction. It needs onnxruntime + tokenizers + numpy and the model
files; if ANY are missing, `available()` is False and the router stays on the
TF-IDF floor — paw's runtime deps stay click + tomlkit (embedding is an opt-in
extra: `pip install port-a-whip[embed]`). Ported from the author's skill-router
`embed.py` (do NOT rebuild); generalized from skill dicts to typed Capabilities,
and reused via the author's already-downloaded model by default (no extra fetch).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Callable

from portaw.kernel.ranking import Capability

MAX_TOKENS = 128
DEFAULT_SEM_MIN = 0.30   # absolute MiniLM-cosine floor (NOT the TF-IDF scale)
DEFAULT_REL_MIN = 0.85   # keep results within this fraction of the top score
DEFAULT_MAX = 3

_MODEL_FILE = "model_quantized.onnx"
_TOKENIZER_FILE = "tokenizer.json"

_session = None
_tokenizer = None
_input_names: set[str] | None = None
_loaded_dir: Path | None = None
_corpus_cache: dict[str, tuple] = {}   # corpus signature -> (matrix, names)


def model_dir(explicit: Path | str | None = None) -> Path:
    """Resolve the model dir: explicit arg → $PAW_EMBED_MODEL_DIR → the author's
    skill-router models dir (~/.claude/hooks/models — reuse it, no extra download)."""
    if explicit is not None:
        return Path(explicit)
    env = os.environ.get("PAW_EMBED_MODEL_DIR")
    if env:
        return Path(env)
    return Path.home() / ".claude" / "hooks" / "models"


def available(md: Path | str | None = None) -> bool:
    """True iff the model files exist AND the runtime libs import. Never raises."""
    d = model_dir(md)
    if not (d / _MODEL_FILE).exists() or not (d / _TOKENIZER_FILE).exists():
        return False
    try:
        import numpy  # noqa: F401
        import onnxruntime  # noqa: F401
        from tokenizers import Tokenizer  # noqa: F401
    except Exception:
        return False
    return True


def _load(md: Path | str | None = None) -> None:
    """Lazy-load the ONNX session + tokenizer, cached at module scope (heavy)."""
    global _session, _tokenizer, _input_names, _loaded_dir
    d = model_dir(md)
    if _session is not None and _loaded_dir == d:
        return
    import onnxruntime as ort
    from tokenizers import Tokenizer

    opts = ort.SessionOptions()
    opts.log_severity_level = 3  # errors only — keep stderr quiet for the hook
    opts.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
    _session = ort.InferenceSession(
        str(d / _MODEL_FILE), sess_options=opts, providers=["CPUExecutionProvider"]
    )
    _input_names = {i.name for i in _session.get_inputs()}

    tok = Tokenizer.from_file(str(d / _TOKENIZER_FILE))
    pad_id = tok.token_to_id("<pad>")
    if pad_id is None:
        pad_id = 1
    tok.enable_truncation(max_length=MAX_TOKENS)
    tok.enable_padding(pad_id=pad_id, pad_token="<pad>")
    _tokenizer = tok
    _loaded_dir = d
    _corpus_cache.clear()  # a model swap invalidates cached vectors


def _encode(texts, md: Path | str | None = None):
    """Embed a list of strings → (n, dim) L2-normalized float32 matrix (mean-pooled)."""
    import numpy as np

    _load(md)
    encs = _tokenizer.encode_batch(list(texts))
    ids = np.array([e.ids for e in encs], dtype=np.int64)
    mask = np.array([e.attention_mask for e in encs], dtype=np.int64)

    feed = {}
    if "input_ids" in _input_names:
        feed["input_ids"] = ids
    if "attention_mask" in _input_names:
        feed["attention_mask"] = mask
    if "token_type_ids" in _input_names:
        feed["token_type_ids"] = np.zeros_like(ids)

    last_hidden = _session.run(None, feed)[0]  # (n, seq, dim)
    m = mask.astype(np.float32)[..., None]
    summed = (last_hidden * m).sum(axis=1)
    counts = np.clip(m.sum(axis=1), 1e-9, None)
    emb = summed / counts
    norm = np.clip(np.linalg.norm(emb, axis=1, keepdims=True), 1e-12, None)
    return (emb / norm).astype(np.float32)


_CACHE_MAX = 8  # distinct corpora cached per process (hooks are short-lived anyway)


def _signature(caps: list[Capability], md: Path | str | None = None) -> str:
    """Stable hash of the corpus (names + text + MODEL DIR) — cache key for the
    vector matrix. The model dir is part of the key: vectors from two different
    models share no space, so a mid-process model switch must miss the cache."""
    h = hashlib.sha1()
    h.update(str(model_dir(md)).encode("utf-8"))
    h.update(b"\2")
    for c in caps:
        h.update(c.name.encode("utf-8"))
        h.update(b"\0")
        h.update(c.text.encode("utf-8"))
        h.update(b"\1")
    return h.hexdigest()


def _corpus_matrix(caps: list[Capability], md: Path | str | None = None):
    """(matrix, names) for the corpus, cached by signature so only the prompt is
    re-embedded per call (corpus vectors are computed once)."""
    import numpy as np

    sig = _signature(caps, md)
    cached = _corpus_cache.get(sig)
    if cached is not None:
        return cached
    mat = _encode([c.text for c in caps], md) if caps else np.zeros((0, 1), np.float32)
    names = [c.name for c in caps]
    if len(_corpus_cache) >= _CACHE_MAX:   # bounded — a long-lived process with a
        _corpus_cache.clear()              # mutating corpus must not grow forever
    _corpus_cache[sig] = (mat, names)
    return mat, names


def embed_scores(
    prompt: str,
    caps: list[Capability],
    *,
    sem_min: float = DEFAULT_SEM_MIN,
    rel_min: float = DEFAULT_REL_MIN,
    max_results: int = DEFAULT_MAX,
    md: Path | str | None = None,
) -> dict[str, float]:
    """prompt → {cap.name: cosine} for the top semantic matches.

    {} when nothing clears `sem_min`, the corpus is empty, or embedding is
    unavailable. Never raises — any failure degrades to {} (the router stays on
    the TF-IDF floor)."""
    try:
        if not caps or not available(md):
            return {}
        import numpy as np

        mat, names = _corpus_matrix(caps, md)
        if mat.shape[0] == 0:
            return {}
        q = _encode([prompt], md)[0]
        sims = mat @ q
        order = np.argsort(-sims)
        top = float(sims[order[0]])
        if top < sem_min:
            return {}
        out: dict[str, float] = {}
        for i in order[:max_results]:
            s = float(sims[i])
            if s < sem_min or s < top * rel_min:
                break
            out[names[int(i)]] = s
        return out
    except Exception:
        return {}


def lazy_embedder(
    md: Path | str | None = None, **kw
) -> Callable[[str, list[Capability]], dict[str, float]]:
    """route()-compatible embed_fn with ALL checks deferred to call time.

    `make_embedder` front-loads `available()` — which imports onnxruntime — so a
    LIVE hook paying that on every prompt would slow lexical hits too. This one
    costs nothing until tier-1 actually misses; unavailable → {} (router stays on
    the TF-IDF floor). Use this in hooks; `make_embedder` (None = honest signal
    for a CLI warning) stays for explicit `--embed` flows."""
    def _embed(prompt: str, caps: list[Capability]) -> dict[str, float]:
        return embed_scores(prompt, caps, md=md, **kw)

    return _embed


def make_embedder(
    md: Path | str | None = None, **kw
) -> Callable[[str, list[Capability]], dict[str, float]] | None:
    """Return a route()-compatible embed_fn, or None if embedding is unavailable.

    Wire it in opt-in: `route(prompt, caps, embed_fn=make_embedder())`. None →
    callers pass nothing → pure TF-IDF (the default everywhere)."""
    if not available(md):
        return None

    def _embed(prompt: str, caps: list[Capability]) -> dict[str, float]:
        return embed_scores(prompt, caps, md=md, **kw)

    return _embed
