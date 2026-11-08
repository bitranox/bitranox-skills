#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit) guard: a doc's bash block must not lose a gate's status.

A `SKILL.md` or `CLAUDE.md` code block is a command a reader pastes into ONE Bash call. When a
gate line (`cargo clippy`, `make test`, `pytest`, any `shell_text.GATE_RE` program) is followed
by another command with nothing consuming the gate's status, the call's exit code is the LAST
command's: a red gate reads green. Measured 2026-11-05: a `Cargo.lock` check appended on the line
after `cargo clippy ... -D warnings` in a skill made a failing clippy exit 0, and only an
independent review probe noticed. The same shape (a newline or `;` severing a gate from what
follows) was by then recorded eight times in the memory store, so prose had stopped working.

What counts as a finding, per fenced block whose info string is bash, sh, shell or zsh:

* a statement whose PROGRAM is a gate (`shell_text.gate_program_in`, the reading
  block-masked-gate-exit already uses, so `grep pytest x` or a heredoc body is no gate);
* not a condition (`if`, `elif`, `while`, `until`, `!`), not backgrounded (`&`);
* no `||` anywhere later in its and-or list (`gate || { echo REFUSE; exit 1; }`, or
  `gate && ok || fail`): an `&&`-only tail still ends the list with the gate's failure;
* followed, after the list ends, by another executable statement that does not read the status
  (`echo $?`, `rc=$?`, `${PIPESTATUS[0]}` consume it deliberately and are left alone);
* no `set -e` / `set -o errexit` earlier in the block, and no `unchained-ok` marker on the gate's
  line or the line above it (the opt-out for a deliberate case: `# unchained-ok: <reason>`).

A statement after a compound's end (`fi`, `done`, `esac`, `}`, `)`) is not judged: the status
there is the compound's, and guessing it costs precision for a rare shape.

Only findings the EDIT ADDS are refused. The resulting file and the file before the edit are both
scanned and the difference taken as a multiset, keyed by the gate and follow-up statements'
text. A legacy block is therefore never a reason to refuse an unrelated edit. When the file cannot
be read or an `old_string` is not in it, the edit's own old and new strings stand in for the two
versions.

It shares the edit-guard matcher group, so NotebookEdit reaches it too and is let through: a
notebook is never a SKILL.md or CLAUDE.md.

Priced before shipping as a BLOCK (2026-11-05), by replaying every Edit, MultiEdit and Write of a
SKILL.md or CLAUDE.md recorded under ~/.claude/projects (tool_use ids deduplicated): 2337 edits
and 17 writes. It refused 2 edits, both the motivating defect above, and no write. The replay
compares each edit's old_string with its new_string (the file as it stood is not recorded), so a
gate OUTSIDE the edited span whose new follow-up line was inserted after it is not counted; the
live hook reads the file and catches that too. Over the 726 SKILL.md and CLAUDE.md files on the
measuring machine, 62 existing blocks already carry the shape (lists of gates pasted as one
block, a release build followed by `strip`, `make test` followed by `make push`); this guard
leaves them alone until an edit adds a new one.

Exit 2 blocks the edit and tells the model which line and what to change; the text echoed back is
text the model itself is writing in this call. Unparseable stdin and any unexpected error exit 0:
a broken guard must never wedge a turn. Pure standard library plus shell_text; launched through
run-python.sh.
"""

import json
import os
import posixpath
import re
import sys
from collections import Counter

from shell_text import LIST_SEP, blank_heredoc_bodies, gate_program_in, mask_data_regions

_TOOLS = {"Edit", "Write", "MultiEdit"}
_DOC_NAMES = {"skill.md", "claude.md"}
_SHELLS = {"bash", "sh", "shell", "zsh"}
_MARKER = "unchained-ok"
_MAX_BYTES = 2_000_000

_FENCE_OPEN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})[ \t]*([^\s`]*)")
_SPLIT = re.compile(r"\s*(?:" + LIST_SEP.pattern + r")\s*")
_CONDITION_WORDS = {"if", "elif", "while", "until", "!"}
_BODY_WORDS = {"then", "do", "else", "{", "(", "time"}
_COMPOUND_ENDS = {"fi", "done", "esac", "}", ")"}
# Reading the status on the next statement consumes it deliberately: `echo $?`, `rc=$?`, and
# `${PIPESTATUS[0]}` after a `gate | tee log`, the one way to keep a gate's status past a pipe.
_STATUS_READ = re.compile(r"\$\?|\$\{?PIPESTATUS\b")
_ERREXIT = re.compile(r"^set\s+(?:-[a-zA-Z]*e[a-zA-Z]*\b|-o\s+errexit\b)")


def _bash_blocks(text):
    """(first body line number, body) for every fenced bash/sh/shell/zsh block in `text`."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        opener = _FENCE_OPEN.match(lines[i])
        if not opener:
            i += 1
            continue
        fence, info = opener.group(1), opener.group(2).lower()
        close = re.compile(r"^[ \t]{0,3}" + re.escape(fence[0]) + "{%d,}[ \t]*$" % len(fence))
        end = i + 1
        while end < len(lines) and not close.match(lines[end]):
            end += 1
        if info in _SHELLS:
            out.append((i + 2, "\n".join(lines[i + 1:end])))
        i = end + 1
    return out


