"""L3 lesson + project memory (Phase 3).

High-precision, compressed, silence-biased, self-tuning recall — machinery off
the per-prompt budget. cross-host + mistake-surfacing = the moat. See
docs/L3-DESIGN.md for the full design (R1-R12, anchor weighting, scope rules).

Layout:
  schema.py      MemoryEntry + Anchors (frozen) + content-hash id
  store.py       jsonl read/write — global ~/.paw/memory + project <root>/.paw/memory
  anchors.py     path/symbol extraction (codegraph node = present-only bonus)
  retrieval.py   reuse kernel.route() (ctype="lesson") + activation rank
  inject.py      silence-biased, per-type threshold, budget cap
  capture.py     Stop-hook fail→fix detect + applicability tag (CC first)
  consolidate.py async dream: dedup / promote / decay / archive
  gate.py        integrity gate (confidence-to-hot, confirm project-write)
  seed.py        project seed + ADR-harvest v1
"""
