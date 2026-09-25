#!/usr/bin/env bash
# run-python.sh - find a working Python 3 and exec it with the given script + args.
#
# Two callers, two contracts, chosen by the FIRST argument:
#   bash run-python.sh <script>.py [args...]          CLI / gate / skill step: LOUD by default
#   bash run-python.sh --hook <script>.py [args...]   hooks.json registration: fail-OPEN
#
# When the shim itself cannot run the script (the script is missing, no Python 3 interpreter,
# an unexpected shell) a CLI caller gets exit 3 and a stderr line, so a mistyped path in a gate
# never reads as a clean pass. A hook must never wedge a turn, so `--hook` turns the same
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
# a hook launch without BITRANOX_RUN_PYTHON_STRICT, which exits 0 so the turn goes on.
_degrade() {
  echo "run-python.sh: $1" >&2
  if [ -n "$_hook_mode" ] && [ -z "$BITRANOX_RUN_PYTHON_STRICT" ]; then exit 0; fi
  exit 3
}

# This shim is designed for Git Bash (Git for Windows) on Windows, and the native
# bash on macOS/Linux. WSL bash mounts Windows under /mnt/c and resolves a *Linux*
# python, and Cygwin uses different path mounts - the native-path/cygpath design
# below assumes Git Bash. Under an unexpected shell, say so and degrade rather than misbehave.
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*|Linux|Darwin) : ;;
  *) _degrade "unexpected shell '$(uname -s 2>/dev/null)'; script not run." ;;
esac

# Self-document a missing script arg instead of erroring obscurely.
[ -n "$1" ] && [ -f "$1" ] || _degrade "script not found: ${1:-<none>}"

# Windows Python defaults to cp1252; force UTF-8 for all IO. PYTHONUTF8 (PEP 540,
# 3.7+) covers modern interpreters; PYTHONIOENCODING is the classic companion that
# also fixes older/edge interpreters on a German-locale Windows box. No-op elsewhere.
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Git Bash passes POSIX paths (/c/Users/...) that a native python.exe misreads as
# <drive>:\c\Users\... Convert absolute args to native Windows form when cygpath exists
# (a Git Bash builtin; the command -v guard makes this a no-op on macOS/Linux).
if command -v cygpath >/dev/null 2>&1; then
  converted=()
  for a in "$@"; do
    case "$a" in
      /*) converted+=("$(cygpath -w "$a")") ;;
      *)  converted+=("$a") ;;
    esac
  done
  set -- "${converted[@]}"
fi

_is_py3() { "$@" -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; }

for cmd in python3 python "py -3"; do
  # shellcheck disable=SC2086
  if _is_py3 $cmd; then
    # shellcheck disable=SC2086
    exec $cmd "$@"
  fi
done

_degrade "no Python 3 interpreter found (tried python3, python, py -3); script not run."
