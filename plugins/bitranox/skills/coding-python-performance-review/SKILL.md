---
name: coding-python-performance-review
description: "Use when reviewing Python code for performance: identifying caching opportunities in pure functions, finding uncompiled regex patterns, profiling hot spots with real test suites, validating optimization claims from a diff, or comparing before/after timing across git history. Runs standalone or as a performance sub-agent inside a larger code-review workflow."
---

# Python Performance Reviewer

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
- "Does this read a big file / huge DB result / huge logfile fully into memory? Could it stream?"
- "Is external input length-bounded and sanitized, or can adversarial input blow up time/memory?"

## Always Flag: Unbounded Memory and Unsafe Input

Independent of the cache/regex pipeline, these are first-class findings (usually SEVERE):

- **Unbounded memory growth.** Code that reads big files, huge database result sets, or huge
  log files fully into memory - or accumulates an unbounded list/dict/string - instead of
  streaming, iterating, chunking, or paginating. Require bounded memory (generators, `iter`
  chunks, server-side cursors, line-by-line/`io` streaming, pagination). Only neglect this when
  the dataset is provably and safely bounded (small, fixed size); then materializing is fine.
- **Unsafe / unbounded input.** Input that is not size-bounded or sanitized: unbounded length,
  unvalidated types, and unhandled encoding or arbitrary characters (non-ASCII, emoji, CJK,
  control characters, binary data). Adversarial input must not blow up time or memory (ReDoS,
  quadratic blow-ups, OOM). Inputs must be bounded, validated, and the handling tested.
- **Untrusted structured input.** Structured data (a dict, JSON, a deserialized payload) used
  without parsing or validating its structure - assuming keys, types, or shape that may be
  missing or wrong. Require a parse/validation step at the boundary, unless the project has
  deliberately accepted skipping it.

## Purpose

Systematically identify performance issues  -  caching opportunities, uncompiled regex, hot spots  -  and validate with real test suite profiling. Present findings one-by-one, implement accepted fixes directly, and save declined items as documented false positives in the project instructions file.

## Reference Files

Use the Read tool to load referenced files for full details.

| Tool                          | File                           | Purpose                                                   |
|-------------------------------|--------------------------------|-----------------------------------------------------------|
| Pure function finder (AST)    | find_cache_candidates.py       | Detect pure, expensive functions via AST analysis         |
| Hotspot profiler              | find_hotspots.py               | Find frequently-called functions from cProfile data       |
| Candidate prioritizer         | prioritize_cache_candidates.py | Cross-reference pure functions with hotspots              |
| Cache profiling template      | profile_with_cache_template.py | Before/after profiling with lru_cache monkey-patch        |
| Uncompiled regex finder (AST) | find_uncompiled_regex.py       | Flag re.match/search/findall with string literal patterns |
| Unbounded memory finder (AST) | find_unbounded_memory.py       | Flag whole-file/DB/log reads that materialize large data  |
| Performance claims checker    | validate_perf_claims.py        | Extract and validate performance claims from a diff       |
| Before/after comparator       | compare_performance.py         | Git-based before/after test-suite timing comparison       |

## Workflow

