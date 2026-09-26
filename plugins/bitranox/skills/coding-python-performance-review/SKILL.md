---
name: coding-python-performance-review
description: Use when reviewing Python code for performance - identifying caching opportunities in pure functions, finding uncompiled regex patterns, profiling hot spots with real test suites, validating optimization claims from a diff, or comparing before/after timing across git history. Runs standalone or as a performance sub-agent inside a larger code-review workflow.
---

# Python Performance Reviewer

## Reviewer Mindset

**You are a meticulous performance analyzer - pedantic, precise, and relentlessly thorough.**

Your approach:
- **Systematic Identification:** Find ALL pure functions, expensive computations, uncompiled regex
- **Profile with REAL Data:** Use actual test suite, never synthetic benchmarks
- **Measure Evidence:** Cache hit rate must be >=20%, improvement must be >5%
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

| Tool                          | File                           | Purpose                                                    |
|-------------------------------|--------------------------------|------------------------------------------------------------|
| Pure function finder (AST)    | find_cache_candidates.py       | Detect pure, expensive functions via AST analysis          |
| Hotspot profiler              | find_hotspots.py               | Find frequently-called functions from cProfile data        |
| Candidate prioritizer         | prioritize_cache_candidates.py | Cross-reference pure functions with hotspots               |
| Cache profiling template      | profile_with_cache_template.py | Before/after profiling with lru_cache monkey-patch         |
| Uncompiled regex finder (AST) | find_uncompiled_regex.py       | Flag re.match/search/findall with string literal patterns  |
| Unbounded memory finder (AST) | find_unbounded_memory.py       | Flag whole-file/DB/log reads that materialize large data   |
| Performance claims extractor  | validate_perf_claims.py        | Extract claims from a diff; YOU validate each by profiling |
| Before/after comparator       | compare_performance.py         | Git-based before/after test-suite timing comparison        |

## Workflow

