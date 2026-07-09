# ADR-001: Automated Test Architecture for Context Pipeline

## Status
Approved

## Context
As the KNX AI Smart Home project moves forward (Sprint 10.5 and beyond), the number of tests is expected to grow to 100-200. Previously, tests were grouped in a few generic files (`test_sprint10.py`, `verify_sprint10.py`). This monolithic approach led to spaghetti tests, difficulty in isolating issues, and a lack of clear test boundaries.

## Decision
We decided to adopt a multi-layered testing architecture based on `pytest`:
1. **`tests/legacy/`**: Houses all deprecated validation scripts.
2. **`tests/unit/`**: Broken down by domain (`repositories/`, `builders/`, `workers/`). Tests pure business logic (Token Optimizer, Thread Builder, Prompt Builder) using mocks.
3. **`tests/integration/`**: Tests the interaction between components (e.g., Coordinator -> Builder -> Repository) and external dependencies (SQLite DB, Queue).
4. **`tests/performance/`**: Collects baselines (latency, throughput) without enforcing Pass/Fail thresholds during early validation.

## Alternatives Considered
- Keeping everything in `tests/` and prefixing files. *Consequence:* Hard to navigate.
- Combining unit and integration tests. *Consequence:* Slower test suites and flaky tests due to hidden side effects.

## Consequences
- **Positive:** Clear boundaries; we know exactly where to put new tests in Sprint 11+.
- **Positive:** Tests can be run selectively (`pytest tests/unit/`).
- **Negative:** Slightly more boilerplate required (e.g., deep directory structures, `conftest.py`).

## Approved By
User (via Constitution update phase 4)

## Date
2026-07-09
