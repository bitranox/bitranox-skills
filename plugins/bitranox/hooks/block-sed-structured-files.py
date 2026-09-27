#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: stop text-editing a STRUCTURED file (JSON/YAML/TOML/XML) with sed.

Editing structured config as raw text is the recurring `no-hand-edit-config-json` footgun: a `sed -i`
silently corrupts structure, hits the wrong match, or churns formatting. The right tool is the bitranox
edit skill for that format (`files-edit-json` / `files-edit-yml` / `files-edit-xml` / `files-edit-toml`),
which round-trips through a parser and re-validates.

Two tiers:
  - BLOCK (exit 2): an in-place text editor (`sed -i` / `gsed -i` / `perl -i`) whose argv targets a
    `.json/.yaml/.yml/.toml/.xml` file. High precision - only fires when such a command is at a command
    position (first token of a segment), so a quoted "sed -i x.json" inside an `echo` does not trip it.
Heredoc bodies are stripped before either tier runs: a body is text being written, not a
command, so a document or script that merely mentions `sed -i x.json` must not be blocked.

  - WARN (exit 0, stderr): a `>`/`>>` redirection onto one of those files (often legitimate generation,
    so only a nudge, never a block).

Fail-open: any parse/IO error -> exit 0 (a broken guard must never wedge a turn). Pure standard library;
launched via run-python.sh so it works on Windows too.
"""
import json
import re
import sys

import shell_text
from shell_text import SEP, mask_data_regions, strip_heredoc_bodies

STRUCTURED_EXT = (".json", ".yaml", ".yml", ".toml", ".xml")
INPLACE_CMDS = {"sed", "gsed", "perl"}
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
REDIRECT = re.compile(r">>?\s*['\"]?(?P<f>[^\s'\";|&]+\.(?:json|ya?ml|toml|xml))\b", re.I)

EDIT_SKILLS = "files-edit-json / files-edit-yml / files-edit-xml / files-edit-toml"

# Launchers that RUN the command after them, so the editor is not argv[0]: `sudo sed -i x.json`,
# `env LC_ALL=C sed -i ...`. shell_text's git guards step over the same set for the same reason;
# `command` and `exec` are added because they, too, run the next word as the program.
_LAUNCHERS = shell_text._COMMAND_PREFIXES | {"command", "exec"}

# Perl switches whose ARGUMENT is the rest of their cluster: in `-Mlib=inc` the `i` belongs to the
# module name, and in `-I/opt/lib` to the path, so neither is the in-place switch.
_PERL_ARG_SWITCHES = frozenset("eEMmIxdDFC")


def _targets_structured(tokens):
    """True if any argv token names a structured-config file (quotes stripped)."""
    for t in tokens:
        bare = t.strip("'\"")
        if bare.lower().endswith(STRUCTURED_EXT):
            return bare
    return None


def _perl_cluster_has(token, wanted):
    """True if the single-dash switch cluster `token` holds one of the switch letters in `wanted`.

    Perl bundles switches, so `-pi` is `-p -i` and `-lpi` is `-l -p -i`. The walk stops at a switch
    that takes the rest of the cluster as its argument (`-Mlib=inc`), and at anything that is not a
    letter or digit, so an `-i` extension (`-pi.bak`) is still read as `-i`.
    """
    if not token.startswith("-") or token.startswith("--"):
        return False
    for char in token[1:]:
        if char in wanted:
            return True
        if char in _PERL_ARG_SWITCHES or not char.isalnum():
            return False
    return False


def _has_inplace(cmd, tokens):
    """True if the argv carries an in-place flag for this editor."""
    if cmd == "perl":
        return (any(_perl_cluster_has(t, "i") for t in tokens)
                and any(_perl_cluster_has(t, "pn") for t in tokens))
    # sed / gsed: -i, -i.bak, --in-place
    return any(t == "-i" or t.startswith("-i") or t == "--in-place" or t.startswith("--in-place") for t in tokens)


def _editor_index(argv, tool_name):
    """Index of the in-place editor a leading launcher runs (`sudo sed ...`), else 0.

    Only after a KNOWN launcher, and only within the same bounded look-ahead the git guards use, so
    the scan stays a statement walk: `timeout 30 ssh host 'sed -i x.json'` keeps the quoted remote
    command as one token, whose basename is never `sed`.
    """
    if shell_text.basename_for_tool(argv[0], tool_name) not in _LAUNCHERS:
        return 0
    limit = min(len(argv), 1 + shell_text._PREFIX_SCAN_LIMIT)
    for at in range(1, limit):
        if shell_text.basename_for_tool(argv[at], tool_name) in INPLACE_CMDS:
            return at
    return 0


def assess(command, tool_name="Bash"):
    r"""Pure: classify a shell command. Returns (action, file, message); action in {block, warn, None}.

    `tool_name` picks BOTH the splitting language and the path-separator rules. This guard decides
    whether argv[0] names an in-place editor, so a PowerShell `C:\tools\sed.exe` has to survive
    the split AND reduce to `sed` - either half missing and the guard declines to fire on exactly
    what it exists to block.
    """
    # A heredoc body is DATA being written, not a command the shell will run. Scanning it
    # makes this guard fire on a script or document that merely CONTAINS a `sed -i x.json`
    # line - which is how it blocked a probe being written about this very footgun, twice.
    # The command-position check alone does not cover it: `&&` inside a body splits into
    # segments whose first token really is `sed`.
    command = strip_heredoc_bodies(command or "")
    # Split on the length-preserving MASKED text: a `;` inside a quoted string separates nothing,
    # and splitting there manufactured a sed invocation out of an `echo` argument.
    masked = mask_data_regions(command, tool_name=tool_name)
    starts = [0] + [m.end() for m in SEP.finditer(masked)]
    ends = [m.start() for m in SEP.finditer(masked)] + [len(command)]
    for segment in [command[a:b] for a, b in zip(starts, ends)]:
        try:
            tokens = shell_text.split_for_tool(segment, tool_name)
        except ValueError:
            tokens = segment.split()
        # skip leading ENV=val assignments to find the real command
        argv = [t for t in tokens if not ASSIGN.match(t)]
        if not argv:
            continue
        argv = argv[_editor_index(argv, tool_name):]
        cmd = shell_text.basename_for_tool(argv[0], tool_name)
        if cmd in INPLACE_CMDS and _has_inplace(cmd, argv[1:]):
            target = _targets_structured(argv[1:])
            if target:
                return ("block", target,
                        f"Refusing to edit {target} with {cmd} -i: editing a structured file as text is the "
                        f"no-hand-edit-config footgun (silent corruption / wrong match / format churn). Use the "
                        f"bitranox edit skill for that format ({EDIT_SKILLS}) - load -> edit the object -> dump "
                        f"-> re-validate. For a one-off, a small Python `json`/`rtoml`/`ruamel.yaml` script does "
                        f"the same.")
    m = REDIRECT.search(command)
    if m:
        return ("warn", m.group("f"),
                f"Redirecting into {m.group('f')} overwrites a structured file as raw text. If this is an "
                f"edit (not fresh generation), prefer the {EDIT_SKILLS} skill so the result is parsed and "
                f"validated.")
    return (None, None, "")


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0
    action, _file, message = assess(command, event.get("tool_name") or "Bash")
    if action == "block":
        sys.stderr.write("STRUCTURED-FILE GUARD: " + message + "\n")
        return 2  # PreToolUse: non-zero blocks the tool call and feeds stderr back to the model
    if action == "warn":
        sys.stderr.write("STRUCTURED-FILE GUARD (warning): " + message + "\n")
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
