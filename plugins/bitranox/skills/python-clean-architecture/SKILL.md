---
name: python-clean-architecture
description: Use when structuring Python 3.10+ projects with layered ports-and-adapters architecture, reviewing layer dependency violations, scaffolding domain-driven designs, deciding where code belongs across domain, application, adapter, and composition layers, or setting up ports, UoW, outbox, and idempotency patterns
---

# Layered Architecture for Python

## Overview

Framework-agnostic, typed Python architecture optimized for **change**, **testability**, and **clear boundaries**. Inner layers never import from outer layers. Domain stays pure.

**Primary goal:** Keep the cost of change low over the lifetime of the system. Business logic should be easy to understand, test, and evolve independently of infrastructure choices.

**Target:** Python >=3.10 | Typed | Pure domain | Framework-agnostic core | No compatibility shims

## When to Use

- Starting a new Python project that needs long-term maintainability
- Reviewing existing code for architecture violations (imports crossing layers)
- Deciding where a new class/function belongs (domain vs application vs adapter)
- Structuring data flow between external inputs, domain logic, and outputs
- Setting up testing strategy with proper isolation
- Implementing reliability patterns (UoW, outbox, idempotency)
- Refactoring framework-centric code to layered architecture

**When NOT to use:**
- Single-file scripts or throwaway prototypes (use SCRIPT mode -- see `script-mode.md`)
- Projects already using a different established architecture

## Layers & Dependency Rule

**Inner layers never import from outer layers.** Source code dependencies point inward only, toward more stable and abstract code.

Inner layers change less frequently and for more important reasons. Outer layers (I/O, formatting, frameworks) are plugins to the inner layers.

```
+------------------------------------------------------------+
|  Composition Root (outermost)                               |
|  compose.py, main entrypoints, framework wiring             |
|  +------------------------------------------------------+  |
|  |  Adapters                                             |  |
|  |  Route handlers, ORM repositories, Pydantic models,   |  |
|  |  message consumers, CLI parsers, HTTP clients          |  |
|  |  +------------------------------------------------+  |  |
|  |  |  Application                                    |  |  |
|  |  |  Use case classes, Protocol ports,               |  |  |
|  |  |  request/response dataclasses                    |  |  |
|  |  |  +------------------------------------------+   |  |  |
|  |  |  |  Domain                                   |   |  |  |
|  |  |  |  @dataclass(frozen=True) entities,         |   |  |  |
|  |  |  |  Value Objects, Domain Services,           |   |  |  |
|  |  |  |  Domain Events                             |   |  |  |
|  |  |  +------------------------------------------+   |  |  |
|  |  +------------------------------------------------+  |  |
|  +------------------------------------------------------+  |
+------------------------------------------------------------+
```

You may need more or fewer layers depending on complexity. The dependency rule always applies: dependencies point inward, abstraction increases inward.

| Layer                | Contains                                 | Rules                                                                       |
|----------------------|------------------------------------------|-----------------------------------------------------------------------------|
| **Domain**           | Entities, Value Objects, Domain Services | Pure, sync, no I/O, no logs, no frameworks                                  |
| **Application**      | Use Cases, Ports (`Protocol`s), DTOs     | Orchestrates domain + ports; no framework types                             |
| **Adapters**         | Transport, Persistence, Messaging        | Implements ports; maps DTOs <-> external formats                            |
| **Composition Root** | Wiring                                   | Binds adapters to ports per process; the only place that imports everything |

### Data Crossing Boundaries

Data passed across a boundary must always be in the form most convenient for the **inner** layer. Never pass ORM row structures or Pydantic request models inward -- adapters convert to domain types at the boundary.

### Domain vs Use Cases

|                  | Domain                                                      | Use Cases                                                          |
|------------------|-------------------------------------------------------------|--------------------------------------------------------------------|
| **Scope**        | Core business rules (exist without automation)              | Application-specific workflows (exist because system is automated) |
| **Change rate**  | Slowest                                                     | Faster (new features, workflow changes)                            |
| **Dependencies** | Know nothing about use cases                                | Depend on domain, never the reverse                                |
| **Python**       | `@dataclass(frozen=True, slots=True)` with business methods | Classes in `application/use_cases/` with `execute()`               |

