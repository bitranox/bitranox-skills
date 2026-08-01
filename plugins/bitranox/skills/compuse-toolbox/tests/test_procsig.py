"""Tests for procsig.py - safe process find/kill that cannot self-match. ASCII only.

The load-bearing property is the exclusion: a match set NEVER contains the tool's own process or
any ancestor (the shell), so it cannot kill the caller the way `pkill -f` does.
"""
from pathlib import Path

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
