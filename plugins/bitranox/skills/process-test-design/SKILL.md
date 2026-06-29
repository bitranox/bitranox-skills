---
name: process-test-design
description: Use when writing, reviewing, or pruning tests - deciding unit vs integration vs e2e, whether to mock/monkeypatch or use the real dependency, which edge/adversarial inputs to cover (unusual UTF, emoji, CJK, binary, wrong types, oversized), why a test is flaky or order-dependent, or whether a test earns its keep. Keywords - mock, monkeypatch, fake, fixture, e2e, integration test, flaky, order-dependent, sleep, adversarial input, low-value test, coverage. For the red-green discipline see process-test-driven-development; for what to validate at a boundary see coding-input-sanitization.
---

# process-test-design

## Overview

How to write tests that are worth having: real behavior over mocks, the edge inputs that actually
break code, deterministic and order-independent, and no low-value filler. This is the WHAT-to-write
companion to `bitranox:process-test-driven-development` (the red-green-refactor discipline and the
mock anti-patterns) - follow that for WHEN/order; this for test design and quality.

**Core principle: a test must be able to fail for a real, specific reason.** A test that cannot fail
(asserts nothing, restates the implementation, or exercises a mock) is negative value - it adds
maintenance and false confidence. Test observable behavior at a boundary, not internals.

## Prefer real over mocked; mock only at the true edge

- **Default to integration / e2e against the real dependency** (real DB, real broker, real HTTP via a
  local server or recorded fixtures). In-memory fakes accept arguments the real service rejects, so
  green unit tests can still ship a broken contract. Treat the integration/e2e run as the proof.
- **Avoid monkeypatching. Use dependency injection.** Pass the collaborator in (a port/protocol) and
  substitute a real-ish fake or the real thing in tests. Reach for `monkeypatch`/patch only at a true
  external edge you cannot inject (a third-party global, the clock, the network) - never to reach into
  your own internals. Patching your own code is a design smell: make it injectable instead.
- **Fakes live behind the same interface as the real thing** (a `fake_*` implementation of the port),
  exercised by the same contract tests as the real adapter, so the fake cannot drift.
- See `bitranox:process-test-driven-development` -> `testing-anti-patterns.md` (testing the mock,
  test-only methods in production, incomplete mocks, integration-as-afterthought).

## Adversarial inputs at the boundary (the test side of sanitization)

For any function/endpoint at an application or facing-API boundary, test the input battery, not just
the happy path. (Validation rules: `bitranox:coding-input-sanitization`; full per-codepath matrix:
enumerate every variant/caller a path serves and cover each branch.)

| Axis           | Cover at least                                                                                       |
|----------------|------------------------------------------------------------------------------------------------------|
| Text / Unicode | empty, whitespace-only, very long; non-ASCII, accented, combining marks, RTL, zero-width, emoji, CJK |
| Bytes          | control chars, NUL byte, invalid UTF-8 / raw binary                                                  |
| Type           | wrong type (str where int, None, list where scalar), missing field, extra field                      |
| Numbers        | 0, -1, 1, max, off-by-one at every limit, overflow, NaN/inf where float                              |
| Size           | empty collection, one element, at the cap, over the cap (DoS bound)                                  |
| Structure      | malformed JSON, truncated payload, duplicate keys, deeply nested                                     |

Assert the SPECIFIC behavior (rejected with a typed error, normalized, or escaped) - not just "does
not crash".

## Deterministic and order-independent

- **No dependence on test execution order.** No shared mutable module/global state between tests; each
  test sets up and tears down its own world (fixtures). A test must pass run alone and in any order
  (green with random ordering on and off).
- **No real `sleep` for timing.** Poll a condition with a timeout (condition-based waiting), or inject
  the clock. A fixed `sleep(n)` is either flaky (too short) or slow (too long).
- **Inject time and randomness.** No bare `datetime.now()` / `random` / `uuid4` in code under test -
  pass a clock / seed so the test is reproducible.
- **No unmarked network / filesystem / external resource.** Those belong in integration tests
  (marked, opt-in), not the unit suite. The unit suite runs offline and identically every time.
- A flaky test is a bug in the test or the code, never "just re-run it" - fix the determinism.

## Run in a clean, project-correct environment

- **Run tests in the project's OWN venv, never the IDE's.** An ambient `VIRTUAL_ENV` (PyCharm, or carried
  over from another project's shell) silently hijacks the interpreter, so the suite runs against the
  wrong env. Isolate it: `env -u VIRTUAL_ENV uv run pytest` (mechanism + the bmk variant:
  `bitranox:coding-python-uv` "stray VIRTUAL_ENV"). "Fresh" = the project venv, isolated - only recreate
  (`uv venv --clear && uv sync`) when debugging suspected env corruption.
- **A wrong-venv failure masquerades as a code failure.** `ModuleNotFoundError` for a dep you know is
  installed, a flood of phantom type-check errors, or pip-audit CVEs for packages not in your tree are a
  WRONG-VENV smell, not a real defect. Before trusting such a failure, verify the interpreter:
  `uv run python -c "import sys; print(sys.executable)"` should point at `./.venv`. (Evidence before
  conclusions - see `bitranox:process-review-verification-before-completion`.)

## Prune low-value tests

Delete a test when it:
- asserts nothing (or only that no exception was raised, for logic that should assert a result),
- restates the implementation line-by-line (changes whenever the code changes, catches nothing),
- tests the language, framework, or a mock rather than your behavior,
- duplicates another test's coverage with no new branch.

Fewer, behavior-focused tests beat many brittle ones. Coverage percent is a smell detector, not a goal.

## Quick checklist

- [ ] Real dependency or an injected fake behind the real interface; monkeypatch only at a true edge
- [ ] Integration / e2e path exists and is the proof of the contract
- [ ] Boundary inputs covered (UTF/emoji/CJK/binary/wrong-type/oversized/edge numbers), asserting specific behavior
- [ ] Order-independent (passes alone and shuffled); no shared mutable state
- [ ] No real `sleep`; time/randomness injected; unit suite offline
- [ ] Run in the project venv, not the IDE's (`env -u VIRTUAL_ENV uv run ...`); a ModuleNotFound / phantom-type / pip-audit-noise failure is a wrong-venv smell, not a code bug
- [ ] One behavior per test; name states the behavior
- [ ] No test that cannot fail for a real reason

## Common mistakes

- **Mocking your own internals** instead of injecting them. Make the seam a port; pass a fake in.
- **Green units, broken contract.** Fakes accepted what the real service rejects. Add the integration test.
- **"It passes on my machine / re-run it."** Flakiness is a defect - fix order/timing/clock, do not retry.
- **Testing the happy path only.** The bugs live in the edge battery above.
- **Chasing 100% coverage** with assertion-free or impl-mirroring tests. Delete those; they hide rot.

## Cross-references

- `bitranox:process-test-driven-development` - red-green-refactor discipline + `testing-anti-patterns.md`.
- `bitranox:coding-input-sanitization` - what to validate/escape at the boundary (this skill is how to TEST it).
- Per-repo convention (bmk): `make test` (unit, offline) vs `make testintegration` (real resources);
  shared fixtures in `tests/conftest.py`.
