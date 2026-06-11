# integration/ — host-side hook sources (kernel-unify)

Deployable sources for host hooks that paw integrates *into* (vs the package's
own hooks). Tracked here so the integration is reproducible and reviewable; the
live copy lives under the host's config dir.

Both files (`skill-router.py`, `embed.py`) deploy to `~/.claude/hooks/` and must
be copied together — `skill-router.py` calls `embed.search`, and the unified
`embed.py` shares paw's MiniLM session with `skill-router.py`'s memory bridge.

## skill-router.py

The author's live `~/.claude/hooks/skill-router.py` (UserPromptSubmit), extended
for **kernel-unify** (2026-06-10):

- ranking delegates to `portaw.kernel.ranking.route` — ONE ranker in the live
  path — with the inline TF-IDF copy kept as a zero-paw fallback;
- paw L3 memory (+sets) is surfaced through this ONE hook via
  `portaw.adapters.router.paw_block`, instead of wiring a second competing
  UserPromptSubmit hook (no double-fire).

Both bridges are optional-import + fail-silent, so the hook still works with no
paw install.

## embed.py

The skill-router's tier-2 semantic fallback (multilingual MiniLM, ONNX), extended
for **embed-unify** (2026-06-11):

- `_encode` delegates the ONNX session + encode to `portaw.kernel.embed.encode`
  when paw is importable, so a prompt that fires BOTH skill-semantic search and
  paw memory-recall tier-2 loads MiniLM **once** per process, not twice;
- `_encode_inline` is kept as the zero-paw fallback (mirrors
  `_inline_route`/`_kernel_route`). Both read the same `models/` dir, so the
  vectors are identical either way.

Optional-import + fail-silent like the router bridges; a missing model still
degrades to silence, never a crash.

### Deploy

`~/.claude/hooks/*` is protected by `nah` (the secure-agent guard blocks an agent
from modifying its own hooks — `nah trust` on the path does NOT clear it, it is a
hard self-protection rule). So edit **these** files, never the live ones, then
copy them over from your own shell (nah guards the agent's tools, not your
terminal):

```powershell
Copy-Item integration\skill-router.py "$env:USERPROFILE\.claude\hooks\skill-router.py"
Copy-Item integration\embed.py        "$env:USERPROFILE\.claude\hooks\embed.py"
```

Back up the live files first if you don't already have one.

### Validate

- `tests/test_skill_router_parity.py` pins the live hook's `_inline_route` ≡
  `_kernel_route` over the real corpus + skill-graph.json.
- `tests/test_embed_unify.py` pins the deploy source's unify seam, and (post-copy,
  model present) that the delegated encode is byte-identical to paw's own.

Both skip cleanly when the author's hook isn't present. Run
`py -m pytest tests/test_skill_router_parity.py tests/test_embed_unify.py` after
any deploy.