Use case request/response models must be **independent** -- no framework types, no entity references, no knowledge of delivery mechanism.

## Domain-Centric Project Structure

Your top-level directory structure should tell readers about the **system**, not the **framework**. When new developers look at the project, their first impression should be "This is a lending platform" -- not "This is a FastAPI app."

**Bad** -- framework-centric:
```
src/api/routes/ middleware/ dependencies/ models/ schemas/ crud/
```

**Good** -- domain-centric:
```
src/lending_platform/
  loans/
    domain/         # Loan entity, Money VO, interest rules
    application/
      use_cases/    # create_loan.py, approve_loan.py
      ports/        # loan_repository.py, credit_check.py
    adapters/       # sqlalchemy_loan_repo.py, experian_credit.py
  customers/
    domain/ application/ adapters/
  composition/      # compose.py -- FastAPI only appears here
```

| Question                                                    | Good answer                               |
|-------------------------------------------------------------|-------------------------------------------|
| Can you tell what the system *does* from top-level folders? | Yes -- bounded contexts visible           |
| Can you tell what *framework* is used?                      | No -- hidden in adapters/composition      |
| Can you unit-test all use cases without any framework?      | Yes -- plain dataclasses + protocol ports |
| Could you swap the delivery mechanism (web -> CLI)?         | Yes -- add adapter, zero core changes     |

## Design Principles

Brief, practical guidelines for structuring modules in Python layered architecture.

**One actor per module.** Each use case serves one stakeholder group. If two different teams need changes to the same module, split it. Use a Facade if callers need a single entry point.

**Extend by adding, not by modifying.** New behavior should mean new adapters implementing existing ports, not editing use cases. New output format? New adapter -- zero changes to the use case.

**Honor port contracts.** All adapters implementing a port must satisfy the same behavioral contract. Verify via **contract tests** -- a single parameterized test suite run against every adapter implementation (in-memory, PostgreSQL, Redis). If any adapter needs special handling, the port contract is wrong.

**Keep ports narrow.** A `UserRepository` port with `find`, `save`, `delete`, `search`, `bulk_import`, `export_csv` serves too many consumers. Split into focused ports: `UserReader(Protocol)`, `UserWriter(Protocol)`. Each use case depends only on the port slice it needs.

**Depend on abstractions for volatile code.** Domain and application layers import only `Protocol`s and dataclasses. Stable things (stdlib, well-established libraries) are fine to depend on directly. The composition root is the only place that imports concrete adapter classes.

**Prefer immutability in the domain.** Use `@dataclass(frozen=True, slots=True)` for entities and value objects. Push mutable state to adapters where it belongs, protected by the Unit of Work pattern.

**Use `Protocol` to invert dependencies.** When the natural direction of a function call opposes the desired dependency direction, introduce a `Protocol` in the inner layer and implement it in the outer layer. This is what makes the dependency rule possible.

## Data Modeling

```
External Input -> Pydantic (validate) -> Dataclass (domain) -> Pydantic (serialize) -> Output
     (raw)         (adapter boundary)     (pure business logic)   (adapter boundary)      (JSON/API)
```

| Use Case            | Type                                  | Notes                                |
|---------------------|---------------------------------------|--------------------------------------|
| Domain entities/VOs | `@dataclass(frozen=True, slots=True)` | Pure, no deps                        |
| Internal DTOs       | `@dataclass`                          | When data already trusted            |
| Boundary validation | Pydantic `BaseModel`                  | Parse untrusted input, coerce types  |
| Serialization       | Pydantic `BaseModel`                  | `.model_dump()`, `.model_validate()` |
| Configuration       | Pydantic `BaseSettings`               | Env var parsing                      |

**Never:** Pass `dict[str, Any]` between modules or layers. Dicts acceptable only when: truly dynamic data, <3 keys, single function scope, no business logic.

