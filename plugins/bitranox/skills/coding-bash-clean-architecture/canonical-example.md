# Canonical Example -- Service Health Check (Bash)

A CLI tool that checks health of multiple services, validates results, and produces a report.
Demonstrates all layers, dependency inversion, testability, and structured error handling.

---

## Domain (Pure Functions)

```bash
# === Domain (pure functions -- NO I/O, no external commands) ===

# Validate a service definition string "name:host:port"
# stdout: validated string | stderr: error message
domain__validate_service_def() {
    local def="$1"
    local name host port

    IFS=: read -r name host port <<< "$def"

    [[ -n "$name" ]] || { echo "error: empty service name" >&2; return 1; }
    # Not just non-empty: this host reaches a shell redirection in the TCP adapter, so the
    # character set is the rule that matters. A non-empty check alone lets `a;id;x` through.
    [[ "$host" =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ ]] \
        || { echo "error: invalid host for $name" >&2; return 1; }
    [[ "$port" =~ ^[0-9]+$ ]] || { echo "error: port must be numeric for $name" >&2; return 1; }
    (( port >= 1 && port <= 65535 )) || { echo "error: port out of range for $name" >&2; return 1; }

    echo "${name}:${host}:${port}"
}

# Parse a service definition into nameref associative array
domain__parse_service() {
    local def="$1"
    declare -n _svc="$2"

    IFS=: read -r "_svc[name]" "_svc[host]" "_svc[port]" <<< "$def"
}

# Determine health status from check result
# $1=response_time_ms $2=threshold_ms
# stdout: "healthy" | "degraded" | "down"
domain__classify_health() {
    local response_time="$1"
    local threshold="$2"

    if [[ "$response_time" == "-1" ]]; then
        echo "down"
    elif (( response_time > threshold )); then
        echo "degraded"
    else
        echo "healthy"
    fi
}

# Build summary from individual check results (one per line: "name status time_ms")
# stdout: summary lines
domain__build_summary() {
    local results="$1"
    local total=0 healthy=0 degraded=0 down=0

    while IFS=' ' read -r _name status _time; do
        # A here-string always appends a newline, so an empty or newline-terminated
        # accumulator still yields one blank record. Guard the RECORD, not the string.
        [[ -n "$_name" ]] || continue
        (( ++total ))
        case "$status" in
            healthy)  (( ++healthy )) ;;
            degraded) (( ++degraded )) ;;
            down)     (( ++down )) ;;
        esac
    done <<< "$results"

    echo "total=$total"
    echo "healthy=$healthy"
    echo "degraded=$degraded"
    echo "down=$down"

    if (( down > 0 )); then
        echo "overall=critical"
    elif (( degraded > 0 )); then
        echo "overall=warning"
    else
        echo "overall=ok"
    fi
}
```

---

## Application Ports (Contracts)

```bash
# === Application Ports (documented function signature contracts) ===

# port: check_tcp
# Checks if a TCP port is reachable.
# args: $1=host $2=port $3=timeout_seconds
# stdout: response_time_ms (or "-1" if unreachable)
# return: 0 always (response_time conveys status)

# port: read_service_list
# Reads service definitions from a source.
# args: $1=source_path
# stdout: one "name:host:port" line per service
# return: 0 on success, 1 if source not found

# port: write_report
# Writes a health report.
# args: $1=report_content $2=destination
# return: 0 on success, 1 on failure
```

---

## Application Use Cases

```bash
# === Application Use Cases (orchestration via port references) ===

# Check health of all services from a config source.
# $1=check_tcp_fn $2=read_services_fn $3=write_report_fn
# $4=source_path $5=report_dest $6=threshold_ms
# $7=name of the caller's report variable (nameref out-parameter)
uc__check_all_services() {
    local check_tcp_fn="$1"
    local read_services_fn="$2"
    local write_report_fn="$3"
    local source_path="$4"
    local report_dest="$5"
    local threshold="${6:-1000}"
    declare -n _uc_report_out="$7"

    # Read service list via port
    local service_lines
    service_lines=$("$read_services_fn" "$source_path") || return 1

    local results=""
    local line

    while IFS= read -r line; do
        [[ -n "$line" ]] || continue

        # Validate (domain - pure)
        local validated
        validated=$(domain__validate_service_def "$line") || continue

        # Parse (domain - pure)
        declare -A svc=()
        domain__parse_service "$validated" svc

        # Check via port (adapter does I/O)
        local response_time
        response_time=$("$check_tcp_fn" "${svc[host]}" "${svc[port]}" 5)

        # Classify (domain - pure)
        local status
        status=$(domain__classify_health "$response_time" "$threshold")

        results+="${svc[name]} $status ${response_time}"$'\n'
    done <<< "$service_lines"

    # Build summary (domain - pure)
    local report
    report=$(domain__build_summary "$results")

    # Hand the report back through the nameref, NOT stdout: the write port below
    # may print to stdout itself, and a caller capturing us would swallow it and
    # get the report twice.
    _uc_report_out="$report"

    # Write via port (adapter does I/O)
    "$write_report_fn" "$report" "$report_dest" || return 1
}
```

