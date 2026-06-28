#!/usr/bin/env python3
"""View / set / reset the bitranox layered-memory knobs (informed-consent decisions).

All knobs live in one machine-local config, `~/.claude/.bitranox-memory.json`. A decision recorded
here is applied automatically thereafter - the hooks/skills never re-ask. Thin wrapper over
self_improve_signals (the single source of truth), like the meta-dream-project cadence CLI.

Usage:
  settings.py view                 print every knob and its current value
  settings.py set <key> <value>    set one knob (validated against the known schema)
  settings.py reset                restore all knobs to the recommended defaults

Pure standard library.
"""

import sys
from pathlib import Path

# self_improve_signals lives in the plugin's hooks dir: skills/meta-memory-settings -> skills -> bitranox -> hooks
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))

import self_improve_signals as sig  # noqa: E402


def _coerce(key, raw):
    """Coerce a string value to the type of that knob's default (bool / int / str)."""
    default = sig.DEFAULT_CONFIG[key]
    if isinstance(default, bool):
        return str(raw).strip().lower() in ("1", "true", "yes", "on")
    if isinstance(default, int):
        return int(raw)
    return str(raw)


def _print_config(cfg):
    for k in sorted(cfg):
        print("%s = %s" % (k, cfg[k]))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "view"

    if cmd == "view":
        _print_config(sig.load_config())
        return 0
    if cmd == "reset":
        _print_config(sig.save_config(dict(sig.DEFAULT_CONFIG)))
        return 0
    if cmd == "set":
        if len(argv) < 3:
            print("usage: settings.py set <key> <value>", file=sys.stderr)
            return 2
        key, raw = argv[1], argv[2]
        if key not in sig.DEFAULT_CONFIG:
            print("unknown key %r; known: %s" % (key, ", ".join(sorted(sig.DEFAULT_CONFIG))),
                  file=sys.stderr)
            return 2
        try:
            value = _coerce(key, raw)
        except ValueError:
            print("bad value %r for %s" % (raw, key), file=sys.stderr)
            return 2
        _print_config(sig.save_config({key: value}))
        return 0

    print("usage: settings.py [view|set <key> <value>|reset]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
