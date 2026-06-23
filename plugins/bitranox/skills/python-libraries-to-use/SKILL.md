---
name: python-libraries-to-use
description: Use when choosing Python libraries for a task, when writing new Python code that needs dependencies, when reviewing Python imports for non-preferred libraries, or when unsure which library to use for JSON, HTTP, logging, TOML, YAML, compression, database access, testing, or CLI tools
---

# Python Library Usage Guidelines

## Overview

Standardized library choices for all Python projects. Ensures consistency, avoids reinventing the wheel, and enforces preferred tools over alternatives.

**General Rule:** Always prefer existing library functions over custom implementations.

**Library Selection Policy:**
* The **first entry** in each list is the *preferred* option.
* Alternatives may be used only if they offer specific advantages or required functionality.
* Propose new functions to our internal libraries (`lib_*`) if needed — we can change them.

## Quick Reference Table

| Category             | Preferred Library                       | Do NOT Use                           |
|----------------------|-----------------------------------------|--------------------------------------|
| CLI exit/traceback   | `lib_cli_exit_tools`                    | manual `sys.exit`                    |
| Logging (apps)       | `lib_log_rich`                          | `print()`, bare `logging`            |
| Logging (libs)       | `logging` stdlib                        | `lib_log_rich`                       |
| Terminal output      | `rich`                                  | `colorama` (fallback only)           |
| TUI                  | `textual`                               | `curses`                             |
| Domain models        | `dataclasses`                           | `dict`, `Pydantic`                   |
| Boundary validation  | `pydantic`                              | manual parsing                       |
| Enums                | `IntEnum` / `StrEnum`                   | plain `Enum`, magic strings          |
| TOML                 | `rtoml`                                 | `tomllib`, `tomli`                   |
| JSON                 | `orjson`                                | `json` stdlib                        |
| YAML                 | `ruamel.yaml`                           | `PyYAML`                             |
| HTTP                 | `httpx2`                                | `requests, httpx`                    |
| Compression (stream) | `isal`                                  | `gzip` stdlib                        |
| Compression (store)  | `libdeflate`                            | `gzip` stdlib                        |
| Paths                | `pathlib.Path`                          | `os.path`                            |
| .env files           | `python-dotenv`                         | manual parsing                       |
| Config management    | `lib_layered_config`                    | manual argparse + env                |
| Database (ODBC)      | `pyodbc`                                | raw ODBC bindings                    |
| Database (MySQL)     | `mysql-connector-python` / `SQLAlchemy` | `PyMySQL`, `mysqlclient`             |
| ORM / query builder  | `SQLAlchemy`                            | custom ORM, raw SQL for complex apps |
| Testing              | `pytest`                                | `unittest`                           |
| Date/time            | `datetime` + `zoneinfo`                 | `pytz`                               |
| Subprocess           | `subprocess.run`                        | `os.system`                          |
| Type checking        | `mypy`                                  | no type checking                     |

---

## CLI Tools

1. `lib_cli_exit_tools` — for handling CLI exit codes, tracebacks, and related utilities. Propose new functions if needed.

---

## Logging

| Context                | Library            | Configuration                                   |
|------------------------|--------------------|-------------------------------------------------|
| **Applications**       | `lib_log_rich`     | Full structured logging with rich output        |
| **Libraries/Packages** | `logging` (stdlib) | `logging.getLogger(__name__)` + `NullHandler()` |

**Why the distinction:**
- Libraries must not configure logging (leave that to the consuming application)
- Libraries install `NullHandler` to prevent "no handler found" warnings
- Applications control output format, level, and destination via `lib_log_rich`

**Library pattern:**
```python
# src/<pkg>/__init__.py
import logging
logging.getLogger(__name__).addHandler(logging.NullHandler())
```

**Application pattern (basic):**
```python
import lib_log_rich
from lib_log_rich.runtime import attach_std_logging

# Initialize with RuntimeConfig
lib_log_rich.init(lib_log_rich.RuntimeConfig(
    service="my-app",
    environment="dev",
    console_level="INFO",      # INFO and above to console
    backend_level="WARNING",   # WARNING and above to journald/EventLog
))

# Bridge stdlib logging so existing logging.* calls work
attach_std_logging()

# Use lib_log_rich's LoggerProxy for new code
logger = lib_log_rich.getLogger(__name__)
logger.info("Application started", extra={"port": 8080})

# Or use stdlib logging (bridged automatically)
import logging
logging.info("This also works!")

# Clean shutdown (flushes queues, closes adapters)
lib_log_rich.shutdown()
```

