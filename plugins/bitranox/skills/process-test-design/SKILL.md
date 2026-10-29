---
name: process-test-design
description: Use when writing, reviewing, or pruning tests in ANY language - deciding unit vs integration vs e2e, whether to mock/patch or use the real dependency, which edge/adversarial inputs to cover (unusual UTF, emoji, CJK, binary, wrong types, oversized), why a test is flaky or order-dependent, or whether a test earns its keep. Keywords - mock, monkeypatch, spy, stub, fake, fixture, e2e, integration test, flaky, order-dependent, sleep, adversarial input, low-value test, coverage, pytest, vitest, jest, go test, cargo test, bats. For the red-green discipline see process-test-driven-development; for what to validate at a boundary see coding-input-sanitization.
---

# process-test-design

## Overview

How to write tests that are worth having: real behavior over mocks, the edge inputs that actually
break code, deterministic and order-independent, and no low-value filler. This is the WHAT-to-write
companion to `bitranox:process-test-driven-development` (the red-green-refactor discipline and the
mock anti-patterns) - follow that for WHEN/order; this for test design and quality.

**Core principle: a test must be able to fail for a real, specific reason.** A test that cannot fail
(asserts nothing, restates the implementation, or exercises a mock) is negative value - it adds
maintenance and false confidence. Test observable behavior at a boundary, not internals.

**Every principle here is language-neutral; only the mechanics differ.** Examples name Python where
one is needed, but the rules apply to any language - the per-ecosystem commands, seams, and tier
conventions are in "Per-language mechanics" below. When your language is not listed, map it by role
(what is the injection seam, what marks a test tier, what shuffles order) rather than assuming the
rule does not apply.

## Prefer real over mocked; mock only at the true edge

- **Default to integration / e2e against the real dependency** (real DB, real broker, real HTTP via a
  local server or recorded fixtures). In-memory fakes accept arguments the real service rejects, so
  green unit tests can still ship a broken contract. Treat the integration/e2e run as the proof.
- **Avoid monkeypatching. Use dependency injection.** Pass the collaborator in (a port/protocol) and
  substitute a real-ish fake or the real thing in tests. Reach for `monkeypatch`/patch only at a true
  external edge you cannot inject (a third-party global, the clock - with the caveat below, the
  network) - never to reach into your own internals. Patching your own code is a design smell: make
  it injectable instead.
- **Fakes live behind the same interface as the real thing** (a `fake_*` implementation of the port),
  exercised by the same contract tests as the real adapter, so the fake cannot drift.
- **"Patch the network/clock" is the fallback, not the choice, when you own the caller.** If the code
  under test is yours, the collaborator IS injectable - inject it, even for a unit test, and keep the
  real call for the integration tier. Patching a global (`fetch`, the HTTP module, the clock) is
  correct only when nothing you own sits between the test and that global: third-party code you cannot
  change calls it, or the call is buried in a dependency. "It is an external edge" does not license
  patching a global you could have passed in.
- **Never patch the clock function itself: it is process-global, and the runtime's own timers read
  it.** In Python, `patch("time.monotonic", ...)` replaces it for the whole process, and so does
  `patch("pkg.mod.time.monotonic", ...)` - that path reaches the SAME function object through the
  module's `time` name. asyncio's `loop.time()` is `time.monotonic()`, so every `sleep`, `wait_for`
  and `call_later` freezes and the test hangs, often in teardown. The same holds in any runtime whose
  scheduler reads the clock you swap. Inject a clock; when the code is not yours, patch the
  CONSUMER's own name for it - a module-level `_now = time.monotonic` it calls (patch `pkg.mod._now`),
  or the module's `time` name replaced with a stub that keeps the rest of `time` - never the function
  on the time module.
- **Drive the interaction, not the handler.** For anything a user reaches through an interaction (a
  key binding, a route, a CLI argument, a permission check), the test presses the key, clicks the
  row or runs the command, and asserts on what renders or what the command prints. A direct call to
  the handler proves the handler works, never that a user can reach it: a binding that claims the
  framework's own focus key (in Textual, `tab` is `focus_next`; rebinding it with `priority=True`
  stops focus ever reaching a table) leaves a row-selection handler unreachable while a test that
  calls the handler directly stays green. Reserve direct calls for pure functions. When a test does
  bypass the interaction, say why in the test body; if the reason is "the interaction is awkward to
  drive", that awkwardness is usually the bug.
- See `bitranox:process-test-driven-development` -> `testing-anti-patterns.md` (testing the mock,
  test-only methods in production, incomplete mocks, integration-as-afterthought).

## Per-language mechanics

Same rules, different handles. The "self-mock tell" column is what to grep for when auditing a suite:
it is the idiom that reaches into the code under test instead of injecting at a seam.

| Language        | Inject the seam as                | Self-mock tell (the anti-pattern)                                | Real dependency for the e2e tier        | Order / shuffle                                                                                                                                                                                   |
|-----------------|-----------------------------------|------------------------------------------------------------------|-----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Python          | constructor arg typed `Protocol`  | `monkeypatch.setattr(MyClass, "_method")`                        | testcontainers, a local server, `respx` | `pytest -p randomly`                                                                                                                                                                              |
| TypeScript / JS | constructor arg or interface      | `vi.spyOn(obj, "privateMethod")`, `jest.mock` of your own module | `node:http` server, MSW, testcontainers | `vitest --sequence.shuffle`                                                                                                                                                                       |
| Go              | interface parameter               | package-level function var swapped in a test                     | `httptest.Server`, real DB in Docker    | `go test -shuffle=on`                                                                                                                                                                             |
| Rust            | generic param or `Box<dyn Trait>` | `#[cfg(test)]` branch inside production code                     | `wiremock`, a real DB behind a feature  | `cargo test -- -Z unstable-options --shuffle` (nightly only; `cargo nextest run` does NOT shuffle - it runs lexicographically, one process per test, and `RUST_TEST_SHUFFLE` is silently ignored) |
| Bash            | a command name/path variable      | redefining the function under test in the test                   | a stub binary earlier on `PATH`         | `bats` (isolate per file)                                                                                                                                                                         |

