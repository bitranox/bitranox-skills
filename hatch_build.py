"""Wheel build hook: force-include plugins/bitranox, skipping every gitignored, machine-local
path under it - a curated memory store, its pointer file, or another plugin's own state dir.

hatchling's `force-include` bypasses BOTH the project's own `exclude` config and its automatic
`.gitignore` consultation (`recurse_forced_files` only filters a small hardcoded set of VCS/cache
directory and file names), so a machine-local `CLAUDE.local.md`, `.claude-memory/` or
`.remember/` anywhere under `plugins/bitranox` always shipped in a LOCAL `uv build`, whatever the
working tree held.

`force-include` (rather than `only-include` + `sources`) is required here, not a style choice: it
is the one file-selection mechanism `WheelBuilder.build_editable_detection` never inspects (it
only walks `recurse_selected_project_files()`). Renaming `plugins/bitranox` to a different prefix
(`bitranox_skills/plugin`) through `sources` instead makes that detector read the rename as an
unsupported path REWRITE (https://github.com/pfmoore/editables/issues/20) and refuse every
`uv run` / `pip install -e`. So this hook keeps force-include, and computes its file list itself
so the excluded names never enter the mapping in the first place.

Pure standard library.
"""

from __future__ import annotations

import os

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

# Mirrors the gitignored, machine-local names that can appear anywhere under plugins/bitranox/
# (see .gitignore): the curated memory store, its legacy name, its pointer file, and another
# plugin's own state dir (not gitignored in THIS repo, but never something its wheel should ship).
EXCLUDE_NAMES = frozenset({
    "CLAUDE.local.md", ".claude-memory", ".claude-bx-selflearning", ".remember", "notes.md",
    ".plan",
})

TARGET_PREFIX = "bitranox_skills/plugin"


def plugin_force_include(root: str) -> dict[str, str]:
    """{absolute source file: wheel-relative target} for every file under `root`/plugins/bitranox
    whose name, or an ancestor directory's name, is not in `EXCLUDE_NAMES`."""
    source = os.path.join(root, "plugins", "bitranox")
    mapping: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_NAMES)
        for name in sorted(filenames):
            if name in EXCLUDE_NAMES:
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, source).replace(os.sep, "/")
            mapping[path] = "%s/%s" % (TARGET_PREFIX, rel)
    return mapping


class PluginTreeBuildHook(BuildHookInterface):
    """Populates `force_include` with `plugin_force_include`'s filtered, per-file mapping."""

    def initialize(self, version: str, build_data: dict) -> None:
        build_data["force_include"].update(plugin_force_include(self.root))
