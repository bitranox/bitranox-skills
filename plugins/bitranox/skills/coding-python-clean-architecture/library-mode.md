# Library Development — SDK / Package / Plugin (Pure Python)

Applies when the output is a **reusable library** (imported by other apps), not just an application.
Inherits all Non-Negotiables from `SKILL.md`. Ports follow `port-contracts.md`. Architecture review via `review-checklists.md`. Target Python >=3.10.

---

## Public API Policy

- **One canonical import path:** `import <pkg>` (and `<pkg>.<bounded_context>` if exposed)
- Everything not public lives in `<pkg>._internal` or stays unexported
- Use `__all__` to pin the surface; re-export stable types from a thin facade
- **Never** leak adapter/framework/driver types into the public surface
- Keep dataclass fields and function signatures stable once public; new params as keyword-only with defaults

```python
# src/<pkg>/__init__.py
from ._version import __version__
from .facade import run_use_case, RequestContext, Result, LibraryError

__all__ = ["__version__", "run_use_case", "RequestContext", "Result", "LibraryError"]

import logging as _logging
_logging.getLogger(__name__).addHandler(_logging.NullHandler())
```

---

## Versioning & Deprecation

**SemVer 2.0.0:**
- **PATCH:** Bug fixes, doc updates, internal improvements
- **MINOR:** Backward-compatible features; introduce deprecations here
- **MAJOR:** Breaking changes, remove previously deprecated APIs

**Deprecation window:** >=1 minor release. Emit `DeprecationWarning` with removal version.

```python
# src/<pkg>/_deprecations.py
from functools import wraps
import warnings

def deprecated(*, since: str, remove_in: str, alt: str | None = None):
    def deco(fn):
        msg = f"{fn.__name__} deprecated since {since}; removed in {remove_in}."
        if alt:
            msg += f" Use {alt} instead."
        @wraps(fn)
        def wrapper(*a, **kw):
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return fn(*a, **kw)
        return wrapper
    return deco
```

---

## Errors & Results

```python
# src/<pkg>/errors.py
class LibraryError(Exception): ...
class NotFound(LibraryError): ...
class InvalidInput(LibraryError): ...
class Conflict(LibraryError): ...
# Map domain/application errors -> these in adapters/facade
```

Result envelope (when used):

```python
# src/<pkg>/facade.py
from collections.abc import Mapping
from typing import Any, TypedDict

class Result(TypedDict, total=False):
    ok: bool
    error: dict[str, str]  # {"code": "...", "message": "..."}
    data: Mapping[str, Any]
```

**Rule:** Library surface returns typed results OR raises library exceptions; transport exceptions never leak.

---

## Logging, Metrics, Tracing

- **No prints.** Use `logging.getLogger(__name__)`; NullHandler by default
- Expose hooks, not opinions: accept optional `on_event` or `on_trace` callbacks at the facade
- Thread `trace_id` via `contextvars`

## Configuration

- Accept config via explicit objects/kwargs; **never** read `os.environ` inside public APIs
- Validate at the edge (facade) and freeze with `@dataclass(frozen=True, slots=True)`

## Thread-Safety & Resources

- Document whether the library is thread-safe; default: reentrant, no global mutable state
- Caches must be local to instances (or guarded) and optional
- Resources (files/sockets): expose context managers; no resources held at import time

---

## Packaging (PEP 621)

```toml
[build-system]
requires = ["hatchling>=1.21"]
build-backend = "hatchling.build"

[project]
name = "<pkg>"
dynamic = ["version"]
requires-python = ">=3.10"
description = "Layered, ports-and-adapters library for <domain>"
readme = "README.md"
license = { text = "MIT" }
dependencies = []  # core stays zero/low deps

[project.optional-dependencies]
adapters-sql = ["psycopg[binary]>=3.2"]
adapters-http = ["httpx>=0.27"]
dev = [
  "pytest>=8.2","pytest-asyncio>=0.24","ruff>=0.5","pyright>=1.1",
  "import-linter>=2.0","coverage[toml]>=7.6","mkdocs-material>=9.5",
  "mkdocstrings[python]>=0.24"
]

[tool.hatch.version]
path = "src/<pkg>/_version.py"

[tool.hatch.build.targets.wheel]
packages = ["src/<pkg>"]
include = ["src/<pkg>/py.typed"]
```

Ship `py.typed` (empty file, PEP 561) in the wheel. Keep runtime deps minimal; adapters via extras only.

---

## Plugins (entry points)

```python
# src/<pkg>/plugins.py
from importlib.metadata import entry_points
from typing import Protocol, runtime_checkable

API_VERSION = (1, 0)

@runtime_checkable
class Plugin(Protocol):
    api_version: tuple[int, int]
    name: str
    def register(self) -> None: ...

def discover(group: str = "<pkg>.plugins") -> list[Plugin]:
    eps = entry_points(group=group)
    out: list[Plugin] = []
    for ep in eps:
        plugin = ep.load()
        if not isinstance(plugin, Plugin):
            continue
        if plugin.api_version[0] != API_VERSION[0]:
            continue
        out.append(plugin)
    return out
```

Third-party plugin pyproject:
```toml
[project.entry-points."<pkg>.plugins"]
my_plugin = "vendor_pkg.plugin:PluginImpl"
```

---

## Canonical Library Layout

```
/pyproject.toml
/src
  /<pkg>/
    __init__.py
    _version.py
    py.typed
    facade.py
    errors.py
    _deprecations.py
    _internal/                # non-public helpers
    <bounded_context>/
      domain/
      application/
      adapters/
      platform/
    composition/
      compose.py
/docs
  index.md
/examples
/CHANGELOG.md
/CONTRIBUTING.md
/LICENSE
```

---

## Library Self-Check

- [ ] Public API is small, documented, and re-exported via `__all__`
- [ ] No heavy work at import; logging uses NullHandler only
- [ ] SemVer + deprecations documented; removals scheduled for next major
- [ ] Typed wheel shipped (`py.typed`); strict type-checking passes
- [ ] Adapters behind extras; no framework types in public API
- [ ] Plugin Protocols are narrow; discovery uses entry points; contract tests exist
- [ ] Concurrency/resource contracts documented; no global mutable state
- [ ] Inward-only dependency direction still enforced (no core imports from adapters)

## Library Review Checklist

- [ ] Public API separated from internals; `__all__` defined; import paths stable
- [ ] pyproject + `py.typed` present; wheel builds reproducibly
- [ ] Deprecation helper used; policy documented; CHANGELOG updated
- [ ] Exceptions stable; transport/framework types not exposed
- [ ] Plugins conform to `Protocol`; contract tests pass for each adapter
- [ ] Import-time is light; logging configured via NullHandler only
- [ ] Layered architecture rules intact (inward-only dependencies, ports/adapters)