> Tiering: the profiling runs (Step 3) are mechanical - run them in parallel/background, no model. The
> bounded judgment work (Step 4's existing-cache audit, and review-pipeline claim-validation below) is
> ideal **`sonnet`** subagent work. The final synthesis/prioritization call warrants **`opus`**: if it
> runs inline (not dispatched), and the session is not on `opus`, offer switch-model-or-continue per
> "The session model is fixed" in `bitranox:process-agents-subagent-driven-development` (the main agent
> cannot self-switch its model). See "Concrete tiers" in the same skill.

```
Step 1 (Read instructions) -> Step 2 (Setup) -> Step 3 (Profile) ->
Step 4 (Analyze: candidates + regex + hotspots + prioritize + audit existing caches + unbounded memory) ->
Step 5 (Merge & sort) -> Step 6 (Present one-by-one) ->
  -- Implement fix / remove ineffective cache + run tests
  -- Save decline to instructions
  -- Step 7 (Final verification)
```

### Validating a claim or comparing before/after (review-pipeline mode)

When invoked to vet a performance claim in a diff rather than hunt for new ones, skip the
discovery steps and use the two checker tools directly:

- `validate_perf_claims.py <diff_file>` - EXTRACTS the "Nx faster / N% faster / twice as
  fast" style claim phrases from the diff's ADDED lines and prints each with its `path:line`.
  It does no profiling and reaches no verdict: YOU check each against a real profiled run and
  report the unproven or contradicted ones.
- `compare_performance.py` - stash the working changes (untracked files too), time the test
  suite on the previous commit, restore the branch and the changes, time again, and report
  the measured delta as before/after evidence. Exit 2 means there is no valid comparison: a
  suite run failed, there is no previous commit, or a git step failed; never quote its
  numbers then. If stderr says the repository was NOT restored, run the git commands it prints
  first: they name the branch to check out and the sha of the stash holding your uncommitted
  changes. When the BEFORE run created a file where the stash puts back one of your untracked
  files, it re-applies nothing and names that file: move it out of the way before those
  commands. If it says PART of your changes was re-applied, it prints no command to run: the
  stash still holds all of them, and the rest is restored by hand.

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

Respect previously reviewed items by DEFAULT, but they are not frozen: RE-ASSESS a declined finding against current ground truth (an already-implemented fix stays done - never re-suggest it). Do not casually re-raise a declined finding; re-open one ONLY when concrete ground truth shows its premise no longer holds (the data it was sized against grew, the code moved onto a hot path, it now blows up memory/time). Then surface it as a propose-first "Reconsider" finding (Step 6) - never silently skip a declined item ground truth now contradicts, and never silently change one. This "does the premise still hold?" judgment is bounded work a weak/literal session model gets wrong: run it on a **`sonnet`** subagent (pin the tier per dispatch; the main agent cannot self-switch its model - see "The session model is fixed" in `bitranox:process-agents-subagent-driven-development`), or inline when already on a capable model.

### Step 2: Setup

Run the portable bootstrap. `setup_env.py` is stdlib-only and cross-platform: it
walks up from the current directory for a `pyproject.toml` (clear error + non-zero
exit if none), creates a scratch temp dir (via `tempfile.mkdtemp`, honouring
TMPDIR/TEMP/TMP - never a hardcoded `/tmp`) with `cache/ logs/ perf/` subdirs,
validates the interpreter it records (see `python` below) is Python 3.10+ by running it
once, and writes `session.json` into that scratch dir holding every path later steps need.

`SKILL_DIR` is this skill's own directory - the one holding this `SKILL.md` and
`setup_env.py` (`skills/coding-python-performance-review/` inside the plugin). You
must set it YOURSELF before the bootstrap: `session.json` is written BY
`setup_env.py`, so the `skill_dir` field read back in the next block does not exist
yet and cannot be used to launch the script that creates it.
`bx_py` runs it first, with the first of `python3`, `python`, `py -3` that actually starts - a
bare `python` is missing on most Linux boxes and on macOS, and Windows' `python3` can be the
Store stub, which exists but does not run. That is the user's own interpreter (an activated
venv or conda env included), which is what a project WITHOUT a `.venv/` or `venv/` gets
recorded. `uv run` is only the fallback for a machine where that fails (no Python 3.10+): it
fetches an interpreter, but the one it records is uv's throwaway script env. Run it once,
capturing the printed session-file path. The script prints
`Session file: <path>` on its first line, echoes the full JSON, and exits non-zero
with a clear stderr message if there is no `pyproject.toml` or the interpreter is
too old. `session.json` replaces the old `/tmp/bx-perf-session` and
`/tmp/bx-perf-skill-dir` side-channel files; it contains `tmpdir`, `project_root`,
`skill_dir`, `python`, and `status`. `python` is the PROJECT's interpreter (its `.venv/` or
`venv/`), not the one running `setup_env.py`. With no project venv it falls back to the running
interpreter and says so on stderr; then check `python` before profiling - above all when the
`uv run` fallback ran, whose throwaway env has neither the project nor pytest. The version gate judges that recorded
interpreter, because every later step runs it: a venv python that cannot start, or one older than
3.10, exits 2 naming its path, and no scratch dir is created.

```bash
# Set SKILL_DIR to this skill's own directory (the one holding setup_env.py) - substitute
# the real absolute path. Nothing else can supply it yet: session.json does not exist until
# the next line runs.
SKILL_DIR="/absolute/path/to/skills/coding-python-performance-review"

# Run the bootstrap once; capture the path to session.json from its output.
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
BX_PERF_OUT="$(bx_py "$SKILL_DIR/setup_env.py" || uv run "$SKILL_DIR/setup_env.py")" || {
    echo "Setup failed - aborting performance analysis"; exit 1
}
echo "$BX_PERF_OUT"
BX_PERF_SESSION="$(printf '%s\n' "$BX_PERF_OUT" | sed -n 's/^Session file: //p')"
```

**Interpreter rule.** From here on every step runs the RECORDED interpreter, `"$PYTHON_CMD"`,
quoted because its path may hold a space. `bx_py` does only the two jobs that come before that
interpreter is known: launching `setup_env.py` and reading `session.json` back. Each block below
runs in a fresh shell, so it re-defines both helpers, and exits 2 when it cannot read
`session.json` rather than writing its output under an empty scratch path.

```bash
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
PYTHON_CMD="$(read_field python)" && BX_PERF_TMPDIR="$(read_field tmpdir)" \
    && SKILL_DIR="$(read_field skill_dir)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }
```

### Step 3: Validate Prerequisites and Profile