---

## Adapters

### TCP Check Adapter

```bash
# === Adapters ===

# Implements port: check_tcp
adapter__check_tcp_nc() {
    local host="$1" port="$2" timeout_sec="${3:-5}"
    local start end elapsed

    start=$(date +%s%N)

    # Positional args into a SINGLE-quoted body: interpolating them makes `bash -c` re-parse the
    # values as code, so a host of `a;id;x` from the config file would run `id`.
    # The single quotes above ARE the fix; expanding here would be the bug, so silence SC2016.
    # shellcheck disable=SC2016
    if timeout "$timeout_sec" bash -c 'exec 3<>"/dev/tcp/$1/$2"' _ "$host" "$port" 2>/dev/null; then
        end=$(date +%s%N)
        elapsed=$(( (end - start) / 1000000 ))
        echo "$elapsed"
    else
        echo "-1"
    fi
}
```

### File Adapters

```bash
# Implements port: read_service_list
adapter__read_services_from_file() {
    local file="$1"
    [[ -f "$file" ]] || { echo "error: config file not found: $file" >&2; return 1; }
    # Strip comments and blank lines
    grep -v '^\s*#' "$file" | grep -v '^\s*$'
}

# Implements port: write_report
adapter__write_report_to_file() {
    local content="$1" dest="$2"
    local dir
    dir=$(dirname "$dest")
    [[ -d "$dir" ]] || mkdir -p "$dir"
    echo "$content" > "$dest"
}

# Implements port: write_report (stdout variant)
adapter__write_report_to_stdout() {
    local content="$1"
    shift  # ignore destination
    echo "$content"
}
```

### CLI Adapter

```bash
# CLI argument parsing (adapter boundary)
adapter__parse_args() {
    local config_file="" report_dest="-" threshold=1000

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--config)    config_file="$2"; shift 2 ;;
            -o|--output)    report_dest="$2"; shift 2 ;;
            -t|--threshold) threshold="$2"; shift 2 ;;
            -h|--help)      adapter__show_usage; exit 0 ;;
            -V|--version)   echo "$VERSION"; exit 0 ;;
            *)              echo "error: unknown option: $1" >&2; return 1 ;;
        esac
    done

    [[ -n "$config_file" ]] || { echo "error: --config is required" >&2; return 1; }
    [[ "$threshold" =~ ^[0-9]+$ ]] || { echo "error: --threshold must be numeric" >&2; return 1; }

    echo "${config_file}:${report_dest}:${threshold}"
}

adapter__show_usage() {
    cat >&2 <<'USAGE'
Usage: health-check -c CONFIG [-o OUTPUT] [-t THRESHOLD_MS]

Options:
  -c, --config FILE       Service definitions (name:host:port per line)
  -o, --output FILE       Report destination (default: stdout)
  -t, --threshold MS      Response time threshold (default: 1000)
  -h, --help              Show this help
  -V, --version           Show version
USAGE
}

# Format report for human display
adapter__format_report_human() {
    local report="$1"
    local overall
    overall=$(echo "$report" | grep '^overall=' | cut -d= -f2)

    echo "=== Service Health Report ==="
    echo "$report" | grep -v '^overall=' | while IFS='=' read -r key val; do
        printf "  %-12s %s\n" "$key:" "$val"
    done
    echo "  Overall:     $overall"
    echo "=============================="
}
```

---

## Composition Root

```bash
#!/usr/bin/env bash
set -euo pipefail

readonly VERSION="1.0.0"
readonly EXIT_OK=0
readonly EXIT_USAGE=2
readonly EXIT_NOT_FOUND=3
readonly EXIT_INTERNAL=70

readonly TRACE_ID="${TRACE_ID:-$(date +%s%N)}"
log_info()  { echo "[INFO]  [$TRACE_ID] $*" >&2; }
log_error() { echo "[ERROR] [$TRACE_ID] $*" >&2; }

# Source layers (in multi-file, these would be separate files)
# source lib/domain.sh
# source lib/application.sh
# source lib/adapters/file.sh
# source lib/adapters/tcp.sh

# Support sourcing for tests: `source script.sh --source-only`. This MUST come
# AFTER the layer sources above: put it first and a test sourcing this file
# returns 0 having defined nothing.
[[ "${1:-}" == "--source-only" ]] && return 0

cleanup() {
    # Remove temp files, release locks, etc.
    :
}

main() {
    trap cleanup EXIT

    # Parse args (adapter boundary)
    local parsed
    parsed=$(adapter__parse_args "$@") || {
        adapter__show_usage
        exit $EXIT_USAGE
    }

    local config_file report_dest threshold
    IFS=: read -r config_file report_dest threshold <<< "$parsed"

    log_info "Starting health check: config=$config_file threshold=${threshold}ms"

    # Select write adapter based on destination
    local write_fn="adapter__write_report_to_file"
    [[ "$report_dest" != "-" ]] || write_fn="adapter__write_report_to_stdout"

    # Execute use case with wired adapters. NOT inside a command substitution:
    # the stdout write adapter prints the report, and a capture here would
    # swallow it and corrupt $result.
    local result="" rc=0
    uc__check_all_services \
        adapter__check_tcp_nc \
        adapter__read_services_from_file \
        "$write_fn" \
        "$config_file" \
        "$report_dest" \
        "$threshold" \
        result \
        || rc=$?

    if (( rc != 0 )); then
        case $rc in
            1) log_error "Config not found: $config_file"; exit $EXIT_NOT_FOUND ;;
            *) log_error "Health check failed"; exit $EXIT_INTERNAL ;;
        esac
    fi

    # Format for human display (adapter)
    adapter__format_report_human "$result" >&2

    # Determine exit code from overall status
    local overall
    overall=$(echo "$result" | grep '^overall=' | cut -d= -f2)
    case "$overall" in
        ok)       exit $EXIT_OK ;;
        warning)  exit $EXIT_OK ;;  # still success, just degraded
        critical) exit 1 ;;
    esac
}

main "$@"
```

