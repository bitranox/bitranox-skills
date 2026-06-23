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

# Windows Python defaults to cp1252; force UTF-8 for all IO (PEP 540). No-op elsewhere.
export PYTHONUTF8=1

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

# No Python 3 found: degrade silently. A Stop hook must never wedge the turn.
echo "self-improve: no Python 3 interpreter found (tried python3, python, py -3); gate skipped." >&2
exit 0