**A real external program with an interactive prompt (`sudo`, an askpass helper, an installer)
is tested through a stand-in on `PATH`, in any language, not by patching `subprocess` or your own
relaunch helper.** Put a small executable script (shebang, mode +x) in the test's temp dir that
writes its argv to a file and exits with the code the test picks, and prepend its directory to
`PATH` (pytest: `monkeypatch.setenv("PATH", f"{d}{os.pathsep}{os.environ['PATH']}")`). The real
subprocess call then runs with nothing patched, and the argv contract - the flags and their order -
stays under test: assert on the logged argv and on how each exit code is mapped. A patch of
`subprocess.run` or of the helper skips exactly that: the argv really built and how the real
call's result is read. A stand-in cannot model a terminal (pty allocation, a Ctrl+C delivered to
the process group at the prompt), so keep one real-terminal run for signal behaviour. On Windows,
`CreateProcess` searches the PARENT's `PATH` and appends only `.exe` to a bare name: when the code
passes its own `env=` to the child, or the stand-in is a `.cmd`, resolve the program to an
absolute path with `shutil.which(name, path=<that env's PATH>)`.

**A program that relaunches ITSELF through an argv it builds (a background mode, a re-exec, a
generated systemd unit) needs a test of that exact argv through the real entry point** (for click,
`CliRunner().invoke(cli, built_argv)`), not only the in-process or `--foreground` path. The argv
crosses the program's own argument validation (`click.Choice`, argparse `choices=`, a required
flag), which no other test reaches. It is a caller you wrote, so it feels covered, but a value the
parser rejects fails only in the deployed path, exits at parsing before any of your logging runs,
and leaves the foreground test green. Add that test whenever a value is added to anything the argv
carries, and find the sites by grepping for where the code builds an argv naming its own program.
Keep what an operator may type separate from what the code's own relaunch paths forward, with the
latter as the union of every value the code emits.

**Mark the tiers so a bare test run stays offline.** Every ecosystem needs a way to keep the
network/DB tests out of the default run; pick the project's and use it consistently: pytest markers
(`-m "not integration"`), a filename or directory convention (`*.e2e.test.ts`, `test/e2e/`), a
separate config or workspace project, Go build tags, Rust `#[ignore]`, a `bats` tag. State it in the
project's own docs so the split is discoverable - inventing a private convention per test file is
how the integration tier quietly stops running.

**A marker only skips when something acts on it - registering it is not wiring it.** In pytest,
listing a name under `[tool.pytest.ini_options] markers` silences the unknown-marker warning and
nothing more; the skip has to come from a `pytest_runtest_setup` hook in `conftest.py` that reads
`item.iter_markers()` and calls `pytest.skip()`. A marker that guards a CONDITION (a platform, a
capability, an available service) is the dangerous case, because a registered-but-unwired one reads
exactly like a guard and runs everywhere. Before you trust one, grep `conftest.py` for the marker
name; if only the config mentions it, it is documentation. Then prove the skip fires by forcing the
condition rather than assuming.

**A `skipif` condition runs at import, before any skip.** pytest evaluates the condition when the
module is imported, at collection, so `skipif(os.geteuid() != 0)` raises `AttributeError` on
Windows and the whole module fails collection, taking every test in it; the error names the module,
not the test, so it reads as a broken import. Build the condition from something that exists on
every platform (`sys.platform`, `shutil.which(tool) is None`), and short-circuit the platform-only
call behind it (`sys.platform == "win32" or os.geteuid() == 0`) or move the call into the test
body. Do not guard with `hasattr(os, "geteuid")`: it is import-safe, but pyright does not narrow on
it, so a `--pythonplatform Windows` check still reports `geteuid` as not a known attribute of
`os`, while the right side of a `sys.platform` test is unreachable there and passes. A
condition that touches an optional dependency is the same trap: import-guard it rather than call
into it.

**Gate on the capability the code needs, not on the platform or the package import.** The rule
above says what is safe to EVALUATE at import; this one says what to gate ON. Use `sys.platform`
when the API really is per-OS (`os.geteuid`). When the feature depends on how the interpreter was
BUILT, the OS is the wrong axis: `sqlite3.Connection.enable_load_extension` exists only in a
CPython built with loadable sqlite extensions, so code loading sqlite-vec, spatialite or sqlean
fails on any other build with
`AttributeError: 'sqlite3.Connection' object has no attribute 'enable_load_extension'`.
Observed example: the python.org macOS framework build (what
`actions/setup-python` has installed on macOS runners) lacks it, while Homebrew and uv-managed
interpreters have it, so the failure appears when a CI cell changes interpreter.
`importorskip("sqlite_vec")` does not cover it (the package imports fine), and a
`sys.platform == "darwin"` skip is wrong both ways: it skips a macOS interpreter that works and
runs on any other build without the feature. In the production code, probe
`hasattr(conn, "enable_load_extension")` before the call and raise an error that names the
interpreter as the cause; in the tests, skip on the same capability asked of the class,
`hasattr(sqlite3.Connection, "enable_load_extension")`, since a `skipif` is evaluated at import,
before any connection exists (a `hasattr` is fine here: pyright knows the method either way, so
there is no narrowing to lose). When such a cell turns red, size the damage from the job log
itself, not from a summary someone wrote of it: count every `FAILED` line, since a summary usually
names only the tests its author looked at.

Watch for two families that mean the same thing - one wired, one not. A repo that carries both
(`posix_only`/`windows_only` wired to a real skip, and `os_posix`/`os_windows` registered and inert)
hands you a coin flip. Fix that at the root by wiring the unwired family, not by renaming the
markers in the one test that failed: the rename fixes today's file and leaves the trap armed for the
next test someone writes.

**What decides the tier is the dependency, not the realism.** A test belongs in the marked tier when
it needs something the machine does not already provide - an external service, a shared DB, Docker,
credentials, the real network - or when it is slow enough to hurt the default run. A dependency you
start and stop inside the test process (an ephemeral loopback HTTP server, a temp-file DB) is real
enough to prove the contract while staying offline, deterministic and fast, so it belongs in the
DEFAULT run. "Uses the real implementation" and "must be marked and skipped" are different
questions; answer them separately.

## Injecting a callable as a seam: three traps a green suite cannot show

Injecting a stdlib callable so a test can substitute it is the right shape. Three things about it
fail silently.

**Annotate the attribute with YOUR contract, not the stdlib's.** A bare assignment makes pyright
strict infer the library function's exact signature, and an honest double is then rejected:

```python
self._sleep = time.sleep                              # infers (seconds: _SupportsFloatOrIndex, /) -> None
self._sleep: Callable[[float], None] = time.sleep     # infers YOUR contract
```

