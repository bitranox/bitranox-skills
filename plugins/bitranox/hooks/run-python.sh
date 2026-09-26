#!/usr/bin/env bash
# run-python.sh - find a working Python 3 and exec it with the given script + args.
#
# Two callers, two contracts, chosen by the FIRST argument:
#   bash run-python.sh <script>.py [args...]          CLI / gate / skill step: LOUD by default
#   bash run-python.sh --hook <script>.py [args...]   hooks.json registration: fail-OPEN
#
# When the shim itself cannot run the script (the script is missing or unreadable, no Python 3
# interpreter, an unexpected shell, a failed path conversion) a CLI caller gets exit 3 and a stderr
# line, so a mistyped path in a gate never reads as a clean pass. A hook must never wedge a turn, so `--hook` turns the same
# conditions into exit 0 after the stderr line. Neither mode ever produces exit 2 on its own (the
# code Claude Code treats as a block); a script's OWN exit code, 2 included, always passes through.
# BITRANOX_RUN_PYTHON_STRICT=1 forces the loud contract in both modes.
#
# Claude Code runs hook commands through bash on every desktop platform (Git Bash
# on Windows), so hooks.json invokes this shim:
#   bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh" --hook "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py"
#
# The hard part is finding Python, not finding bash:
#   - python3 is canonical on macOS/Linux; on Windows it is usually the Microsoft
#     Store stub, which exits non-zero in a non-TTY subprocess - the probe skips it.
#   - python is the python.org install on Windows (and Python 2 on some EOL Linux,
#     guarded by the >= 3 check).
#   - py -3 is the Windows Python launcher.
# Approach adapted from Anthropic's claude-plugins-official sg-python.sh.
set -e

_hook_mode=""
if [ "$1" = "--hook" ]; then
  _hook_mode=1
  shift
fi

# Master kill-switch (DEV ONLY). BITRANOX_HOOKS_OFF=1, set at SESSION LAUNCH, silences every plugin
# hook in this one place (all hooks are launched through this shim with --hook). It disables the
# guards, sweeps, recall, capture, and session inject - never set it permanently. A deliberate CLI
# call (no --hook) is not a hook, so it still runs: skipping it with exit 0 would fake a clean run.
if [ -n "$_hook_mode" ] && [ -n "$BITRANOX_HOOKS_OFF" ]; then
  echo "run-python.sh: BITRANOX_HOOKS_OFF is set - hook skipped (dev kill-switch)." >&2
  exit 0
fi

# The shim could not run the script: always say so on stderr, then exit 3 (loud) unless this is
# a hook launch without BITRANOX_RUN_PYTHON_STRICT, which exits 0 so the turn goes on. The code is
# decided once here because the Python bootstrap below degrades with the same one.
_degrade_rc=3
if [ -n "$_hook_mode" ] && [ -z "$BITRANOX_RUN_PYTHON_STRICT" ]; then _degrade_rc=0; fi
_degrade() {
  echo "run-python.sh: $1" >&2
  exit "$_degrade_rc"
}

# Git Bash (Git for Windows) is the supported Windows shell; native bash on macOS/Linux is the
# other target. Cygwin is accepted best-effort and untested: it has cygpath, so the conversion
# below plausibly works. WSL reports Linux to uname and cannot be told apart from it here. Any
# other kernel name is an unexpected shell: say so and degrade rather than misbehave.
case "$(uname -s 2>/dev/null)" in
  MINGW* | MSYS* | CYGWIN* | Linux | Darwin) : ;;
  *) _degrade "unexpected shell '$(uname -s 2>/dev/null)'; script not run." ;;
esac

# Self-document a missing or unreadable script arg instead of erroring obscurely. The bootstrap
# below re-checks at the moment python opens it, so this is the clean message, not the guarantee.
[ -n "$1" ] && [ -f "$1" ] || _degrade "script not found: ${1:-<none>}"
[ -r "$1" ] || _degrade "script not readable: $1"

# Windows Python defaults to cp1252; force UTF-8 for all IO. PYTHONUTF8 (PEP 540,
# 3.7+) covers modern interpreters; PYTHONIOENCODING is the classic companion that
# also fixes older/edge interpreters on a German-locale Windows box. No-op elsewhere.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Git Bash passes POSIX paths (/c/Users/...) that a native python.exe misreads as
# <drive>:\c\Users\... Convert the SCRIPT path to native Windows form when cygpath exists
# (a Git Bash builtin; the command -v guard makes this a no-op on macOS/Linux). Only the script
# path: a later argument is the script's own business, and a slash-leading one need not be a path
# at all (a /regex/, a /flag).
if command -v cygpath >/dev/null 2>&1; then
  case "$1" in
    /*)
      _script=$(cygpath -w "$1") || _degrade "cygpath failed on the script path: $1"
      shift
      set -- "$_script" "$@"
      ;;
  esac
fi

# python itself exits 2 when it cannot open a script, and 2 is the code Claude Code treats as a
# block. The -f/-r checks above cannot close that: the file can vanish before python opens it, and
# python opens the cygpath result, not the path that was checked. So python is handed this
# bootstrap instead of the script. It runs the script as `python script.py` would (argv, __file__,
# __name__ == "__main__", sys.path[0] = the script's resolved directory), and when runpy fails to
# OPEN the script - no frame of the script ever ran - it degrades with the shim's own code. An
# OSError the script raises itself has the script's frame in its traceback and passes through.
# The degrade code arrives in an environment variable the bootstrap removes before the script runs.
# Loader frames are matched by their code's co_filename: runpy is a frozen module on 3.11+, so its
# frames read "<frozen runpy>" while runpy.__file__ names the .py on disk.
# Git Bash's MSYS runtime rewrites slash-bearing arguments to a native python.exe, but leaves alone
# any argument whose first whitespace comes before its first slash or backslash
# (msys2_path_conv.cc, convert()): keep the code starting with "import os, ..." so it passes intact.
_bootstrap='import os, runpy, sys
rc = int(os.environ.pop("_BITRANOX_RUN_PYTHON_DEGRADE_RC", "3"))
sys.argv = sys.argv[1:]
script = os.path.abspath(sys.argv[0])
if not getattr(sys.flags, "safe_path", False):
    sys.path[0] = os.path.dirname(os.path.realpath(script))
try:
    runpy.run_path(script, run_name="__main__")
except OSError as exc:
    pkgutil = sys.modules.get("pkgutil")
    loader = {"<string>", runpy.run_path.__code__.co_filename}
    if pkgutil is not None:
        loader.add(pkgutil.read_code.__code__.co_filename)
    tb = exc.__traceback__
    while tb is not None and tb.tb_frame.f_code.co_filename in loader:
        tb = tb.tb_next
    if tb is not None:
        raise
    sys.stderr.write("run-python.sh: cannot open script %s: %s; script not run.\n" % (sys.argv[0], exc.strerror or exc))
    sys.exit(rc)
'

_is_py3() { "$@" -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; }

for cmd in python3 python "py -3"; do
  # shellcheck disable=SC2086
  if _is_py3 $cmd; then
    # shellcheck disable=SC2086
    _BITRANOX_RUN_PYTHON_DEGRADE_RC=$_degrade_rc exec $cmd -c "$_bootstrap" "$@"
  fi
done

_degrade "no Python 3 interpreter found (tried python3, python, py -3); script not run."
