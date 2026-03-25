"""Tests for tyr.rules — built-in rule sets and RuleBuilder."""

import pytest
from tyr.core import Validator, Severity
from tyr.rules import (
    ConventionalCommits,
    BranchNaming,
    PRTitle,
    SemanticVersion,
    RuleBuilder,
)


# -- ConventionalCommits -----------------------------------------------------

class TestConventionalCommits:
    @pytest.fixture()
    def validator(self):
        v = Validator()
        v.register(ConventionalCommits.rule_set())
        return v

    def test_valid_feat(self, validator):
        r = validator.validate("feat: add user login", target="commit")
        assert r.passed

    def test_valid_fix_with_scope(self, validator):
        r = validator.validate("fix(auth): handle expired tokens", target="commit")
        assert r.passed

    def test_valid_breaking_change(self, validator):
        r = validator.validate("feat!: remove old API", target="commit")
        assert r.passed

    def test_invalid_prefix(self, validator):
        r = validator.validate("added: new button", target="commit")
        assert not r.passed

    def test_missing_colon_space(self, validator):
        r = validator.validate("feat add login", target="commit")
        assert not r.passed

    def test_empty_description(self, validator):
        r = validator.validate("feat: ", target="commit")
        assert not r.passed

    def test_long_line_warns(self, validator):
        msg = "feat: " + "a" * 80
        r = validator.validate(msg, target="commit")
        assert r.has_warnings

    def test_uppercase_description_warns(self, validator):
        r = validator.validate("feat: Add login", target="commit")
        assert r.has_warnings

    def test_strict_mode(self):
        v = Validator()
        v.register(ConventionalCommits.rule_set(strict=True))
        r = v.validate("feat: Add login", target="commit")
        # In strict mode, uppercase description is an error
        assert not r.passed

    def test_all_types_accepted(self, validator):
        for t in ConventionalCommits.TYPES:
            r = validator.validate(f"{t}: do something", target="commit")
            assert r.passed, f"Type '{t}' should be accepted"


# -- BranchNaming ------------------------------------------------------------

class TestBranchNaming:
    @pytest.fixture()
    def validator(self):
        v = Validator()
        v.register(BranchNaming.rule_set())
        return v

    def test_valid_feature_branch(self, validator):
        r = validator.validate("feature/add-login", target="branch")
        assert r.passed

    def test_valid_bugfix_branch(self, validator):
        r = validator.validate("bugfix/fix-crash", target="branch")
        assert r.passed

    def test_invalid_prefix(self, validator):
        r = validator.validate("wip/stuff", target="branch")
        assert not r.passed

    def test_double_slash_fails(self, validator):
        r = validator.validate("feature//bad", target="branch")
        assert not r.passed

    def test_long_branch_warns(self, validator):
        name = "feature/" + "a" * 100
        r = validator.validate(name, target="branch")
        assert r.has_warnings

    def test_ticket_id_required(self):
        v = Validator()
        v.register(BranchNaming.rule_set(require_ticket=True))
        r = v.validate("feature/add-login", target="branch")
        assert not r.passed
        r2 = v.validate("feature/PROJ-123-add-login", target="branch")
        assert r2.passed

    def test_custom_prefixes(self):
        v = Validator()
        v.register(BranchNaming.rule_set(prefixes=["dev", "staging"]))
        assert v.validate("dev/thing", target="branch").passed
        assert not v.validate("feature/thing", target="branch").passed


# -- PRTitle -----------------------------------------------------------------

class TestPRTitle:
    @pytest.fixture()
    def validator(self):
        v = Validator()
        v.register(PRTitle.rule_set())
        return v

    def test_valid_pr_title(self, validator):
        r = validator.validate("feat: add login page", target="pr")
        assert r.passed

    def test_too_long(self, validator):
        title = "feat: " + "x" * 80
        r = validator.validate(title, target="pr")
        assert not r.passed

    def test_trailing_period_warns(self, validator):
        r = validator.validate("feat: add login.", target="pr")
        assert r.has_warnings

    def test_empty_title_fails(self, validator):
        r = validator.validate("   ", target="pr")
        assert not r.passed

    def test_no_prefix_required(self):
        v = Validator()
        v.register(PRTitle.rule_set(require_prefix=False))
        r = v.validate("add login page", target="pr")
        assert r.passed


# -- SemanticVersion ---------------------------------------------------------

class TestSemanticVersion:
    @pytest.fixture()
    def validator(self):
        v = Validator()
        v.register(SemanticVersion.rule_set())
        return v

    def test_simple_version(self, validator):
        assert validator.validate("1.0.0", target="version").passed

    def test_v_prefix(self, validator):
        assert validator.validate("v2.3.4", target="version").passed

    def test_prerelease(self, validator):
        assert validator.validate("1.0.0-alpha.1", target="version").passed

    def test_build_metadata(self, validator):
        assert validator.validate("1.0.0+build.42", target="version").passed

    def test_invalid_version(self, validator):
        assert not validator.validate("1.0", target="version").passed

    def test_no_v_prefix_mode(self):
        v = Validator()
        v.register(SemanticVersion.rule_set(allow_v_prefix=False))
        assert not v.validate("v1.0.0", target="version").passed
        assert v.validate("1.0.0", target="version").passed


# -- RuleBuilder -------------------------------------------------------------

class TestRuleBuilder:
    def test_basic_build(self):
        rule = (
            RuleBuilder("my-rule")
            .pattern(r"^fix:")
            .description("Must start with fix:")
            .build()
        )
        assert rule.name == "my-rule"
        assert rule.validate("fix: something") is None
        assert rule.validate("feat: something") is not None

    def test_warning_severity(self):
        rule = (
            RuleBuilder("warn-rule")
            .pattern(r"^todo", )
            .description("Should not start with todo")
            .as_warning()
            .inverse(True)
            .build()
        )
        assert rule.severity == Severity.WARNING
        assert rule.inverse is True

    def test_info_severity(self):
        rule = RuleBuilder("info-rule").as_info().build()
        assert rule.severity == Severity.INFO

    def test_custom_validator(self):
        rule = (
            RuleBuilder("custom")
            .custom(lambda v: "nope" if "bad" in v else None)
            .build()
        )
        assert rule.validate("good") is None
        assert rule.validate("bad input") == "nope"