## Core Patterns

### Ports (Application-owned Protocols)

```python
class PaymentPort(Protocol):
    async def charge(self, customer_id: str, amount: Money) -> str: ...
```

Ports are `Protocol`s in `application/ports/`. Adapters implement them. The business rules own the interface; adapters are **plugins**. See `port-contracts.md` for all standard port definitions (UoW, Outbox, IdempotencyStore, IdProvider, Clock).

### Unit of Work

```python
class UnitOfWork(Protocol[D]):
    async def run(self, fn: Callable[[D, RequestContext], Awaitable[T]], *, ctx: RequestContext | None = None) -> T: ...
```

- Runs callable inside transaction scope
- Supplies transaction-bound repos/adapters
- Never pass raw connections/locks into core

### Reliability Patterns

| Pattern           | Rule                                                           |
|-------------------|----------------------------------------------------------------|
| **Lock ordering** | Sort IDs before acquiring locks (prevents deadlocks)           |
| **Outbox**        | Persist events within same transaction; publish after commit   |
| **Idempotency**   | `run_once(key, fn)` with uniqueness guard                      |
| **Timeouts**      | `asyncio.wait_for(coro, timeout=)`; propagate `CancelledError` |

## Boundaries

### Plugin Architecture

The database and UI are *plugins* to the business rules. Core business rules are kept separate from, and independent of, components that are either optional or implemented in many different forms. All dependency arrows point inward.

```python
# Business rules own the interface (port)
class WikiPageRepository(Protocol):
    def find(self, slug: str) -> WikiPage | None: ...
    def save(self, page: WikiPage) -> None: ...

# Adapters are plugins -- each implements the same port
class InMemoryWikiPageRepo: ...     # development/testing plugin
class FileSystemWikiPageRepo: ...   # flat-file plugin
class PostgresWikiPageRepo: ...     # production plugin
```

The boundary sits at the `Protocol`. Business rules know nothing about which adapter is plugged in.

### Boundary Crossing Modes

| Mode                        | Mechanism                           | Cost       | Python example                            |
|-----------------------------|-------------------------------------|------------|-------------------------------------------|
| **Source-level** (monolith) | Function calls, same process        | Negligible | Standard `import` + `Protocol`            |
| **Deployment component**    | Separate pip packages, same process | Negligible | `myapp-domain`, `myapp-adapters-postgres` |
| **Local process**           | Sockets / IPC                       | Moderate   | FastAPI + Celery on same host             |
| **Service**                 | Network (HTTP/gRPC/messaging)       | High       | Separate deployments                      |

**Recommended approach:** Start at source-level. Push decoupling to where a service *could* be formed, but keep components in the same process. Escalate to deployment-level or service-level only when development, deployment, or operational issues demand it.

At runtime, boundary crossing is just a function call. The trick is managing *source code dependencies* so they always point toward the inner layer. Use `Protocol` to invert dependencies when control flow opposes the desired dependency direction.

### Partial Boundaries

Full boundaries are expensive. When the cost is too high, use a partial strategy:

| Strategy               | Inverted?     | When to use                                                                        |
|------------------------|---------------|------------------------------------------------------------------------------------|
| **Skip the Last Step** | Yes           | Full interface design, but keep both sides in same package. Expect to split later. |
| **Strategy Pattern**   | One direction | Single `Protocol` with concrete implementation. Most common in Python.             |
| **Facade**             | No            | Thin class grouping service calls. Unlikely to ever need full boundary.            |

**When to draw boundaries:** Watch for friction. Implement boundaries at the inflection point where the cost of implementing becomes less than the cost of ignoring. Review boundary decisions as the system evolves.

| Signal                                         | Action                                    |
|------------------------------------------------|-------------------------------------------|
| Two modules change for different reasons/rates | Draw boundary                             |
| You want to swap an implementation             | Draw boundary (introduce `Protocol`)      |
| Cross-team ownership                           | Draw boundary (independent deployability) |
| Single developer, no swap foreseeable          | Skip or use partial boundary              |

## I/O Boundary Isolation

