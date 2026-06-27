---
name: coding-bash-clean-architecture
description: Use when structuring Bash 4.3+ scripts or multi-file projects with clean architecture, reviewing layer dependency violations in shell scripts, deciding where functions belong across domain, application, adapter, and composition layers, or setting up ports and dependency inversion in bash
---

# Clean Architecture for Bash

## Overview

Framework-agnostic, structured Bash architecture optimized for **change**, **testability**, and **clear boundaries**. Inner layers never call outer layer functions directly. Domain stays pure (no I/O, no external commands).

**Target:** Bash >=4.3 | `set -euo pipefail` | Pure domain | Tool-agnostic core | No global mutable state in domain

## When to Use

- Starting a new bash script/project that needs long-term maintainability
- Reviewing existing shell scripts for architecture violations (I/O mixed with logic)
- Deciding where a new function belongs (domain vs application vs adapter)
- Structuring data flow between CLI input, business logic, and system output
- Setting up testing strategy with proper isolation
- Refactoring monolithic "god scripts" into clean architecture

**When NOT to use:**
- One-liner scripts or trivial wrappers (<30 lines)
- Scripts that are purely I/O orchestration with no business logic (simple `rsync` wrappers, etc.)
- Use SCRIPT mode for single-file scripts (see `script-mode.md`)

## Layers & Dependency Rule

**Inner layers never call outer layer functions directly.** Dependencies point inward only.

| Layer                | Contains                                                            | Rules                                                                  |
|----------------------|---------------------------------------------------------------------|------------------------------------------------------------------------|
| **Domain**           | Pure functions: validation, computation, transformation             | No I/O, no external commands, no `echo` to terminal, no env mutation   |
| **Application**      | Use case functions, port contracts (documented function signatures) | Orchestrates domain + ports; receives port function names as arguments |
| **Adapters**         | I/O functions: file, network, system, CLI parsing                   | Implements port contracts; maps external data to/from domain format    |
| **Composition Root** | `main()` wiring                                                     | Binds adapters to ports; entry point                                   |

## SOLID Adapted to Bash

| Principle | Rule                                                                                                            |
|-----------|-----------------------------------------------------------------------------------------------------------------|
| **SRP**   | One responsibility per function; split by use case, never `utils.sh` grab-bags                                  |
| **OCP**   | Extend by adding new adapter functions, not editing core logic                                                  |
| **LSP**   | All adapters implementing a port contract must accept the same args and return the same format                  |
| **ISP**   | Port contracts are narrow: one function per I/O concern                                                         |
| **DIP**   | Core functions receive I/O function names as parameters; never hardcode external commands in domain/application |

## Data Flow

```
CLI args -> validate (adapter boundary) -> domain functions (pure) -> format output (adapter) -> stdout/file
  (raw)     (composition/adapter)           (no I/O, no side effects)   (adapter boundary)       (external)
```

| Use Case               | Mechanism                                    | Notes                              |
|------------------------|----------------------------------------------|------------------------------------|
| Function return values | stdout capture: `result=$(fn args)`          | Primary data passing mechanism     |
| Structured data        | Associative arrays (`declare -A`)            | Bash 4.0+; pass by nameref         |
| Complex returns        | Multiple lines on stdout, one field per line | Parse with `read` or `mapfile`     |
| Error signaling        | Return code + stderr                         | `return 1` with `echo "error" >&2` |
| Cross-function data    | Nameref: `declare -n ref="$1"`               | Bash 4.3+; avoids globals          |

**Never:** Use global variables for data flow between layers. Globals acceptable only for: constants (`readonly`), configuration set once in composition root, and `trap` cleanup state.

## Core Patterns

### Ports (Function-Name Contracts)

Bash has no interfaces. Ports are **documented function signatures** that adapters must implement. Pass the function name to use cases.

```bash
# --- PORT CONTRACT ---
# port: read_config
# args: $1 = config file path
# stdout: key=value lines (one per line)
# return: 0 on success, 1 on not found, 2 on parse error

# --- ADAPTER (implements port) ---
adapter__read_config_file() {
    local file="$1"
    [[ -f "$file" ]] || return 1
    grep -v '^#' "$file" | grep -v '^$'
}

# --- USE CASE (receives port function name) ---
uc__load_settings() {
    local read_config_fn="$1"
    local config_path="$2"

    local raw
    raw=$("$read_config_fn" "$config_path") || return 1

    # Call domain function (pure)
    domain__parse_settings "$raw"
}

# --- COMPOSITION ---
main() {
    uc__load_settings adapter__read_config_file "/etc/myapp.conf"
}
```

### Dependency Inversion via Function References

