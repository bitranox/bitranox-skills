# /// script
# requires-python = ">=3.10"
# ///
"""Move big files with a real speed cap, and judge whether a long transfer is still alive.

Why this exists: on 2026-08-03 a 5.4 GB download was declared stalled because the output
file read 0 bytes - Windows does not update a file's size in the directory entry until the
handle is flushed, so the size was a stale lie. Meanwhile the curl process had burned 158 s
of CPU, which is flatly inconsistent with "stalled". Acting on the one flat instrument
nearly killed a healthy transfer that was already 373 MB in.

The rule this encodes: ONE instrument can prove MOTION but never prove ABSENCE of motion.
So a single flat signal is UNKNOWN, never STALLED, and when signals disagree the moving one
wins and the flat one is named as suspect.

    # is this transfer alive?
    uv run transfer.py check --file big.iso --pid 4992 --interval 10

    # fetch with a real cap (bits are spelled out, because `curl 8M` is 8 MiB/s = 67 Mbit)
    uv run transfer.py fetch URL -o big.iso --rate 8Mbit

    # send one to another host, capped and resumable (rsync --bwlimit is KiB/s, so 8 Mbit = 976)
    uv run transfer.py push big.iso root@host:/dst/ --rate 8Mbit --ssh "ssh -i /key"

check: exit 0 ADVANCING, 1 STALLED, 2 UNKNOWN.  fetch/push: exit 0 ok, 1 failed.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

CLK_TCK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100


@dataclass
class Signal:
    """One progress indicator sampled twice. `None` means "could not read", NOT "zero"."""

    name: str
    before: float | None
    after: float | None

    @property
    def usable(self) -> bool:
        return self.before is not None and self.after is not None

    @property
    def delta(self) -> float | None:
        return None if not self.usable else self.after - self.before


def decide(signals: list[Signal]) -> tuple[int, str]:
    """(exit code, message). PURE - the whole judgement, no I/O.

    Asymmetric by design: motion needs ONE witness, a stall needs at least TWO, because a
    single instrument that reads flat is indistinguishable from a single instrument that
    is broken.
    """
    usable = [s for s in signals if s.usable]
    unusable = [s.name for s in signals if not s.usable]
    if not usable:
        return 2, ("UNKNOWN: no signal could be read "
                   f"({', '.join(unusable) or 'none given'}). Missing evidence is not "
                   "evidence of a stall.")

    moving = [s for s in usable if s.delta != 0]
    flat = [s for s in usable if s.delta == 0]

    if moving:
        detail = ", ".join(f"{s.name} {s.delta:+g}" for s in moving)
        msg = f"ADVANCING: {detail}"
        if flat:
            msg += (f" | did NOT move: {', '.join(s.name for s in flat)} - that instrument "
                    "is suspect here, do not read a stall from it alone")
        if unusable:
            msg += f" | unreadable: {', '.join(unusable)}"
        return 0, msg

    if len(usable) < 2:
        return 2, (f"UNKNOWN: only one usable signal ({usable[0].name}) and it is flat. "
                   "One instrument cannot prove a stall - add a second, independent one "
                   "(process CPU, io counters, a remote-side count).")

    names = ", ".join(s.name for s in usable)
    extra = f" | unreadable: {', '.join(unusable)}" if unusable else ""
    return 1, f"STALLED: {len(usable)} independent signals all flat ({names}){extra}"


# ---- readers: every one returns None rather than raising ---------------------------

def read_file_size(path: str | Path) -> int | None:
    try:
        return Path(path).stat().st_size
    except OSError:
        return None


def read_pid_cpu_seconds(pid: int) -> float | None:
    """utime+stime from /proc/<pid>/stat, in seconds."""
    try:
        parts = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    except (OSError, IndexError):
        return None
    try:  # fields 14/15 after the comm field (1-indexed 14,15 -> 11,12 here)
        return (int(parts[11]) + int(parts[12])) / CLK_TCK
    except (ValueError, IndexError):
        return None


def read_pid_io_bytes(pid: int) -> int | None:
    """read_bytes+write_bytes from /proc/<pid>/io (needs permission)."""
    try:
        text = Path(f"/proc/{pid}/io").read_text()
    except OSError:
        return None
    total = 0
    for key in ("read_bytes:", "write_bytes:"):
        m = re.search(rf"^{key}\s+(\d+)$", text, re.M)
        if not m:
            return None
        total += int(m.group(1))
    return total


def read_command_number(cmd: str) -> float | None:
    """First number printed by a command - the generic/remote sampler.

    Split with shlex and run WITHOUT a shell: the toolbox contract forbids shell=True, and
    a sampler needs no local shell anyway. A remote sampler still works, because the remote
    command travels as ONE quoted argument and the far side runs its own shell:
        --cmd "ssh host 'powershell -File C:\\count.ps1'"
    """
    try:
        argv = shlex.split(cmd)
    except ValueError:
        return None
    if not argv:
        return None
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", p.stdout or "")
    return float(m.group(0)) if m else None


# ---- rate parsing -------------------------------------------------------------------

_RATE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kmg]?)(bit|b|)\s*$", re.I)


def parse_rate(text: str) -> int:
    """Bytes/s from '8Mbit' | '1M' | '1000000'.

    BIT units are spelled out and divided by 8; BYTE units follow curl and are binary
    (1M = 1 MiB). `curl --limit-rate 8M` is 8 MiB/s = ~67 Mbit/s, so asking for "8 Mbit"
    and typing 8M caps 8x too high and nothing complains.
    """
    m = _RATE.match(text or "")
    if not m:
        raise ValueError(f"unparseable rate {text!r}; use 8Mbit, 1M, or plain bytes/s")
    value, scale, unit = float(m.group(1)), m.group(2).lower(), m.group(3).lower()
    if unit == "bit":
        mult = {"": 1, "k": 1_000, "m": 1_000_000, "g": 1_000_000_000}[scale]
        return int(value * mult / 8)
    mult = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[scale]
    return int(value * mult)


# ---- commands -----------------------------------------------------------------------

def cmd_check(args: argparse.Namespace) -> int:
    def sample() -> list[Signal]:
        out = []
        if args.file:
            out.append(("file:size", read_file_size(args.file)))
        if args.pid:
            out.append((f"pid{args.pid}:cpu_s", read_pid_cpu_seconds(args.pid)))
            out.append((f"pid{args.pid}:io_bytes", read_pid_io_bytes(args.pid)))
        for i, c in enumerate(args.cmd or []):
            out.append((f"cmd{i}", read_command_number(c)))
        return out

    first = sample()
    time.sleep(args.interval)
    second = sample()
    signals = [Signal(n, b, a) for (n, b), (_, a) in zip(first, second)]
    code, msg = decide(signals)
    print(msg)
    return code


def build_fetch_args(url: str, out: str, rate_bps: int | None) -> list[str]:
    """curl argv for a resumable, capped, non-spinning download. Data, so tests can assert.

    --no-progress-meter is not cosmetic: curl's meter emits \\r updates with no newline, and
    piping that into a consumer (PowerShell `| Out-Null` was the live case) makes it buffer
    one ever-growing line and peg a core.
    """
    argv = ["curl", "-L", "--no-progress-meter", "--retry", "5", "--retry-delay", "5",
            "-C", "-", "-o", out, url]
    if rate_bps:
        argv[1:1] = ["--limit-rate", str(rate_bps)]
    return argv


def cmd_fetch(args: argparse.Namespace) -> int:
    if shutil.which("curl") is None:
        print("fetch: curl not found on PATH", file=sys.stderr)
        return 1
    rate = parse_rate(args.rate) if args.rate else None
    out = args.output or args.url.rsplit("/", 1)[-1]
    argv = build_fetch_args(args.url, out, rate)
    if rate:
        print(f"# cap {rate} B/s ({rate * 8 / 1e6:.3g} Mbit/s) -> {out}", file=sys.stderr)
    p = subprocess.run(argv)
    size = read_file_size(out)
    print(f"{out} {size if size is not None else '?'} bytes (curl rc={p.returncode})")
    return 0 if p.returncode == 0 else 1


def build_push_args(src: str, dest: str, rate_bps: int | None,
                    ssh: str | None = None) -> list[str]:
    """rsync argv for a resumable, capped host-to-host push. Data, so tests can assert.

    The unit conversion is the reason this is code and not a remembered flag. rsync's
    --bwlimit is KiB/s when given no suffix, so an 8 Mbit/s cap is 976 - not 8, and not
    8000. That is the same class of trap as curl's --limit-rate (where a bare 8M means
    8 MiB/s = 67 Mbit/s), which parse_rate already exists to solve; this just applies it
    on the other side. A hand-computed cap is how one silently ends up 8x or 1024x off.

    --bwlimit=0 means UNLIMITED in rsync, so a sub-KiB rate floors at 1 rather than
    rounding to 0 and quietly removing the cap the caller asked for.

    --partial keeps the bytes of a killed transfer and --inplace makes the resume append
    to that same file instead of restarting into a temp copy - which matters most on
    exactly the big, slow, capped transfers this is for.
    """
    argv = ["rsync", "-av", "--partial", "--inplace"]
    if rate_bps:
        # floor, not round: this is a CAP, so landing under the requested rate is correct
        # and landing over it is not. 8 Mbit = 976.5625 KiB/s -> 976 (7.995 Mbit), whereas
        # rounding gives 977 (8.004 Mbit), which exceeds the limit the caller asked for.
        argv.append(f"--bwlimit={max(1, int(rate_bps / 1024))}")
    if ssh:
        argv += ["-e", ssh]
    argv += [src, dest]
    return argv


def cmd_push(args: argparse.Namespace) -> int:
    if shutil.which("rsync") is None:
        print("push: rsync not found on PATH", file=sys.stderr)
        return 1
    rate = parse_rate(args.rate) if args.rate else None
    argv = build_push_args(args.src, args.dest, rate, ssh=args.ssh)
    if rate:
        print(f"# cap {rate} B/s ({rate * 8 / 1e6:.3g} Mbit/s) -> {args.dest}", file=sys.stderr)
    p = subprocess.run(argv)
    return 0 if p.returncode == 0 else 1

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd_name", required=True)

    c = sub.add_parser("check", help="sample signals twice and judge motion")
    c.add_argument("--file", help="watch this file's size")
    c.add_argument("--pid", type=int, help="watch this pid's CPU + io counters")
    c.add_argument("--cmd", action="append",
                   help="shell command printing a number (repeatable; use for remote hosts)")
    c.add_argument("--interval", type=float, default=10.0, help="seconds between samples [10]")
    c.set_defaults(func=cmd_check)

    f = sub.add_parser("fetch", help="download resumably with a real rate cap")
    f.add_argument("url")
    f.add_argument("-o", "--output")
    f.add_argument("--rate", help="e.g. 8Mbit (bits) or 1M (MiB/s, curl-style)")

    u = sub.add_parser("push", help="send a file to another host, resumably, with a rate cap")
    u.add_argument("src", help="local path to send")
    u.add_argument("dest", help="[user@]host:/path/ destination")
    u.add_argument("--rate", help="e.g. 8Mbit (bits) or 1M (MiB/s); converted to rsync KiB/s")
    u.add_argument("--ssh", help="ssh command, e.g. 'ssh -i /key -o BatchMode=yes'")
    u.set_defaults(func=cmd_push)
    f.set_defaults(func=cmd_fetch)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