Split behaviors that are **hard to test** from behaviors that are **easy to test** into two modules. The I/O-facing module contains hard-to-test behavior stripped to its barest essence; the logic module contains all extracted testable logic.

| Boundary              | I/O Side (thin)                      | Logic Side (testable)          |
|-----------------------|--------------------------------------|--------------------------------|
| **UI**                | View (template/renderer)             | Presenter (formats View Model) |
| **Database**          | Repository adapter (SQL/ORM)         | Use case + repository port     |
| **External services** | HTTP client adapter                  | Use case + service port        |
| **Message queues**    | Consumer adapter (deserialize + ack) | Use case + event handler       |

**Presenter example:**

```python
@dataclass
class LoanViewModel:
    principal_display: str    # "$1,234.56"
    rate_display: str         # "4.50%"
    is_overdue: bool
    status_label: str         # "Active" | "Defaulted"

class LoanPresenter:
    def present(self, loan: Loan, today: date) -> LoanViewModel:
        return LoanViewModel(
            principal_display=f"${loan.principal.to_decimal():,.2f}",
            rate_display=f"{loan.rate * 100:.2f}%",
            is_overdue=loan.next_due_date < today,
            status_label="Defaulted" if loan.is_defaulted else "Active",
        )
# View just renders the ViewModel -- zero logic, strings/bools only
```

**Principle:** At every architectural boundary, look for the opportunity to isolate I/O. Extract testable behavior into a module that works with simple data structures and protocol ports.

## Error Handling

| Layer               | Style                                                                                       |
|---------------------|---------------------------------------------------------------------------------------------|
| Domain/Application  | Raise domain exceptions                                                                     |
| Adapters/Boundaries | Catch -> map to result envelope `{"ok": False, "error": {"code": "...", "message": "..."}}` |
| Transport           | Map -> HTTP status / exit codes                                                             |

**Never** let raw exceptions leak to external consumers.

## Folder Layout

```
src/<pkg>/
  <bounded_context>/
    domain/        # entities.py, values.py, events.py, services.py
    application/
      use_cases/
      ports/       # uow.py, outbox.py, idempotency.py, id_provider.py, clock.py, <entity>_repository.py
    adapters/
      memory/      # in-memory implementations
      uow/
    platform/      # config.py, observability.py
  composition/     # compose.py (wiring)
  testing/         # Testing API (NOT deployed to production)
```

Flatten if single small domain; re-introduce `<bounded_context>/` on growth.

**Guardrails:** `domain` imports nothing outside `domain`. `application` imports `domain` and its own `ports`. `adapters` implement `application.ports` and map to/from domain DTOs. Composition wires everything.

Each package directory requires an `__init__.py` (can be empty). Omit only if using implicit namespace packages (PEP 420).

## Package Organization

Keep packages cohesive and their dependency graph clean:

- **Group by change reason.** Modules that change together belong in the same package. A requirement change should ideally touch only one package.
- **Split to reduce coupling.** If consumers only use a fraction of your package, split it. Don't force dependents to pull in modules they never import. Break fat `common/` packages into focused ones: `common_types`, `common_testing`, `common_infra`.
- **No cycles in import graphs.** Cycles make independent testing and reasoning impossible. Break cycles by introducing a `Protocol` in the inner layer or extracting shared types into a new package.
- **Stable packages should be abstract.** Packages with many dependents are hard to change -- protect them by making them mostly `Protocol`s and base types. Packages with few dependents can be concrete and change freely.
- **Enforce boundaries in Python.** Python lacks `package-private`. Use `import-linter` contracts, `_`-prefixed modules, `__all__` in `__init__.py`, and leading-underscore convention to enforce boundaries. Organization without encapsulation is just folder structure, not architecture.

Four packaging approaches from least to most robust:

| Approach                                     | Encapsulation | Recommended?                  |
|----------------------------------------------|---------------|-------------------------------|
| **By Layer** (web/, service/, data/)         | Weak          | No -- prototype only          |
| **By Feature** (orders/, billing/)           | Moderate      | Small projects                |
| **Ports & Adapters** (domain/, adapters/)    | Strong        | **Default choice**            |
| **By Component** (single facade per feature) | Best          | Monolith-to-microservice path |

