"""`run` stops on the first Ctrl-C or worker error instead of working through the queue.

Each test counts the command starts on disk, never the elapsed time: a timing margin is what made
the fetch tests flaky on a loaded macOS runner.
"""
import os
import signal
import sys
import threading
import time
import uuid

import pytest

import proxy_pool as pp

_WORKER = """\
import os, sys, time, uuid
open(os.path.join(sys.argv[1], uuid.uuid4().hex), "w").close()
time.sleep(float(sys.argv[2]))
sys.exit(int(sys.argv[3]))
"""
_NO_DEAD_ANSWER = "never-printed-by-the-worker"


def _setup(tmp_path, items, proxies=("p:1", "p:2", "p:3")):
    store = tmp_path / "store"
    store.mkdir()
    pp._grow(pp._p(str(store), "live.txt"), list(proxies))
    worklist = tmp_path / "work.txt"
    worklist.write_text("".join(f"{item}\n" for item in items), encoding="utf-8")
    script = tmp_path / "worker.py"
    script.write_text(_WORKER, encoding="utf-8")
    starts = tmp_path / "starts"
    starts.mkdir()
    return str(store), str(worklist), script, starts


def _run(store, worklist, cmd, *, workers, per_item=1):
    return pp.run(store, worklist, cmd, workers, per_item, 60, False, "http://unused.invalid/", 1, 1,
                  None, _NO_DEAD_ANSWER, cooldown=0.0)


def _worker_cmd(script, starts, seconds, exit_code):
    return f'"{sys.executable}" "{script}" "{starts}" {seconds} {exit_code}'


def _when_started(starts, interrupt):
    """Fire `interrupt` once the first command has started, however slow this host is."""
    def watch():
        deadline = time.monotonic() + 60
        while not os.listdir(starts) and time.monotonic() < deadline:
            time.sleep(0.01)
        interrupt()
    thread = threading.Thread(target=watch, daemon=True)
    thread.start()
    return thread


@pytest.mark.skipif(sys.platform == "win32",
                    reason="os.kill(own pid, SIGINT) terminates the process on Windows rather "
                           "than raising KeyboardInterrupt")
def test_a_ctrl_c_starts_no_queued_item(tmp_path):
    items = [f"i{n}" for n in range(12)]
    store, worklist, script, starts = _setup(tmp_path, items)
    _when_started(starts, lambda: os.kill(os.getpid(), signal.SIGINT))
    with pytest.raises(KeyboardInterrupt):
        _run(store, worklist, _worker_cmd(script, starts, 0.5, 0), workers=2)
    # The two running when the signal came, plus slack for a worker that just took the next item
    # on a loaded host; all 12 start without the stop.
    assert len(os.listdir(starts)) <= 4


@pytest.mark.skipif(sys.platform == "win32",
                    reason="os.kill(own pid, SIGINT) terminates the process on Windows rather "
                           "than raising KeyboardInterrupt")
def test_a_ctrl_c_stops_a_running_item_before_its_next_proxy(tmp_path):
    # One item and a chain of eight proxies, each attempt failing: without the stop the running
    # item walks the rest of its chain after the interrupt.
    proxies = [f"p:{n}" for n in range(8)]
    store, worklist, script, starts = _setup(tmp_path, ["only"], proxies)
    _when_started(starts, lambda: os.kill(os.getpid(), signal.SIGINT))
    with pytest.raises(KeyboardInterrupt):
        _run(store, worklist, _worker_cmd(script, starts, 0.5, 1), workers=1, per_item=8)
    assert len(os.listdir(starts)) <= 2     # all 8 without the stop; slack for a loaded host


@pytest.mark.skipif(not hasattr(signal, "pthread_kill"), reason="no pthread_kill on this platform")
def test_a_ctrl_c_delivered_to_another_thread_still_stops_the_run(tmp_path):
    # The kernel may deliver a process-directed SIGINT to any thread not blocking it. Here it lands
    # on the watcher's thread, so the main thread runs the handler only when it next executes. One
    # item with a long failing chain: no future completes to wake an untimed wait, so only the timed
    # wake stops the chain early (an item that finishes would wake the main thread by itself).
    proxies = [f"p:{n}" for n in range(8)]
    store, worklist, script, starts = _setup(tmp_path, ["only"], proxies)
    _when_started(starts, lambda: signal.pthread_kill(threading.get_ident(), signal.SIGINT))
    with pytest.raises(KeyboardInterrupt):
        _run(store, worklist, _worker_cmd(script, starts, 0.5, 1), workers=1, per_item=8)
    assert len(os.listdir(starts)) <= 3     # all 8 without the wake; slack for a loaded host


def test_a_worker_error_starts_no_queued_item(tmp_path):
    # {item} as the program: the first item is a file that cannot be executed, which raises an
    # OSError out of the worker that is not CommandNotFound; the rest are real runs.
    not_a_program = tmp_path / f"{uuid.uuid4().hex}.txt"
    not_a_program.write_text("not a program\n", encoding="utf-8")
    store, worklist, script, starts = _setup(tmp_path, [str(not_a_program)] + [sys.executable] * 8)
    with pytest.raises(OSError) as raised:
        _run(store, worklist, f'"{{item}}" "{script}" "{starts}" 0.5 0', workers=1)
    assert not isinstance(raised.value, pp.CommandNotFound)
    # The free worker may take an item or two before the main thread cancels the queue.
    assert len(os.listdir(starts)) <= 2


def test_every_item_still_runs_without_an_interrupt(tmp_path):
    items = [f"i{n}" for n in range(4)]
    store, worklist, script, starts = _setup(tmp_path, items)
    assert _run(store, worklist, _worker_cmd(script, starts, 0, 0), workers=2) == (4, 4)
    assert len(os.listdir(starts)) == 4
