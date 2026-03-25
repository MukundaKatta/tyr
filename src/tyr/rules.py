"""
Built-in rule sets and a fluent rule builder for Tyr.

Provides ready-made conventions:
- ConventionalCommits: validates commit messages (feat/fix/docs/... prefix)
- BranchNaming: validates branch names (feature/bugfix/hotfix prefix)
- PRTitle: validates pull-request titles (length + prefix)
- SemanticVersion: validates semver strings (vX.Y.Z)

Also provides RuleBuilder for constructing custom rules with a fluent API.
"""

from __future__ import annotations

from typing import Optional, Callable, List

from tyr.core import Rule, RuleSet, Severity


# ---------------------------------------------------------------------------
# Built-in rule factories
# ---------------------------------------------------------------------------

class ConventionalCommits:
    """Factory for Conventional Commits rule set.

    Rules enforce the pattern: ``type(scope)?: description``
    where *type* is one of feat, fix, docs, style, refactor, perf, test,
    build, ci, chore, revert.
    """

    TYPES = (
        "feat", "fix", "docs", "style", "refactor",
        "perf", "test", "build", "ci", "chore", "revert",
    )

    @classmethod
    def rule_set(cls, strict: bool = False) -> RuleSet:
        """Create the Conventional Commits rule set.

        Args:
            strict: When True, the scope and description format are also
                checked with error severity.  When False those extra checks
                are warnings only.
        """
        rs = RuleSet(
            name="conventional-commits",
            target="commit",
            description="Conventional Commits specification for commit messages.",
        )

        types_pattern = "|".join(cls.TYPES)

        # Primary rule: type prefix is required
        rs.add_rule(Rule(
            name="cc-type-prefix",
            pattern=rf"^({types_pattern})(\(.+\))?!?:\s",
            description=(
                "Commit message must start with a valid type prefix "
                "followed by a colon and space."
            ),
            severity=Severity.ERROR,
        ))

        # Description must not be empty
        rs.add_rule(Rule(
            name="cc-non-empty-description",
            pattern=rf"^({types_pattern})(\(.+\))?!?:\s.+",
            description="Commit message must have a non-empty description after the prefix.",
            severity=Severity.ERROR,
        ))

        # Optional: description should start lowercase
        rs.add_rule(Rule(
            name="cc-lowercase-description",
            pattern=rf"^({types_pattern})(\(.+\))?!?:\s[a-z]",
            description="Description should start with a lowercase letter.",
            severity=Severity.WARNING if not strict else Severity.ERROR,
        ))

        # Optional: message length hint
        def _check_length(value: str) -> Optional[str]:
            first_line = value.split("\n", 1)[0]
            if len(first_line) > 72:
                return (
                    f"First line is {len(first_line)} characters; "
                    f"keep it under 72 for readability."
                )
            return None

        rs.add_rule(Rule(
            name="cc-line-length",
            pattern=".*",  # always matches — real logic in custom_validator
            description="First line should be 72 characters or fewer.",
            severity=Severity.WARNING if not strict else Severity.ERROR,
            custom_validator=_check_length,
        ))

        return rs


class BranchNaming:
    """Factory for branch-naming convention rules.

    Enforces patterns like ``feature/PROJ-123-short-desc``.
    """

    PREFIXES = ("feature", "bugfix", "hotfix", "release", "chore", "docs")

    @classmethod
    def rule_set(
        cls,
        prefixes: Optional[List[str]] = None,
        require_ticket: bool = False,
    ) -> RuleSet:
        """Create the branch-naming rule set.

        Args:
            prefixes: Allowed branch prefixes. Defaults to PREFIXES.
            require_ticket: If True, require a ticket ID segment
                (e.g. ``PROJ-123``) after the prefix.
        """
        allowed = prefixes or list(cls.PREFIXES)
        prefix_pattern = "|".join(allowed)

        rs = RuleSet(
            name="branch-naming",
            target="branch",
            description="Branch naming convention with type prefixes.",
        )

        # Prefix rule
        rs.add_rule(Rule(
            name="bn-prefix",
            pattern=rf"^({prefix_pattern})/",
            description=(
                f"Branch name must start with one of: "
                f"{', '.join(allowed)} followed by '/'."
            ),
            severity=Severity.ERROR,
        ))

        # Slug format after prefix
        rs.add_rule(Rule(
            name="bn-slug-format",
            pattern=r"^[a-z]+/[a-zA-Z0-9._-]+$",
            description=(
                "Branch name after the prefix should use alphanumeric "
                "characters, hyphens, dots, or underscores only."
            ),
            severity=Severity.WARNING,
        ))

        # No double slashes
        rs.add_rule(Rule(
            name="bn-no-double-slash",
            pattern=r"//",
            description="Branch name must not contain consecutive slashes.",
            severity=Severity.ERROR,
            inverse=True,
        ))

        if require_ticket:
            rs.add_rule(Rule(
                name="bn-ticket-id",
                pattern=rf"^({prefix_pattern})/[A-Z]+-[0-9]+",
                description=(
                    "Branch name must include a ticket ID "
                    "(e.g. PROJ-123) after the prefix."
                ),
                severity=Severity.ERROR,
            ))

        # Length check
        def _branch_length(value: str) -> Optional[str]:
            if len(value) > 100:
                return (
                    f"Branch name is {len(value)} characters; "
                    f"keep it under 100."
                )
            return None

        rs.add_rule(Rule(
            name="bn-max-length",
            pattern=".*",
            description="Branch name should be 100 characters or fewer.",
            severity=Severity.WARNING,
            custom_validator=_branch_length,
        ))

        return rs


