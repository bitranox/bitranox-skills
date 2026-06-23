# Script Mode -- One-File Clean Architecture (Bash)

Use when delivering a **single Bash file** (no separate library required).
Respects Domain/Application/Adapters boundaries logically inside one file.
Inherits all Non-Negotiables from the main skill.

---

## Rules

- Keep **all code in one file**, separated by section comment markers
- **Domain stays pure** (no I/O, no external commands); Application orchestrates via port function refs; Adapters do I/O
- `set -euo pipefail` at script top; `trap` cleanup in composition section
- Structured exit codes; map domain errors to exit codes in composition only
- Logging to stderr (`>&2`); stdout reserved for data output
- No code outside functions except: shebang, `set`, `readonly` constants, section markers, and final `main "$@"` call
- Layer prefixes enforced: `domain__`, `uc__`, `adapter__`

---

## One-File Logical Layout

```bash
#!/usr/bin/env bash
set -euo pipefail
# <Summary> -- minimal, structured CLI following Clean Architecture.

# === Constants ===
readonly VERSION="1.0.0"
readonly EXIT_OK=0
readonly EXIT_USAGE=2
readonly EXIT_NOT_FOUND=3
readonly EXIT_CONFLICT=4
readonly EXIT_INTERNAL=70
readonly EXIT_TIMEOUT=124

# === Observability ===
readonly TRACE_ID="${TRACE_ID:-$(date +%s%N)}"

log_info()  { echo "[INFO]  [$TRACE_ID] $*" >&2; }
log_error() { echo "[ERROR] [$TRACE_ID] $*" >&2; }
log_debug() { [[ "${DEBUG:-0}" == "1" ]] && echo "[DEBUG] [$TRACE_ID] $*" >&2 || true; }

# === Domain (pure functions -- NO I/O, no external commands) ===
domain__validate_thing() { :; }
domain__compute_result() { :; }

# === Application Ports (documented contracts) ===
# port: fetch_data -- $1=source -> stdout: raw data, return: 0|1
# port: store_result -- $1=data $2=dest -> return: 0|1

# === Application Use Cases (orchestration -- no direct I/O) ===
uc__process() {
    local fetch_fn="$1" store_fn="$2"
    shift 2
    # ... orchestrate domain + ports ...
}

# === Adapters (I/O: file, network, system) ===
adapter__fetch_from_file() { :; }
adapter__store_to_file() { :; }

# === CLI Adapter (argument parsing + output formatting) ===
adapter__parse_args() { :; }
adapter__format_output() { :; }

# === Composition (wire + main) ===
cleanup() { :; }  # trap handler

main() {
    trap cleanup EXIT

    # Parse & validate args (boundary)
    local args
    args=$(adapter__parse_args "$@") || exit $EXIT_USAGE

    # Wire adapters to use cases
    local result
    result=$(uc__process adapter__fetch_from_file adapter__store_to_file "$args") \
        || exit $EXIT_INTERNAL

    # Format output (adapter)
    adapter__format_output "$result"
}

main "$@"
```

---

## Exit Code Mapping

Map domain/application errors to exit codes **only in composition**:

```bash
main() {
    trap cleanup EXIT

    local validated_input
    validated_input=$(adapter__parse_and_validate "$@") || {
        log_error "Invalid arguments"
        exit $EXIT_USAGE
    }

    local result
    if ! result=$(uc__do_work adapter__read adapter__write "$validated_input"); then
        case $? in
            1) log_error "Not found"; exit $EXIT_NOT_FOUND ;;
            2) log_error "Conflict"; exit $EXIT_CONFLICT ;;
            *) log_error "Unexpected error"; exit $EXIT_INTERNAL ;;
        esac
    fi

    adapter__format_output "$result"
    exit $EXIT_OK
}
```

---

## Script Self-Check

- [ ] File has section comment markers (Domain/Application/Adapters/Composition)
- [ ] `set -euo pipefail` at top
- [ ] Domain functions contain no I/O, no external commands, no `echo` to terminal
- [ ] Use cases receive port function names as arguments (DIP)
- [ ] Adapters implement documented port contracts
- [ ] Args validated at boundary; errors mapped to exit codes in composition only
- [ ] Logging to stderr; stdout for data only
- [ ] No code outside functions (except shebang, set, readonly, section markers, final `main "$@"`)
- [ ] `trap` cleanup in composition section only
- [ ] Layer prefixes used: `domain__`, `uc__`, `adapter__`
- [ ] Bash >=4.3 compatible (namerefs require 4.3+; avoid namerefs if targeting macOS default bash 3.2)
