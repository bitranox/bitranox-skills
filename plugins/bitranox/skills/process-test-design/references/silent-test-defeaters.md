# Silent test defeaters: the detail

Read this when a test patches a name, parses tool output, asserts on an exception message (a
reworded one included) or on rendered output, loops until a condition holds or times how long that
takes, pins or clears an environment variable (one a library reads at import included), redirects or
deletes coverage data from a conftest, simulates a race between a check and an open, blocks a stub
so it can be signalled, plants a marker to prove a process ran, starts a fixture process that must
carry a given `/proc/<pid>/comm` name, asserts a descriptor was closed or a file is held only
through a memory map, binds a unix socket under `tmp_path`, builds a test double by subclassing a
`@dataclass`, configures a logger in a fixture, checks that an event from another thread wakes an
asyncio consumer, races a call on a helper thread, mints synthetic identifiers (ids that something
later truncates included), carries a skip or an exclusion, judges an artifact, compares against a
git ref, guards against cost, or tests environment isolation - or when you are about to claim a code
path is untested, or a mutation survives. Also when a unit suite's code can reach a real host or a
user-facing service, a test guards a secret it might print, a test spawns a nested test runner or
several writers to one file, asserts a real tool's verdict, relies on conftest fixtures reaching
`src/` doctests or on fixtures ported from a template, feeds a FIFO from a writer thread, times a
cost ratio or a growth ratio, or verifies a fix for a rare flake. Each entry names the trigger, the
mechanism that makes the test pass (or fail) for the wrong reason, and the fix.

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

### Timestamp BEFORE the probe that gets in, when the probe is the operation itself

In a unit test, a timeout is driven by injecting the clock (the "No timer in a test" rule in
SKILL.md). This entry covers the test that must measure REAL elapsed time, such as an integration
test or a benchmark, of how long until a resource is freed, when the only probe is the operation
itself (a send refused while another is in flight, a lock acquire that then does real work). The
probe that finally gets in runs a full operation of its own, so a timestamp taken after it adds
that whole duration (measured: every run read 1.0 s for a 0.5 s budget), the test's name ("freed
after one budget") becomes a false claim, and the lost slack fails it on a slow CI host. Take the
timestamp BEFORE each probe and report the one taken before the probe that succeeded:

```python
for _ in range(MAX_PROBES):
    t = time.monotonic()
    result = probe()
    if freed(result):
        break
else:
    raise AssertionError(f"not freed after {MAX_PROBES} probes")
elapsed = t - started
```

Prefer a probe that observes the state without doing the work, when one exists.

### A fake clock frozen during a read cannot see read latency

When code judges something by elapsed time around a slow read (a reset or liveness judge that
compares a deadline with the time a device or log read returned), a fake reader that returns
instantly while the injected clock stands still gives every read zero latency. Code that uses the
timestamp taken BEFORE the read then passes exactly like code that uses the one taken after it, and
a judge blind to read latency passes review. Make the reader fake advance the injected clock by a
latency and sample its result at the END of the read, where the real call returns, and give at
least one test a latency large enough to cross the judge's slack.

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

### A FIFO writer thread that is still alive may already be done

A fixture that feeds a FIFO from a writer thread must not read `writer.is_alive()` in teardown as
"nothing opened the FIFO, so release the writer by reading". The thread stays alive for a moment
after its write and close; a teardown that then opens the FIFO for reading BLOCKS FOREVER, because
no writer is left to open the other end. It is intermittent and hangs a CI job to its job timeout,
and only a faulthandler stack naming the fixture teardown points at it. Join the writer first with
a short grace (teardown cleanup, not an assertion). Then release a writer still stuck in its
`open()` with `os.open(path, os.O_RDONLY | os.O_NONBLOCK)`, which never waits and unblocks the
writer's open; join it, then close the descriptor. RED it deterministically with a writer that
sleeps after its write and close, so the old teardown always meets the finished-but-alive window,
and run that teardown on a daemon thread joined with a plain `join()` under the runner's per-test
timeout, as in the entry above.

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

### A fixture process with a given comm name: rename a Python child with prctl

