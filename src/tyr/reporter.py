"""
Reporting utilities for Tyr validation results.

Formats validation output as plain text, JSON, or GitHub-compatible
annotations.  Also provides Summary and SeverityCounter for aggregating
results across multiple validations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Dict

from tyr.core import ValidationResult, Severity


@dataclass
class SeverityCounter:
    """Counts violations by severity level."""

    errors: int = 0
    warnings: int = 0
    infos: int = 0

    @property
    def total(self) -> int:
        """Total number of violations across all severities."""
        return self.errors + self.warnings + self.infos

    def add(self, severity: Severity) -> None:
        """Increment the counter for the given severity."""
        if severity == Severity.ERROR:
            self.errors += 1
        elif severity == Severity.WARNING:
            self.warnings += 1
        else:
            self.infos += 1

    def as_dict(self) -> Dict[str, int]:
        """Serialize to a plain dictionary."""
        return {
            "errors": self.errors,
            "warnings": self.warnings,
            "infos": self.infos,
            "total": self.total,
        }


@dataclass
class Summary:
    """Aggregate statistics across multiple validation results."""

    total_inputs: int = 0
    passed: int = 0
    failed: int = 0
    counter: SeverityCounter = field(default_factory=SeverityCounter)

    def add_result(self, result: ValidationResult) -> None:
        """Incorporate a single validation result into the summary."""
        self.total_inputs += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        for violation in result.violations:
            self.counter.add(violation.severity)

    def as_dict(self) -> Dict:
        """Serialize to a plain dictionary."""
        return {
            "total_inputs": self.total_inputs,
            "passed": self.passed,
            "failed": self.failed,
            "violations": self.counter.as_dict(),
        }


class ValidationReporter:
    """Formats validation results for different output targets."""

    def __init__(self, results: List[ValidationResult] | None = None) -> None:
        self._results: List[ValidationResult] = list(results or [])

    def add(self, result: ValidationResult) -> None:
        """Append a validation result."""
        self._results.append(result)

    def add_many(self, results: List[ValidationResult]) -> None:
        """Append multiple results at once."""
        self._results.extend(results)

    # -- Summaries ----------------------------------------------------------

    def summary(self) -> Summary:
        """Build an aggregated summary across all stored results."""
        s = Summary()
        for r in self._results:
            s.add_result(r)
        return s

    # -- Text output --------------------------------------------------------

    def as_text(self, verbose: bool = False) -> str:
        """Render results as human-readable plain text.

        Args:
            verbose: If True, include info-level violations.
        """
        lines: List[str] = []
        for result in self._results:
            status = "PASS" if result.passed else "FAIL"
            lines.append(f"[{status}] ({result.target}) {result.input_value}")
            for v in result.violations:
                if not verbose and v.severity == Severity.INFO:
                    continue
                tag = v.severity.value.upper()
                lines.append(f"  {tag}: {v.message}")
        # Append summary line
        s = self.summary()
        lines.append(
            f"\n{s.total_inputs} checked, {s.passed} passed, "
            f"{s.failed} failed "
            f"({s.counter.errors}E / {s.counter.warnings}W / {s.counter.infos}I)"
        )
        return "\n".join(lines)

    # -- JSON output --------------------------------------------------------

    def as_json(self, indent: int = 2) -> str:
        """Render results as a JSON string."""
        payload = {
            "results": [r.as_dict() for r in self._results],
            "summary": self.summary().as_dict(),
        }
        return json.dumps(payload, indent=indent)

    # -- GitHub annotations -------------------------------------------------

    def as_github_annotations(self) -> List[Dict[str, str]]:
        """Produce a list of GitHub-compatible annotation dicts.

        Each annotation has keys: ``level``, ``message``, and ``title``.
        These can be used with the ``::error`` / ``::warning`` / ``::notice``
        workflow command syntax.
        """
        _severity_to_gh = {
            Severity.ERROR: "error",
            Severity.WARNING: "warning",
            Severity.INFO: "notice",
        }
        annotations: List[Dict[str, str]] = []
        for result in self._results:
            for v in result.violations:
                annotations.append({
                    "level": _severity_to_gh[v.severity],
                    "title": v.rule_name,
                    "message": v.message,
                })
        return annotations

    def as_github_commands(self) -> str:
        """Render violations as ``::error`` / ``::warning`` workflow commands."""
        lines: List[str] = []
        for ann in self.as_github_annotations():
            lines.append(
                f"::{ann['level']} title={ann['title']}::{ann['message']}"
            )
        return "\n".join(lines)
