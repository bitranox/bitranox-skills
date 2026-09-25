"""Tests for procsig.py - safe process find/kill that cannot self-match. ASCII only.

The load-bearing property is the exclusion: a match set NEVER contains the tool's own process or
any ancestor (the shell), so it cannot kill the caller the way `pkill -f` does.
"""
import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

import procsig as P


def _mkproc(root, pid, exe="/usr/local/bin/openvmm", comm=None, cmdline=None, ppid=1):
    """Create a fake /proc/<pid> with exe symlink, comm, cmdline (NUL-joined), and stat (ppid)."""
    name = comm or Path(exe).name
    d = root / str(pid)
    d.mkdir(parents=True)
    (d / "exe").symlink_to(exe)                       # dangling is fine; os.readlink still resolves
    (d / "comm").write_text(name + "\n", encoding="utf-8")
    parts = cmdline or [exe]
    (d / "cmdline").write_bytes(("\0".join(parts) + "\0").encode("utf-8"))
    (d / "stat").write_text(f"{pid} ({name[:15]}) S {ppid} 0 0\n", encoding="utf-8")
    return d


# ---- the pure scanner ---------------------------------------------------------------------------
def test_scan_by_exe_basename(tmp_path):
    _mkproc(tmp_path, 100, exe="/usr/local/bin/openvmm")
    _mkproc(tmp_path, 101, exe="/usr/bin/bash")
    hits = P.scan(tmp_path, exe="openvmm")
    assert [h["pid"] for h in hits] == [100]


def test_scan_by_exe_full_path(tmp_path):
    _mkproc(tmp_path, 100, exe="/usr/local/bin/openvmm")
    assert [h["pid"] for h in P.scan(tmp_path, exe="/usr/local/bin/openvmm")] == [100]


def test_scan_by_comm(tmp_path):
    _mkproc(tmp_path, 200, exe="/x/vmworker", comm="vmworker")
    _mkproc(tmp_path, 201, exe="/x/other", comm="other")
    assert [h["pid"] for h in P.scan(tmp_path, comm="vmworker")] == [200]


def test_scan_by_cmdline_substring(tmp_path):
    _mkproc(tmp_path, 300, exe="/x/openvmm", cmdline=["openvmm", "--vm", "vm-79099-disk-0"])
    _mkproc(tmp_path, 301, exe="/x/openvmm", cmdline=["openvmm", "--vm", "vm-64000-disk-0"])
    assert [h["pid"] for h in P.scan(tmp_path, cmdline="79099")] == [300]


# ---- the safety property: exclusion of self + ancestors -----------------------------------------
def test_ancestors_walks_the_ppid_chain(tmp_path):
    _mkproc(tmp_path, 10, ppid=1)
    _mkproc(tmp_path, 20, ppid=10)
    _mkproc(tmp_path, 30, ppid=20)
    assert P.ancestors(30, tmp_path) == {30, 20, 10, 1}


def test_resolve_targets_excludes_self_and_ancestors(tmp_path):
    # The matching ancestor (pid 20) is a PLAIN argv on purpose. It used to be `bash -c "pkill
    # openvmm"`, but a shell carrying the needle is now skipped by the cmdline carve-out before
    # exclusion is ever consulted - so that fixture would make this test pass green while
    # exercising resolve_targets not at all.
    _mkproc(tmp_path, 20, exe="/x/openvmm-supervisor",
            cmdline=["openvmm-supervisor", "--watch", "openvmm"], ppid=1)
    _mkproc(tmp_path, 300, exe="/x/openvmm", cmdline=["openvmm"], ppid=1)
    procs = P.scan(tmp_path, cmdline="openvmm")            # matches BOTH
    assert {p["pid"] for p in procs} == {20, 300}
    targets = P.resolve_targets(procs, exclude={20, 1})    # self/ancestor set
    assert targets == [300]