```bash
# Use case depends on abstraction (function name parameter), not concretion
uc__process_data() {
    local fetch_fn="$1"      # port: fetch data
    local store_fn="$2"      # port: store result
    local input="$3"

    local raw_data
    raw_data=$("$fetch_fn" "$input") || return 1

    local result
    result=$(domain__transform "$raw_data")

    "$store_fn" "$result"
}

# Composition wires concrete adapters
main() {
    uc__process_data \
        adapter__fetch_from_api \
        adapter__store_to_file \
        "$1"
}
```

### Nameref for Structured Data (Bash 4.3+)

```bash
# Domain function populates associative array via nameref
domain__parse_record() {
    local input="$1"
    declare -n _out="$2"  # nameref to caller's associative array

    local key="${input%%:*}"
    local val="${input#*:}"
    _out[name]="$key"
    _out[value]="$val"
    # No I/O, no external commands — pure parameter expansion
}

# Caller
declare -A record
domain__parse_record "host:example.com" record
echo "${record[name]}"  # "host" -- I/O happens in adapter/composition
```

## Error Handling

| Layer       | Style                                                               |
|-------------|---------------------------------------------------------------------|
| Domain      | `return 1` + descriptive stderr: `echo "error: invalid format" >&2` |
| Application | Propagate domain return codes; add context                          |
| Adapters    | Catch external failures, map to domain error codes                  |
| Composition | Map to exit codes; final stderr formatting                          |

```bash
# Domain (pure validation)
domain__validate_port() {
    local port="$1"
    [[ "$port" =~ ^[0-9]+$ ]] || { echo "error: port must be numeric" >&2; return 1; }
    (( port >= 1 && port <= 65535 )) || { echo "error: port out of range" >&2; return 1; }
    echo "$port"  # return validated value
}

# Adapter (catches external failure)
adapter__check_port_open() {
    local host="$1" port="$2"
    timeout 5 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null || return 1
}
```

## Exit Codes

| Code | Meaning                                |
|-----:|----------------------------------------|
| 0    | Success                                |
| 1    | General error                          |
| 2    | Invalid input / usage error            |
| 3    | Not found                              |
| 4    | Conflict / precondition fail           |
| 70   | Unexpected internal error              |
| 124  | Timeout                                |
| 126  | Permission denied                      |
| 127  | Command not found (dependency missing) |

## Naming Conventions

| Layer                   | Prefix              | Example                                              |
|-------------------------|---------------------|------------------------------------------------------|
| Domain                  | `domain__`          | `domain__validate_email`, `domain__compute_checksum` |
| Application (use cases) | `uc__`              | `uc__deploy_service`, `uc__backup_database`          |
| Adapters                | `adapter__`         | `adapter__read_file`, `adapter__call_api`            |
| Composition/main        | `main`, `compose__` | `main`, `compose__wire_production`                   |
| Constants               | `UPPER_SNAKE`       | `readonly MAX_RETRIES=3`                             |

Double underscore separates namespace from function name. Prevents collision with system commands.

## Folder Layout (Multi-File)

```
project/
  bin/
    my-tool             # Entry point (sources lib, calls main)
  lib/
    domain.sh           # Pure functions: validation, transformation, computation
    application.sh      # Use cases: orchestration via port function references
    ports.sh            # Port contract documentation (comments only)
    adapters/
      file.sh           # File I/O adapter functions
      api.sh            # HTTP/API adapter functions
      system.sh         # System command adapter functions
    compose.sh          # Wiring: bind adapters to ports, call use cases
  tests/
    test_domain.sh      # Unit tests for domain (no mocking needed)
    test_application.sh # Use case tests with stub adapters
    test_integration.sh # Real adapters, real I/O
```

For single-file scripts, use comment-based section markers. See `script-mode.md`.

**Guardrails:** `domain.sh` sources nothing and calls no external commands. `application.sh` sources `domain.sh` only. `adapters/*.sh` implement port contracts. `compose.sh` sources everything and wires.

**Source guards** (prevent double-sourcing in multi-file projects):

```bash
# At the top of each library file (e.g., domain.sh)
[[ -n "${_DOMAIN_SH_LOADED:-}" ]] && return 0
readonly _DOMAIN_SH_LOADED=1
```

## Testing Strategy