**Application pattern (with lib_layered_config):**
```python
# logging_setup.py - centralized logging initialization
from lib_layered_config import Config
import lib_log_rich.config
import lib_log_rich.runtime

def init_logging(config: Config) -> None:
    """Initialize logging from layered config [lib_log_rich] section."""
    if not lib_log_rich.runtime.is_initialised():
        lib_log_rich.config.enable_dotenv()  # optional: load LOG_* from .env
        log_config = dict(config.get("lib_log_rich", default={}))
        log_config.setdefault("service", "my-app")
        log_config.setdefault("environment", "prod")
        runtime_config = lib_log_rich.runtime.RuntimeConfig(**log_config)
        lib_log_rich.runtime.init(runtime_config)
        lib_log_rich.runtime.attach_std_logging()
```

**Key RuntimeConfig options:**
- `service` (required): Logical service name
- `environment` (required): Deployment label (dev/stage/prod)
- `console_level`: Threshold for Rich console (default: INFO)
- `backend_level`: Threshold for journald/EventLog (default: WARNING)
- `queue_enabled`: Background queue for async delivery (default: True)
- `enable_journald`/`enable_eventlog`/`enable_graylog`: Backend adapters

**Shutdown (required for clean exit):**
```python
# Synchronous shutdown - flushes queues, drains adapters, clears state
lib_log_rich.shutdown()

# Async shutdown - for asyncio applications
await lib_log_rich.shutdown_async()
```

**Important:** Always call `shutdown()` before process exit to ensure:
- Background queue is drained (pending log events are delivered)
- Graylog/journald/EventLog adapters flush their buffers
- Global runtime state is cleared

Safe to call multiple times after initialization.

*Propose new functions to `lib_log_rich` if needed — we can change that library.*

---

## Colored Terminal Output

1. `rich` — preferred for beautiful, formatted console output.
2. `colorama` — may be used if `rich` is unavailable or not suitable.

---

## Text-based User Interfaces (TUI)

1. `textual` — for building rich, interactive TUIs in the terminal.

---

## Data Models: Dataclasses vs Pydantic

**Rule:** Prefer structured types (dataclasses or Pydantic) over dicts. Data flowing between modules **must** use typed models, not raw dicts.

### Decision Matrix

| Use Case                        | Recommended             | Why                            |
|---------------------------------|-------------------------|--------------------------------|
| Domain entities & value objects | `dataclasses`           | Keep domain dependency-free    |
| Internal DTOs (trusted data)    | `dataclasses`           | Lightweight, no parsing needed |
| External input validation       | `pydantic.BaseModel`    | Type coercion, sanitization    |
| JSON/dict serialization         | `pydantic.BaseModel`    | Built-in `.model_dump()`       |
| Configuration from env/files    | `pydantic.BaseSettings` | Validation + env parsing       |
| Performance-critical paths      | `dataclasses`           | Lower overhead                 |

### Preference Order

1. **`dataclasses` (stdlib)** — default for domain/application layer.
   * Always use `@dataclass(frozen=True, slots=True)` for immutability and efficiency.
   * Use for internal data that doesn't need validation or format conversion.

2. **`pydantic.BaseModel`** — use at boundaries where data enters/exits the system.
   * Parsing untrusted input (HTTP requests, CLI args, config files).
   * Type coercion needed (string -> int, string -> datetime).
   * Serialization to JSON, dict, or other formats required.
   * Use `model_config = ConfigDict(frozen=True)` for immutability.

3. **`pydantic.dataclasses`** — when you want dataclass syntax with Pydantic validation.
   * Useful for gradual migration from stdlib dataclasses.

### Dict Usage Policy

**Default**: Use typed structures (`dataclass`, `Pydantic`) for all data.

**Dicts are acceptable only when ALL of these apply:**
- Truly dynamic/schema-less data (e.g., arbitrary JSON passthrough with no business logic)
- Fewer than 3 keys
- No cross-module flow (contained within a single function/helper)
- No business logic operates on the dict

**Never acceptable:**
- Passing `dict[str, Any]` between modules or layers
- Using dict keys in conditionals or business logic
- Dict as function return type for structured data

**When in doubt**: Convert to a typed structure at the boundary.

### Anti-patterns
- Passing `dict[str, Any]` between modules
- Using Pydantic in the domain layer
- Using dataclasses for untrusted external input
- Mixing dict-based and model-based data in the same flow

### Data Flow Pattern