def test_a_caller_shell_holding_the_needle_never_even_matches(tmp_path):
    """The original incident shape, now stopped one layer EARLIER than the exclusion.

    Exclusion only ever covered self and ancestors, and the 2026-07-28 kill hit a SIBLING shell,
    which is neither. Declining to search a shell's command string removes the whole class rather
    than one more instance of it.
    """
    _mkproc(tmp_path, 20, exe="/bin/bash", cmdline=["bash", "-c", "pkill openvmm"], ppid=1)
    _mkproc(tmp_path, 300, exe="/x/openvmm", cmdline=["openvmm"], ppid=1)
    assert [p["pid"] for p in P.scan(tmp_path, cmdline="openvmm")] == [300]


# ---- main() find + kill -------------------------------------------------------------------------
def test_main_find_lists_matches(tmp_path, capsys, monkeypatch):
    _mkproc(tmp_path, 300, exe="/x/openvmm", cmdline=["openvmm", "--vm", "x"], ppid=1)
    monkeypatch.setattr(P, "PROC", tmp_path)
    monkeypatch.setattr(P, "_self_and_ancestors", lambda: set())
    assert P.main(["--exe", "openvmm"]) == 0
    assert "300" in capsys.readouterr().out


def test_main_kill_signals_only_matched_nonexcluded(tmp_path, monkeypatch):
    _mkproc(tmp_path, 20, exe="/bin/bash", cmdline=["bash", "-c", "procsig --kill --cmdline openvmm"], ppid=1)
    _mkproc(tmp_path, 300, exe="/x/openvmm", cmdline=["openvmm"], ppid=1)
    monkeypatch.setattr(P, "PROC", tmp_path)
    monkeypatch.setattr(P, "_self_and_ancestors", lambda: {20, 1})   # the caller shell + init
    killed = []
    monkeypatch.setattr(P, "_kill", lambda pid, sig: killed.append((pid, sig)))
    rc = P.main(["--kill", "--cmdline", "openvmm"])
    assert rc == 0
    assert [pid for pid, _ in killed] == [300]              # NEVER the caller shell (20)


def test_main_kill_nothing_matched_is_rc1(tmp_path, monkeypatch):
    _mkproc(tmp_path, 300, exe="/x/other", cmdline=["other"], ppid=1)
    monkeypatch.setattr(P, "PROC", tmp_path)
    monkeypatch.setattr(P, "_self_and_ancestors", lambda: set())
    monkeypatch.setattr(P, "_kill", lambda pid, sig: None)
    assert P.main(["--kill", "--exe", "openvmm"]) == 1


# ---- --cmdline must not match a command string a shell was merely HANDED -------------------------

def test_scan_by_cmdline_skips_a_sibling_shell_carrying_the_needle(tmp_path):
    """A shell handed a command string is not evidence that the program is running.

    Measured 2026-07-28: `procsig --cmdline bp_sweep_watchdog.py --kill` signaled the real watchdog
    AND a sibling bash whose argv merely CONTAINED the needle - the caller's own pipeline - which
    killed the command mid-run. Self and ancestors were excluded; a sibling is neither, so the
    exclusion could not help. The fix is upstream of it: a shell's command string is never
    searched.
    """
    _mkproc(tmp_path, 400, exe="/usr/bin/python3", cmdline=["python3", "watchdog.py"])
    _mkproc(tmp_path, 401, exe="/bin/bash", cmdline=["bash", "-c", "python3 watchdog.py & sleep 1"])
    assert [h["pid"] for h in P.scan(tmp_path, cmdline="watchdog.py")] == [400]