| Type            | Purpose                                                                      |
|-----------------|------------------------------------------------------------------------------|
| **Unit**        | Domain functions with direct calls (no mocking needed — they're pure)        |
| **Stub**        | Use cases with stub adapter functions (bash functions that return test data) |
| **Integration** | Real adapters against real files/services                                    |
| **E2E**         | Full script execution with known inputs/outputs                              |

### Stub Adapters for Testing

```bash
# Stub adapter (replaces real I/O for testing)
stub__read_config() {
    echo "host=localhost"
    echo "port=8080"
}

# Test use case with stub
test_load_settings() {
    local result
    result=$(uc__load_settings stub__read_config "/fake/path")
    [[ "$result" == *"localhost"* ]] || { echo "FAIL: expected localhost"; return 1; }
    echo "PASS: test_load_settings"
}
```

## Observability

- **Structured logging** to stderr: `log_info "msg" >&2` (never to stdout — that's for data)
- Thread `TRACE_ID` via environment variable or global (set once in composition root)
- Log at adapter boundaries only; domain stays silent
- Use `PS4='+ ${BASH_SOURCE}:${LINENO}: '` with `set -x` for debug tracing

## Non-Negotiables Checklist

- [ ] Dependencies point inward only (domain calls nothing external)
- [ ] Domain pure: no I/O, no external commands, no `echo` to terminal (only stdout for return values)
- [ ] Use cases receive port function names as parameters (DIP)
- [ ] `set -euo pipefail` at script top
- [ ] Structured exit codes (not random numbers)
- [ ] Boundary validation (arguments checked at adapter/composition boundary)
- [ ] No global mutable state in domain/application (use namerefs or stdout)
- [ ] Logging to stderr only; stdout reserved for data
- [ ] Cleanup via `trap` in composition root (not scattered)
- [ ] Functions prefixed by layer (`domain__`, `uc__`, `adapter__`)
- [ ] `shellcheck` passes with no warnings (run: `shellcheck -x script.sh`)

## Operating Modes

| Mode         | Output                                               | Reference                  |
|--------------|------------------------------------------------------|----------------------------|
| **GENERATE** | Full project with domain/app/adapter/compose + tests | See `canonical-example.md` |
| **REVIEW**   | Violations + fix checklist                           | See `review-checklists.md` |
| **SCRIPT**   | Single file with logical layer sections              | See `script-mode.md`       |

## Refactoring Path (monolithic script -> clean arch)

1. Identify pure logic (validation, computation, string processing) -> move to `domain__` functions
2. Identify I/O operations (file reads, API calls, system commands) -> wrap in `adapter__` functions
3. Identify orchestration sequences -> extract to `uc__` use case functions
4. Document port contracts for each adapter function signature
5. Make use cases receive adapter function names as parameters
6. Create `main()` as composition root: parse args, wire adapters, call use cases
7. Add `set -euo pipefail` and structured exit codes
8. Write domain unit tests (pure function tests, no mocking)
9. Write stub adapter tests for use cases

## Common Mistakes

| Mistake                                          | Fix                                                                       |
|--------------------------------------------------|---------------------------------------------------------------------------|
| Calling `curl`/`grep`/`find` in domain functions | Domain is pure; wrap I/O commands in adapter functions                    |
| Using global variables for data flow             | Use stdout + capture, or namerefs (`declare -n`)                          |
| Logging to stdout                                | Stdout is for data; log to stderr (`>&2`)                                 |
| Hardcoding file paths in use cases               | Pass paths as parameters; set defaults in composition root                |
| Mixing argument parsing with business logic      | Parse in adapter/composition; pass validated values to use cases          |
| No `set -euo pipefail`                           | Always set at script top; handle expected failures with `\| true` or `if` |
| Random exit codes                                | Use structured exit code table; map in composition root                   |
| `trap` cleanup in random functions               | Single `trap` in composition root; adapters provide cleanup functions     |
| Sourcing everything at top level                 | Source only what each layer needs; domain sources nothing                 |
| `eval` for dynamic dispatch                      | Use `"$fn_name" args` (indirect call) — safe, no eval needed              |

## Reference Files

| File                   | Content                                                                  |
|------------------------|--------------------------------------------------------------------------|
| `script-mode.md`       | Single-file scripts: logical layer sections, exit codes, one-file layout |
| `canonical-example.md` | Complete Service Health Check example (domain through composition)       |
| `review-checklists.md` | All review checklists for REVIEW mode output                             |

## Glossary

| Term                   | Definition                                                                                  |
|------------------------|---------------------------------------------------------------------------------------------|
| **Adapter**            | Bash function performing I/O (file, network, system commands), implementing a port contract |
| **Application Layer**  | Use case functions orchestrating domain + port calls (no direct I/O)                        |
| **Composition Root**   | `main()` function: parses args, wires adapters to use cases, sets traps                     |
| **Domain**             | Pure bash functions: validation, computation, transformation (no I/O, no external commands) |
| **Nameref**            | `declare -n ref="$1"` — Bash 4.3+ mechanism for passing structured data without globals     |
| **Port**               | Documented function signature contract that adapters must implement                         |
| **Function Reference** | Passing a function name as a string argument for indirect call: `"$fn_name" args`           |