## Cross-Bounded-Context Communication

Bounded contexts must not share domain internals. Choose one integration style per boundary:

| Style                     | When                                        | Mechanism                                                   |
|---------------------------|---------------------------------------------|-------------------------------------------------------------|
| **Domain Events**         | Eventual consistency acceptable             | Outbox -> message broker -> consumer adapter                |
| **Application Service**   | Synchronous query needed                    | Context A's adapter calls Context B's use case via port     |
| **Shared Kernel**         | Tight coupling justified (e.g., `Money` VO) | Shared `kernel/` package; both contexts depend inward on it |
| **Anti-Corruption Layer** | Integrating legacy/external systems         | Adapter translates external model to local domain model     |

**Rules:**
- Never import directly between `context_a.domain` and `context_b.domain`
- Shared kernel must be minimal and change-controlled
- Event contracts are owned by the publisher; consumers maintain their own projections
- Use import-linter independence contracts to enforce (see `review-checklists.md`)

## Independence & Decoupling

### Decoupling Layers (horizontal)

Separate things that change for different reasons: UI concerns change independently from business rules, which change independently from persistence details.

### Decoupling Use Cases (vertical)

Use cases are **narrow vertical slices** through all layers. Each use case changes at a different rate, for different reasons. Keep them separate: one module per use case in `application/use_cases/`.

### Decoupling Modes

| Mode                        | Communication                   | When to escalate                           |
|-----------------------------|---------------------------------|--------------------------------------------|
| **Source-level** (monolith) | Direct calls                    | Default starting point                     |
| **Deployment-level**        | Same process, separate packages | When teams need independent release cycles |
| **Service-level**           | Network calls                   | When operational scaling demands it        |

Start source-level. A good architecture allows sliding up *and back down* this spectrum without rewriting.

### True vs Accidental Duplication

| Type           | Definition                                                 | Action                                |
|----------------|------------------------------------------------------------|---------------------------------------|
| **True**       | Every change to one requires the same change to the other  | Eliminate -- extract shared code      |
| **Accidental** | Code looks similar *now* but evolves along different paths | **Do not unify** -- they will diverge |

**Common traps:** Two use cases with similar DTOs (accidental -- each serves different actors). A DB record that looks like a view model (accidental -- keep layers decoupled). Two contexts with similar `User` types (accidental -- will evolve independently). **Rule:** When separating use cases or layers, similar code is usually accidental duplication. Verify before unifying.

## Sync vs Async

The examples use `async` throughout. Adapt based on I/O profile:

| Profile                                     | Style                          | Notes                                       |
|---------------------------------------------|--------------------------------|---------------------------------------------|
| Network I/O dominant (APIs, DBs, messaging) | `async`                        | Use `asyncio`, `async def`, `await`         |
| CPU-bound or simple CLI tools               | Sync                           | Drop `async`/`await`; use regular functions |
| Mixed                                       | `async` with `run_in_executor` | Keep domain pure either way                 |

**Domain stays the same regardless:** pure, sync, no I/O. The choice affects application and adapter layers only. Ports can define sync or async methods -- pick one per project and stay consistent.

## Testing Strategy

| Type            | Purpose                                                     |
|-----------------|-------------------------------------------------------------|
| **Unit**        | Domain + use cases with in-memory adapters                  |
| **Contract**    | Same suite against all port implementations (parameterized) |
| **Integration** | Real infra via composition root                             |
| **E2E**         | Public surface (HTTP/CLI)                                   |

### The Test Boundary

Tests sit in the outermost layer -- nothing depends on them, but they depend inward. Tests that mirror production structure 1:1 (test class per production class) are structurally coupled and fragile. Refactoring production code breaks hundreds of tests.

**Solution:** Test through a **Testing API** -- a dedicated API that hides the structure of the application from tests.

### Testing API

