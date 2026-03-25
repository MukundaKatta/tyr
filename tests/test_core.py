"""Tests for tyr.core — Rule, RuleSet, Validator, ValidationResult."""

import pytest
from tyr.core import Rule, RuleSet, ValidationResult, Violation, Validator, Severity


# -- Severity ----------------------------------------------------------------

class TestSeverity:
    def test_str_representation(self):
        assert str(Severity.ERROR) == "error"
        assert str(Severity.WARNING) == "warning"
        assert str(Severity.INFO) == "info"

    def test_from_string(self):
        assert Severity.from_string("error") is Severity.ERROR
        assert Severity.from_string("WARNING") is Severity.WARNING
        assert Severity.from_string(" info ") is Severity.INFO

    def test_from_string_invalid(self):
        with pytest.raises(ValueError, match="Unknown severity"):
            Severity.from_string("critical")


# -- Rule --------------------------------------------------------------------

class TestRule:
    def test_simple_match(self):
        rule = Rule(
            name="starts-with-feat",
            pattern=r"^feat:",
            description="Must start with feat:",
        )
        assert rule.validate("feat: add login") is None

    def test_simple_no_match(self):
        rule = Rule(
            name="starts-with-feat",
            pattern=r"^feat:",
            description="Must start with feat:",
        )
        msg = rule.validate("fix: typo")
        assert msg is not None
        assert "does not match" in msg

    def test_inverse_rule_passes_when_no_match(self):
        rule = Rule(
            name="no-wip",
            pattern=r"(?i)^wip",
            description="Must not be WIP.",
            inverse=True,
        )
        assert rule.validate("feat: ready") is None

    def test_inverse_rule_fails_when_matches(self):
        rule = Rule(
            name="no-wip",
            pattern=r"(?i)^wip",
            description="Must not be WIP.",
            inverse=True,
        )
        msg = rule.validate("WIP: still working")
        assert msg is not None
        assert "must NOT match" in msg

    def test_custom_validator(self):
        def max_len(value):
            if len(value) > 10:
                return "too long"
            return None

        rule = Rule(
            name="short",
            pattern=".*",
            description="Short strings only.",
            custom_validator=max_len,
        )
        assert rule.validate("hi") is None
        assert rule.validate("this is way too long") == "too long"

    def test_invalid_regex_raises(self):
        with pytest.raises(ValueError, match="invalid regex"):
            Rule(name="bad", pattern="[invalid", description="nope")

    def test_compiled_pattern(self):
        rule = Rule(name="test", pattern=r"^\d+$", description="digits")
        assert rule.compiled_pattern.match("123")
        assert not rule.compiled_pattern.match("abc")


# -- Violation ---------------------------------------------------------------

class TestViolation:
    def test_as_dict(self):
        v = Violation(
            rule_name="r1",
            message="bad input",
            severity=Severity.WARNING,
            input_value="xyz",
        )
        d = v.as_dict()
        assert d["rule"] == "r1"
        assert d["severity"] == "warning"
        assert d["input"] == "xyz"


# -- ValidationResult --------------------------------------------------------

class TestValidationResult:
    def test_passed_with_no_violations(self):
        r = ValidationResult(input_value="abc", target="test")
        assert r.passed is True
        assert r.error_count == 0

    def test_failed_with_error_violation(self):
        r = ValidationResult(input_value="abc", target="test")
        r.add_violation(Violation("r", "msg", Severity.ERROR, "abc"))
        assert r.passed is False
        assert r.error_count == 1

    def test_passed_with_only_warnings(self):
        r = ValidationResult(input_value="abc", target="test")
        r.add_violation(Violation("r", "msg", Severity.WARNING, "abc"))
        assert r.passed is True
        assert r.has_warnings is True
        assert r.warning_count == 1

    def test_info_count(self):
        r = ValidationResult(input_value="abc", target="test")
        r.add_violation(Violation("r", "msg", Severity.INFO, "abc"))
        assert r.info_count == 1
        assert r.passed is True

    def test_as_dict(self):
        r = ValidationResult(input_value="abc", target="test")
        d = r.as_dict()
        assert d["input"] == "abc"
        assert d["passed"] is True
        assert d["violations"] == []


# -- RuleSet -----------------------------------------------------------------

class TestRuleSet:
    def test_add_and_len(self):
        rs = RuleSet("test-set", "commit")
        rs.add_rule(Rule("r1", ".*", "desc"))
        rs.add_rule(Rule("r2", ".*", "desc"))
        assert len(rs) == 2

    def test_get_rule(self):
        rs = RuleSet("test-set", "commit")
        rule = Rule("r1", r"^feat", "desc")
        rs.add_rule(rule)
        assert rs.get_rule("r1") is rule
        assert rs.get_rule("nonexistent") is None

    def test_remove_rule(self):
        rs = RuleSet("test-set", "commit")
        rs.add_rule(Rule("r1", ".*", "desc"))
        assert rs.remove_rule("r1") is True
        assert len(rs) == 0
        assert rs.remove_rule("r1") is False

    def test_iteration(self):
        rs = RuleSet("test-set", "commit")
        rs.add_rule(Rule("r1", ".*", "desc"))
        rs.add_rule(Rule("r2", ".*", "desc"))
        names = [r.name for r in rs]
        assert names == ["r1", "r2"]

    def test_repr(self):
        rs = RuleSet("test-set", "commit")
        assert "test-set" in repr(rs)


# -- Validator ---------------------------------------------------------------

class TestValidator:
    def test_validate_passes(self):
        v = Validator()
        rs = RuleSet("test", "commit")
        rs.add_rule(Rule("r1", r"^feat:", "needs feat prefix"))
        v.register(rs)
        result = v.validate("feat: hello", target="commit")
        assert result.passed

    def test_validate_fails(self):
        v = Validator()
        rs = RuleSet("test", "commit")
        rs.add_rule(Rule("r1", r"^feat:", "needs feat prefix"))
        v.register(rs)
        result = v.validate("oops: hello", target="commit")
        assert not result.passed
        assert len(result.violations) == 1

    def test_validate_unknown_target_passes(self):
        v = Validator()
        result = v.validate("anything", target="unknown")
        assert result.passed

    def test_validate_many(self):
        v = Validator()
        rs = RuleSet("test", "branch")
        rs.add_rule(Rule("r1", r"^feature/", "branch prefix"))
        v.register(rs)
        results = v.validate_many(
            ["feature/login", "bugfix/oops"], target="branch"
        )
        assert results[0].passed
        assert not results[1].passed

    def test_validate_all_targets(self):
        v = Validator()
        rs1 = RuleSet("commits", "commit")
        rs1.add_rule(Rule("r1", r"^feat:", "needs feat"))
        rs2 = RuleSet("branches", "branch")
        rs2.add_rule(Rule("r2", r"^feature/", "needs feature/"))
        v.register(rs1).register(rs2)
        results = v.validate_all_targets({
            "commit": ["feat: ok"],
            "branch": ["feature/x", "bad"],
        })
        assert len(results["commit"]) == 1
        assert len(results["branch"]) == 2
        assert results["commit"][0].passed
        assert not results["branch"][1].passed

    def test_get_targets(self):
        v = Validator()
        v.register(RuleSet("a", "commit"))
        v.register(RuleSet("b", "branch"))
        assert sorted(v.get_targets()) == ["branch", "commit"]

    def test_unregister(self):
        v = Validator()
        v.register(RuleSet("a", "commit"))
        assert v.unregister("a") is True
        assert v.get_targets() == []
        assert v.unregister("a") is False
