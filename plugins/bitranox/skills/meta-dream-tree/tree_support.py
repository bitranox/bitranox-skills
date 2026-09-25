"""Two things every tool in this skill must do exactly the same way, so they live in one place.

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

Pure standard library. Not a CLI.
"""
from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

__all__ = ["STORE_DIR", "store_anchor", "utf8_stdio"]

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
