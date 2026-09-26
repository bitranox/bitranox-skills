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

Run with plain python3, NOT uv run: a `check --cmd` sampler inherits the launcher's
environment, and uv run swaps in its own throwaway interpreter.

    # is this transfer alive?
    python3 transfer.py check --file big.iso --pid 4992 --interval 10

    # fetch with a real cap (bits are spelled out, because `curl 8M` is 8 MiB/s = 67 Mbit)
    python3 transfer.py fetch URL -o big.iso --rate 8Mbit

    # send one to another host, capped and resumable (rsync --bwlimit is KiB/s, so 8 Mbit = 976)
    python3 transfer.py push big.iso root@host:/dst/ --rate 8Mbit --ssh "ssh -i /key"

    # a sampler runs with NO shell: wrap a pipeline in one explicitly
    python3 transfer.py check --file big.iso --cmd "sh -c 'grep eth0 /proc/net/dev'"

check: exit 0 ADVANCING, 1 STALLED, 2 UNKNOWN (or a usage error).
fetch/push: exit 0 ok, 1 the transfer failed, 2 usage error (bad rate, no output name, curl or
rsync missing). --pid reads /proc, so it is Linux-only; elsewhere its signals read unusable.
"""
from __future__ import annotations

# Run with plain python3, never `uv run`: the command this jig runs inherits the launcher's
# environment, and under uv run a child `python3` resolves to uv's throwaway build env, where
# pytest and the project's packages are missing - a false RED. toolbox-nudge reads this.
LAUNCH_WITH = "python3"

import argparse
import os
import posixpath
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

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
        extra = f" | unreadable: {', '.join(unusable)}" if unusable else ""
        return 2, (f"UNKNOWN: only one usable signal ({usable[0].name}) and it is flat. "
                   "One instrument cannot prove a stall - add a second, independent one "
                   f"(process CPU, io counters, a remote-side count).{extra}")

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


# A number standing on its own: not the 0 of `eth0`, not a piece of `v1.2.3`, not `42MB`.
_NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")

# Tokens that only mean something to a shell. With no shell they reach the first program as
# plain arguments, and it may still print a number - of the wrong thing.
_SHELL_OPERATORS = frozenset({"|", "||", "|&", "&", "&&", ";", ";;", ">", ">>", "<", "<<",
                              "2>", "2>>", "2>&1", "&>", "1>"})


def _split_windows(cmd: str) -> list[str]:
    """Split the way Windows itself does (CommandLineToArgvW); shlex eats the backslashes."""
    import ctypes  # noqa: PLC0415 - Windows-only API, never loaded elsewhere
    from ctypes import wintypes  # noqa: PLC0415 - same

    shell32 = ctypes.windll.shell32  # type: ignore[attr-defined]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    argc = ctypes.c_int(0)
    # A leading dummy argv[0]: the first token follows different quoting rules.
    argv = shell32.CommandLineToArgvW("x " + cmd, ctypes.byref(argc))
    if not argv:
        raise ValueError(f"cannot split command line {cmd!r}")
    try:
        return [argv[i] for i in range(1, argc.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(argv)  # type: ignore[attr-defined]


def split_command(cmd: str) -> list[str]:
    """argv for a --cmd string, split by this platform's rules. Raises ValueError if unsplittable.

    POSIX shlex reads a backslash as an escape, so an unquoted `C:\\Tools\\x.exe` would come back
    as `C:Toolsx.exe`; Windows has its own rules and no single quotes.
    """
    return _split_windows(cmd) if os.name == "nt" else shlex.split(cmd)


def command_argument(cmd: str) -> str:
    """argparse type for --cmd: refuse what cannot run as intended without a shell."""
    try:
        argv = split_command(cmd)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"cannot split {cmd!r}: {exc}") from exc
    if not argv:
        raise argparse.ArgumentTypeError("empty command")
    bad = [t for t in argv if t in _SHELL_OPERATORS or (len(t) > 1 and t.endswith(";"))]
    if bad:
        raise argparse.ArgumentTypeError(
            f"{cmd!r} uses shell syntax ({' '.join(bad)}) but runs with no shell; wrap it in one "
            "explicitly, e.g. sh -c '...', or quote the pipeline into the remote ssh argument")
    return cmd


def read_command_number(cmd: str) -> float | None:
    """First standalone number printed by a command that SUCCEEDED - the generic/remote sampler.

    Run WITHOUT a shell: the toolbox contract forbids shell=True, and a sampler needs no local
    shell anyway. A remote sampler still works, because the remote command travels as ONE
    quoted argument and the far side runs its own shell:
        --cmd "ssh host 'powershell -File C:\\count.ps1'"
    A non-zero exit is unreadable, never a reading: the number it printed may be an error
    count, a line number or a partial output.
    """
    try:
        argv = split_command(cmd)
    except ValueError:
        return None
    if not argv:
        return None
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    m = _NUMBER.search(p.stdout or "")
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
        rate = int(value * mult / 8)
    else:
        mult = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[scale]
        rate = int(value * mult)
    if rate <= 0:
        # 0 B/s is not a cap: curl gets no --limit-rate and rsync reads 0 as unlimited.
        raise ValueError(f"rate {text!r} is under 1 byte/s, which would remove the cap")
    return rate


def rate_argument(text: str) -> int:
    """argparse type for --rate: a bad rate is a usage error (exit 2), never a traceback."""
    try:
        return parse_rate(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def default_output_name(url: str) -> str:
    """The last PATH segment of `url`; the query and fragment may hold slashes of their own.

    Raises ValueError when the path names no file (a trailing slash, a bare host), because
    curl would then be handed an empty or directory-like -o.
    """
    name = posixpath.basename(urlsplit(url).path)
    if name in ("", ".", ".."):
        raise ValueError(f"cannot derive a file name from {url!r}; pass -o NAME")
    return name


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

    if args.pid and not Path("/proc").is_dir():
        print(f"check: --pid reads /proc, which only Linux has; pid{args.pid} will be unreadable",
              file=sys.stderr)
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

    --fail is what makes an HTTP error a failure: without it curl saves a 404 page as the
    file and exits 0, so the "download" succeeds with the wrong bytes.
    """
    argv = ["curl", "-L", "--fail", "--no-progress-meter", "--retry", "5", "--retry-delay", "5",
            "-C", "-", "-o", out, url]
    if rate_bps:
        argv[1:1] = ["--limit-rate", str(rate_bps)]
    return argv