Under `typeCheckingMode: strict`, assigning a double declared `(_seconds: float) -> None` to the
first form is an error - the parameter is positional-only and `_SupportsFloatOrIndex` is not
assignable to `float`. The second form accepts it. The failure lands on the TEST, so it reads as a
bad double rather than as a missing annotation.

**A double must have the seam's SHAPE, or a fail-open caller goes inert.** A double written as
`*a, **k` that returns whatever the caller expects accepts calls the real seam rejects: a keyword
the seam does not take (`capture_output=` passed to a seam whose signature is
`(argv, *, stdin_text=None, timeout=30)`), or `.returncode` read off a result the seam returns as
an `(rc, stdout, stderr)` tuple. Against the real callable that call raises `TypeError`, and a
fail-open `except Exception: return False` turns the crash into "allowed", the same answer a
correct check gives. The guard then refuses nothing while every unit test passes, because the
suite never constructs the real callable; the tell is the unit tests and one real invocation
disagreeing. Green tests against a hand-written double are not enough to ship such a guard. After
wiring a new call through a seam:

- run it ONCE against the real callable and assert the observable outcome (the guard actually
  refuses an input that must be refused), not merely that it returns;
- build the double from the seam's signature rather than `*a, **k`, and assert on the arguments it
  received;
- add a test that fails when the seam's contract moves (check the call's keywords against
  `inspect.signature(seam).parameters`), and RED it by restoring the mismatched call.
- a hand-written copy of a dependency's TYPES has two axes: its CONSTANTS (the limits and
  thresholds it reports) and its SHAPE (the field and attribute names your code reads). A fidelity
  check that pins only the constants passes while the double still carries a field the real class
  has dropped, so every test stays green while each real call raises `AttributeError`. Prefer
  copying the real module (its small import closure) into the fixture, keeping a stand-in only for
  the part that touches live state, such as a write path. Where the double must stay hand-written,
  compare its field set to the real class's, not only its values, and give it `__slots__` so
  reading a dropped field raises instead of returning a default. RED that check by renaming one
  field in a scratch copy of the dependency and requiring the suite to fail: a fidelity check
  nobody has seen fail is a claim, not a guard.