```bash
# Re-load paths from session.json (set BX_PERF_SESSION in Step 2). All stdlib, no jq.
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)" && SKILL_DIR="$(read_field skill_dir)" \
    && PYTHON_CMD="$(read_field python)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }

echo "Validating prerequisites..."
# Ensure pytest is importable. Do NOT use `pip install --user` (it misbehaves in
# uv-managed / Python 3.13+ envs). Only install if genuinely missing, preferring uv.
if ! "$PYTHON_CMD" -c "import pytest" 2>/dev/null; then
    echo "pytest not found - installing..."
    uv pip install pytest 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_install.txt" \
        || "$PYTHON_CMD" -m pip install pytest 2>&1 | tee -a "$BX_PERF_TMPDIR/cache/pytest_install.txt" \
        || true
fi

# Detect the test directory portably: prefer pyproject [tool.pytest.ini_options]
# testpaths, else the first existing of tests/ test/, else let pytest discover.
TESTDIR="$("$PYTHON_CMD" - <<'PY'
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
    "$PYTHON_CMD" -m cProfile -o "$BX_PERF_TMPDIR/perf/test_profile.prof" -m pytest ${TESTDIR:+"$TESTDIR"} -v 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_profiling.txt" || true
fi

# Profile local-only tests (if marker exists)
echo "Profiling local_only tests..."
"$PYTHON_CMD" -m cProfile -o "$BX_PERF_TMPDIR/perf/test_local_only.prof" -m pytest ${TESTDIR:+"$TESTDIR"} -v -m local_only 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_local_only_profiling.txt" || true

# Profile integration tests (if marker exists)
echo "Profiling integrationtest tests..."
"$PYTHON_CMD" -m cProfile -o "$BX_PERF_TMPDIR/perf/test_integration.prof" -m pytest ${TESTDIR:+"$TESTDIR"} -v -m integrationtest 2>&1 | tee "$BX_PERF_TMPDIR/cache/pytest_integration_profiling.txt" || true

echo "Prerequisites validated"
```

### Step 4: Run Analysis Pipeline

#### 4a: Identify Pure Function Candidates

Run `find_cache_candidates.py` from the skill directory against the project's Python files. A
function that returns a list, dict, set or ndarray it builds is never reported: `lru_cache`
would hand every caller that one object, so one caller's edit changes every later result.
Return a tuple or frozenset first if such a function should be cached.

```bash
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)" && SKILL_DIR="$(read_field skill_dir)" \
    && PYTHON_CMD="$(read_field python)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }

# Discover Python files into an ARRAY, so a path holding a space stays ONE argument.
# BX_PERF_FILES, when set, is the list to scan: one path per line.
python_files=()
if [ -n "${BX_PERF_FILES:-}" ]; then
    while IFS= read -r f; do [ -n "$f" ] && python_files+=("$f"); done <<< "$BX_PERF_FILES"
elif [ -d "src" ]; then
    while IFS= read -r -d '' f; do python_files+=("$f"); done < <(find src/ -name '*.py' -print0)
else
    while IFS= read -r -d '' f; do python_files+=("$f"); done \
        < <(find . -name '*.py' -not -path './.venv/*' -not -path './venv/*' -print0)
fi

if [ "${#python_files[@]}" -gt 0 ]; then
    "$PYTHON_CMD" "$SKILL_DIR/find_cache_candidates.py" "${python_files[@]}" > "$BX_PERF_TMPDIR/cache/cache_candidates.txt" 2>&1 || true
    echo "Cache candidates identified"
fi
```

The three AST finders (4a, 4b, 4f) exit 2 when any path was missing or could not be parsed;
each such file gets an `ERROR` line in the output file and was NOT scanned, so a "Found 0"
beside an `ERROR` line is not a clean result.

#### 4b: Find Uncompiled Regex Patterns

Run `find_uncompiled_regex.py` and scan for `re.match()`, `re.search()`, `re.findall()`, etc. called with string literal patterns instead of pre-compiled objects:

```bash
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)" && SKILL_DIR="$(read_field skill_dir)" \
    && PYTHON_CMD="$(read_field python)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }

# Discover Python files into an ARRAY, so a path holding a space stays ONE argument.
# BX_PERF_FILES, when set, is the list to scan: one path per line.
python_files=()
if [ -n "${BX_PERF_FILES:-}" ]; then
    while IFS= read -r f; do [ -n "$f" ] && python_files+=("$f"); done <<< "$BX_PERF_FILES"
elif [ -d "src" ]; then
    while IFS= read -r -d '' f; do python_files+=("$f"); done < <(find src/ -name '*.py' -print0)
else
    while IFS= read -r -d '' f; do python_files+=("$f"); done \
        < <(find . -name '*.py' -not -path './.venv/*' -not -path './venv/*' -print0)
fi

if [ "${#python_files[@]}" -gt 0 ]; then
    "$PYTHON_CMD" "$SKILL_DIR/find_uncompiled_regex.py" "${python_files[@]}" > "$BX_PERF_TMPDIR/cache/uncompiled_regex.txt" 2>&1 || true
    echo "Uncompiled regex scan complete"
fi
```

Every `re.match(r'...', ...)` inside a function body should become a module-level `_RE = re.compile(r'...')` with `_RE.match(...)` at the call site. This avoids recompilation on every call.

#### 4c: Profile to Find Hot Functions

Run `find_hotspots.py` from the skill directory and analyze profiling data:

```bash
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)" && SKILL_DIR="$(read_field skill_dir)" \
    && PYTHON_CMD="$(read_field python)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }

# Analyze hotspots from all available profile files
> "$BX_PERF_TMPDIR/cache/hotspots.txt"
for prof_file in "$BX_PERF_TMPDIR/perf/"*.prof; do
    if [ -f "$prof_file" ]; then
        echo "--- $(basename "$prof_file") ---" >> "$BX_PERF_TMPDIR/cache/hotspots.txt"
        "$PYTHON_CMD" "$SKILL_DIR/find_hotspots.py" "$prof_file" >> "$BX_PERF_TMPDIR/cache/hotspots.txt" 2>&1 || true
    fi
done
echo "Hot spots identified"
```

`find_hotspots.py` exits 2 when a profile cannot be read, and `2>&1 || true` puts its
`ERROR reading profile ...` line into `hotspots.txt` under that profile's `---` header. Such a
section is NOT a result: no hotspots there means the profile was never read, not that nothing
is hot.

#### 4d: Cross-Reference Candidates with Hot Spots

Run `prioritize_cache_candidates.py` from the skill directory:

```bash
# Re-load paths from session.json (see Step 2 for read_field / BX_PERF_SESSION).
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)" && SKILL_DIR="$(read_field skill_dir)" \
    && PYTHON_CMD="$(read_field python)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }

"$PYTHON_CMD" "$SKILL_DIR/prioritize_cache_candidates.py" "$BX_PERF_TMPDIR/cache/cache_candidates.txt" "$BX_PERF_TMPDIR/cache/hotspots.txt" > "$BX_PERF_TMPDIR/cache/priority_cache_candidates.txt" 2>&1 || true
echo "Priority candidates identified"
```

`prioritize_cache_candidates.py` exits 2 when either input cannot be read, and
`priority_cache_candidates.txt` then holds only its `ERROR reading input: ...` line: that is
NOT "no high-priority candidates". Also read the `ERROR` lines inside `cache_candidates.txt` and
`hotspots.txt` - a file or profile that was not scanned cannot match anything here either.

#### 4e: Audit Existing Caches

This is an instructions-only step (no script). Use the Grep tool to find existing cache decorators:

- Search pattern: `@lru_cache|@cache|@functools\.lru_cache|@functools\.cache`
- Exclude `.venv/`, `venv/`, `__pycache__/`

For each cached function found, read the function and evaluate:

1. Check profiling data from `hotspots.txt`  -  is the function called frequently (>100 calls)?
2. Read the function body  -  is it pure (no I/O, no side effects, deterministic)?
3. Check the function signature  -  are all args hashable (no mutable defaults leaking through)?
   And the return value: a cached function returning a list/dict/set/ndarray it builds hands
   every caller the same object (HARMFUL unless it returns a tuple/frozenset).
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
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)" && SKILL_DIR="$(read_field skill_dir)" \
    && PYTHON_CMD="$(read_field python)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }

