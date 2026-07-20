# Testing Architecture

The `test/` directory contains multiple categories of tests. These categories have different responsibilities and must remain independent.

IMPORTANT: THIS IS NOT `pytest suite`, this is intentionally just a runnable script to check if the implemented setup work or not in more focus way, not a testing framework.

---

## Overview

```text
test/
├── algorithms/
│   ├── candidate_search/
│   ├── candidate_scoring/
│   ├── floor_plan_solver/
│   ├── floor_plan_scoring/
│   └── ...
│
└── flow-test/
```

The two sections serve different purposes.

---

# test/algorithms/

This directory contains tests for individual algorithm features.

Each feature is tested in complete isolation.

The objective is to verify that a single algorithm behaves correctly when provided with realistic inputs.

These tests should validate the feature itself, not the interaction between multiple features.

Typical responsibilities include:

- validating inputs
- validating outputs
- exercising the complete public API
- testing important execution paths
- verifying realistic behaviour
- producing debug JSON outputs
- using a mock environment instead of the full application pipeline

Each feature owns its own testing assets such as:

- builders
- mock data
- fixtures
- debug helpers
- output directory

Feature tests must not depend on another feature's test code.

For example:

Candidate Search tests should not import Candidate Scoring test utilities.

Floor Plan Solver tests should not depend on Candidate Search tests.

Every feature test should be executable independently.

---

# test/flow-test/

This directory contains integration tests between multiple algorithms.

The objective is to verify that independent features work correctly when connected together.

Flow tests simulate small portions of the real generation pipeline while still running inside a lightweight mock environment.

These are **not** end-to-end application tests.

Instead, they validate feature-to-feature integration.

Examples:

- Candidate Search → Candidate Scoring
- Preprocessing → Candidate Search
- Solver → Floor Plan Scoring
- Post Processing → Opening Generation

Flow tests should:

- use the real algorithm implementations
- connect multiple features together
- verify data compatibility between stages
- verify that outputs from one stage are valid inputs for the next
- validate the overall flow behaviour
- print useful debugging information
- avoid requiring the API, database, background workers, or full server infrastructure

---

# Separation Rules

The two testing categories must remain independent.

Specifically:

- `test/algorithms` must never depend on `test/flow-test`.
- `test/flow-test` must never import helper code from `test/algorithms`.
- Mock builders, fixtures, and helper functions should stay local to the test category that owns them.
- Shared production code should always come from `app/...`, never from another test folder.

If a flow test needs mock data, create it inside `test/flow-test`.

Do not reuse testing utilities from feature-specific tests.

---

# Mock Environment

Unless explicitly testing the production pipeline, tests should execute in a mock environment.

This means:

- no FastAPI server
- no API routes
- no background jobs
- no database
- no SSE
- no external services

Only the algorithm modules required for the test should be executed.

The goal is fast, deterministic, and easily debuggable tests.

---

# Adding New Tests

When creating a new test:

Choose `test/algorithms` if:

- only one feature is being tested
- the focus is correctness of that feature
- dependencies are mocked or locally created

Choose `test/flow-test` if:

- multiple algorithms are connected
- the focus is integration
- data flows between stages
- behaviour across the flow is being verified

Do not mix these two responsibilities.