"""Three things every tool in this skill must do exactly the same way, so they live in one place.

1. **Find the store the ENGINE uses.** `memory_engine.py` reads and writes a level's bodies under
   `resolve_anchor(level) or level`: the TOPMOST ancestor carrying a `CLAUDE.md` AND a
   `.claude-memory/` store. A tool that instead walks up to the NEAREST store is diverted by a
   leftover mid-chain store (a decoy), and then backs up, scans or records a baseline against a
   store the engine never reads - while the real one goes unbacked-up. So the tools do not
   re-implement the walk: they call the engine's own resolver, handed in by the caller, and apply
   the engine's own fallback.
2. **Print without dying on a cp1252 console.** A bare `python3` on Windows writes to stdout in
   the ANSI code page, so one non-cp1252 character in a path or a transcript line raises
   UnicodeEncodeError halfway through the output and the tool exits 1, which every CLI here uses
   to mean a real finding. `hooks/run-python.sh` forces UTF-8, but a direct launch does not.
3. **Keep the --json contract on a usage error.** argparse's own `error()` prints usage text to
   stderr and exits 2, so a caller that asked for `--json` and parses stdout got nothing to parse.
   `EnvelopeArgumentParser` prints the exit-2 envelope `{ok: false, command, data, skipped,
   error}` on stdout first when a json flag is in argv, then lets argparse do the rest. It mirrors
   compuse-toolbox's `_cli_envelope.EnvelopeArgumentParser`; skills do not import across each
   other, because each one ships and runs on its own.

Pure standard library. Not a CLI.
"""

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

__all__ = ["STORE_DIR", "EnvelopeArgumentParser", "store_anchor", "utf8_stdio", "wants_json"]

_JSON_FLAGS: tuple[str, ...] = ("--json",)

STORE_DIR = ".claude-memory"


def store_anchor(start: Path | str, resolve: Callable[[str], object]) -> Path | None:
    """The dir whose `.claude-memory/` the engine uses for `start`, or None when it has none.

    `resolve` is the engine's `resolve_anchor` (from `uuid_store`), passed in so a tool bound to a
    particular engine keeps using THAT engine's rule. The fallback to `start` itself is the engine's
    too (`memory_engine._anchor`): with no `CLAUDE.md` anywhere above, a level is its own anchor.
    The answer is None rather than a guess when that dir holds no store, because a nearer store is
    exactly the one the engine would NOT read.

    Examples:
        >>> store_anchor("/", lambda p: None) is None
        True
    """
    here = Path(os.path.abspath(Path(start).expanduser()))
    found = resolve(str(here))
    anchor = Path(found) if found else here
    if not (anchor / STORE_DIR).is_dir():
        return None
    return anchor.resolve()


def utf8_stdio() -> None:
    """Make stdout and stderr write UTF-8, replacing what cannot be encoded instead of raising.

    Guarded: a stream that is not a TextIOWrapper (a test capture, a closed or detached stream)
    is left alone rather than crashing the tool before it has done anything.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            continue


def wants_json(argv: Sequence[str] | None, flags: Sequence[str] = _JSON_FLAGS) -> bool:
    """Whether a json flag appears among the options of `argv` (sys.argv[1:] when None).

    A token after a bare `--` is an operand, not an option, so it does not count.

    Args:
        argv: The argument list as given to the parser.
        flags: The flag spellings that select JSON output.

    Returns:
        True when one of `flags` (or `flag=value`) is present before any `--`.

    Examples:
        >>> wants_json(["scan", "--json"])
        True
        >>> wants_json(["--", "--json"])
        False
    """
    tokens = sys.argv[1:] if argv is None else argv
    for token in tokens:
        if token == "--":
            return False
        if any(token == flag or token.startswith(flag + "=") for flag in flags):
            return True
    return False


def _subcommand_name(prog: object) -> str:
    """The sub-command a sub-parser serves: argparse hands it prog as "<root prog> <name>"."""
    words = str(prog or "").split()
    return words[-1] if words else ""


class EnvelopeArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser whose usage errors also print the exit-2 envelope under a json flag.

    The root records argv once; a sub-parser made through `add_subparsers` reads that record,
    because it is handed only the tail of argv and a json flag typed before the sub-command would
    otherwise be missed. A sub-parser's envelope names its sub-command and the root's names
    `envelope_command`, matching the `command` field each tool prints on its other exits.

    Args:
        *args: Passed to argparse.ArgumentParser.
        envelope_command: The `command` field; defaults to the parser's prog.
        **kwargs: Passed to argparse.ArgumentParser.

    Examples:
        >>> EnvelopeArgumentParser(prog="tool").envelope_command
        'tool'
    """

    def __init__(self, *args: Any, envelope_command: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.envelope_command = envelope_command or self.prog
        self._envelope_root: EnvelopeArgumentParser = self
        self._envelope_argv: list[str] | None = None
        self._envelope_active: EnvelopeArgumentParser = self

    def parse_known_args(self, args: Sequence[str] | None = None,
                         namespace: argparse.Namespace | None = None) -> Any:
        root = self._envelope_root
        if root is self:
            self._envelope_argv = list(sys.argv[1:] if args is None else args)
            self._envelope_active = self
        else:
            # An unrecognized argument is reported by the ROOT after the sub-command parsed, so
            # the root needs to know which sub-command was chosen to name it in the envelope.
            root._envelope_active = self
        return super().parse_known_args(args, namespace)

    def add_subparsers(self, **kwargs: Any) -> Any:
        if "parser_class" not in kwargs:
            root = self._envelope_root
            cls = type(self)

            def make_child(**child_kwargs: Any) -> EnvelopeArgumentParser:
                child_kwargs.setdefault("envelope_command",
                                        _subcommand_name(child_kwargs.get("prog")))
                child = cls(**child_kwargs)
                child._envelope_root = root
                return child

            kwargs["parser_class"] = make_child
        return super().add_subparsers(**kwargs)

    def error(self, message: str) -> Any:
        root = self._envelope_root
        if wants_json(root._envelope_argv):
            named = root._envelope_active if self is root else self
            print(json.dumps({"ok": False, "command": named.envelope_command, "data": {},
                              "skipped": [], "error": message}, indent=2))
            sys.stdout.flush()
        return super().error(message)