def test_scan_by_cmdline_skips_a_shell_behind_a_forking_wrapper(tmp_path):
    """`timeout 30 ssh host '<cmd>'` is the standard fleet-probe form and must be skipped too.

    timeout/sudo/sshpass FORK AND KEEP their argv, so the shell sits one token further along. An
    earlier fix that tested only argv[0] against a shell table let exactly this shape through.
    """
    _mkproc(tmp_path, 500, exe="/usr/bin/python3", cmdline=["python3", "watchdog.py"])
    _mkproc(tmp_path, 501, exe="/usr/bin/timeout",
            cmdline=["timeout", "30", "ssh", "host", "python3 watchdog.py"])
    assert [h["pid"] for h in P.scan(tmp_path, cmdline="watchdog.py")] == [500]


def test_scan_by_cmdline_still_matches_a_plain_argv(tmp_path):
    """The carve-out must not swallow the ordinary case it exists to protect."""
    _mkproc(tmp_path, 600, exe="/x/openvmm", cmdline=["openvmm", "--vm", "vm-79099-disk-0"])
    _mkproc(tmp_path, 601, exe="/x/openvmm", cmdline=["openvmm", "--vm", "vm-64000-disk-0"])
    assert [h["pid"] for h in P.scan(tmp_path, cmdline="vm-79099")] == [600]


# ---- a short-option CLUSTER ending in c hands over a command string too -------------------------

@pytest.mark.parametrize("parts", [
    ["script", "-qc", "python3 w.py; true", "/dev/null"],
    ["su", "root", "-lc", "python3 w.py; true"],
    ["runuser", "-u", "root", "-lc", "python3 w.py && true"],
])
def test_a_clustered_c_on_a_non_shell_is_never_searched(parts):
    """`script -qc '<cmd>'` and `su root -lc '<cmd>'` hand a whole command to a shell exactly like
    a standalone `-c` does; only testing the standalone spelling searched them in full."""
    assert P._cmdline_search_text(parts, exe="/usr/bin/" + parts[0], comm=parts[0]) is None


@pytest.mark.parametrize("parts", [
    ["gcc", "-c", "foo.c"],
    ["grep", "-ic", "pattern", "file"],
    ["script", "-q", "out.log"],
])
def test_a_one_word_clustered_c_value_is_still_identity(parts):
    """The control: a one-word value after a c-cluster is an option value, not a command."""
    assert P._cmdline_search_text(parts, exe="/usr/bin/" + parts[0], comm=parts[0]) \
        == " ".join(parts)


# ---- the shell-option walker, one case per documented regression --------------------------------

@pytest.mark.parametrize("parts, expected", [
    (["bash", "-O", "extglob", "-c", "python3 w.py"], "bash -O extglob -c"),
    (["zsh", "-o", "pipefail", "-c", "python3 w.py"], "zsh -o pipefail -c"),
    (["bash", "--rcfile", "/etc/rc", "-c", "python3 w.py"], "bash --rcfile /etc/rc -c"),
    (["bash", "--rcfile=/etc/rc", "-c", "python3 w.py"], "bash --rcfile=/etc/rc -c"),
    (["bash", "--norc", "-c", "python3 w.py"], "bash --norc -c"),
    (["fish", "--command", "python3 w.py"], "fish --command"),
    (["fish", "--command=python3 w.py"], "fish"),
    (["bash", "-oc", "pipefail", "python3 w.py"], None),
    (["bash", "-oO", "pipefail", "extglob", "-c", "python3 w.py"], None),
    (["bash", "--not-modelled", "-c", "python3 w.py"], None),
    (["busybox", "sh", "-c", "python3 w.py"], "busybox sh -c"),
    (["busybox", "httpd", "-f"], "busybox httpd -f"),
    (["setsid", "bash", "-lc", "python3 w.py"], "setsid bash -lc"),
    (["bash", "deploy.sh", "--flag"], "bash deploy.sh --flag"),
    (["rsync", "-av", "/home/u/.ssh", "/backup"], "rsync -av /home/u/.ssh /backup"),
])
def test_the_shell_option_walker(parts, expected):
    assert P._cmdline_search_text(parts, exe="/usr/bin/" + parts[0], comm=parts[0]) == expected


