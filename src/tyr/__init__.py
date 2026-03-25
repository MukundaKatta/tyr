"""
Tyr - Automated naming convention validator for Git workflows.

Named after the Norse God of Justice and Law, Tyr enforces naming
conventions across branches, commits, and pull requests.
"""

from tyr.core import (
    Rule,
    RuleSet,
    ValidationResult,
    Violation,
    Validator,
    Severity,
)
from tyr.rules import (
    ConventionalCommits,
    BranchNaming,
    PRTitle,
    SemanticVersion,
    RuleBuilder,
)
from tyr.reporter import ValidationReporter, Summary, SeverityCounter

__version__ = "0.1.0"
__all__ = [
    "Rule",
    "RuleSet",
    "ValidationResult",
    "Violation",
    "Validator",
    "Severity",
    "ConventionalCommits",
    "BranchNaming",
    "PRTitle",
    "SemanticVersion",
    "RuleBuilder",
    "ValidationReporter",
    "Summary",
    "SeverityCounter",
]
