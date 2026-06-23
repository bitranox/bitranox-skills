# Review Checklists -- REVIEW Mode Output

Use these checklists when auditing bash scripts against clean architecture. Report violations and propose concrete refactors.

---

## Architecture

- [ ] Inward dependencies only; domain functions call no external commands
- [ ] Domain functions contain no I/O (`echo` only to stdout for return values, never terminal)
- [ ] Use cases receive I/O functions as parameters (DIP via function references)
- [ ] Port contracts documented (args, stdout, return codes)
- [ ] Functions prefixed by layer (`domain__`, `uc__`, `adapter__`)
- [ ] No business logic in adapters; adapters only do I/O and format conversion

## Shell Hygiene

- [ ] `set -euo pipefail` at script top
- [ ] All variables quoted (`"$var"` not `$var`)
- [ ] Local variables declared with `local` in every function
- [ ] No global mutable variables in domain/application (use `readonly` for constants)
- [ ] No `eval`; use `"$fn_name" args` for indirect function calls
- [ ] Subshells `$(...)` preferred over backticks
- [ ] `[[ ]]` preferred over `[ ]` for tests

## Data Flow

- [ ] Stdout reserved for data; logging to stderr only
- [ ] Structured data passed via stdout lines or nameref (not global variables)
- [ ] No `dict`-style hacks with `eval`; use associative arrays with namerefs
- [ ] Functions return data via stdout or nameref; error details via stderr

## Error Handling

- [ ] Domain/application return meaningful codes (0=ok, 1=error, etc.)
- [ ] Exit codes mapped to human meaning only in composition root
- [ ] Structured exit code table (0, 2, 3, 4, 70, 124, 126, 127)
- [ ] `trap` cleanup registered once in composition root
- [ ] Expected failures handled with `if` or `|| handler` (not relying on `set -e` alone)
- [ ] No `exit` calls inside domain/application functions (only `return`)

## Observability

- [ ] Logging functions write to stderr with severity prefix
- [ ] Trace ID set in composition root; threaded to log functions
- [ ] No `echo` debug statements left in domain/application
- [ ] `PS4` configured for debug mode (`set -x`)
- [ ] Sensitive data (passwords, tokens) never logged

## Testing

- [ ] Domain functions have direct unit tests (no mocking needed)
- [ ] Use case tests use stub adapter functions
- [ ] Stub adapters match port contract signatures
- [ ] Integration tests use real adapters with controlled inputs
- [ ] Test framework follows simple assert pattern (or uses bats)

## Boundaries

- [ ] CLI argument parsing in adapter/composition only
- [ ] Input validation at boundary before passing to domain
- [ ] File paths, URLs, credentials passed as parameters (not hardcoded)
- [ ] No sourcing of external files in domain functions
- [ ] Config centralized in composition root; no scattered env var reads

## Multi-File Layout (if applicable)

- [ ] `domain.sh` sources nothing external
- [ ] `application.sh` sources only `domain.sh`
- [ ] `adapters/*.sh` source nothing from domain/application (they implement contracts)
- [ ] `compose.sh` or `main` script sources everything and wires
- [ ] No circular source dependencies
