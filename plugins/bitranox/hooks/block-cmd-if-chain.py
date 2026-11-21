#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: a cmd.exe `if` followed by a `&` chain, sent over ssh.

In cmd.exe, `if <cond> a & b` parses as `if <cond> (a & b)`: every `&`, `&&` and `||` that follows
the condition on that line belongs to the `if`. A shell's `if` ends at `;` or a newline, so the
line reads like a sequence and is not one. The classic shape is the "clean, then recreate" one-liner
sent to a Windows host:

    ssh win "if exist tbx rmdir /s /q tbx & mkdir tbx && tar -xf src.tar -C tbx && pytest"

When `tbx` did not exist, NOTHING after the condition runs, and the call exits 0 with no output.
The next step (an scp into the missing directory) then fails with a message that reads like a path
or quoting problem. Hit three times before this guard existed.

The fix is one of: parenthesise the `if` so the chain is unconditional,
`(if exist X rmdir /s /q X) & mkdir X`; send each step as its own ssh call and read each exit
status; or ship a .cmd / .ps1 file and run it. When every step after the condition really is meant
to be conditional, the block form `if exist X ( a & b )` says so, and passes.

WHAT IS JUDGED
--------------
Only a local statement whose PROGRAM is `ssh` (found the way the shell finds it, past `timeout`,
`env`, `nice` and the other launchers `shell_text.statement_program` knows), or an unexpanded
`$VAR` that the same command assigned an `ssh ...` command line. Its options are skipped by ssh's
own grammar (the flags that take a value, attached or separate, and `--`), plus any `$K` word that
stands before the host (options kept in a variable), the next operand is the destination, and the
rest, joined with spaces as ssh joins them, is the remote command. The local shell's redirections
(`2>&1`, `&>log`) are dropped first: they never reach the remote side. A heredoc body is stdin, not
the remote command, and is not read, and a statement whose program is not ssh (`echo`, `grep`,
`git commit -m`) is not judged. So a doc, a test fixture or a commit message describing this
footgun is not refused.

When the remote command is `cmd /c "..."` (or `/k`, any spelling of the binary, with `/s /q /d`
style switches), the prefix and that one pair of quotes are removed and the inner line is judged,
as the inner cmd.exe parses it. An UNQUOTED `cmd /c if exist X a & b` is judged as it stands: the
outer cmd.exe splits it at the `&`, so `b` runs whatever the condition says. A remote
`powershell -Command "..."` passes for the same reason: its argument is quoted at cmd.exe's level.
A `&` right after `<` or `>` (`2>&1`) is a redirection, not a chain.

HOW A cmd.exe LINE IS TOLD FROM A POSIX ONE
-------------------------------------------
There is no way to ask which shell the remote host runs, so the rule keys on GRAMMAR that only
cmd.exe accepts, and prefers silence whenever the text could be POSIX:

- the `if` must stand at command position (line start, after `@`, `(`, `&`, `&&`, `||` or `|`)
  and be followed by a cmd.exe condition: `[/i] [not] exist|defined|errorlevel|cmdextversion X`,
  or `[/i] [not] A==B` / `A EQU B` (and NEQ, LSS, LEQ, GTR, GEQ). A POSIX `if` is followed by a
  command: `[`, `[[`, `test`, `!`, a program name - none of which is one of those words, and
  `if [ "$a" == "b" ]` puts the `==` inside a `[` test, which the operand rule never reaches;
- a comparison operand starting with `$`, `[` or `(` is POSIX or PowerShell, not cmd.exe;
- a line carrying a `then` or `fi` word after the `if` is a POSIX conditional: never judged.

Only then is the line walked the way cmd.exe walks it: `"` toggles quoting, `^` escapes the next
character, and `(`/`)` nest. The `if`'s body runs to the end of the line or to the `)` closing a
group opened before it. A `&`, `&&` or `||` at the `if`'s own depth inside that body is the finding.
A body that is itself a parenthesised block (`if exist X ( a & b )`) is deliberate and passes, and
so does anything after such a block: whether cmd.exe attaches a `& c` written after the closing
paren to the `if` was not verified, and an unverified claim is no reason to refuse.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the call and shows
stderr to the model; every other path, including any error, exits 0 so a broken guard never wedges
a turn.

Decisions:

- The rule is a BLOCK, not a nudge, and keys on the cmd.exe `if` grammar inside an ssh remote
  command, never on a bare "if exist" substring. Why: the failure is silent (exit 0, no output),
  so a warning beside a call that looks successful is read past; and the substring matches prose,
  fixtures and POSIX lines alike. Evidence: replayed with guard_replay.py over the transcript corpus
  on 2026-11-17 (5,960 transcripts, 222,918 distinct Bash calls; 8,458 of them carry `ssh`, 265
  carry `ssh` and a cmd.exe-looking `if`). `find_swallowing_if` fires on 24: 0.011% of all calls,
  0.28% of ssh calls. Every firing was read against its source command: 24 of 24 are the footgun,
  a cmd.exe `if` at command position in an ssh remote line with a `&`/`&&`/`||` after it at the
  same depth; 0 false positives. 8 of the 24 were followed in the same call by scp's
  `dest open ... No such file or directory` into the directory the swallowed `mkdir` never made;
  the memory fact's tbx/tar/pytest line and the bare-form probe that verified the parenthesised
  fix are among them. guard_replay's precision reads 0: nothing blocks a call whose damage is a
  silent exit 0, so precision was priced by reading each firing, not by a later gate. The first
  draft fired 12 times with 2 false positives, both fixed and pinned: a LOCAL `2>&1 | tail` read
  as a remote chain (`test_a_local_redirection_after_the_remote_command_is_not_a_chain`), and an
  unquoted `cmd /c if ... & mkdir` the outer cmd.exe splits
  (`test_an_unquoted_cmd_slash_c_belongs_to_the_outer_cmd`). It also missed 14: options in a
  `$K` variable read as the host (`test_ssh_options_held_in_a_variable_do_not_hide_the_remote_if`)
  and ssh called as `$SSH` (`test_ssh_called_through_a_variable_holding_it_is_judged`). Of the 241
  ssh calls carrying a cmd.exe-looking `if` that do not fire, every one with a `&` or `||` after
  the `if` was read: a parenthesised `if`, a block form, the `&&` sitting after the closing quote
  (local), prose or test fixtures, or an `if` with nothing after it. Pinned by
  `test_replay_decision_is_recorded` and the per-shape tests in `test_block_cmd_if_chain.py`.
  Reopen if a replay shows a refusal of a line whose chain was meant to be conditional often
  enough that the block-form advice is routed around, or a remote cmd.exe spelling the rule misses.
- Rejected: firing on any `if` followed later by `&` in an ssh argument. A POSIX `if ...; then
  ...; fi && next` has the same characters and is correct; the `then`/`fi` and operand rules exist
  to keep it silent (`test_posix_if_over_ssh_passes`).
- Rejected: treating a `&` written after an `if`'s parenthesised block as part of the `if`. Not
  verified on a Windows host, and the brief for this guard named the block form as deliberate.
  Pinned by `test_block_form_passes`.
