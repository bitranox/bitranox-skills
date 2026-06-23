# Canonical Example — Money Transfer (Pure Python)

Apply this pattern to any multi-aggregate state transition that emits events.

> **Implements:** GENERATE mode from `SKILL.md` | **Ports:** `port-contracts.md` | **Review:** `review-checklists.md`

---

## Domain

### Value Objects

```python
# src/<pkg>/accounts/domain/values.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

Currency: TypeAlias = Literal["USD","EUR","GBP"]

@dataclass(frozen=True, slots=True)
class Money:
    """Immutable monetary value with currency enforcement."""
    cents: int
    currency: Currency

    def __post_init__(self) -> None:
        if self.cents < 0:
            raise ValueError("Invalid cents")

    def plus(self, other: Money) -> Money:
        self._cur(other)
        return Money(self.cents + other.cents, self.currency)

    def minus(self, other: Money) -> Money:
        self._cur(other)
        if self.cents < other.cents:
            raise ValueError("Insufficient funds")
        return Money(self.cents - other.cents, self.currency)

    def _cur(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError("Currency mismatch")
```

### Entities

```python
# src/<pkg>/accounts/domain/entities.py
from dataclasses import dataclass
from .values import Money

@dataclass(slots=True)
class Account:
    """Bank account entity with balance management."""
    id: str
    balance: Money

    def withdraw(self, amount: Money) -> None:
        self.balance = self.balance.minus(amount)

    def deposit(self, amount: Money) -> None:
        self.balance = self.balance.plus(amount)
```

### Events

```python
# src/<pkg>/accounts/domain/events.py
from typing import TypedDict
from .values import Currency

class DomainEvent(TypedDict):
    """Base fields every domain event must carry."""
    type: str
    v: int
    id: str
    at: str  # ISO-8601

class FundsTransferred(DomainEvent):
    """Event emitted when funds move between accounts."""
    from_id: str
    to_id: str
    amount_cents: int
    currency: Currency
```

---

## Use Case

```python
# src/<pkg>/accounts/application/use_cases/transfer_funds.py
from collections.abc import Awaitable, Callable
from typing import TypedDict
from ...application.ports.uow import UnitOfWork, RequestContext
from ...application.ports.outbox import Outbox
from ...application.ports.account_repository import AccountRepository
from ...application.ports.id_provider import IdProvider
from ...application.ports.clock import Clock
from ...application.ports.idempotency import IdempotencyStore
from ...domain.values import Money, Currency
from ...domain.events import FundsTransferred

class TransferFundsInput(TypedDict):
    from_id: str
    to_id: str
    amount_cents: int
    currency: Currency
    idempotency_key: str

class TransferDeps(TypedDict):
    """Transaction-bound dependencies for the transfer use case."""
    account_repo: AccountRepository
    outbox: Outbox

def create_transfer_funds(
    *,
    uow: UnitOfWork[TransferDeps],
    id_provider: IdProvider,
    clock: Clock,
    idempotency: IdempotencyStore,
) -> Callable[[TransferFundsInput, RequestContext | None], Awaitable[dict[str, bool]]]:
    """Factory to create transfer_funds use case with injected dependencies."""

    async def transfer_funds(
        input: TransferFundsInput, ctx: RequestContext | None = None
    ) -> dict[str, bool]:
        if input["from_id"] == input["to_id"]:
            raise ValueError("Same account")
        amount = Money(input["amount_cents"], input["currency"])

        async def work(deps: TransferDeps, _ctx: RequestContext) -> dict[str, bool]:
            account_repo = deps["account_repo"]
            outbox = deps["outbox"]

            # Deterministic lock order to prevent deadlocks
            lo, hi = sorted((input["from_id"], input["to_id"]))
            pair = await account_repo.find_pair_for_update(lo, hi, ctx=_ctx)
            if len(pair) != 2:
                raise ValueError("Account not found")
            a, b = pair
            from_acct = a if a.id == input["from_id"] else b
            to_acct = b if from_acct is a else a

            if (
                from_acct.balance.currency != amount.currency
                or to_acct.balance.currency != amount.currency
            ):
                raise ValueError("Currency mismatch")

            from_acct.withdraw(amount)
            to_acct.deposit(amount)
            await account_repo.save_many([from_acct, to_acct], ctx=_ctx)

            evt: FundsTransferred = {
                "type": "FundsTransferred",
                "v": 1,
                "id": id_provider(),
                "from_id": input["from_id"],
                "to_id": input["to_id"],
                "amount_cents": amount.cents,
                "currency": amount.currency,
                "at": clock.now().isoformat(),
            }
            await outbox.add_all([evt], ctx=_ctx)
            return {"ok": True}

        return await idempotency.run_once(
            key=f"transfer:{input['from_id']}:{input['to_id']}:{input['idempotency_key']}",
            fn=lambda: uow.run(work, ctx=(ctx or RequestContext())),
        )

    return transfer_funds
```

---

## In-Memory Adapters (pure stdlib)

### Account Repository