Code that recognises a process by its kernel command name (`/proc/<pid>/comm`: a live-session or
daemon check) needs a fixture whose comm is that name. `exec -a` changes argv[0], not comm, and
copying a binary under the wanted name works only where that binary is standalone: a multicall
build (uutils coreutils, busybox) picks its applet from argv[0] and exits at once (uutils prints
`coreutils: unknown program '<name>'`). Start a Python child that renames itself, with the cwd the
check under test inspects, and kill it in teardown:

```bash
python3 -c 'import ctypes, time; ctypes.CDLL(None).prctl(15, b"NAME", 0, 0, 0); time.sleep(30)'
```

15 is `PR_SET_NAME`. It is Linux only, and a name longer than 15 bytes is silently cut to 15.
Assert the fixture is alive (`os.kill(pid, 0)`, `kill -0`) and read its comm back before running
the check: a fixture that died at start makes the path under test pass or fail for the wrong
reason, and its one-line error is easy to miss in test output.

### Build a missing path under the test's temp dir

A path chosen as "obviously absent" is not absent everywhere: `/nonexistent` is the `nobody`
account's home on Debian and Ubuntu, mode 0700, so the error is a permission error on some
machines and a missing-file error on others. Use `tmp_path / "absent.json"`, absent by
construction on every platform; in a doctest use a relative, obviously fictional path. Assert the
error TYPE, not the operating system's message text.

A doctest that ECHOES a path has a second trap besides existence: `str(Path("/abs/probe"))` renders
`\abs\probe` on Windows, so the expected output fails every Windows cell while Linux and macOS
pass. In a doctest that prints a path, use a relative single-component name (`Path("probe-name")`)
or compare `.as_posix()`, never a POSIX-absolute literal.

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

### A test input computed from the mutated constant follows the mutation

A mutation of a constant cannot turn a test RED when the test's INPUT is derived from that same
constant: the input moves with it. `step_back = WALL_CLOCK_SLACK_S - 1` stays on the allowed side
of the slack whatever the slack is, so mutating the slack to 0 makes the step -1 and the test stays
green. Use a literal input and assert its relation to the constant as a separate precondition
(`step_back = 9.0`, then `assert step_back < WALL_CLOCK_SLACK_S`), so the mutation fails the
precondition or the behaviour and the run goes RED.

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

### Vary the part of a minted id that truncation keeps

Short forms are prefixes (a `[:8]` hash, a `--short` sha, a uuid prefix used as a file or directory
name, a log column), so a fixture minting zero-padded ids such as `f"{n:064x}"` produces values
that differ only where truncation throws them away: every one shares the first eight hex
characters. They collide as files or directories, and the failure surfaces inside the code under
test as an assertion that it cannot tell two records apart. Before minting, find where the id is
shortened and vary THAT part, for example `f"{n:02x}" * 32`, a full-length digest whose leading
bytes differ per `n`. When an identity test fails that way, check the fixture's ids in their
truncated form before reading the implementation.

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

### A dataclass double that redefines a field as a property fails at construction

