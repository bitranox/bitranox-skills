---
name: performance
description: "Use when reviewing Python code for performance issues: identifying caching opportunities in pure functions, finding uncompiled regex patterns, profiling hot spots with real test suites, or validating optimization claims. Runs standalone or as sub-agent of review_anal orchestrator."
---

# Performance Analysis

## Reviewer Mindset

**You are a meticulous performance analyzer - pedantic, precise, and relentlessly thorough.**

Your approach:
- **Systematic Identification:** Find ALL pure functions, expensive computations, uncompiled regex
- **Profile with REAL Data:** Use actual test suite, never synthetic benchmarks
- **Measure Evidence:** Cache hit rate must be >20%, improvement must be >5%
- **Cross-Reference:** Identify functions called frequently in profiling data
- **Reject Low-Benefit:** Don't recommend changes if criteria not met
- **Regex Hygiene:** Every repeated regex call must use a compiled pattern

**Your Questions:**
- "Is this function pure and deterministic? Let me analyze the AST."
- "Is it called frequently? Let me check profiling data."
- "Are regex patterns compiled at module level? Let me scan the AST."
- "What's the cache hit rate with REAL test data? Let me measure."
- "Does caching improve performance >5%? Let me benchmark with real tests."

## Purpose

Systematically identify performance issues — caching opportunities, uncompiled regex, hot spots — and validate with real test suite profiling. Present findings one-by-one, implement accepted fixes directly, and save declined items as documented false positives in the project instructions file.

## Reference Files

Use the Read tool to load referenced files for full details.

| Tool                          | File                           | Purpose                                                   |
|-------------------------------|--------------------------------|-----------------------------------------------------------|
| Pure function finder (AST)    | find_cache_candidates.py       | Detect pure, expensive functions via AST analysis         |
| Hotspot profiler              | find_hotspots.py               | Find frequently-called functions from cProfile data       |
| Candidate prioritizer         | prioritize_cache_candidates.py | Cross-reference pure functions with hotspots              |
| Cache profiling template      | profile_with_cache_template.py | Before/after profiling with lru_cache monkey-patch        |
| Uncompiled regex finder (AST) | find_uncompiled_regex.py       | Flag re.match/search/findall with string literal patterns |

## Workflow

```
Step 1 (Read instructions) → Step 2 (Setup) → Step 3 (Profile) →
Step 4 (Analyze: candidates + regex + hotspots + prioritize + audit existing caches) →
Step 5 (Merge & sort) → Step 6 (Present one-by-one) →
  ├─ Implement fix / remove ineffective cache + run tests
  └─ Save decline to instructions
  └─ Step 7 (Final verification)
```

## Execution Steps

### Step 1: Read Project Instructions

Before any analysis, read the project's CLAUDE.md or AGENTS.md and look for a `# Performance` section.

Collect all **previously reviewed items** — both fixes already implemented and findings the user declined (documented false positives). Each entry contains:
- Short title
- File path and function name
- Reason (why it was fixed, or why it was declined)

Also scan codebase for inline comments containing "by design", "intentional", or "performance: accepted".

All previously reviewed items are **OFF-LIMITS** — skip them silently during presentation in Step 6. Never re-suggest an already-implemented fix. Never re-raise a previously declined finding.

### Step 2: Setup

