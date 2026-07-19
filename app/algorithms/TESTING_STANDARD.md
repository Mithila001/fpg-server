# Algorithm Testing Standard

## Purpose

This document defines the standard testing structure used by all algorithm modules within:

```text
app/algorithms/
```

The goal of this standard is to make every feature's testing setup feel familiar, predictable, and easy to maintain regardless of the feature being tested.

Every algorithm module should follow this standard unless there is a clear project-wide reason not to.

The standard intentionally defines only the common foundation shared by all algorithm modules. Individual features may extend their testing setup when necessary, but they should not change the responsibilities of the standard files or directories defined here.

---

# Standard Test Structure

Every algorithm feature should contain a `tests` directory with the following baseline structure.

```text
tests/
│
├── builders.py
├── conftest.py
├── debug.py
├── test_input_output.py
├── data/
└── output/
```

Additional files and helper modules may be added when required, but these should complement the standard rather than replace it.

---

# Core Files

## builders.py

### Purpose

Provide reusable builders for creating test objects.

Builders reduce duplicated setup code and make tests easier to read.

### Responsibilities

- Build valid default input objects.
- Hide unnecessary construction complexity.
- Support optional overrides.
- Create reusable helper functions for tests.

### Must Not

- Execute the feature being tested.
- Contain assertions.
- Produce debug output.
- Read or write output files.
- Depend on execution order.

---

## conftest.py

### Purpose

Provide shared pytest configuration and fixtures.

### Responsibilities

- Shared pytest fixtures.
- Monkeypatch helpers.
- Temporary directories.
- Common pytest setup.

### Must Not

- Contain business logic.
- Replace builders.
- Execute algorithm code during import.

---

## debug.py

### Purpose

Provide a manual execution entry point for the feature.

This script exists for debugging, experimentation, visualization, and inspecting algorithm behavior.

It is **not** an automated test.

### Responsibilities

Typical execution flow:

1. Build sample input.
2. Execute the feature.
3. Print useful information.
4. Generate visualizations if applicable.
5. Save generated artifacts.
6. Exit.

### Typical Outputs

- Visualizations
- Exported JSON
- Timing information
- Debug reports
- Intermediate algorithm state

### Must Not

- Contain pytest tests.
- Replace automated testing.
- Be imported by production code.

---

## test_input_output.py

### Purpose

Verify the public input/output contract of the feature.

This is the baseline smoke test that confirms the feature can execute successfully with valid input.

### Responsibilities

Typical checks include:

- Valid input is accepted.
- Execution completes successfully.
- Output object is returned.
- Output type is correct.
- Output contract is valid.

### Must Not

- Contain large numbers of unrelated behavioral tests.
- Replace feature-specific testing.

---

# Core Directories

## data/

### Purpose

Store reusable static test resources.

Typical contents:

- JSON
- YAML
- CSV
- Images
- Reference files
- Sample requests
- Expected outputs

### Must Not

Contain generated files.

---

## output/

### Purpose

Store generated artifacts created while debugging.

Typical contents:

- Visualizations
- Images
- Logs
- Timing reports
- Exported JSON
- Temporary debug artifacts

### Notes

This directory is intended for generated output only.

It should not contain source test data.

The directory should normally be excluded from version control.

---

# Builder Guidelines

Builders should always return valid objects by default.

Whenever possible, builders should expose optional parameters that allow tests to modify only the fields relevant to the current test.

Good:

```python
build_solver_input()

build_solver_input(room_count=6)

build_solver_input(width=140)
```

Avoid requiring every test to manually construct large object graphs.

Builders should prioritize readability over minimizing lines of code.

---

# Test Data Guidelines

Reusable sample data should be stored inside:

```text
tests/data/
```

Avoid embedding large dictionaries or JSON directly inside test files whenever the data may be reused.

Prefer meaningful sample datasets over artificially minimal examples whenever practical.

---

# Debug Output Guidelines

All generated artifacts should be written to:

```text
tests/output/
```

Examples include:

- PNG visualizations
- SVG visualizations
- JSON exports
- Debug logs
- Performance reports

Debug scripts should never overwrite source test data.

---

# Naming Conventions

The following names are standardized across every algorithm feature.

```text
builders.py
conftest.py
debug.py
test_input_output.py
data/
output/
```

Maintaining consistent naming allows developers to immediately understand the testing layout of any feature without learning feature-specific conventions.

---

# Feature Extensions

Algorithm modules are encouraged to add additional test files whenever appropriate.

Examples include:

```text
test_validation.py

test_scoring.py

test_geometry.py

test_constraints.py

test_post_processing.py
```

Additional helper modules may also be added when they improve organization.

However, the responsibilities of the standard files defined in this document should remain unchanged.

---

# General Principles

When writing tests for algorithm modules:

- Keep tests deterministic whenever practical.
- Prefer reusable builders over duplicated setup.
- Keep debugging separate from automated testing.
- Store reusable test data in `tests/data/`.
- Store generated artifacts in `tests/output/`.
- Keep test code easy to read.
- Avoid unnecessary complexity.
- Favor consistency across the project over feature-specific variations.

A developer familiar with one algorithm module should immediately understand the testing structure of every other algorithm module.