"""

import json
import re
import sys

from hook_event import parse_pre_tool_use
import shell_text
from shell_text import (
    drop_redirections,
    iter_segments,
    mask_data_regions,
    split_for_tool,
    statement_program,
    strip_heredoc_bodies,
)

# ssh(1) options that take a value: `-p 22` or `-p22`. Every other single-letter flag stands alone
# and may be bundled (`-tt`, `-4C`). Taken from the OpenSSH manual's synopsis.
_SSH_VALUE_FLAGS = frozenset("BbcDEeFIiJLlmOoPpQRSWw")

# A word that is nothing but a parameter expansion: `$K`, `${K}`, `${O[@]}`.
_UNEXPANDED = re.compile(r"\$(?:\{[^}]*\}|[A-Za-z_][A-Za-z0-9_]*)")

_CMD_PREFIX = re.compile(
    r"^\s*@?\s*(?:\S*[\\/])?cmd(?:\.exe)?\s+(?:/[a-z](?::\S*)?\s+)*?/[ck]\s+(?:/[a-z]\s+)*",
    re.IGNORECASE,
)

# A cmd.exe operand: a double-quoted string or a run of non-blank characters.
_OPERAND = r'(?:"[^"\n]*"|[^\s"]+)'
_COMPARE_OP = r"(?:==|\s(?:equ|neq|lss|leq|gtr|geq)\s)"
_CONDITION = re.compile(
    r"if\s+(?:/i\s+)?(?:not\s+)?(?:"
    r"(?:exist|defined)\s+" + _OPERAND + r"|"
    r"(?:errorlevel|cmdextversion)\s+\d+|"
    r"(?P<lhs>" + r'"[^"\n]*"|[^\s"=]+' + r")\s*" + _COMPARE_OP + r"\s*" + _OPERAND +
    r")(?=\s|$)",
    re.IGNORECASE,
)
_POSIX_KEYWORD = re.compile(r"(?<![\w-])(?:then|fi)(?![\w-])")
_POSIX_OPERAND_START = ("$", "[", "(")


def _ssh_remote_command(tokens):
    """The remote command an ssh argv runs, joined as ssh joins it, or None when it has none."""
    idx, end = 1, len(tokens)
    while idx < end:
        word = tokens[idx]
        if word == "--":
            idx += 1
            break
        if not word.startswith("-") or word == "-":
            break
        idx += 1
        for pos, flag in enumerate(word[1:], start=1):
            if flag in _SSH_VALUE_FLAGS:
                if pos == len(word) - 1:
                    idx += 1                       # the value is the next word
                break                              # an attached value ends the bundle
    # Options kept in a variable (`K="-i key -o BatchMode=yes"; ssh $K host '...'`) arrive here as
    # one unexpanded `$K` word, which the shell later splits into options. Read as the destination,
    # it made the real host the first word of the remote command and hid every `if` behind it: most
    # of the misses in the replay had this shape. A variable word followed by another single word
    # and then more is options; one followed directly by a spaced string (`ssh $H 'cmd'`) is the host.
    while (idx + 2 < end and _UNEXPANDED.fullmatch(tokens[idx])
           and not any(c.isspace() for c in tokens[idx + 1])):
        idx += 1
    if idx >= end:
        return None
    rest = tokens[idx + 1:]                        # tokens[idx] is the destination
    return " ".join(rest) if rest else None


def _variable_ssh_remote(tokens, text):
    """The remote command of `$SSH "..."`, where SSH was assigned an ssh command line in `text`.

    `SSH="ssh -i key admin@win"; $SSH "if exist X ... & ..."` hides the program behind a
    variable, and two of the replay's real misses had that shape. Whether the variable also holds
    the host is unknowable, so the remote command is taken from the first word that contains
    whitespace - a quoted command string - which a host or an option never is.
    """
    if not tokens:
        return None
    match = _UNEXPANDED.fullmatch(tokens[0])
    if not match:
        return None
    name = tokens[0].strip("${}")
    if not re.search(r"(?<![\w])" + re.escape(name) + r"=[\"']?(?:timeout\s+\S+\s+)?ssh\s", text):
        return None
    for at in range(1, len(tokens)):
        if any(c.isspace() for c in tokens[at]):
            return " ".join(tokens[at:])
    return None


def _unwrap_cmd(remote):
    """`remote` without a leading `cmd /c` and its one pair of outer quotes, when it has both."""
    match = _CMD_PREFIX.match(remote)
    if not match:
        return remote
    inner = remote[match.end():].strip()
    if len(inner) >= 2 and inner.startswith('"') and inner.endswith('"'):
        return inner[1:-1]
    # Unquoted, the line is the OUTER cmd.exe's: `cmd /c if exist X a & b` is `cmd /c if exist X a`
    # and then `b`, so the `&` ends the inner command and nothing is swallowed. Judge it as it stands.
    return remote


class _Line:
    """One cmd.exe line, walked the way cmd.exe walks it: quotes, `^` escapes, paren depth."""

    def __init__(self, text):
        self.text = text
        self.depth = []                            # depth at each index, outside quotes
        self.live = []                             # True where the char is unquoted and unescaped
        self._walk()

    def _walk(self):
        depth, quoted, escaped = 0, False, False
        for char in self.text:
            live = not quoted and not escaped
            if escaped:
                escaped = False
            elif char == '"':
                quoted = not quoted
            elif not quoted and char == "^":
                escaped = True
            elif live and char == ")":
                depth -= 1
            self.depth.append(depth)
            self.live.append(live)
            if live and char == "(":
                depth += 1

    def command_positions(self):
        """Indices where a command may start: the line start and after a live operator or paren."""
        yield 0
        for at, char in enumerate(self.text):
            if self.live[at] and char in "(&|":
                yield at + 1

    def chain_after(self, start, depth):
        """Index of the first live `&`/`||` at `depth` from `start` until the body ends, else -1."""
        text = self.text
        for at in range(start, len(text)):
            if not self.live[at]:
                continue
            if self.depth[at] < depth:
                return -1                          # a `)` closed the group the `if` stood in
            if self.depth[at] != depth:
                continue
            if text[at] == "&" and at and text[at - 1] in "<>":
                continue                           # `2>&1`, `>&2`: a redirection, not a chain
            if text[at] == "&" or text.startswith("||", at):
                return at
        return -1


def _swallowing_if_in_line(line):
    """Whether this cmd.exe line has an unparenthesised `if` followed by a `&` chain."""
    walk = _Line(line)
    for pos in walk.command_positions():
        head = line[pos:]
        stripped = head.lstrip(" \t@")
        at = pos + len(head) - len(stripped)
        if at >= len(line) or not walk.live[at]:
            continue
        match = _CONDITION.match(line, at)
        if not match:
            continue
        lhs = match.group("lhs")
        if lhs and lhs.startswith(_POSIX_OPERAND_START):
            continue
        if _POSIX_KEYWORD.search(line, match.end()):
            return False                           # `if ...; then ... fi`: a POSIX conditional
        body = match.end()
        while body < len(line) and line[body] in " \t":
            body += 1
        if body < len(line) and line[body] == "(":
            continue                               # block form: deliberate
        if walk.chain_after(body, walk.depth[at]) != -1:
            return True
    return False


def _remote_lines(remote):
    """The lines of a remote cmd.exe command string."""
    inner = _unwrap_cmd(remote)
    return [line for line in re.split(r"\r\n|\r|\n", inner) if line.strip()]


def find_swallowing_if(command, tool_name="Bash"):
    """The first remote cmd.exe line whose `if` swallows a `&` chain, or None. PURE.

    Args:
        command: the Bash (or PowerShell) tool's command string.
        tool_name: picks the argv split, POSIX for Bash and Windows rules for PowerShell.

    Returns:
        The offending remote line, for the refusal to quote (the caller typed it inline), or None.

    Examples:
        >>> find_swallowing_if('ssh win "if exist t rmdir /s /q t & mkdir t"')
        'if exist t rmdir /s /q t & mkdir t'
        >>> find_swallowing_if('ssh win "(if exist t rmdir /s /q t) & mkdir t"') is None
        True
    """
    text = strip_heredoc_bodies(command or "")
    if "ssh" not in text.lower():
        return None
    masked = mask_data_regions(text, tool_name=tool_name)
    for at, segment in iter_segments(masked, tool_name):
        raw = text[at:at + len(segment)]
        try:
            tokens = split_for_tool(raw, tool_name)
        except ValueError:
            continue
        # The local shell consumes `2>&1 | tail` before ssh runs, so its redirections are not part
        # of the remote command; left in, `2>&1` read as a chain after the remote `if`.
        idx = statement_program(tokens, ("ssh",), tool_name)
        if idx is not None:
            remote = _ssh_remote_command(drop_redirections(tokens[idx:]))
        else:
            remote = _variable_ssh_remote(drop_redirections(tokens), text)
        if not remote:
            continue
        for line in _remote_lines(remote):
            if _swallowing_if_in_line(line):
                return line
    return None


_SHOWN = 240


def refusal(line):
    """The refusal text for an offending remote `line`."""
    shown = line if len(line) <= _SHOWN else line[:_SHOWN] + " ..."
    return (
        "A cmd.exe `if` swallows every command after it on the line, so this chain runs only when\n"
        "the condition holds. cmd.exe parses `if <cond> a & b` as `if <cond> (a & b)`: the `&`,\n"
        "`&&` and `||` after the condition belong to the `if`. Sent to a Windows host, `if exist X\n"
        "rmdir /s /q X & mkdir X` creates nothing when X did not exist, and the call exits 0 with\n"
        "no output - every later step silently skipped.\n"
        "Remote line: " + shown + "\n"
        "Fix, one of:\n"
        '  ssh <host> "(if exist X rmdir /s /q X) & mkdir X"   parenthesise the if; the rest runs\n'
        '  ssh <host> "if exist X rmdir /s /q X"  then  ssh <host> "mkdir X"   one call per step,\n'
        "      reading each exit status\n"
        "  ship a .cmd or .ps1 file, copy it over, and run that\n"
        "If every step after the condition is MEANT to be conditional, say so with the block form:\n"
        '  ssh <host> "if exist X ( rmdir /s /q X & mkdir X )"\n'
    )


def main() -> int:
    """Block an ssh call whose remote cmd.exe line chains after an unparenthesised `if`."""
    try:
        event = parse_pre_tool_use(json.load(sys.stdin))
    except (json.JSONDecodeError, ValueError):
        return 0
    if event is None:
        return 0
    command = str((event.get("tool_input") or {}).get("command") or "")
    tool_name = event.get("tool_name") or "Bash"
    line = find_swallowing_if(command, tool_name)
    if line is None:
        return 0
    return shell_text.refuse(refusal(line))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a guard must never wedge a turn
        sys.exit(0)
