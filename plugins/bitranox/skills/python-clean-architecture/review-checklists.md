# Review Checklists — REVIEW Mode Output

Use these checklists when auditing code against layered ports-and-adapters architecture. Report violations with severity, location, and concrete fix.

> **Architecture rules:** `SKILL.md` | **Correct port patterns:** `port-contracts.md` | **Reference implementation:** `canonical-example.md`

---

## How to Report

For each violation found:

1. **Location:** File and line (or module path)
2. **Severity:** CRITICAL / HIGH / MEDIUM / LOW
3. **Violation:** What rule is broken
4. **Fix:** Concrete, actionable refactor step

Example:

> **[HIGH] `src/app/orders/use_cases/place_order.py:12`** — Imports `sqlalchemy.orm.Session` (framework type in application layer). **Fix:** Define `UnitOfWork` port in `application/ports/`; inject via composition root.

---

## Severity Levels

| Severity     | Meaning                                                | Examples                                                                 |
|--------------|--------------------------------------------------------|--------------------------------------------------------------------------|
| **CRITICAL** | Breaks architectural invariants; must fix before merge | Domain imports adapter; raw DB in use case; framework types in ports     |
| **HIGH**     | Significant boundary violation; fix in current PR      | `dict[str, Any]` between layers; logging in domain; `os.environ` in core |
| **MEDIUM**   | Degraded maintainability; fix within sprint            | Missing contract tests; overly broad port; no idempotency on mutation    |
| **LOW**      | Style or improvement opportunity                       | Missing `slots=True`; naming convention; could extract value object      |

---

## Architecture

| #  | Check                                                    | Severity | Example Violation                                    |
|----|----------------------------------------------------------|----------|------------------------------------------------------|
| A1 | Inward dependencies only; no outer types in core         | CRITICAL | `from ..adapters.db import engine` in use case       |
| A2 | Use cases small, single-purpose; no I/O in domain        | HIGH     | `requests.get()` inside domain service               |
| A3 | Ports are narrow and cohesive                            | MEDIUM   | One port with 15 methods spanning unrelated concerns |
| A4 | Domain is pure: no framework imports, no logging, no I/O | CRITICAL | `import logging` or `import django` in domain        |
| A5 | Adapters implement only declared ports                   | MEDIUM   | Adapter adds public methods not on any port          |

## Reliability

| #  | Check                                                   | Severity | Example Violation                                                      |
|----|---------------------------------------------------------|----------|------------------------------------------------------------------------|
| R1 | UoW binds tx-scoped repos; no raw tx/locks in core      | HIGH     | `connection.begin()` in use case                                       |
| R2 | Deterministic lock ordering for multi-aggregate updates | HIGH     | Locking accounts in request order instead of sorted ID order           |
| R3 | Outbox persists events within tx; publisher exists      | MEDIUM   | Publishing events directly in use case without transactional guarantee |
| R4 | Idempotency with uniqueness guarantee and TTL           | MEDIUM   | No idempotency key on state-mutating endpoints                         |

## Boundaries

| #  | Check                                                   | Severity | Example Violation                                              |
|----|---------------------------------------------------------|----------|----------------------------------------------------------------|
| B1 | Inputs validated at the edge; DTOs mapped               | HIGH     | Raw `request.json` dict passed to use case                     |
| B2 | Money handled as integer minor units; no float leakage  | HIGH     | `price: float` in domain entity                                |
| B3 | No `dict[str, Any]` flowing between modules/layers      | HIGH     | Use case returns `dict[str, Any]` to transport                 |
| B4 | Domain events extend typed base; no `Mapping[str, Any]` | MEDIUM   | Outbox accepts `list[dict]` instead of `Sequence[DomainEvent]` |

## Observability & Security

| #  | Check                                                     | Severity | Example Violation                                    |
|----|-----------------------------------------------------------|----------|------------------------------------------------------|
| O1 | Tracing/logging at boundaries with `trace_id`             | MEDIUM   | No correlation ID threaded through request lifecycle |
| O2 | Config centralized; no `os.environ` in core               | HIGH     | `os.getenv("DB_URL")` in repository adapter          |
| O3 | AuthZ enforced in adapter; `RequestContext` passed inward | HIGH     | Role check inside domain entity                      |
| O4 | Health/ready checks present if transport exists           | LOW      | HTTP service with no `/health` endpoint              |
| O5 | PII/PHI redacted by default at boundary mappers           | MEDIUM   | User email logged in plain text at adapter boundary  |

## Tests

| #  | Check                                                       | Severity | Example Violation                                       |
|----|-------------------------------------------------------------|----------|---------------------------------------------------------|
| T1 | Unit + Contract tests present                               | MEDIUM   | Only integration tests exist                            |
| T2 | In-memory adapters for unit tests                           | MEDIUM   | Unit tests hit real database                            |
| T3 | Contract tests parameterized across adapter implementations | LOW      | Tests only cover memory adapter, not production adapter |
| T4 | Testing API available (seed, freeze time, bypass auth)      | LOW      | Tests use `time.sleep()` and real clock                 |

## Error Handling

| #  | Check                                                                   | Severity | Example Violation                                       |
|----|-------------------------------------------------------------------------|----------|---------------------------------------------------------|
| E1 | Stable result envelope at boundaries                                    | MEDIUM   | Different error shapes across endpoints                 |
| E2 | Domain errors mapped at boundary; no transport exceptions leaked inward | HIGH     | `HTTPException` raised inside use case                  |
| E3 | Error codes documented and stable across versions                       | LOW      | Error codes change between releases without deprecation |

---

## Import Enforcement

Multi-context example:
```toml
[[tool.importlinter.contracts]]
name = "Layering within <bounded_context>"
type = "layers"
layers = [
  "<pkg>.<bounded_context>.domain",
  "<pkg>.<bounded_context>.application",
  "<pkg>.<bounded_context>.adapters",
]

[[tool.importlinter.contracts]]
name = "Context independence (core)"
type = "independence"
modules = [
  "<pkg>.accounts.domain",
  "<pkg>.payments.domain",
  "<pkg>.accounts.application",
  "<pkg>.payments.application",
]
```

Flat (single domain):
```toml
[[tool.importlinter.contracts]]
name = "Clean layers (flat)"
type = "layers"
layers = ["<pkg>.domain", "<pkg>.application", "<pkg>.adapters"]
```
