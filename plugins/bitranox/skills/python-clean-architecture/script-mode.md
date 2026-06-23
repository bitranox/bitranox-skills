# Script Mode — One-File Layered Architecture (CLI-first)

Use when delivering a **single Python file** (no package install required).
Respects Domain/Application/Adapters boundaries logically inside one file.
Inherits all Non-Negotiables from `SKILL.md`; adapt Outbox/Idempotency pragmatically. Review with `review-checklists.md`.

---

## Rules

- Keep **all code in one file**, separated by logical layer markers
- **Domain stays pure** (no I/O); Application orchestrates via ports; Adapters do I/O
- Typed CLI (`argparse`), input validation at boundary, result -> exit code mapping
- `asyncio.wait_for(coro, timeout=)` for deadlines; propagate `CancelledError` -> exit code 124
- Structured logging to stderr (key=value); `trace_id` via `contextvars`
- No top-level side effects; entry via `if __name__ == "__main__": raise SystemExit(main())` (sync) or `raise SystemExit(asyncio.run(main()))` (async)
- **Stdlib-only by default**; use PEP 723 for deps (confined to adapters)

---

## PEP 723 — Inline Script Metadata

Use when a one-file script needs dependencies. Keep core boundaries: only adapters import 3rd-party.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests", "rich>=13"]
# ///

# === Domain (no I/O, no rich) ===
# ...

# === Adapters (I/O; rich allowed here) ===
from rich.console import Console
console = Console()
```

Run with: `uv run --script your_script.py`

If you don't need deps, **omit** the PEP 723 block and stay stdlib-only.

---

## Exit Codes

| Code | Meaning                      |
|-----:|------------------------------|
| 0    | Success                      |
| 2    | Invalid input / usage error  |
| 3    | Not found                    |
| 4    | Conflict / precondition fail |
| 70   | Unexpected internal error    |
| 124  | Timeout / cancelled          |

---

## One-File Logical Layout

```python
#!/usr/bin/env python3
"""<Summary> — minimal, typed, dependency-free CLI with layered ports-and-adapters design."""

# === Imports (stdlib only; or adapter-only 3p if PEP 723 used) ===
# === Observability/Context (trace_id) ===
# === Domain (no I/O) ===
# === Application Ports (Protocols) ===
# === Application Use Cases (orchestration only) ===
# === Adapters (CLI/file/stdio; 3p deps live here) ===
# === Composition (wire ports) ===
# === CLI (argparse) + main() + exit mapping ===
```

---

## Result/Errors

- Return typed result from use case; map to human/JSON in adapter
- Map domain/application errors to exit codes only in CLI adapter
- **Read-only scripts:** Outbox/Idempotency are N/A
- **Mutating scripts:** Simple idempotency guard (file-based or hash set)

---

## Complete Example — URL Health Checker

```python
#!/usr/bin/env python3
"""url-health — Check HTTP endpoint health. Stdlib-only, typed, layered."""

import argparse
import sys
from dataclasses import dataclass
from typing import Protocol, TypedDict
from urllib.error import URLError
from urllib.request import urlopen

# === Domain (no I/O) ===

@dataclass(frozen=True, slots=True)
class HealthResult:
    url: str
    ok: bool
    status: int | None
    error: str | None = None

# === Application Ports ===

class HttpProbe(Protocol):
    def check(self, url: str, *, timeout: float) -> HealthResult: ...

# === Application Use Case ===

def check_health(probe: HttpProbe, url: str, *, timeout: float = 5.0) -> HealthResult:
    return probe.check(url, timeout=timeout)

# === Adapters ===

class UrllibProbe:
    def check(self, url: str, *, timeout: float) -> HealthResult:
        try:
            with urlopen(url, timeout=timeout) as r:
                return HealthResult(url=url, ok=r.status < 400, status=r.status)
        except URLError as e:
            return HealthResult(url=url, ok=False, status=None, error=str(e.reason))
        except TimeoutError:
            return HealthResult(url=url, ok=False, status=None, error="timeout")

# === Composition ===

class Deps(TypedDict):
    probe: HttpProbe

def compose() -> Deps:
    return {"probe": UrllibProbe()}

# === CLI + main ===

def main() -> int:
    ap = argparse.ArgumentParser(description="Check URL health")
    ap.add_argument("url")
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()

    if not args.url.startswith(("http://", "https://")):
        print("error: URL must start with http:// or https://", file=sys.stderr)
        return 2

    result = check_health(compose()["probe"], args.url, timeout=args.timeout)
    if result.ok:
        print(f"OK {result.url} status={result.status}")
        return 0
    print(f"FAIL {result.url} error={result.error or result.status}")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Script Self-Check

- [ ] File has logical boundaries (Domain/Application/Adapters/Composition/CLI)
- [ ] Domain contains no I/O/logging; use case returns typed data
- [ ] Ports are narrow; adapters implement only those ports
- [ ] Input validated at edge; errors mapped to exit codes
- [ ] Timeout/cancellation handled; `trace_id` threaded
- [ ] No heavy work at import; all side effects in `main`
- [ ] Stdlib-only by default; if deps used, PEP 723 block present and deps confined to adapters
- [ ] Python >=3.10 compatible
