#!/usr/bin/env py
"""Semantic fallback for skill-router — multilingual sentence embeddings.

Tier-2 of the router. Used only when the fast TF-IDF lexical tier returns
nothing AND the prompt contains non-ASCII letters (e.g. Thai / CJK / Cyrillic).
A multilingual MiniLM model (ONNX) embeds the prompt and the skill corpus into a
shared semantic space, so a prompt in any language can match English skill docs.

Heavy by design — loaded lazily, never on plain-English prompts. Corpus vectors
are built once and cached, keyed by the index signature, so only the single
prompt is embedded per call.

embed-unify (2026-06-11): the ONNX session+encode is delegated to paw's
``portaw.kernel.embed`` when paw is importable under the same interpreter, so a
prompt that fires BOTH this skill-semantic search AND paw memory-recall tier-2
loads MiniLM ONCE per process, not twice. ``_encode_inline`` is the zero-paw
fallback (mirrors how the router's ``_inline_route`` backs ``_kernel_route``).
Both point at the same ./models/ dir, so the vectors are identical either way.

Dependencies (install via setup_embeddings.ps1): onnxruntime, tokenizers, numpy.
Model files live in ./models/ . If anything is missing this module raises and the
caller falls back to silence — never crashes the hook.
"""
import os
import io
import json

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(HERE, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "model_quantized.onnx")
TOKENIZER_PATH = os.path.join(MODEL_DIR, "tokenizer.json")
INDEX = os.path.join(HERE, ".skill-index.json")
VECS = os.path.join(HERE, ".skill-vecs.npz")

# ---- tuning ----
SEM_MIN = 0.30        # absolute semantic-cosine floor (MiniLM scale, not TF-IDF)
REL_MIN = 0.85        # keep results within this fraction of the top score
MAX_RESULTS = 3
MAX_TOKENS = 128      # truncate long prompts / docs

_session = None
_tokenizer = None
_input_names = None


def _ensure_files():
    if not os.path.exists(MODEL_PATH) or not os.path.exists(TOKENIZER_PATH):
        raise RuntimeError("embedding model not installed")


def _load():
    """Lazy-load the ONNX session + tokenizer. Cached at module scope."""
    global _session, _tokenizer, _input_names
    if _session is not None:
        return
    _ensure_files()
    import onnxruntime as ort  # noqa: F401
    from tokenizers import Tokenizer

    opts = ort.SessionOptions()
    opts.log_severity_level = 3  # errors only, keep stderr quiet
    opts.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
    _session = ort.InferenceSession(
        MODEL_PATH, sess_options=opts, providers=["CPUExecutionProvider"]
    )
    _input_names = {i.name for i in _session.get_inputs()}

    tok = Tokenizer.from_file(TOKENIZER_PATH)
    pad_id = tok.token_to_id("<pad>")
    if pad_id is None:
        pad_id = 1
    tok.enable_truncation(max_length=MAX_TOKENS)
    tok.enable_padding(pad_id=pad_id, pad_token="<pad>")
    _tokenizer = tok


def _encode(texts):
    """Embed a list of strings -> (n, dim) L2-normalized float32 matrix.

    Delegates to paw's shared session (ONE MiniLM per process) when paw is
    importable; inline ONNX otherwise. A paw IMPORT failure -> inline; a genuine
    embed failure (missing deps/model) propagates either way -> the caller's
    semantic_fallback returns []. Both paths read the same MODEL_DIR."""
    try:
        from portaw.kernel import embed as _paw
    except Exception:
        return _encode_inline(texts)
    return _paw.encode(list(texts), MODEL_DIR)


def _encode_inline(texts):
    """Standalone ONNX encode — the zero-paw fallback (paw absent)."""
    import numpy as np

    _load()
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

    # mean pooling over real tokens (mask-weighted)
    m = mask.astype(np.float32)[..., None]
    summed = (last_hidden * m).sum(axis=1)
    counts = np.clip(m.sum(axis=1), 1e-9, None)
    emb = summed / counts

    norm = np.linalg.norm(emb, axis=1, keepdims=True)
    norm = np.clip(norm, 1e-12, None)
    return (emb / norm).astype(np.float32)


def _doc_text(skill):
    return (skill.get("name", "") + ". " + skill.get("desc", "")).strip()


def _corpus_vectors(idx):
    """Return (matrix, skills) for the indexed corpus, cached by index sig."""
    import numpy as np

    skills = idx.get("skills", [])
    sig = json.dumps(idx.get("sig", {}), sort_keys=True)

    if os.path.exists(VECS):
        try:
            data = np.load(VECS, allow_pickle=False)
            if str(data["sig"]) == sig and data["mat"].shape[0] == len(skills):
                return data["mat"], skills
        except Exception:
            pass

    mat = _encode([_doc_text(s) for s in skills]) if skills else np.zeros((0, 1), np.float32)
    try:
        np.savez(VECS, mat=mat, sig=np.array(sig))
    except OSError:
        pass
    return mat, skills


def search(prompt):
    """Semantic top matches. Returns [(score, skill_dict), ...] or []."""
    import numpy as np

    with io.open(INDEX, "r", encoding="utf-8") as f:
        idx = json.load(f)

    mat, skills = _corpus_vectors(idx)
    if mat.shape[0] == 0:
        return []

    q = _encode([prompt])[0]            # (dim,)
    sims = mat @ q                        # cosine (all normalized)
    order = np.argsort(-sims)

    out = []
    top = float(sims[order[0]])
    if top < SEM_MIN:
        return []
    for i in order[:MAX_RESULTS]:
        s = float(sims[i])
        if s < SEM_MIN or s < top * REL_MIN:
            break
        out.append((s, skills[int(i)]))
    return out
