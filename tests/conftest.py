"""Global test isolation — no test ever touches the real ~/.paw or ~/.claude.

Individual tests still monkeypatch these for their own tmp layouts; this
autouse fixture is the safety net for tests that DON'T (e.g. router run_hook
tests, which now write router-outcome counters as a side effect).
"""

import pytest

import portaw.memory.sessionlog as sessionlog
import portaw.memory.store as store
import portaw.sets.state as state_mod


@pytest.fixture(autouse=True)
def _isolated_paw_home(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "global_dir", lambda: tmp_path / "paw-home" / "memory")
    monkeypatch.setattr(state_mod, "state_path",
                        lambda: tmp_path / "paw-home" / "state.json")
    monkeypatch.setattr(sessionlog, "_dir", lambda: tmp_path / "paw-home" / "session")
