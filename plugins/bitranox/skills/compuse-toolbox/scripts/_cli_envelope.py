# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""The one JSON envelope and exit-code boundary every compuse-toolbox jig shares.

Not a tool: a sibling module the jigs import by bare name (`from _cli_envelope import ...`), which
works under `uv run scripts/x.py` and `python3 scripts/x.py` alike because the script's own
directory is first on sys.path. The leading underscore is what keeps repo-gate's toolbox coverage
check from asking it for a nudge rule. Standard library only: a jig is run bare, with nothing
provisioned.

The exit-code standard it encodes:

    0  ran, and the answer is yes / nothing wrong          (EXIT_YES)
    1  ran, and the answer is no: a finding, a partial outcome   (EXIT_NO)
    2  could not run: bad input, missing tool, crash, unreadable or unwritable path, a refusal of
       the whole action                                       (EXIT_ERROR)

Under `--json` a jig prints `{ok, command, data, skipped}` on EVERY exit, 2 included, with an
optional `error` string; `ok` means "ran without error", so it is `exit != 2`. A 1 is therefore
`ok: true` - the tool worked and the answer was no - and a caller reads the verdict from the exit
code or from `data`, never from `ok`.

Three pieces make that hold on the paths a jig does not write by hand:

- `EnvelopeArgumentParser` prints the exit-2 envelope on stdout for an argparse usage error when a
  json flag is in argv (sub-commands included), then the usual usage text on stderr.
- `guarded` / `run_guarded` wrap `main`: an uncaught exception becomes one stderr line naming the
  type, the message and the raising frame, the envelope under `--json`, and exit 2 - never a
  traceback with Python's exit 1, which reads as "the answer is no".
- `emit` prints an envelope and returns the code, so `return emit(1, ...)` keeps the two in step.

Examples:
    >>> envelope_for_exit(1, "tool", {"n": 0})
    {'ok': True, 'command': 'tool', 'data': {'n': 0}, 'skipped': []}
    >>> envelope(False, "tool", error="no such file")["error"]
    'no such file'
    >>> wants_json(["--", "--json"])
    False
