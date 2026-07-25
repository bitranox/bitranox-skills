# /// script
# requires-python = ">=3.10"
# ///
"""Find or signal processes safely - the self-match-proof replacement for `pgrep -f` / `pkill -f`.

Why: `pgrep -f X` / `pkill -f X` match against /proc/<pid>/cmdline, and the shell running the very
command holds X in its own cmdline, so it matches (and kills) itself - the classic
pgrep-self-match footgun, where a stray match kills your own shell. This tool
reads /proc directly and ALWAYS excludes its own process and every ancestor (the caller's shell),
so it structurally cannot signal the caller. It never puts the match string on a command line
another pgrep could see either.

Match by (pick one):
  --exe PATH_OR_BASENAME   the /proc/<pid>/exe target (cannot self-match a command line at all)
  --comm NAME              the process name in /proc/<pid>/comm
  --cmdline SUBSTR         a substring of the full command line (the safe `pgrep -f` replacement)

Default action lists matches; `--kill` (with `--signal`, default TERM) signals them. Excluded
matches (self/ancestors, or an unreadable proc) are shown but never signaled.

Run: `uv run scripts/procsig.py --exe myserver`
     `uv run scripts/procsig.py --kill --signal TERM --cmdline job-1234`
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

PROC = Path("/proc")                                          # overridden in tests with a fake tree


def _read_exe(pdir: Path) -> str:
    """Resolved target of /proc/<pid>/exe, or '' if unreadable (kernel thread, permission)."""
    try:
        return os.readlink(pdir / "exe")
    except OSError:
        return ""


def _read_comm(pdir: Path) -> str:
    try:
        return (pdir / "comm").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _read_cmdline(pdir: Path) -> str:
    """The NUL-separated /proc/<pid>/cmdline joined with spaces, or '' if unreadable."""
    try:
        raw = (pdir / "cmdline").read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()


def _ppid(pdir: Path) -> int | None:
    """Parent pid from /proc/<pid>/stat. The comm field can hold spaces/parens, so split after the
    LAST ')': fields then are [state, ppid, ...]."""
    try:
        stat = (pdir / "stat").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    rparen = stat.rfind(")")
    if rparen == -1:
        return None
    rest = stat[rparen + 1:].split()
    return int(rest[1]) if len(rest) >= 2 and rest[1].lstrip("-").isdigit() else None


def scan(proc_root, *, exe=None, comm=None, cmdline=None) -> list[dict]:
    """Processes under `proc_root` matching the one given filter. PURE over proc_root - unit-testable.

    exe matches the exe path OR its basename; comm matches exactly; cmdline matches as a substring.
    """
    hits = []
    for pdir in sorted(Path(proc_root).glob("[0-9]*"), key=lambda p: int(p.name)):
        pid = int(pdir.name)
        p_exe, p_comm, p_cmd = _read_exe(pdir), _read_comm(pdir), _read_cmdline(pdir)
        if exe is not None:
            ok = p_exe == exe or os.path.basename(p_exe) == exe
        elif comm is not None:
            ok = p_comm == comm
        else:
            ok = bool(cmdline) and cmdline in p_cmd
        if ok:
            hits.append({"pid": pid, "exe": p_exe, "comm": p_comm, "cmdline": p_cmd})
    return hits


def ancestors(pid: int, proc_root) -> set[int]:
    """`pid` plus every ancestor pid, walking the ppid chain. Cycle/So-missing-safe. PURE."""
    seen: set[int] = set()
    cur: int | None = pid
    while cur is not None and cur not in seen:
        seen.add(cur)
        cur = _ppid(Path(proc_root) / str(cur))
    return seen


def resolve_targets(procs: list[dict], exclude: set[int]) -> list[int]:
    """PIDs of `procs` that are not in `exclude` (self/ancestors). PURE - the safety gate."""
    return [p["pid"] for p in procs if p["pid"] not in exclude]


def _self_and_ancestors() -> set[int]:
    """This process plus its ancestors (the caller shell chain) - the live exclusion set."""
    return ancestors(os.getpid(), PROC)


def _kill(pid: int, sig: int) -> None:                        # seam: monkeypatched in tests
    os.kill(pid, sig)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find or signal processes without self-matching.")
    m = ap.add_mutually_exclusive_group(required=True)
    m.add_argument("--exe", help="match /proc/<pid>/exe path or basename")
    m.add_argument("--comm", help="match the process name (/proc/<pid>/comm) exactly")
    m.add_argument("--cmdline", help="match a substring of the full command line (safe pgrep -f)")
    ap.add_argument("--kill", action="store_true", help="signal the matches (default: just list)")
    ap.add_argument("--signal", default="TERM", help="signal name for --kill (default TERM)")
    args = ap.parse_args(argv)

    procs = scan(PROC, exe=args.exe, comm=args.comm, cmdline=args.cmdline)
    excluded = _self_and_ancestors()
    targets = resolve_targets(procs, excluded)

    for p in procs:
        tag = "  [self/ancestor - skipped]" if p["pid"] in excluded else ""
        print(f"{p['pid']:>8}  {p['exe'] or p['comm'] or '?':40.40}  {p['cmdline'][:60]}{tag}")

    if not args.kill:
        return 0 if procs else 1
    try:
        sig = getattr(signal, args.signal if args.signal.startswith("SIG") else "SIG" + args.signal)
    except AttributeError:
        print(f"unknown signal: {args.signal}", file=sys.stderr)
        return 2
    for pid in targets:
        try:
            _kill(pid, int(sig))
            print(f"signaled {pid} with {args.signal}")
        except OSError as exc:
            print(f"failed to signal {pid}: {exc}", file=sys.stderr)
    return 0 if targets else 1


if __name__ == "__main__":
    sys.exit(main())
