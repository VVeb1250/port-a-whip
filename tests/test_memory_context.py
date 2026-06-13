"""host_context + scoped-drop diagnostic tests — pure, synthetic entries."""

from portaw.memory.context import detect_stacks, host_context, scoped_drop_report
from portaw.memory.retrieval import RetrievalContext
from portaw.memory.schema import MemoryEntry


def _lesson(body, applicability):
    return MemoryEntry.new("lesson", body, scope="global", applicability=applicability)


def test_detect_stacks_from_marker(tmp_path):
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")
    assert "python" in detect_stacks(tmp_path)


def test_host_context_project_id_is_root_name(tmp_path):
    ctx = host_context(tmp_path)
    assert ctx.project_id == tmp_path.name


def test_scoped_drop_report_names_ineligible_stack_lessons():
    entries = [
        _lesson("await missing", "stack:python"),
        _lesson("rust borrow", "stack:rust"),
        _lesson("always true", "universal"),
    ]
    # context has python only → rust lesson is the casualty
    ctx = RetrievalContext(stacks=frozenset({"python"}), project_id="paw")
    report = scoped_drop_report(entries, ctx)
    assert len(report) == 1
    assert "stack:rust" in report[0]
    assert "1 lesson" in report[0]


def test_scoped_drop_report_flags_project_mismatch():
    entries = [_lesson("graphify save", "project:graphify")]
    ctx = RetrievalContext(stacks=frozenset(), project_id="port-a-whip")
    report = scoped_drop_report(entries, ctx)
    assert len(report) == 1 and "project:graphify" in report[0]


def test_scoped_drop_report_empty_when_all_eligible():
    entries = [
        _lesson("u", "universal"),
        _lesson("p", "stack:python"),
    ]
    ctx = RetrievalContext(stacks=frozenset({"python"}), project_id="paw")
    assert scoped_drop_report(entries, ctx) == []


def test_scoped_drop_report_ignores_project_type_entries():
    # project-type memory is pre-scoped, not applicability-filtered → never "dropped"
    proj = MemoryEntry.new("project", "a decision", scope="project")
    ctx = RetrievalContext(stacks=frozenset(), project_id="x")
    assert scoped_drop_report([proj], ctx) == []
