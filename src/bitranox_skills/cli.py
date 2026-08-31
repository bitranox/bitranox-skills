"""`bitranox-skills` - install the bundled skills into a Claude Code skills directory.

Installed with `uv tool install bitranox-skills`, which is why this module has no
third-party dependencies: a tool install that has to resolve anything can fail for reasons
that have nothing to do with the skills.

Scope note: this installs SKILLS only. The plugin's hooks need entries in settings.json,
and editing a user's settings from a CLI is a different and riskier job - `bitranox-skills
path` prints where the hooks live so they can be wired deliberately.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import PLUGIN_DIR, SKILLS_DIR, plugin_version, skill_names

__all__ = ["main", "default_destination"]

EXIT_OK = 0
EXIT_NO = 1
EXIT_ERROR = 2


def default_destination() -> Path:
    """Where Claude Code looks for personal skills."""
    return Path.home() / ".claude" / "skills"


def _emit(payload: dict[str, object], as_json: bool, human: str) -> None:
    """Machine-readable on request, prose otherwise; diagnostics never go to stdout."""
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(human)


def cmd_path(args: argparse.Namespace) -> int:
    payload = {
        "ok": True,
        "command": "path",
        "data": {"plugin": str(PLUGIN_DIR), "skills": str(SKILLS_DIR),
                 "hooks": str(PLUGIN_DIR / "hooks"), "version": plugin_version()},
    }
    _emit(payload, args.json, str(PLUGIN_DIR))
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    names = skill_names()
    payload = {"ok": True, "command": "list", "data": {"count": len(names), "skills": names}}
    _emit(payload, args.json, "\n".join(names))
    return EXIT_OK if names else EXIT_NO


def cmd_install(args: argparse.Namespace) -> int:
    dest = Path(args.dest).expanduser() if args.dest else default_destination()
    names = skill_names()
    if not names:
        print("no bundled skills found; the wheel is incomplete", file=sys.stderr)
        return EXIT_ERROR

    planned, skipped = [], []
    for name in names:
        target = dest / name
        # An existing directory is somebody's own copy until they say otherwise: overwriting
        # it silently is how a local edit disappears without a trace.
        (skipped if target.exists() and not args.force else planned).append(name)

    if not args.dry_run:
        try:
            dest.mkdir(parents=True, exist_ok=True)
            for name in planned:
                target = dest / name
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(SKILLS_DIR / name, target)
        except OSError as exc:
            print(f"install failed: {exc}", file=sys.stderr)
            return EXIT_ERROR

    if skipped and not args.json:
        print(f"skipped {len(skipped)} already present (use --force to overwrite)",
              file=sys.stderr)
    payload = {
        "ok": True,
        "command": "install",
        "data": {"destination": str(dest), "installed": planned, "version": plugin_version(),
                 "dry_run": bool(args.dry_run)},
        "skipped": skipped,
    }
    verb = "would install" if args.dry_run else "installed"
    _emit(payload, args.json, f"{verb} {len(planned)} skill(s) into {dest}")
    return EXIT_OK


class _VersionAction(argparse.Action):
    """Report the version only when asked.

    argparse's built-in `action="version"` takes the string EAGERLY, at parser construction,
    so passing plugin_version() there made every invocation read the bundled manifest -
    including `--help`, and including runs in a source checkout where the package data is
    not laid down and the read raises.
    """

    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        print(plugin_version())
        parser.exit()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bitranox-skills",
        description="Install the bitranox Claude Code skill collection.",
    )
    parser.add_argument("--version", action=_VersionAction, help="print the bundled version")
    parser.add_argument("--json", action="store_true",
                        help="emit a JSON envelope on stdout; diagnostics stay on stderr")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("path", help="print where the bundled plugin, skills and hooks live")
    sub.add_parser("list", help="list the bundled skill names")

    install = sub.add_parser("install", help="copy the skills into a Claude Code skills dir")
    install.add_argument("--dest", help=f"target directory (default: {default_destination()})")
    install.add_argument("--force", action="store_true", help="overwrite skills already there")
    install.add_argument("--dry-run", action="store_true", help="report the plan, change nothing")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {"path": cmd_path, "list": cmd_list, "install": cmd_install}
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return EXIT_ERROR
    try:
        return handler(args)
    except FileNotFoundError as exc:
        # The bundled manifest is missing: a source checkout, or a wheel built without the
        # force-include. Say which, rather than surfacing a traceback about a path.
        print(f"bundled plugin data not found ({exc}). This command needs an installed "
              f"copy: uv tool install bitranox-skills", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
