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

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the call and
shows stderr to the model; every other path (including any error) exits 0, so a broken guard
never wedges a turn.
"""
import collections
import json
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
    return " ".join(line[:-1] if line.endswith("\\") else line for line in lines[first:at + 1])


def _stdin_heredoc_bodies(command):
    """The bodies of the heredocs that feed a stdin-reading git command.

    A heredoc is the message when its opener sits on the same (logical) line as that git command:
    `git commit -F - <<'EOF'` and `cat <<'EOF' | git commit -F -` both qualify. A heredoc on any
    other line feeds some other program - a script, a notes file - and is not the message.
    """
    lines = command.split("\n")
    bodies = []
    for at, _opener, (start, end) in shell_text.iter_heredocs(command):
        line = _logical_line(lines, at)
        try:
            toks = shell_text.split_for_tool(line, "Bash")
        except ValueError:
            continue
        if _reads_stdin_message(toks):
            bodies.append("\n".join(lines[start:end]))
    return bodies


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


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    hits, mis_encoded = [], []
    for msg in _messages(command, event.get("tool_name") or "Bash"):
        if msg.bad_byte is not None:
            mis_encoded.append(msg)
        # A -F file's lines are never quoted back: this hook runs BEFORE the call is approved, so
        # the path is still only a string the caller named, and exit 2 shows stderr to the model.
        hits += (tell_chars.find_tell_codepoints(msg.text) if msg.from_file
                 else tell_chars.find_tell_lines(msg.text))
    if not hits and not mis_encoded:
        return 0
    for msg in mis_encoded:
        sys.stderr.write(
            "%s is not valid UTF-8 (first bad byte at byte %d). git assumes UTF-8 for a commit "
            "message, so a tell saved in another encoding is invisible to this check - an em-dash "
            "from a Windows editor is byte 0x97. Re-save the file as UTF-8.\n"
            % (msg.path, msg.bad_byte)
        )
    if not hits:
        return 2
    sys.stderr.write(
        "AI-writing tell(s) in the git message (em/en-dash, curly quote, ellipsis, NBSP, "
        "ZWSP, BOM, etc.). Rewrite with ASCII (use - , . : () ...) before committing:\n"
    )
    sys.stderr.write("\n".join(hits[:20]) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