"""
from __future__ import annotations

import argparse
import functools
import json
import sys
import traceback
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any, TextIO

__all__ = [
    "EXIT_ERROR",
    "EXIT_NO",
    "EXIT_YES",
    "EnvelopeArgumentParser",
    "emit",
    "envelope",
    "envelope_for_exit",
    "guarded",
    "render",
    "run_guarded",
    "wants_json",
]

EXIT_YES = 0
EXIT_NO = 1
EXIT_ERROR = 2

#: The exit a Ctrl-C conventionally gets (128 + SIGINT); no envelope, since nothing was answered.
_EXIT_INTERRUPTED = 130

DEFAULT_JSON_FLAGS: tuple[str, ...] = ("--json",)


def envelope(ok: bool, command: str, data: Any = None, skipped: Iterable[str] = (),
             error: str | None = None) -> dict[str, Any]:
    """Build the envelope dict, keys in the order ok, command, data, skipped (then error).

    Args:
        ok: True when the run completed without error (exit 0 or 1), False on exit 2.
        command: The jig or sub-command name.
        data: The payload; None becomes {}. A list is kept as a list.
        skipped: Notes on what was not examined.
        error: A one-line reason; the key appears only when given.

    Returns:
        The envelope as a plain dict.
    """
    env: dict[str, Any] = {"ok": bool(ok), "command": command,
                           "data": {} if data is None else data, "skipped": list(skipped)}
    if error is not None:
        env["error"] = error
    return env


def envelope_for_exit(code: int, command: str, data: Any = None, skipped: Iterable[str] = (),
                      error: str | None = None) -> dict[str, Any]:
    """The envelope for an exit code: ok is `code != 2`.

    Args:
        code: The exit code the jig is about to return.
        command: As for `envelope`.
        data: As for `envelope`.
        skipped: As for `envelope`.
        error: As for `envelope`.

    Returns:
        The envelope as a plain dict.
    """
    return envelope(code != EXIT_ERROR, command, data, skipped, error)


def render(env: dict[str, Any], indent: int | None = 2) -> str:
    """Serialise an envelope. ASCII-escaped, so a cp1252 console or pipe cannot fail on it.

    Args:
        env: The envelope dict.
        indent: json.dumps indent; None for one line.

    Returns:
        The JSON text.
    """
    return json.dumps(env, indent=indent, ensure_ascii=True)


def emit(code: int, command: str, data: Any = None, *, skipped: Iterable[str] = (),
         error: str | None = None, indent: int | None = 2, file: TextIO | None = None) -> int:
    """Print the envelope for `code` and return `code`.

    Args:
        code: The exit code; decides `ok`.
        command: As for `envelope`.
        data: As for `envelope`.
        skipped: As for `envelope`.
        error: As for `envelope`.
        indent: As for `render`.
        file: Stream to print to; stdout when None (looked up at call time, so capture works).

    Returns:
        `code`, unchanged.

    Examples:
        >>> emit(0, "tool", indent=None)
        {"ok": true, "command": "tool", "data": {}, "skipped": []}
        0
    """
    print(render(envelope_for_exit(code, command, data, skipped, error), indent=indent),
          file=sys.stdout if file is None else file)
    return code


def wants_json(argv: Sequence[str] | None, flags: Sequence[str] = DEFAULT_JSON_FLAGS) -> bool:
    """Whether a json flag appears among the options of `argv` (sys.argv[1:] when None).

    A token after a bare `--` is an operand, not an option, so it does not count.

    Args:
        argv: The argument list as given to the parser.
        flags: The flag spellings that select JSON output.

    Returns:
        True when one of `flags` (or `flag=value`) is present before any `--`.
    """
    tokens = sys.argv[1:] if argv is None else argv
    for token in tokens:
        if token == "--":
            return False
        if any(token == flag or token.startswith(flag + "=") for flag in flags):
            return True
    return False


class EnvelopeArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser whose usage errors also print the exit-2 envelope under a json flag.

    Sub-parsers made through `add_subparsers` share the root's record of argv, so a json flag given
    before the sub-command still counts when the sub-command's own arguments are wrong.

    Args:
        envelope_command: The `command` field; defaults to the root parser's prog.
        json_flags: The flag spellings that select JSON output.
        *args: Passed to argparse.ArgumentParser.
        **kwargs: Passed to argparse.ArgumentParser.
    """

    def __init__(self, *args: Any, envelope_command: str | None = None,
                 json_flags: Sequence[str] = DEFAULT_JSON_FLAGS, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.envelope_command = envelope_command
        self.json_flags = tuple(json_flags)
        self._envelope_root: EnvelopeArgumentParser = self
        self._envelope_argv: list[str] | None = None

    def parse_known_args(self, args: Sequence[str] | None = None,
                         namespace: argparse.Namespace | None = None) -> Any:
        # Only the root records: a sub-parser is handed the tail of argv, which may not hold the
        # flag the caller actually typed.
        if self._envelope_root is self:
            self._envelope_argv = list(sys.argv[1:] if args is None else args)
        return super().parse_known_args(args, namespace)

    def add_subparsers(self, **kwargs: Any) -> Any:
        if "parser_class" not in kwargs:
            root = self._envelope_root
            cls = type(self)

            def make_child(**child_kwargs: Any) -> EnvelopeArgumentParser:
                child_kwargs.setdefault("envelope_command", root.envelope_command)
                child_kwargs.setdefault("json_flags", root.json_flags)
                child = cls(**child_kwargs)
                child._envelope_root = root
                return child

            kwargs["parser_class"] = make_child
        return super().add_subparsers(**kwargs)

    def error(self, message: str) -> Any:
        root = self._envelope_root
        if wants_json(root._envelope_argv, flags=self.json_flags):
            emit(EXIT_ERROR, root.envelope_command or root.prog, error=message)
        super().error(message)


def _raising_frame(exc: BaseException) -> str:
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return ""
    last = frames[-1]
    return f" (at {Path(last.filename).name}:{last.lineno} in {last.name})"


def run_guarded(fn: Callable[[Sequence[str] | None], int], argv: Sequence[str] | None = None, *,
                command: str, json_flags: Sequence[str] = DEFAULT_JSON_FLAGS) -> int:
    """Call `fn(argv)`, mapping any uncaught exception to exit 2 plus the envelope under --json.

    SystemExit passes through untouched (argparse's own 2, an explicit sys.exit). Ctrl-C returns
    130 with no envelope, since nothing was answered and 130 is not "ok".

    Args:
        fn: The jig's real main, taking argv and returning an exit code.
        argv: The argument list; None means sys.argv[1:].
        command: The `command` field and the stderr prefix.
        json_flags: The flag spellings that select JSON output.

    Returns:
        `fn`'s exit code, 2 on an uncaught exception, 130 on KeyboardInterrupt.
    """
    try:
        return fn(argv)
    except KeyboardInterrupt:
        return _EXIT_INTERRUPTED
    except Exception as exc:  # noqa: BLE001 - this IS the process boundary
        message = f"{type(exc).__name__}: {exc}"
        if wants_json(argv, flags=json_flags):
            emit(EXIT_ERROR, command, error=message)
        print(f"{command}: internal error: {message}{_raising_frame(exc)}", file=sys.stderr)
        return EXIT_ERROR


def guarded(command: str, *, json_flags: Sequence[str] = DEFAULT_JSON_FLAGS
            ) -> Callable[[Callable[..., int]], Callable[..., int]]:
    """Decorator form of `run_guarded` for `def main(argv=None) -> int`.

    Args:
        command: The `command` field and the stderr prefix.
        json_flags: The flag spellings that select JSON output.

    Returns:
        A decorator wrapping main in the exit-2 boundary.
    """
    def decorate(fn: Callable[..., int]) -> Callable[..., int]:
        @functools.wraps(fn)
        def wrapper(argv: Sequence[str] | None = None) -> int:
            return run_guarded(fn, argv, command=command, json_flags=json_flags)
        return wrapper
    return decorate
