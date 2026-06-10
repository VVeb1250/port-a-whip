"""Host-context derivation — who/where is asking, for eligibility (§2.1).

A recall without a ``RetrievalContext`` silently kills every ``stack:*`` and
``project:*`` lesson (they are ineligible against an empty context), so every
entrypoint — CLI and live hooks — derives one here. Marker-file detection is the
zero-config floor; explicit flags override. I/O is limited to ``Path.exists``.
"""

from __future__ import annotations

from pathlib import Path

from portaw.memory.retrieval import RetrievalContext

# cwd marker file → stack tag (cheap eligibility heuristic; explicit flags override)
STACK_MARKERS = {
    "pyproject.toml": "python", "setup.py": "python", "requirements.txt": "python",
    "package.json": "typescript", "tsconfig.json": "typescript",
    "Cargo.toml": "rust", "go.mod": "golang", "build.gradle": "kotlin",
    "build.gradle.kts": "kotlin", "pubspec.yaml": "flutter", "Package.swift": "swift",
}


def detect_stacks(root: Path | str) -> frozenset[str]:
    """Infer host stacks from project marker files (zero-config eligibility floor)."""
    r = Path(root)
    return frozenset(tag for marker, tag in STACK_MARKERS.items() if (r / marker).exists())


def host_context(
    cwd: Path | str | None = None,
    *,
    stacks: frozenset[str] | None = None,
    project_id: str | None = None,
) -> RetrievalContext:
    """Build the retrieval context for a host location (default: process cwd)."""
    root = Path(cwd) if cwd else Path.cwd()
    return RetrievalContext(
        stacks=stacks if stacks is not None else detect_stacks(root),
        project_id=project_id or root.name,
    )