The Testing API has **superpowers**: seed data directly, freeze time, bypass auth, force testable states. It is a superset of the application's use cases.

```python
# testing/api.py -- NOT deployed to production
class TestingAPI:
    def __init__(self, app: Application) -> None:
        self._app = app

    async def seed_user(self, user_id: str, name: str, role: str = "admin") -> User:
        """Bypass registration, create user directly."""
        ...

    def freeze_time(self, at: datetime) -> None:
        """Replace clock port with frozen clock."""
        self._app.clock = FrozenClock(at)

    async def execute_as(self, user_id: str, use_case, input):
        """Execute any use case as any user, bypassing auth."""
        ctx = RequestContext(user_id=user_id, roles=("admin",))
        return await use_case.execute(input, ctx=ctx)
```

```python
# tests/conftest.py
@pytest.fixture
async def api() -> TestingAPI:
    app = create_test_app()  # In-memory adapters, no real infra
    return TestingAPI(app)
```

**Test through behavior, not structure:**
```python
# GOOD: Tests business rules through the Testing API
class TestPlaceOrder:
    async def test_valid_order_succeeds(self, api: TestingAPI):
        await api.seed_user("u1", "Alice")
        order_id = await api.execute_as("u1", api.place_order, PlaceOrderCommand(...))
        assert order_id is not None
```

Keep the Testing API and its fakes/builders in a separate `testing/` package that is never included in production builds.

## Framework Isolation

### Keep Frameworks at the Edge

Frameworks want deep integration. Protect your core by keeping them in outer layers only.

| Risk                     | Description                                                             |
|--------------------------|-------------------------------------------------------------------------|
| Architecture pollution   | Framework asks you to inherit base classes into your entities/use cases |
| Outgrowing the framework | As your product matures, the framework's design fights you              |
| Evolution divergence     | Framework deprecates features you depend on                             |
| Lock-in                  | A better alternative appears, but you're stuck                          |

### The Solution: Constrain Framework Imports

| Principle                                          | Python application                                                                             |
|----------------------------------------------------|------------------------------------------------------------------------------------------------|
| Keep at arm's length                               | Framework imports only in `adapters/` and `composition/`, never in `domain/` or `application/` |
| Don't derive business objects from framework bases | Entities are plain `@dataclass`, not Django `Model` or SQLAlchemy `Base`                       |
| Use proxies in outer layers                        | Adapter classes wrap framework behavior and implement your ports                               |
| Let only composition root know the framework       | `compose.py` wires FastAPI/Django; it's the dirtiest module -- that's OK                       |

```python
# WRONG: Framework in domain
class Order(DeclarativeBase): ...  # Entity married to SQLAlchemy

# RIGHT: Framework stays in adapters
# domain/entities.py
@dataclass(frozen=True, slots=True)
class Order: ...

# adapters/persistence/models.py
class OrderModel(DeclarativeBase):
    def to_domain(self) -> Order: ...
    @classmethod
    def from_domain(cls, order: Order) -> "OrderModel": ...
```

**Frameworks you must depend on** (stdlib, `typing`, `dataclasses`): that's fine -- but it should be a *decision*, not an accident.

## Composition Root

The composition root is the outermost wiring point. Nothing depends on it -- it depends on everything.

**Responsibilities:** Create factories/strategies, wire concrete adapters to abstract ports, hand control to the application.

You can have multiple composition roots for different environments:

```python
# composition/main_prod.py
def create_app() -> Application:
    config = ProdConfig.from_env()
    return Application(uow=PostgresUoW(config.db_url), cache=RedisCache(config.redis_url))

# composition/main_test.py
def create_app() -> Application:
    return Application(uow=InMemoryUoW(), cache=InMemoryCache())

# composition/main_dev.py
def create_app() -> Application:
    return Application(uow=SqliteUoW(":memory:"), cache=InMemoryCache())
```

**The composition root is deliberately dirty.** It imports every concrete class so the rest of the system stays abstract. Keep it thin: parse config, construct, wire, start. No business logic.

## Deployment vs Architecture