**After adding a wait or retry to a shared path, read the test file's WALL CLOCK, not its pass
count.** Every pre-existing test that goes through that path now pays the real delay. One 30-second
settle took a file from 0.07s to 90.05s while staying fully green. A slow suite never fails; it
decays until someone stops running it. Inject the sleep or clock too, and watch the file's duration
in CI (`pytest --durations`, the runner's slow-test report) rather than asserting elapsed time inside
a test.

## Adversarial inputs at the boundary (the test side of sanitization)

For any function/endpoint at an application or facing-API boundary, test the input battery, not just
the happy path. (Validation rules: `bitranox:coding-input-sanitization`; full per-codepath matrix:
enumerate every variant/caller a path serves and cover each branch.)

| Axis           | Cover at least                                                                                       |
|----------------|------------------------------------------------------------------------------------------------------|
| Text / Unicode | empty, whitespace-only, very long; non-ASCII, accented, combining marks, RTL, zero-width, emoji, CJK |
| Bytes          | control chars, NUL byte, invalid UTF-8 / raw binary                                                  |
| Type           | wrong type (str where int, None, list where scalar), missing field, extra field                      |
| Numbers        | 0, -1, 1, max, off-by-one at every limit, overflow, NaN/inf where float                              |
| Size           | empty collection, one element, at the cap, over the cap (DoS bound)                                  |
| Structure      | malformed JSON, truncated payload, duplicate keys, deeply nested                                     |

Assert the SPECIFIC behavior (rejected with a typed error, normalized, or escaped) - not just "does
not crash".

**A file NAME that is invalid UTF-8 is refused by macOS.** Creating one (`b"bad\xff\xfe.txt"`)
works on Linux, but APFS rejects it with `EILSEQ`, so the macOS CI cell goes red. Windows never
reaches the filesystem: Python decodes a bytes path there as UTF-8 and raises `UnicodeDecodeError`,
so such a test is POSIX-only and needs its own Windows skip.
Create every such name through ONE shared helper that catches `OSError`, skips when
`err.errno == errno.EILSEQ` and re-raises anything else, and route every non-UTF-8-name test in the
suite through it; never skip on a broad `OSError`, which hides real failures on every platform.

**A test for an input bound must fail fast when run RED, not exhaust memory.** It runs at least
once against code without the bound (RED), and again whenever the bound regresses, and that code
reads its input whole: an endless generator drove one RED arm to 36 GB RSS in five minutes, and in
CI it would take the runner down rather than fail. Feed a generator that yields items for a while
and then raises a test-local error (`_ReadTooFarError("read more than 50 entries")`): the fixed
code stops before it, the unfixed code hits it in milliseconds and the failure names why. When the
point is the TYPE (an iterator where a list is expected), use a small `range(3)`, not
`range(10**9)`. Run any RED arm that may still allocate without limit under a memory cap and a
timeout (`ulimit -v 4000000` in KiB, plus `timeout`). For a LARGE cap (a walk capped at 1,000,000
records), make the cap an injectable keyword and test at a small cap such as 3, plus one test that
the default equals the shipped constant; feeding cap+1 real records takes minutes.

**How much is enough (the stopping rule).** Cover one case per BRANCH the code actually takes, not
one per input you can imagine. For each failure the code distinguishes - a different error type, a
different message, a different recovery - there is one test. Inputs the code handles identically get
one representative case between them. Applied to a thin HTTP wrapper: one non-2xx case if every
status is treated the same (two if 4xx and 5xx diverge), one malformed-body case, one
transport-failure case, and no more. When a caller only ever sees your declared error type, the test
that matters is the one asserting the raw underlying error was converted to it.

**The branch rule governs the axis table above.** An axis with no corresponding branch in the code
gets no test - if nothing bounds a number, an "at max / overflow" case asserts nothing you have
promised. But do not just drop it: a missing branch where the axis clearly applies (an unbounded
size or length reaching a real sink) is a CODE finding - report the absent validation rather than
writing a test that documents its absence.

**A file a library reads before your code is several inputs, not one.** For a shipped default
config or a bundled data file, missing, unreadable and corrupt (and empty, a directory or a FIFO
where the code can meet one) each take their own path through a library you do not own, so they
surface at different places with different exceptions and exit codes. Measured on one release of
a config library: a missing default was skipped and the run failed later with a bare not-found
error under the wrong-command-line exit code, an unreadable one escaped as a bare
`PermissionError`, and only a corrupt one was refused as a configuration error. An `except` written
around the first exception you reproduced therefore fixes one kind and leaves the rest. Before
writing the handler, probe each kind on its own through the real entry point, and require the same
refusal for all of them: one exit code and one message shape, the message naming which kind it
met. Each kind that surfaced differently is its own
branch under the stopping rule, so it keeps its own test arm, and a later fix for one cannot
silently leave another. Damage the shipped file with the technique in "Damaging the installed
package" below.

## Scrub a captured artifact fully before it becomes a fixture

A captured artifact (a packet capture, a protocol exchange, a log or config dump) committed as a
test fixture carries more than its headers. A scrub that only touches the header/summary fields
looks complete while the structured payload underneath - options, TLVs, nested records - still
carries site topology (internal hostnames, domain names, subnets, device identifiers, vendor/serial
data). This is general practice, not tied to one protocol: it applies to DHCP, DNS, LLDP, and SNMP
captures, and equally to log and config dumps - scrub every layer the format defines, not just the
fields visible in a summary view.

**Assert the shipped fixture's fields in a test**, not only once by eye before committing. A fixture
nobody asserts on can silently re-acquire unscrubbed content the next time it is regenerated (a
re-capture, a re-export): the eyeball check does not repeat, the assertion does. Parse the committed
fixture and assert the sanitized values, including the structured payload fields, so the scrub is
enforced by the suite rather than remembered by a person.

## Deterministic and order-independent

- **No dependence on test execution order.** No shared mutable module/global state between tests; each
  test sets up and tears down its own world (fixtures). A test must pass run alone and in any order
  (green with random ordering on and off). An environment variable the code under test SETS is
  such state: `monkeypatch.delenv(name, raising=False)` on an absent variable records nothing to
  undo, so call `monkeypatch.setenv(name, "x")` first, then `delenv(name)` (detail in
  `references/silent-test-defeaters.md`, "Pin the environment an output premise depends on").
- **Code the tests call in-process must not leave process-global state behind.** A script's
  `main()` that installs signal handlers, or changes `os.environ`, the cwd or `sys.stdout`, runs
  inside the test runner when a test calls it directly. Left installed by a bare
  `signal.signal(...)`, a SIGTERM, SIGHUP or SIGINT handler changes how the runner itself reacts
  for the rest of the session, and the leak surfaces far from its cause (an unrelated later test,
  a Ctrl-C behaving oddly). In the production code, install such state through a context manager
  that saves the previous value and restores it in `finally`, including a nested hold-off such as
  `SIG_IGN` for SIGINT while an undo runs. For signals, skip installing off the main thread, where
  `signal.signal` raises `ValueError`, and let the exception a handler raises propagate out of the
  context, so an entry point that maps it to exit 128 + the signal number still does. Pin the
  restore with a before/after test: compare `signal.getsignal()` for every signal involved (or the
  variable, the cwd) around an in-process call, on the success path AND the error or undo path; a
  mutation that drops the restore must turn it RED.
- **A test that sends a fatal signal to its own process installs a raising handler first.** To
  prove the code under test catches SIGTERM, SIGINT or SIGHUP (any signal whose default action
  ends the process), a test that calls `os.kill(os.getpid(), signal.SIGTERM)` first installs an
  outer handler that RAISES a test-local exception (`signal.signal(sig, raising_handler)`) and
  restores the previous handler in `finally`. The code under test saves and replaces that handler
  while it is active, so a correct run never reaches it. Without it, a regression that drops the
  handler under test lets the signal's default action kill the test runner itself: the suite dies
  mid-run with no report naming the broken test, it reads as an infrastructure crash, and every
  test after it goes unreported. RED-check by deleting the handler under test: the expected result
  is one failed test, not a dead runner. Such a test is POSIX-only: on Windows
  `os.kill(pid, signal.SIGTERM)` is TerminateProcess and no handler runs, so give it a Windows skip.
- **A fixture serving from a listening socket calls `shutdown()` before `close()`.** For a server
  thread on a fixed address and port, teardown is
  `with suppress(OSError): listener.shutdown(socket.SHUT_RDWR)`, then `listener.close()`, then a
  plain `join()` of the server thread (the runner's per-test timeout catches a wedge). On Linux,
  `close()` alone does not wake a thread blocked in `accept()`: the thread stays parked, the port
  stays bound, and the next fixture's `bind()` fails with `EADDRINUSE`. If that fixture answers a
  busy port with `pytest.skip(...)`, the next test SKIPS instead of failing. A skip looks benign in
  a summary line, so a RED that reads "1 failed, 1 skipped" passes for a RED, and later a GREEN
  that is half skips passes for a GREEN. Run every RED with `-rs` and require 0 skipped for the
  tests you just wrote: a skipped test has not gone RED.
- **No timer in a test: no `sleep`, no poll-until-deadline loop, no `*_timeout` wait.** A fixed
  `sleep(n)` is flaky or slow, and a deadline loop or `wait(timeout=5)` is the same bet against the
  machine's load with a longer fuse. Block on an event the code under test signals - a channel/queue
  receive, a thread `join`, a condition variable, an awaited future or promise. When the code offers
  none, plant one: a sender dropped when the thread exits, a completion callback or hook the test
  passes in. Let the runner's per-test timeout (pytest-timeout, nextest `terminate-after`, the
  framework's test timeout; configure one suite-wide if the project has none) catch a wedge instead
  of a deadline written into the test. Treat a sleep, deadline loop or timeout-bounded wait inside a
  test as a review defect. The one exception, a COUNT-bounded spin (a zero-duration yield such as
  `await asyncio.sleep(0)`, which yields rather than waits) or a fake-driven production loop where
  no event exists or can be planted, is in `references/silent-test-defeaters.md`. Code that has its own timeout is driven by injecting its clock, not by
  waiting it out. A PRECONDITION state the test needs at a moment (a task still in flight, a file
  not yet written) comes from an event the run emits too, never from making one delay outlast
  another: a slower runner loses that race and the arm goes red for a non-defect. When such an arm
  fails, check first that its precondition HELD (print the event order) before reading anything
  the system did as a defect, in a commit message or anywhere else: what a system does under an
  unmet precondition is not evidence about the property the arm tests.
- **Never a zero or near-zero deadline, timeout or age.** `deadline=0.0` checked with
  `monotonic() - started > 0.0` races the clock tick instead of testing the code. On Windows with
  Python 3.12 or older, `time.monotonic()` advances in steps of about 15.6 ms (3.13 and later use a
  1 microsecond clock there), so two reads inside one tick differ by exactly 0.0 and only the
  Windows cells for those versions go red, which reads like flakiness or a version bug. Set the
  clock state explicitly: keep a realistic deadline and move the start into the past by a wide
  margin (`started -= 600.0` against a 60 s deadline), or inject the clock, and assert that
  precondition held before reading what the code did. When one Windows cell reds on a timing
  assertion while its sibling cells pass, suspect clock resolution, which itself differs by Python
  version on Windows, before an interpreter bug.
- **Inject time and randomness.** No bare now-clock, RNG, or UUID call in code under test - pass a
  clock / seed so the test is reproducible. (`datetime.now()`/`random`/`uuid4` in Python;
  `Date.now()`/`Math.random()`/`crypto.randomUUID()` in JS, or `vi.useFakeTimers()` at the edge;
  `time.Now`/`rand` in Go; `Instant::now`/`rand` in Rust; `$RANDOM`/`date` in Bash.)
- **No unmarked network / filesystem / external resource.** Those belong in integration tests
  (marked, opt-in), not the unit suite. The unit suite runs offline and identically every time.
- A flaky test is a bug in the test or the code, never "just re-run it" - fix the determinism.

## Wait on whatever lands LAST

When a test waits for A and then asserts on B, read the PRODUCER's order. If B is written after
A, the wait is satisfied while B is still absent, and the test is a race that only a slow machine
loses - so it passes locally for months and fails on one CI cell. Wait on the last thing the
producer emits, or on a signal it writes only when finished, never on the first thing that
happens to be observable.

## Reproducing a flake: starve it, or slow the clock it races

A flake reproduces under the pressure that matches its MECHANISM, and the two mechanisms need
opposite apparatus. Repetition alone is the weakest option and is what most runs reach for first.

- **A race between tasks** reproduces under CPU STARVATION. Pin the suite to one cpu (read the
  allowed set from the process's own status rather than assuming cpu 0) and run N busy
  competitors on that cpu, interleaved with an unstarved arm. It has a working range: past
  roughly 2.3x competitors it also reports margin failures that are not defects, so a finding
  there needs checking against the unstarved arm before you believe it. Measured: 45 unstarved
  runs found nothing, while the starved arm found two real ordering defects on every run.
- **A race against a TIMER** does not reproduce that way, because contention reschedules tasks
  and the timer keeps its own time. Find the clock the race is against and slow THAT - a UI
  framework's update tick, an animation rate, a poll interval - which widens the window the test
  samples in. Measured: 16 busy competitors reproduced a UI flake 0 times in 400 runs, while
  dropping the framework's tick reproduced it in 10 of 80, and 0 of 80 after the fix.

Both arms must run through the REAL test entry point. A standalone probe that reconstructs the
setup can stub out the very path that fails, and then passes whatever the code does.

## Run in a clean, project-correct environment

**The rule in any language: run against the project's OWN pinned toolchain, resolved from a lockfile,
never an ambient or global one.** Two runs that resolve different dependency versions turn a real
defect into "works on my machine" and an environment flake into a phantom bug. Per ecosystem: commit
the lockfile and install from it, not from the loose ranges (`uv sync` / `npm ci` not `npm install` /
`go mod download` with a committed `go.sum` / `cargo build --locked`), and pin the runtime version
(`requires-python`, `.nvmrc` or `engines`, the `go` directive, `rust-toolchain.toml`). An
environment-shaped failure - a missing module you know is installed, a flood of phantom type errors,
audit findings for packages not in your tree - is a wrong-environment smell to verify before you
trust it as a code bug.

Python specifics, where the trap is most common:

- **Run tests in the project's OWN venv, never the IDE's.** An ambient `VIRTUAL_ENV` (PyCharm, or carried
  over from another project's shell) silently hijacks the interpreter, so the suite runs against the
  wrong env. Isolate it: `env -u VIRTUAL_ENV uv run pytest` (mechanism + the bmk variant:
  `bitranox:coding-python-uv` "stray VIRTUAL_ENV"). "Fresh" = the project venv, isolated - only recreate
  (`uv venv --clear && uv sync`) when debugging suspected env corruption.
- **A wrong-venv failure masquerades as a code failure.** `ModuleNotFoundError` for a dep you know is
  installed, a flood of phantom type-check errors, or pip-audit CVEs for packages not in your tree are a
  WRONG-VENV smell, not a real defect. Before trusting such a failure, verify the interpreter:
  `uv run python -c "import sys; print(sys.executable)"` should point at `./.venv`. (Evidence before
  conclusions - see `bitranox:process-review-verification-before-completion`.)
- **Keep `.venv` out of git.** The project venv is a per-machine build artifact - never commit it;
  gitignore it (and untrack it if it slipped in). Mechanics: `bitranox:compuse-git` "Don't track local
  build artifacts".

**A green `windows-latest` cell is WEAKER evidence than a real Windows machine.** CI is usually the
stricter environment; here it is the better-equipped one. GitHub's Windows runner has been observed
to carry Git for Windows' `usr/bin` on PATH, so `true`, `false`, `env`, `touch` and `sh` resolve
there. A plain Windows install has none of them, and neither, by default, does one with Git
installed (the binaries exist on disk, but `shutil.which("true")` returns `None`). A test that uses
them as throwaway child commands passes in CI and fails on the machines the code ships to, so the
green cell describes the runner, not your users. Spawn `sys.executable` with `-c` instead, which
exists wherever the suite runs: `[sys.executable, "-c", "raise SystemExit(1)"]` for a child that
exits 1. When triaging Windows failures, run the suite on a real Windows machine rather than
iterating against the CI log; where the two disagree, believe the real machine.

**A huge parametrize value breaks every Windows cell at setup.** Before each phase pytest writes
`<node id> (<phase>)` into the `PYTEST_CURRENT_TEST` environment variable, and an id it builds
from a str or bytes parameter is the whole value, escaped. Windows caps an environment entry
(`NAME=value`, counted in UTF-16 units) at 32767, so such a case errors at SETUP inside pytest's
own runner frames while Linux, macOS and the local gate pass; it reads like infrastructure, not
like a test defect. Search the (often huge) job log for this line rather than reading it:

```text
ValueError: the environment variable is longer than 32767 characters
```

Fix the case with a short explicit id (`pytest.param(value, id="too-many-pairs")`), then close the
shape once per suite in `conftest.py`, so it fails at collection on whichever machine runs first:

```python
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Windows counts "PYTEST_CURRENT_TEST=<node id> (teardown)" (the longest phase) in UTF-16 units
    room = 32767 - len("PYTEST_CURRENT_TEST=") - len(" (teardown)")
    too_long = [i.nodeid for i in items if len(i.nodeid.encode("utf-16-le")) // 2 > room]
    if too_long:
        named = [f"{nodeid[:120]}... ({len(nodeid)} chars)" for nodeid in too_long]
        raise pytest.UsageError(f"node ids too long for Windows, give them an id: {named}")
```

`pytest.UsageError` ends the run with exit 4 before any test runs. To list the longest ids:
`pytest --collect-only -q | awk '{print length($0)}' | sort -n | tail`.

## A permission-wall test on Windows: build the wall stat cannot see past

A test that needs a path the user cannot check (so `stat` raises `PermissionError`) is built with
`chmod` on POSIX. On Windows the obvious version - deny the user on the directory - does not
work, for two reasons that both leave the test passing for the wrong reason:

- **`os.stat` of a denied directory succeeds.** CPython falls back to reading the entry from the
  PARENT directory's listing, so `stat` raises only when the directory's read-attributes AND the
  parent's list-directory right are both denied. Deny only those two rights: a full-control deny
  also removes your own right to change the ACL back, so the wall cannot be taken down.
- **An elevated session can see through any ACL.** An admin token with `SeBackupPrivilege`
  enabled (an OpenSSH session typically has it enabled, not merely present - check `whoami /priv`)
  opens files with backup semantics and ignores every deny entry. Disable the backup and restore
  privileges for the wall's lifetime and restore their previous state after.

Inside the test, assert the wall holds (`stat` raises) BEFORE asserting the behaviour under test,
so a runner whose token or ACL handling differs fails loudly instead of passing vacuously. Build
the wall through the Win32 security API rather than `icacls` by account name, which fails when the
name does not map to a SID:

- Take the user's SID from the process token (`GetTokenInformation`, `TokenUser`).
- Per path, save the DACL (`GetNamedSecurityInfoW`), add ONE non-inheritable deny entry
  (`SetEntriesInAclW` with `DENY_ACCESS`; `FILE_READ_ATTRIBUTES` (0x80) on the directory,
  `FILE_LIST_DIRECTORY` (0x1) on a parent the test owns, such as a `tmp_path` subdirectory), and
  apply it (`SetNamedSecurityInfoW`).
- Disable the privileges with `AdjustTokenPrivileges` (attributes 0, keeping the previous state it
  returns). The token is process-wide, so the wall must not span tests running in parallel threads.
- Take it down in reverse: privileges first, then the parent's saved DACL, then the directory's.

## Damaging the installed package: run a copy, with an intact copy as control

When a defect exists only with a SHIPPED file missing, unreadable or corrupt (the code finds it by
its own location, such as a default config inside the package), do not damage the checkout or the
installed package (destructive, and racy across parallel runs), and do not monkeypatch the loader
(that proves nothing about the real path). `shutil.copytree` the package directory into `tmp_path`
with `ignore=shutil.ignore_patterns("__pycache__")`, damage the COPY, and run `python -m <pkg>` as
a real child process with `PYTHONPATH` set to the copy's PARENT directory and `cwd` inside
`tmp_path` (`-m` puts the cwd first on `sys.path`, so a run from the repo root can import the
checkout). Probe each kind of damage in its own arm, assert the damage holds before running (an
unreadable file is still readable to root), and assert each damaged arm's exit code AND message.

In the same module, run an INTACT copy through the same harness and require exit 0: without it, a
harness that fails for its own reasons reads exactly like the damage being refused. Exit 0 does
not show which copy the child imported, so also have the intact arm report `<pkg>.__file__` and
assert it lies under `tmp_path` - a child started with `-I` ignores `PYTHONPATH` and would import
the installed package instead.

## Prune low-value tests

Delete a test when it:
- asserts nothing (or only that no exception was raised, for logic that should assert a result),
- restates the implementation line-by-line (changes whenever the code changes, catches nothing),
- tests the language, framework, or a mock rather than your behavior,
- duplicates another test's coverage with no new branch.

Fewer, behavior-focused tests beat many brittle ones. Coverage percent is a smell detector, not a goal.

**A replacement test is unproven until it fails on what the deleted one covered.** This holds
whether you are pruning or swapping tests as a side effect of a rewrite or refactor: a green suite
after the swap says only that the new test passes, never that it reaches the old test's branch.
Before treating the behaviour as still covered, break the branch the deleted test guarded (say,
the `except` path an option turns on to print full error details) and require the new test to go
RED naming that case, then restore the code and require GREEN. If it stays green, the coverage was
lost silently and the replacement must be made to drive that path. Copy the file aside before
mutating and restore from the copy (see "Single-layer mutation" under Common mistakes).

**Never commit a test that asserts behavior the code does not have.** When docs promise something the
code never wired up (a documented cache nothing calls, a flag with no effect), the honest output is a
FINDING - the feature is missing or the doc is wrong - not a red test left in the suite. A permanently
failing test is a broken gate, and a skipped one is a comment that rots. Report the gap, and write the
test when the behavior lands.

## A gate that only ever passed has not been shown to gate

A regression/perf gate that compares each run ONLY against a committed baseline answers "did this
move", never "is this right". A cell already broken when the baseline was seeded passes forever, and
a slow bleed of sub-threshold regressions never trips it. Pair the relative check with an ABSOLUTE
sanity bound (or a sibling/reference cell measured in the SAME run), declare a known-bad cell with a
tracking id so it is reported rather than frozen in, and make a declared cell that RECOVERS fail too
so a stale waiver cannot re-hide a fix.

The same doubt applies to any gate: validate it against a KNOWN-BAD input once, so you have seen it
go red. Otherwise "green for months" is equally consistent with "it stopped gating months ago".

**An exemption or scope limit added to a guard, filter, or validator needs the same proof, run in
the untouched direction.** Add a test where the trigger is present but the exemption must NOT
apply, asserting the verdict stays unchanged - not only a test proving the exemption fires where it
should. Then keep the case the guard was built to catch as a permanent test, re-run after every
exemption added later: two narrow-looking exemptions added in the same change can each pass alone
and still add up to silencing the guard on its own motivating case.

Write those negative tests FIRST, then the positive ones. An exemption is where the safe direction
inverts: a wrong block is loud, because someone's correct input is refused and they complain, while
a wrong exemption is silent, because the guard just says nothing and that reads as the input being
fine. Test what the trigger is a PROXY for, not that it is present. For an exemption meant to let
two commits in different repositories through, keyed on a `cd` between them, ask "did the working
directory change", not "is there a `cd`" (both `cd`s in this command enter the same repository:
`cd /repo && git commit -F m.txt ; cd /repo && git commit --amend --no-edit`), and "are these
different repositories", not "are the path strings different" (`/repo` and `/repo/` are one).
Then prove each exemption test reaches the code it names: mutate that code in a scratch copy and
require the test to FAIL. A test input that an earlier guard clause already decides never reaches
the exemption, and stays green whatever the exemption does.

**A consistency test pays on the code it did not grow up with, so it enumerates every entry.** A
test that pins declarations to implementations (a hook registry against its handlers' docstrings,
a plugin manifest, a CLI command table) must iterate EVERY declared entry, never only the ones your
change touched. The change that adds the test is already consistent, because you wrote both sides
while looking at them; the drift sits in the older entries, and a stale registration fails
silently: it never fires, which looks exactly like a feature nobody used. Scoping the test to your
diff removes the one population where its defects live. Make it also assert how many entries it
read, so an entry its pattern cannot parse fails the test instead of dropping out of the
comparison. Expect the first run to fail on code you did not write and treat that as the test
working, not as scope creep: fix that defect in its own commit, so the new test and the old defect
stay separable.

**A test that enumerates the repository's files asks git which files the repo owns.** List them
with `git ls-files -z --cached --others --exclude-standard` and split on NUL: tracked files plus
untracked ones that are not ignored (plain `git ls-files` drops the new ones, and without `-z` a
non-ASCII path comes back quoted and opens nothing). Skip a listed path that is gone from disk (a
tracked file deleted but not yet staged), then apply the test's own path filter, such as
root-level only. Never glob the working tree and subtract a hand-kept
list of local-only files: that list is a second copy of `.gitignore`, so the next gitignored file
something writes into the tree (a state file, a scratch log) turns the local run red while a
fresh CI clone, which never has that file, stays green.

Nine mechanics worth stating because they silently defeat a test that looks right:

- **`from m import X` binds a COPY at import time.** `monkeypatch.setattr(m, "X", v)` mutates `m`'s
  namespace and never reaches the consumer's already-bound name, so the test runs against the
  original value and passes for the wrong reason. Best, inject - which is why this skill prefers a
  seam over patching in the first place; where you own the reader, read the qualified `m.X` at call
  time and drop the bare import; else patch at the CONSUMER (`setattr(consumer, "X")`). Default
  arguments, module splits and composition containers bind early the same way (reference below).
- **A standard-library wrapper can hold its OWN copy of the function you patch, on some
  interpreter versions only.** Python 3.10's `pathlib.Path.cwd()` calls `os.getcwd` through an
  accessor that bound it at import, so `monkeypatch.setattr(os, "getcwd", fake)` never reaches it
  there, while 3.11 and later read `os.getcwd` at call time and the same test is right. The test
  then runs the REAL lookup on the oldest cell only, and does whatever a real run does from that
  directory - it read the repository's own config file. Patch the name the code under test calls
  (`Path.cwd`), or better make the real lookup fail (chdir into a directory, then remove it: any
  POSIX `getcwd` then raises). Prove the patch reaches it on the OLDEST interpreter the project
  declares - undo the fix and require the test RED there, not only on the newest - and give the
  test a sandbox a missed patch would FAIL on, so a miss shows up as red instead of silently
  reading real files.
- **A correctness test cannot prove an INDEX is used.** Results rank correctly whether the store
  used the index or full-scanned. Assert the plan (`EXPLAIN` shows an index scan, `list_indices` is
  non-empty), or the check silently passes on an O(n) path.
- **Two files sharing a BASENAME collide, and the loser's tests exercise the winner.** Python
  resolves an import to the first match on `sys.path`, and pytest's default `prepend` mode prepends
  each test root as it collects, so with two same-named modules the one collected FIRST wins for the
  whole run. The other directory's tests then run against a file you never changed. Both suites stay
  green, so nothing announces it; the tell is a fix that reads as absent in the full run while
  passing in isolation, and the shadowed file's real coverage is zero. Ship the module once, or run
  `--import-mode=importlib`, which keys modules by path instead of basename.
- **A teardown on a doctest's LAST line does not run when an earlier line raises.** A
  `mock.patch(...).start()` closed only by a trailing `mock.patch.stopall()` leaks the patch into
  every test collected after it, and under `--doctest-modules` the doctest executes in the collected
  module's namespace, so the leak is global. The resulting failures land far away and look unrelated
  to the doctest. Prefer a real injectable seam over patching inside a doctest at all.
- **`--doctest-modules` never collects a doctest in a Click command's docstring.** The decorator
  replaces the function with a `click.Command`, which doctest's finder does not walk, so a false
  example rots while the suite reports every doctest passing; naming the file on the command line
  changes nothing. A passing count is no evidence, so run the examples in a test of your own: walk
  the root group and `cli.commands` by introspection, recursing into subgroups (an AST scan for
  `>>>` misses a command that has no example at all), run each `command.callback.__doc__` through
  `doctest.DocTestParser().get_doctest(doc, dict(vars(module)), name, module.__file__, 0)` and a
  `doctest.DocTestRunner`, and fail on any failed example. Also fail a command with no example, or
  one whose examples carry no expected output: an import-only example passes while proving nothing.
  Write each example against the root group with the context object it expects
  (`CliRunner().invoke(cli, ["hello"], obj=...)`); invoking the bare command skips the root's setup.
- **Testing discovery does not prove the scan uses it.** A helper that filters paths (skipping
  `.venv`, suffixed venvs, `node_modules`, `.git`) can be covered exclusion by exclusion while the
  command run afterwards re-walks the tree (`-Recurse`, `rglob`, a bare directory argument) and
  undoes every exclusion, so the discovered list only decides WHETHER the scan runs. The thorough
  discovery tests are what make the whole path look covered. Assert at the seam that actually runs:
  plant a file under `.venv` in the fixture and assert the argv or command string handed to the
  subprocess names exactly the filtered files, with no re-walk flag. A green CI stage is no
  evidence either: a job that builds its venv outside the checkout never has a vendored tree in
  range, so only a developer machine exercises the exclusion.
- **A fixture built to make code FAIL can run the success path instead.** Tolerant APIs absorb the
  "broken" input: `Path.rglob()` and `glob()` over a regular file or a missing path yield nothing
  rather than raising (Python 3.10 through 3.14), and a `dict.get` default, an `except OSError` two
  layers down, or an empty list meaning both "none found" and "never looked" do the same. The test
  then asserts nothing, and its RED ("DID NOT RAISE") reads as a missing fix when the fixture never
  produced the condition. Make the failure come from a collaborator injected at a real seam (the
  code's `run=` / `runner=` parameter; add one when the code has none) that raises by construction,
  not from an input you believe
  is malformed, and assert the condition happened (the collaborator was called) before reading the
  RED. Once the fix exists, RED it by mutating the fix back with `__pycache__` cleared. If the RED
  message is about the fixture rather than your case, the fixture is the bug.
- **A test that passes a non-default flag tests the path that already worked.** Supplying
  `by_alias=True`, `sort_keys=True`, `strict=True`, an explicit encoding or a timezone exercises
  exactly the option production omits, so a defect in the DEFAULT path stays invisible, and the
  explicit flag reads as thoroughness. For each keyword a test passes, add the case where the
  caller omits it. For serialization, assert on the bytes a DEFAULT dump produces and validate them
  against the shipped schema, not a hand-written expectation, and make sure the data reaches the
  branch at all (a round-trip fixture with no instance of the aliased field tests nothing). When a
  docstring claims a wire format, run the default path and check the claim.

Prove a codec/serializer swap by SEMANTIC equivalence - decode the new output with the OLD decoder
and compare the values - not by byte-equality, which fails on harmless ordering or padding changes
and passes on a compatible-looking but wrong encoding.

**A check built on a lenient parser can only see what that parser exposes.** A validator that reads
structured input through a forgiving reader - a bare `text.split("---", 2)[1]`, an unanchored regex,
a try/except that swallows a parse error - inherits every malformation that reader tolerates. A
second, smuggled copy of the block further down the file lands wherever the split throws its
unexamined remainder, so a check that only asserts on the fields it extracted reports the file clean
while never looking at what the parser silently dropped. Before trusting such a check, enumerate
concretely what its own parser forgives (a duplicated block, a glued-on closing delimiter, a
duplicate key a dict-based loader overwrites), then verify each one STRUCTURALLY against the raw
text - a delimiter count, a line scan - rather than through the same parser, which by construction
cannot see what it already swallowed. The tell: the validator reads its subject with the same
tolerant helper the production loader uses, so its clean verdict can only confirm what that helper
already accepted.

**Read `references/silent-test-defeaters.md` (Read tool)** when a test patches a name, parses tool
output, asserts on an exception message or on rendered output, loops until a condition holds,
pins or clears an environment variable (its own or a spawned child's, or one a library reads at
import), redirects or deletes coverage data from a conftest, simulates a race between a
check and an open, blocks a stub so it can be signalled mid-call, plants a marker to prove a
process ran (or did not), asserts that no file descriptor leaked or that a file is held only
through a memory map, binds a unix socket under `tmp_path`, builds a test double by subclassing
a `@dataclass`, mints synthetic identifiers (an address, a serial, ids that something later
truncates), carries a skip or an exclusion, judges an artifact, compares against a git ref,
guards against cost, or tests environment isolation - or before you claim a code path is untested
or accept a surviving mutation.

## Quick checklist

- [ ] Real dependency or an injected fake behind the real interface; patch only where you own no seam
- [ ] Integration / e2e path exists and is the proof of the contract
- [ ] Test tiers marked so the default run stays offline, by the project's stated convention
- [ ] Boundary inputs covered (UTF/emoji/CJK/binary/wrong-type/oversized/edge numbers), asserting specific behavior
- [ ] Every error branch the code can raise has a test asserting the declared error type
- [ ] Order-independent (passes alone and shuffled); no shared mutable state; code called in-process restores the signal handlers, env, cwd or stdout it changes
- [ ] No timer in a test (`sleep`, deadline poll loop, `*_timeout` wait): block on an event the code signals, plant one if it has none, let the runner's per-test timeout catch a wedge
- [ ] Time/randomness injected, never by patching the process-global clock function; unit suite offline
- [ ] Runs against the project's own locked toolchain, not an ambient/global one; an environment-shaped failure is a wrong-env smell, not a code bug (Python: `env -u VIRTUAL_ENV uv run ...`)
- [ ] One behavior per test; name states the behavior
- [ ] A test that builds a precondition (a permission wall, a missing file, a dead port) asserts it holds before relying on it
- [ ] No test that cannot fail for a real reason
- [ ] Every new RED read before trusting it: the failing line is the assertion, and `-rs` shows 0 skipped

## Common mistakes

- **Mocking your own internals** instead of injecting them. Make the seam a port; pass a fake in.
- **Patching a global you could have injected.** "The network is an external edge" is not a licence to
  stub `fetch` when the caller is your own code - inject the collaborator and keep the real call for e2e.
- **Inventing a private tier convention per file.** If the project has no stated way to mark
  integration tests, add one and document it; an undiscoverable tier is a tier that stops running.
- **Green units, broken contract.** Fakes accepted what the real service rejects. Add the integration test.
- **"It passes on my machine / re-run it."** Flakiness is a defect - fix order/timing/clock, do not retry.
- **Testing the happy path only.** The bugs live in the edge battery above.
- **Chasing 100% coverage** with assertion-free or impl-mirroring tests. Delete those; they hide rot.
- **Single-layer mutation stays green (defense in depth).** Disabling ONE validation check can leave its test green because a LATER check rejects the same bad input, so the test looks like coverage it lacks. Mutate the single layer first; if it stays green, find which later check absorbed it - the test is asserting a contract no single mutation can break, so prove it by disabling the whole defense stack in ONE mutation. Copy the file aside before mutating and restore from that copy, never `git checkout -- <file>` - it restores from the index or HEAD and so discards the uncommitted work you are testing.

## Cross-references

- `bitranox:process-test-driven-development` - red-green-refactor discipline + `testing-anti-patterns.md`.
- `bitranox:coding-input-sanitization` - what to validate/escape at the boundary (this skill is how to TEST it).
- Per-repo convention (bmk): `make test` (unit, offline) vs `make testintegration` (real resources);
  shared fixtures in `tests/conftest.py`.
