# Silent test defeaters: the detail

Read this when a test patches a name, parses tool output, asserts on an exception message or on
rendered output, loops until a condition holds, pins or clears an environment variable (one a
library reads at import included), redirects or deletes coverage data from a conftest, simulates
a race between a check and an open, blocks a stub so it can be signalled, plants a marker to prove
a process ran, asserts a descriptor was closed or a file is held only through a memory map, binds
a unix socket under `tmp_path`, carries a skip or an exclusion, judges an artifact, compares
against a git ref, guards against cost, or tests environment isolation - or when you are about to
claim a code path is untested, or a mutation survives. Each entry names the trigger, the mechanism
that makes the test pass (or fail) for the wrong reason, and the fix.

## Determinism and environment

### Bound every loop in a test by something the subject does not control

First choice is no loop at all: block on an event the code under test signals, or plant one (the
"No timer in a test" rule in SKILL.md). This entry covers the loops that remain - a production
`while` loop driven by a fake, which IS the code under test, and a spin on cooperative tasks
(`while x not in started: await asyncio.sleep(0)`) where the code offers no event and none can be
planted. Unbounded, either HANGS the suite when a regression makes its exit condition unreachable:
no failing assertion, only a timeout that names no cause. Bound it by a COUNT, never a wall-clock
deadline (a deadline is the timer the SKILL.md rule forbids): give a spin a helper with a
predicate, a message and a tick ceiling; give a production loop an independent backstop (a hard
cap that never binds while the real guard works) and assert in the test that it never fired. Make the fake
advance every counter the real system advances (distinct ids, growing totals), or a
de-duplicating consumer freezes the loop for a reason unrelated to the change. Then mutate the
guard the loop depends on and require a fast, NAMED failure.

### Pin the environment an output premise depends on

When a test's premise is a property of its output (no escape bytes, no colour, no control
characters, a width), set the variables that decide it - `FORCE_COLOR`, `NO_COLOR`, `TERM`,
`COLORTERM`, `COLUMNS`, the locale - in the suite's own fixture (`monkeypatch.setenv` / `delenv`)
instead of inheriting them, and add a control asserting the premise holds (the output DOES contain
colour when the test is about stripping it). Inherited, the same test is a guard on one machine
and a wall of unrelated red on another.

A spawned child needs the same pinning. A child env built as `{**os.environ, "FORCE_COLOR": "1"}`
inherits the parent's `TERM`, and rich draws no colour under `TERM=dumb` or `TERM=unknown` even
with `FORCE_COLOR` set (any other `TERM`, or none, still gets colour), so a test asserting colour
passes or fails by the terminal it was launched from. Build the child env by removing every colour
variable (`NO_COLOR`, `FORCE_COLOR`, `COLORTERM`, `TERM`) and then setting the ones the test
wants, including an explicit `TERM` such as `xterm-256color`. Prove the fix by running the test
under a hostile parent environment (`TERM=dumb`, `NO_COLOR=1`) as well as a clean one.

**`monkeypatch.delenv(name, raising=False)` on an ABSENT variable records nothing to undo.**
pytest registers a restore only when the variable exists, so if the code under test then sets it
(a `.env` loader, `os.environ.setdefault`), the value outlives the test and fails later tests in
unrelated modules, depending on order. Write `monkeypatch.setenv(name, "x")` followed by
`monkeypatch.delenv(name)`: the `setenv` records the original absent state, so teardown restores
the variable to absent. Suspect this whenever an order-dependent failure involves environment
variables.

**A library that reads the environment at IMPORT ignores a per-test `delenv`.** pytest imports
the code under test at collection, under the launching environment, so a module-level value
computed from a variable is fixed before any fixture runs. The delenv list looks complete and
passes locally, where the variable is unset at process start, and fails only where it is set -
every GitHub runner exports `GITHUB_ACTIONS=true`. rich-click is such a library:
`rich_click.rich_click` computes `FORCE_TERMINAL` (from `FORCE_COLOR`, `PY_COLORS`,
`GITHUB_ACTIONS`) and `WIDTH` and `MAX_WIDTH` (from `TERMINAL_WIDTH`) as module globals, and every
help and usage-error render copies them, so on a runner that output comes out styled for a
terminal (coloured and wrapped) and tests reading its text fail in CI only. In the autouse
fixture, after the delenv loop, re-derive the globals through rich-click's own default functions:

```python
import rich_click.rich_click
from rich_click.rich_help_configuration import force_terminal_default, terminal_width_default

monkeypatch.setattr(rich_click.rich_click, "FORCE_TERMINAL", force_terminal_default())
monkeypatch.setattr(rich_click.rich_click, "WIDTH", terminal_width_default())
monkeypatch.setattr(rich_click.rich_click, "MAX_WIDTH", terminal_width_default())
```

Verify before pushing by exporting the variables BEFORE pytest starts
(`GITHUB_ACTIONS=true FORCE_COLOR=1 TERMINAL_WIDTH=60 pytest`); setting them inside a test reaches
nothing and proves nothing. After a rich-click upgrade, re-list the globals it computes at import
with `grep -n '_default()' rich_click/rich_click.py`. For any other library, grep its module
level for `os.environ` and `os.getenv` before trusting a per-test `delenv`.

### A check-then-open race: make `stat` answer for another file

Code that checks `path.stat()` (refusing anything but a regular file) and then opens the path is
not proven by a test that hands it a FIFO directly: the check refuses that FIFO whether it looks at
the path or at the open handle, so the test cannot tell the two apart. The race is the name
changing between the check and the open, so simulate that swap. Subclass the concrete Path type so
`stat()` answers for a real regular file while the name the code opens is a FIFO:

```python
class Swapped(type(fifo)):  # the concrete PosixPath: subclassing pathlib.Path fails before 3.12
    def stat(self, *, follow_symlinks=True):
        return real_file.stat(follow_symlinks=follow_symlinks)
```

On the unfixed code, opening the FIFO blocks waiting for a writer, so the RED arm is a hang. Run the
load in a daemon thread and wait with a plain `join()`, letting the runner's per-test timeout catch
the hang (a signal-based timeout such as pytest-timeout's default on POSIX interrupts the `join()`;
a `join(timeout=...)` is the deadline the "No timer in a test" rule forbids). In a `finally`,
release a reader still blocked by opening the FIFO's write end
(`os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)`, then close it), so the thread ends. Guard it with
`if thread.is_alive()` and catch `ENXIO`: with no reader waiting (the fixed code never blocks, or
the interrupted reader has not reached its open yet) that open raises `ENXIO`, which would error the
arm. Keep the direct FIFO test as well; the swap test is the one that fails on a path-based check.
The fix it forces: open non-blocking (`O_NONBLOCK`), `fstat` the HANDLE and refuse a non-regular
file, so the check and the use are about the same object.

### A blocking stub must `exec` its blocker

When a stub (a fake external program written as shell) must block so the test can signal the
process under test mid-call, end it with `exec sleep N`, not `sleep N`. Without `exec` the stub
shell forks the `sleep`. When the stub shell is killed - by the signal, or by the code under
test's own cleanup (`subprocess.run` kills its child on an exception) - the forked `sleep` survives
as an orphan holding the stdout/stderr pipe it inherited, and the test's `communicate()` waits for
EOF until the sleep ends: a RED that should fail at once takes the full N seconds on every case.
With `exec` the process that gets killed is the blocker itself. Whether a shell execs its last
command unasked varies (bash 5.3 does for a `-c` string, dash does not), so write `exec`.

Signal only once the stub has started, never after a fixed `time.sleep()`. Make the start an event
the test blocks on: a FIFO the test creates and the stub writes to before blocking
(`printf x > "$STARTED"; exec sleep 30`, while the test does `open(started).read()`). Then call
`communicate()` with no timeout and let the runner's per-test timeout catch a wedge. A
`touch MARKER` the test polls for is the poll-until-deadline loop the "No timer in a test" rule
forbids; the FIFO is the event planted in its place. This shape is POSIX: on Windows there is no
FIFO or shell `exec`, and a parent's `terminate()` is `TerminateProcess`.

### Build a missing path under the test's temp dir

A path chosen as "obviously absent" is not absent everywhere: `/nonexistent` is the `nobody`
account's home on Debian and Ubuntu, mode 0700, so the error is a permission error on some
machines and a missing-file error on others. Use `tmp_path / "absent.json"`, absent by
construction on every platform; in a doctest use a relative, obviously fictional path. Assert the
error TYPE, not the operating system's message text.

### Reproducing a flake against a UI framework's tick

