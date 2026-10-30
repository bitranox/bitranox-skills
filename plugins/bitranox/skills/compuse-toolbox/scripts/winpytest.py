# /// script
# requires-python = ">=3.14"
# ///
"""Ship a repo's committed tree to a Windows host over ssh and run its pytest suite there.

Testing a Windows-only path on a real Windows machine beats pushing and reading CI, but the
hand-rolled transfer fails in ways that cost a round trip each, because the remote shell of a
Windows OpenSSH server is cmd.exe, not a POSIX shell:

- `if exist X rmdir /s /q X & mkdir X` runs the mkdir only when X EXISTED: cmd puts every `&`
  after an `if` inside its body. So the mkdir is its own ssh call here.
- an scp destination with forward slashes (`C:/work/src.tar`) fails with `dest open ... Failure`;
  the destination is written with BACKSLASHES whatever form you give.
- PowerShell syntax sent to that cmd shell fails, so every remote command here is cmd syntax.

Steps: `git archive HEAD` to a local tar (uncommitted changes are NOT shipped, and a dirty tree is
named on stderr), `rmdir` the destination in one ssh call, `mkdir` it in the next, scp the tar, then
`cd /d DEST && tar -xf src.tar && [set "K=V" &&] uv run [--frozen] [--extra X] pytest ARGS`.
`--frozen` is added when the repo tracks a uv.lock. Every ssh and scp call carries `-i KEY`,
`BatchMode=yes` and `PreferredAuthentications=publickey`, so a refused key fails instead of
prompting.

The destination is deleted recursively before each run, so it is refused unless it is an absolute
`X:\\dir\\sub` path at least two levels deep, with no `..` and no quote: never a drive root or a
top-level folder such as `C:\\Users`.

Exit codes: 0 = pytest passed, 1 = pytest ran and tests failed (its rc 1 WITH its tally
line, or its short test summary under -qq), 2 = no verdict (a step before pytest failed, rc 1
with neither - cmd's errorlevel from a failed cd, tar or uv sync - or pytest exited 2-5:
interrupted, internal error, usage error, nothing collected; or ssh failed). `--json` prints `{ok, command, data, skipped}` with the raw pytest rc,
its summary line and the tail of its output.

Run:
  `uv run scripts/winpytest.py --host WINHOST --user USER --key ~/.ssh/KEY --dest 'C:\\work\\proj'`
  `uv run scripts/winpytest.py --host WINHOST --key K --dest C:/work/proj --env MODE=x -- -q tests/test_win.py`
"""

import argparse
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, EnvelopeArgumentParser, emit, guarded

__all__ = ["dest_problem", "execute", "pytest_ran", "pytest_summary", "windows_path"]

COMMAND = "winpytest"
_TAIL = 40
_CONNECT_TIMEOUT = "15"
_ABS_WIN = re.compile(r"^[A-Za-z]:\\")
_SUMMARY = re.compile(r"^=*\s*((?:\d+ [a-z]+(?:, )?)+ in [\d.]+s(?: \([^)]*\))?|no tests ran in [\d.]+s)"
                      r"\s*=*\s*$", re.MULTILINE)
_SHORT_SUMMARY = re.compile(r"^=+ short test summary info =+\s*$", re.MULTILINE)
# Any CSI escape (ESC [ params intermediates final), not just SGR colour: pytest with --color=yes
# (or PY_COLORS / FORCE_COLOR in the env) starts every rule line with one, which hides it from
# the `^=` anchors above, and a terminal-aware plugin may emit other CSI codes too.
_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

#: (rc, stdout, stderr) for an argv. The ssh/scp edge; injected so tests need no Windows host.
Runner = Callable[[list[str]], tuple[int, str, str]]


class StepFailed(Exception):
    """A step before pytest failed; the run has no verdict."""


def windows_path(path: str) -> str:
    """`path` with every forward slash as a backslash and no trailing separator. PURE."""
    text = path.replace("/", "\\")
    return text if re.fullmatch(r"[A-Za-z]:\\", text) else text.rstrip("\\")