Subclassing a `@dataclass` and redefining one of its fields as a `@property` (to return a value
computed from the test's setup) breaks the generated `__init__`: it assigns every field, the
assignment hits the read-only property, and construction raises `AttributeError` (on Python 3.14:
`property 'x' of 'Double' object has no setter`), whether or not the subclass is itself decorated.
The test goes red in its setup, before the code under test runs, so it passes the "did it go RED"
check while proving nothing about the behaviour. When the value is fixed at setup, use
`dataclasses.replace(real, total=value)`: a real instance, so `isinstance` and static typing at an
`Order`-typed parameter still hold; a proxy fails `isinstance(x, Order)` and a strict type check
where the code under test is typed `Order`. Only when the value must be computed on access, build
the double as a proxy: hold a real instance and forward everything else through `__getattr__`,
overriding only the attribute you need (`__getattr__` runs only for names the proxy does not
define, so the property wins):

```python
class OrderDouble:
    def __init__(self, real: Order, total: int) -> None:
        self._real = real
        self._total = total

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)

    @property
    def total(self) -> int:
        return self._total
```

For every new RED, read the failing line and require it to be the assertion the test was written
for: a RED raised in construction or setup is a RED for the wrong reason.

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

Match the VALIDATOR's own phrase for the rule under test, never a number or other piece of the
input. pydantic, like most validators, echoes the input in its message (`input_value=11`), so a
bound test that passes `offset=11` and matches `"11"` is satisfied by a refusal for a different
reason (an `extra="forbid"` model refusing the `offset` field the feature has not added yet), and
the arm is green before the feature exists. Match the rule's wording
(`match="less than or equal to 10"`) and run the arm against the pre-feature code, requiring RED.

### A substring assertion on a reworded message must fail on the OLD message

A short token can already sit inside a longer word of the old text: an assertion that a reworded
hint says "quoted" passes on an old message that said "unquoted", so the test cannot go red.
Assert a phrase only the new wording contains (several words, or a token anchored on word
boundaries), run the assertion against the pre-fix message, and require it to FAIL before you
trust it.

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

### pytest adds capture handlers to a logger a fixture made non-propagating

When a test's call phase starts, pytest's logging plugin adds its `LogCaptureHandler`s to every
logger whose `propagate` is False at that moment (measured on pytest 9.1.0, 9.1.1 and 9.2.0; 9.0.3
and 8.4.2 add none). A fixture runs in the setup phase, so a fixture that sets
`logger.propagate = False` hands the test a logger already carrying two capture handlers that
production never has. Code that asks which handlers would see a record then answers differently
than in production: a bridge that skips a logger with handlers, a fallback that fires only when
there are none (`logging.lastResort` writing to stderr), a handler-count assertion. Measured: a
warning on such a logger reached stderr when the test body set `propagate = False`, and did not
when a fixture set it. Configure the isolated logger inside the test body (a context manager that
restores `propagate` and the handlers in `finally`), or assert on `logger.handlers` explicitly so
the extras show in the failure. For "does this reach stderr at all", run the code in a subprocess
and read its stderr: in-process, pytest's root handlers catch every propagating record before
`lastResort` is consulted, so a warning production prints never reaches `capfd` (measured on 9.0.3
and 9.1.1 alike).

### `tests/conftest.py` fixtures never reach a `src/` doctest

A conftest's fixtures, autouse ones included, apply only to items collected at or below its own
directory. The doctests `--doctest-modules` collects from `src/` therefore get NONE of
`tests/conftest.py`, so its autouse isolation (environment redirects, config roots pointed under
a temp dir) silently skips every src doctest, which then runs against the machine's real
configuration while the suite's isolation looks complete. Fix shape:

- Move the autouse fixtures into a `conftest.py` at the rootdir, which reaches both trees.
- Set `testpaths = ["src", "tests"]`. Without it a bare `pytest --doctest-modules` also collects
  the root `conftest.py` as a module named `conftest`, and collection errors on the clash with
  `tests/conftest.py` ("import file mismatch").
- Move constants the tests imported from `tests/conftest.py` into a bare-name module under
  `tests/`, with `tests` on pytest's `pythonpath` and pyright's `extraPaths`.
- Add a pyright `executionEnvironments` entry rooted at `tests/`, so a test's
  `from conftest import ...` still resolves to `tests/conftest.py`, not the root one.

Check which fixtures each doctest really receives with a small collect-only plugin, run as
`PYTHONPATH=. pytest -p fixture_probe --collect-only -q --doctest-modules`
(`pytest --fixtures-per-test` crashes on a doctest item, which has no `.function`):

```python
# fixture_probe.py
def pytest_collection_finish(session):
    for item in session.items:
        if type(item).__name__ == "DoctestItem":
            print(item.nodeid, sorted(item.fixturenames))
```

An isolation fixture missing from a doctest's list is not applied to it. Check this whenever you
add an autouse or isolation fixture to a project that runs `--doctest-modules`.

### Port a template's autouse fixtures along with its tests

Tests copied from a template repository into a derived one lean on the template's autouse
fixtures without naming them, which is what autouse means. A ported test can pass locally and
fail in CI when the fixture it needed neutralised something only CI sets (a library's
import-time environment read, see "Pin the environment an output premise depends on"). Before
porting, list the template's autouse fixtures by name, compare them with every `conftest.py` in
the derived repo, and port each missing one or record why the derived repo does not need it:

```python
import ast
import sys


def autouse_fixtures(path: str) -> set[str]:
    tree = ast.parse(open(path, encoding="utf-8").read())
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for deco in node.decorator_list
        if isinstance(deco, ast.Call)
        and any(kw.arg == "autouse" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in deco.keywords)
    }


template, derived = sys.argv[1], sys.argv[2]  # the two conftest.py files
missing = sorted(autouse_fixtures(template) - autouse_fixtures(derived))
print("\n".join(missing) or "no autouse fixture missing")
sys.exit(1 if missing else 0)
```

## Cross-thread tests: wait on what the call itself does

### A cross-thread wake-up test awaits only the thing being woken

A test that checks an event emitted on another thread wakes an asyncio consumer (a task parked in
`queue.get()`, a future the thread resolves) exists to catch an emit that queues the work without
waking the loop: `queue.put_nowait(item)` called from a foreign thread instead of
`loop.call_soon_threadsafe(queue.put_nowait, item)`. That work runs as soon as anything ELSE wakes
the loop, so the test may await nothing but the woken thing. Awaiting the emitting thread through
`await asyncio.to_thread(thread.join)` completes a future on the loop when the thread exits; the
wake that delivers it also runs the stranded callback, and the test passes on the broken code.
Fire the emit from a `threading.Timer`, so it lands while the loop is asleep, await only the
consumer, and assert the elapsed time. The item alone proves nothing: the `wait_for` timeout's own
timer wakes the loop in the end, and the item arrives late but intact, with no `TimeoutError`.

```python
async def test_emit_from_another_thread_wakes_the_consumer():
    queue = asyncio.Queue()
    adapter = Adapter(queue, loop=asyncio.get_running_loop())
    threading.Timer(0.05, adapter.emit, args=("x",)).start()
    started = time.monotonic()
    item = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert item == "x"
    assert time.monotonic() - started < 0.5  # a missed wake-up arrives at ~1.0 s or the next poll
```

Measured with the non-thread-safe emit: this form took 1.001 s, the `to_thread(join)` form 0.001 s;
with `call_soon_threadsafe` both took the timer's 0.050 s. This is the one place the "No timer in a
test" rule in SKILL.md gives way, because the latency IS the property and nothing the code signals
tells "woken" from "woken later". The delay only gets the loop to sleep before the emit: starting a
plain thread right after the consumer parks passed on the broken code too, because the emit landed
before the loop went to sleep and its next pass delivered it. A slow runner can make the delay too
short and the test miss the defect, never fail correct code. Keep the bound far below the
consumer's fallback poll interval and far above the timer delay, and RED the test against the
non-thread-safe emit.

### A flag set before a call proves the thread started, not that the call ran

A test that races a call on a helper thread against a blocked worker (`stop()` while the worker
waits on a gate) often signals readiness from the helper before the call:
`started.set(); worker.stop()`. The main thread waits on `started`, releases the worker and asserts
on what `stop()` should have prevented, but the helper can be descheduled between the flag and the
call, and the worker then runs as if no stop came. The test passes wherever the helper wins that
race and fails on the scheduler that does not, such as a free-threaded build on a loaded CI runner.
Wait on an observable the CALL itself sets: an event set inside it, the state it changes
(`worker.stop_requested.wait()`), or a test hook the code exposes for that moment. RED the test by
inserting a `time.sleep()` between the flag and the call in a scratch copy: the flag form must
fail and the fixed form must not. Measured on a small worker: the flag form let it process both
items even without the inserted sleep; waiting on the stop request processed none, with and without
a 0.2 s sleep.

## Child processes, nested runners and shared files

### A nested test runner inherits the outer runner's environment

A test that starts a test runner of its own (pytest in a scratch project, to test a plugin, a
fixture or a parallel-coverage setup) hands the child the OUTER run's environment. Under
pytest-xdist that includes `PYTEST_XDIST_WORKER=gwN`, so a serial inner run identifies itself as
an xdist worker: the test passes run serially and fails in every `-n auto` run, with an assertion
such as `{'gw7'} != {'main'}` that blames the code. Build the child env without the outer
runner's variables (`PYTEST_XDIST_WORKER`, `PYTEST_XDIST_WORKER_COUNT`, `PYTEST_CURRENT_TEST`,
`PYTEST_ADDOPTS`, and whatever an outer autouse fixture set that the nested run is meant to
bypass), and identify the processes the nested run is about by an `os.getpid()` each records from
inside itself, never by a label it may have inherited. Run such a test under `-n 2` as well as
serially before trusting it.