Architecture is defined by boundaries and dependencies, not by process boundaries. Microservices are a **deployment choice**, not an architectural choice.

| Fallacy                                   | Reality                                                                |
|-------------------------------------------|------------------------------------------------------------------------|
| "Services are decoupled"                  | Still strongly coupled by shared data structures                       |
| "Services enable independent development" | Only if internal architecture is clean; monoliths can achieve the same |
| "Adding a new feature is easy"            | Cross-cutting features require coordinated changes across all services |

**Rule:** Start monolith with clean internal boundaries. Extract services only when you have a proven need for independent deployment. A well-structured monolith is architecturally superior to poorly structured microservices.

## Details (What Is NOT Architecture)

| Detail         | Why it's not architecture                                | Python implication                                               |
|----------------|----------------------------------------------------------|------------------------------------------------------------------|
| **Database**   | Just a mechanism to move data between disk and RAM       | Repository ports return domain dataclasses, never ORM models     |
| **Web / UI**   | An I/O device -- one of many delivery mechanisms         | Route handlers are thin adapters; no business logic in routes    |
| **Frameworks** | Tools for someone else's problems, not your architecture | Use in adapters/composition only; domain/application import none |

**Key distinction:** The *data* is architecturally significant. The *database* is not.

## Observability & Security

- **Structured logging** at adapter boundaries; thread `trace_id` via `contextvars`
- **Health** (`/health`) and **readiness** (`/ready`) checks when transport exists
- **RED metrics** (Rate, Errors, Duration) per use case/adapter
- Centralize config in one module; **never** read `os.environ` outside it
- AuthN/Z in adapters; pass `RequestContext` (claims/roles) to use cases
- PII/PHI boundary mappers **redact by default**

## Non-Negotiables Checklist

- [ ] Dependencies point inward only (enforced via `import-linter`)
- [ ] Domain pure (no I/O, logs, frameworks, mutable state)
- [ ] Use cases free of framework/driver types
- [ ] Request/response DTOs independent of entities and framework types
- [ ] UoW binds transaction-scoped repos
- [ ] Deterministic lock ordering for multi-aggregate ops
- [ ] Outbox + Idempotency implemented
- [ ] Boundary validation (Pydantic at edges)
- [ ] Money as integer minor units (cents)
- [ ] Observability hooks at boundaries (`trace_id` via contextvars)
- [ ] UoW generic over typed deps (`UnitOfWork[D]`); no `Mapping[str, Any]` for deps
- [ ] Domain events extend `DomainEvent` base TypedDict
- [ ] In-memory unit tests + contract test outline
- [ ] Top-level folders reveal the domain, not the framework
- [ ] Testing API with superpowers (seed, freeze time, bypass auth)
- [ ] No framework base classes in domain entities
- [ ] Package dependency graph is acyclic

## Operating Modes

| Mode         | Output                                                    | Reference                  |
|--------------|-----------------------------------------------------------|----------------------------|
| **GENERATE** | Full domain-first project with tests                      | See `canonical-example.md` |
| **REVIEW**   | Violations + PR-ready fix checklist                       | See `review-checklists.md` |
| **LIBRARY**  | Small public API, `py.typed`, deprecation policy, plugins | See `library-mode.md`      |
| **SCRIPT**   | Single file with logical layer sections                   | See `script-mode.md`       |

### Selecting a Mode

The agent selects the mode based on context:

| Signal                                            | Mode     |
|---------------------------------------------------|----------|
| "Create a new project/service/feature"            | GENERATE |
| "Review this code for architecture violations"    | REVIEW   |
| "Build a reusable library/SDK/package"            | LIBRARY  |
| Deliverable is a single file; no `pyproject.toml` | SCRIPT   |

If ambiguous, ask the user. A project may use multiple modes over its lifecycle (GENERATE initially, REVIEW on changes, LIBRARY if extracted).

## Import Enforcement (pyproject.toml)