def dest_problem(dest: str) -> str | None:
    """Why `dest` must not be deleted recursively, or None when it may be. PURE."""
    if not _ABS_WIN.match(dest):
        return "the destination must be an absolute Windows path such as C:\\work\\proj"
    parts = [p for p in dest[3:].split("\\") if p]
    if len(parts) < 2:
        return "the destination is deleted before each run, so it must be at least two levels deep"
    if ".." in parts or '"' in dest:
        return "the destination may hold neither '..' nor a double quote"
    return None


def _plain(text: str) -> str:
    """`text` without terminal escape sequences, so coloured pytest output parses. PURE."""
    return _CSI.sub("", text)


def pytest_summary(text: str) -> str | None:
    """The last pytest tally line (`3 passed, 1 skipped in 2.10s`), without its `=` rule. PURE."""
    found = _SUMMARY.findall(_plain(text))
    return found[-1].strip() if found else None


def _run(argv: list[str]) -> tuple[int, str, str]:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False)
    except OSError as exc:
        return 127, "", f"cannot run {argv[0]}: {exc}"
    return done.returncode, done.stdout, done.stderr


def _ssh_opts(key: str | None) -> list[str]:
    opts = ["-o", "BatchMode=yes", "-o", "PreferredAuthentications=publickey",
            "-o", f"ConnectTimeout={_CONNECT_TIMEOUT}"]
    return (["-i", key] if key else []) + opts


def _target(args: argparse.Namespace) -> str:
    return f"{args.user}@{args.host}" if args.user else args.host


def _step(runner: Runner, name: str, argv: list[str]) -> tuple[str, str]:
    rc, out, err = runner(argv)
    if rc != 0:
        raise StepFailed(f"step '{name}' exited {rc}: {(err or out).strip()[:300]}")
    return out, err


def _git_out(runner: Runner, repo: Path, *args: str) -> str:
    return _step(runner, "git " + args[0], ["git", "-C", str(repo), *args])[0]


def _pytest_command(args: argparse.Namespace, dest: str, frozen: bool) -> str:
    env = "".join(f'set "{pair}" && ' for pair in args.env)
    uv = ["uv", "run"] + (["--frozen"] if frozen else [])
    for extra in args.extra:
        uv += ["--extra", extra]
    pytest_args = subprocess.list2cmdline(args.pytest_args)
    return (f'cd /d "{dest}" && tar -xf src.tar && {env}{" ".join(uv)} pytest'
            + (f" {pytest_args}" if pytest_args else ""))


def _ship(args: argparse.Namespace, dest: str, runner: Runner, scratch: Path) -> bool:
    """Archive, clear, create and copy; returns whether the repo tracks a uv.lock."""
    repo = Path(args.repo).resolve()
    if _git_out(runner, repo, "status", "--porcelain", "--untracked-files=no").strip():
        print(f"{COMMAND}: warning: uncommitted changes in {repo} are NOT shipped "
              "(git archive HEAD); commit them to test them", file=sys.stderr)
    frozen = bool(_git_out(runner, repo, "ls-files", "--", "uv.lock").strip())
    tar = scratch / "src.tar"
    _git_out(runner, repo, "archive", "--format=tar", "-o", str(tar), "HEAD")
    ssh = ["ssh", *_ssh_opts(args.key), _target(args)]
    _step(runner, "rmdir", ssh + [f'if exist "{dest}" rmdir /s /q "{dest}"'])
    _step(runner, "mkdir", ssh + [f'mkdir "{dest}"'])
    _step(runner, "scp", ["scp", *_ssh_opts(args.key), str(tar), f"{_target(args)}:{dest}\\src.tar"])
    return frozen


