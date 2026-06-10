# integration/ — host-side hook sources (kernel-unify)

Deployable sources for host hooks that paw integrates *into* (vs the package's
own hooks). Tracked here so the integration is reproducible and reviewable; the
live copy lives under the host's config dir.

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

### Deploy

`~/.claude/hooks/*` is protected by `nah` (the secure-agent guard blocks an agent
from modifying its own hooks — `nah trust` on the path does NOT clear it, it is a
hard self-protection rule). So edit **this** file, never the live one, then copy
it over from your own shell (nah guards the agent's tools, not your terminal):

```powershell
Copy-Item integration\skill-router.py "$env:USERPROFILE\.claude\hooks\skill-router.py"
```

Back up the live file first if you don't already have one.

### Validate

`tests/test_skill_router_parity.py` pins the live hook's `_inline_route` ≡
`_kernel_route` over the real corpus + skill-graph.json (skips when the author's
hook isn't present). Run `py -m pytest tests/test_skill_router_parity.py` after
any deploy.