---

## Testing with Stub Adapters

```bash
#!/usr/bin/env bash
set -euo pipefail
# test_health_check.sh -- Unit and stub tests

# Source the script under test (all functions)
# No `2>/dev/null || true` here: a source that defines nothing must be loud.
source "$(dirname "$0")/../health-check.sh" --source-only

PASS=0 FAIL=0

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [[ "$expected" == "$actual" ]]; then
        echo "PASS: $desc"
        (( ++PASS ))
    else
        echo "FAIL: $desc (expected='$expected', actual='$actual')"
        (( ++FAIL ))
    fi
}

# --- Domain Unit Tests (pure, no mocking needed) ---

test_validate_service_def__valid() {
    local result
    result=$(domain__validate_service_def "web:example.com:443")
    assert_eq "valid service def" "web:example.com:443" "$result"
}

test_validate_service_def__invalid_port() {
    domain__validate_service_def "web:example.com:abc" 2>/dev/null && {
        echo "FAIL: should reject non-numeric port"; (( ++FAIL ))
    } || {
        echo "PASS: rejects non-numeric port"; (( ++PASS ))
    }
}

test_classify_health__healthy() {
    local result
    result=$(domain__classify_health "50" "1000")
    assert_eq "healthy response" "healthy" "$result"
}

test_classify_health__down() {
    local result
    result=$(domain__classify_health "-1" "1000")
    assert_eq "down response" "down" "$result"
}

test_build_summary__all_healthy() {
    # The trailing newline is what uc__check_all_services actually produces.
    # Without it this test never sees the accumulator's real shape.
    local input=$'web healthy 50\napi healthy 30\n'
    local result
    result=$(domain__build_summary "$input")
    assert_eq "counts both services" "2" "$(echo "$result" | grep '^total=' | cut -d= -f2)"
    assert_eq "overall ok" "ok" "$(echo "$result" | grep '^overall=' | cut -d= -f2)"
}

# --- Use Case Tests with Stubs ---

stub__check_tcp_always_healthy() {
    echo "42"  # 42ms response time
}

stub__read_services() {
    echo "web:localhost:80"
    echo "api:localhost:8080"
}

stub__write_report_noop() {
    :  # do nothing
}

test_uc__check_all_services() {
    local result=""
    uc__check_all_services \
        stub__check_tcp_always_healthy \
        stub__read_services \
        stub__write_report_noop \
        "/fake/path" \
        "/fake/dest" \
        1000 \
        result
    local overall
    overall=$(echo "$result" | grep '^overall=' | cut -d= -f2)
    assert_eq "all healthy -> ok" "ok" "$overall"
}

# --- Run all tests ---
test_validate_service_def__valid
test_validate_service_def__invalid_port
test_classify_health__healthy
test_classify_health__down
test_build_summary__all_healthy
test_uc__check_all_services

echo "---"
echo "Results: $PASS passed, $FAIL failed"
(( FAIL == 0 )) || exit 1
```

---

## Key Patterns Demonstrated

| Pattern                   | Where                                                                              |
|---------------------------|------------------------------------------------------------------------------------|
| **Pure domain functions** | `domain__validate_service_def`, `domain__classify_health`, `domain__build_summary` |
| **Dependency inversion**  | `uc__check_all_services` receives function names for all I/O                       |
| **Nameref data passing**  | `domain__parse_service` populates caller's associative array                       |
| **Port contracts**        | Documented function signatures with args/stdout/return spec                        |
| **Stub adapters**         | `stub__check_tcp_always_healthy` replaces real TCP check in tests                  |
| **Composition root**      | `main()` wires adapters, parses args, maps exit codes                              |
| **Structured exit codes** | Domain errors mapped to exit codes only in `main()`                                |
| **Logging to stderr**     | `log_info`, `log_error` write to `>&2`; stdout reserved for data                   |