```bash
# Create temp directory for all scratch files
BX_PERF_TMPDIR=$(mktemp -d /tmp/bx-perf-XXXXXX)
echo "$BX_PERF_TMPDIR" > /tmp/bx-perf-session

# Validate we're in a Python project (walk upward looking for pyproject.toml)
found_project=false
check_dir="$(pwd)"
while [ "$check_dir" != "/" ]; do
    if [ -f "$check_dir/pyproject.toml" ]; then
        found_project=true
        PROJECT_ROOT="$check_dir"
        break
    fi
    check_dir="$(dirname "$check_dir")"
done

if [ "$found_project" = false ]; then
    echo "ERROR: No pyproject.toml found in any parent directory. Not a Python project."
    exit 1
fi

cd "$PROJECT_ROOT" || exit 1
echo "Working directory: $PROJECT_ROOT"

# Resolve SKILL_DIR: env var > project-local > user-level
if [ -z "${SKILL_DIR:-}" ]; then
    if [ -d "$PROJECT_ROOT/.claude/skills/performance" ]; then
        SKILL_DIR="$PROJECT_ROOT/.claude/skills/performance"
    elif [ -d "$HOME/.claude/skills/performance" ]; then
        SKILL_DIR="$HOME/.claude/skills/performance"
    else
        echo "ERROR: performance skill not found in project or user directory"
        exit 1
    fi
fi
echo "$SKILL_DIR" > /tmp/bx-perf-skill-dir

mkdir -p "$BX_PERF_TMPDIR"/{cache,logs,perf}

# Python validation
if [ -n "${BX_PERF_PYTHON:-}" ]; then
    PYTHON_CMD="$BX_PERF_PYTHON"
    if ! command -v "$PYTHON_CMD" &> /dev/null; then
        echo "ERROR: Python interpreter not found: $PYTHON_CMD"
        exit 1
    fi
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
    if echo "$PYTHON_VERSION" | grep -qE "Python 3\.(13|[2-9][0-9])"; then
        echo "Using BX_PERF_PYTHON: $PYTHON_CMD ($PYTHON_VERSION)"
    else
        echo "ERROR: Python version mismatch. Expected 3.13+, got: $PYTHON_VERSION"
        exit 1
    fi
else
    echo "Running in standalone mode - validating Python 3.13..."
    PYTHON_CMD=""
    if command -v python3.13 &> /dev/null; then
        PYTHON_CMD="python3.13"
    elif command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        if echo "$PYTHON_VERSION" | grep -qE "Python 3\.(13|[2-9][0-9])"; then
            PYTHON_CMD="python3"
        fi
    fi
    if [ -z "$PYTHON_CMD" ]; then
        echo "ERROR: Python 3.13 or higher not found"
        exit 1
    fi
    echo "Found Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"
fi

# Initialize status tracking
echo "IN_PROGRESS" > "$BX_PERF_TMPDIR/cache/status.txt"

set -e
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_num=$2
    echo "FAILED" > "$BX_PERF_TMPDIR/cache/status.txt"
    echo "Performance analysis failed - check logs for details"
    cat > "$BX_PERF_TMPDIR/cache/ERROR.txt" << EOF
Error occurred in Performance subagent
Exit code: $exit_code
Failed at line: $line_num
Time: $(date -Iseconds)
Check log file: $BX_PERF_TMPDIR/logs/cache.log
EOF
    exit $exit_code
}
```

### Step 3: Validate Prerequisites and Profile

```bash
BX_PERF_TMPDIR="$(cat /tmp/bx-perf-session 2>/dev/null)"
SKILL_DIR="$(cat /tmp/bx-perf-skill-dir 2>/dev/null)"

echo "Validating prerequisites..."
$PYTHON_CMD -m pip install --user pytest 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_install.txt" || true

# Profile unit tests
if [ ! -f "$BX_PERF_TMPDIR/perf/test_profile.prof" ]; then
    echo "Profiling unit tests..."
    $PYTHON_CMD -m cProfile -o "$BX_PERF_TMPDIR/perf/test_profile.prof" -m pytest tests/ -v 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_profiling.txt" || true
fi

# Profile local-only tests (if marker exists)
echo "Profiling local_only tests..."
$PYTHON_CMD -m cProfile -o "$BX_PERF_TMPDIR/perf/test_local_only.prof" -m pytest tests/ -v -m local_only 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_local_only_profiling.txt" || true

# Profile integration tests (if marker exists)
echo "Profiling integrationtest tests..."
$PYTHON_CMD -m cProfile -o "$BX_PERF_TMPDIR/perf/test_integration.prof" -m pytest tests/ -v -m integrationtest 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_integration_profiling.txt" || true

echo "Prerequisites validated"
```

### Step 4: Run Analysis Pipeline

#### 4a: Identify Pure Function Candidates

Run `find_cache_candidates.py` from the skill directory against the project's Python files:

```bash
BX_PERF_TMPDIR="$(cat /tmp/bx-perf-session 2>/dev/null)"
SKILL_DIR="$(cat /tmp/bx-perf-skill-dir 2>/dev/null)"

# Discover Python files
if [ -n "${BX_PERF_FILES:-}" ]; then
    python_files="$BX_PERF_FILES"
elif [ -d "src" ]; then
    python_files=$(find src/ -name '*.py' | tr '\n' ' ')
else
    python_files=$(find . -name '*.py' -not -path './.venv/*' -not -path './venv/*' | tr '\n' ' ')
fi

if [ -n "$python_files" ]; then
    $PYTHON_CMD "$SKILL_DIR/find_cache_candidates.py" $python_files > "$BX_PERF_TMPDIR/cache/cache_candidates.txt" 2>&1 || true
    echo "Cache candidates identified"
fi
```

#### 4b: Find Uncompiled Regex Patterns

Run `find_uncompiled_regex.py` and scan for `re.match()`, `re.search()`, `re.findall()`, etc. called with string literal patterns instead of pre-compiled objects:

```bash
BX_PERF_TMPDIR="$(cat /tmp/bx-perf-session 2>/dev/null)"
SKILL_DIR="$(cat /tmp/bx-perf-skill-dir 2>/dev/null)"

# Discover Python files
if [ -n "${BX_PERF_FILES:-}" ]; then
    python_files="$BX_PERF_FILES"
elif [ -d "src" ]; then
    python_files=$(find src/ -name '*.py' | tr '\n' ' ')
else
    python_files=$(find . -name '*.py' -not -path './.venv/*' -not -path './venv/*' | tr '\n' ' ')
fi

if [ -n "$python_files" ]; then
    $PYTHON_CMD "$SKILL_DIR/find_uncompiled_regex.py" $python_files > "$BX_PERF_TMPDIR/cache/uncompiled_regex.txt" 2>&1 || true
    echo "Uncompiled regex scan complete"
fi
```

Every `re.match(r'...', ...)` inside a function body should become a module-level `_RE = re.compile(r'...')` with `_RE.match(...)` at the call site. This avoids recompilation on every call.

#### 4c: Profile to Find Hot Functions

Run `find_hotspots.py` from the skill directory and analyze profiling data:

```bash
BX_PERF_TMPDIR="$(cat /tmp/bx-perf-session 2>/dev/null)"
SKILL_DIR="$(cat /tmp/bx-perf-skill-dir 2>/dev/null)"

# Analyze hotspots from all available profile files
> "$BX_PERF_TMPDIR/cache/hotspots.txt"
for prof_file in "$BX_PERF_TMPDIR/perf/"*.prof; do
    if [ -f "$prof_file" ]; then
        echo "--- $(basename "$prof_file") ---" >> "$BX_PERF_TMPDIR/cache/hotspots.txt"
        $PYTHON_CMD "$SKILL_DIR/find_hotspots.py" "$prof_file" >> "$BX_PERF_TMPDIR/cache/hotspots.txt" 2>&1 || true
    fi
done
echo "Hot spots identified"
```

#### 4d: Cross-Reference Candidates with Hot Spots

Run `prioritize_cache_candidates.py` from the skill directory:

```bash
BX_PERF_TMPDIR="$(cat /tmp/bx-perf-session 2>/dev/null)"
SKILL_DIR="$(cat /tmp/bx-perf-skill-dir 2>/dev/null)"

$PYTHON_CMD "$SKILL_DIR/prioritize_cache_candidates.py" "$BX_PERF_TMPDIR/cache/cache_candidates.txt" "$BX_PERF_TMPDIR/cache/hotspots.txt" > "$BX_PERF_TMPDIR/cache/priority_cache_candidates.txt" 2>&1 || true
echo "Priority candidates identified"
```

#### 4e: Audit Existing Caches

This is an instructions-only step (no script). Use the Grep tool to find existing cache decorators:

- Search pattern: `@lru_cache|@cache|@functools\.lru_cache|@functools\.cache`
- Exclude `.venv/`, `venv/`, `__pycache__/`

For each cached function found, read the function and evaluate:

1. Check profiling data from `hotspots.txt` — is the function called frequently (>100 calls)?
2. Read the function body — is it pure (no I/O, no side effects, deterministic)?
3. Check the function signature — are all args hashable (no mutable defaults leaking through)?
4. Cross-reference with hotspots — does caching this function actually save measurable time?

Manually write findings to `$BX_PERF_TMPDIR/cache/existing_caches.txt` with this format:
```
file:line - @decorator function_name()
Calls: N, Cumtime: Xs
Verdict: EFFECTIVE | INEFFECTIVE | HARMFUL
Reason: ...
```

Verdicts:
- **EFFECTIVE**: High call count, measurable time savings — keep (not presented in Step 6, but reported in Step 7 summary)
- **INEFFECTIVE**: Low call count (<100), negligible cumtime, or cache hit rate <20% — propose removal
- **HARMFUL**: Caches impure function, mutable args without conversion, or masks a bug — propose removal with explanation

### Step 5: Merge, Classify, and Sort Findings

Parse the five output files from Step 4. Output format reference:

- `cache_candidates.txt`: `file:line - function()` + `Reason: ...`
- `uncompiled_regex.txt`: `file:line - re.func(pattern, ...)` + `Fix: ...`
- `hotspots.txt`: `file:line - function()` + `Calls: N, Cumtime: Xs`
- `priority_cache_candidates.txt`: `file:line - function()`
- `existing_caches.txt`: `file:line - @decorator function_name()` + `Verdict: ...`

Classify each finding by severity:

- **SEVERE**: Uncompiled regex in a hot function (in both regex + hotspots) OR harmful existing cache
- **MEDIUM**: Priority cache candidate (confirmed by profiling) OR uncompiled regex in non-hot function OR ineffective existing cache
- **MINOR**: Cache candidate NOT confirmed by profiling

Filter out all accepted items collected in Step 1. Sort findings SEVERE → MEDIUM → MINOR.

### Step 6: Present and Implement Findings

Present each finding **ONE AT A TIME** using this format:

```
## Issue N: [Short Title]
**Severity**: SEVERE | MEDIUM | MINOR
**Type**: Uncompiled Regex | Cache Candidate | Ineffective Cache
**File**: file:line
**Function**: function_name
**Call count**: N (from profiling, if available)
**Description**: what the issue is (for Ineffective Cache: include the verdict reason — actual call count, cumtime, impurity details, or why the cache provides no benefit)
**Suggested fix**: specific code change
```

Ask: "Implement this fix? Or skip? If skipping, what's the reason?"

Wait for the user's response before proceeding to the next finding.

**On accept — Uncompiled Regex:**
1. Add `_RE_NAME = re.compile(r'...')` at module level (after imports)
2. Replace `re.func(r'...', text)` → `_RE_NAME.func(text)` at the call site
3. Run tests, show diff

**On accept — Cache Candidate:**
1. Add `from functools import lru_cache` if missing
2. Add `@lru_cache` decorator above function
3. If mutable args (list/dict), convert to tuples or use wrapper
4. Run tests, show diff

**On accept — Ineffective Cache (removal):**
1. Remove `@lru_cache` / `@cache` decorator from the function
2. Remove `from functools import lru_cache` / `cache` if no longer used
3. If mutable-arg wrappers were added only for caching, remove those too
4. Run tests, show diff

**On decline:**
Append to the `# Performance` section in the project's CLAUDE.md or AGENTS.md:

```
- **[Title]**: [user's reason]. [file:line, function_name]
```

Create the section or file if it does not exist. Never duplicate entries.

### Step 7: Final Verification

Run the full test suite. Report pass/fail. Summarize effective existing caches that were kept. Mark session complete:

```bash
BX_PERF_TMPDIR="$(cat /tmp/bx-perf-session 2>/dev/null)"

# Run full test suite
if [ -f "Makefile" ] && grep -q '^test' Makefile; then
    make test 2>&1 | tee "$BX_PERF_TMPDIR/cache/final_test_run.txt"
    TEST_EXIT=$?
else
    $PYTHON_CMD -m pytest tests/ -v 2>&1 | tee "$BX_PERF_TMPDIR/cache/final_test_run.txt"
    TEST_EXIT=$?
fi

if [ $TEST_EXIT -eq 0 ]; then
    echo "SUCCESS" > "$BX_PERF_TMPDIR/cache/status.txt"
    echo "Performance analysis complete - all tests passing"
else
    echo "FAILED" > "$BX_PERF_TMPDIR/cache/status.txt"
    echo "Performance analysis complete - TESTS FAILING (exit code: $TEST_EXIT)"
fi
```

After running the test suite, report:
- Total findings presented, accepted, declined
- Existing caches audited: list EFFECTIVE caches that were kept (from `existing_caches.txt`)
- Final test suite status: pass or fail

## Common Mistakes

| Mistake                                | Fix                                                   |
|----------------------------------------|-------------------------------------------------------|
| Dump all issues at once                | Present ONE at a time, wait for response              |
| Suggest changes to accepted items      | Read project instructions first, filter out           |
| Vague suggestions ("consider caching") | Show exact `@lru_cache` or `re.compile()` change      |
| Skip saving declined items             | ALWAYS append to project instructions                 |
| Not running tests after fixes          | Run tests after EVERY implementation                  |
| Caching impure functions               | Never cache time/random/I/O/state-modifying           |
| Caching with mutable args              | Convert list/dict to tuples; lru_cache needs hashable |
| Re-raising declined items              | Check accepted list from Step 1                       |
| MINOR before SEVERE                    | Sort: SEVERE → MEDIUM → MINOR                         |
| Ignoring existing ineffective caches   | Audit existing `@lru_cache`/`@cache`, propose removal |

## Key Behaviors

- **ALWAYS use REAL test suite** — never synthetic benchmarks
- **ALWAYS measure cache hit rate >20% AND improvement >5%**
- **NEVER cache without evidence** — show the profiling data
- **NEVER cache non-deterministic or side-effect functions**
- **ONE issue at a time** — never batch-present
- **ALWAYS audit existing caches** — verify they're still effective, propose removal if not
- **RESPECT prior decisions** — check project instructions before suggesting