### Concurrent appends to one shared file tear on Windows

Child processes (xdist workers, multiprocessing workers) that each APPEND records to one shared
log race on Windows only. POSIX `O_APPEND` puts every write at the end atomically; Windows
emulates append as seek-to-end then write, so two writers overwrite each other's lines (measured:
34 to 57 of 600 lines lost and 16 to 30 torn per trial on Windows, none on Linux). The symptom
lands in the reader, on the Windows cells only: an `IndexError` on an empty line, three records
read as two. Give each writer its own file (named by pid or worker id), written once, and merge in
the reader.

### Put the tool's own reason in an assertion on its verdict

A test that drives a real external tool (a resolver, a compiler, a linter) and asserts only its
boolean verdict prints `assert False` when it fails, because `capsys` or `capfd` swallowed what
the tool said. A failure that happens only in CI then cannot be diagnosed from the log and costs a
commit and a CI cycle just to see the reason. Carry the reason in the assertion message:
`assert ok, stream.getvalue()`, `assert proc.returncode == 0, proc.stderr`.

## Tests that must not reach the outside, or leak into it

### A unit suite that drives real hosts must be UNABLE to reach one

Faking the remote side per test (a stub on `PATH`, an injected runner) protects only the tests
that remember to do it. One that forgets runs the real `ssh` against a real host and does there
whatever the code does: stop, roll back or restart a machine, flush its neighbour table. It stays
unnoticed while it is harmless by luck, for example because a fake key path does not exist. Make
reaching a host impossible for the whole unit suite with an autouse fixture at the true external
edge, `subprocess.Popen`, which `run`, `call` and `check_output` all go through:

```python
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REMOTE = {"ssh", "scp", "sshpass", "rsync"}


class RealHostRefused(BaseException):
    """A BaseException, so an `except Exception` in the code under test cannot swallow it."""


def _words(args) -> list[str]:
    if isinstance(args, (str, bytes)):
        args = [args]
    words = []
    for arg in (os.fsdecode(a) for a in args):
        lex = shlex.shlex(arg, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        words.extend(lex)  # splits shell operators, and sees through timeout/env/nice and `bash -c`
    return words


def refuse_real_hosts(args, env, allowed: Path) -> None:
    path = os.pathsep.join(os.get_exec_path(env))  # the CHILD's PATH, not the test's
    for word in _words(args):
        if os.path.basename(word) not in REMOTE:
            continue
        found = shutil.which(word, path=path)
        if found and not Path(found).resolve().is_relative_to(allowed):
            raise RealHostRefused(f"{word!r} resolves to {found}, not a stub under {allowed}")


@pytest.fixture(autouse=True)
def no_real_hosts(monkeypatch, tmp_path_factory):
    allowed = tmp_path_factory.getbasetemp().resolve()
    real_popen = subprocess.Popen

    class GuardedPopen(real_popen):
        def __init__(self, args, *a, **kw):
            refuse_real_hosts(args, kw.get("env"), allowed)
            super().__init__(args, *a, **kw)

    monkeypatch.setattr(subprocess, "Popen", GuardedPopen)
```

The only remote program allowed is a stub the test wrote under its temp dir and put FIRST on the
child's `PATH`; a real `ssh` earlier on that `PATH` resolves first and is refused. It inspects
every word, so it errs towards refusing (`echo ssh` is refused too), the safe direction for this
guard. Prove it by deleting the `raise` and requiring the refusal tests RED.

To audit an existing suite before the guard lands, run it in a namespace with no route out
(`unshare -rn`, then `ip link set lo up` inside) with logging `ssh` and `scp` stubs first on
`PATH` that append `$PYTEST_CURRENT_TEST` and their argv to a file. A test's own `PATH` stub
SHADOWS the audit stub, so the audit undercounts: tests driving their own stubs never reach it,
and the Popen guard is what finds those.

### A self-skipping test must decide without touching the resource

A test that skips when an external resource is unavailable (a keyring, a desktop session bus, a
device) must make that decision WITHOUT touching it. One that builds the real client on the
inherited session bus and skips only after the first call fails has already reached the service
on every default run: a secret-service keyring test that attempted an unlock before skipping
activated the keyring daemon and popped a password dialog on the user's desktop at every gate run,
while its skip looked like safe handling. Probe without side effects: make the real arm opt-in
through an environment variable that names it, and give it a private resource
(`dbus-run-session` around the run, with `HOME` and the `XDG_*` directories under the temp dir,
since a private bus alone still writes the real keyring files). Then guard the default run in
conftest so no test can reach a user-facing service at all: point `DBUS_SESSION_BUS_ADDRESS` at
an address where nothing listens (`unix:path=<tmp>/no-bus`) rather than only deleting it, because
with it unset some clients autolaunch or discover a session bus of their own.