# Discover Python files into an ARRAY, so a path holding a space stays ONE argument.
# BX_PERF_FILES, when set, is the list to scan: one path per line.
python_files=()
if [ -n "${BX_PERF_FILES:-}" ]; then
    while IFS= read -r f; do [ -n "$f" ] && python_files+=("$f"); done <<< "$BX_PERF_FILES"
elif [ -d "src" ]; then
    while IFS= read -r -d '' f; do python_files+=("$f"); done < <(find src/ -name '*.py' -print0)
else
    while IFS= read -r -d '' f; do python_files+=("$f"); done \
        < <(find . -name '*.py' -not -path './.venv/*' -not -path './venv/*' -print0)
fi

if [ "${#python_files[@]}" -gt 0 ]; then
    "$PYTHON_CMD" "$SKILL_DIR/find_unbounded_memory.py" "${python_files[@]}" > "$BX_PERF_TMPDIR/cache/memory_candidates.txt" 2>&1 || true
    echo "Unbounded-memory candidates identified"
fi
```

### Step 5: Merge, Classify, and Sort Findings

Parse the six output files from Step 4. Output format reference:

- `cache_candidates.txt`: `file:line - function()` + `Reason: ...`
- `uncompiled_regex.txt`: `file:line - re.func(pattern, ...)` + `Fix: ...`
- `hotspots.txt`: `file:line - function()` + `Calls: N, Cumtime: Xs`
- `priority_cache_candidates.txt`: `**file:line - function()**` + `Action: ...` (the emitter
  wraps this line in markdown bold; strip the `**` before lifting it into a finding)
- `existing_caches.txt`: `file:line - @decorator function_name()` + `Verdict: ...`
- `memory_candidates.txt`: `file:line - <obj>.read()/.fetchall()/...` + `Risk: ...`

Classify each finding by severity:

- **SEVERE**: Unbounded memory / unsafe input (source confirmed able to grow unbounded) OR uncompiled regex in a hot function (in both regex + hotspots) OR harmful existing cache
- **MEDIUM**: Priority cache candidate (confirmed by profiling) OR uncompiled regex in non-hot function OR ineffective existing cache
- **MINOR**: Cache candidate NOT confirmed by profiling

Re-assess accepted items from Step 1 against ground truth (see Step 1): RESPECT them by default (do not present), but reclassify one as a propose-first "Reconsider" finding when concrete ground truth shows its premise no longer holds. Sort findings SEVERE -> MEDIUM -> MINOR.

### Step 6: Present and Implement Findings

Present each finding **ONE AT A TIME** using this format:

```
## Issue N: [Short Title]
**Severity**: SEVERE | MEDIUM | MINOR
**Type**: Uncompiled Regex | Cache Candidate | Ineffective Cache | Unbounded Memory | Unsafe Input
**File**: file:line
**Function**: function_name
**Call count**: N (from profiling, if available)
**Description**: what the issue is (for Ineffective Cache: include the verdict reason  -  actual call count, cumtime, impurity details, or why the cache provides no benefit)
**Suggested fix**: specific code change
```

**A re-opened accepted item uses this variant** (propose-first): `## Reconsider accepted item N: [Title]` / Severity / File / **Originally accepted because** / **What changed (ground truth)** / **Proposal** (re-affirm as-is, or a specific change - the user's call).

After presenting findings, emit a **Still-accepted summary**: the accepted items you RESPECTED this run, each with a one-line "still holds" note.

Ask: "Implement this fix? Or skip? If skipping, what's the reason?"

Wait for the user's response before proceeding to the next finding.

**On accept  -  Uncompiled Regex:**
1. Add `_RE_NAME = re.compile(r'...')` at module level (after imports)
2. Replace `re.func(r'...', text)` -> `_RE_NAME.func(text)` at the call site
3. Run tests, show diff