def cmd_fetch(args: argparse.Namespace) -> int:
    if shutil.which("curl") is None:
        print("fetch: curl not found on PATH", file=sys.stderr)
        return 2
    rate = args.rate
    try:
        out = args.output or default_output_name(args.url)
    except ValueError as exc:
        print(f"fetch: {exc}", file=sys.stderr)
        return 2
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
        return 2
    rate = args.rate
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
    c.add_argument("--pid", type=int, help="watch this pid's CPU + io counters (Linux: /proc)")
    c.add_argument("--cmd", action="append", type=command_argument,
                   help="command printing a number, run with no shell (repeatable; a failing "
                        "command reads as unreadable; wrap a pipeline in sh -c '...'; use for "
                        "remote hosts via ssh)")
    c.add_argument("--interval", type=float, default=10.0, help="seconds between samples [10]")
    c.set_defaults(func=cmd_check)

    f = sub.add_parser("fetch", help="download resumably with a real rate cap")
    f.add_argument("url")
    f.add_argument("-o", "--output", help="output file [the URL path's last segment]")
    f.add_argument("--rate", type=rate_argument,
                   help="e.g. 8Mbit (bits) or 1M (MiB/s, curl-style)")
    f.set_defaults(func=cmd_fetch)

    u = sub.add_parser("push", help="send a file to another host, resumably, with a rate cap")
    u.add_argument("src", help="local path to send")
    u.add_argument("dest", help="[user@]host:/path/ destination")
    u.add_argument("--rate", type=rate_argument,
                   help="e.g. 8Mbit (bits) or 1M (MiB/s); converted to rsync KiB/s")
    u.add_argument("--ssh", help="ssh command, e.g. 'ssh -i /key -o BatchMode=yes'")
    u.set_defaults(func=cmd_push)
    return p


def _tolerate_console_encoding() -> None:
    """A cp1252 console cannot encode every file name; escape it, never crash."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="backslashreplace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _tolerate_console_encoding()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