A race against a timer reproduces by slowing that timer, not by starving the CPU. Textual, for
example, repaints every 1/`TEXTUAL_FPS` seconds (default 60) while `Pilot.pause()` waits only a
short idle sleep, so running the exact failing pytest node with `TEXTUAL_FPS=10` is the RED arm;
keep it as the RED for the fix.

## Skips, exclusions and mutations

### A skip's reason is prose nothing executes

The skip condition is code; the reason is not checked by anything, so a reason copied from a
neighbouring test keeps a platform cell dark while the real failure goes unseen. When you write a
skip or meet one, check that the mechanism its reason names (a subprocess, a binary, a filesystem
behaviour) occurs in THAT test at all. If it does not, find what really fails, then fix it or
rewrite the reason to name it - do not just delete the skip, which may be load-bearing.

### Make an exclusion assert its own premise

An exclusion in a guard ("nothing in this cell can change", "this code is never raised here") is
written with a reason that later expires unnoticed, and widening it is always the smaller diff.
Make the exclusion test its own premise (for "never raised here", assert the value is not
referenced in the source) so it fails when the premise expires and asks to be promoted into
coverage. When a fix starts producing an exempted value, grep the tests for exemptions naming it
and narrow them in the same change - the fix never touches the test file, so nothing else prompts
the re-read.

### A surviving mutation can be absorbed by the fixture

If every fixture that triggers the mutated condition also triggers another condition that yields
the same result, the mutation changes nothing and the test looks protective while it cannot tell
the code with and without the check apart. Add a case where only the mutated condition varies,
re-run the mutation, and require RED.

## Rendered output and fixtures

### An absence can be the column's doing

When asserting a payload is ABSENT from rendered output (a table, a TUI screen), a sanitiser that
strips control bytes keeps the letters, so a narrow column can clip the payload and the assertion
holds by layout. Render at a width that cannot clip, or assert on the model rather than the page,
and keep width claims in their own test. Prove it by lengthening the payload until the assertion
would have to fail if the column were the only reason it passed.

### Give a synthetic identifier the real one's width

A made-up address, serial, WWN or hostname wider than the real ones is clipped by a column sized
for the real width, so the arm fails on its own fixture and reads like a defect in the code. Copy
the shape from a real capture, keeping length and separators and changing only the characters;
where the width IS the subject, state it in the test and assert it.

## Python patch and import mechanics

### A patch reaches a reader only if the reader looks the name up at call time

Four bindings happen before the test runs, and each turns `monkeypatch.setattr` into a silent
no-op that still PASSES:

- `from config import X` copies the value into the importer at import time. Better than any patch,
  inject the value. Where you own the reader, read the qualified `config.X` at call time and
  remove the bare import, so a missed qualification fails as a `NameError` instead of reading the
  stale copy; where you do not, patch the copy at the CONSUMER (`setattr(consumer, "X", v)`).
- `def f(paths=CONST)` evaluates `CONST` when the `def` executes. Patching the module constant
  never reaches the default, so a test that substitutes "the search paths" keeps reading the real
  system file. Pass the constant explicitly at the call site (`f(paths=mod.CONST)`) or resolve it
  inside the body.
- A module SPLIT. A bare global inside a function resolves against the module the function is
  DEFINED in. Before splitting, run `grep -n 'monkeypatch.setattr' tests/` and list every patched
  name; keep each in the same file as its callers, or call through a module object
  (`mod.helper(...)`), which every importer shares.
- A composition container (a services object, a DI container) captures its collaborators when it
  is built. Patching the function's module attribute afterwards is never consulted. Build the
  container inside the test with the substitute passed in, or expose the collaborator as a
  parameter.

Prove the seam: break what the test claims to depend on (delete the file, empty the directory,
make the substitute raise) and require the test to FAIL. A patch-based test never seen red is not
evidence.

### Patching `pkg.mod.subprocess.run` patches every caller in the process

`pkg.mod.subprocess` IS the shared `subprocess` module, so `mock.patch("pkg.mod.subprocess.run")`
and `monkeypatch.setattr` on that dotted path set `run` for every module in the process until the
patch ends. A git helper, another module or a fixture that shells out during that test goes
through the fake, and the test then measures the fake's call log. Prefer injecting the runner. If
you must patch, patch a name the module owns (`from subprocess import run` in the module, then
patch `pkg.mod.run`), or make the fake dispatch on `argv[0]` and raise on any command it was not
written for.

### Import sibling test helpers by bare module name

