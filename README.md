# Tyr -- Convention Validator

> **Norse Mythology**: Tyr is the God of Justice and Law | Automated naming convention validation for Git workflows

[![GitHub Pages](https://img.shields.io/badge/Live_Demo-Visit_Site-blue?style=for-the-badge)](https://MukundaKatta.github.io/tyr/)
[![GitHub](https://img.shields.io/github/license/MukundaKatta/tyr?style=flat-square)](LICENSE)

## Overview

Tyr validates branch names, commit messages, PR titles, and version strings against configurable rule sets. Rule-based validation with centralized rule management -- no external dependencies required.

**Tech Stack:** Python 3.9+, zero dependencies

## Features

- **Conventional Commits** -- validates commit messages (`feat:`, `fix:`, `docs:`, etc.)
- **Branch Naming** -- enforces `feature/`, `bugfix/`, `hotfix/` prefixes with optional ticket IDs
- **PR Title** -- checks length limits and prefix requirements
- **Semantic Version** -- validates `vX.Y.Z` strings with prerelease and build metadata support
- **Custom Rules** -- fluent `RuleBuilder` API for project-specific conventions
- **Multiple Output Formats** -- plain text, JSON, and GitHub Actions annotations

## Quick Start

```python
from tyr import Validator, ConventionalCommits, BranchNaming

validator = Validator()
validator.register(ConventionalCommits.rule_set())
validator.register(BranchNaming.rule_set())

result = validator.validate("feat: add user login", target="commit")
print(result.passed)  # True

result = validator.validate("wip/stuff", target="branch")
print(result.passed)  # False
```

## Reporting

```python
from tyr import ValidationReporter

reporter = ValidationReporter()
reporter.add(result)
print(reporter.as_text())
print(reporter.as_github_commands())
```

## Custom Rules

```python
from tyr import RuleBuilder, RuleSet, Validator, Severity

rule = (
    RuleBuilder("no-wip")
    .pattern(r"(?i)^wip")
    .description("WIP commits are not allowed")
    .severity(Severity.ERROR)
    .inverse(True)
    .build()
)

rule_set = RuleSet("custom", "commit")
rule_set.add_rule(rule)

v = Validator()
v.register(rule_set)
```

## Running Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

## Project Structure

```
tyr/
  src/tyr/
    __init__.py    -- Package exports
    core.py        -- Rule, RuleSet, Validator, ValidationResult
    rules.py       -- Built-in rule sets and RuleBuilder
    reporter.py    -- Text, JSON, and GitHub annotation output
  tests/
    test_core.py
    test_rules.py
    test_reporter.py
```

## License

MIT License

## Part of the Mythological Portfolio

This is project **#tyr** in the [100-project Mythological Portfolio](https://github.com/MukundaKatta) by Officethree Technologies.
