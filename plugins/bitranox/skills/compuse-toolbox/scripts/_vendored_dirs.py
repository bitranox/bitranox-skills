# /// script
# requires-python = ">=3.10"
# ///
"""The directories a toolbox walk prunes: git's object store, vendored trees and tool caches.

One set for every walker (grep_all, conflict_scan), so the two cannot drift apart: each used to
carry its own copy, kept in step by a comment. Kept small and explicit on purpose - a broad skip
list would bring back the silent under-reporting grep_all exists to stop - and it names only
trees nobody edits: what git keeps for itself, what a package manager installs, what a tool caches.

A virtualenv is recognised two ways. By name prefix, because `.venv-win`, `.venv-3.12` and
`.venv-bmk` are venvs too and naming only `.venv` walked the rest as project files. And by its
`pyvenv.cfg` (PEP 405: every venv holds one at its root), because `venv/` and `env/` carry no
dotted name at all. The marker costs one stat per directory the walk reaches; a name rule is
checked first, so the common skips never pay it.

Standard library only, and loadable on 3.10: a sibling of scripts that may run under a project's
own interpreter. Imported by bare name, which works because running a script puts its own
directory first on sys.path, and the tests' conftest puts scripts/ there too.
"""

from __future__ import annotations

import os

__all__ = ["VENDORED_DIR_NAMES", "VENV_MARKER", "VENV_PREFIX", "is_vendored_dir",
           "prune_vendored"]

VENDORED_DIR_NAMES = frozenset({".git", "node_modules", "__pycache__", ".mypy_cache",
                                ".pytest_cache", ".ruff_cache"})
VENV_PREFIX = ".venv"
VENV_MARKER = "pyvenv.cfg"


def is_vendored_dir(parent: str, name: str) -> bool:
    """Whether the directory `name` inside `parent` is pruned from a walk.

    Examples:
        >>> is_vendored_dir("/nonexistent-parent", "node_modules")
        True
        >>> is_vendored_dir("/nonexistent-parent", ".venv-3.12")
        True
        >>> is_vendored_dir("/nonexistent-parent", "src")
        False
    """
    if name in VENDORED_DIR_NAMES or name.startswith(VENV_PREFIX):
        return True
    return os.path.isfile(os.path.join(parent, name, VENV_MARKER))


def prune_vendored(parent: str, dirnames: list[str]) -> None:
    """Drop every vendored directory from `dirnames` IN PLACE, as os.walk needs to skip them."""
    dirnames[:] = [d for d in dirnames if not is_vendored_dir(parent, d)]