def _parser() -> EnvelopeArgumentParser:
    p = EnvelopeArgumentParser(description=(__doc__ or COMMAND).splitlines()[0],
                               envelope_command=COMMAND, json_flags=("--json",))
    p.add_argument("--host", required=True, help="the Windows host (an ssh_config alias works)")
    p.add_argument("--user", help="the login user (default: ssh's own choice)")
    p.add_argument("--key", help="the private key file")
    p.add_argument("--repo", default=".", help="the repository whose HEAD is shipped (default: cwd)")
    p.add_argument("--dest", required=True, help="absolute Windows dir, two levels deep; DELETED "
                                                  "and recreated before each run")
    p.add_argument("--env", action="append", default=[], metavar="KEY=VALUE",
                   help="set in the remote cmd shell before pytest (repeatable)")
    p.add_argument("--extra", action="append", default=[], help="uv --extra to install (repeatable)")
    p.add_argument("--json", action="store_true", help="print one JSON envelope")
    p.add_argument("pytest_args", nargs="*", help="after `--`: arguments for pytest")
    return p


def pytest_ran(out: str) -> bool:
    """Whether pytest's own output shows it ran: a tally line, or (under -qq, which prints no
    tally) its short test summary header. PURE."""
    return pytest_summary(out) is not None or _SHORT_SUMMARY.search(_plain(out)) is not None


def _verdict(rc: int, ran: bool) -> int:
    # rc 1 is pytest's "tests failed" only when pytest's output shows it ran: the remote line is
    # `cd /d X && tar -xf ... && uv run pytest`, and cmd gives errorlevel 1 when cd, tar or uv's
    # resolve/sync fails, so a bare rc 1 does not prove pytest ever ran.
    if rc == 0:
        return EXIT_YES
    return EXIT_NO if rc == 1 and ran else EXIT_ERROR


def _no_verdict_reason(rc: int, host: str, ran: bool) -> str:
    if rc == 1 and not ran:
        return (f"the remote command exited 1 on {host} with no pytest tally or short summary: "
                "cd, tar or uv failed before pytest ran; no verdict")
    return f"pytest exited {rc} on {host}: no verdict"


def execute(argv: Sequence[str] | None = None, *, runner: Runner = _run) -> int:
    """The whole run, with the ssh/scp/git runner as a seam."""
    args = _parser().parse_args(argv)
    dest = windows_path(args.dest)
    bad_env = [pair for pair in args.env if "=" not in pair or '"' in pair]
    problem = dest_problem(dest) or (f"--env needs KEY=VALUE without quotes: {bad_env[0]}"
                                     if bad_env else None)
    if problem:
        return _fail(args, problem)
    with tempfile.TemporaryDirectory(prefix="winpytest-") as scratch:
        try:
            frozen = _ship(args, dest, runner, Path(scratch))
        except StepFailed as exc:
            return _fail(args, str(exc))
    rc, out, err = runner(["ssh", *_ssh_opts(args.key), _target(args),
                           _pytest_command(args, dest, frozen)])
    summary = pytest_summary(out)
    ran = pytest_ran(out)
    code = _verdict(rc, ran)
    data: dict[str, Any] = {"host": args.host, "dest": dest, "pytest_rc": rc, "summary": summary,
                            "tail": (out + err).splitlines()[-_TAIL:]}
    if args.json:
        return emit(code, COMMAND, data, error=None if code != EXIT_ERROR else
                    _no_verdict_reason(rc, args.host, ran))
    sys.stdout.write(out)
    sys.stderr.write(err)
    print(f"{COMMAND}: {_status_line(rc, args.host, summary, ran)}", file=sys.stderr)
    return code


def _status_line(rc: int, host: str, summary: str | None, ran: bool) -> str:
    if summary:
        return f"pytest exited {rc} on {host} ({summary})"
    if _verdict(rc, ran) == EXIT_ERROR:
        return _no_verdict_reason(rc, host, ran)
    return f"pytest exited {rc} on {host} (no summary line)"


def _fail(args: argparse.Namespace, message: str) -> int:
    if args.json:
        return emit(EXIT_ERROR, COMMAND, None, error=message)
    print(f"{COMMAND}: {message}", file=sys.stderr)
    return EXIT_ERROR


@guarded(COMMAND, json_flags=("--json",))
def main(argv: list[str] | None = None) -> int:
    """Run; an uncaught exception exits 2, never 1, which means 'tests failed'."""
    return execute(argv)


if __name__ == "__main__":
    sys.exit(main())