```
External Input -> Pydantic (validate) -> Dataclass (domain logic) -> Pydantic (serialize) -> External Output
```

---

## Enums: Prefer IntEnum

**Rule:** Replace string literals representing categories, statuses, modes, event types, or command names with `Enum` classes. **Prefer `IntEnum` over `Enum`** where possible.

### Why IntEnum?

| Feature                | `Enum`                          | `IntEnum`                          |
|------------------------|---------------------------------|------------------------------------|
| JSON serialization     | Requires custom encoder         | Works natively (serializes as int) |
| Database storage       | Needs explicit conversion       | Stores as integer directly         |
| Comparison with int    | `Status.ACTIVE == 1` -> `False` | `Status.ACTIVE == 1` -> `True`     |
| Arithmetic operations  | Not supported                   | Supported (inherits from `int`)    |
| Pydantic compatibility | Works                           | Works + auto-coerces from int      |

### When to use each

| Use Case                                        | Recommended         |
|-------------------------------------------------|---------------------|
| Status codes, error codes, log levels           | `IntEnum`           |
| Database-backed enumerations                    | `IntEnum`           |
| API response codes                              | `IntEnum`           |
| Purely semantic categories (no numeric meaning) | `Enum` or `StrEnum` |
| String-based identifiers (e.g., HTTP methods)   | `StrEnum`           |

### Example

```python
from enum import IntEnum, StrEnum, auto

# Preferred for numeric categories
class TaskStatus(IntEnum):
    PENDING = 0
    RUNNING = 1
    COMPLETED = 2
    FAILED = 3

# Works seamlessly with JSON, databases, comparisons
assert TaskStatus.RUNNING == 1  # True
assert TaskStatus.RUNNING > TaskStatus.PENDING  # True

# Use StrEnum for string-based identifiers
class HttpMethod(StrEnum):
    GET = auto()
    POST = auto()
    PUT = auto()
    DELETE = auto()
```

### Anti-patterns
- Using plain `Enum` when values need JSON serialization
- Magic strings: `if status == "pending"` instead of `if status == Status.PENDING`
- Magic numbers: `if code == 1` instead of `if code == ErrorCode.INVALID_INPUT`

---

## Serialization Formats

### TOML

**Use `rtoml`** for all TOML parsing operations.

- Preferred over stdlib `tomllib` for consistency across Python versions
- Preferred over `tomli` (third-party read-only)
- Provides both read and write capabilities

```python
import rtoml

# Reading from file
config = rtoml.load(path)          # path as str or Path

# Writing to file
rtoml.dump(data, path)

# Reading from string
config = rtoml.loads(toml_string)

# Writing to string
toml_string = rtoml.dumps(data)
```

### JSON

**Use `orjson`** for all JSON serialization/deserialization.

- Significantly faster than stdlib `json` (10-50x for large payloads)
- Native support for `dataclasses`, `datetime`, `UUID`, `numpy` arrays
- Returns `bytes` (not `str`) — more efficient for I/O
- Strict by default (no NaN/Infinity, sorted keys optional)

```python
import orjson

# Reading
data = orjson.loads(json_bytes)  # accepts bytes or str

# Writing
json_bytes = orjson.dumps(data)

# With options (pretty print, sorted keys, datetime as ISO)
json_bytes = orjson.dumps(
    data,
    option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS
)

# Dataclass serialization (native support)
from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass
class User:
    name: str
    created: datetime

orjson.dumps(User("Alice", datetime.now(timezone.utc)))  # works directly
```

### YAML

**Use `ruamel.yaml`** for all YAML operations.

- Preserves comments and formatting on round-trip (read -> modify -> write)
- Full YAML 1.2 support (unlike `PyYAML` which only supports YAML 1.1)
- Preferred over `PyYAML`

```python
from ruamel.yaml import YAML

yaml = YAML()
yaml.preserve_quotes = True

# Reading
with open("config.yaml") as f:
    data = yaml.load(f)

# Writing (preserves comments and formatting)
with open("config.yaml", "w") as f:
    yaml.dump(data, f)
```

---

## HTTP/REST Calls

**Use `httpx`** for all HTTP requests. Do not use `requests`.

- Modern async-first design with sync support
- HTTP/1.1 and HTTP/2 support
- Connection pooling and keep-alive by default
- Type-annotated API
- Timeout configuration required (no silent hangs)

