#!/usr/bin/env python3
"""PreToolUse(Bash) guard: stop text-editing a STRUCTURED file (JSON/YAML/TOML/XML) with sed.

Editing structured config as raw text is the recurring `no-hand-edit-config-json` footgun: a `sed -i`
silently corrupts structure, hits the wrong match, or churns formatting. The right tool is the bitranox
edit skill for that format (`files-edit-json` / `files-edit-yml` / `files-edit-xml` / `files-edit-toml`),
which round-trips through a parser and re-validates.

Two tiers:
  - BLOCK (exit 2): an in-place text editor (`sed -i` / `gsed -i` / `perl -i`) whose argv targets a
    `.json/.yaml/.yml/.toml/.xml` file. High precision - only fires when such a command is at a command
    position (first token of a segment), so a quoted "sed -i x.json" inside an `echo` does not trip it.
  - WARN (exit 0, stderr): a `>`/`>>` redirection onto one of those files (often legitimate generation,
    so only a nudge, never a block).

Fail-open: any parse/IO error -> exit 0 (a broken guard must never wedge a turn). Pure standard library;
launched via run-python.sh so it works on Windows too.
"""
import json
import re
import shlex
import sys

STRUCTURED_EXT = (".json", ".yaml", ".yml", ".toml", ".xml")
SEP = re.compile(r"&&|\|\||[;\n|]")
INPLACE_CMDS = {"sed", "gsed", "perl"}
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
REDIRECT = re.compile(r">>?\s*['\"]?(?P<f>[^\s'\";|&]+\.(?:json|ya?ml|toml|xml))\b", re.I)

EDIT_SKILLS = "files-edit-json / files-edit-yml / files-edit-xml / files-edit-toml"


def _targets_structured(tokens):
    """True if any argv token names a structured-config file (quotes stripped)."""
    for t in tokens:
        bare = t.strip("'\"")
        if bare.lower().endswith(STRUCTURED_EXT):
            return bare
    return None


def _has_inplace(cmd, tokens):
    """True if the argv carries an in-place flag for this editor."""
    if cmd == "perl":
        return any(t == "-i" or t.startswith("-i") for t in tokens) and any("-p" in t or "-n" in t for t in tokens)
    # sed / gsed: -i, -i.bak, --in-place
    return any(t == "-i" or t.startswith("-i") or t == "--in-place" or t.startswith("--in-place") for t in tokens)


def assess(command):
    """Pure: classify a shell command. Returns (action, file, message); action in {block, warn, None}."""
    for segment in SEP.split(command):
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        # skip leading ENV=val assignments to find the real command
        argv = [t for t in tokens if not ASSIGN.match(t)]
        if not argv:
            continue
        cmd = argv[0].split("/")[-1]  # basename, so /usr/bin/sed -> sed
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
    action, _file, message = assess(command)
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
