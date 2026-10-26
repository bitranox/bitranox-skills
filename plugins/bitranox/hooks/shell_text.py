#!/usr/bin/env python3
"""Shared shell-command text handling for the command-scanning guards.

A guard that inspects a Bash command must judge COMMANDS, not data. A heredoc body is data: it is
text being written to a file or piped to a program, not something the shell will execute. Scanning
it makes a guard fire on prose that merely MENTIONS the footgun it guards - which blocks you from
writing the documentation, memory entry, or commit message that warns about that very footgun. This
repo has shipped that failure before, in more than one guard.

It lives here rather than in each guard because two copies had already drifted apart in wording and
would eventually drift in behaviour: a guard learning about a new heredoc form must teach every
other guard at the same time, and a copy that misses the lesson silently blocks something the
others allow.

Import it directly (`import shell_text`); the hooks directory is on `sys.path` for both the
`run-python.sh` launch and the test conftest.
"""

import bisect
import os
import re
import shlex
from pathlib import PurePosixPath, PureWindowsPath

# The delimiter of a heredoc is a whole shell WORD, not an identifier: bash accepts `<<\EOF`,
# `<<'END-OF'`, `<<END.X`, `<<E"O"F` and `<<1`, and takes the word after quote removal as the
# delimiter. Reading only `[A-Za-z_]\w*` failed the opener entirely on the first three, so the body
# was judged as commands and its apostrophe opened a quote that hid every later statement - a
# `sed -i` on a JSON file two lines down included. Group 1 is the RAW word; `heredoc_delimiter`
# and `heredoc_is_quoted` read it, because quoting ANYWHERE in the word makes the body literal.
#
# The lookarounds exclude the HERE-STRING `<<< word`, which feeds one word on stdin and opens no
# body. Unguarded, its last two `<` read as `<< word`, and since a body runs to its delimiter every
# later line of the command was dropped as data - a `git push` on the next line included.
_HEREDOC_WORD = r"""(?:[^\s;&|()<>'"\\`]|\\.|'[^'\n]*'|"(?:[^"\\\n]|\\.)*")+"""
HEREDOC_OPEN = re.compile(r"(?<!<)<<(?!<)-?[ \t]*(" + _HEREDOC_WORD + ")")


def heredoc_delimiter(opener) -> str:
    """The delimiter a `HEREDOC_OPEN` match names: its word after bash's quote removal.

    `<<'EOF'`, `<<"EOF"`, `<<\\EOF` and `<<E"O"F` all end at a line reading `EOF`.
    """
    word, out, i = opener.group(1), [], 0
    while i < len(word):
        ch = word[i]
        if ch == "\\" and i + 1 < len(word):
            out.append(word[i + 1])
            i += 2
        elif ch == "'":
            close = word.index("'", i + 1)            # the pattern guarantees a closing quote
            out.append(word[i + 1:close])
            i = close + 1
        elif ch == '"':
            i += 1
            while word[i] != '"':
                if word[i] == "\\" and word[i + 1] in '"\\$`':
                    i += 1                            # inside "", backslash escapes only these
                out.append(word[i])
                i += 1
            i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def heredoc_is_quoted(opener) -> bool:
    """True when ANY part of the delimiter word is quoted, which makes the body literal: bash then
    expands nothing in it, while a bare `<<EOF` body still runs its substitutions."""
    return any(ch in opener.group(1) for ch in "'\"\\")


# The tools whose `tool_input.command` is a shell command string. Claude Code routes the model's
# shell commands through the `PowerShell` tool on Windows where that tool is enabled, and on a
# Windows box without Git Bash it registers no `Bash` tool at all. So a guard that compares
# `tool_name` against "Bash" alone simply never runs there, while still reading - in hooks.json, in
# its docstring, and in its own passing tests - exactly like a guard that is switched on. A hook
# that never fires and one that fires and finds nothing are both silent.
SHELL_TOOLS = ("Bash", "PowerShell")

# A lone `&` ends a statement: it backgrounds the one before it and starts the next. The
# lookarounds keep the `&` that belongs to a redirection (`2>&1`, `&>f`, `<&3`, `>&f`) or to the
# `|&` pipe, and a backslash-escaped `\&`, from reading as one.
_LONE_AMPERSAND = r"(?<![<>&|\\])&(?![>&])"

# Statement separators as REGEXES, for a guard that splits text it has already run through
# `mask_data_regions` (or accepts the raw text's quoting blind spot). A regex cannot carry quoting
# state, so on unmasked text `iter_segments` is the right tool. One copy, imported by every such
# guard: private copies had each drifted, and all of them missed the lone `&`, so the command
# after `echo x &` was never judged by a guard that blocks.
#
# `SEP` also splits a PIPELINE into its elements, for the guards that ask what each program is.
# `LIST_SEP` keeps a pipeline whole, for the ones that ask about a statement's overall status or
# its last element.
#
# `|&` is ONE operator, the pipe that also carries stderr, and its `&` is not a statement of its
# own: left glued to the next element, `ls |& git push` handed a guard the program `&`.
#
# A SUBSHELL paren is deliberately NOT here, although `(git push)` runs a push. Several callers
# split RAW text, where a regex cannot tell a structural paren from one in a quoted label, and a
# corpus replay measured the cost: every verdict it changed was an `echo "=== (must PASS) ==="`
# label cut in half. The quote-aware walk (`iter_segments`) separates subshells instead.
SEP = re.compile(r"&&|\|\||\|&|[;\n|]|" + _LONE_AMPERSAND)
LIST_SEP = re.compile(r"&&|\|\||[;\n]|" + _LONE_AMPERSAND)

# The characters after which a `#` begins a new word, and therefore a comment. Mid-word it is data:
# `a#b`, `${#arr}`, `$#`.
_COMMENT_MAY_FOLLOW = frozenset(" \t\n;&|(")

# A statement can also begin INSIDE a command substitution, and what is in there is a real
# command. Anchoring a match at a segment start is what makes `git commit` appearing as DATA not
# count - but without that, anchoring also silently drops `A=$(git commit ...)`, which the older
# match-anywhere regexes did see. Measured as a regression when the walk replaced them.
#
# Which of these separators actually separates depends on QUOTING, which a regex cannot carry, so
# the spellings live in the walk below rather than in a pattern of their own.


def _iter_separators(text, tool_name=None):
    """(start, end) of every separator in `text` that genuinely begins a new statement.

    Quoting decides this, and it decides it DIFFERENTLY for the two kinds of separator, which
    is why one "is it quoted" flag is not enough:

    * inside SINGLE quotes nothing is special - `echo '$(git commit)'` runs no git at all;
    * inside DOUBLE quotes a command substitution STILL runs, while `;` `|` `&&` are literal.

    Neither is expressible as a pattern, because quoting is state carried across the string, so
    this walks it. The stack matters as much as the flags: when `$(` opens, the quoting in force
    outside it must be restored at the matching `)`, or the closing `"` of `echo "$(date)"` reads
    as an OPENING one and every separator on the rest of the line looks quoted - turning a false
    block into a silent miss, which is the worse direction.

    `tool_name` decides which character escapes, and the two shells are mirror images of each
    other, so guessing is wrong in both directions at once. Under Bash `\\` escapes and a backtick
    opens a substitution; under PowerShell a BACKTICK escapes and `\\` is a PATH SEPARATOR. Reading
    `\\` as an escape under PowerShell eats the separator behind a Windows path, so
    `cd C:\\; git commit` stops being seen at all - the same tool-versus-host confusion that
    `split_for_tool` exists to prevent, one function further down.
    """
    # An UNKNOWN tool escapes NOTHING. The two readings are not symmetric: the Bash one enables
    # backslash escaping, which is the reading that can swallow a separator and hide a command, so
    # defaulting an unrecognised tool to it puts the silent miss in the fallback. Escaping nothing
    # errs toward MORE separators - a false block, which is visible and recoverable. Same rule as
    # `split_for_tool` one function down: an unknown tool takes the stricter reading.
    escape, substitutes = {
        "Bash": ("\\", True),
        "PowerShell": ("`", False),
    }.get(tool_name, ("", True))
    depth: list[tuple[str, bool, bool]] = []   # (closer, saved_single, saved_double)
    in_single = in_double = False
    i, n = 0, len(text)
    escaped_end = -1                           # just past the last escaped pair: `\ #` is mid-word
    backticks = 0                              # open backtick substitutions, a count not a scan
    while i < n:
        ch = text[i]
        if ch == escape and not in_single:
            i += 2                             # an escaped character is data, whatever it is
            escaped_end = i
            continue
        if in_single:
            in_single = ch != "'"
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = not in_double
            i += 1
            continue
        if (not in_double and ch == "#" and i != escaped_end
                and (i == 0 or text[i - 1] in _COMMENT_MAY_FOLLOW)):
            # A comment runs to the end of its line and separates nothing inside it. Walked as
            # text, the apostrophe of `# don't` opened a single-quoted span that swallowed the
            # newline and every command after it. The newline itself is left to end the statement.
            #
            # Inside a BACKTICK substitution it ends at the closing backtick if that comes first:
            # bash cuts the substitution out at its backtick before parsing it, so the comment of
            # `echo \`ls #x\`; git push` cannot reach the push, and reading on to the newline did.
            i = _comment_end(text, i, n, backticks)
            continue
        if substitutes and text.startswith("$$", i):
            # The PID, `$$`, is one token. Its second `$` is not the start of `$'...'`: in
            # `echo $$'x\'` the quote is a PLAIN single quote, whose backslash is literal.
            i += 2
            continue
        if substitutes and not in_double and text.startswith("$'", i):
            # ANSI-C quoting, where a backslash DOES escape: `$'it\'s'` is one string. Read as a
            # plain single-quoted span it closed at `\'`, and the next quote opened a span that hid
            # the separator after it.
            i = _ansi_c_end(text, i + 2)
            continue
        if depth and not in_double and ch == depth[-1][0]:
            # The closer ENDS the substitution's statement. Without this the rest of the line
            # stays glued to it, so `foo=$(ls) git commit -m x` yields one segment `ls) git
            # commit -m x` whose start is `ls)` - and a gate that anchors at the start cannot
            # see the commit at all. It also drops the stray `)` off the last operand token.
            yield i, i + 1
            closer, in_single, in_double = depth.pop()
            backticks -= closer == "`"
            i += 1
            continue
        two = text[i:i + 2]
        # A substitution runs a command even inside double quotes. Process substitution does
        # NOT happen there, so only `$(` and a backtick survive the in_double test.
        if two == "$(" or (substitutes and not in_double and two in ("<(", ">(")):
            yield i, i + 2
            depth.append((")", in_single, in_double))
            in_single = in_double = False
            i += 2
            continue
        if ch == "`" and substitutes:
            yield i, i + 1
            depth.append(("`", in_single, in_double))
            backticks += 1
            in_single = in_double = False
            i += 1
            continue
        if in_double:
            i += 1                             # a plain separator is literal in double quotes
            continue
        if ch == "(" and i != escaped_end and (i == 0 or text[i - 1] in _COMMENT_MAY_FOLLOW):
            # A SUBSHELL. Its paren is a statement boundary on both sides: `(git push)` runs a
            # push that, left whole, read as the program `(git` with the operand `push)`. Only a
            # paren at a word start opens one - `f()`, `arr=(a b)` and `!(glob)` stay words.
            yield i, i + 1
            depth.append((")", in_single, in_double))
            i += 1
            continue
        if two in ("&&", "||", "|&"):
            # `|&` is one operator, the pipe that carries stderr too. Split as `|` alone, its `&`
            # stayed glued to the next element and `ls |& git push` began with the program `&`.
            yield i, i + 2
            i += 2
            continue
        if ch in ";\n|" or (ch == "&" and _is_lone_ampersand(text, i)):
            yield i, i + 1
            i += 1
            continue
        i += 1