# ---- a blank needle matches nothing, and an unreadable proc never matches ------------------------

def _no_exe_proc(root, pid, comm="kthreadd"):
    d = root / str(pid)
    d.mkdir(parents=True)
    (d / "comm").write_text(comm + "\n", encoding="utf-8")
    (d / "cmdline").write_bytes(b"")
    (d / "stat").write_text(f"{pid} ({comm}) S 1 0 0\n", encoding="utf-8")


def _harness(tmp_path, monkeypatch, excluded=frozenset()):
    monkeypatch.setattr(P, "PROC", tmp_path)
    monkeypatch.setattr(P, "_self_and_ancestors", lambda: set(excluded))
    sent = []
    monkeypatch.setattr(P, "_kill", lambda pid, sig: sent.append((pid, sig)))
    return sent


@pytest.mark.parametrize("flag, needle", [
    ("--exe", ""), ("--exe", "   "), ("--comm", ""), ("--comm", " "), ("--cmdline", ""),
    ("--cmdline", "\t"),
])
def test_a_blank_needle_is_refused_and_signals_nothing(tmp_path, monkeypatch, capsys, flag,
                                                       needle):
    """`--exe "$UNSET" --kill` matched every process whose exe link is unreadable - kernel
    threads, and the user's own `systemd --user` - and signaled them."""
    _no_exe_proc(tmp_path, 2)
    _mkproc(tmp_path, 300, exe="/x/worker", cmdline=["worker"])
    sent = _harness(tmp_path, monkeypatch)
    assert P.main(["--kill", flag, needle]) == 2
    assert sent == []
    assert "empty" in capsys.readouterr().err


def test_a_proc_with_an_unreadable_exe_never_matches_by_exe(tmp_path):
    _no_exe_proc(tmp_path, 2)
    _mkproc(tmp_path, 300, exe="/x/worker", cmdline=["worker"])
    assert P.scan(tmp_path, exe="") == []
    assert [h["pid"] for h in P.scan(tmp_path, exe="worker")] == [300]


# ---- names the kernel reports differently from the name you know -------------------------------

def test_a_replaced_binary_still_matches_by_exe(tmp_path):
    """After a package upgrade the old daemon's exe link reads `<path> (deleted)` - and the old
    daemons are exactly the processes one goes looking for."""
    _mkproc(tmp_path, 300, exe="/usr/sbin/worker (deleted)", comm="worker", cmdline=["worker"])
    assert [h["pid"] for h in P.scan(tmp_path, exe="worker")] == [300]
    assert [h["pid"] for h in P.scan(tmp_path, exe="/usr/sbin/worker")] == [300]
    assert P.scan(tmp_path, exe="worker (deleted)") == []


def test_a_long_name_matches_by_comm_despite_kernel_truncation(tmp_path):
    """The kernel keeps 15 bytes of comm, so `backup-scheduler` is `backup-schedule` there."""
    _mkproc(tmp_path, 300, exe="/opt/backup-scheduler", comm="backup-schedule",
            cmdline=["./backup-scheduler"])
    assert [h["pid"] for h in P.scan(tmp_path, comm="backup-scheduler")] == [300]
    assert [h["pid"] for h in P.scan(tmp_path, comm="backup-schedule")] == [300]


def test_a_truncated_comm_alone_does_not_match_a_different_long_name(tmp_path):
    """The control: two long names sharing 15 bytes must not be confused - the full name has to
    be confirmed from the exe or argv[0]."""
    _mkproc(tmp_path, 300, exe="/opt/backup-scheduler-v2", comm="backup-schedule",
            cmdline=["/opt/backup-scheduler-v2"])
    assert P.scan(tmp_path, comm="backup-scheduler") == []


# ---- exit codes: 0 found / 1 none / 2 could not answer or could not act -------------------------