In a `tests/` directory without `__init__.py`, write `from helpers import ...`, never
`from tests.helpers import ...`. `python -m pytest` puts the current directory on `sys.path`, so
`tests` imports as a namespace package and the suite passes locally; bare `pytest` (the usual CI
invocation) does not, and collection dies with `ModuleNotFoundError: No module named 'tests'`,
reddening every test in the run. Grep `from tests\.` before pushing tests someone else wrote; a CI
collection error naming `tests` is this, not a missing dependency.

### pytest names `tmp_path` after the test function

`tmp_path` is `.../pytest-<n>/<test_function_name><n>`, so every path the test prints, logs or
parses contains the test's own name. A test named `test_skipped_rows` that splits tool output on
`"skipped"` cuts inside a path, and the failure looks like a defect in the code under test. Keep
the split or match token out of the test function's name, and better, anchor on structure (a
header line, a JSON field, a line prefix) rather than a bare substring. When a parse in a test
misbehaves, print the raw output and look for your own identifiers in it before suspecting the
code.

The same long path breaks a unix socket. An `AF_UNIX` path is capped at `sizeof(sun_path)`, 108
bytes on Linux and 104 on macOS, and `tmp_path` plus a long test name passes that easily, so
`sock.bind(str(tmp_path / "daemon.sock"))` raises `OSError: AF_UNIX path too long` on one machine
and works on another, appearing and vanishing with renames and temp roots. Never catch that error
as a skip: the test then silently stops testing what it was written for. Change into the directory
and bind a short RELATIVE name (`monkeypatch.chdir(tmp_path); sock.bind("s")`): the kernel
resolves it against the cwd and only the relative string counts toward the limit.

### Harvest a `pytest.raises(match=...)` pattern per parametrized arm

Two inputs can be refused by two different layers (a grammar error, and a runtime limit below
it), with different messages. A pattern harvested from the first arm then fails the second, and
the failure reads like the code under test. Give every arm an impossible `match=` first and read
what pytest prints for each - reading the raising code gets it wrong when the refusal comes from a
lower layer - then parametrize the pattern alongside the input, or match only a substring every
arm shares.

### Prove "untested" with branch coverage, not by grepping the name

Run the one test module under branch coverage with the data file outside the tree, and quote the
Missing ranges:

```bash
python -m coverage run --branch --data-file=<tmp> -m pytest -p no:cacheprovider -q <test module>
python -m coverage report -m --data-file=<tmp>
```

Then grep the function name and read each hit: a test that does
`monkeypatch.setattr(mod, "fn", lambda *a: SENTINEL)` names the function without ever running it,
and a test can reach only its early return. With pytest-cov, `--cov=` must name the IMPORTABLE
module: a file loaded under an alias (a hyphenated script that a conftest registers in
`sys.modules`) prints `Module ... was never imported` and `No data was collected`, yet the run
still exits 0. Check the report has a `Stmts` count before quoting any range. `--cov=` also writes
`.coverage` into the tree.

### A conftest cannot choose where pytest-cov writes its data

pytest-cov builds its Coverage object, and resolves the data file, in its own `tryfirst`
`pytest_load_initial_conftests` hook, before any conftest is imported. A conftest that sets
`COVERAGE_FILE` (at import or in `pytest_configure`) therefore redirects nothing: the run writes
to the configured `data_file` (`.coverage` by default), and a docstring claiming the hook "runs
before pytest-cov sets up" is wrong. To isolate a run's coverage, set `COVERAGE_FILE` in the
environment of the process that starts pytest or `coverage run`. To see where a run really
writes, point the variable the hook uses (a `TMPDIR`, a session path) at an empty scratch
directory and look for the file there.

Never delete or rename a coverage data file (or its SQLite journal files) from a conftest. A
conftest runs in every session, including the ones that measure nothing, and pytest-cov already
erases the data file when a run starts and combines the parallel files beside it when a run ends,
so a purge whose redirect never took effect deletes another run's data: a `coverage run` followed
by a plain `pytest` of one file leaves `coverage report` saying "No data to report". Two runs
sharing one data file interfere this way even with no conftest at all, so give each concurrent
run its own `COVERAGE_FILE` from the launching environment.

## Leaked and held resources

### A lowest-free-descriptor check cannot see a leak behind a closed lower one