def _is_lone_ampersand(text, i):
    """True when the `&` at `i` backgrounds a statement rather than belonging to an operator.

    The walk's twin of `_LONE_AMPERSAND`: `&&` is consumed before this is asked, and the `&` of
    `2>&1`, `&>f`, `<&3` and `|&` is part of a redirection or a pipe.
    """
    return (i == 0 or text[i - 1] not in "<>&|") and text[i + 1:i + 2] not in (">", "&")


def _comment_end(text, start, size, backticks):
    """Index where the `#` comment opening at `start` stops: its newline, or - inside an open
    backtick substitution - the backtick that closes it, whichever comes first. The newline and
    the backtick are both left for the caller to read, since each ends something itself."""
    newline = text.find("\n", start)
    end = size if newline == -1 else newline
    if backticks:
        tick = text.find("`", start, end)
        end = end if tick == -1 else tick
    return end


def _ansi_c_end(text, start):
    """Index just past the `'` that closes an ANSI-C `$'...'` string whose body starts at `start`.

    Inside `$'...'` a backslash escapes the next character, `\\'` included - the one difference
    from a plain single-quoted string, where a backslash is literal. Unterminated runs to the end,
    as bash would keep reading.
    """
    i, n = start, len(text)
    while i < n:
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "'":
            return i + 1
        i += 1
    return n


PR_RE = re.compile(r"^(?:\w+=\S+\s+)*gh\b.*\bpr\b.*\bcreate\b")
GATED_GIT_VERBS = frozenset({"commit", "push"})


# git global options that consume a SEPARATE following token, so a subcommand search never
# mistakes their VALUE for the verb. Lifted here from `git-footgun-guard`, which had the only
# correct implementation of this in the plugin while three other callers each got it wrong in
# their own way - two blind to any option at all, and the regex pair above wrong in BOTH
# directions (see `git_verb_operands`).
GIT_VALUE_OPTS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
)


# A statement need not BEGIN with the program that decides it. These RUN a command handed to them
# as a later operand, so the git call sits behind them - measured in the real corpus as
# `nice -n 19 ionice -c3 git -C "$S" commit -F msg` and `timeout 1500 git rebase --continue`,
# both of which a first-token-only reading missed entirely.
#
# `command` and `exec` belong here for the same reason: each runs the next word as the program, so
# `command git push` is a push. The sed guard had added them to a private copy of this set, which
# left every git guard blind to the same two spellings.
_COMMAND_PREFIXES = frozenset({
    "nice", "ionice", "timeout", "sudo", "doas", "env", "stdbuf",
    "nohup", "setsid", "chrt", "taskset", "time", "command", "exec",
})

# A segment cut from a loop or branch body starts at the keyword, not at the command - and so does
# a CONDITION: `if git push; then`, `while ! git push; do` and `until git push` run the push.
_STATEMENT_KEYWORDS = frozenset({
    "if", "while", "until", "do", "then", "else", "elif", "{", "!", "(",
})

# How far past a launcher to look. Its own flags and their values sit here, and so does an operand
# that carries no dash at all (`timeout 1500`, `nice -n 19`), which is why this cannot simply skip
# tokens beginning with `-`.
_PREFIX_SCAN_LIMIT = 12


def past_command_prefix(tokens, idx, programs, tool_name="Bash"):
    """Index of the first of `programs` that the launcher at `tokens[idx]` runs, else None.

    None as well when `tokens[idx]` is not a known launcher (`sudo`, `nice`, `timeout`, `env`,
    `command`, `exec`, ...): starting only after a KNOWN one is what bounds the scan. `ssh host
    '...'` is not one, so the scan never begins there - the same reason `_deciding_program_index`
    refuses to scan the token list for a script name.

    Scans at most `_PREFIX_SCAN_LIMIT` tokens forward for one whose basename (by the tool's path
    rules, `.exe` dropped) is EXACTLY one of `programs`, which keeps it a statement walk rather
    than a bag-of-tokens test. The shapes that would abuse a looser scan cannot reach it: `nice -n
    19 echo "git commit"` and `timeout 30 ssh host 'git commit'` keep the whole quoted command as
    ONE token, whose basename is the entire string.

    Pass the program set rather than asking "is it git?": the sed guard asks the same question
    about `sed`/`perl`, and a guard that needs it should not have to read this module's private
    launcher set to answer it.
    """
    if idx >= len(tokens) or basename_for_tool(tokens[idx], tool_name) not in _COMMAND_PREFIXES:
        return None
    limit = min(len(tokens), idx + 1 + _PREFIX_SCAN_LIMIT)
    for at in range(idx + 1, limit):
        if basename_for_tool(tokens[at], tool_name) in programs:
            return at
    return None


def statement_program(tokens, programs, tool_name="Bash"):
    """Index of the program a statement runs when it is one of `programs`, else None.

    Loop and branch keywords, leading `VAR=value` assignments and a known launcher in front of the
    program (`timeout 900 make test`, `env -u VIRTUAL_ENV make test`) are skipped, so the program
    is found where the shell finds it rather than at the first word.
    """
    idx = 0
    while idx < len(tokens) and (
        tokens[idx] in _STATEMENT_KEYWORDS
        or ("=" in tokens[idx] and not tokens[idx].startswith("-"))
    ):
        idx += 1                                  # loop/branch keywords, then VAR=value env prefix
    if idx < len(tokens) and basename_for_tool(tokens[idx], tool_name) in _COMMAND_PREFIXES:
        idx = past_command_prefix(tokens, idx, programs, tool_name)
    if idx is None or idx >= len(tokens) or basename_for_tool(tokens[idx], tool_name) not in programs:
        return None
    return idx


def git_verb_operands(tokens, verbs, tool_name="Bash"):
    r"""Tokens after git's SUBCOMMAND when this really is `git <global opts> <verb>`; else None.

    The single answer to "what git command is this?", because asking it with a regex is wrong in
    both directions and every caller here had drifted:

    * UNDER-matching, which the 2026-08-28 audit found in two nudges: `\bgit\s+rev-parse\b`
      requires the verb to sit adjacent to `git`, so any global option between them silences the
      hook - and `git -C <path>` is the shape the rev-parse nudge's own advice steers people
      toward, so the one reader who half-learned the lesson got nothing.
    * OVER-matching: an anchored `git (-C \S+|-\S+)* commit` regex treats `-C` as a bare flag,
      so `git -C commit status` reads `-C`'s VALUE as the verb and the repo gate BLOCKS a status
      command run in a directory named `commit`. In the other direction `git -c key=value commit`
      is not gated at all, because `key=value` does not start with `-` and ends the option run
      early. A commit that the gate cannot see is a commit it cannot gate.

    Leading `VAR=value` environment assignments are skipped, and the program name is taken with
    `basename_for_tool`, so `/usr/bin/git` and `git.exe` both count.
    """
    idx = statement_program(tokens, ("git",), tool_name)
    if idx is None:
        return None
    idx += 1
    while idx < len(tokens) and tokens[idx].startswith("-"):
        if tokens[idx] in GIT_VALUE_OPTS:
            idx += 1                              # this option's VALUE is a separate token
        idx += 1
    if idx >= len(tokens) or tokens[idx] not in verbs:
        return None
    return tokens[idx + 1:]


def argv_for_match(segment, tool_name="Bash"):
    r"""Quote-aware argv for NAME MATCHING a command - never for resolving an operand.

    `segment.split()` is wrong wherever a global option's VALUE may be quoted and contain a
    space: `git -c user.name="Robert Nowotny" commit` splits into `user.name="Robert` plus
    `Nowotny"`, so the option walk consumes the wrong token, reads the next one as the verb, and
    the command is not recognised at all. The 2026-08-30 corpus replay found that exact commit
    had really run, and `is_gated_command` is what repo-gate consults to decide whether to BLOCK,
    so this was a commit the gate could not see.

    Fixing `-c key=value` alone in the earlier pass closed the instance and left the shape: the
    value simply has to contain a space to walk past the same gate again.

    Mangling is acceptable here and only here. `split_for_tool` eats POSIX backslashes, so an
    operand it returns may name nothing on disk - but a caller that merely COMPARES a token
    against a verb name is unaffected, which is exactly what the verb walk does.

    Falls back to a whitespace split when the segment does not parse. An unbalanced quote is
    normal in a segment cut out of a larger command, and a caller whose whole purpose is a
    yes/no is better served by a partial answer than by an exception.

    A trailing COMMENT is removed first, by bash's own word rule, and line continuations with it.
    Left in, the apostrophe of `# don't force` made shlex refuse the whole segment, and the
    fallback then split the raw text: the continuation of `git \\<newline> push` stayed a token and
    `-c user.name="A B"` fell into two, so the verb walk found no push to gate.

    A lone trailing backslash is a continuation whose newline the CALLER cut: the separator walk
    keeps `\\<newline>` inside the segment, and a `segment.strip()` then leaves the backslash with
    nothing to escape. shlex refused it, and the same fallback split a quoted `-c` value - measured
    on 18 of 1,091 recorded pushes. It is dropped here rather than at each caller, because a caller
    that strips gets no error, only a verb it can no longer see.
    """
    text = _drop_severed_continuation(_without_comments(segment, tool_name), tool_name)
    try:
        return split_for_tool(text, tool_name)
    except ValueError:
        return text.split()


def _drop_severed_continuation(text, tool_name):
    """`text` without a final UNESCAPED backslash, under the POSIX reading only.

    An odd run of trailing backslashes ends in one that escapes nothing; an even run is escaped
    data and stays. Under PowerShell a trailing backslash is a path (`cd C:\\`), never an escape.
    """
    if tool_name == "PowerShell":
        return text
    body = text.rstrip(" \t")
    run = len(body) - len(body.rstrip("\\"))
    return body[:-1] if run % 2 else text


def _without_comments(segment, tool_name):
    """`segment` with every comment and unquoted line continuation turned into spaces.

    Both are exactly the regions `mask_data_regions` turns into SPACES rather than filler, so the
    mask decides them - including which `#` starts a word - and nothing else is touched.
    """
    masked = mask_data_regions(segment, tool_name=tool_name)
    return "".join(" " if mask == " " else char for char, mask in zip(segment, masked))


def is_git_verb(segment, verbs, tool_name="Bash"):
    """True when `segment` is a `git <global opts> <verb>` command for one of `verbs`."""
    return git_verb_operands(argv_for_match(segment, tool_name), verbs, tool_name) is not None


# Programs that move the shell's directory. `popd` returns somewhere no static read tracks.
_CD_PROGRAMS = frozenset({"cd", "pushd", "chdir", "set-location", "sl"})
_UNKNOWABLE_DIR = re.compile(r"[$`*?<>|]")        # a destination no static read can resolve
# Ways to point git at another repository than its working directory; nothing here follows them.
_REPO_OPTIONS = ("--git-dir", "--work-tree")
_REPO_ENV = ("GIT_DIR=", "GIT_WORK_TREE=")


def _readable_dir(target, base):
    """Where `cd target` (or `git -C target`) lands from `base`, or None when it cannot be read.

    Unreadable: no target (a bare `cd` goes to HOME), `-` ($OLDPWD), a tilde path (the HOME of the
    shell that runs it), or a variable, substitution or glob. An absolute target is readable even
    when `base` is not. A path that does not exist is left for git to refuse.
    """
    if not target or target == "-" or target.startswith("~") or _UNKNOWABLE_DIR.search(target):
        return None
    if is_rooted(target):
        return os.path.normpath(target)
    return os.path.normpath(os.path.join(base, target)) if base else None


def is_rooted(path):
    """True when `cd path` lands in the same place whatever directory the shell is in.

    Not `os.path.isabs` alone: from Python 3.13 it answers False on Windows for a root with no
    drive (`/r`, `\\r`), yet the shell still lands at that root (Git Bash's `/`, PowerShell's
    current-drive root), and `os.path.join` already treats it as one - so with a base the same
    statement read `\\r`, without a base it read "unknown", decided by the host's Python version.
    """
    return os.path.isabs(path) or (os.sep == "\\" and path[:1] in ("/", "\\"))


