---
name: process-test-design
description: Use when writing, reviewing, or pruning tests in ANY language - deciding unit vs integration vs e2e, whether to mock/patch or use the real dependency, which edge/adversarial inputs to cover (unusual UTF, emoji, CJK, binary, wrong types, oversized), why a test is flaky or order-dependent, or whether a test earns its keep. Keywords - mock, monkeypatch, spy, stub, fake, fixture, e2e, integration test, flaky, order-dependent, sleep, adversarial input, low-value test, coverage, pytest, vitest, jest, go test, cargo test, bats. For the red-green discipline see process-test-driven-development; for what to validate at a boundary see coding-input-sanitization.
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

**Every principle here is language-neutral; only the mechanics differ.** Examples name Python where
one is needed, but the rules apply to any language - the per-ecosystem commands, seams, and tier
conventions are in "Per-language mechanics" below. When your language is not listed, map it by role
(what is the injection seam, what marks a test tier, what shuffles order) rather than assuming the
rule does not apply.

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
- **"Patch the network/clock" is the fallback, not the choice, when you own the caller.** If the code
  under test is yours, the collaborator IS injectable - inject it, even for a unit test, and keep the
  real call for the integration tier. Patching a global (`fetch`, the HTTP module, the clock) is
  correct only when nothing you own sits between the test and that global: third-party code you cannot
  change calls it, or the call is buried in a dependency. "It is an external edge" does not license
  patching a global you could have passed in.
- See `bitranox:process-test-driven-development` -> `testing-anti-patterns.md` (testing the mock,
  test-only methods in production, incomplete mocks, integration-as-afterthought).

## Per-language mechanics

Same rules, different handles. The "self-mock tell" column is what to grep for when auditing a suite:
it is the idiom that reaches into the code under test instead of injecting at a seam.

| Language        | Inject the seam as                | Self-mock tell (the anti-pattern)                                | Real dependency for the e2e tier        | Order / shuffle             |
|-----------------|-----------------------------------|------------------------------------------------------------------|-----------------------------------------|-----------------------------|
| Python          | constructor arg typed `Protocol`  | `monkeypatch.setattr(MyClass, "_method")`                        | testcontainers, a local server, `respx` | `pytest -p randomly`        |
| TypeScript / JS | constructor arg or interface      | `vi.spyOn(obj, "privateMethod")`, `jest.mock` of your own module | `node:http` server, MSW, testcontainers | `vitest --sequence.shuffle` |
| Go              | interface parameter               | package-level function var swapped in a test                     | `httptest.Server`, real DB in Docker    | `go test -shuffle=on`       |
| Rust            | generic param or `Box<dyn Trait>` | `#[cfg(test)]` branch inside production code                     | `wiremock`, a real DB behind a feature  | `cargo nextest run`         |
| Bash            | a command name/path variable      | redefining the function under test in the test                   | a stub binary earlier on `PATH`         | `bats` (isolate per file)   |

**Mark the tiers so a bare test run stays offline.** Every ecosystem needs a way to keep the
network/DB tests out of the default run; pick the project's and use it consistently: pytest markers
(`-m "not integration"`), a filename or directory convention (`*.e2e.test.ts`, `test/e2e/`), a
separate config or workspace project, Go build tags, Rust `#[ignore]`, a `bats` tag. State it in the
project's own docs so the split is discoverable - inventing a private convention per test file is
how the integration tier quietly stops running.

**What decides the tier is the dependency, not the realism.** A test belongs in the marked tier when
it needs something the machine does not already provide - an external service, a shared DB, Docker,
credentials, the real network - or when it is slow enough to hurt the default run. A dependency you
start and stop inside the test process (an ephemeral loopback HTTP server, a temp-file DB) is real
enough to prove the contract while staying offline, deterministic and fast, so it belongs in the
DEFAULT run. "Uses the real implementation" and "must be marked and skipped" are different
questions; answer them separately.

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

**How much is enough (the stopping rule).** Cover one case per BRANCH the code actually takes, not
one per input you can imagine. For each failure the code distinguishes - a different error type, a
different message, a different recovery - there is one test. Inputs the code handles identically get
one representative case between them. Applied to a thin HTTP wrapper: one non-2xx case if every
status is treated the same (two if 4xx and 5xx diverge), one malformed-body case, one
transport-failure case, and no more. When a caller only ever sees your declared error type, the test
that matters is the one asserting the raw underlying error was converted to it.

**The branch rule governs the axis table above.** An axis with no corresponding branch in the code
gets no test - if nothing bounds a number, an "at max / overflow" case asserts nothing you have
promised. But do not just drop it: a missing branch where the axis clearly applies (an unbounded
size or length reaching a real sink) is a CODE finding - report the absent validation rather than
writing a test that documents its absence.

## Deterministic and order-independent

- **No dependence on test execution order.** No shared mutable module/global state between tests; each
  test sets up and tears down its own world (fixtures). A test must pass run alone and in any order
  (green with random ordering on and off).
