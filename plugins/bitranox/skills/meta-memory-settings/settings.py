#!/usr/bin/env python3
"""View / set / reset the bitranox layered-memory knobs (informed-consent decisions).

All knobs live in one machine-local config, `~/.claude/.bitranox-memory.json`. A decision recorded
here is applied automatically thereafter - the hooks/skills never re-ask. Thin wrapper over
self_improve_signals (the single source of truth), like the meta-dream-tree cadence CLI.

Usage:
  settings.py view                 print every knob and its current value
  settings.py set <key> <value>    set one knob (validated against the known schema)
  settings.py reset                restore all knobs to the recommended defaults

Exit codes: 0 done; 1 the config could not be written (nothing was saved); 2 usage error, an
unknown key or value, or an existing config file that is not UTF-8 text or not a JSON object (left
untouched).

Pure standard library.
"""

import sys
from pathlib import Path

# self_improve_signals lives in the plugin's hooks dir: skills/meta-memory-settings -> skills -> bitranox -> hooks
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))

import self_improve_signals as sig  # noqa: E402


# The knobs whose value is one of a fixed set. Without this the CLI stored anything it was given:
# `set dream_mode of` (the realistic typo for `off`) wrote the literal string and exited 0, leaving
# a config that every reader then falls back to a default on, silently and forever.
ENUM_CHOICES = {
    "dream_mode": ("off", "auto", "propose"),
    "privacy": ("open", "walled"),
    "promotion": ("corroborated", "eager"),
    "skill_placement": ("lowest", "user", "project"),
    "mcp_search": ("off", "auto"),
    "classifier_backend": ("off", "jev"),
    "classifier_stop_signal": ("off", "shadow"),
    "classifier_skill_router": ("off", "shadow"),
    "classifier_recall_rerank": ("off", "shadow"),
}

_TRUE_WORDS = ("1", "true", "yes", "on")
_FALSE_WORDS = ("0", "false", "no", "off")


def _coerce(key, raw):
    """Coerce a string value to the type of that knob's default (bool / int / list / str).
    A list knob accepts a JSON array (`["/a","/b"]`) or a comma/os.pathsep-separated string.

    Raises ValueError on a value the knob cannot hold, so a typo is refused rather than stored."""
    default = sig.DEFAULT_CONFIG[key]
    if key in ENUM_CHOICES:
        value = str(raw).strip()
        if value not in ENUM_CHOICES[key]:
            raise ValueError("%s must be one of: %s (got %r)"
                             % (key, ", ".join(ENUM_CHOICES[key]), value))
        return value
    if isinstance(default, bool):  # bool BEFORE int (bool is an int subclass)
        word = str(raw).strip().lower()
        if word not in _TRUE_WORDS + _FALSE_WORDS:
            raise ValueError("%s must be one of: %s (got %r)"
                             % (key, ", ".join(_TRUE_WORDS + _FALSE_WORDS), str(raw).strip()))
        return word in _TRUE_WORDS
    if isinstance(default, list):
        return _coerce_list(key, raw)
    if isinstance(default, int):
        return _coerce_int(key, raw)
    return str(raw)


# (low, high) inclusive; None = unbounded. A negative or zero percentage made the handover threshold
# 1 token, so the handover offer fired on every turn; context_window 0 means "detect", and anything
# between 1 and 999 cannot be a real model window.
INT_BOUNDS = {
    "context_handover_pct": (1, 100),
    "context_handover_cap": (1, None),
    "context_window": (1000, None),
}
_INT_SPECIAL = {"context_window": (0,)}


def _coerce_int(key, raw):
    value = int(raw)                                  # ValueError on a non-integer
    if value in _INT_SPECIAL.get(key, ()):
        return value
    low, high = INT_BOUNDS.get(key, (None, None))
    if (low is not None and value < low) or (high is not None and value > high):
        special = "".join(" or %d" % v for v in _INT_SPECIAL.get(key, ()))
        span = "%s..%s" % (low, "" if high is None else high)
        raise ValueError("%s must be in %s%s (got %d)" % (key, span, special, value))
    return value