def _cd_target(args):
    """The destination operand of a cd-like command, its own options skipped.

    Taking the first word as the target read `cd -P <dir>` as a cd into "<previous>/-P".
    """
    for index, token in enumerate(args):
        if token == "--":
            return args[index + 1] if index + 1 < len(args) else None
        if token == "-" or not token.startswith("-"):
            return token
    return None


# `pushd +2` / `pushd -1` rotate the directory stack: where they land is the stack's business.
_STACK_ROTATION = re.compile(r"^[+-]\d+$")


def directory_change(statement, here, tool_name="Bash", *, expand_home=False):
    """(changes, landing) for ONE statement: does it move the shell's directory, and to where.

    THE cd reader. Four nudges once carried a private regex each, and they had drifted in every
    direction a cd can be read: anchored or not, an env-assignment prefix or not, a bare `cd` seen
    or missed, a quoted path with a space kept whole, cut at the space, or refused - so the next fix
    had to be found and made four times, and a nudge that missed it judged the wrong repository.

    `changes` is False when the statement is not a directory change at all; `landing` is then
    `here`, unchanged, so a caller can write `changed, here = directory_change(stmt, here)`. When it
    IS one, `landing` is the normalised directory, or None when no static read can say where it
    goes: a bare `cd` or a tilde path (HOME of the shell that runs it), `cd -`, a variable,
    substitution or glob, `popd`, a stack rotation, or a relative target from an unknown `here`.
    What a caller does with None is its own policy - stop judging, fail open, or carry on.

    `statement` is RAW text (quotes intact), already cut out of the command by the caller; words
    come from `argv_for_match`, so `cd "a b"` is one word and a trailing comment is not one. Loop
    and branch keywords, a subshell paren and `NAME=value` prefixes in front of the program are
    skipped. `expand_home` resolves `~` and `~/...` against this process's HOME, for a caller that
    has decided the hook and the shell share one.
    """
    tool = tool_name or "Bash"
    tokens = argv_for_match((statement or "").strip().lstrip("(").strip(), tool)
    return _directory_change_tokens(tokens, here, tool, expand_home)


def _directory_change_tokens(tokens, here, tool, expand_home=False):
    """`directory_change` on an argv the caller already split."""
    idx = 0
    while idx < len(tokens) and (
        tokens[idx] in _STATEMENT_KEYWORDS
        or ("=" in tokens[idx] and not tokens[idx].startswith("-"))
    ):
        idx += 1
    if idx >= len(tokens):
        return False, here
    program = basename_for_tool(tokens[idx], tool).lower()
    if program == "popd":
        return True, None
    if program not in _CD_PROGRAMS:
        return False, here
    target = _cd_target(tokens[idx + 1:])
    if program == "pushd" and target and _STACK_ROTATION.match(target):
        return True, None
    if expand_home and target and (target == "~" or target.startswith(("~/", "~\\"))):
        target = os.path.expanduser(target)
    return True, _readable_dir(target, here)


def _apply_git_options(prefix, here, tool):
    """`here` moved by the `-C` options in `prefix` (the tokens before the verb), or None.

    None when a `--git-dir`/`--work-tree` option or a `GIT_DIR`/`GIT_WORK_TREE` assignment points
    git elsewhere: nothing here models them, and guessing would judge the wrong repository.
    """
    git_at = next(i for i, token in enumerate(prefix) if basename_for_tool(token, tool) == "git")
    if any(token.startswith(_REPO_ENV) for token in prefix[:git_at]):
        return None
    options, index = prefix[git_at + 1:], 0
    while index < len(options):
        token = options[index]
        if token.startswith(_REPO_OPTIONS):
            return None
        if token == "-C":                         # several compose, each relative to the last
            here = _readable_dir(options[index + 1] if index + 1 < len(options) else None, here)
        index += 2 if token in GIT_VALUE_OPTS else 1
    return here


#: One literal assignment in a statement that does nothing else: a bare word of path characters, or
#: a quoted string with nothing inside it the shell would expand.
_LITERAL_VALUE = r"""(?:[A-Za-z0-9_./:@%+,-]+|"[^"$`\\]*"|'[^']*')"""
_ASSIGNMENT_STATEMENT = re.compile(
    r"^(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*=%s(?:\s+[A-Za-z_][A-Za-z0-9_]*=%s)*$" % (_LITERAL_VALUE, _LITERAL_VALUE))
_ONE_ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(%s)" % _LITERAL_VALUE)
#: Separators after which the next statement always runs, in the same shell.
_SEQUENCING = frozenset({";", "&&"})


def _sequenced(gap):
    """True when the text between two statements is `;`, `&&` or a plain newline - never `||`, a
    pipe, `&`, a parenthesis, or a backslash continuation, after which the assignment may not run,
    or runs in another shell."""
    stripped = gap.strip(" \t")
    return stripped in _SEQUENCING or stripped == "\n"


def _leading_assignments(raw, gap_before, gap_after):
    """{name: value} for a statement that only assigns absolute literal paths, else None.

    None also when the statement is not fenced in by plain sequencing on both sides, so a value is
    read only where bash certainly sets it in the shell the next statement runs in. A value that
    bash would still expand or that is not an absolute path (a tilde, a glob, a relative path that
    CDPATH could redirect) also gives None.
    """
    statement = raw.strip()
    if not _ASSIGNMENT_STATEMENT.match(statement) or gap_before.strip(" \t\n") or not _sequenced(gap_after):
        return None
    found = {}
    for name, value in _ONE_ASSIGNMENT.findall(statement):
        value = value[1:-1] if value[:1] in "\"'" else value
        if not is_rooted(value) or _UNKNOWABLE_DIR.search(value) or re.search(r"[~\[\]{}]", value):
            return None
        found[name] = value
    return found


def _expansions(raw, known):
    """The names in `known` that `raw` may have replaced by their value, and nothing else.

    A reference counts only when the shell expands it to exactly the value: inside double quotes
    (`"$W"`, `"${W}/x"`), or unquoted when the value holds no whitespace. A single quote anywhere in
    the statement, or a backslash or other character in front of the `$`, leaves every name out -
    the tokenizer has already removed the quotes, so `cd '$W'` would otherwise read as the variable.
    """
    if "'" in raw:
        return {}
    usable = {}
    for name, value in known.items():
        hits = [m.start() for m in re.finditer(r"\$(?:\{%s\}|%s(?![A-Za-z0-9_]))" % (name, name), raw)]
        before = [raw[i - 1] if i else " " for i in hits]
        if hits and all(c == '"' or (c in " \t" and not re.search(r"\s", value)) for c in before):
            usable[name] = value
    return usable


_LEADING_REFERENCE = re.compile(r"^\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))(.*)$", re.DOTALL)


def _expand_known(token, usable):
    """`token` with a leading `$NAME`/`${NAME}` replaced by its value when `usable` has it."""
    match = _LEADING_REFERENCE.match(token)
    name = match and (match.group(1) or match.group(2))
    if not name or name not in usable:
        return token
    return usable[name] + match.group(3)


#: `CDPATH=...` as a word, as a statement, a prefix, or after `export`.
_CDPATH_ASSIGNMENT = re.compile(r"(?:^|\s)CDPATH=")


#: Quoted text and backslash escapes, removed before counting a statement's own parentheses.
_QUOTED_OR_ESCAPED = re.compile(r"""'[^']*'|"(?:[^"\\]|\\.)*"|\\.""", re.DOTALL)


#: A shell comment: `#` at the start of a word.
_COMMENT_START = re.compile(r"(?:^|\s)#")


class _SubshellTracker:
    """Where a Bash statement runs, given the subshells opened and closed before it.

    Bash runs `( ... )`, `$( ... )`, `<( ... )` and a backtick pair in a CHILD shell, so a cd
    inside one is undone when it closes. The segmenter leaves those openers and closers in the gaps
    between statements, and braces `{ ...; }` group in the same shell, so they are not counted.

    A `)` in a gap does not always close a subshell. An array `a=(x)`, a function `f()`,
    `${x:-(a)}` and extglob `!(x)` keep their `(` INSIDE the statement text and send only the `)`
    to the gap; those are counted per statement (`statement`) and absorb the next closer first. A
    case pattern `a)` has no `(` at all: inside `case ... esac` a closer that could be either kind
    makes the tracker give up (`lost`), and so does a closer matching no opener - a wrong directory
    is worse than None, which falls back.
    """

    def __init__(self):
        self.open = []          # per open subshell: (its opener, the directory it was entered from)
        self.inner = 0          # statement-text `(` whose `)` has not arrived yet
        self.cases = 0          # `case ... esac` blocks open
        self.commented = False  # a `#` comment was seen: a later paren may be the comment's
        self.lost = False

    def statement(self, segment, tokens):
        """Count a statement's own parentheses and case/esac nesting; return its excess closers.

        A closer the statement's text holds beyond its own openers first closes an earlier inner
        `(`; any left over closes a subshell, which the caller applies AFTER the statement ran -
        the segmenter can glue a subshell's `)` to its last word (`(a=(1); cd /r; echo); ...`).
        """
        bare = _QUOTED_OR_ESCAPED.sub("", segment)
        # The segmenter does not know comments, so a `)` inside `# ...` reaches a gap like a real one.
        self.commented = self.commented or _COMMENT_START.search(bare) is not None
        excess = bare.count(")") - bare.count("(")
        absorbed = min(self.inner, max(excess, 0))
        self.inner += -absorbed if excess > 0 else -excess
        if tokens[:1] == ["case"]:
            self.cases += 1
        elif tokens[:1] == ["esac"] and self.cases:
            self.cases -= 1
        return max(excess, 0) - absorbed

    def gap(self, gap, here):
        """`here` after the subshell boundaries in `gap`, the text between two statements."""
        if self.commented and any(char in gap for char in "()`"):
            self.lost = True
            return None
        for char in gap:
            if char == "(":
                self.open.append(("(", here))
            elif char == "`" and not (self.open and self.open[-1][0] == "`"):
                self.open.append(("`", here))
            elif char == ")" and self.inner:
                self.inner -= 1
            elif char == ")" and self.cases:
                self.lost = self.lost or bool(self.open)   # a pattern, or this subshell's closer
            elif char in ")`":
                if not self.open or self.open[-1][0] != ("(" if char == ")" else "`"):
                    self.lost = True
                    return None
                here = self.open.pop()[1]
        return here


_FUNCTION_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:-]*$")
_EMPTY_PARENS = re.compile(r"[ \t]*\([ \t]*\)")


def _moves_the_shell(tokens, tool):
    """True when any word of the statement is a cd-like program, wherever it stands."""
    return any(basename_for_tool(token, tool).lower() in _CD_PROGRAMS | {"popd"} for token in tokens)


def _defined_function(tokens, parens_follow=False):
    """(name, the tokens after the name) when the statement opens `name() ...`, `name () ...` or
    `function name ...`, else None.

    `parens_follow` says the text right after the statement is `()`: the segmenter cuts `f () {`
    at its parentheses, so the statement arrives as the bare name."""
    if parens_follow and len(tokens) == 1 and _FUNCTION_NAME.match(tokens[0]):
        return tokens[0], []
    if tokens[:1] == ["function"] and len(tokens) > 1:
        name, rest = tokens[1], tokens[2:]
        name = name[:-2] if name.endswith("()") else name
        rest = rest[1:] if rest[:1] == ["()"] else rest
        return (name, rest) if _FUNCTION_NAME.match(name) else None
    if tokens and tokens[0].endswith("()") and _FUNCTION_NAME.match(tokens[0][:-2]):
        return tokens[0][:-2], tokens[1:]
    if len(tokens) > 1 and tokens[1] == "()" and _FUNCTION_NAME.match(tokens[0]):
        return tokens[0], tokens[2:]
    return None