```python
import httpx

# Synchronous usage
response = httpx.get("https://api.example.com/data", timeout=10.0)
data = response.json()

# With client (recommended for multiple requests)
with httpx.Client(timeout=30.0) as client:
    response = client.post(
        "https://api.example.com/submit",
        json={"key": "value"},
    )

# Async usage
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get("https://api.example.com/data")
```

**Required patterns:**
- Always specify `timeout` (never rely on defaults)
- Use `Client`/`AsyncClient` context managers for connection reuse
- Prefer async in async codebases

---

## Database Access

### Decision Matrix

| Use Case                      | Library                  | Notes                                                 |
|-------------------------------|--------------------------|-------------------------------------------------------|
| **ODBC connections (any DB)** | `pyodbc`                 | Most widely used, stable, works with any ODBC driver  |
| **MySQL (simple tasks)**      | `mysql-connector-python` | Official Oracle driver, pure Python, no external libs |
| **MySQL (ORM / complex)**     | `SQLAlchemy`             | Use `mysql-connector-python` as MySQL backend         |
| **Async database access**     | `SQLAlchemy` (async)     | With `asyncio` extension + async driver               |

### Usage Patterns

```python
# Direct ODBC connection (any database with ODBC driver)
import pyodbc

conn = pyodbc.connect(connection_string)
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
rows = cursor.fetchall()
conn.close()

# Direct MySQL connection (simple tasks)
import mysql.connector

conn = mysql.connector.connect(
    host="localhost", database="mydb", user="user", password="pass"
)
cursor = conn.cursor()
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
rows = cursor.fetchall()
conn.close()

# SQLAlchemy with mysql-connector-python backend (ORM / complex queries)
from sqlalchemy import create_engine

engine = create_engine(
    "mysql+mysqlconnector://user:pass@host/db",
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### Rules
- Use `pyodbc` for ad-hoc or cross-database ODBC access
- Use `mysql-connector-python` directly for simple MySQL tasks
- Use `SQLAlchemy` (with `mysql-connector-python` as backend) for ORM, migrations, or complex queries
- Always use parameterized queries — **never** string-format SQL
- Always configure connection pooling for long-running applications

---

## Testing

| Component            | Library           | Notes                                     |
|----------------------|-------------------|-------------------------------------------|
| **Test framework**   | `pytest`          | Preferred over `unittest`                 |
| **Coverage**         | `pytest-cov`      | Coverage reporting integrated with pytest |
| **Mocking**          | `unittest.mock`   | stdlib — no extra dependency needed       |
| **Async tests**      | `pytest-asyncio`  | For testing async code                    |
| **Parameterization** | `pytest` built-in | `@pytest.mark.parametrize`                |
| **Fixtures**         | `pytest` built-in | Prefer fixtures over setUp/tearDown       |

**Rules:**
- Use `pytest` style (functions + fixtures), not `unittest` style (classes + setUp/tearDown)
- Use `pytest.raises` for exception testing, not try/except
- Name test files `test_*.py`, test functions `test_*`
- Use `conftest.py` for shared fixtures

---

## Compression (gzip alternatives)

**Use high-performance compression libraries instead of stdlib `gzip`.**

| Use Case          | Library                | Why                                                      |
|-------------------|------------------------|----------------------------------------------------------|
| **Web transport** | `isal` (ISA-L / igzip) | Intel-optimized, 2-4x faster compression/decompression   |
| **Storage**       | `libdeflate`           | Higher compression ratios, optimized for single-shot ops |

```python
# Web transport: ISA-L (igzip) — streaming, fast
import isal.igzip as igzip

# Compress for HTTP response
compressed = igzip.compress(data, compresslevel=1)  # level 0-3

# Decompress incoming
decompressed = igzip.decompress(compressed)

# Streaming with file-like objects
with igzip.open("file.gz", "wb") as f:
    f.write(data)
```

```python
# Storage: libdeflate — single-shot, high ratio
import libdeflate

# Compress for archival (levels 1-12, default 6)
compressor = libdeflate.Compressor(compression_level=9)
compressed = compressor.compress(data)

