"""Failure→fix detector tests — synthetic CC transcript, pure."""

import json

from portaw.memory import store
from portaw.memory.capture import run_capture_hook
from portaw.memory.detect import from_transcript, parse_transcript


def _tu(tid, command):
    return {"message": {"content": [
        {"type": "tool_use", "id": tid, "name": "Bash", "input": {"command": command}}
    ]}}


def _tr(tid, text, is_error):
    return {"message": {"content": [
        {"type": "tool_result", "tool_use_id": tid, "content": text, "is_error": is_error}
    ]}}


def _write_transcript(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")


def test_parse_transcript_collects_bash_calls(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "python build.py"),
        _tr("a", "python: command not found", True),
        _tu("b", "py build.py"),
        _tr("b", "built ok", False),
    ])
    calls = parse_transcript(p)
    assert len(calls) == 2
    assert calls[0].is_error and not calls[1].is_error


def test_detect_pairs_failure_with_similar_fix(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "python build.py"),
        _tr("a", "'python' is not recognized as an internal command", True),
        _tu("b", "py build.py"),
        _tr("b", "ok", False),
    ])
    sigs = from_transcript(p)
    assert len(sigs) == 1
    assert sigs[0].trigger.startswith("python build.py")
    assert sigs[0].fix == "py build.py"
    assert "build.py" in sigs[0].paths


def test_no_signal_without_shared_token(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "python build.py"),
        _tr("a", "command not found", True),
        _tu("b", "ls something_else.txt"),
        _tr("b", "ok", False),
    ])
    assert from_transcript(p) == []


def test_no_signal_when_no_error(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "py build.py"),
        _tr("a", "ok", False),
    ])
    assert from_transcript(p) == []


def test_error_detected_from_text_without_is_error_flag(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "python run.py"),
        _tr("a", "Traceback (most recent call last):", False),  # flag absent
        _tu("b", "py run.py"),
        _tr("b", "ok", False),
    ])
    sigs = from_transcript(p)
    assert len(sigs) == 1 and sigs[0].fix == "py run.py"


def test_error_detected_from_nonzero_exit_marker(tmp_path):
    # the common runner form the original Bash-centric markers missed
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "pytest tests/api.py"),
        _tr("a", "process exited with exit code 1", False),  # no is_error flag
        _tu("b", "pytest tests/api.py -x"),
        _tr("b", "ok", False),
    ])
    sigs = from_transcript(p)
    assert len(sigs) == 1 and sigs[0].fix == "pytest tests/api.py -x"


def test_error_detected_from_error_colon_prefix(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "tsc src/app.ts"),
        _tr("a", "error: cannot find module src/app.ts", False),
        _tu("b", "tsc src/app.ts --skipLibCheck"),
        _tr("b", "ok", False),
    ])
    sigs = from_transcript(p)
    assert len(sigs) == 1 and sigs[0].fix.endswith("--skipLibCheck")


def test_from_transcript_missing_file_empty():
    assert from_transcript("nope/does/not/exist.jsonl") == []


def test_run_capture_hook_from_transcript(tmp_path, monkeypatch):
    p = tmp_path / "t.jsonl"
    _write_transcript(p, [
        _tu("a", "python deploy.py"),
        _tr("a", "python: command not found", True),
        _tu("b", "py deploy.py"),
        _tr("b", "ok", False),
    ])
    saved = {}
    monkeypatch.setattr(store, "load_lessons", lambda: [])
    monkeypatch.setattr(store, "save_lessons", lambda e: saved.update(e=e))
    payload = json.dumps({"transcript_path": str(p), "cwd_name": "paw"})
    results = run_capture_hook(payload)
    assert len(results) == 1 and results[0].stored
    assert "deploy.py" in saved["e"][0].body