class _BodyTracker:
    """Statements the walk reads but cannot place: case arms and function bodies.

    Which `case` arm runs depends on a value, and a function body runs only where the function is
    CALLED, so a cd in either is not a cd at that point of the text. A case block holding a cd, or a
    call of a function this command defined with a cd in its `{ }` body, makes every later
    directory unknown (`unknown`); a statement inside a body is not applied where it is written
    (`statement` returns True). A `( )` body runs in a subshell, so its cd never escapes and it is
    read like any other subshell.
    """

    def __init__(self, tool):
        self.tool = tool
        self.cases = 0          # `case ... esac` blocks open
        self.body = None        # [name, open braces, holds a cd] of the `{ }` body being read
        self.pending = None     # a function named without its body: `f()` then `{` on the next line
        self.moving = set()     # functions this command defined whose body holds a cd
        self.unknown = False

    def statement(self, tokens, parens_follow=False):
        """Read one statement; True when it sits inside a function body and must not be applied."""
        if self.body is not None:
            return self._in_body(tokens)
        definition = _defined_function(tokens, parens_follow)
        pending, self.pending = self.pending, None
        if definition is None and pending and tokens[:1] == ["{"]:
            definition = pending, tokens
        if definition is not None:
            return self._open(*definition)
        program = next((t for t in tokens if t not in _STATEMENT_KEYWORDS and "=" not in t), None)
        self._case(program, tokens)
        self.unknown = self.unknown or program in self.moving
        return False

    def _open(self, name, rest):
        if rest[:1] != ["{"]:
            self.pending = None if rest else name
            return False
        self.body = [name, 0, False]
        return self._in_body(rest)

    def _in_body(self, tokens):
        body = self.body
        body[1] += tokens.count("{") - tokens.count("}")
        body[2] = body[2] or _moves_the_shell(tokens, self.tool)
        if body[1] <= 0:
            if body[2]:
                self.moving.add(body[0])
            self.body = None
        return True

    def _case(self, program, tokens):
        """Track `case ... esac` by the program word, so an `echo case` opens nothing."""
        if program == "case":
            self.cases += 1
        in_case = self.cases > 0
        if program == "esac" and self.cases:
            self.cases -= 1
        self.unknown = self.unknown or (in_case and _moves_the_shell(tokens, self.tool))


def git_verb_dir(command, cwd, verbs, tool_name=None):
    """The directory the first `git <verb>` in `command` runs in, or None when it is unreadable.

    Follows every cd-like statement before the verb, then the verb's own `-C` values, starting from
    `cwd` - the same path the shell and git take. The event cwd a hook receives is where the SESSION
    sits, not where a `cd <repo> && git commit` lands, so a hook that judges a repository must ask
    this rather than read its own working directory. Two hooks once answered it separately and
    judged different repositories for the same commit.

    Operands come from `argv_for_match`, which eats POSIX backslashes, so a backslash-separated
    Windows path resolves to a directory that does not exist; callers then find no repository
    there and must treat that like None.

    One narrow variable form is followed: `W=/r; cd "$W" && git commit` lands in /r. Measured
    2026-10-19: read as unreadable, that commit was judged in the session's repository, which it was
    not touching, and blocked for it. The values come only from LEADING statements that do nothing
    but assign absolute literal paths, each followed by `;`, `&&` or a newline
    (`_leading_assignments`), and they are used only in the ONE statement right after them, through
    a reference the shell expands to exactly that value (`_expansions`); then they are forgotten.
    Anything wider - control flow, subshells, pipelines, `read`, `declare`, `+=`, a later statement
    that might reassign the name - is a shell this reader does not model, and a wrong directory is
    worse than None, which falls back. Bash only: PowerShell assigns with `$W = ...`.

    A cd inside a subshell - `(cd /r); git commit`, `x=$(cd /r; pwd)` - holds only until that
    subshell closes (`_SubshellTracker`), so the git after it runs where the command started.
    Bash only again: PowerShell's `( )` and `$( )` run in the same runspace, so its location sticks.

    A cd inside a `case` block, or inside the `{ }` body of a function this command defines and
    then calls, makes the verb's directory None (`_BodyTracker`): which arm runs is decided by a
    value, and a body runs where it is called, not where it is written. `case a in a) cd /r;; esac;
    git commit` and `f() { cd /r; }; f; git commit` both commit in /r while the text reads /s. A body
    that is only defined moves nothing, and a verb inside one gives None.

    Once the command assigns `CDPATH` (`CDPATH=/a; cd sub`, `export CDPATH=...`, or as a prefix),
    a RELATIVE cd is unknown: bash tries each CDPATH entry first, and whether `/a/sub` exists is not
    in the text. A CDPATH inherited from the environment is invisible here and not modelled.
    """
    tool, here = tool_name or "Bash", cwd
    text = blank_heredoc_bodies(command or "")
    segments = list(iter_segments(text, tool))
    known, leading, previous_end = {}, tool == "Bash", 0
    subshells, gap_start, cdpath_set = _SubshellTracker(), 0, False
    bodies = _BodyTracker(tool)
    for index, (at, segment) in enumerate(segments):
        if tool == "Bash":
            here = subshells.gap(text[gap_start:at], here)
        gap_start = at + len(segment)
        # Read off the raw text, before the leading-assignment block can consume the statement. A
        # quoted `CDPATH=` in an echo also counts; that only costs a None, never a wrong directory.
        cdpath_set = cdpath_set or _CDPATH_ASSIGNMENT.search(segment) is not None
        following = segments[index + 1][0] if index + 1 < len(segments) else len(text)
        gap_after = text[at + len(segment):following]
        if leading:
            found = _leading_assignments(segment, text[previous_end:at], gap_after)
            previous_end = at + len(segment)
            if found is not None:
                known.update(found)
                continue
            leading = False
        tokens = argv_for_match(segment.strip().lstrip("(").strip(), tool)
        usable, known = _expansions(segment, known), {}
        if not tokens:
            continue
        tokens = [_expand_known(token, usable) for token in tokens]
        closers = subshells.statement(segment, tokens) if tool == "Bash" else 0
        in_body = bodies.statement(tokens, _EMPTY_PARENS.match(text, at + len(segment)) is not None)
        # With CDPATH set, a relative target is unknown: reading it from no directory (None) makes
        # `_readable_dir` refuse exactly the relative ones and keep the rooted ones.
        changed, landing = _directory_change_tokens(tokens, None if cdpath_set else here, tool)
        if in_body:
            # Defined here, run only where it is called: a verb in it has no readable directory.
            if git_segment_dir(tokens, verbs, here, tool)[0]:
                return None
        elif changed:
            # `cd x & ...` and `cd x | ...` run the cd in a subshell: the next statement starts
            # where this one did.
            if gap_after.strip(" \t") not in ("&", "|"):
                here = landing
        else:
            is_verb, where = git_segment_dir(tokens, verbs, here, tool)
            if is_verb:
                return None if subshells.lost or bodies.unknown else where
        if closers:
            here = subshells.gap(")" * closers, here)
    return None


def git_segment_dir(tokens, verbs, here, tool_name="Bash"):
    """(is this statement `git <verb>` for one of `verbs`, the directory it runs in or None).

    `here` is where the statement starts; the verb's own `-C` values move it, and a `--git-dir`,
    `--work-tree` or `GIT_DIR` points it somewhere nothing here models (None)."""
    tool = tool_name or "Bash"
    operands = git_verb_operands(tokens, verbs, tool)
    if operands is None:
        return False, here
    return True, _apply_git_options(tokens[:len(tokens) - len(operands) - 1], here, tool)


def iter_segments(text, tool_name=None):
    """(offset, segment) for each statement in `text`, offsets into `text` itself.

    `SEP.split` throws the positions away, which is fine for a yes/no question and not fine for a
    caller that must know whether a write happened BEFORE the gated verb. Without this such a
    caller keeps its own second splitter, and the two drift on exactly the shapes that matter.
    """
    pos = 0
    for start, end in _iter_separators(text, tool_name):
        yield pos, text[pos:start]
        pos = end
    yield pos, text[pos:]