def _statements(block):
    """[(raw, masked, separator_after, start_offset)] for one block, continuations joined.

    Cut on the masked text, so a separator inside quotes, a substitution, a comment or a heredoc
    body is none; a newline reads as an unconditional separator, which is the whole point here.
    """
    joined = re.sub(r"\\\n", "  ", block)              # same length: offsets still map to lines
    raw = blank_heredoc_bodies(joined)
    masked = mask_data_regions(raw)
    out, start = [], 0
    for sep in _SPLIT.finditer(masked):
        out.append((raw[start:sep.start()], masked[start:sep.start()], sep.group(0).strip(), start))
        start = sep.end()
    out.append((raw[start:], masked[start:], "", start))
    return out


def _first_word(masked):
    words = masked.split()
    return words[0] if words else ""


def _gate_in(masked):
    """The gate statement's program text when `masked` runs a gate as a body command, else None."""
    words = masked.split()
    while words and words[0] in _BODY_WORDS:
        words = words[1:]
    if not words or words[0] in _CONDITION_WORDS:
        return None
    rest = " ".join(words)
    return rest if gate_program_in(rest) else None


def _marked(block, offset):
    line_start = block.rfind("\n", 0, offset) + 1
    prev_start = block.rfind("\n", 0, max(line_start - 1, 0)) + 1 if line_start else line_start
    line_end = block.find("\n", offset)
    line_end = len(block) if line_end < 0 else line_end
    return _MARKER in block[prev_start:line_end]


def _list_end(stmts, at):
    """Index of the last statement in the and-or list that `stmts[at]` belongs to."""
    while at < len(stmts) - 1 and stmts[at][2] in ("&&", "||"):
        at += 1
    return at


def block_findings(block):
    """[(gate_offset, gate_text, next_offset, next_text)] for unconsumed gate statuses in one block."""
    stmts = _statements(block)
    found, errexit, i = [], False, 0
    while i < len(stmts):
        raw, masked, _sep, offset = stmts[i]
        if _ERREXIT.match(masked.strip()):
            errexit = True
        gate = None if errexit else _gate_in(masked)
        if gate is None:
            i += 1
            continue
        end = _list_end(stmts, i)
        refused = any(stmts[k][2] == "||" for k in range(i, end))
        if refused or stmts[end][2] == "&" or _marked(block, offset):
            i = end + 1
            continue
        follow = next((s for s in stmts[end + 1:] if s[1].strip()), None)
        if (follow is not None and _first_word(follow[1]) not in _COMPOUND_ENDS
                and not _STATUS_READ.search(follow[0])):
            found.append((offset, " ".join(raw.split()), follow[3], " ".join(follow[0].split())))
        i = end + 1
    return found


def findings(text):
    """[(line, gate_text, next_line, next_text)] for every bash block in a whole document."""
    out = []
    for first_line, block in _bash_blocks(text):
        for gate_at, gate, next_at, nxt in block_findings(block):
            out.append((first_line + block.count("\n", 0, gate_at), gate,
                        first_line + block.count("\n", 0, next_at), nxt))
    return out


def _versions(tool, tool_input, current):
    """(before, after) document text for the edit, or the edit's own strings when it cannot apply."""
    if tool == "Write":
        return current or "", tool_input.get("content") or ""
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    edits = [e for e in edits or [] if isinstance(e, dict)]
    after = current
    for edit in edits:
        old, new = edit.get("old_string") or "", edit.get("new_string") or ""
        if after is None or not old or old not in after:
            after = None
            break
        after = after.replace(old, new) if edit.get("replace_all") else after.replace(old, new, 1)
    if after is not None:
        return current, after
    return ("\n".join(e.get("old_string") or "" for e in edits),
            "\n".join(e.get("new_string") or "" for e in edits))


def _read(path):
    try:
        if os.path.getsize(path) > _MAX_BYTES:
            return None
        with open(path, encoding="utf-8", errors="replace", newline="") as fh:
            return fh.read()
    except OSError:
        return None


def added_findings(before, after):
    """Findings in `after` that `before` does not already hold, compared as a multiset."""
    old = Counter((g, n) for _l, g, _m, n in findings(before))
    new = []
    for line, gate, next_line, nxt in findings(after):
        if old[(gate, nxt)]:
            old[(gate, nxt)] -= 1
        else:
            new.append((line, gate, next_line, nxt))
    return new


def decide(event):
    """Pure-ish (reads the target file): a block reason, or None to allow."""
    tool = event.get("tool_name") or ""
    if tool not in _TOOLS:
        return None
    tool_input = event.get("tool_input") or {}
    raw_path = (tool_input.get("file_path") or "").replace("\\", "/")
    if posixpath.basename(raw_path).lower() not in _DOC_NAMES:
        return None
    before, after = _versions(tool, tool_input, _read(raw_path))
    new = added_findings(before, after)
    if not new:
        return None
    rows = "\n".join("  line %d: `%s`\n    then line %d runs `%s`, and the call's exit code is that one's"
                     % (line, gate[:160], next_line, nxt[:160]) for line, gate, next_line, nxt in new)
    return (
        "This edit adds a bash block where a gate's exit status is lost: a reader pasting the "
        "block gets the LAST command's exit code, so a red gate reads green.\n%s\n"
        "Fix one of these ways: give the gate its own refusal on its line "
        "(`<gate> || { echo \"REFUSE: <gate> failed\"; exit 1; }`, a `\\` continuation is fine), "
        "chain the follow-up with `&&`, or read the status explicitly on the next line "
        "(`echo \"rc=$?\"`). If losing it is deliberate, put `# %s: <reason>` on the gate's line "
        "or the line above.\nFile: %s" % (rows, _MARKER, raw_path))


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    reason = decide(event)
    if reason is not None:
        sys.stderr.write("UNCHAINED GATE: " + reason + "\n")
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
