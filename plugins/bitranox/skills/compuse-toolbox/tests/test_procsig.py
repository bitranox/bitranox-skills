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
    # the caller's shell (pid 20) is a match too, but must be excluded so it is never signaled
    _mkproc(tmp_path, 20, exe="/bin/bash", cmdline=["bash", "-c", "pkill openvmm"], ppid=1)
    _mkproc(tmp_path, 300, exe="/x/openvmm", cmdline=["openvmm"], ppid=1)
    procs = P.scan(tmp_path, cmdline="openvmm")            # matches BOTH (the shell's cmdline holds it)
    assert {p["pid"] for p in procs} == {20, 300}
    targets = P.resolve_targets(procs, exclude={20, 1})    # self/ancestor set
    assert targets == [300]


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
