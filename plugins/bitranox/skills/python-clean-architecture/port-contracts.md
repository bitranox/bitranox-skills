# Port Contracts — Standard Protocol Definitions

Reference `Protocol`s for application-layer ports. All ports live in `application/ports/`.

> **Usage examples:** `canonical-example.md` | **Layer rules:** `SKILL.md` | **Review checks:** `review-checklists.md`

---

## UnitOfWork

```python
# src/<pkg>/<bc>/application/ports/uow.py
from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from typing import Protocol, TypeVar

T = TypeVar("T")
D = TypeVar("D")

@dataclass(slots=True)
class RequestContext:
    """Cross-cutting request metadata."""
    trace_id: str | None = None
    user_id: str | None = None
    roles: tuple[str, ...] = ()

class UnitOfWork(Protocol[D]):
    """Transactional boundary for coordinating repository operations.

    Generic over D: a TypedDict describing transaction-bound deps.
    Each use case defines its own deps type for full type safety.
    """

    async def run(
        self,
        fn: Callable[[D, RequestContext], Awaitable[T]],
        *,
        ctx: RequestContext | None = None,
        timeout: float | None = None,
    ) -> T:
        """Execute fn within a transactional scope.

        Args:
            fn: Async callable receiving typed, transaction-bound deps and context.
            ctx: Request metadata for tracing and authorization.
            timeout: Maximum seconds before cancellation.

        Returns:
            The value returned by fn.

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout.
            Exception: Any exception from fn propagates after rollback.
        """
        ...
```

---

## Outbox

```python
# src/<pkg>/<bc>/application/ports/outbox.py
from collections.abc import Sequence
from typing import Protocol
from .uow import RequestContext
from ...domain.events import DomainEvent  # base TypedDict defined in domain layer

class Outbox(Protocol):
    """Store domain events within the current transaction for later publishing."""

    async def add_all(
        self, events: Sequence[DomainEvent], *, ctx: RequestContext | None = None
    ) -> None:
        """Persist events to the outbox within the active transaction.

        Args:
            events: Typed domain events to store for subsequent publication.
            ctx: Request context for tracing correlation.

        Note:
            Events are published by a separate worker after commit.
            DomainEvent is the base TypedDict from domain/events.py;
            concrete events (e.g., FundsTransferred) extend it.
        """
        ...
```

---

## IdempotencyStore

```python
# src/<pkg>/<bc>/application/ports/idempotency.py
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

T = TypeVar("T")

class IdempotencyStore(Protocol):
    """Guard against duplicate command execution."""

    async def run_once(
        self,
        key: str,
        fn: Callable[[], Awaitable[T]],
        *,
        ttl_seconds: int | None = None,
    ) -> T:
        """Execute fn only if key has not been seen before.

        Args:
            key: Unique identifier for the operation (e.g., request ID).
            fn: Async callable to execute if key is new.
            ttl_seconds: How long to remember the key; None means forever.

        Returns:
            Result of fn on first call, or cached/default on duplicates.

        Note:
            Implementations should use a unique constraint (DB key or set)
            to guarantee exactly-once semantics.
        """
        ...
```

---

## IdProvider

```python
# src/<pkg>/<bc>/application/ports/id_provider.py
from typing import Protocol

class IdProvider(Protocol):
    """Generate unique identifiers for domain entities and events."""

    def __call__(self) -> str:
        """Return a new unique identifier string (UUID hex, ULID, nanoid)."""
        ...
```

---

## Clock

```python
# src/<pkg>/<bc>/application/ports/clock.py
from datetime import datetime, timezone
from typing import Protocol

class Clock(Protocol):
    """Provide the current time; injectable for testing."""

    def now(self) -> datetime:
        """Return the current UTC datetime (timezone-aware)."""
        ...

def system_clock() -> Clock:
    """Create a clock that returns real system time."""
    class _Clock:
        def now(self) -> datetime:
            return datetime.now(timezone.utc)
    return _Clock()
```

---

## Domain-Specific Repository (example)

```python
# src/<pkg>/<bc>/application/ports/account_repository.py
from collections.abc import Sequence
from typing import Protocol
from ...domain.entities import Account
from ...application.ports.uow import RequestContext

class AccountRepository(Protocol):
    """Port for account persistence operations."""

    async def find_by_id(
        self, id: str, *, ctx: RequestContext | None = None
    ) -> Account | None:
        """Retrieve an account by its identifier."""
        ...

    async def find_pair_for_update(
        self, id_a: str, id_b: str, *, ctx: RequestContext | None = None
    ) -> Sequence[Account]:
        """Fetch two accounts with pessimistic locking.

        Acquires locks in deterministic order (sorted IDs) to prevent deadlocks.
        """
        ...

    async def save_many(
        self, accounts: Sequence[Account], *, ctx: RequestContext | None = None
    ) -> None:
        """Persist multiple accounts within the current transaction."""
        ...
```

Keep domain-specific repos **narrow** (`find/save`, `find_pair_for_update`). Add new repos in `application/ports/` as needed.