```toml
[tool.importlinter]
root_package = "<pkg>"

[[tool.importlinter.contracts]]
name = "Clean layers"
type = "layers"
layers = ["<pkg>.domain", "<pkg>.application", "<pkg>.adapters"]

[[tool.importlinter.contracts]]
name = "No cross-context imports"
type = "independence"
modules = ["<pkg>.orders", "<pkg>.billing", "<pkg>.shipping"]
```

Multi-context: add per-context layering + independence contracts. See `review-checklists.md`.

## Refactoring Path (framework-centric -> layered architecture)

1. Extract domain to `.../domain/`
2. Move orchestration to use cases in `application/`
3. Define ports (`Protocol`s) for external needs
4. Wrap framework/infra as adapters
5. Add composition root and wire
6. Write contract tests for ports/adapters
7. Route handlers to use cases
8. Remove direct framework/ORM calls from core

## Common Mistakes

| Mistake                                  | Fix                                                                                         |
|------------------------------------------|---------------------------------------------------------------------------------------------|
| Importing ORM models in domain           | Domain uses plain dataclasses; adapters map to/from ORM                                     |
| Pydantic models in domain layer          | Pydantic at boundaries only; domain uses `@dataclass(frozen=True, slots=True)`              |
| Use case returns framework response      | Use case returns DTO; adapter maps to HTTP/CLI response                                     |
| Passing `dict[str, Any]` between layers  | Define typed dataclasses or Pydantic models at each boundary                                |
| Raw DB connections in use cases          | Use UoW pattern; use case receives transaction-bound repos                                  |
| Logging in domain entities               | Domain stays pure; observability hooks at adapter boundaries                                |
| Reading `os.environ` in core             | Centralize config parsing; inject via composition root                                      |
| Framework types leaking into ports       | Ports use stdlib types only (`Protocol`, `dataclass`, `TypedDict`)                          |
| Unifying accidentally similar DTOs       | Each use case gets its own request/response -- they serve different actors and will diverge |
| Passing entities across boundaries       | Use separate DTOs; entities and view models change for different reasons                    |
| Folder structure reveals framework       | Organize by bounded context, not by framework convention                                    |
| Starting with microservices              | Start monolith with clean boundaries; extract services when proven need exists              |
| Tests structurally coupled to production | Test through a Testing API that hides internal structure                                    |
| Premature boundary elimination           | Verify duplication is real before unifying; similar code often serves different actors      |

## Reference Files

| File                   | Content                                                             |
|------------------------|---------------------------------------------------------------------|
| `port-contracts.md`    | All standard Protocol definitions with full code                    |
| `canonical-example.md` | Complete Money Transfer example (domain through composition)        |
| `library-mode.md`      | Library/SDK development: public API, versioning, plugins, packaging |
| `script-mode.md`       | Single-file scripts: PEP 723, exit codes, logical layout            |
| `review-checklists.md` | All review checklists for REVIEW mode output                        |

## Glossary

| Term                    | Definition                                                                                  |
|-------------------------|---------------------------------------------------------------------------------------------|
| **Adapter**             | Concrete implementation of a port (transport/persistence/messaging); a plugin to the core   |
| **Application Layer**   | Use cases + port contracts (no framework types)                                             |
| **Boundary**            | A line separating software elements; restricts knowledge between sides                      |
| **Composition Root**    | Process bootstrap wiring adapters to ports; the outermost wiring point                      |
| **Domain**              | Pure business logic (entities, value objects, domain services); the most stable layer       |
| **DomainEvent**         | Base `TypedDict` all domain events extend (`type`, `v`, `id`, `at`)                         |
| **Outbox**              | Transactional event persistence for reliable publish-after-commit                           |
| **Partial Boundary**    | Lightweight boundary (strategy, facade) when full separation is too expensive               |
| **Plugin Architecture** | External details (DB, UI) are plugins to business rules via ports                           |
| **Port**                | Core-owned interface (`Protocol`) expressing an external dependency                         |
| **Testing API**         | Test-only API with superpowers (seed, freeze time, bypass auth) hiding production structure |
| **UoW**                 | Port scoping a transaction, yielding tx-bound adapters to a work function                   |
