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
from __future__ import annotations

import re
import shlex
from pathlib import PurePosixPath, PureWindowsPath

# The opener forms bash accepts: `<<WORD`, `<<-WORD`, `<< WORD`, `<<'WORD'`, `<<"WORD"`. The
# backreference keeps the quoting symmetric, so `<<'EOF"` is not read as a quoted delimiter.
#
# The lookarounds exclude the HERE-STRING `<<< word`, which feeds one word on stdin and opens no
# body. Unguarded, its last two `<` read as `<< word`, and since a body runs to its delimiter every
# later line of the command was dropped as data - a `git push` on the next line included.
HEREDOC_OPEN = re.compile(r"(?<!<)<<(?!<)-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

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
SEP = re.compile(r"&&|\|\||[;\n|]|" + _LONE_AMPERSAND)
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
            newline = text.find("\n", i)
            i = n if newline == -1 else newline
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
            _closer, in_single, in_double = depth.pop()
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
            in_single = in_double = False
            i += 1
            continue
        if in_double:
            i += 1                             # a plain separator is literal in double quotes
            continue
        if two in ("&&", "||"):
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
_GATED_GIT_VERBS = frozenset({"commit", "push"})


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
_COMMAND_PREFIXES = frozenset({
    "nice", "ionice", "timeout", "sudo", "doas", "env", "stdbuf",
    "nohup", "setsid", "chrt", "taskset", "time",
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


def _past_command_prefix(tokens, idx, tool_name):
    """Index of `git` when a known launcher runs it, else None.

    Scans forward for a token whose basename is EXACTLY `git`, which is narrow enough to stay a
    statement walk rather than the bag-of-tokens test this module replaced. The two shapes that
    would abuse a looser scan cannot reach it: `nice -n 19 echo "git commit"` and `timeout 30 ssh
    host 'git commit'` keep the whole quoted command as ONE token, whose basename is the entire
    string and never `git`.

    Starting only after a KNOWN launcher is what bounds it. `ssh host '...'` is not one, so the
    scan never begins there - the same reason `_deciding_program_index` refuses to scan the token
    list for a script name.
    """
    limit = min(len(tokens), idx + 1 + _PREFIX_SCAN_LIMIT)
    for at in range(idx + 1, limit):
        if basename_for_tool(tokens[at], tool_name) == "git":
            return at
    return None


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
    idx = 0
    while idx < len(tokens) and (
        tokens[idx] in _STATEMENT_KEYWORDS
        or ("=" in tokens[idx] and not tokens[idx].startswith("-"))
    ):
        idx += 1                                  # loop/branch keywords, then VAR=value env prefix
    if idx < len(tokens) and basename_for_tool(tokens[idx], tool_name) in _COMMAND_PREFIXES:
        idx = _past_command_prefix(tokens, idx, tool_name)
    if idx is None or idx >= len(tokens) or basename_for_tool(tokens[idx], tool_name) != "git":
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
    """
    try:
        return split_for_tool(segment, tool_name)
    except ValueError:
        return segment.split()


def is_git_verb(segment, verbs, tool_name="Bash"):
    """True when `segment` is a `git <global opts> <verb>` command for one of `verbs`."""
    return git_verb_operands(argv_for_match(segment, tool_name), verbs, tool_name) is not None


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
        if is_git_verb(seg, _GATED_GIT_VERBS, tool_name or "Bash") or PR_RE.match(seg):
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


def commands_only(command: str) -> str:
    """`command` with every DATA region removed, leaving only text the shell will EXECUTE.

    The pairing every command-scanning guard needs, in one call. Each half alone leaves a hole the
    other closes, and both holes have shipped: `mask_data_regions` cannot see a heredoc BODY,
    because a body is not quoted, so a `git -C /elsewhere` written into a runbook read as the repo
    the command acts on; `strip_heredoc_bodies` cannot see a quoted ARGUMENT, so `echo 'pgrep -f x'`
    read as an invocation. A guard that calls only one is not half-safe, it is wrong in whichever
    direction it skipped - and which half was skipped is invisible at the call site, which is why
    this exists instead of the two-call idiom.

    Offsets do NOT survive: the heredoc strip removes lines. A caller that needs POSITIONS (to tell
    a write before the verb from one after it) must use `mask_data_regions` and handle heredocs
    itself - `gated-prep-nudge` is the one that does.

    NOT for every guard, and the exception is not an edge case. A quoted string is data to the
    LOCAL shell and a COMMAND to a remote one, so a guard whose subject is `ssh host \'...\'`,
    `bash -c \'...\'` or any other execute-this-string form must NOT mask quotes - that deletes
    exactly what it is looking for. Measured: routing `warn-inline-powershell` through this made
    `ssh host \'powershell -command "x"\'` stop firing and took six tests with it. Those guards
    want `strip_heredoc_bodies` alone. Ask what the guard's subject IS before reaching for this.
    """
    return mask_data_regions(strip_heredoc_bodies(command or ""))


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
    every reader of heredocs uses it, so none can disagree about where a body starts.

    The regex knows the opener's SYNTAX; where a `<<` sits decides whether it is one, and two
    places make it something else:

    - a QUOTED argument, a comment or a substitution: `git commit -m "docs: explain <<EOF
      heredocs"` opens nothing, and reading it as an opener swallowed the rest of the command, so
      every guard downstream went silent on a real `git push` after it;
    - ARITHMETIC, where `<<` is a left shift: `(( z = x << y ))` and `$((1 << n))` read as a
      heredoc delimited by `y` or `n`, and every later line up to one spelling it was dropped.

    The test is whether the `<<` ITSELF sits in such a region, so a quoted mention does not hide a
    real opener later on the same line. Quoting is read over the whole remaining text, not line by
    line: a string can span lines (`python3 -c "...` with `\\"cat <<EOF\\"` inside it), and a line
    read alone loses the quote it is in. The walk restarts after each body, because a body is data
    and an apostrophe in it would otherwise open a quote that hides the next opener. The delimiter
    is read from the RAW match: masking hides the quotes of `<<'EOF'`, which are heredoc syntax
    rather than a string, and reading the masked form made that opener look bare.
    """
    lines = (command or "").split("\n")
    index = 0
    while index < len(lines):
        found = _next_opener(lines, index)
        if found is None:
            return
        at, opener = found
        end = at + 1
        # The terminator is the first line that is exactly the delimiter; bash allows leading
        # whitespace with the `<<-` form, so the comparison is made on the stripped line.
        while end < len(lines) and lines[end].strip() != opener.group(2):
            end += 1
        yield at, opener, (at + 1, end)
        index = end + 1


def _next_opener(lines, start):
    """(line index, match) of the first real heredoc opener at or after line `start`, or None."""
    if not any("<<" in line for line in lines[start:]):
        return None
    masked = _blank_arithmetic(mask_data_regions("\n".join(lines[start:])))
    offset = 0
    for index in range(start, len(lines)):
        line = lines[index]
        region = masked[offset:offset + len(line)]
        for match in HEREDOC_OPEN.finditer(line):
            if region[match.start():match.start() + 2] == "<<":
                return index, match
        offset += len(line) + 1
    return None


def find_heredoc_opener(line: str):
    """The `HEREDOC_OPEN` match for the first `<<` on `line` that opens a heredoc, or None."""
    for _at, opener, _body in iter_heredocs(line):
        return opener
    return None


def _blank_arithmetic(masked: str) -> str:
    """`masked` with every bare `(( ... ))` arithmetic command blanked, length preserved.

    Only the bare form is left for this to find: `mask_data_regions` already fills `$(( ))`. At
    the start of a command bash reads `((` as arithmetic, so a subshell inside a subshell has to be
    written `( (`, and a `((` here is arithmetic. An unclosed one is blanked to the end of its
    line only, so a stray `((` cannot hide every opener after it.
    """
    out = list(masked)
    start = masked.find("((")
    while start != -1:
        depth, cursor, closed = 0, start, False
        while cursor < len(masked):
            if masked[cursor] == "(":
                depth += 1
            elif masked[cursor] == ")":
                depth -= 1
                if depth == 0:
                    cursor += 1
                    closed = True
                    break
            cursor += 1
        if not closed:
            newline = masked.find("\n", start)
            cursor = len(masked) if newline == -1 else newline
        for index in range(start, cursor):
            out[index] = " "
        start = masked.find("((", cursor)
    return "".join(out)


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


def heredoc_bodies(command: str) -> str:
    """Exactly what `strip_heredoc_bodies` removes: the heredoc bodies, openers and terminators
    excluded, several joined by newlines, and "" when the command opens none.

    A body is data when judging what RUNS, which is why it is stripped there. It is also where a
    program gets AUTHORED, and a chore hand-rolled inside one is invisible to every rule that only
    ever sees the stripped text.
    """
    return "\n".join(_split_heredocs(command)[1])


def blank_unexpanded_text(command: str) -> str:
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
    """
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
    while index < size:
        char = command[index]
        if in_single:
            out.append(char if char in "'\n" else " ")
            in_single = char != "'"
            index += 1
        elif char == "\\" and index + 1 < size and not in_double:
            if command[index + 1] == "\n":
                cont_prev = cont_prev if len(out) == cont_at else (out[-1][-1:] if out else "")
                out.append(" \n")
                cont_at = len(out)
            else:
                out.append("  ")
                word_at = len(out)
            index += 2
        elif not in_double and command.startswith("$'", index):
            # ANSI-C `$'...'` expands nothing either, and its `\'` does not close it.
            stop = _ansi_c_end(command, index + 2)
            closed = stop > index + 2 and command[stop - 1] == "'"
            body = command[index + 2:stop - 1 if closed else stop]
            out.append("$'" + "".join(c if c == "\n" else " " for c in body) + ("'" if closed else ""))
            index = stop
        elif in_double:
            if char == "\\" and index + 1 < size:
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
            while index < size and command[index] != "\n":
                out.append(" ")
                index += 1
        else:
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


def mask_data_regions(command: str, fill: str = "Q", tool_name="Bash") -> str:
    """Replace every region that cannot affect STATEMENT STRUCTURE with a filler character.

    `blank_unexpanded_text` above answers "will the shell expand this?" and therefore must leave
    double-quoted text intact. A guard reading statement structure asks a different question, and
    for it the answer is unambiguous: whatever the shell does with `$?` inside
    `git commit -m "wip; git push"`, that `;` is not a separator and those words are not a command.

    Four regions are masked, each including its own delimiters:

    - single- and double-quoted strings, and ANSI-C `$'...'` strings (where `\\'` does not close);
    - `$(...)` command substitution and `$((...))` arithmetic, depth-counted so nesting survives;
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
    """
    escape = {"Bash": "\\", "PowerShell": "`"}.get(tool_name, "")
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
        elif bash_quoting and command.startswith("$'", index):
            # ANSI-C quoting: a backslash escapes here, so `\'` does not close the string. Scanned
            # as a plain single quote it closed early and the next `'` masked the rest of the line.
            stop = _ansi_c_end(command, index + 2)
            out.append(fill * (stop - index))
            index = stop
        elif char in "'\"":
            # Scan for the CLOSING quote rather than the next one: inside a double-quoted region
            # `\"` is an escaped quote, and `find` would stop there, leaving the rest of a commit
            # message to be scanned as shell. Single quotes have no escape, so only `"` looks.
            cursor = index + 1
            while cursor < size:
                if char == '"' and escape and command[cursor] == escape and cursor + 1 < size:
                    cursor += 2
                    continue
                if command[cursor] == char:
                    cursor += 1
                    break
                cursor += 1
            out.append(fill * (cursor - index))       # unterminated quote runs to the end
            index = cursor
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
            depth, cursor = 0, index
            while cursor < size:
                if command.startswith("$(", cursor):
                    depth += 1
                    cursor += 2
                    continue
                if command[cursor] == "(":
                    depth += 1                    # arithmetic `$(( ))` and nested subshells
                    cursor += 1
                    continue
                if command[cursor] == ")":
                    depth -= 1
                    cursor += 1
                    if depth == 0:
                        break
                    continue
                cursor += 1
            out.append(fill * (cursor - index))
            index = cursor
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
    if _RUNS_SUBSTITUTION.search(segment):
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
