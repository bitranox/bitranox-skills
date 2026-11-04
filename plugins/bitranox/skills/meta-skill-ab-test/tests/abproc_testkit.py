"""Process helpers the suite shares: is a pid still running, clean up after a failed test, SIGINT on a marker.

Imported by its bare name (conftest puts this directory on sys.path), never as tests.<module>:
a bare `pytest` run does not make `tests` a package.
"""
import os
import signal
import threading
import time
from pathlib import Path


def alive(pid):
    """True while pid runs; a zombie (killed, not yet reaped by its new parent) counts as gone."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    if not Path("/proc/self/stat").exists():
        return True  # no procfs (macOS): kill(0) is the only reading there is
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return False  # it exited between the two reads
    except (OSError, IndexError):
        return True
    return state != "Z"


def gone_within(pid, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not alive(pid):
            return True
        time.sleep(0.05)
    return False


def kill_if_alive(pid):
    """Cleanup for a test that failed: never leave a process it started running past the test."""
    if pid is not None and alive(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def pids_in(*pidfiles):
    """The pid written in each existing pidfile, in order."""
    return [int(p.read_text(encoding="utf-8")) for p in pidfiles if p.is_file() and p.read_text(encoding="utf-8").strip()]


class SigintOnMarker:
    """Send this process one SIGINT as soon as `marker` exists, i.e. once the step to interrupt has started.

    A fixed timer would land wherever a slow runner happens to be; the marker is written by the
    very step the test means to interrupt.
    """

    def __init__(self, marker, timeout_s=60.0):
        self.marker, self.timeout_s = marker, timeout_s
        self.sent = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)

    def _watch(self):
        deadline = time.monotonic() + self.timeout_s
        while not self._stop.is_set() and time.monotonic() < deadline:
            if self.marker.exists():
                self.sent = True
                os.kill(os.getpid(), signal.SIGINT)
                return
            self._stop.wait(0.02)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
