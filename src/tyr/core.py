"""
Core validation engine for Tyr.

Provides the foundational data structures and validation logic:
- Rule: a single naming convention rule with a regex pattern
- RuleSet: a named collection of rules for a specific target
- Validator: applies rule sets to input strings and collects results
- ValidationResult / Violation: structured output from validation
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Callable, Pattern


class Severity(Enum):
    """Severity levels for rule violations."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Parse a severity from its string representation.

        Args:
            value: One of 'error', 'warning', or 'info' (case-insensitive).

        Returns:
            The corresponding Severity enum member.

        Raises:
            ValueError: If the value does not match a known severity.
        """
        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(
            f"Unknown severity '{value}'. "
            f"Expected one of: {', '.join(m.value for m in cls)}"
        )


@dataclass(frozen=True)
class Rule:
    """A single naming convention rule.

    Attributes:
        name: Short identifier for the rule (e.g. 'conventional-prefix').
        pattern: Regex pattern that the input *must* match to pass.
        description: Human-readable explanation of the rule.
        severity: How serious a violation of this rule is.
        inverse: If True, the input must *not* match the pattern to pass.
        custom_validator: Optional callable for logic beyond regex matching.
            Receives the input string and returns an error message or None.
    """

    name: str
    pattern: str
    description: str
    severity: Severity = Severity.ERROR
    inverse: bool = False
    custom_validator: Optional[Callable[[str], Optional[str]]] = None

    def __post_init__(self) -> None:
        """Validate that the pattern compiles as a valid regex."""
        try:
            re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(
                f"Rule '{self.name}' has an invalid regex pattern "
                f"'{self.pattern}': {exc}"
            ) from exc

    @property
    def compiled_pattern(self) -> "Pattern[str]":
        """Return the compiled regex pattern."""
        return re.compile(self.pattern)

    def validate(self, value: str) -> Optional[str]:
        """Check *value* against this rule.

        Returns:
            An error message string if the rule is violated, or None if it passes.
        """
        # Run custom validator first if present
        if self.custom_validator is not None:
            custom_msg = self.custom_validator(value)
            if custom_msg is not None:
                return custom_msg

        match = self.compiled_pattern.search(value)
        if self.inverse:
            if match:
                return (
                    f"Value '{value}' must NOT match pattern "
                    f"'{self.pattern}': {self.description}"
                )
        else:
            if not match:
                return (
                    f"Value '{value}' does not match pattern "
                    f"'{self.pattern}': {self.description}"
                )
        return None


@dataclass(frozen=True)
class Violation:
    """A single rule violation produced during validation.

    Attributes:
        rule_name: The name of the rule that was violated.
        message: Human-readable explanation of the violation.
        severity: The severity inherited from the rule.
        input_value: The original string that was validated.
    """

    rule_name: str
    message: str
    severity: Severity
    input_value: str

    def as_dict(self) -> Dict[str, str]:
        """Serialize the violation to a plain dictionary."""
        return {
            "rule": self.rule_name,
            "message": self.message,
            "severity": self.severity.value,
            "input": self.input_value,
        }


@dataclass
class ValidationResult:
    """Aggregated result of validating one input against a rule set.

    Attributes:
        input_value: The original string that was validated.
        target: The rule-set target name (e.g. 'branch', 'commit').
        violations: All violations found during validation.
    """

    input_value: str
    target: str
    violations: List[Violation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if there are no error-level violations."""
        return not any(v.severity == Severity.ERROR for v in self.violations)

    @property
    def has_warnings(self) -> bool:
        """True if there are warning-level violations."""
        return any(v.severity == Severity.WARNING for v in self.violations)

    @property
    def error_count(self) -> int:
        """Number of error-level violations."""
        return sum(1 for v in self.violations if v.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        """Number of warning-level violations."""
        return sum(1 for v in self.violations if v.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        """Number of info-level violations."""
        return sum(1 for v in self.violations if v.severity == Severity.INFO)

    def add_violation(self, violation: Violation) -> None:
        """Append a violation to the result."""
        self.violations.append(violation)

    def as_dict(self) -> Dict:
        """Serialize the result to a plain dictionary."""
        return {
            "input": self.input_value,
            "target": self.target,
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "violations": [v.as_dict() for v in self.violations],
        }


class RuleSet:
    """A named collection of rules for a specific validation target.

    Attributes:
        name: Identifier for this rule set (e.g. 'conventional-commits').
        target: What the rules apply to ('branch', 'commit', 'pr', etc.).
        description: Human-readable purpose of this rule set.
    """

    def __init__(
        self,
        name: str,
        target: str,
        description: str = "",
    ) -> None:
        self.name = name
        self.target = target
        self.description = description
        self._rules: List[Rule] = []

    @property
    def rules(self) -> List[Rule]:
        """Return a copy of the rules list."""
        return list(self._rules)

    def add_rule(self, rule: Rule) -> "RuleSet":
        """Add a rule to the set. Returns self for chaining."""
        self._rules.append(rule)
        return self

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name. Returns True if found and removed."""
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) < before

    def get_rule(self, name: str) -> Optional[Rule]:
        """Look up a rule by name."""
        for rule in self._rules:
            if rule.name == name:
                return rule
        return None

    def __len__(self) -> int:
        return len(self._rules)

    def __iter__(self):
        return iter(self._rules)

    def __repr__(self) -> str:
        return (
            f"RuleSet(name={self.name!r}, target={self.target!r}, "
            f"rules={len(self._rules)})"
        )


class Validator:
    """Applies one or more rule sets to input strings.

    Usage::

        validator = Validator()
        validator.register(my_rule_set)
        result = validator.validate("feat: add login", target="commit")
    """

    def __init__(self) -> None:
        self._rule_sets: Dict[str, List[RuleSet]] = {}

    def register(self, rule_set: RuleSet) -> "Validator":
        """Register a rule set. Returns self for chaining."""
        target = rule_set.target
        if target not in self._rule_sets:
            self._rule_sets[target] = []
        self._rule_sets[target].append(rule_set)
        return self

    def unregister(self, name: str, target: Optional[str] = None) -> bool:
        """Remove a rule set by name, optionally scoped to a target."""
        found = False
        targets = [target] if target else list(self._rule_sets.keys())
        for t in targets:
            if t in self._rule_sets:
                before = len(self._rule_sets[t])
                self._rule_sets[t] = [
                    rs for rs in self._rule_sets[t] if rs.name != name
                ]
                if len(self._rule_sets[t]) < before:
                    found = True
                if not self._rule_sets[t]:
                    del self._rule_sets[t]
        return found

    def get_targets(self) -> List[str]:
        """Return all registered target names."""
        return list(self._rule_sets.keys())

    def get_rule_sets(self, target: str) -> List[RuleSet]:
        """Return rule sets registered for a given target."""
        return list(self._rule_sets.get(target, []))

    def validate(self, value: str, target: str) -> ValidationResult:
        """Validate *value* against all rule sets for *target*.

        Args:
            value: The string to validate (branch name, commit message, etc.).
            target: Which category of rules to apply.

        Returns:
            A ValidationResult with any violations found.
        """
        result = ValidationResult(input_value=value, target=target)
        rule_sets = self._rule_sets.get(target, [])

        for rule_set in rule_sets:
            for rule in rule_set:
                error_msg = rule.validate(value)
                if error_msg is not None:
                    result.add_violation(
                        Violation(
                            rule_name=rule.name,
                            message=error_msg,
                            severity=rule.severity,
                            input_value=value,
                        )
                    )

        return result

    def validate_many(
        self, values: List[str], target: str
    ) -> List[ValidationResult]:
        """Validate multiple values against the same target.

        Args:
            values: Strings to validate.
            target: Target category.

        Returns:
            A list of ValidationResult objects, one per input.
        """
        return [self.validate(v, target) for v in values]

    def validate_all_targets(
        self, values_by_target: Dict[str, List[str]]
    ) -> Dict[str, List[ValidationResult]]:
        """Validate values across multiple targets at once.

        Args:
            values_by_target: Mapping of target name to list of input strings.

        Returns:
            Mapping of target name to list of ValidationResult objects.
        """
        results: Dict[str, List[ValidationResult]] = {}
        for target, values in values_by_target.items():
            results[target] = self.validate_many(values, target)
        return results