- **No real `sleep` for timing.** Poll a condition with a timeout (condition-based waiting), or inject
  the clock. A fixed `sleep(n)` is either flaky (too short) or slow (too long).
- **Inject time and randomness.** No bare now-clock, RNG, or UUID call in code under test - pass a
  clock / seed so the test is reproducible. (`datetime.now()`/`random`/`uuid4` in Python;
  `Date.now()`/`Math.random()`/`crypto.randomUUID()` in JS, or `vi.useFakeTimers()` at the edge;
  `time.Now`/`rand` in Go; `Instant::now`/`rand` in Rust; `$RANDOM`/`date` in Bash.)
- **No unmarked network / filesystem / external resource.** Those belong in integration tests
  (marked, opt-in), not the unit suite. The unit suite runs offline and identically every time.
- A flaky test is a bug in the test or the code, never "just re-run it" - fix the determinism.

## Run in a clean, project-correct environment

**The rule in any language: run against the project's OWN pinned toolchain, resolved from a lockfile,
never an ambient or global one.** Two runs that resolve different dependency versions turn a real
defect into "works on my machine" and an environment flake into a phantom bug. Per ecosystem: commit
the lockfile and install from it, not from the loose ranges (`uv sync` / `npm ci` not `npm install` /
`go mod download` with a committed `go.sum` / `cargo build --locked`), and pin the runtime version
(`requires-python`, `.nvmrc` or `engines`, the `go` directive, `rust-toolchain.toml`). An
environment-shaped failure - a missing module you know is installed, a flood of phantom type errors,
audit findings for packages not in your tree - is a wrong-environment smell to verify before you
trust it as a code bug.

Python specifics, where the trap is most common:

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
- **Keep `.venv` out of git.** The project venv is a per-machine build artifact - never commit it;
  gitignore it (and untrack it if it slipped in). Mechanics: `bitranox:compuse-git` "Don't track local
  build artifacts".

## Prune low-value tests

Delete a test when it:
- asserts nothing (or only that no exception was raised, for logic that should assert a result),
- restates the implementation line-by-line (changes whenever the code changes, catches nothing),
- tests the language, framework, or a mock rather than your behavior,
- duplicates another test's coverage with no new branch.

Fewer, behavior-focused tests beat many brittle ones. Coverage percent is a smell detector, not a goal.

**Never commit a test that asserts behavior the code does not have.** When docs promise something the
code never wired up (a documented cache nothing calls, a flag with no effect), the honest output is a
FINDING - the feature is missing or the doc is wrong - not a red test left in the suite. A permanently
failing test is a broken gate, and a skipped one is a comment that rots. Report the gap, and write the
test when the behavior lands.

## Quick checklist

- [ ] Real dependency or an injected fake behind the real interface; patch only where you own no seam
- [ ] Integration / e2e path exists and is the proof of the contract
- [ ] Test tiers marked so the default run stays offline, by the project's stated convention
- [ ] Boundary inputs covered (UTF/emoji/CJK/binary/wrong-type/oversized/edge numbers), asserting specific behavior
- [ ] Every error branch the code can raise has a test asserting the declared error type
- [ ] Order-independent (passes alone and shuffled); no shared mutable state
- [ ] No real `sleep`; time/randomness injected; unit suite offline
- [ ] Runs against the project's own locked toolchain, not an ambient/global one; an environment-shaped failure is a wrong-env smell, not a code bug (Python: `env -u VIRTUAL_ENV uv run ...`)
- [ ] One behavior per test; name states the behavior
- [ ] No test that cannot fail for a real reason

## Common mistakes

- **Mocking your own internals** instead of injecting them. Make the seam a port; pass a fake in.
- **Patching a global you could have injected.** "The network is an external edge" is not a licence to
  stub `fetch` when the caller is your own code - inject the collaborator and keep the real call for e2e.
- **Inventing a private tier convention per file.** If the project has no stated way to mark
  integration tests, add one and document it; an undiscoverable tier is a tier that stops running.
- **Green units, broken contract.** Fakes accepted what the real service rejects. Add the integration test.
- **"It passes on my machine / re-run it."** Flakiness is a defect - fix order/timing/clock, do not retry.
- **Testing the happy path only.** The bugs live in the edge battery above.
- **Chasing 100% coverage** with assertion-free or impl-mirroring tests. Delete those; they hide rot.
- **Single-layer mutation stays green (defense in depth).** Disabling ONE validation check can leave its test green because a LATER check rejects the same bad input, so the test looks like coverage it lacks. Mutate the single layer first; if it stays green, find which later check absorbed it - the test is asserting a contract no single mutation can break, so prove it by disabling the whole defense stack in ONE mutation.

## Cross-references

- `bitranox:process-test-driven-development` - red-green-refactor discipline + `testing-anti-patterns.md`.
- `bitranox:coding-input-sanitization` - what to validate/escape at the boundary (this skill is how to TEST it).
- Per-repo convention (bmk): `make test` (unit, offline) vs `make testintegration` (real resources);
  shared fixtures in `tests/conftest.py`.