# Decompress
decompressor = libdeflate.Decompressor()
decompressed = decompressor.decompress(compressed, len(original_data))
```

**Selection guide:**
- **Streaming / chunked data** -> `isal.igzip`
- **HTTP compression** -> `isal.igzip` (compatible with standard gzip)
- **Archive / backup** -> `libdeflate` (better ratios)
- **Unknown decompressed size** -> `isal.igzip` (handles streaming)

---

## Date & Time

**Use `datetime` (stdlib)** with timezone awareness enforced. **Use `zoneinfo` (stdlib)** for named timezones.

- Always use timezone-aware datetimes — never naive datetimes
- Use `zoneinfo` (Python 3.9+) for named timezones — **do not use `pytz`**
- Store/transmit as UTC; convert to local only for display

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Always timezone-aware
now_utc = datetime.now(timezone.utc)
now_berlin = datetime.now(ZoneInfo("Europe/Berlin"))

# Convert between timezones
local_time = now_utc.astimezone(ZoneInfo("Europe/Berlin"))

# Parse ISO format
parsed = datetime.fromisoformat("2025-01-15T10:30:00+01:00")

# Format for storage/transmission (ISO 8601 UTC)
timestamp_str = now_utc.isoformat()
```

### Anti-patterns
- `datetime.now()` without timezone (creates naive datetime)
- Using `pytz` (replaced by `zoneinfo` in stdlib since Python 3.9)
- Storing naive datetimes in databases
- Comparing naive and aware datetimes (raises `TypeError`)

---

## Directory & Filepath Handling

**Always use `pathlib.Path`** and ensure cross-platform compatibility.

**Critical Rule:** Accept Linux-style paths (`//share/directory`, `/path/to/file`) even on Windows.

- UNC paths (`//server/share`) must work on all platforms
- Never use `os.path` for new code — prefer `pathlib`
- Use `Path.as_posix()` when storing/transmitting paths
- Use forward slashes (`/`) in configuration files and APIs

```python
from pathlib import Path
import sys

def normalize_path(path_str: str) -> Path:
    """Convert any path string to a native Path, preserving UNC paths.

    Args:
        path_str: Path string (Linux or Windows style).

    Returns:
        Native Path object.

    Examples:
        >>> normalize_path('//server/share/file.txt')  # UNC path
        >>> normalize_path('/home/user/file.txt')      # Linux path
    """
    # On Windows, convert forward-slash UNC paths to native backslash form
    if sys.platform == "win32" and path_str.startswith("//"):
        return Path(path_str.replace("/", "\\"))
    return Path(path_str)

# For storage/transmission, always use POSIX style
def path_to_string(path: Path) -> str:
    """Convert Path to portable string representation."""
    return path.as_posix()

# Accept both styles in function signatures
def process_file(file_path: str | Path) -> None:
    path = Path(file_path) if isinstance(file_path, str) else file_path
    # ... process
```

**Configuration & API Guidelines:**
- Store paths as POSIX strings (`/path/to/file`, `//server/share`)
- Parse with `Path()` or `normalize_path()` at runtime
- Never hardcode backslashes in source code or configs

---

## .env File Reading

**Use `python-dotenv`** for loading `.env` files.

- Use `find_dotenv()` to walk up parent directories automatically
- Do not commit `.env` files to version control

```python
from dotenv import load_dotenv, find_dotenv

# find_dotenv() walks up directories to find .env
load_dotenv(find_dotenv(usecwd=True))

# Or with explicit path
load_dotenv("/path/to/project/.env")

# Access loaded values
import os
db_host = os.getenv("DB_HOST", "localhost")
```

**Integration with Pydantic BaseSettings** (`pip install pydantic-settings`):
```python
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

class AppSettings(BaseSettings):
    db_host: str = "localhost"
    db_port: int = 5432
    debug: bool = False

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = AppSettings()  # auto-reads .env + environment variables
```

---

## Configuration Management

**Use `lib_layered_config`** for application configuration.

- Supports layered config: defaults -> config file -> environment variables -> CLI args
- Integrates with `lib_log_rich` for logging setup (see Logging section)

**For simpler cases or libraries**, use `pydantic.BaseSettings` (see .env section above).

---

## Subprocess / External Commands

**Use `subprocess.run`** (stdlib) for running external commands.

- Always use list form for arguments, not `shell=True`
- Set `check=True` to raise on non-zero exit codes
- Set `capture_output=True` when you need stdout/stderr
- Set `timeout` to prevent hanging

```python
import subprocess

result = subprocess.run(
    ["git", "status", "--porcelain"],
    capture_output=True,
    text=True,
    check=True,
    timeout=30,
)
print(result.stdout)
```

### Anti-patterns
- `shell=True` with unsanitized input (command injection risk)
- `os.system()` (no output capture, no error handling)
- Missing `timeout` on external calls

---

## Type Checking

**Use `mypy`** for static type checking.

- Run as part of CI/CD pipeline
- Use strict mode (`--strict`) for new projects
- Use `py.typed` marker file for typed libraries (PEP 561)

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
```