```python
# src/<pkg>/accounts/adapters/memory/account_repository.py
import asyncio
from collections.abc import Sequence
from ...domain.entities import Account

def make_memory_account_repo(state: dict[str, Account]):
    """In-memory account repository backed by a dict."""
    locks: dict[str, asyncio.Lock] = {}

    def _lock(key: str) -> asyncio.Lock:
        lock = locks.get(key)
        if lock is None:
            lock = locks.setdefault(key, asyncio.Lock())
        return lock

    class _Repo:
        async def find_by_id(self, id: str, *, ctx=None) -> Account | None:
            return state.get(id)

        async def find_pair_for_update(
            self, id_a: str, id_b: str, *, ctx=None
        ) -> Sequence[Account]:
            # NOTE: Locks released before save_many. Safe for single-threaded
            # test scenarios. Production adapters hold locks until tx commit.
            lo, hi = sorted((id_a, id_b))
            async with _lock(lo):
                async with _lock(hi):
                    a, b = state.get(lo), state.get(hi)
                    if a is None or b is None:
                        return []
                    return [Account(a.id, a.balance), Account(b.id, b.balance)]

        async def save_many(self, accounts: Sequence[Account], *, ctx=None) -> None:
            for acc in accounts:
                state[acc.id] = acc

    return _Repo()
```

### Outbox

```python
# src/<pkg>/accounts/adapters/memory/outbox.py
from collections.abc import Sequence
from ...domain.events import DomainEvent

def make_memory_outbox(storage: list[DomainEvent] | None = None):
    events = storage if storage is not None else []

    class _Outbox:
        async def add_all(self, evts: Sequence[DomainEvent], *, ctx=None) -> None:
            events.extend(evts)

    return _Outbox()
```

### Idempotency

```python
# src/<pkg>/accounts/adapters/memory/idempotency.py
def make_memory_idempotency():
    seen: set[str] = set()

    class _Idem:
        async def run_once(self, key: str, fn, *, ttl_seconds: int | None = None):
            if key in seen:
                return {"ok": True}
            seen.add(key)
            return await fn()

    return _Idem()
```

### Unit of Work

```python
# src/<pkg>/accounts/adapters/uow/memory_uow.py
import asyncio
from collections.abc import Callable, Mapping
from typing import Any
from ...application.ports.uow import RequestContext

def make_memory_uow(*, deps_factory: Callable[[], Mapping[str, Any]]):
    class _UoW:
        async def run(self, fn, *, ctx: RequestContext | None = None, timeout: float | None = None):
            deps = dict(deps_factory())
            coro = fn(deps, ctx or RequestContext())
            if timeout is None:
                return await coro
            return await asyncio.wait_for(coro, timeout=timeout)

    return _UoW()
```

---

## Composition Root (testing wiring)

```python
# src/<pkg>/composition/compose.py
import uuid
from ..accounts.domain.values import Money
from ..accounts.domain.entities import Account
from ..accounts.domain.events import DomainEvent
from ..accounts.adapters.memory.account_repository import make_memory_account_repo
from ..accounts.adapters.memory.outbox import make_memory_outbox
from ..accounts.adapters.memory.idempotency import make_memory_idempotency
from ..accounts.adapters.uow.memory_uow import make_memory_uow
from ..accounts.application.ports.clock import system_clock
from ..accounts.application.use_cases.transfer_funds import create_transfer_funds

def compose_testing():
    """Wire in-memory adapters for testing."""
    state = {
        "A": Account("A", Money(10_00, "USD")),
        "B": Account("B", Money(0, "USD")),
    }
    outbox_storage: list[DomainEvent] = []

    uow = make_memory_uow(deps_factory=lambda: {
        "account_repo": make_memory_account_repo(state),
        "outbox": make_memory_outbox(outbox_storage),
    })

    id_provider = lambda: uuid.uuid4().hex
    clock = system_clock()
    idempotency = make_memory_idempotency()

    return {
        "transfer_funds": create_transfer_funds(
            uow=uow, id_provider=id_provider, clock=clock, idempotency=idempotency
        ),
        "_state": state,
        "_outbox": outbox_storage,
    }
```

---

## Key Patterns Demonstrated

| Pattern                         | Where                                                                |
|---------------------------------|----------------------------------------------------------------------|
| **Immutable VOs**               | `Money(frozen=True, slots=True)` with invariant validation           |
| **Deterministic lock ordering** | `sorted((from_id, to_id))` in use case and repo                      |
| **Outbox**                      | Events persisted in same transaction via `outbox.add_all()`          |
| **Idempotency**                 | `run_once(key, fn)` wrapping entire UoW call                         |
| **Typed deps**                  | `TransferDeps(TypedDict)` ensures type-safe access in work function  |
| **UoW**                         | Transaction-bound typed deps injected into work function             |
| **Factory use cases**           | `create_transfer_funds()` returns typed callable with full signature |
| **TypedDict events**            | Extend `DomainEvent` base; versioned with `type` and `v` fields      |
| **Composition root**            | Single wiring point, testing vs production                           |