def _coerce_list(key, raw):
    """A JSON array or a comma/os.pathsep-separated string of non-empty strings.

    Every element must be a non-blank STRING: `str()` turned a JSON null into the path "None", and
    an empty string became Path("."), the cwd, which also displaced the $HOME default because the
    list was then non-empty. discovery_roots entries must also be rooted (absolute, or ~-relative):
    a relative root resolves against whatever directory a hook happens to run in."""
    import json as _json
    import os as _os
    s = str(raw).strip()
    if s.startswith("["):
        parsed = _json.loads(s)                       # ValueError (JSONDecodeError) on bad JSON
        if not isinstance(parsed, list):
            raise ValueError("expected a JSON list")
        bad = [x for x in parsed if not isinstance(x, str) or not x.strip()]
        if bad:
            raise ValueError("every element must be a non-empty string (got %r)" % (bad[0],))
        values = [x.strip() for x in parsed]
    else:
        values = [part.strip() for part in s.replace(_os.pathsep, ",").split(",") if part.strip()]
    if key == "discovery_roots":
        unrooted = [v for v in values if not Path(_os.path.expanduser(v)).anchor]
        if unrooted:
            raise ValueError("every root must be an absolute or ~-relative path (got %r)"
                             % unrooted[0])
    return values


def _print_config(cfg):
    for k in sorted(cfg):
        print("%s = %s" % (k, cfg[k]))


def _config_problem():
    """Why the existing config file cannot be used, or None when it is absent or a JSON object.

    `load_config` falls back to the defaults on a corrupt file, which is right for a hook but
    wrong here: `view` then showed defaults the user never chose, and the next `set` wrote those
    defaults over every choice the damaged file still held."""
    import json as _json
    p = sig._config_path()
    try:
        text = p.read_text(encoding="utf-8-sig")
    except (FileNotFoundError, NotADirectoryError):   # no config can exist there: nothing to protect
        return None
    except OSError as exc:
        return "cannot read %s: %s" % (p, exc)
    except UnicodeDecodeError as exc:
        # Decoded exactly as load_config decodes it, so "readable" means the same thing on both
        # sides: a file the hooks read as the defaults is one this CLI refuses, never one it shows
        # as the defaults or overwrites with them. A UTF-16 file lands here too.
        return ("%s is not UTF-8 text (%s); re-save it as UTF-8, or delete the file to start "
                "from the defaults" % (p, exc))
    try:
        parsed = _json.loads(text)
    except ValueError as exc:
        parsed, why = None, str(exc)
    else:
        why = "the top level is %s, not an object" % type(parsed).__name__
    if isinstance(parsed, dict):
        return None
    return ("%s is not a valid config (%s); fix the JSON by hand, or delete the file to start "
            "from the defaults" % (p, why))


def _save_and_print(updates):
    try:
        cfg = sig.save_config(updates, strict=True)
    except OSError as exc:
        print("not saved: %s" % exc, file=sys.stderr)
        return 1
    _print_config(cfg)
    return 0


def _run_set(key, raw):
    if key not in sig.DEFAULT_CONFIG:
        print("unknown key %r; known: %s" % (key, ", ".join(sorted(sig.DEFAULT_CONFIG))),
              file=sys.stderr)
        return 2
    try:
        value = _coerce(key, raw)
    except ValueError as exc:
        # surface WHICH values are legal - "bad value" alone leaves the caller guessing
        print("bad value for %s: %s" % (key, exc), file=sys.stderr)
        return 2
    return _save_and_print({key: value})


USAGE = "usage: settings.py [view | set <key> <value> | reset]"
# The exact argument count per verb. Leftovers used to be ignored, so `reset --dry-run` really
# reset and `set classifier_model jev 2025` stored "jev" - both exiting 0.
_ARGC = {"view": 1, "reset": 1, "set": 3}


def _reconfigure_stdout():
    """A cp1252 console (bare `python3` on Windows) cannot encode every value a knob may hold; the
    UnicodeEncodeError then came AFTER the write, so `set` reported failure for a stored value and
    `view` crashed on every run. Escape instead of crashing. Guarded: a replaced stream may lack it."""
    try:
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError, OSError):
        pass


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    argv = argv or ["view"]
    cmd = argv[0]
    if _ARGC.get(cmd) != len(argv):
        print(USAGE, file=sys.stderr)
        return 2
    problem = _config_problem()
    if problem:
        print(problem, file=sys.stderr)
        return 2
    if cmd == "view":
        _print_config(sig.load_config())
        return 0
    if cmd == "reset":
        return _save_and_print(dict(sig.DEFAULT_CONFIG))
    return _run_set(argv[1], argv[2])


if __name__ == "__main__":
    _reconfigure_stdout()
    sys.exit(main())