### A secrets or privacy gate test can leak what it guards

pytest's failure output prints what a failing test compared: assertion rewriting shows both sides
of `assert token not in text`, `-vv` prints full diffs, and `--tb=long` with `-l`
(`--showlocals`) prints the test's locals. A test that guards against a private token reaching
logs or CI output therefore publishes that token into the CI log the moment it fails. Keep the
secret out of everything the failure prints: do the scan in a helper that returns only a count
and redacted positions, never bind the scanned text in the test's own frame, and assert on the
helper's result (`hits = token_offsets(read_output())`,
`assert not hits, f"{len(hits)} token(s) at offsets {hits}"`). Then test the leak paths
themselves: plant a known FAKE token so the test fails, run it with `--tb=long -vv -l`, and assert
the captured output does not contain that token.

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

### Assert a same-machine ratio, never an absolute wall-clock budget

A performance regression test with an ABSOLUTE budget ("processes 32 MiB in under 0.5 s") fails
a correct implementation on a busy shared runner (measured: 0.507 s on one macOS cell), and a
rerun only hides it. Time the code against a baseline run on the same machine over the same data
(best of three, such as one plain `bytes.replace` pass over the same buffer) and assert the RATIO.
Put the limit between the MEASURED ratios of the correct code and of the regression the test
guards, measured on every interpreter the project supports (measured: correct at most 1.01x, a
per-byte loop at least 10.7x, limit 3), and prove RED by swapping the regression in. Do not take
the regression's cost from a comment or docstring: one claimed about 100x and measured 11x, so a
limit derived from the claim would have kept the thin margin.

### A growth-ratio check: user CPU time, equal windows, fresh pages

A check that compares the time at n with the time at k*n (linear, not quadratic) needs three
things, or it flakes just above its ceiling and each "widen the repeats" fix only moves the flake:

1. Read USER CPU time (`os.times().user`), not `time.thread_time()` or `time.process_time()`.
   Those count kernel time too, including page faults, and the k*n arm allocates above the
   allocator's mmap threshold, so it faults in fresh pages on every scan while the n arm reuses
   its buffers. A linear scan then reads super-linear, and a "cache step" seen through
   `thread_time` is mostly this (measured: the large arm spent 33-35% of its time in the kernel,
   the small one 0%; the thread-time ratio read 24-27x where user time read 15-18x).
2. Give both arms EQUAL windows before taking the minimum of N: time the n arm as k back-to-back
   scans and divide by k. A short pass can fall wholly inside a fast moment of the runner, while a
   long one only averages over it.
3. A test that must CAUSE page faults takes a fresh anonymous `mmap` per round: glibc hands a
   freed large buffer straight back, already faulted in.

RED each with a virtual-clock test: a fast window placed inside the first short pass (for 2), and
a simulated load keyed to work done rather than to the scan count, since a cost that raises its own
load runs away.

### Verify a rare-flake fix with an amplified, interleaved A/B

Green CI after a fix for a rare flake is evidence only against the flake's base rate, so measure
that first: list the workflow's recent runs (about 25), search each failed run's log
(`gh run view <id> --log-failed`) for the test id, and count. At 1 failure in 26 runs, two green
runs follow with no fix at all about 93% of the time, and about 59 clean runs are needed for 90%
confidence. Instead:

1. Build two environments that differ ONLY in the fixed dependency: both from the lockfile, then
   pin the old version in arm A (`uv pip install --no-deps <pkg>==<old>`).
2. Amplify through the REAL test, not a probe (pytest-repeat `--count 50`, xdist at about twice
   the core count), alternating which arm runs first each round.
3. Require liveness: the old arm must reproduce the CI failure's own shape first. Zero failures in
   the new arm mean nothing until it has.

Measured on a platform-only stderr race: old arm 8 of 2800, new arm 0 of 2800 (P about 0.004), in
about 45 minutes on one 12-core machine, against an estimated two months of nightly CI for the
same confidence.

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