> Tiering: the profiling runs (Step 3) are mechanical - run them in parallel/background, no model. The
> bounded judgment work (Step 4's existing-cache audit, and review-pipeline claim-validation below) is
> ideal **`sonnet`** subagent work. The final synthesis/prioritization call warrants **`opus`**: if it
> runs inline (not dispatched), and the session is not on `opus`, offer switch-model-or-continue per
> "The session model is fixed" in `bitranox:process-agents-subagent-driven-development` (the main agent
> cannot self-switch its model). See "Concrete tiers" in the same skill.

```
Step 1 (Read instructions) -> Step 2 (Setup) -> Step 3 (Profile) ->
Step 4 (Analyze: candidates + regex + hotspots + prioritize + audit existing caches) ->
Step 5 (Merge & sort) -> Step 6 (Present one-by-one) ->
  -- Implement fix / remove ineffective cache + run tests
  -- Save decline to instructions
  -- Step 7 (Final verification)
```

### Validating a claim or comparing before/after (review-pipeline mode)

When invoked to vet a performance claim in a diff rather than hunt for new ones, skip the
discovery steps and use the two checker tools directly:

- `validate_perf_claims.py <diff_file>` - extract any "Nx faster / N% faster" style claims from
  the diff and check them against a real profiled run; report unproven or contradicted claims.
- `compare_performance.py` - stash the working changes, time the test suite on the previous
  commit, restore, time again, and report the measured delta as before/after evidence.

Report findings with measured numbers from the real test suite; never accept a claim on
synthetic benchmarks.

## Execution Steps

### Step 1: Read Project Instructions

Before any analysis, read the project's CLAUDE.md or AGENTS.md and look for a `# Performance` section.

Collect all **previously reviewed items**  -  both fixes already implemented and findings the user declined (documented false positives). Each entry contains:
- Short title
- File path and function name
- Reason (why it was fixed, or why it was declined)

Also scan codebase for inline comments containing "by design", "intentional", or "performance: accepted".

All previously reviewed items are **OFF-LIMITS**  -  skip them silently during presentation in Step 6. Never re-suggest an already-implemented fix. Never re-raise a previously declined finding.

### Step 2: Setup

Run the portable bootstrap. `setup_env.py` is stdlib-only and cross-platform: it
walks up from the current directory for a `pyproject.toml` (clear error + non-zero
exit if none), creates a scratch temp dir (via `tempfile.mkdtemp`, honouring
TMPDIR/TEMP/TMP - never a hardcoded `/tmp`) with `cache/ logs/ perf/` subdirs,
validates the running interpreter is Python 3.13+, and writes `session.json` into
that scratch dir holding every path later steps need.

`SKILL_DIR` is the directory containing `setup_env.py` (the skill directory).
`uv run` is preferred (it fetches an isolated 3.13+ interpreter); plain `python`
works too. Run it once, capturing the printed session-file path. The script prints
`Session file: <path>` on its first line, echoes the full JSON, and exits non-zero
with a clear stderr message if there is no `pyproject.toml` or the interpreter is
too old. `session.json` replaces the old `/tmp/bx-perf-session` and
`/tmp/bx-perf-skill-dir` side-channel files; it contains `tmpdir`, `project_root`,
`skill_dir`, `python`, and `status`.

```bash
# Run the bootstrap once; capture the path to session.json from its output.
BX_PERF_OUT="$(uv run "$SKILL_DIR/setup_env.py" || python "$SKILL_DIR/setup_env.py")" || {
    echo "Setup failed - aborting performance analysis"; exit 1
}
echo "$BX_PERF_OUT"
BX_PERF_SESSION="$(printf '%s\n' "$BX_PERF_OUT" | sed -n 's/^Session file: //p')"
```

Read any field back portably with a tiny stdlib `python -c` (no `jq` needed):

```bash
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
PYTHON_CMD="$(read_field python)"
BX_PERF_TMPDIR="$(read_field tmpdir)"
SKILL_DIR="$(read_field skill_dir)"
```

### Step 3: Validate Prerequisites and Profile

```bash
# Re-load paths from session.json (set BX_PERF_SESSION in Step 2). All stdlib, no jq.
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)"
SKILL_DIR="$(read_field skill_dir)"
PYTHON_CMD="$(read_field python)"

echo "Validating prerequisites..."
# Ensure pytest is importable. Do NOT use `pip install --user` (it misbehaves in
# uv-managed / Python 3.13+ envs). Only install if genuinely missing, preferring uv.
if ! $PYTHON_CMD -c "import pytest" 2>/dev/null; then
    echo "pytest not found - installing..."
    uv pip install pytest 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_install.txt" \
        || $PYTHON_CMD -m pip install pytest 2>&1 | tee -a "$BX_PERF_TMPDIR/cache/pytest_install.txt" \
        || true
fi

# Detect the test directory portably: prefer pyproject [tool.pytest.ini_options]
# testpaths, else the first existing of tests/ test/, else let pytest discover.
TESTDIR="$(python - <<'PY'
import os
try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None
paths = []
if tomllib and os.path.isfile("pyproject.toml"):
    try:
        with open("pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
        tp = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths")
        if isinstance(tp, str):
            paths = tp.split()
        elif isinstance(tp, list):
            paths = list(tp)
    except Exception:
        paths = []
chosen = next((p for p in paths if os.path.isdir(p)), None)
if chosen is None:
    chosen = next((d for d in ("tests", "test") if os.path.isdir(d)), "")
print(chosen)
PY
)"
echo "Test directory: ${TESTDIR:-<pytest discovery>}"

# Profile unit tests
if [ ! -f "$BX_PERF_TMPDIR/perf/test_profile.prof" ]; then
    echo "Profiling unit tests..."
    $PYTHON_CMD -m cProfile -o "$BX_PERF_TMPDIR/perf/test_profile.prof" -m pytest ${TESTDIR:+"$TESTDIR"} -v 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_profiling.txt" || true
fi

# Profile local-only tests (if marker exists)
echo "Profiling local_only tests..."
$PYTHON_CMD -m cProfile -o "$BX_PERF_TMPDIR/perf/test_local_only.prof" -m pytest ${TESTDIR:+"$TESTDIR"} -v -m local_only 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_local_only_profiling.txt" || true

# Profile integration tests (if marker exists)
echo "Profiling integrationtest tests..."
$PYTHON_CMD -m cProfile -o "$BX_PERF_TMPDIR/perf/test_integration.prof" -m pytest ${TESTDIR:+"$TESTDIR"} -v -m integrationtest 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_integration_profiling.txt" || true

echo "Prerequisites validated"
```

### Step 4: Run Analysis Pipeline

#### 4a: Identify Pure Function Candidates

Run `find_cache_candidates.py` from the skill directory against the project's Python files:

```bash
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)"; SKILL_DIR="$(read_field skill_dir)"; PYTHON_CMD="$(read_field python)"

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
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)"; SKILL_DIR="$(read_field skill_dir)"; PYTHON_CMD="$(read_field python)"

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
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)"; SKILL_DIR="$(read_field skill_dir)"; PYTHON_CMD="$(read_field python)"

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
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)"; SKILL_DIR="$(read_field skill_dir)"; PYTHON_CMD="$(read_field python)"

$PYTHON_CMD "$SKILL_DIR/prioritize_cache_candidates.py" "$BX_PERF_TMPDIR/cache/cache_candidates.txt" "$BX_PERF_TMPDIR/cache/hotspots.txt" > "$BX_PERF_TMPDIR/cache/priority_cache_candidates.txt" 2>&1 || true
echo "Priority candidates identified"
```

#### 4e: Audit Existing Caches

This is an instructions-only step (no script). Use the Grep tool to find existing cache decorators:

- Search pattern: `@lru_cache|@cache|@functools\.lru_cache|@functools\.cache`
- Exclude `.venv/`, `venv/`, `__pycache__/`

For each cached function found, read the function and evaluate:

1. Check profiling data from `hotspots.txt`  -  is the function called frequently (>100 calls)?
2. Read the function body  -  is it pure (no I/O, no side effects, deterministic)?
3. Check the function signature  -  are all args hashable (no mutable defaults leaking through)?
4. Cross-reference with hotspots  -  does caching this function actually save measurable time?

Manually write findings to `$BX_PERF_TMPDIR/cache/existing_caches.txt` with this format:
```
file:line - @decorator function_name()
Calls: N, Cumtime: Xs
Verdict: EFFECTIVE | INEFFECTIVE | HARMFUL
Reason: ...
```

Verdicts:
- **EFFECTIVE**: High call count, measurable time savings  -  keep (not presented in Step 6, but reported in Step 7 summary)
- **INEFFECTIVE**: Low call count (<100), negligible cumtime, or cache hit rate <20%  -  propose removal
- **HARMFUL**: Caches impure function, mutable args without conversion, or masks a bug  -  propose removal with explanation

#### 4f: Detect Unbounded Memory Patterns

Run `find_unbounded_memory.py` to flag code that reads big files, huge database result sets, or huge log files fully into memory (whole-file `read()`/`readlines()`/`read_text()`, `fetchall()`, pandas readers without `chunksize=`) instead of streaming. Each hit is a CANDIDATE - confirm the source can actually grow unbounded before flagging it (a provably small, fixed dataset is fine), then classify it SEVERE.

```bash
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)"; SKILL_DIR="$(read_field skill_dir)"; PYTHON_CMD="$(read_field python)"

# Discover Python files
if [ -n "${BX_PERF_FILES:-}" ]; then
    python_files="$BX_PERF_FILES"
elif [ -d "src" ]; then
    python_files=$(find src/ -name '*.py' | tr '\n' ' ')
else
    python_files=$(find . -name '*.py' -not -path './.venv/*' -not -path './venv/*' | tr '\n' ' ')
fi

if [ -n "$python_files" ]; then
    $PYTHON_CMD "$SKILL_DIR/find_unbounded_memory.py" $python_files > "$BX_PERF_TMPDIR/memory_candidates.txt" 2>&1 || true
    echo "Unbounded-memory candidates identified"
fi
```

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

Filter out all accepted items collected in Step 1. Sort findings SEVERE -> MEDIUM -> MINOR.

### Step 6: Present and Implement Findings

Present each finding **ONE AT A TIME** using this format:

```
## Issue N: [Short Title]
**Severity**: SEVERE | MEDIUM | MINOR
**Type**: Uncompiled Regex | Cache Candidate | Ineffective Cache
**File**: file:line
**Function**: function_name
**Call count**: N (from profiling, if available)
**Description**: what the issue is (for Ineffective Cache: include the verdict reason  -  actual call count, cumtime, impurity details, or why the cache provides no benefit)
**Suggested fix**: specific code change
```

Ask: "Implement this fix? Or skip? If skipping, what's the reason?"

Wait for the user's response before proceeding to the next finding.

**On accept  -  Uncompiled Regex:**
1. Add `_RE_NAME = re.compile(r'...')` at module level (after imports)
2. Replace `re.func(r'...', text)` -> `_RE_NAME.func(text)` at the call site
3. Run tests, show diff

**On accept  -  Cache Candidate:**
1. Add `from functools import lru_cache` if missing
2. Add `@lru_cache` decorator above function
3. If mutable args (list/dict), convert to tuples or use wrapper
4. Run tests, show diff

**On accept  -  Ineffective Cache (removal):**
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
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
read_field() { python -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)"; PYTHON_CMD="$(read_field python)"

# Detect the test directory portably (same logic as Step 3): prefer pyproject
# testpaths, else first existing of tests/ test/, else let pytest discover.
TESTDIR="$(python - <<'PY'
import os
try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None
paths = []
if tomllib and os.path.isfile("pyproject.toml"):
    try:
        with open("pyproject.toml", "rb") as fh:
            data = tomllib.load(fh)
        tp = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths")
        if isinstance(tp, str):
            paths = tp.split()
        elif isinstance(tp, list):
            paths = list(tp)
    except Exception:
        paths = []
chosen = next((p for p in paths if os.path.isdir(p)), None)
if chosen is None:
    chosen = next((d for d in ("tests", "test") if os.path.isdir(d)), "")
print(chosen)
PY
)"