**On accept  -  Cache Candidate:**
1. **Measure first - this is what "never cache without evidence" means in practice.** Copy
   `profile_with_cache_template.py` (this skill's own directory) to
   `$BX_PERF_TMPDIR/cache/profile_cache_<function>.py`, set its `MODULE_NAME` and
   `FUNCTION_NAME` to the candidate, and run it with `$PYTHON_CMD` from the project root. After
   an untimed warm-up run it times the suite `REPEATS` (default 5) times without and 5 times
   with a fresh cache, interleaved, and prints the hit rate, the median improvement, and a
   RECOMMEND/REJECT verdict: it recommends only when the hit rate is >20%, the median
   improvement is >5%, AND every cached run beat every uncached run - otherwise REJECT as
   run-to-run noise (raise `REPEATS` for a noisy suite).
2. **On REJECT: do not add the cache.** Report the measured numbers and move on - a measured
   rejection is a successful finding, not a failure. **On ABORT (exit 2)** a suite run failed,
   with or without the cache: there is no measurement, so do not add the cache; if only the
   cached run failed, the cache changes behaviour - report that instead.
3. On RECOMMEND: add `from functools import lru_cache` if missing
4. Add `@lru_cache` decorator above function
5. If mutable args (list/dict), convert to tuples or use wrapper
6. Run tests, show diff, and quote the measured hit rate and improvement as the evidence

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
bx_py() { local c; for c in python3 python "py -3"; do $c -c "" >/dev/null 2>&1 && { $c "$@"; return; }; done
    echo "no python3, python or py -3 starts on this machine" >&2; return 127; }
read_field() { bx_py -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$BX_PERF_SESSION" "$1"; }
BX_PERF_TMPDIR="$(read_field tmpdir)" && PYTHON_CMD="$(read_field python)" || { echo "cannot read session file '$BX_PERF_SESSION'" >&2; exit 2; }

# Detect the test directory portably (same logic as Step 3): prefer pyproject
# testpaths, else first existing of tests/ test/, else let pytest discover.
TESTDIR="$("$PYTHON_CMD" - <<'PY'
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

# Run full test suite.
# PIPESTATUS[0] is load-bearing: after a pipe, $? is tee's status (tee virtually always
# succeeds), so reading $? here would report SUCCESS over a failing suite.
if [ -f "Makefile" ] && grep -q '^test' Makefile; then
    make test 2>&1 | tee "$BX_PERF_TMPDIR/cache/final_test_run.txt"
    TEST_EXIT=${PIPESTATUS[0]}
else
    "$PYTHON_CMD" -m pytest ${TESTDIR:+"$TESTDIR"} -v 2>&1 | tee "$BX_PERF_TMPDIR/cache/final_test_run.txt"
    TEST_EXIT=${PIPESTATUS[0]}
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

| Mistake                                                 | Fix                                                      |
|---------------------------------------------------------|----------------------------------------------------------|
| Dump all issues at once                                 | Present ONE at a time, wait for response                 |
| Re-raise an accepted item with no new evidence          | Respect silently; re-open only on a ground-truth trigger |
| Vague suggestions ("consider caching")                  | Show exact `@lru_cache` or `re.compile()` change         |
| Skip saving declined items                              | ALWAYS append to project instructions                    |
| Not running tests after fixes                           | Run tests after EVERY implementation                     |
| Caching impure functions                                | Never cache time/random/I/O/state-modifying              |
| Caching with mutable args                               | Convert list/dict to tuples; lru_cache needs hashable    |
| Caching a function that returns a new list/dict/set     | Return a tuple/frozenset; callers share the cached value |
| Silently skip an accepted item ground truth contradicts | Re-open as a propose-first "Reconsider" finding          |
| MINOR before SEVERE                                     | Sort: SEVERE -> MEDIUM -> MINOR                          |
| Ignoring existing ineffective caches                    | Audit existing `@lru_cache`/`@cache`, propose removal    |

## Key Behaviors

- **ALWAYS use REAL test suite**  -  never synthetic benchmarks
- **ALWAYS measure cache hit rate >20% AND improvement >5%**
- **NEVER cache without evidence**  -  show the profiling data
- **NEVER cache non-deterministic or side-effect functions**
- **ONE issue at a time**  -  never batch-present
- **ALWAYS audit existing caches**  -  verify they're still effective, propose removal if not
- **RESPECT prior decisions by default, but RE-ASSESS them**  -  re-open an accepted item (propose-first) only when ground truth shows its premise no longer holds; never silently skip one that ground truth now contradicts
- **ALWAYS flag unbounded memory**  -  big files / huge DB results / huge logfiles must stream, not load whole
- **ALWAYS flag unsafe input**  -  bound length, sanitize types/encoding (non-ASCII/emoji/CJK/binary), test it
