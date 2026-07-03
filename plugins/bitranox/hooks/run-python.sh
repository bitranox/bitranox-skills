#!/usr/bin/env bash
# run-python.sh - find a working Python 3 and exec it with the given script + args.
#
# Claude Code runs hook commands through bash on every desktop platform (Git Bash
# on Windows), so hooks.json invokes this shim:
#   bash "${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh" "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py" [args...]
#
# The hard part is finding Python, not finding bash:
#   - python3 is canonical on macOS/Linux; on Windows it is usually the Microsoft
#     Store stub, which exits non-zero in a non-TTY subprocess - the probe skips it.
#   - python is the python.org install on Windows (and Python 2 on some EOL Linux,
#     guarded by the >= 3 check).
#   - py -3 is the Windows Python launcher.
# Approach adapted from Anthropic's claude-plugins-official sg-python.sh.
set -e

# Degrade path. HOOKS must never wedge a turn, so the default is fail-OPEN (exit 0 after a stderr
# note). A DELIBERATE caller (e.g. the dream running memory_engine.py) sets BITRANOX_RUN_PYTHON_STRICT=1
# to fail LOUD instead: the same conditions then exit non-zero (3) so the failure cannot pass silently.
_degrade() {
  echo "self-improve: $1" >&2
  if [ -n "$BITRANOX_RUN_PYTHON_STRICT" ]; then exit 3; fi
  exit 0
}

# This shim is designed for Git Bash (Git for Windows) on Windows, and the native
# bash on macOS/Linux. WSL bash mounts Windows under /mnt/c and resolves a *Linux*
# python, and Cygwin uses different path mounts - the native-path/cygpath design
# below assumes Git Bash. If launched under an unexpected shell, skip loudly to
# stderr rather than misbehave (still exit 0; a Stop hook must never wedge a turn).
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*|Linux|Darwin) : ;;
  *) _degrade "unexpected shell '$(uname -s 2>/dev/null)'; gate skipped." ;;
esac

# Self-document a missing script arg instead of erroring obscurely.
[ -n "$1" ] && [ -f "$1" ] || _degrade "gate script not found: ${1:-<none>}"

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

# No Python 3 found. Fail-open for hooks; fail-loud (exit 3) under BITRANOX_RUN_PYTHON_STRICT.
_degrade "no Python 3 interpreter found (tried python3, python, py -3); gate skipped."
