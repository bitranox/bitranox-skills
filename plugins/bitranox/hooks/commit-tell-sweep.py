#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard against AI-writing typographic / invisible tells in a git
commit / merge / tag MESSAGE passed inline.

The `tell-sweep` PostToolUse hook catches tells in prose FILES, but a commit message
(`git commit -m "..."`) is not a file edit, so it slips through - and a commit message is
exactly where an em-dash or a curly quote leaks into permanent git history. This hook scans
the inline message of any git command (`-m`/`--message`, or the file named by `-F`/`--file`)
using the SAME `tell_chars.RANGES`, and BLOCKS the commit before it runs so the message can be
fixed. Tells inside backtick code spans are ignored (a message that references the character
itself in backticks is fine).

It cannot see an editor-composed message (a bare `git commit` opens $EDITOR after the tool
returns) - that path relies on the humanizer skill; the inline `-m`/`-F` form is the common
Claude Code case and the one this closes.

It also BLOCKS an AI attribution line - a `Co-Authored-By:` trailer naming Claude or Anthropic, or
a `Generated with Claude Code` footer - in the same git messages and in the body of a `gh pr`
command (`--body`/`-b`, `--body-file`/`-F`, including a stdin heredoc). Commits and PRs carry human
authorship only; the harness asks for that trailer in every session, and a written rule kept losing
to it (16 of 30 commits in one repo carried it). A Linux-kernel `Assisted-by: Claude:<model>`
trailer is a different line and passes. A PR body gets only this check, not the tell check.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the call and
shows stderr to the model; every other path (including any error) exits 0, so a broken guard
never wedges a turn.
"""
import collections
import json
import os
import posixpath
import re
import sys

import shell_text
import tell_chars


# git short options that CONSUME a value, so whatever follows them INSIDE a cluster is that value
# rather than another flag: in `-Cm` the `m` is `-C`'s argument (reuse commit "m"), not the message
# flag, and reading the next token as a message there would block a commit that carries none.
#
# Deliberately tuned for `git commit`, not per-subcommand, and that is a known limit rather than an
# oversight: `-s` is `--signoff` here and takes no value, which is what lets `-sm "msg"` work, but
# in `git merge` the same letter is `--strategy` and does take one. So `git merge -sm ours` is read
# as a message where git reads it as a strategy. Accepted because reaching a wrong verdict from it
# needs a strategy or branch name containing a typographic tell, and commit is nearly all of the
# traffic this hook sees. Splitting the set per subcommand means parsing the subcommand first.
_VALUE_SHORT = "cCFmStu"

# text plus the two facts that decide how a hit in it may be REPORTED: `from_file` (a -F file's
# lines are never quoted back) and `bad_byte` (its own finding). Bundled so a new call site cannot
# carry the text without them and silently pick the unsafe form. `path` is None for an inline -m
# value; echoing a -F path is safe, the caller typed it in the command.
Message = collections.namedtuple("Message", "text from_file bad_byte path")

# A co-author trailer naming Claude or an anthropic.com address, or the Claude Code footer. A plain
# mention ("fix the Claude Code hook", "drop the `Generated with Claude Code` footer") and a human
# co-author are not attribution, so both are matched as WHOLE lines: the trailer only with
# Claude/Anthropic in it, the footer only with nothing but punctuation or an emoji around it.
_ATTRIBUTION = re.compile(
    r"^[ \t]*co-authored-by:[^\n]*\b(?:claude|anthropic)\b"
    r"|^[^\w\n]*generated with \[?claude code\]?(?:\(https?://[^)\s]*\))?[^\w\n]*$",
    re.IGNORECASE | re.MULTILINE,
)


def _cluster(tok, toks, i):
    """What a single-dash short-option cluster carries: (kind, value, extra tokens consumed).

    `git commit -am "..."` and `-sm "..."` are the commonest commit forms there are, and both a
    `t in ("-m", "--message")` test and a `t.startswith("-m")` test miss them, because the flag
    sits in the MIDDLE of the cluster - so the message list came back empty and this guard
    approved a message it had never read. Scanning stops at the first value-taking option, which
    is what keeps `-Cm` from being misread as a message flag.

    `kind` is "msg", "file", or None.
    """
    body = tok[1:]
    for pos, ch in enumerate(body):
        if ch not in _VALUE_SHORT:
            continue
        if ch not in ("m", "F"):
            return None, None, 0          # -c/-C/-S/-t/-u swallow the rest as their own value
        kind = "msg" if ch == "m" else "file"
        rest = body[pos + 1:]
        if rest:                          # attached form: -m"msg" / -Fmsg.txt
            return kind, rest, 0
        if i + 1 < len(toks):             # separated form: -am "msg" / -F msg.txt
            return kind, toks[i + 1], 1
        return None, None, 0
    return None, None, 0


# A commit message file is a few lines. The cap bounds how much of a file this guard pulls in
# before its command has been approved, and no real message comes near it.
_MAX_MESSAGE_BYTES = 64 * 1024


def _read_message_file(path):
    """A Message for the file, or None when it cannot be read - a path we cannot open carries no
    tell. Capped: see `_MAX_MESSAGE_BYTES`."""
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_MAX_MESSAGE_BYTES)
    except OSError:
        return None
    text, bad_byte = tell_chars.decode_utf8(raw, truncated=len(raw) == _MAX_MESSAGE_BYTES)
    return Message(text, True, bad_byte, path)


# `-F`/`--file` values that name the COMMAND's standard input rather than a file. git reads the
# message from stdin for `-`, and the device paths reach the same descriptor. Opened inside this
# hook they would name the HOOK's stdin - the event pipe, already consumed - so the guard read
# nothing and approved a message it had never seen, which is how `git commit -F - <<'EOF'` (a
# recurring form: a quoted heredoc is the one inline route bash never expands) went unchecked.
_STDIN_PATHS = frozenset({"-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"})

# Tokens that end the statement a stdin redirect could belong to.
_STATEMENT_ENDS = frozenset({";", "&&", "||", "|", "&"})


def _argv(command, tool_name):
    """The command's argv, or None when it cannot be split.

    An apostrophe in a quoted heredoc body is plain text to bash, but a split of the RAW command
    reads it as an unterminated quote and raises, which used to blank every message in the
    command - an inline `-m` beside any such heredoc included. The raw split is tried first because
    it keeps a body that IS a message (`-m "$(cat <<'EOF' ... EOF)"`); only when it fails is the
    command re-split with heredoc bodies removed. A stdin message's body is read separately.
    """
    try:
        return shell_text.split_for_tool(command, tool_name)
    except ValueError:
        pass
    if tool_name == "PowerShell":
        return None
    try:
        return shell_text.split_for_tool(shell_text.strip_heredoc_bodies(command), tool_name)
    except ValueError:
        return None


def _message_flags(toks):
    """(kind, value, index) for every message-bearing flag in `toks`; kind is "msg" or "file"."""
    found, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t in ("--message", "--file") and i + 1 < len(toks):
            found.append(("msg" if t == "--message" else "file", toks[i + 1], i))
            i += 2
            continue
        if t.startswith("--message="):
            found.append(("msg", t.split("=", 1)[1], i))
        elif t.startswith("--file="):
            found.append(("file", t.split("=", 1)[1], i))
        elif t.startswith("-") and not t.startswith("--") and len(t) > 1:
            kind, value, extra = _cluster(t, toks, i)
            if kind is not None:
                found.append((kind, value, i))
            i += extra
        i += 1
    return found


def _reads_stdin_message(toks):
    """True when `toks` hold a git command whose message file is its own standard input."""
    return "git" in toks and any(kind == "file" and value in _STDIN_PATHS
                                 for kind, value, _ in _message_flags(toks))


def _redirected_stdin(toks, start):
    """The path a `< path` redirect feeds into the statement that begins at `start`, or None."""
    for i in range(start, len(toks)):
        t = toks[i]
        if t in _STATEMENT_ENDS:
            return None
        if t == "<" and i + 1 < len(toks):
            return toks[i + 1]
        if t.startswith("<") and not t.startswith("<<") and len(t) > 1:
            return t[1:]
    return None


def _logical_line(lines, at):
    """Line `at` joined with the backslash-continued lines before it, as bash reads one line."""
    first = at
    while first > 0 and lines[first - 1].endswith("\\"):
        first -= 1
    return " ".join(line.removesuffix("\\") for line in lines[first:at + 1])


def _stdin_heredoc_bodies(command, reads_stdin=_reads_stdin_message):
    """The bodies of the heredocs that feed a command whose message is its own stdin.

    A heredoc is the message when its opener sits on the same (logical) line as that command:
    `git commit -F - <<'EOF'` and `cat <<'EOF' | git commit -F -` both qualify. A heredoc on any
    other line feeds some other program - a script, a notes file - and is not the message.
    `reads_stdin` decides which command that is (a git message, or a gh PR body).
    """
    lines = command.split("\n")
    bodies = []
    for at, _opener, (start, end) in shell_text.iter_heredocs(command):
        line = _logical_line(lines, at)
        try:
            toks = shell_text.split_for_tool(line, "Bash")
        except ValueError:
            continue
        if reads_stdin(toks):
            bodies.append("\n".join(lines[start:end]))
    return bodies


def _is_gh_pr(toks):
    """True when `toks` hold a `gh pr ...` command."""
    return any(toks[i] == "gh" and toks[i + 1] == "pr" for i in range(len(toks) - 1))


def _gh_body_flags(toks):
    """(kind, value) for every body flag of a `gh pr` command; kind is "msg" or "file"."""
    if not _is_gh_pr(toks):
        return []
    found, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t in ("--body", "-b", "--body-file", "-F") and i + 1 < len(toks):
            found.append(("msg" if t in ("--body", "-b") else "file", toks[i + 1]))
            i += 2
            continue
        if t.startswith("--body="):
            found.append(("msg", t.split("=", 1)[1]))
        elif t.startswith("--body-file="):
            found.append(("file", t.split("=", 1)[1]))
        elif t[:2] in ("-b", "-F") and len(t) > 2:
            found.append(("msg" if t[1] == "b" else "file", t[2:]))
        i += 1
    return found


def _reads_stdin_body(toks):
    """True when `toks` hold a `gh pr` command whose body file is its own standard input."""
    return any(kind == "file" and value in _STDIN_PATHS for kind, value in _gh_body_flags(toks))


def _gh_bodies(command, tool_name="Bash"):
    """The PR bodies a `gh pr` command sends: `--body` values, `--body-file` contents, and the
    heredoc feeding `--body-file -`. Empty unless the command is a `gh pr` command."""
    toks = _argv(command, tool_name)
    if not toks or not _is_gh_pr(toks):
        return []
    msgs, reads_stdin = [], False
    for kind, value in _gh_body_flags(toks):
        if kind == "msg":
            msgs.append(Message(value, False, None, None))
        elif value in _STDIN_PATHS:
            reads_stdin = True
        else:
            found = _read_message_file(value)
            if found is not None:
                msgs.append(found)
    if reads_stdin and tool_name != "PowerShell":
        msgs += [Message(body, False, None, None)
                 for body in _stdin_heredoc_bodies(command, _reads_stdin_body)]
    return msgs


def _stdin_messages(command, toks, tool_name):
    """Messages a stdin-reading git command receives: a heredoc body, or a `< file` redirect."""
    msgs = []
    if tool_name != "PowerShell":
        msgs += [Message(body, False, None, None) for body in _stdin_heredoc_bodies(command)]
    for kind, value, index in _message_flags(toks):
        if kind != "file" or value not in _STDIN_PATHS:
            continue
        path = _redirected_stdin(toks, index)
        found = _read_message_file(path) if path else None
        if found is not None:
            msgs.append(found)
    return msgs


def _messages(command, tool_name="Bash"):
    """Inline commit/merge/tag messages in a git command, as (text, from_file) pairs: the values
    of -m/--message, the contents of the file named by -F/--file, and - when that file is the
    command's own stdin - the heredoc or redirected file feeding it. Empty unless the command is a
    git command.

    `from_file` travels with the text because it decides how a hit may be REPORTED. A -m value or
    a heredoc body is text the caller typed and already has; a -F file's content is not.

    `tool_name` picks the splitting language. It matters here because this function RESOLVES a
    token - it opens the `-F` path - so a separator eaten by the wrong splitter leaves a path that
    opens nothing and the guard approves a message it never read.
    """
    toks = _argv(command, tool_name)
    if not toks or "git" not in toks:
        return []
    msgs, reads_stdin = [], False
    for kind, value, _index in _message_flags(toks):
        if kind == "msg":
            msgs.append(Message(value, False, None, None))
        elif value in _STDIN_PATHS:
            reads_stdin = True
        else:
            found = _read_message_file(value)
            if found is not None:
                msgs.append(found)
    if reads_stdin:
        msgs += _stdin_messages(command, toks, tool_name)
    return msgs


# A write whose target is a message file: a `>`/`>>` redirect or a `tee` operand. Read on the
# command text (heredoc bodies stripped), because a split argv glues `>$M;` into one word.
_WRITE_TARGET = re.compile(r"""(?:(?<![<>&\d])>>?|\btee(?:\s+-a)?)\s*(["']?)([^\s;&|<>"']+)\1""")


def _message_file_values(toks):
    """Every -F/--file value of a git command and --body-file value of a gh pr command."""
    values = []
    if "git" in toks:
        values += [v for kind, v, _i in _message_flags(toks) if kind == "file"]
    values += [v for kind, v in _gh_body_flags(toks) if kind == "file"]
    return [v for v in values if v not in _STDIN_PATHS]


_PRINTERS = frozenset({"printf", "echo"})
_ESCAPES = {"\\n": "\n", "\\t": "\t"}


def _printed_text(segment, tool_name):
    """What a printf/echo statement prints, escapes decoded; None when it is not one of them."""
    try:
        toks = shell_text.split_for_tool(segment.strip(), tool_name)
    except ValueError:
        return None
    if not toks or shell_text.basename_for_tool(toks[0], tool_name) not in _PRINTERS:
        return None
    words = []
    for tok in toks[1:]:
        if re.match(r"\d*>|\|", tok):
            break                                  # the redirection and what follows it
        if tok.startswith("-") and not words:
            continue                               # printf --, echo -e / -n
        words.append(tok)
    text = " ".join(words)
    for escape, char in _ESCAPES.items():
        text = text.replace(escape, char)
    return text


def _heredoc_writes(command, value):
    """Bodies of the heredocs whose opener line writes `value` (`cat > $M <<'EOF'`)."""
    lines = command.split("\n")
    bodies = []
    for at, _opener, (start, end) in shell_text.iter_heredocs(command):
        line = _logical_line(lines, at)
        if any(match.group(2) == value for match in _WRITE_TARGET.finditer(line)):
            bodies.append("\n".join(lines[start:end]))
    return bodies


def _statement_writes(text, value, limit, tool_name):
    """(texts, unrecoverable) for the statements before `limit` whose redirect or tee writes `value`.

    A printf/echo writer's text is read off the command; a `| tee value` takes the printer before
    the pipe. Any other writer (cp, a script) cannot be read here, which is `unrecoverable`.
    """
    texts, unrecoverable, previous, prior = [], False, 0, None
    for at, segment in shell_text.iter_segments(text, tool_name):
        separator, previous = text[previous:at], at + len(segment)
        if at >= limit:
            break
        if re.search(r"(?<!<)<<(?!<)", segment):
            prior = segment
            continue                               # a heredoc writer: `_heredoc_writes` reads it
        if any(match.group(2) == value for match in _WRITE_TARGET.finditer(segment)):
            printed = _printed_text(segment, tool_name)
            if printed is None and separator.strip() == "|" and prior is not None:
                printed = _printed_text(prior, tool_name)
            if printed is None:
                unrecoverable = True
            else:
                texts.append(printed)
        prior = segment
    return texts, unrecoverable


# The programs that read a message file.
_MESSAGE_READERS = frozenset({"git", "gh"})

# Runners that start their command on ANOTHER machine or inside a container, mapped to the
# subcommand that does so (None: the runner itself does). A git behind one of these reads its -F
# path over there. This is deliberately the closed set of REMOTE runners and not an allow-list of
# local launchers: a local list can never be complete (flock, xargs, uv run, parallel ...), and
# every wrapper missing from it silently exempted a provably missing message file.
_REMOTE_RUNNERS = {
    "ssh": None, "lxc-attach": None, "nsenter": None, "chroot": None,
    "pct": frozenset({"exec", "enter"}), "docker": frozenset({"exec", "run"}),
    "podman": frozenset({"exec", "run"}), "kubectl": frozenset({"exec"}),
    "machinectl": frozenset({"shell", "run"}), "incus": frozenset({"exec"}),
    "lxc": frozenset({"exec"}),
}

# A Windows path this Python resolves the way the shell does: drive-qualified (`C:/x`, `C:\\x`).
_WINDOWS_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")


def provably_missing(value, windows=None):
    """True only when `value` is a message-file path this host can check and it does not exist.

    `windows` defaults to the running host. On Windows a drive-less root is not checkable: Git Bash
    maps `/tmp` and `/c/...` itself, while Python resolves `/tmp/msg.txt` as `C:\\tmp\\msg.txt`,
    so a naive exists() there judged every POSIX-style -F path missing and blocked the commit. Such
    a path degrades to unchecked rather than refused. A path with an expansion names nothing yet.
    """
    if windows is None:
        windows = os.name == "nt"
    if "$" in value:
        return False
    # posixpath, not os.path: from Python 3.13 os.path.isabs on Windows rejects a drive-less
    # root, so the POSIX arm asked of a Windows interpreter judged '/x' relative.
    checkable = _WINDOWS_DRIVE_PATH.match(value) if windows else posixpath.isabs(value)
    return bool(checkable) and not os.path.exists(value)


def _read_on_this_host(text, value, tool_name):
    """True when a statement in `text` runs git or gh HERE with `value` as its message file.

    `ssh host git commit -F /x` and `pct exec 100 -- git commit -F /x` carry the same flag, but a
    remote runner stands in front of the git, so the file is on the other machine and cannot be
    checked. Any other word in front of it (sudo, flock, xargs, uv run) runs the git here.
    """
    for _at, segment in shell_text.iter_segments(text, tool_name):
        try:
            toks = shell_text.split_for_tool(segment, tool_name)
        except ValueError:
            continue
        reader = _reader_index(toks, tool_name)
        if (reader is not None and value in _message_file_values(toks)
                and not _runs_remotely(toks[:reader], tool_name)):
            return True
    return False


def _reader_index(toks, tool_name):
    """Index of the first git or gh word in `toks`, else None."""
    for at, tok in enumerate(toks):
        if shell_text.basename_for_tool(tok, tool_name) in _MESSAGE_READERS:
            return at
    return None


def _runs_remotely(before, tool_name):
    """True when the words in front of the reader include a remote runner (with its subcommand)."""
    for at, tok in enumerate(before):
        runner = shell_text.basename_for_tool(tok, tool_name)
        if runner not in _REMOTE_RUNNERS:
            continue
        subcommands = _REMOTE_RUNNERS[runner]
        if subcommands is None or subcommands.intersection(before[at + 1:]):
            return True
    return False


def same_command_messages(command, tool_name="Bash"):
    """(messages, unread) for message files that do not exist yet when this guard runs.

    A file the SAME command writes before the commit (`printf ... > $M && git commit -F $M`) is
    created only after this PreToolUse guard has run, so opening it reads nothing - and an
    attribution trailer written that way went through (2026-10-29, a public repo). Its text is
    read off the command instead: a heredoc body, or what a printf/echo prints. A writer whose
    text cannot be read here (cp, a script), or a path that `provably_missing` says is absent, that
    a git or gh run on THIS host reads and that nothing in the command writes, lands in `unread`:
    the guard refuses rather than approve a message it never saw. A relative path that nothing
    writes is left to `_messages`, since the command may run the commit in another directory, and
    so is a path a remote git reads (`ssh host git commit -F /x`, `pct exec 100 -- git ...`): that
    file lives on the other machine, so its absence here proves nothing.
    """
    toks = _argv(command, tool_name)
    if not toks:
        return [], []
    text = shell_text.strip_heredoc_bodies(command)
    messages, unread = [], []
    for value in dict.fromkeys(_message_file_values(toks)):
        verb = re.search(r"(?:-F|--file|--body-file)(?:=|\s+)([\"']?)" + re.escape(value) + r"\1",
                         text)
        limit = verb.start() if verb else len(text)
        bodies = [] if tool_name == "PowerShell" else _heredoc_writes(command, value)
        texts, unrecoverable = _statement_writes(text, value, limit, tool_name)
        messages += [Message(t, False, None, None) for t in bodies + texts]
        written = bool(bodies or texts or unrecoverable)
        missing = provably_missing(value) and _read_on_this_host(text, value, tool_name)
        if unrecoverable or (missing and not written):
            unread.append(value)
    return messages, unread


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    tool_name = event.get("tool_name") or "Bash"
    written, unread = same_command_messages(command, tool_name)
    if unread:
        return shell_text.refuse(
            "The message file %s does not exist yet when this check runs, and this command "
            "creates it in a way the check cannot read (or nothing creates it). Its text cannot be "
            "checked for AI-writing tells or an AI attribution trailer, so it would be committed "
            "unread. Write the message file in its own earlier command (the Write tool, or a "
            "separate Bash call), then run the commit with -F naming it.\n" % ", ".join(unread)
        )
    messages = _messages(command, tool_name) + written
    if any(_ATTRIBUTION.search(msg.text) for msg in messages + _gh_bodies(command, tool_name)):
        # The line is not quoted back: a -F file's content is never echoed (see below), and the
        # caller knows which trailer or footer they added.
        return shell_text.refuse(
            "AI attribution line in the git message or PR body: a Co-Authored-By trailer naming "
            "Claude or Anthropic, or a 'Generated with Claude Code' footer. Remove it - commits "
            "and PRs carry human authorship only, whatever the session's attribution reminder "
            "says. (A Linux-kernel 'Assisted-by: Claude:<model>' trailer is allowed.)\n"
        )
    hits, mis_encoded = [], []
    for msg in messages:
        if msg.bad_byte is not None:
            mis_encoded.append(msg)
        # A -F file's lines are never quoted back: this hook runs BEFORE the call is approved, so
        # the path is still only a string the caller named, and exit 2 shows stderr to the model.
        hits += (tell_chars.find_tell_codepoints(msg.text) if msg.from_file
                 else tell_chars.find_tell_lines(msg.text))
    if not hits and not mis_encoded:
        return 0
    parts = [
        "%s is not valid UTF-8 (first bad byte at byte %d). git assumes UTF-8 for a commit "
        "message, so a tell saved in another encoding is invisible to this check - an em-dash "
        "from a Windows editor is byte 0x97. Re-save the file as UTF-8.\n"
        % (msg.path, msg.bad_byte)
        for msg in mis_encoded
    ]
    if hits:
        parts.append(
            "AI-writing tell(s) in the git message (em/en-dash, curly quote, ellipsis, NBSP, "
            "ZWSP, BOM, etc.). Rewrite with ASCII (use - , . : () ...) before committing:\n"
            + "\n".join(hits[:20]) + "\n"
        )
    return shell_text.refuse("".join(parts))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