# Run full test suite
if [ -f "Makefile" ] && grep -q '^test' Makefile; then
    make test 2>&1 | tee "$BX_PERF_TMPDIR/cache/final_test_run.txt"
    TEST_EXIT=$?
else
    $PYTHON_CMD -m pytest ${TESTDIR:+"$TESTDIR"} -v 2>&1 | tee "$BX_PERF_TMPDIR/cache/final_test_run.txt"
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
| MINOR before SEVERE                    | Sort: SEVERE -> MEDIUM -> MINOR                       |
| Ignoring existing ineffective caches   | Audit existing `@lru_cache`/`@cache`, propose removal |

## Key Behaviors

- **ALWAYS use REAL test suite**  -  never synthetic benchmarks
- **ALWAYS measure cache hit rate >20% AND improvement >5%**
- **NEVER cache without evidence**  -  show the profiling data
- **NEVER cache non-deterministic or side-effect functions**
- **ONE issue at a time**  -  never batch-present
- **ALWAYS audit existing caches**  -  verify they're still effective, propose removal if not
- **RESPECT prior decisions**  -  check project instructions before suggesting
- **ALWAYS flag unbounded memory**  -  big files / huge DB results / huge logfiles must stream, not load whole
- **ALWAYS flag unsafe input**  -  bound length, sanitize types/encoding (non-ASCII/emoji/CJK/binary), test it