class PRTitle:
    """Factory for pull-request title convention rules."""

    @classmethod
    def rule_set(
        cls,
        max_length: int = 80,
        require_prefix: bool = True,
    ) -> RuleSet:
        """Create the PR title rule set.

        Args:
            max_length: Maximum allowed title length.
            require_prefix: Whether a type prefix (feat/fix/...) is required.
        """
        rs = RuleSet(
            name="pr-title",
            target="pr",
            description="Pull-request title conventions.",
        )

        if require_prefix:
            types = "|".join(ConventionalCommits.TYPES)
            rs.add_rule(Rule(
                name="pr-type-prefix",
                pattern=rf"^({types})(\(.+\))?!?:\s",
                description=(
                    "PR title must start with a conventional type prefix."
                ),
                severity=Severity.ERROR,
            ))

        # Max length
        def _title_length(value: str) -> Optional[str]:
            if len(value) > max_length:
                return (
                    f"PR title is {len(value)} characters; "
                    f"maximum is {max_length}."
                )
            return None

        rs.add_rule(Rule(
            name="pr-max-length",
            pattern=".*",
            description=f"PR title should be at most {max_length} characters.",
            severity=Severity.ERROR,
            custom_validator=_title_length,
        ))

        # Non-empty after prefix
        rs.add_rule(Rule(
            name="pr-non-empty",
            pattern=r"\S",
            description="PR title must not be empty or whitespace-only.",
            severity=Severity.ERROR,
        ))

        # No trailing punctuation
        rs.add_rule(Rule(
            name="pr-no-trailing-period",
            pattern=r"\.$",
            description="PR title should not end with a period.",
            severity=Severity.WARNING,
            inverse=True,
        ))

        return rs


class SemanticVersion:
    """Factory for semantic version validation rules."""

    @classmethod
    def rule_set(cls, allow_v_prefix: bool = True) -> RuleSet:
        """Create the semantic-version rule set.

        Args:
            allow_v_prefix: If True, an optional leading 'v' is accepted.
        """
        rs = RuleSet(
            name="semantic-version",
            target="version",
            description="Semantic Versioning 2.0.0 format.",
        )

        prefix = r"v?" if allow_v_prefix else ""
        semver_core = r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        prerelease = r"(-((0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(\.(0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
        build_meta = r"(\+([0-9a-zA-Z-]+(\.[0-9a-zA-Z-]+)*))?"
        full_pattern = rf"^{prefix}{semver_core}{prerelease}{build_meta}$"

        rs.add_rule(Rule(
            name="sv-format",
            pattern=full_pattern,
            description="Must be a valid Semantic Version (e.g. v1.2.3, 0.1.0-alpha).",
            severity=Severity.ERROR,
        ))

        # No leading zeros in numeric parts (already handled by the regex
        # above, but we add an explicit info-level hint for clarity)
        rs.add_rule(Rule(
            name="sv-no-leading-zeros",
            pattern=r"(?<!\d)0\d+",
            description="Numeric version parts must not have leading zeros.",
            severity=Severity.INFO,
            inverse=True,
        ))

        return rs


# ---------------------------------------------------------------------------
# Fluent rule builder
# ---------------------------------------------------------------------------

class RuleBuilder:
    """Fluent API for building custom Rule instances.

    Example::

        rule = (
            RuleBuilder("my-rule")
            .pattern(r"^fix:")
            .description("Must start with 'fix:'")
            .severity(Severity.ERROR)
            .build()
        )
    """

    def __init__(self, name: str) -> None:
        self._name = name
        self._pattern: str = ".*"
        self._description: str = ""
        self._severity: Severity = Severity.ERROR
        self._inverse: bool = False
        self._custom_validator: Optional[Callable[[str], Optional[str]]] = None

    def pattern(self, regex: str) -> "RuleBuilder":
        """Set the regex pattern."""
        self._pattern = regex
        return self

    def description(self, text: str) -> "RuleBuilder":
        """Set the human-readable description."""
        self._description = text
        return self

    def severity(self, level: Severity) -> "RuleBuilder":
        """Set the violation severity."""
        self._severity = level
        return self

    def as_warning(self) -> "RuleBuilder":
        """Shortcut: set severity to WARNING."""
        self._severity = Severity.WARNING
        return self

    def as_info(self) -> "RuleBuilder":
        """Shortcut: set severity to INFO."""
        self._severity = Severity.INFO
        return self

    def inverse(self, flag: bool = True) -> "RuleBuilder":
        """Set inverse matching (input must NOT match)."""
        self._inverse = flag
        return self

    def custom(self, fn: Callable[[str], Optional[str]]) -> "RuleBuilder":
        """Attach a custom validator function."""
        self._custom_validator = fn
        return self

    def build(self) -> Rule:
        """Construct the Rule instance."""
        return Rule(
            name=self._name,
            pattern=self._pattern,
            description=self._description,
            severity=self._severity,
            inverse=self._inverse,
            custom_validator=self._custom_validator,
        )
