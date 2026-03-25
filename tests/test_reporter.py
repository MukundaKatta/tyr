"""Tests for tyr.reporter — ValidationReporter, Summary, SeverityCounter."""

import json

from tyr.core import ValidationResult, Violation, Severity
from tyr.reporter import ValidationReporter, Summary, SeverityCounter


def _make_result(passed_input: bool = True) -> ValidationResult:
    """Helper to create a ValidationResult with optional violations."""
    r = ValidationResult(input_value="test-input", target="commit")
    if not passed_input:
        r.add_violation(
            Violation("rule-x", "something wrong", Severity.ERROR, "test-input")
        )
    return r


class TestSeverityCounter:
    def test_counts(self):
        c = SeverityCounter()
        c.add(Severity.ERROR)
        c.add(Severity.ERROR)
        c.add(Severity.WARNING)
        c.add(Severity.INFO)
        assert c.errors == 2
        assert c.warnings == 1
        assert c.infos == 1
        assert c.total == 4

    def test_as_dict(self):
        c = SeverityCounter()
        c.add(Severity.ERROR)
        d = c.as_dict()
        assert d["errors"] == 1
        assert d["total"] == 1


class TestSummary:
    def test_aggregate(self):
        s = Summary()
        s.add_result(_make_result(True))
        s.add_result(_make_result(False))
        assert s.total_inputs == 2
        assert s.passed == 1
        assert s.failed == 1
        assert s.counter.errors == 1

    def test_as_dict(self):
        s = Summary()
        s.add_result(_make_result(True))
        d = s.as_dict()
        assert d["passed"] == 1


class TestValidationReporter:
    def test_as_text(self):
        reporter = ValidationReporter()
        reporter.add(_make_result(True))
        reporter.add(_make_result(False))
        text = reporter.as_text()
        assert "[PASS]" in text
        assert "[FAIL]" in text
        assert "2 checked" in text

    def test_as_json(self):
        reporter = ValidationReporter([_make_result(False)])
        data = json.loads(reporter.as_json())
        assert len(data["results"]) == 1
        assert data["summary"]["failed"] == 1

    def test_github_annotations(self):
        reporter = ValidationReporter([_make_result(False)])
        annotations = reporter.as_github_annotations()
        assert len(annotations) == 1
        assert annotations[0]["level"] == "error"
        assert annotations[0]["title"] == "rule-x"

    def test_github_commands(self):
        reporter = ValidationReporter([_make_result(False)])
        cmds = reporter.as_github_commands()
        assert cmds.startswith("::error title=rule-x::")

    def test_verbose_text_includes_info(self):
        r = ValidationResult(input_value="x", target="test")
        r.add_violation(Violation("info-rule", "just info", Severity.INFO, "x"))
        reporter = ValidationReporter([r])
        # Non-verbose hides info
        assert "INFO" not in reporter.as_text(verbose=False)
        # Verbose shows info
        assert "INFO" in reporter.as_text(verbose=True)

    def test_add_many(self):
        reporter = ValidationReporter()
        reporter.add_many([_make_result(True), _make_result(False)])
        s = reporter.summary()
        assert s.total_inputs == 2