def test_list_mode_exit_code_ignores_self_and_ancestors(tmp_path, monkeypatch):
    """A needle typed on procsig's own command line matches procsig itself. Counting that as a hit
    made `procsig --cmdline X && echo running` print running for a process that does not exist."""
    _mkproc(tmp_path, 20, exe="/usr/bin/python3", cmdline=["python3", "procsig.py", "--cmdline",
                                                           "zz-nothing"])
    _harness(tmp_path, monkeypatch, excluded={20, 1})
    assert P.main(["--cmdline", "zz-nothing"]) == 1


def test_list_mode_exit_code_is_0_for_a_real_match(tmp_path, monkeypatch):
    _mkproc(tmp_path, 20, exe="/usr/bin/python3", cmdline=["python3", "procsig.py"])
    _mkproc(tmp_path, 300, exe="/x/zz-worker", cmdline=["zz-worker"])
    _harness(tmp_path, monkeypatch, excluded={20, 1})
    assert P.main(["--exe", "zz-worker"]) == 0


def test_a_missing_proc_is_an_error_not_not_running(tmp_path, monkeypatch, capsys):
    _harness(tmp_path / "no-proc-here", monkeypatch)
    assert P.main(["--exe", "worker"]) == 2
    assert "nothing can be answered" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["_IGN", "_DFL", "_SETMASK", "SIG_IGN", "BOGUS", "NSIG"])
def test_a_name_that_is_not_a_signal_is_refused(tmp_path, monkeypatch, capsys, name):
    """`getattr(signal, "SIG" + name)` also finds SIG_IGN (1), SIG_DFL (0) and SIG_SETMASK (2),
    so `--signal _IGN` sent SIGHUP."""
    _mkproc(tmp_path, 300, exe="/x/worker", cmdline=["worker"])
    sent = _harness(tmp_path, monkeypatch)
    assert P.main(["--kill", "--signal", name, "--exe", "worker"]) == 2
    assert sent == []
    assert "unknown signal" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["TERM", "SIGTERM", "term"])
def test_a_real_signal_name_is_accepted(tmp_path, monkeypatch, name):
    _mkproc(tmp_path, 300, exe="/x/worker", cmdline=["worker"])
    sent = _harness(tmp_path, monkeypatch)
    assert P.main(["--kill", "--signal", name, "--exe", "worker"]) == 0
    assert sent == [(300, int(signal.SIGTERM))]


@pytest.mark.parametrize("error", [PermissionError(1, "Operation not permitted"),
                                   ProcessLookupError(3, "No such process")])
def test_kill_exits_2_when_a_signal_could_not_be_delivered(tmp_path, monkeypatch, capsys, error):
    _mkproc(tmp_path, 300, exe="/x/worker", cmdline=["worker"])
    _harness(tmp_path, monkeypatch)

    def refuse(pid, sig):
        raise error

    monkeypatch.setattr(P, "_kill", refuse)
    assert P.main(["--kill", "--exe", "worker"]) == 2
    assert "failed to signal 300" in capsys.readouterr().err


def test_a_non_cp1252_cmdline_does_not_crash_a_cp1252_console(tmp_path):
    """Listing prints each match's command line; a cp1252 stdout must not turn that into a
    traceback whose exit 1 reads as "not running"."""
    proc_root = tmp_path / "proc"
    _mkproc(proc_root, 300, exe="/x/worker", cmdline=["worker", "東京"])
    script = (f"import sys; sys.path.insert(0, {str(Path(P.__file__).parent)!r}); "
              "import procsig as P; from pathlib import Path; "
              f"P.PROC = Path({str(proc_root)!r}); P._self_and_ancestors = lambda: set(); "
              "sys.exit(P.main(['--exe', 'worker']))")
    r = subprocess.run([sys.executable, "-c", script], capture_output=True, check=False,
                       env={**os.environ, "PYTHONIOENCODING": "cp1252"})
    assert r.returncode == 0, r.stderr
    assert b"Traceback" not in r.stderr
    assert b"300" in r.stdout