def _windows_command_argv(command):
    r"""Split a Windows command line by the documented C-runtime rules.

    Pure Python rather than `CommandLineToArgvW`, unlike the copy in `harness_checks`: that one
    parses a command line THIS MACHINE will run, so a Windows-only path is fine there. This one
    parses the PowerShell TOOL's string, which can reach a hook on any host - pwsh runs on Linux -
    and a ctypes path would also be untestable on the platform most of this suite runs on.

    The backslash rules only bite around a quote: 2n backslashes before one are n backslashes and
    the quote still toggles, 2n+1 are n backslashes and a LITERAL quote, and a run with no quote
    after it is literal throughout. That last rule is the one that matters here - it is what keeps
    `C:\dir\file.txt` intact.

    PowerShell's own single-quoted string is read on top of those rules, because the tool's
    string is PowerShell before any C runtime sees it: `-newermt '-3 minutes'` is one argument,
    and splitting it at the space made two hooks each keep a private re-join.
    """
    args, cur, in_quotes, started, i, n = [], [], False, False, 0, len(command)
    while i < n:
        ch = command[i]
        if ch == "\\":
            j = i
            while j < n and command[j] == "\\":
                j += 1
            slashes = j - i
            if j < n and command[j] == '"':
                cur.append("\\" * (slashes // 2))
                if slashes % 2:
                    cur.append('"')
                else:
                    in_quotes = not in_quotes
                started, i = True, j + 1
            else:
                cur.append("\\" * slashes)
                started, i = True, j
            continue
        if ch == '"':
            in_quotes, started, i = not in_quotes, True, i + 1
            continue
        if ch == "'" and not in_quotes:
            verbatim, stop = _powershell_single_quoted(command, i)
            if verbatim is not None:
                cur.append(verbatim)
                started, i = True, stop
                continue
        if ch in " \t" and not in_quotes:
            if started:
                args.append("".join(cur))
                cur, started = [], False
            i += 1
            continue
        cur.append(ch)
        started, i = True, i + 1
    if started:
        args.append("".join(cur))
    return args


def _powershell_single_quoted(command, start):
    """(text, index past the closing quote) of the PowerShell single-quoted string at `start`.

    A single-quoted string is VERBATIM (about_Quoting_Rules): no escape, no expansion, and `''`
    is one literal quote. `(None, start)` when no closing quote follows, so the caller keeps the
    apostrophe as an ordinary character - the Windows arm has never raised, and none of its
    callers catches a ValueError.
    """
    out, i, n = [], start + 1, len(command)
    while i < n:
        if command[i] != "'":
            out.append(command[i])
            i += 1
        elif command.startswith("''", i):
            out.append("'")
            i += 2
        else:
            return "".join(out), i + 1
    return None, start


def split_for_tool(command, tool_name="Bash", comments=False):
    r"""Split a tool's `tool_input.command` into argv, by the TOOL's language, never the host OS.

    A hook on a `Bash|PowerShell` matcher receives two different languages. The Bash tool is a
    POSIX command line even on Windows, because Claude Code runs it through Git Bash - verified
    against real bash, which mangles an unquoted `C:\Users\me\f.txt` to `C:Usersmef.txt` exactly
    as `shlex` does, so shlex is not merely tolerable there, it is what the tool actually does -
    once an unquoted backslash-newline continuation is removed first, which bash does and shlex
    does not.
    The PowerShell tool is a Windows command line, where that same backslash is a PATH SEPARATOR
    and eating it hands the caller a path that opens nothing.

    That matters only where a guard RESOLVES the token - opens, stats or executes it - because the
    read then fails and a fail-open approves what the guard exists to block. Tokens merely compared
    or name-matched survive mangling.

    `comments` reaches the POSIX arm only, where shlex knows `#`. The Windows arm has no comment
    concept at all - the C runtime hands `#` to the program like any other character - so passing
    it does not silently mean something different there, it means nothing.

    Do NOT reach for `harness_checks.split_command_line` instead: it keys on `os.name`, which is
    right for a command this machine will run and wrong here - on a Windows host it would hand the
    Bash tool's POSIX string to the Windows parser. An unknown tool takes the Bash reading, which
    is the one that cannot invent separators that were never in the string.
    """
    if tool_name == "PowerShell":
        return _windows_command_argv(command)
    return shlex.split(_join_line_continuations(command), comments=comments)


def _join_line_continuations(command):
    r"""`command` with every unquoted backslash-newline removed, as bash removes it before splitting.

    shlex does not: it keeps the newline as part of the NEXT token, so `status && \<newline>git
    commit` handed the verb walk a program named `<newline>git` and the commit went unrecognised by
    every guard that splits argv - the repo gate included. A continuation inside single quotes is
    literal and stays; `mask_data_regions` is what tells the two apart, since it turns only an
    unquoted continuation into two spaces and masks a quoted one with its string.
    """
    if "\\\n" not in command:
        return command
    masked = mask_data_regions(command)
    out, i, n = [], 0, len(command)
    while i < n:
        if command.startswith("\\\n", i) and masked[i:i + 2] == "  ":
            i += 2
            continue
        out.append(command[i])
        i += 1
    return "".join(out)


def basename_for_tool(token, tool_name="Bash"):
    r"""The program name from a token that may carry a path, by the TOOL's separator rules.

    A guard asking "is this command `sed`?" has to strip the path first, and which characters
    separate a path is the tool's question, not the host's. `C:\bin\sed.exe` is a path in
    PowerShell and one long filename under POSIX rules - so a basename taken on `/` alone returns
    the whole string and never matches, which is a guard silently declining to fire.

    This is the SECOND half of the same defect as `split_for_tool`, and either half alone leaves
    the guard off: split correctly and the basename still fails, fix the basename and the split
    has already eaten the separators.

    On the Bash arm a BACKSLASH separates too. A token reaching this still carries one only
    because it was quoted - bash keeps backslashes inside double quotes - so `"C:\Git\git.exe"`
    really is a path Git Bash runs, and reading it as one long filename left it unmatched.

    `.exe` is dropped on BOTH arms, because it is about how a program is NAMED and not about
    separators at all - Git Bash on Windows runs `sed.exe`, and every command allowlist in this
    plugin is spelled without the suffix. Stripping it only on the PowerShell arm left
    `sed.exe -i config.json` unblocked under the tool that carries nearly all the traffic.
    """
    if tool_name == "PowerShell":
        name = PureWindowsPath(token).name
    else:
        name = PurePosixPath(token.replace("\\", "/")).name
    return name[:-4] if name.lower().endswith(".exe") else name

def is_shell_tool(tool_name) -> bool:
    """True when `tool_name` is a tool that carries a shell command in `tool_input.command`.

    Use this in place of a literal `tool_name == "Bash"` check, and pair it with a
    `Bash|PowerShell` matcher in hooks.json - the matcher decides whether the hook runs at all, so
    widening only one of the two leaves the guard off on the platform it was widened for.
    """
    return tool_name in SHELL_TOOLS


# Commands whose exit status is a quality verdict worth protecting: a test run, a linter, a type
# checker, a build. Two guards ask about them - one about a pipe that masks the verdict, one about a
# commit sent beside the run in the same message - so the vocabulary lives here, once.
GATE_RE = re.compile(
    r"\b(?:"
    r"cargo\s+(?:fmt|clippy|test|build|check|xtask)"
    r"|pytest|ruff|pyright|mypy|tsc|bandit"
    r"|go\s+(?:test|vet)"
    r"|npm\s+(?:run\s+)?(?:test|lint)"
    r"|dotnet\s+test"
    r"|make\s+\S*(?:test|check|lint)"
    r")\b"
)

# The gate.py jig (compuse-toolbox) runs a gate and exits with the gate's own status.
GATE_JIG_NAME = r"(?<![\w.-])gate\.py\b"
GATE_JIG_RE = re.compile(GATE_JIG_NAME)

# A gate whose verdict a BACKGROUND job loses: broader than GATE_RE, because a backgrounded
# `make push` or `ci_wait` is read for its verdict the same way, and neither matches GATE_RE's
# build-tool vocabulary. Two guards ask about it - one about a run_in_background compound whose
# notice reports the wrong command, one about a gate detached with a trailing `&`.
BACKGROUND_GATE_RE = re.compile(
    r"\b(?:"
    r"make\s+\S*(?:test|check|lint|push|release)"
    r"|ci_wait(?:\.py)?"
    r"|gh\s+run\s+watch"
    r")\b"
    r"|" + GATE_RE.pattern
)


# Words that run the program after them. Their own operands sit in between and are skipped: the
# value of a short option that takes one (`env -u NAME`, `nice -n 19`, `env -C DIR`), a long
# option's value (`uv run --with pytest`), a duration (`timeout 900`), `run` after `uv`, and
# `NAME=value` assignments (`env A=1 make test`).
_GATE_LAUNCHERS = frozenset({
    "env", "timeout", "nice", "ionice", "nohup", "setsid", "stdbuf", "time", "command", "exec",
    "sudo", "doas", "uv", "uvx", "python", "python3", "py",
})
_GATE_SHORT_WITH_VALUE = frozenset({"-u", "-n", "-C", "-c", "-k", "-s", "-S", "-p", "-o"})
_GATE_SCAN_LIMIT = 16

# Words in front of a pipeline's program that are syntax, not a program: a subshell or group
# opener and the `!` that negates the pipeline. `( pytest -q ) | tail` still runs pytest.
_GROUP_OPENERS = frozenset({"(", "{", "!"})


def _is_assignment_word(word):
    name, sep, _value = word.partition("=")
    return bool(sep) and name.replace("_", "a").isalnum() and not name[:1].isdigit()


def program_word_at(words, tool_name="Bash"):
    """Index of the word a statement RUNS, past assignments and launchers; None when there is none.

    `python -m X` runs X. `python -c ...` runs code, never a gate by name, so it answers None.
    Shared by the two gate guards so they agree on which word is the program: a gate word
    searched ANYWHERE in a statement made `grep pytest docs/x.md` read as pytest running.
    """
    at = 0
    for _ in range(_GATE_SCAN_LIMIT):
        while at < len(words) and _is_assignment_word(words[at]):
            at += 1
        if at >= len(words):
            return None
        program = basename_for_tool(words[at], tool_name).lower()
        if program not in _GATE_LAUNCHERS and not program.startswith("python"):
            return at
        at += 1
        while at < len(words) and (words[at].startswith("-") or words[at] == "run"
                                   or words[at][:1].isdigit() or _is_assignment_word(words[at])):
            word = words[at]
            if word == "-c" and program.startswith(("python", "py")):
                return None
            if word == "-m":
                return at + 1 if at + 1 < len(words) else None
            at += 2 if (word in _GATE_SHORT_WITH_VALUE
                        or (word.startswith("--") and "=" not in word)) else 1
    return None


def runs_a_gate(command, tool_name="Bash"):
    """True when a statement of `command` RUNS a recognised gate (or the gate.py jig) as its program.

    A gate that is only text - inside a heredoc body or quotes, or an argument of another program
    (`grep -rn pytest docs/`, `cat pytest.ini`) - does not count. The program word is matched as
    written, path and all, which is the reading block-commit-beside-sibling-gate was priced on.
    """
    for _at, segment in iter_segments(commands_only(command or "", tool_name), tool_name):
        words = segment.split()
        at = program_word_at(words, tool_name)
        if at is None:
            continue
        if GATE_JIG_RE.search(words[at]) or GATE_RE.match(" ".join(words[at:at + 3])):
            return True
    return False


def gate_program_in(text, tool_name="Bash", pattern=GATE_RE, start=0, end=None):
    """The `pattern` match at the PROGRAM word of the statement `text[start:end]`, else None.

    One pipeline element or one statement, already split by the caller. The match is taken where
    the program's NAME begins - past a path and any opening quote, so `.venv/bin/pytest` and the
    restored quoted `"$X/ci_wait.py"` are gates - and it may run on into the following words, so
    `make test`, `cargo test` and `go vet` match as they do in the vocabulary. An argument is
    never the program, so `grep pytest docs/x.md` and `cat pytest.ini` answer None.

    The returned match indexes `text` itself, so a caller cutting a longer command at
    `match.start()` cuts it where the gate runs.
    """
    end = len(text) if end is None else end
    tokens = [(start + m.start(), start + m.end()) for m in re.finditer(r"\S+", text[start:end])]
    while tokens and text[tokens[0][0]:tokens[0][1]] in _GROUP_OPENERS:
        tokens = tokens[1:]
    if tokens:
        lead, last = tokens[0]
        while lead < last - 1 and text[lead] in "({":
            lead += 1                              # `(pytest`, the opener glued to the program
        tokens[0] = (lead, last)
    at = program_word_at([text[a:b] for a, b in tokens], tool_name)
    if at is None:
        return None
    word_start, word_end = tokens[at]
    word = text[word_start:word_end]
    name_at = word_start + max(word.rfind("/"), word.rfind("\\")) + 1
    while name_at < word_end and text[name_at] in "\"'":
        name_at += 1
    return pattern.match(text, name_at, end)


def is_gated_command(command, tool_name=None):
    """True when a statement in `command` is a git commit, a git push, or a gh pr create.

    Heredoc bodies are dropped first, then each remaining statement is matched anchored at its
    start, so "git commit"/"git push" appearing as DATA does not count - only an actual command
    does. Over-matching is not harmless here: the repo gate blocks on it, and a CHANGELOG line
    ABOUT committing would then block the commit that adds it.

    Anchoring alone does NOT cover a heredoc body, which is why the strip is needed and not merely
    tidy. The body is split on the same separators as the surrounding command, so a line such as
    `for cmd in ("git checkout -- f && git commit -m x",)` yields a segment beginning with a
    real-looking command. Measured 2026-08-20: writing the tests for `gated-prep-nudge` was blocked
    by the repo gate, because the test data named the very shapes under test - a guard refusing to
    let its own documentation be written.

    It lives in this module rather than in the gate that first needed it because a second consumer
    now asks the same question for its own reason - a commit is the moment work concludes, which is
    when the decision-review nudge fires. Two copies of this regex set would drift, and the drift
    would be silent in both directions: a shape one recognises and the other does not.
    """
    for _at, seg in iter_segments(strip_heredoc_bodies(command or ""), tool_name):
        seg = seg.strip().lstrip("(").strip()
        if is_git_verb(seg, GATED_GIT_VERBS, tool_name or "Bash") or PR_RE.match(seg):
            return True
    return False


def opens_a_pr(command, tool_name=None):
    """True when a statement in `command` is a `gh pr create` - the PR half of is_gated_command.

    Segmented and anchored exactly like is_gated_command, so the two cannot disagree about what a
    statement is; only the verb set differs. It exists because the decision-review nudge counts a
    PR as work concluding and a commit or push as NOT concluding - measured over three weeks of
    transcripts, firing the review on every commit walked tooling decisions at the end of ordinary
    work sessions, and each walk ended in a memory capture, an engine fix and a plugin release from
    a project that had nothing to do with the tool.
    """
    for _at, seg in iter_segments(strip_heredoc_bodies(command or ""), tool_name):
        seg = seg.strip().lstrip("(").strip()
        if PR_RE.match(seg):
            return True
    return False


def commands_only(command: str, tool_name="Bash") -> str:
    """`command` with every DATA region removed, leaving only text the shell will EXECUTE.

    `tool_name` picks the escape rules, as it does for `mask_data_regions`: a hook registered for
    PowerShell that masked by the Bash reading ate the `;` of `cd C:\\; git push`.

    The pairing every command-scanning guard needs, in one call. Each half alone leaves a hole the
    other closes, and both holes have shipped: `mask_data_regions` cannot see a heredoc BODY,
    because a body is not quoted, so a `git -C /elsewhere` written into a runbook read as the repo
    the command acts on; `strip_heredoc_bodies` cannot see a quoted ARGUMENT, so `echo 'pgrep -f x'`
    read as an invocation. A guard that calls only one is not half-safe, it is wrong in whichever
    direction it skipped - and which half was skipped is invisible at the call site, which is why
    this exists instead of the two-call idiom.

    Offsets do NOT survive: the heredoc strip removes lines. A caller that needs POSITIONS (to tell
    a write before the verb from one after it, or to slice the raw command at a match) wants
    `commands_only_aligned`, which masks the same regions and keeps every offset.

    NOT for every guard, and the exception is not an edge case. A quoted string is data to the
    LOCAL shell and a COMMAND to a remote one, so a guard whose subject is `ssh host \'...\'`,
    `bash -c \'...\'` or any other execute-this-string form must NOT mask quotes - that deletes
    exactly what it is looking for. Measured: routing `warn-inline-powershell` through this made
    `ssh host \'powershell -command "x"\'` stop firing and took six tests with it. Those guards
    want `strip_heredoc_bodies` alone. Ask what the guard's subject IS before reaching for this.
    """
    return mask_data_regions(strip_heredoc_bodies(command or ""), tool_name=tool_name)


def commands_only_aligned(command: str, tool_name="Bash") -> str:
    """The offset-preserving twin of `commands_only`: the same data regions, blanked or masked in
    place, so `len(out) == len(command)` and an offset found on the result indexes the raw command.

    Heredoc bodies and terminators become spaces (`blank_heredoc_bodies`), then quoted text,
    substitutions and comments are masked by `mask_data_regions` under `tool_name`'s escape rules.
    Cutting the blanked body lines back out of the result gives exactly `commands_only(command,
    tool_name)`, so the two never disagree about what is a command; this one only keeps the
    positions. A `git push` found here at `m.start()` is `command[m.start():m.end()]`.

    Use it when the caller slices the raw command or compares positions; use `commands_only` when
    it only asks whether something is present. The same caveat applies: a guard whose subject is a
    string handed to another shell (`ssh host '...'`, `bash -c '...'`) must not mask quotes at all.
    """
    return mask_data_regions(blank_heredoc_bodies(command or ""), tool_name=tool_name)


# `cd /long/scratch/path && <the command that matters>`. Almost every Bash call in a real session
# opens this way, so a reader that takes a command's SUBJECT from its opening words would name `cd`
# for nearly all of them and treat a session's distinct work as one look-alike group.
_LEADING_CD = re.compile(r"^\s*cd\s+(?:'[^']*'|\"[^\"]*\"|[^\s;&|\n]+)\s*(?:&&|;|\n)\s*")


def strip_leading_cd(command: str) -> str:
    """`command` without its leading `cd <dir> &&` / `cd <dir>;` / `cd <dir>` newline chain. PURE.

    Only the LEADING chain goes: a `cd` after the first real command is part of the work, and a
    lone `cd <dir>` with nothing after it is left as it is.
    """
    previous = None
    while previous != command:
        previous = command
        command = _LEADING_CD.sub("", command, count=1)
    return command


def iter_heredocs(command: str):
    """Yield (line, opener, body) for every heredoc the shell would open in `command`.

    `line` is the opener's index in `command.split("\\n")`, `opener` its `HEREDOC_OPEN` match on
    that raw line, and `body` the half-open (start, end) range of body lines; the terminator, when
    there is one, is line `end`. An unterminated body runs to the last line. THE heredoc walk:
    every reader of heredocs uses it, so none can disagree about where a body starts. Read the
    delimiter with `heredoc_delimiter`, never off the match: it is a whole word after quote removal.

    The regex knows the opener's SYNTAX; where a `<<` sits decides whether it is one:

    - a QUOTED argument or a comment makes it text: `git commit -m "docs: explain <<EOF
      heredocs"` opens nothing, and reading it as an opener swallowed the rest of the command, so
      every guard downstream went silent on a real `git push` after it;
    - ARITHMETIC makes it a left shift: `(( z = x << y ))` and `$((1 << n))` read as a heredoc
      delimited by `y` or `n`, and every later line up to one spelling it was dropped;
    - a COMMAND SUBSTITUTION makes it code again, even inside double quotes: in
      `git commit -m "$(cat <<'EOF' ... EOF\\n)"` the heredoc is real, and missing it left an odd
      `"` in its body to open a string that hid every later statement.

    One left-to-right pass carries the quoting and substitution state ACROSS each body, the way
    bash reads it: the body starts at the newline that ends the opener's line and is skipped
    whole, so an apostrophe in it opens nothing, and after the terminator the walk resumes inside
    whatever the opener sat in. Two openers on one line take their bodies in order. Linear in the
    length of the command, which matters because this runs on every shell call.
    """
    command = command or ""
    if "<<" not in command:
        return
    yield from _HeredocScan(command).run()


class _HeredocScan:
    """The single pass behind `iter_heredocs`. State is a stack of open closers - `)` for a
    substitution or subshell, a backtick, `"` for a double-quoted string - plus the openers still
    waiting for the newline that starts their bodies."""

    def __init__(self, text):
        self.text = text
        self.lines = text.split("\n")
        self.starts = [0]
        for line in self.lines[:-1]:
            self.starts.append(self.starts[-1] + len(line) + 1)
        self.stack: list[str] = []
        self.backticks = 0
        self.pending: list[tuple[int, re.Match]] = []
        self.escaped_end = -1
        self.parens: dict[int, int] | None = None

    def run(self):
        i, size = 0, len(self.text)
        while i < size:
            found, i = self._step(i)
            yield from found
        for at, opener in self.pending:                # unterminated: runs to the last line
            yield at, opener, (len(self.lines), len(self.lines))

    def _line_of(self, offset):
        return bisect.bisect_right(self.starts, offset) - 1

    def _step(self, i):
        """(heredocs completed here, next offset) for the character at `i`."""
        text, ch = self.text, self.text[i]
        in_double = bool(self.stack) and self.stack[-1] == '"'
        if ch == "\\":
            self.escaped_end = i + 2                   # an escaped character is data
            return (), i + 2
        if ch == "\n" and self.pending and not in_double:
            return self._bodies(i)
        if text.startswith("$$", i):
            return (), i + 2                           # the PID, never the start of `$'...'`
        if text.startswith("$((", i):
            return (), self._paren_run_end(i + 1)      # arithmetic: its `<<` is a shift
        if text.startswith("$(", i):
            self.stack.append(")")
            return (), i + 2
        if text.startswith("${", i):
            close = text.find("}", i + 2)
            return (), len(text) if close == -1 else close + 1
        if ch in "`\"":
            self._toggle(ch, in_double)
            return (), i + 1
        if in_double:
            return (), i + 1
        return self._code(i)

    def _toggle(self, ch, in_double):
        """Open or close a backtick substitution or a double-quoted string at a `ch` of that kind."""
        if ch == '"':
            if in_double:
                self.stack.pop()
            else:
                self.stack.append('"')
        elif self.stack and self.stack[-1] == "`":
            self.stack.pop()
            self.backticks -= 1
        else:
            self.stack.append("`")
            self.backticks += 1

    def _code(self, i):
        """The step for a character in live code, outside any double-quoted string."""
        text, ch = self.text, self.text[i]
        if ch == "'":
            close = text.find("'", i + 1)
            return (), len(text) if close == -1 else close + 1
        if text.startswith("$'", i):
            return (), _ansi_c_end(text, i + 2)
        if text.startswith("((", i):
            return (), self._paren_run_end(i)          # bare arithmetic command
        if ch == "(":
            self.stack.append(")")
            return (), i + 1
        if ch == ")":
            if self.stack and self.stack[-1] == ")":
                self.stack.pop()
            return (), i + 1
        if ch == "#" and i != self.escaped_end and (i == 0 or text[i - 1] in _COMMENT_MAY_FOLLOW):
            return (), _comment_end(text, i, len(text), self.backticks)
        if text.startswith("<<", i):
            return self._opener(i)
        return (), i + 1

    def _opener(self, i):
        """Queue the heredoc whose `<<` is at `i`, if it is one; a here-string `<<<` is not."""
        if self.text.startswith("<<<", i):
            return (), i + 3
        at = self._line_of(i)
        opener = HEREDOC_OPEN.match(self.lines[at], i - self.starts[at])
        if opener is None:
            return (), i + 2
        self.pending.append((at, opener))
        return (), self.starts[at] + opener.end()

    def _bodies(self, newline):
        """Skip the bodies of every queued opener, which start after the `newline` at this offset.

        The terminator is the first line that is exactly the delimiter; bash allows leading
        whitespace with the `<<-` form, so the comparison is made on the stripped line.
        """
        line, found = self._line_of(newline) + 1, []
        for at, opener in self.pending:
            delimiter, end = heredoc_delimiter(opener), line
            while end < len(self.lines) and self.lines[end].strip() != delimiter:
                end += 1
            found.append((at, opener, (line, end)))
            line = end + 1
        self.pending = []
        return found, len(self.text) if line >= len(self.lines) else self.starts[line]

    def _paren_run_end(self, start):
        """Offset just past the `)` that balances the `(` at `start`, counted without regard to
        quoting; an unbalanced one runs to the end of its line only, so a stray `((` cannot hide
        every opener after it. The pairs are matched once for the whole text, which keeps a run of
        unclosed `((` linear rather than rescanning the rest of the command for each."""
        if self.parens is None:
            self.parens, opened = {}, []
            for index, char in enumerate(self.text):
                if char == "(":
                    opened.append(index)
                elif char == ")" and opened:
                    self.parens[opened.pop()] = index
        close = self.parens.get(start)
        if close is not None:
            return close + 1
        newline = self.text.find("\n", start)
        return len(self.text) if newline == -1 else newline


def find_heredoc_opener(line: str):
    """The `HEREDOC_OPEN` match for the first `<<` on `line` that opens a heredoc, or None."""
    for _at, opener, _body in iter_heredocs(line):
        return opener
    return None


def _split_heredocs(command: str):
    """(command lines, body lines) for `command`, split at every heredoc the shell would open.

    One scanner for both readings of a command: a body is DATA when judging what runs, and it is
    AUTHORED TEXT when asking what is being written. Deriving the two from separate walks let them
    disagree about where a body starts, so they share this one.
    """
    lines = command.split("\n")
    kept: list[str] = []
    bodies: list[str] = []
    index = 0
    for _at, _opener, (start, end) in iter_heredocs(command):
        kept.extend(lines[index:start])
        bodies.extend(lines[start:end])
        index = end + 1                               # drop the terminator line itself
    kept.extend(lines[index:])
    return kept, bodies


def strip_heredoc_bodies(command: str) -> str:
    """Drop heredoc bodies, keeping the command lines around them.

    The opener line is KEPT, because it is a real command (`cat <<EOF > file.txt` still redirects,
    and `cmd <<EOF | grep x` still pipes). Only the body and its terminator are removed.

    An unterminated heredoc consumes the rest of the input, which is the safe direction: the shell
    would treat those lines as data too, so a guard must not judge them as commands.
    """
    return "\n".join(_split_heredocs(command)[0])


def blank_heredoc_bodies(command: str) -> str:
    """`command` with every heredoc body blanked to spaces IN PLACE, so offsets survive.

    Blanks exactly the lines `strip_heredoc_bodies` removes - the body lines and the terminator
    line, found by the same `iter_heredocs` walk - replacing every character on them with a space,
    a CRLF's `\\r` included, while every `\\n` stays where it was. Everything else is byte-identical,
    so `len(out) == len(command)` and any offset found on the result is an offset into the RAW
    command: `command[m.start():m.end()] == m.group()` for a match `m` of non-blank text.

    Prefer it over `strip_heredoc_bodies` whenever the caller SLICES the raw command, or compares
    positions, at offsets it found on the scanned text. The stripped text has lost lines, so an
    offset from it points at a different character in the raw command and nothing raises. The two
    agree on every match confined to one kept line; only a pattern spanning a body differs, since
    the stripped text makes the opener line adjacent to the line after the terminator while here
    the blank lines stay in between.

    `mask_data_regions` knows nothing about heredocs, so running it on the result does not re-open
    the body: the opener's quoted delimiter is masked like any quoted word, and the blanked body is
    whitespace to it, so an apostrophe or `(` that was in the body can no longer open a region.
    `commands_only_aligned` is that pairing in one call.
    """
    command = command or ""
    lines = command.split("\n")
    for _at, _opener, (start, end) in iter_heredocs(command):
        for index in range(start, min(end + 1, len(lines))):   # end is the terminator, if any
            lines[index] = " " * len(lines[index])
    return "\n".join(lines)


def heredoc_bodies(command: str) -> str:
    """Exactly what `strip_heredoc_bodies` removes: the heredoc bodies, openers and terminators
    excluded, several joined by newlines, and "" when the command opens none.

    A body is data when judging what RUNS, which is why it is stripped there. It is also where a
    program gets AUTHORED, and a chore hand-rolled inside one is invisible to every rule that only
    ever sees the stripped text.
    """
    return "\n".join(_split_heredocs(command)[1])


def blank_unexpanded_text(command: str, *, tool_name="Bash") -> str:
    """Blank the regions the shell will neither execute nor expand, keeping structure intact.

    A heredoc is not the only data region in a command. These three are just as inert, and a guard
    that scans them fires on text merely DESCRIBING a footgun:

    - a BACKSLASH-ESCAPED character (`\\$?`), which bash passes through literally;
    - a SINGLE-quoted string, where no expansion happens at all, and an ANSI-C `$'...'` one;
    - a `#` comment, which is never executed.

    A DOUBLE-quoted string is deliberately left alone: `$?` expands there, so `echo "rc=$?"` is a
    genuine status read. That also means prose inside double quotes remains indistinguishable from
    the real thing - the two are identical to the shell, so no scanner can separate them.

    A caller asking about STATEMENT STRUCTURE rather than expansions wants the opposite treatment
    of the same characters, and `mask_data_regions` below is that function - not a flag here.

    Blanking to spaces rather than deleting keeps offsets, line structure and every pipe, `;` and
    `&&` outside the quotes, so callers that split on those still see the same command shape.

    `tool_name` picks the escape character, by the rule `mask_data_regions` states: under
    PowerShell a BACKTICK escapes (inside double quotes too), a backslash is a path separator and
    there is no ANSI-C string. Read as Bash, `"C:\\temp\\"` never closed, so a single-quoted `$?`
    after it stayed visible, and the escaped quotes of `` `'$?`' `` were read as a single-quoted
    string, blanking a status read that really expands. Any other value, None included, is the
    Bash reading - what every caller got before the keyword existed.
    """
    powershell = tool_name == "PowerShell"
    escape = "`" if powershell else "\\"
    out: list[str] = []
    index, size = 0, len(command)
    in_single = in_double = False
    # Whether a `#` may open a comment is decided by the character BEFORE it as bash reads it, and
    # an escaped pair is blanked to spaces here - so the blank alone said "word start" and `a\ #b`,
    # one word to bash, lost the rest of its line. `word_at` marks the out-position just past an
    # escaped character (mid-word); a continuation is deleted before bash splits words, so what
    # decides after one is the character before its backslash (`cont_prev`, valid at `cont_at`).
    word_at = cont_at = -1
    cont_prev = ""
    in_backtick = False
    while index < size:
        char = command[index]
        if in_single:
            out.append(char if char in "'\n" else " ")
            in_single = char != "'"
            index += 1
        elif char == escape and index + 1 < size and not in_double:
            if command[index + 1] == "\n":
                cont_prev = cont_prev if len(out) == cont_at else (out[-1][-1:] if out else "")
                out.append(" \n")
                cont_at = len(out)
            else:
                out.append("  ")
                word_at = len(out)
            index += 2
        elif command.startswith("$$", index):
            out.append("$$")                   # the PID: its second `$` does not open `$'...'`
            index += 2
        elif not powershell and not in_double and command.startswith("$'", index):
            # ANSI-C `$'...'` expands nothing either, and its `\'` does not close it.
            stop = _ansi_c_end(command, index + 2)
            closed = stop > index + 2 and command[stop - 1] == "'"
            body = command[index + 2:stop - 1 if closed else stop]
            out.append("$'" + "".join(c if c == "\n" else " " for c in body) + ("'" if closed else ""))
            index = stop
        elif in_double:
            if char == escape and index + 1 < size:
                out.append("  " if command[index + 1] != "\n" else " \n")
                index += 2
                continue
            in_double = char != '"'
            out.append(char)
            index += 1
        elif char == "'":
            in_single = True
            out.append(char)
            index += 1
        elif char == '"':
            in_double = True
            out.append(char)
            index += 1
        elif char == "#" and _hash_starts_a_word(out, word_at, cont_at, cont_prev):
            # Inside a backtick substitution the comment also ends at the closing backtick, since
            # bash cuts the substitution out before parsing it: blanking on to the newline hid the
            # `$?` of `echo \`ls #x\`; echo $?`.
            stop = _comment_end(command, index, size, in_backtick)
            out.append(" " * (stop - index))
            index = stop
        else:
            in_backtick ^= char == "`" and not powershell
            out.append(char)
            index += 1
    return "".join(out)


def _hash_starts_a_word(out, word_at, cont_at, cont_prev):
    """Whether a `#` appended at position len(out) of a blanking walk begins a word, and so a
    comment. `word_at` / `cont_at` are the out-positions just past an escaped character and just
    past a line continuation; `cont_prev` is the character before that continuation's backslash."""
    if not out:
        return True
    if len(out) == word_at:
        return False                           # right after an escaped character: mid-word
    if len(out) == cont_at:
        return not cont_prev or cont_prev.isspace()
    return out[-1].isspace()


# The two quoting contexts `_quoting_end` walks. A frame is `[kind, open_parens]`; the paren count
# is only used by a substitution, where `$(( ))` arithmetic and subshells nest plain parentheses.
_DOUBLE_QUOTE, _SUBSTITUTION = "double-quote", "substitution"


def _quoting_end(text, start, context, escape, bash_quoting):
    """Index just past the character that closes a `"..."` string or a `$(...)` substitution
    whose body starts at `start`; an unterminated one runs to the end, as bash keeps reading.

    Each context has its own quoting, and they nest: a `$(...)` inside a double-quoted string
    opens a fresh one, so `"$(echo ")")"` is ONE string, and a `)` written inside quotes within a
    substitution does not close it. A depth count that ignored quoting closed
    `$(grep -l "mem:$s)" f | wc -l)` at the quoted `)`, and the quote after it then ran to the end
    of the command, hiding every later statement. The walk keeps an explicit stack rather than
    recursing, so a pathologically nested command cannot exhaust Python's recursion limit.
    """
    stack = [[context, 0]]
    index, size = start, len(text)
    while stack and index < size:
        if escape and text[index] == escape and index + 1 < size:
            index += 2
            continue
        if stack[-1][0] == _DOUBLE_QUOTE:
            index = _double_quote_step(text, index, stack)
        else:
            index = _substitution_step(text, index, stack, bash_quoting)
    return size if stack else index


def _double_quote_step(text, index, stack):
    """One step inside a double-quoted string: only its closing quote and a `$(` mean anything."""
    if text[index] == '"':
        stack.pop()
        return index + 1
    if text.startswith("$(", index):
        stack.append([_SUBSTITUTION, 0])
        return index + 2
    return index + 1


def _substitution_step(text, index, stack, bash_quoting):
    """One step inside `$(...)`: quotes and comments are skipped whole, parentheses are counted."""
    char = text[index]
    if text.startswith("$(", index):
        stack.append([_SUBSTITUTION, 0])
        return index + 2
    if bash_quoting and text.startswith("$$", index):
        return index + 2                       # the PID: its second `$` does not open `$'...'`
    if bash_quoting and text.startswith("$'", index):
        return _ansi_c_end(text, index + 2)
    if char == "'":
        closing = text.find("'", index + 1)
        return len(text) if closing == -1 else closing + 1
    if char == '"':
        stack.append([_DOUBLE_QUOTE, 0])
        return index + 1
    if char == "#" and (index == 0 or text[index - 1].isspace() or text[index - 1] in ";&|("):
        newline = text.find("\n", index)     # a comment's apostrophe is not a quote
        return len(text) if newline == -1 else newline
    return _paren_step(text, index, stack)


def _paren_step(text, index, stack):
    """Count a plain parenthesis inside a substitution; the unmatched `)` closes it."""
    frame = stack[-1]
    if text[index] == "(":
        frame[1] += 1
    elif text[index] == ")":
        if frame[1]:
            frame[1] -= 1
        else:
            stack.pop()
    return index + 1


def mask_data_regions(command: str, fill: str = "Q", tool_name="Bash") -> str:
    """Replace every region that cannot affect STATEMENT STRUCTURE with a filler character.

    `blank_unexpanded_text` above answers "will the shell expand this?" and therefore must leave
    double-quoted text intact. A guard reading statement structure asks a different question, and
    for it the answer is unambiguous: whatever the shell does with `$?` inside
    `git commit -m "wip; git push"`, that `;` is not a separator and those words are not a command.

    Four regions are masked, each including its own delimiters:

    - single- and double-quoted strings, and ANSI-C `$'...'` strings (where `\\'` does not close);
    - `$(...)` command substitution and `$((...))` arithmetic, depth-counted so nesting survives,
      with the quotes inside them honoured (see `_quoting_end`);
    - `${...}` parameter expansion and `@{...}` revspecs, whose braces are a word, not a
      brace GROUP - `git rev-list @{u}...HEAD` must not read as shell structure;
    - backtick substitution;
    - `#` comments (masked to spaces, since a comment genuinely ends the line).

    Delimiters are masked TOO, which is the difference that matters. Blanking only the content
    leaves the quote characters behind, and `"$MAIN"` then splits into two bare `"` tokens - so a
    parser walking `git -C "$MAIN" commit` reads the option value as `"`, loses the subcommand, and
    silently concludes the statement is not a git command at all. Masking the whole region keeps it
    one token, which is exactly what the shell passes.

    Length is preserved so offsets still line up. Newlines INSIDE a masked region are replaced as
    well: a newline in a quoted commit message is not a statement separator, and leaving it would
    manufacture one.

    `tool_name` picks the escape character, by the rule `_iter_separators` states: under Bash a
    backslash escapes and a backtick substitutes; under PowerShell a BACKTICK escapes and a
    backslash is a path separator, and there is no ANSI-C string. Reading `\\` as an escape under
    PowerShell masked the `;` of `cd C:\\; git commit` and closed no quote at `"C:\\temp\\"`, so the
    statement after it never reached a guard. An unrecognised tool escapes nothing.

    An ABSENT tool (`None`) is the Bash reading, not an unrecognised one. Callers pass None when
    they have no event to ask - a pure helper's default - and escaping nothing there is wrong in
    both directions at once: the `\\"` of `"a\\" > b.md; c"` closed the string, so a redirection
    appeared inside it, and `echo \\"; git push; echo \\"` masked a push that really runs.
    """
    escape = {"Bash": "\\", "PowerShell": "`", None: "\\"}.get(tool_name, "")
    bash_quoting = tool_name != "PowerShell"
    out: list[str] = []
    index, size = 0, len(command)
    cont_at, cont_prev = -1, ""                # see blank_unexpanded_text: `a\<nl>#b` is one word
    while index < size:
        char = command[index]
        if escape and char == escape and index + 1 < size:
            # An escaped NEWLINE is a line continuation: it must become whitespace, not filler,
            # or the two tokens it joins fuse into one word that no longer reads as a command.
            if command[index + 1] == "\n":
                cont_prev = cont_prev if len(out) == cont_at else (out[-1][-1:] if out else "")
                out.append("  ")
                cont_at = len(out)
            else:
                out.append(fill * 2)
            index += 2
        elif bash_quoting and command.startswith("$$", index):
            out.append("$$")                   # the PID: its second `$` does not open `$'...'`
            index += 2
        elif bash_quoting and command.startswith("$'", index):
            # ANSI-C quoting: a backslash escapes here, so `\'` does not close the string. Scanned
            # as a plain single quote it closed early and the next `'` masked the rest of the line.
            stop = _ansi_c_end(command, index + 2)
            out.append(fill * (stop - index))
            index = stop
        elif char == "'":
            closing = command.find("'", index + 1)   # single quotes have no escape
            stop = size if closing == -1 else closing + 1
            out.append(fill * (stop - index))
            index = stop
        elif char == '"':
            # Scan for the CLOSING quote rather than the next one: `\"` is an escaped quote, and a
            # `$(...)` inside the string opens its own quoting, so `"$(echo ")")"` is ONE string.
            stop = _quoting_end(command, index + 1, _DOUBLE_QUOTE, escape, bash_quoting)
            out.append(fill * (stop - index))       # unterminated quote runs to the end
            index = stop
        elif char == "`" and bash_quoting:
            closing = command.find("`", index + 1)
            stop = size if closing == -1 else closing + 1
            out.append(fill * (stop - index))
            index = stop
        elif command.startswith("${", index) or command.startswith("@{", index):
            closing = command.find("}", index + 2)
            stop = size if closing == -1 else closing + 1
            out.append(fill * (stop - index))
            index = stop
        elif command.startswith("$(", index):
            stop = _quoting_end(command, index + 2, _SUBSTITUTION, escape, bash_quoting)
            out.append(fill * (stop - index))
            index = stop
        elif char == "#" and _hash_starts_a_word(out, -1, cont_at, cont_prev):
            while index < size and command[index] != "\n":
                out.append(" ")
                index += 1
        else:
            out.append(char)
            index += 1
    return "".join(out)


# The programs that do NOT execute their arguments. This list is the whole safety argument, so it
# stays closed and small: every entry has to be a program whose operand is stored or printed, never
# run. `echo`/`printf` write it to stdout; `git commit` records it in an object; `gh pr create`
# posts it to an API. None of them hands the text to a shell.
_DATA_SINK_PROGRAMS = frozenset({"echo", "printf"})

# PowerShell's own printing cmdlets, which are what `echo` is under Bash (`echo` itself is an alias
# of Write-Output there). Scoped to the PowerShell tool, and compared case-insensitively because
# PowerShell resolves command names that way: under Bash these names are whatever script happens
# to carry them.
_POWERSHELL_SINK_CMDLETS = frozenset({"write-host", "write-output"})

# Programs where the SUBCOMMAND decides. `git commit -m` stores its text, while `git bisect run`
# executes its argument - so the program name alone is not enough and matching on it would blank a
# statement that really does run a command. Each entry is a prefix of the non-flag operands.
_DATA_SINK_SUBCOMMANDS = {
    "git": (("commit",),),
    "gh": (("pr", "create"),),
    # Writes its `--hook`/`--title`/`--body-file` text into a memory fact and never runs it. Added
    # 2026-08-30 after a corpus replay found it was the ONLY real false positive left in the sed
    # nudge: the tool that records a footgun tripped the guard for that footgun. Only `add` is
    # listed - `reconcile`, `heal` and `move` take paths, and nothing proves them inert.
    "memory_engine.py": (("add",),),
}

# Programs that run a SCRIPT NAMED AS A SEPARATE TOKEN, so the sink is the script and not them.
# `bash run-python.sh .../memory_engine.py add` has three of these stacked in front of the program
# that decides.
#
# What makes stepping past them safe is that the walk HALTS at the first token that is not itself a
# launcher, and whatever it halts on must STILL be in the tables above to have any effect. So the
# blast radius is exactly the scripts listed there, and every other shape falls through to "not a
# sink" - the direction that keeps a false positive rather than deleting a finding.
#
# `bash -c '<text>'` is therefore handled twice over, and the explicit `-c` test below is belt and
# braces rather than the load-bearing part: without it the walk simply halts on `-c`, which is not
# in the tables either. Worth knowing before anyone "simplifies" the walk to skip flags, because
# that is the change the doubling exists to survive.
_SCRIPT_LAUNCHERS = frozenset({"bash", "sh", "python", "python3", "py", "run-python.sh"})

# `$(` and a backtick RUN what they enclose, wherever they sit. `${...}` does not, and neither does
# a substitution written inside single quotes - but telling those apart needs the quoting state,
# and getting that wrong here would blank a statement that executes something. A sink carrying
# either spelling is therefore left intact: the cost is a false positive that was already there,
# and the alternative cost is a miss.
_RUNS_SUBSTITUTION = re.compile(r"\$\(|`")

# PowerShell also EVALUATES `@(...)` (the array subexpression) in argument mode. A bare `(...)`
# needs no entry because it already ends the segment, so the sink's blanking never reaches it -
# but `@(` does not, and `echo @(pkill -f x)` was blanked whole. Under Bash `@(...)` is an extglob
# pattern and runs nothing, so this reading is the PowerShell tool's alone.
_RUNS_SUBSTITUTION_POWERSHELL = re.compile(r"[$@]\(|`")


def _cut_by_substitution(text: str, at: int, segment: str) -> bool:
    """True when this segment ends because a substitution opened, not because a statement ended.

    `iter_segments` treats the inside of `$(...)` as real statements, which it is - so `echo $(cmd)`
    arrives as the three pieces `echo `, `cmd` and `)`. The first looks exactly like a complete,
    inert `echo`, and blanking it would delete the surrounding context of a command that DOES run.
    Testing the segment for a substitution cannot see this: the `$(` was consumed as the boundary
    and is not in the segment at all.

    Measured while writing this: `echo "$(pkill -f foo)"` appeared to be handled correctly, but only
    because `echo "` has an unbalanced quote that shlex rejects. The unquoted `echo $(pkill -f foo)`
    parses cleanly and was blanked.
    """
    return _RUNS_SUBSTITUTION.match(text, at + len(segment)) is not None


def _deciding_program_index(tokens, tool_name):
    """Index of the token that decides what this statement DOES, or None.

    Two things sit in front of it and neither changes the answer: leading `VAR=value` environment
    assignments, and launchers that take their script as a separate token. Both were measured in
    one real corpus command, `BITRANOX_RUN_PYTHON_STRICT=1 bash .../run-python.sh
    .../memory_engine.py add --hook "..."`, where the old reading took the ASSIGNMENT as the
    program name.

    The walk stops at the first token that is not a launcher, so the result must still be in the
    sink tables to matter. It deliberately does NOT scan the whole token list for a known name:
    `ssh host 'memory_engine.py add ...'` would match such a scan, and blanking it would delete a
    real finding, which is the one direction this module must never fail in.

    A flag between a launcher and its script (`python3 -u .../memory_engine.py add`) halts the walk
    at the launcher, so that shape is NOT recognised as a sink. Left deliberately: it fails in the
    safe direction, keeping a false positive, and the corpus replay that motivated this entry did
    not contain it. Widen it when one is measured, not before.
    """
    at = 0
    while at < len(tokens) and "=" in tokens[at] and not tokens[at].startswith("-"):
        at += 1                                     # leading VAR=value environment assignments
    for _ in range(len(_SCRIPT_LAUNCHERS)):         # bounded: no launcher chain is longer
        if at >= len(tokens):
            return None
        if basename_for_tool(tokens[at], tool_name) not in _SCRIPT_LAUNCHERS:
            return at
        nxt = at + 1
        if nxt >= len(tokens) or tokens[nxt].startswith("-"):
            return at                               # `-c` and friends run TEXT, not a named script
        if any(char.isspace() for char in tokens[nxt]):
            return at                               # a quoted command string, not a script path
        at = nxt
    return at


def _sink_keep_words(segment: str, tool_name=None) -> int:
    """How many leading words to KEEP when this statement is a data sink; 0 when it is not.

    The VERB is kept and only its operands are blanked, which matters for a reason none of the
    current callers show: a hook that detects `git commit` could adopt this helper and go blind to
    the verb it gates, silently, with nothing in the diff to point at. Keeping the program name
    also removes strictly less text, so it cannot turn a false positive into a miss.

    For a mapped program the count runs to the end of the matched SUBCOMMAND, skipping flags on the
    way - `git -q commit -m x` keeps three words, not one.
    """
    runs = _RUNS_SUBSTITUTION_POWERSHELL if tool_name == "PowerShell" else _RUNS_SUBSTITUTION
    if runs.search(segment):
        return 0
    head = segment.strip().lstrip("(").strip()
    if not head:
        return 0
    try:
        tokens = split_for_tool(head, tool_name or "Bash")
    except ValueError:
        # Unbalanced quotes. The text cannot be read as argv, so nothing here is provably inert.
        return 0
    if not tokens:
        return 0
    at = _deciding_program_index(tokens, tool_name or "Bash")
    if at is None:
        return 0
    program = basename_for_tool(tokens[at], tool_name or "Bash")
    if program in _DATA_SINK_PROGRAMS:
        return at + 1
    if tool_name == "PowerShell" and program.lower() in _POWERSHELL_SINK_CMDLETS:
        return at + 1
    for prefix in _DATA_SINK_SUBCOMMANDS.get(program, ()):
        matched, wanted = 0, len(prefix)
        for position, token in enumerate(tokens[at + 1:], start=at + 2):
            if token.startswith("-"):
                continue                              # a flag, or a flag's own value
            if token != prefix[matched]:
                break
            matched += 1
            if matched == wanted:
                return position
    return 0


def strip_data_sink_statements(command: str, tool_name=None) -> str:
    """Blank each statement whose program stores or prints its argument instead of running it.

    Three shipped nudges fired on `echo '<the footgun>'` and on a commit message describing one,
    because a quoted string that ssh EXECUTES and a quoted string that echo PRINTS are identical at
    the level of the quote. What separates them is the ENCLOSING program, which is what this reads.

    The allowlist is inverted on purpose. It names the programs that are provably inert, and an
    UNRECOGNISED program is treated as executing - so the only way to be wrong is to leave a false
    positive standing, never to go silent on a real footgun. That direction matters more than it
    looks: this repo has broken three guards by guessing at exactly this boundary, and each time
    the damage was a deleted finding rather than an extra warning.

    The PROGRAM NAME survives and only its operands are blanked, so a caller that asks a different
    question of the same text - did a `git commit` happen here? - still gets the right answer.

    Blanking is length-preserving, so a caller that already holds a match offset into the raw
    command can index the result at the same position - the same contract `mask_data_regions` has.

    NOT a replacement for `strip_heredoc_bodies`: a heredoc body is data for a different reason
    (it is stdin, whatever the program), and the two compose.
    """
    text = command or ""
    if not text:
        return text
    out = list(text)
    for at, segment in iter_segments(text, tool_name):
        if _cut_by_substitution(text, at, segment):
            continue
        keep = _sink_keep_words(segment, tool_name)
        if not keep:
            continue
        words = list(re.finditer(r"\S+", segment))
        if len(words) < keep:
            continue
        for index in range(at + words[keep - 1].end(), min(at + len(segment), len(out))):
            if out[index] != "\n":
                out[index] = " "
    return "".join(out)
