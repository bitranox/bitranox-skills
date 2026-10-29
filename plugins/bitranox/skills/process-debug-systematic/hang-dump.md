# Dumping an Intermittent Hang From Inside It

## Overview

A dump taken after a hung run returns sees a tidy process: the tasks are gone and nothing says
which await never came back. An intermittent hang is otherwise attacked by hypothesis, and
hypotheses about a hang are cheap to form and expensive to test. So instrument the next
reproduction to dump the state WHILE it is hung, then kill it.

**Core principle:** the instrument fires inside the hang, from a thread the hang cannot block.

## The Shape

- **Mark every phase.** Record a timestamp each time the run enters a phase. In pytest, a plugin
  with `pytest_runtest_setup` / `pytest_runtest_call` / `pytest_runtest_teardown` hookwrappers.
- **A daemon WATCHDOG THREAD** watches that mark and fires when one phase outlives its budget.
- **The dump**, one section after another:
  - `faulthandler.dump_traceback(all_threads=True)` for every thread stack;
  - every asyncio task with its stack;
  - every server with its live client count;
  - every transport with its peer and its protocol class;
  - the sockets the process itself holds (for example `ss -tanpH` filtered to its pid);
  - any HTTP client still alive, and which objects hold it.
- **Then kill the run** with `os._exit(<a distinct code>)`. A hang that is never killed reports
  nothing and blocks the next run; the distinct exit code says the watchdog fired.

## Details That Decide Whether It Works

- **Enumerate the tasks ON the loop.** Schedule the collection with
  `loop.call_soon_threadsafe(...)` and wait on a `threading.Event` with a timeout. It is the safe
  way to read loop state from another thread, and it answers what no stack can: if the callback
  never runs, the loop is BLOCKED, not merely waiting on an await.
- **Guard and flush EACH section separately.** One section that raises must not take the rest with
  it. Walking `gc.get_objects()` meets dead weak proxies, and `isinstance()` on one raises
  `ReferenceError`: an unguarded dump dies after the thread stacks and the run hangs with no
  report.
- **Under pytest, write where `os._exit` cannot discard it.** Mid-test, fd 2 points at pytest's
  capture file, and `os._exit` throws that away, so a dump written to `sys.stderr` never reaches
  the CI log. Suspend pytest's global capture first and write to a dup of the real fd 2, or write
  to a file.

## Keep It and Prove It

- **Keep the instrument in the repo**, armed automatically in CI (and on request locally), rather
  than rebuilding it for the next hang.
- **Self-test it:** run a deliberately stalled test in a subprocess with a stall budget of about
  2 seconds, and require the distinct exit code AND every section in the output. An instrument that
  has stopped dumping looks exactly like a bug that has stopped happening.
