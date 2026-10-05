#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard against the pgrep/pkill self-match.

`pgrep -f` / `pkill -f` match against /proc/*/cmdline, which INCLUDES the command
line of the shell running the check. So the checker can match itself: pgrep
reports a false positive, or pkill kills its own shell mid-command (truncated
output). Over SSH it kills the ssh shell (exit 255); locally it kills the script.

Two shapes cause it, and this hook blocks both. Both are read only inside a
`pgrep`/`pkill` call that carries `-f` (alone or bundled, as in `-af`) or `--full`.

1. BRACKET LEAK.

       pgrep -f "[n]ginx"; echo "=== nginx running? ==="

   The bracket trick `[n]ginx` is meant to stop the pattern from matching the
   checker's own argv (the literal `[n]ginx` is not the regex `nginx`). But the
   SAME keyword appearing verbatim anywhere else in the command - an echo/printf
   label, a comment, a commit message, a heredoc body - re-introduces the literal,
   because the whole command string is the shell's own cmdline. The pattern is judged
   as the regex pgrep compiles, against that whole string: `[m]ake test` leaks only
   where `make test` appears, and an unbracketed alternative (`[a]x|b`) always leaks.

2. PLAIN LITERAL.

       ssh host 'pkill -f "iperf3 -s"'

   A `-f` pattern written as a plain literal ALWAYS self-matches: the shell's own
   cmdline contains that very literal. No bracket, no leak needed - the pattern
   itself is the leak.

A call is looked for only in text the shell will EXECUTE: heredoc bodies, `#`
comments, the message text of a git commit/tag/merge, the operands of echo/printf
and the other sinks `shell_text.strip_data_sink_statements` lists, and the pattern
and file operands of grep/egrep/fgrep/zgrep/rg (this guard's own list) are blanked
first. A `$(...)` or backtick substitution inside any of them still runs, so it is
kept, and so is an `rg --pre <command>`, which executes its value.

These forms are NOT blocked because they cannot self-match or already handle it:
  - a pattern containing `$` (`pkill -f "$name"`): argv holds the UNEXPANDED text,
    so the expanded value is not in the shell's own cmdline;
  - a bracket-trick pattern whose literal does not appear elsewhere (shape 1 only
    fires on the actual leak);
  - `pgrep`/`pkill` WITHOUT `-f`/`--full`, bracketed or not: matches comm, not the
    full cmdline, so a shell named bash/sh cannot match a program-name pattern.
    `-F`/`--pidfile` and `-L`/`--logpidfile` are not `-f` either;
  - a command that already excludes the current shell (`grep -vw "$$"`).

A pgrep/pkill named inside a quoted argument of any OTHER program - `ssh host
'pkill -f x'`, `xargs pkill -f x` - still reads as a call; most of those really run
it. Bracket its first letter to pass a mention that does not.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""

import collections
import json
import re
import sys

from shell_text import (
    argv_for_match,
    basename_for_tool,
    is_git_verb,
    iter_segments,
    mask_data_regions,
    past_command_prefix,
    strip_data_sink_statements,
    strip_heredoc_bodies,
)

# A pgrep/pkill invocation up to the next shell separator, so only the flags and
# pattern belonging to THIS call are read.
#
# The program name must be a whole TOKEN, not a substring. `\b` is not that test: a hyphen is a
# word boundary, so `\bpgrep\b` matched the FILENAME `block-pgrep-self-match` and the guard then
# read the rest of the line as that call's arguments. A leading `/` is allowed because
# `/usr/bin/pgrep` is a real invocation; a trailing `-`, `.` or word character is not, because
# `pgrep-self-match` and `pkill-notes.md` name files, not programs.
#
# A call also ends at an unquoted `)` or backtick: `$(pgrep -x a) $(pgrep -f "[a]b")` is two calls,
# and read as one the second call's flags and pattern were credited to the first. A quoted run is
# taken whole, so `pgrep -f "foo)"` keeps its `)`; an unterminated quote (the call sits inside an
# outer quote, as in `ssh host 'pgrep -f x'`) ends the call where it opens.
_PROGRAM = r"(?<![\w-])(?:pgrep|pkill)(?![\w.-])"
_INVOCATION = re.compile(_PROGRAM + r"""(?:[^|;&\n)`'"]|'[^'\n]*'|"[^"\n]*")*""")

_BRACKET_TOKEN = re.compile(r"\[[^\]]\][A-Za-z0-9_./@:+-]+")

# A git message argument (`-m`/`--message`, quoted or bare). Its TEXT is stored, never run. Kept
# beside the shared sink stripper because that one stops at `git -C <dir> commit` - the `-C` value is
# not a flag, so the statement is not recognised as a commit there - and knows no `tag` or `merge`.
#
# Applied ONLY inside a git statement whose verb takes a message: run over the whole command it
# rewrote the `-m zz` INSIDE a pgrep pattern (`pgrep -f "[a]b -m zz"`) to `-m X`, so the pattern the
# guard judged was not the one pgrep runs.
_COMMIT_MSG = re.compile(r"(?:-m|--message)(?:=|\s+)(?:\"[^\"]*\"|'[^']*'|\S+)")
_MESSAGE_VERBS = frozenset({"commit", "tag", "merge"})

# `$(` and a backtick RUN what they enclose, even inside a double-quoted message, so a message that
# carries one is left for the invocation search: `git commit -m "$(pgrep -f x | wc -l) up"` runs a
# real pgrep. A substitution inside SINGLE quotes runs nothing and is kept too, which errs toward a
# visible false block rather than a silent miss.
_RUNS_SUBSTITUTION = re.compile(r"\$\(|`")


def _blank_comments(text, tool_name):
    """`text` with every `#` comment turned into spaces, length preserved.

    `mask_data_regions` already decides which `#` starts a comment (not one inside quotes, not one
    mid-word) and masks exactly those to SPACES, while everything else it masks becomes filler. So
    a space in the mask where the text has none is a comment character, and nothing else changes.
    """
    masked = mask_data_regions(text, tool_name=tool_name or "Bash")
    return "".join(" " if mask == " " else char for char, mask in zip(text, masked))


def strip_data_bodies(cmd, tool_name=None):
    """Remove text the shell will not EXECUTE - heredoc bodies, comments, plain commit messages - so a
    command that merely DISCUSSES `pkill -f` is not read as invoking it.

    Heredoc bodies go through the shared `strip_heredoc_bodies`, which ends a body only at a line that
    IS the delimiter, as bash does; a body line merely starting with the tag stays body.
    """
    out = strip_heredoc_bodies(cmd)
    out = _blank_comments(out, tool_name)
    return _rewrite_git_messages(out, tool_name)


def _rewrite_git_messages(text, tool_name):
    """`text` with each git commit/tag/merge statement's message text replaced by `-m X`.

    Only those statements are touched: a `-m <word>` anywhere else - inside a pgrep pattern, as
    another program's option - is left exactly as written.
    """
    tool = tool_name or "Bash"
    pieces, pos = [], 0
    for at, segment in iter_segments(text, tool_name):
        if not is_git_verb(segment.strip().lstrip("(").strip(), _MESSAGE_VERBS, tool):
            continue
        pieces.append(text[pos:at])
        pieces.append(_COMMIT_MSG.sub(
            lambda m: m.group(0) if _RUNS_SUBSTITUTION.search(m.group(0)) else "-m X", segment))
        pos = at + len(segment)
    pieces.append(text[pos:])
    return "".join(pieces)


# Programs whose operands are a search PATTERN and FILE names: searched for, never executed. Decided
# for THIS guard only (2026-10-05, option B): shell_text's shared sink list stays echo/printf,
# because every guard consults it and grep there would change all of them at once.
_SEARCH_PROGRAMS = frozenset({"grep", "egrep", "fgrep", "zgrep", "rg"})

# rg's `--pre <command>` EXECUTES its value for every file, so such a statement is not inert.
_EXECUTING_SEARCH_OPTION = re.compile(r"^--pre(?:=|$)")


def _search_program_index(tokens, tool_name):
    """Index of grep/rg when that is the program this statement runs, else None.

    Walks past `NAME=value` assignments and the shared launcher set (`sudo`, `timeout 5`, ...), the
    same statement walk the git guards use - never a scan of the whole argv, which would read
    `ssh host 'grep x'` or `echo grep` as a search.
    """
    at = 0
    while at < len(tokens) and "=" in tokens[at] and not tokens[at].startswith("-"):
        at += 1
    if at >= len(tokens):
        return None
    if basename_for_tool(tokens[at], tool_name) in _SEARCH_PROGRAMS:
        return at
    return past_command_prefix(tokens, at, _SEARCH_PROGRAMS, tool_name)


def blank_search_operands(text, tool_name=None):
    """`text` with the operands of every grep/rg statement blanked, length preserved.

    `grep "pkill -f x" file` searches for that text; nothing in it runs. A statement carrying a
    `$(`/backtick substitution is left whole (the substitution runs), and so is one cut short by a
    substitution opening, and an `rg --pre` (it executes its value). The program word survives.
    """
    tool = tool_name or "Bash"
    out = list(text)
    for at, segment in iter_segments(text, tool_name):
        if _RUNS_SUBSTITUTION.search(segment) or _RUNS_SUBSTITUTION.match(text, at + len(segment)):
            continue
        tokens = argv_for_match(segment.strip().lstrip("(").strip(), tool)
        index = _search_program_index(tokens, tool)
        if index is None or any(_EXECUTING_SEARCH_OPTION.match(t) for t in tokens[index + 1:]):
            continue
        words = list(re.finditer(r"\S+", segment))
        if len(words) <= index:
            continue
        for position in range(at + words[index].end(), at + len(segment)):
            if out[position] != "\n":
                out[position] = " "
    return "".join(out)


def _pattern_leak(pattern, ignore_case, haystack):
    """The text in `haystack` that a bracket-trick `pattern` matches, or None when it matches none.

    pgrep compiles its pattern as an extended regex and matches it against each cmdline, so that
    is the test: the bracket form itself can never match its own text (`[n]ginx` needs an `n`
    followed by `ginx`, and its own spelling has a `]` there), so any match is a real leak. Judging
    a de-bracketed WORD instead cut `[m]ake test` at its space and blocked a command whose only
    `make` sat in `maketest.log`, which the regex `make test` never matches. A pattern Python's
    `re` cannot compile falls back to that word test, which errs toward a visible block.
    """
    try:
        found = re.compile(pattern, re.IGNORECASE if ignore_case else 0).search(haystack)
    except re.error:
        for tok in _BRACKET_TOKEN.findall(pattern):
            literal = tok[1] + tok[3:]  # drop the '[' and the ']'
            if literal in haystack:
                return literal
        return None
    return None if found is None else found.group(0)


# A `$` that starts an expansion, not an ERE anchor: the shell substitutes it, so argv holds the
# unexpanded text and what pgrep would run cannot be judged from the command.
_EXPANSION = re.compile(r"\$[\w{(]")


def bracket_leaks(cmd, haystack=None):
    """Shape 1: a bracket-trick pattern that still matches the command's own text elsewhere.

    The bracket form cannot match itself, so a match is always a real label/comment leak.

    TWO texts, and they must not be the same one. `cmd` is where INVOCATIONS are read, so it may
    have inert statements blanked - a pgrep merely named inside an `echo` is not a call. `haystack`
    is where the LEAKED LITERAL is searched for, and there the echo must survive, because an echo
    label is precisely what re-introduces the literal into the shell's own argv, which is what
    `pgrep -f` matches. Blanking it in both places deletes the finding: measured, it took down
    `pgrep -f "[n]ginx"; echo "=== nginx running? ==="`, this hook's own motivating case.

    Defaulting `haystack` to `cmd` keeps the single-argument form meaningful for a caller that has
    only one text.
    """
    haystack = cmd if haystack is None else haystack
    # Only patterns belonging to a real pgrep/pkill invocation can self-match. Scanning the whole
    # command reported ANOTHER command's bracket trick as a leak - `grep "[s]shd"` is grep's own
    # search pattern, and the bracket form there is correct usage, not a footgun.
    leaked = []
    for call in _INVOCATION.findall(cmd):
        full, ignore_case, pattern = _parse_call(_call_words(call))
        # Without -f/--full the call matches comm, the program name, never a command line, so no
        # literal elsewhere in the command can make it match the shell.
        if not full or pattern is None or not _BRACKET_TOKEN.search(pattern):
            continue
        if _EXPANSION.search(pattern):
            continue
        match = _pattern_leak(pattern, ignore_case, haystack)
        if match is not None:
            entry = f"{pattern} -> {match}"
            if entry not in leaked:
                leaked.append(entry)
    return leaked


# pgrep/pkill options that take a VALUE (procps-ng), short and long. The value is not the pattern:
# taking the token after `-f` for the pattern reported `pgrep -f -u root x` as `-f -u`.
_VALUE_SHORT = frozenset("dgGOPstuUFrq")
_VALUE_LONG = frozenset({
    "--delimiter", "--pgroup", "--group", "--older", "--parent", "--session", "--terminal",
    "--euid", "--uid", "--pidfile", "--runstates", "--ns", "--nslist", "--signal", "--queue",
    "--cgroup", "--env",
})
# pkill's signal forms (`-9`, `-TERM`, `-SIGKILL`) carry no value and select no pattern.
_SIGNAL = re.compile(r"-(?:\d+|SIG[A-Z0-9+-]+|[A-Z][A-Z0-9+-]+)$")


def _call_words(call):
    """The shell words of one pgrep/pkill call, quotes removed, ending where the call does.

    The call ends at an unquoted `)` or backtick as well as at a separator: inside `$(pgrep -f x)`
    the closer belongs to the substitution, and read as part of the call it was reported as the
    pattern `x)"`. An unterminated quote runs to the end of the text, which is how the call reads
    when it sits inside an outer quote (`ssh host 'pgrep -f x'`).

    A backslash-escaped quote is unescaped one level first: inside an outer double-quoted string
    (`ssh h "pgrep -f \\"[o]bs\\""`) it is a real quote to the shell that runs the call, and read
    literally it glued the backslashes onto the pattern.
    """
    call = call.replace('\\"', '"').replace("\\'", "'")
    words, cur, has_word, i, n = [], [], False, 0, len(call)
    while i < n:
        ch = call[i]
        if ch in "'\"":
            close = call.find(ch, i + 1)
            close = n if close < 0 else close
            cur.append(call[i + 1:close])
            has_word, i = True, close + 1
            continue
        if ch in ")`":
            break
        if ch.isspace():
            if has_word:
                words.append("".join(cur))
            cur, has_word = [], False
        else:
            cur.append(ch)
            has_word = True
        i += 1
    if has_word:
        words.append("".join(cur))
    return words


_LONG_AS_SHORT = {"--full": "f", "--ignore-case": "i"}


def _option_meaning(word):
    """(short letters the word switches on, takes_next) for one option word of a call's argv.

    `-f` counts alone or bundled (`-af`), and the long form only as exactly `--full`: "any long
    option containing an f" took `--pidfile` and `--logpidfile` for `-f`, and both read PIDs from a
    file and match no command line. Only WORDS are judged, so the `-` inside a hyphenated filename
    (`nudge-detector-footguns`) is never read as a flag.
    """
    if word.startswith("--"):
        name = word.split("=", 1)[0]
        letters = {_LONG_AS_SHORT[name]} if name in _LONG_AS_SHORT else set()
        return letters, name in _VALUE_LONG and "=" not in word
    if _SIGNAL.match(word):
        return set(), False
    letters = set()
    for pos, ch in enumerate(word[1:], 1):
        if ch in _VALUE_SHORT:
            return letters, pos == len(word) - 1   # a value attached to the bundle consumes nothing
        letters.add(ch)
    return letters, False


_Call = collections.namedtuple("_Call", "full ignore_case pattern")


def _parse_call(words):
    """A call's -f/--full and -i/--ignore-case switches and its pattern OPERAND (None when it has
    none), from its words, program name first."""
    letters, pattern, i, operands_only = set(), None, 1, False
    while i < len(words):
        word = words[i]
        i += 1
        if operands_only or not word.startswith("-") or word == "-":
            if pattern is None:
                pattern = word
            continue
        if word == "--":
            operands_only = True
            continue
        seen, takes_next = _option_meaning(word)
        letters |= seen
        i += 1 if takes_next else 0
    return _Call("f" in letters, "i" in letters, pattern)


def plain_f_patterns(cmd):
    """Shape 2: `-f` patterns that are plain literals, so the shell's argv self-matches.

    The pattern is the call's first OPERAND, found by walking its options and the values they
    take, never simply the token after `-f`.
    """
    found = []
    for call in _INVOCATION.findall(cmd):
        full, _ignore_case, pattern = _parse_call(_call_words(call))
        # No operand: nothing to reason about (a malformed or listing-only call). An EMPTY operand
        # is different - it is the worst pattern there is, matching every command line on the
        # box including this shell's - so it is reported, not skipped.
        if not full or pattern is None:
            continue
        if "$" in pattern:
            continue  # variable: argv holds the unexpanded text, cannot self-match
        if _BRACKET_TOKEN.search(pattern):
            continue  # bracket trick: shape 1 owns the leak case
        found.append(pattern)
    return found


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    # Two views of the command, because the two halves of this guard ask different questions.
    #
    # `haystack` is where a leaked literal is searched for, and it is the RAW command: the shell is
    # started with the whole command string, heredoc bodies, comments and commit messages included,
    # so all of it is in the cmdline `pgrep -f` matches. `commands` is what the invocation search
    # reads, and it keeps only what EXECUTES, so `echo \'pkill -f x\'` is not mistaken for a call.
    tool_name = data.get("tool_name")
    haystack = cmd
    executed = strip_data_sink_statements(strip_data_bodies(cmd, tool_name), tool_name)
    commands = blank_search_operands(executed, tool_name)

    # Fast path: only guard commands that call pgrep/pkill.
    if not re.search(_PROGRAM, commands):
        return 0

    # An explicit self-exclusion means the caller already handled it. Read before the search
    # operands are blanked: the exclusion IS a grep, and its `$$` is one of those operands.
    if re.search(r"grep\s+-vw\s+[\"']?\$\$", executed):
        return 0

    leaked = bracket_leaks(commands, haystack)
    plain = plain_f_patterns(commands)
    if not leaked and not plain:
        return 0

    msg = ["BLOCKED: pgrep/pkill would match the shell running this very command."]
    if plain:
        msg += [
            "",
            "PLAIN `-f` PATTERN. `-f` matches /proc/*/cmdline, and this shell's own",
            "cmdline contains the pattern literal, so it always matches itself:",
        ]
        msg += [f"  -f {p}" if p else
                '  -f ""   <- EMPTY pattern: matches EVERY process, including this shell'
                for p in plain]
    if leaked:
        msg += [
            "",
            "BRACKET TRICK DEFEATED by the same literal appearing contiguously elsewhere",
            "(usually an echo/printf label or comment), so the shell's own argv",
            "self-matches and pgrep returns a false positive (or pkill kills its shell):",
        ]
        msg += [f"  {x}" for x in leaked]
    msg += [
        "",
        "Fix, best first:",
        "  - do not match on a command line at all - use a signal that cannot:",
        "    systemctl is-active <unit> | a pidfile + kill -0 <pid> |",
        "    a listening port via ss -ltnH | grep -c :PORT | readlink /proc/<pid>/exe;",
        "  - kill by PID, or use `pkill -x <name>` / `pgrep -x <name>` (matches comm,",
        "    not the full cmdline, so this shell cannot match);",
        "  - if you must use -f: bracket the first char ([n]ginx) AND keep that keyword",
        '    out of every echo/printf label in the same command; or add | grep -vw "$$".',
    ]
    print("\n".join(msg), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
