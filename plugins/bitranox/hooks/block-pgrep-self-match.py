#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard against the pgrep/pkill self-match.

`pgrep -f` / `pkill -f` match against /proc/*/cmdline, which INCLUDES the command
line of the shell running the check. So the checker can match itself: pgrep
reports a false positive, or pkill kills its own shell mid-command (truncated
output). Over SSH it kills the ssh shell (exit 255); locally it kills the script.

Three shapes cause it, and this hook blocks all three. The first two are read only
inside a `pgrep`/`pkill` call that carries `-f` (alone or bundled, as in `-af`) or
`--full`; the third is the same match written by hand.

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

3. HAND-ROLLED pkill -f.

       ps -eo pid=,args= | awk '/sleep 900/ {print $1}' | xargs -r kill

   A ps listing of full command lines (`args`/`cmd`/`command` in `-o`, or a
   default format that prints them: `aux`, `ax`, `-ef`) filtered by awk or grep on a
   pattern that matches this command's own text, with a `kill` consuming the PIDs
   (`| xargs kill`, `kill $(...)`, `| while read p; do kill $p; done`). The filter
   text is in the shell's argv, so the shell is selected. Read-only listings, a
   `comm`-only format, a pattern holding `$`, a pipeline that names `$$`, and one
   whose excluding filter drops this shell's line (`grep -v grep`, awk `!/awk/`:
   the command holds that word too) are left alone.

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

import shell_text
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


# --- shape 3: `ps ... | awk '/text/' | ... kill`, the hand-rolled pkill -f -------------------------
#
# A ps listing that shows the full command line, filtered on a literal and fed to kill, matches this
# shell exactly as `pkill -f` does: the filter text is in the shell's own argv, so the shell's PID
# is selected and killed (measured: exit 144 while stopping a backstop timer). Read on the same
# statement walk as the rest of the command, so a mention in an echo or heredoc is no call.
_PS_PROGRAMS = ("ps",)
_FILTER_PROGRAMS = frozenset({"awk", "gawk", "mawk", "nawk", "grep", "egrep"})
_LEADING_KEYWORDS = frozenset({"do", "then", "else", "{", "!", "time", "sudo", "command", "exec"})
# A kill counts only when it CONSUMES the listing: in the same pipeline (`| xargs kill`), in the
# body of a `| while read p` loop it feeds, around a `$(`/backtick substitution holding it
# (`kill $(...)`, `for p in $(...); do kill $p; done`, `pids=$(...); kill $pids`), through a
# process substitution redirected into a kill, an array read or a loop (`xargs kill < <(...)`,
# `readarray -t p < <(...)`, `done < <(...)`), or through a FILE the listing is written to and a
# later kill reads (`> /tmp/p; kill $(cat /tmp/p)`). A distance window was tried first and blocked
# read-only listings beside an unrelated kill (`kill 4242; ps aux | grep myserver`), since nothing
# it measured said the PIDs reach the kill.
_SUBSTITUTION_OPENERS = frozenset({"$(", "`", "<("})
_LOOP_OPENERS = frozenset({"for", "while", "until", "select"})
_ASSIGNED_NAME = re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=$")
_FORMAT_OPTIONS = frozenset({"-o", "o", "-O", "O", "--format"})
# ps options whose NEXT word is their value (a process name, user, PID list, sort key). Read as a
# bare word, `ps -C sleep`'s `sleep` looked like a run of BSD format letters, so a comm-only
# listing was taken for a full-command-line one.
# Checked against procps-ng 4.0.4 ps(1): `-N` is --deselect and takes NO value (read as one, it
# swallowed the `-f` after it), and there is no `-k` (only BSD `k` and --sort).
_PS_VALUE_OPTIONS = frozenset({
    "-C", "-G", "-U", "-g", "-p", "-q", "-s", "-t", "-u", "-D",
    "--pid", "--ppid", "--sid", "--user", "--User", "--group", "--Group", "--sort", "--tty",
    "--quick-pid", "--cols", "--columns", "--rows", "--lines", "--width", "--date-format",
    "p", "q", "t", "U", "k",
})
_CMDLINE_FIELD = re.compile(r"(?:^|[,=\s])(?:args|cmd|command)\b")
_AWK_REGEX = re.compile(r"(?<![\w)\]])/((?:\\.|[^/\n])+)/")
_GREP_VALUE_OPTIONS = frozenset({"-m", "-A", "-B", "-C", "--max-count", "--label"})


def _program_words(segment, tool_name):
    """The argv of a pipeline element from its program word on, leading loop keywords dropped."""
    words = argv_for_match(segment.strip().lstrip("(").strip(), tool_name or "Bash")
    while words and words[0] in _LEADING_KEYWORDS:
        words = words[1:]
    return words


def _program(words, tool_name):
    return basename_for_tool(words[0], tool_name).lower() if words else ""


def _ps_shows_cmdline(args):
    """True when this ps prints each process's full command line, not only its name."""
    formats = []
    for index, word in enumerate(args):
        if word in _FORMAT_OPTIONS and index + 1 < len(args):
            formats.append(args[index + 1])
        elif word.startswith("--format="):
            formats.append(word.partition("=")[2])
        elif re.match(r"-[a-zA-Z]*o", word) and not word.startswith("--"):
            tail = word[word.index("o") + 1:]
            formats.append(tail if tail else (args[index + 1] if index + 1 < len(args) else ""))
    if formats:
        return any(_CMDLINE_FIELD.search(value) for value in formats)
    # Default formats: BSD letters (`aux`, `ax`) print COMMAND with its arguments, and so does -f.
    return any((word.isalpha() and not word.startswith("-")) or
               (word.startswith("-") and not word.startswith("--") and "f" in word.lower())
               for word in _ps_option_words(args))


def _ps_option_words(args):
    """`args` without the values of ps's value-taking options (`-C NAME`, `-u USER`, `p PID`)."""
    words, skip = [], False
    for word in args:
        if skip:
            skip = False
            continue
        words.append(word)
        skip = word in _PS_VALUE_OPTIONS
    return words


def _filter_patterns(words, tool_name):
    """(pattern, ignore_case, fixed, excluding) for each pattern of an awk or grep element.

    EXCLUDING patterns matter as much as selecting ones: `grep -v grep` and awk's `!/awk/` drop
    this shell's own line, because its command line holds that very word - the common idiom that
    makes a hand-rolled kill safe. None for a filter that cannot be read (patterns from a file).
    """
    program = _program(words, tool_name)
    args = words[1:]
    if program.endswith("awk"):
        index = 0
        while index < len(args) and args[index].startswith("-"):
            if args[index] in ("-f", "--file"):
                return None
            index += 2 if args[index] in ("-F", "-v") else 1
        if index >= len(args):
            return []
        text = args[index]
        return [(m.group(1), False, False, text[:m.start()].rstrip().endswith("!"))
                for m in _AWK_REGEX.finditer(text)]
    found, operands, ignore_case, fixed, excluding = [], [], False, program == "fgrep", False
    index = 0
    while index < len(args):
        word = args[index]
        if word in ("-e", "--regexp") and index + 1 < len(args):
            found.append(args[index + 1])
            index += 2
            continue
        if word in ("-f", "--file"):
            return None
        if word in _GREP_VALUE_OPTIONS:
            index += 2
            continue
        if word.startswith("--"):
            excluding = excluding or word == "--invert-match"
            ignore_case = ignore_case or word == "--ignore-case"
            fixed = fixed or word == "--fixed-strings"
        elif word.startswith("-") and word != "-":
            excluding = excluding or "v" in word
            ignore_case = ignore_case or "i" in word
            fixed = fixed or "F" in word
        else:
            operands.append(word)
        index += 1
    patterns = found or operands[:1]
    return [(p, ignore_case, fixed, excluding) for p in patterns]


def _matches_shell(pattern, ignore_case, fixed, haystack):
    """What `pattern` matches in this shell's own command line, or None (also for `$` text)."""
    if not pattern or _EXPANSION.search(pattern):
        return None
    return _pattern_leak(re.escape(pattern) if fixed else pattern, ignore_case, haystack)


def _kills(words, tool_name):
    """True when this element runs kill, directly or through xargs."""
    if _program(words, tool_name) == "xargs":
        rest = [w for w in words[1:] if not w.startswith("-")]
        return bool(rest) and basename_for_tool(rest[0], tool_name).lower() == "kill"
    return _program(words, tool_name) == "kill"


def _loop_body_kills(segments, start, tool_name):
    """True when a kill runs in the loop body that starts at `segments[start]`, up to its `done`."""
    depth = 1
    for _separator, element in segments[start:]:
        raw = argv_for_match(element.strip(), tool_name or "Bash")
        if raw and raw[0] in _LOOP_OPENERS:
            depth += 1
        if raw and raw[0] == "done":
            depth -= 1
            if depth == 0:
                return False
        if _kills(_program_words(element, tool_name), tool_name):
            return True
    return False


def _expands(words, name):
    """True when a word expands `$name`, `${name}` or an element of it (`${name[@]}`)."""
    reference = re.compile(r"\$\{?" + re.escape(name) + r"(?![A-Za-z0-9_])")
    return any(reference.search(word) for word in words)


def _later_kill_expands(segments, start, name, tool_name):
    """True when a kill at or after `segments[start]` expands `name`."""
    return any(_kills(words, tool_name) and _expands(words, name)
               for words in (_program_words(e, tool_name) for _s, e in segments[start:]))


# `readarray`/`mapfile` and `read` store what they read in a variable; these of their options take
# a value that is NOT that variable (read's `-a NAME` is left out on purpose: its value IS one).
_ARRAY_READERS = {"readarray": "dnOsuCc", "mapfile": "dnOsuCc", "read": "dnNptui"}


def _read_names(words, tool_name):
    """The variables a `readarray`/`mapfile`/`read` statement fills, else an empty list."""
    value_letters = _ARRAY_READERS.get(_program(words, tool_name))
    if value_letters is None:
        return []
    names, skip = [], False
    for word in words[1:]:
        if word.startswith("<"):
            break                                   # the redirection the data comes in through
        if skip:
            skip = False
        elif word.startswith("-"):
            skip = word[-1] in value_letters
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", word):
            names.append(word)
    return names


def _loop_before_kills(segments, done_index, tool_name):
    """True when a kill runs in the loop body that ENDS at the `done` in `segments[done_index]`."""
    depth = 1
    for _separator, element in reversed(segments[:done_index]):
        if _kills(_program_words(element, tool_name), tool_name):
            return True
        raw = argv_for_match(element.strip(), tool_name or "Bash")
        if raw and raw[0] == "done":
            depth += 1
        if raw and raw[0] in _LOOP_OPENERS:
            depth -= 1
            if depth == 0:
                return False
    return False


def _statement_feeds_kill(segments, index, words, tool_name):
    """True when the statement `words` at `segments[index]`, which reads the PIDs, hands them on to
    a kill: it is one, it is the `done` of a loop that kills, or it stores them in a variable a
    later kill expands."""
    if _kills(words, tool_name):
        return True                                # xargs kill < <(ps ...), xargs kill < FILE
    if words and words[0] == "done":
        return _loop_before_kills(segments, index, tool_name)
    return any(_later_kill_expands(segments, index + 1, name, tool_name)
               for name in _read_names(words, tool_name))


def _substitution_consumed(segments, index, tool_name):
    """True when the `$(`/backtick substitution opening at `segments[index]` is fed to a kill."""
    separator, _segment = segments[index]
    if index == 0 or separator not in _SUBSTITUTION_OPENERS:
        return False
    before = segments[index - 1][1]
    words = _program_words(before, tool_name)
    if _kills(words, tool_name):
        return True                                # kill $(ps ...)
    if words and words[0] == "for":
        return _loop_body_kills(segments, index + 1, tool_name)
    if _statement_feeds_kill(segments, index - 1, words, tool_name):
        return True                                # done < <(ps ...), readarray -t p < <(ps ...)
    assigned = _ASSIGNED_NAME.search(before.rstrip("\"'"))     # pids=$( or pids="$(
    if assigned is None:
        return False
    return _later_kill_expands(segments, index + 1, assigned.group(1), tool_name)


# A redirection that writes the listing to a file: `> F`, `>> F`, `>| F`, or the same attached.
_WRITE_REDIRECTION = re.compile(r"^1?>>?\|?(.*)$", re.DOTALL)


def _handoff_file(element_words, tool_name):
    """The file the last element of a listing's pipeline writes (`> F`, `| tee F`), else None."""
    if _program(element_words, tool_name) == "tee":
        operands = [w for w in element_words[1:] if not w.startswith("-")]
        return operands[0] if operands else None
    for at, word in enumerate(element_words):
        written = _WRITE_REDIRECTION.match(word)
        if written is None:
            continue
        target = written.group(1) or (element_words[at + 1] if at + 1 < len(element_words) else "")
        return target or None
    return None


def _reads_file(words, path):
    """True when a statement names `path` as an operand or as a `<` input (`< F`, `<F`).

    The target of an output redirection (`kill 1 > F`) is written, not read, so it is not counted.
    """
    previous = ""
    for word in words:
        if re.sub(r"^\d*<", "", word) == path and not _WRITE_REDIRECTION.match(previous):
            return True
        previous = word
    return False


def _file_handoff_consumed(segments, after, path, tool_name):
    """True when a statement from `segments[after]` on reads `path` and passes its PIDs to a kill:
    `kill $(cat F)`, `xargs kill < F`, `cat F | xargs kill`, `done < F`, `readarray -t p < F`."""
    for index in range(after, len(segments)):
        separator, element = segments[index]
        words = _program_words(element, tool_name)
        if not _reads_file(words, path):
            continue
        if separator in _SUBSTITUTION_OPENERS and _substitution_consumed(segments, index, tool_name):
            return True
        if _statement_feeds_kill(segments, index, words, tool_name):
            return True
        if _kill_consumes(segments, index, _pipeline_after(segments, index, tool_name), tool_name):
            return True
    return False


def _pipeline_after(segments, index, tool_name):
    """The argv of each element piped from `segments[index]` on, up to the first other separator."""
    pipeline = []
    for separator, element in segments[index + 1:]:
        if separator != "|":
            break
        pipeline.append(_program_words(element, tool_name))
    return pipeline


def _kill_consumes(segments, index, pipeline, tool_name):
    """True when a kill receives the PIDs the ps at `segments[index]` lists."""
    if any(_kills(element, tool_name) for element in pipeline):
        return True                                # ps ... | xargs kill
    if pipeline and pipeline[-1] and pipeline[-1][0] == "while":
        return _loop_body_kills(segments, index + len(pipeline) + 1, tool_name)
    if _substitution_consumed(segments, index, tool_name):
        return True
    last = pipeline[-1] if pipeline else _program_words(segments[index][1], tool_name)
    path = _handoff_file(last, tool_name)
    if path is None or "$" in path:
        return False
    return _file_handoff_consumed(segments, index + len(pipeline) + 1, path, tool_name)


def ps_kill_leaks(executed, haystack, tool_name=None):
    """Shape 3: a full-cmdline ps filtered on text this command carries, whose PIDs reach kill.

    `executed` is where the pipeline is read (data regions blanked), `haystack` the raw command the
    filter is matched against, for the reason `bracket_leaks` gives. A pattern holding an
    expansion is skipped (argv holds it unexpanded), and so is a pipeline that excludes `$$`.
    """
    segments, previous = [], 0
    for at, segment in iter_segments(executed, tool_name):
        segments.append((executed[previous:at], segment))
        previous = at + len(segment)
    leaked = []
    for index, (_separator, segment) in enumerate(segments):
        words = _program_words(segment, tool_name)
        if _program(words, tool_name) not in _PS_PROGRAMS or not _ps_shows_cmdline(words[1:]):
            continue
        pipeline = _pipeline_after(segments, index, tool_name)
        if any("$$" in word for element in pipeline for word in element):
            continue
        if not _kill_consumes(segments, index, pipeline, tool_name):
            continue
        filters = [_filter_patterns(element, tool_name) for element in pipeline
                   if _program(element, tool_name) in _FILTER_PROGRAMS]
        if any(f is None for f in filters):
            continue
        patterns = [p for f in filters for p in f]
        if any(excluding and _matches_shell(pattern, case, fixed, haystack) is not None
               for pattern, case, fixed, excluding in patterns):
            continue                               # the shell's own line is filtered out
        for pattern, case, fixed, excluding in patterns:
            match = None if excluding else _matches_shell(pattern, case, fixed, haystack)
            entry = f"{pattern} -> {match}"
            if match is not None and entry not in leaked:
                leaked.append(entry)
    return leaked


_PS_CALL = re.compile(r"(?<![\w-])ps(?![\w.-])")


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

    # Fast path: only guard commands that call pgrep/pkill, or ps.
    if not re.search(_PROGRAM, commands) and not _PS_CALL.search(commands):
        return 0

    # An explicit self-exclusion means the caller already handled it. Read before the search
    # operands are blanked: the exclusion IS a grep, and its `$$` is one of those operands.
    if re.search(r"grep\s+-vw\s+[\"']?\$\$", executed):
        return 0

    leaked = bracket_leaks(commands, haystack)
    plain = plain_f_patterns(commands)
    by_ps = ps_kill_leaks(executed, haystack, tool_name)
    if not leaked and not plain and not by_ps:
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
    if by_ps:
        msg += [
            "",
            "HAND-ROLLED pkill -f: a ps listing of full command lines, filtered on text this",
            "command carries and fed to kill. This shell's own command line holds that text, so",
            "its PID is selected and killed exactly as `pkill -f` would:",
        ]
        msg += [f"  {x}" for x in by_ps]
    msg += [
        "",
        "Fix, best first:",
        "  - do not match on a command line at all - use a signal that cannot:",
        "    systemctl is-active <unit> | a pidfile + kill -0 <pid> |",
        "    a listening port via ss -ltnH | grep -c :PORT | readlink /proc/<pid>/exe;",
        "  - identify the process by what it IS, not its argv: procsig in",
        "    bitranox:compuse-toolbox (--exe, --comm, a pidfile or a port);",
        "  - kill by PID, or use `pkill -x <name>` / `pgrep -x <name>` (matches comm,",
        "    not the full cmdline, so this shell cannot match);",
        "  - if you must use -f: bracket the first char ([n]ginx) AND keep that keyword",
        '    out of every echo/printf label in the same command; or add | grep -vw "$$".',
    ]
    return shell_text.refuse("\n".join(msg))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