"Open a probe descriptor before and after, close it, compare the numbers" relies on the kernel
handing out the lowest free number. It misses the leak whenever the code under test also opens and
closes a LOWER descriptor on the way, which path-walking and socket code usually does: the code
opens the parent directory at N, the file at N+1, closes N, and the leaked N+1 sits above a probe
that still reads N before and after. Assert on the SPECIFIC descriptor instead: record the number
the open returned (wrap the real `os.open` in the test so it records and passes through) and assert
`os.fstat(fd)` raises `OSError` with `errno.EBADF` after the call; or compare the full set of
`/proc/self/fd` entries (Linux) or the open-handle count. Then delete the `close` in the source and
require the test RED before trusting it - a leak test whose only RED came from an unrelated assert
is coverage it is not.

### A plain `mmap` keeps a descriptor, so it cannot prove a maps-only holder

`mmap.mmap(f.fileno(), ...)` duplicates the descriptor and keeps the duplicate open for the life
of the map, so the file stays in `/proc/<pid>/fd` after `f` is closed. A test meant to show that a
holder check finds a file held ONLY through a memory map (the `/proc/<pid>/maps` branch) then
passes even with the maps scan broken, because the fd scan finds the duplicate. Open the map with
`mmap.mmap(..., trackfd=False)`, which keeps no descriptor, close the file, assert the fd table no
longer lists it, and only then assert the holder check still finds it. `trackfd` needs Python 3.13
or later; an older interpreter rejects it as an invalid keyword, so skip there with that reason.

## Gates and guards

### Produce and judge an artifact in one test

A gate split into one test that produces an artifact and another that judges it can pass
vacuously in either half: `-k`, a deleted partner, a marker or an environment variable (with
`NO_COLOR=1` a "no forbidden colour" check has no colour to search) leaves the judge with nothing
to judge. Do both in one test, and assert the artifact makes the question meaningful (at least one
colour, one row, a non-empty capture) before asserting what must be absent.

### A check diffing against a moving git ref goes inert

A check written as "what changed versus `origin/main`" sees an empty diff in CI on a push to that
branch (the ref IS the pushed commit), and in your own RED/GREEN script after you push - it reports
"nothing changed", indistinguishable from "nothing wrong". State the rule as an invariant of the
tree as it stands ("the version the manifest names has a changelog heading"); it holds on a push,
a pull request and a shallow clone, and needs no `fetch-depth: 0`. For a one-off RED/GREEN, pin RED
to an immutable sha (`git rev-parse <commit>^`), say in the script why it is pinned, and report a
passing RED arm as a failure of the instrument. Build both arms and require the control to fire.

### Calibrate a cost or complexity guard at the real entry point

Time the crafted arm and the control through the seam the input actually arrives at, not the hot
helper inside: the surrounding linear work lands in both arms and shrinks the ratio, so a ceiling
picked from the helper's own number passes against the same defect end to end. Record both
numbers in the test, assert the crafted arm reached the hot code (a fast run can be an early
return), and when the seam truncates or caps its input, lift that bound past the crafted size for
the test. Then RED the arm on the pre-fix code.

### An environment-isolation test must expect what only the right repository holds

To prove code ignores an inherited `GIT_DIR` (or another repo-scoping `GIT_*` variable), do not
expect a plain untracked file: through a foreign `GIT_DIR` git still takes the work tree from the
cwd, so `git ls-files --others` lists it and the arm passes with the scrub deleted. Expect
something only the right index or config holds - a file force-added (`git add -f`) under an
ignored path, a committed blob, a repo-local config value - then delete the scrub and require RED.

### A "did it run" marker the platform can silence

Python imports exactly one `sitecustomize`, the first on `sys.path`. Debian and Ubuntu system
interpreters ship their own in the stdlib directory (`/usr/lib/python3.X/sitecustomize.py`), and a
venv built from `/usr/bin/python3.X` searches that directory before its own site-packages. A
`sitecustomize.py` planted in the venv to record "the planted interpreter ran" therefore never
runs, and an arm asserting the marker is ABSENT (an elevated or isolated arm that must not start
that interpreter) passes whether or not the defect exists. A uv-managed or other non-distro
CPython has no such file, so the same test is green on a dev box. Signal execution with a `.pth`
file in the venv's site-packages whose `import` line writes the marker (processed unless the
interpreter runs with `-S`), or with a wrapper script in place of the interpreter that writes the
marker before it `exec`s the real one. A `usercustomize.py` is no alternative: a venv disables the
user site, so it never runs there. Keep a positive control arm that must see the marker, and run
that arm once on a distro system Python.
