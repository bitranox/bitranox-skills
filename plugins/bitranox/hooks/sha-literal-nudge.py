#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a full git sha typed as a literal may have been invented.

An abbreviated sha is how one is DISPLAYED, so the 40-character form feels like something to
complete rather than something to look up - and a completion is plausible by construction, since
only the prefix is ever checked by eye. Measured five times: `fb3330b` printed, then
`fb3330b1d7b7...` typed into `ci_wait --sha`, where the real sha was `fb3330bd1ad7...`. Every
guard downstream checks SHAPE, not existence: `ci_wait`'s full-sha regex, a `headSha ==` filter
and `gh run list --commit` (which answers `[]` with exit 0) all pass a fabricated sha, so a wait
armed on one polls to its deadline. The prose rule was retrieved, restated and violated inside a
single session, which is why this is a hook.

What fires: a bare lowercase 40-hex literal, outside data regions (heredoc bodies, commit messages,
`echo`/`printf` operands, message-flag values, comments), in a command that neither DERIVES a sha
(`$(...)`, backticks) nor ASSERTS one (`rev-parse`, `cat-file`, `merge-base`), and that the
session transcript never SHOWED - no tool result, user message or attachment carried that exact
40-character string. The transcript test is what separates a pasted or printed sha, which is the
normal case, from a padded or invented one: the padding case always shows the short prefix and
never the full form.

What does NOT fire, deliberately: a literal whose only consumer is a local git command that
resolves it (`git show`, `git log`, `git update-ref` ...). Git refuses a nonexistent object LOUDLY
there, so the invented sha costs one round trip and cannot become a silent wait. The consumers
that fail silently - `gh`, `ci_wait`, `grep`, a `test` comparison, a poll loop - are the ones this
exists for.

NON-BLOCKING: emits additionalContext and exits 0, because a sha legitimately arriving from outside
(a CI URL, a pasted commit) must stay usable. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from shell_text import (
    argv_for_match,
    git_verb_operands,
    is_shell_tool,
    iter_segments,
    mask_data_regions,
    strip_data_sink_statements,
    strip_heredoc_bodies,
)

__all__ = ["main", "notice", "shas_in", "shown_shas"]

# A full sha as git prints it: exactly 40 LOWERCASE hex characters, not part of a longer word. An
# uppercase run is a GPG fingerprint, a longer one a sha256 or a hash inside an identifier.
_SHA = re.compile(r"(?<![0-9A-Za-z_])[0-9a-f]{40}(?![0-9A-Za-z_])")

# The same shape in RAW transcript text, where a JSON escape can sit right before it (`\n<sha>`
# reads as `n<sha>`), so only an adjacent hex character disqualifies a hit there.
_SHA_IN_TEXT = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{40}(?![0-9a-fA-F])")

# The command derives a sha itself, or asserts the literal resolves - the two forms the rule asks
# for. `merge-base --is-ancestor` refuses a nonexistent object too, so it is an assertion as well.
_DERIVES_OR_ASSERTS = re.compile(r"\$\(|`|\brev-parse\b|\bcat-file\b|\bmerge-base\b")

# Flags whose VALUE is prose for a human, whatever program takes them.
_MESSAGE_FLAG = re.compile(
    r"(?:(?<=\s)|^)(?:-m|--message|--body|--title|--notes|--subject|--description)(?:=|\s+)")

# Local git verbs that RESOLVE their revision operands and fail loudly on a nonexistent object. A
# literal consumed only by one of these cannot turn into a silent wait.
LOUD_GIT_VERBS = frozenset({
    "show", "log", "diff", "checkout", "switch", "restore", "reset", "revert", "cherry-pick",
    "merge", "rebase", "update-ref", "branch", "tag", "push", "fetch", "rev-list", "describe",
    "name-rev", "format-patch", "worktree", "blame", "ls-tree", "diff-tree", "shortlog", "notes",
    "bisect", "range-diff", "archive", "grep",
})

_FILL = "\x00"

_NOTICE = (
    "FULL SHA TYPED AS A LITERAL: {shas} {where}, and this command neither derives it nor checks "
    "it exists. A 40-character sha completed from a short one (or recalled) is invented: it "
    "passes every shape check, `gh run list --commit` answers [] with exit 0, and a wait armed on "
    "it polls to its deadline. Derive it in the same command (`--sha $(git rev-parse --verify -q "
    "HEAD)`), or prove it resolves first (`git cat-file -e <sha>^{{commit}}`). If you copied it "
    "from output you actually saw, ignore this."
)
_NOT_SHOWN = "does not appear in anything this session was shown (only a prefix, at most)"
_UNKNOWN = "could not be checked against the session transcript"


def _executed_text(command, tool_name):
    """The command with every data region blanked, length preserved."""
    text = strip_data_sink_statements(strip_heredoc_bodies(command), tool_name)
    masked = mask_data_regions(text, _FILL, tool_name or "Bash")
    out = list(text)
    for index, char in enumerate(masked):
        # mask_data_regions turns a comment into spaces and a quoted region into the fill: a
        # non-space character that became a space was inside a comment.
        if char == " " and not text[index].isspace():
            out[index] = " "
    for flag in _MESSAGE_FLAG.finditer(masked):
        cursor = flag.end()
        while cursor < len(masked) and masked[cursor] == _FILL:
            out[cursor] = " "
            cursor += 1
    return "".join(out)


def _consumed_only_by_loud_git(executed, sha, tool_name):
    """True when every statement using `sha` is a local git verb that resolves it loudly."""
    uses = [segment for _at, segment in iter_segments(executed, tool_name) if sha in segment]
    if not uses:
        return False
    return all(
        git_verb_operands(argv_for_match(segment, tool_name), LOUD_GIT_VERBS, tool_name) is not None
        for segment in uses
    )


def shas_in(command, tool_name=None):
    """The bare full-sha literals this command uses without deriving or asserting them, in order."""
    if not command or not isinstance(command, str):
        return []
    executed = _executed_text(command, tool_name)
    if _DERIVES_OR_ASSERTS.search(executed):
        return []
    found = []
    for match in _SHA.finditer(executed):
        sha = match.group(0)
        if sha.isdigit() or sha in found:
            continue
        if _consumed_only_by_loud_git(executed, sha, tool_name):
            continue
        found.append(sha)
    return found


def _is_assistant_line(line):
    try:
        record = json.loads(line)
    except ValueError:
        return False
    return isinstance(record, dict) and record.get("type") == "assistant"


def shown_shas(paths, shas):
    """The subset of `shas` that some NON-assistant transcript record carried verbatim.

    None when no transcript could be read: "not shown" is a claim about a transcript that was
    read, so an unreadable one leaves the question open rather than answering it.

    Only lines holding a candidate are parsed, so a large transcript costs one substring scan. The
    assistant's own records do not count: its earlier tool call carrying the sha is the invention,
    not evidence against it.
    """
    wanted = set(shas)
    seen = set()
    readable = False
    for path in paths:
        if not wanted - seen:
            break
        try:
            handle = open(path, encoding="utf-8", errors="ignore")
        except OSError:
            continue
        readable = True
        with handle:
            for line in handle:
                hits = {sha for sha in wanted - seen if sha in line}
                if not hits or _is_assistant_line(line):
                    continue
                seen |= {m.group(0) for m in _SHA_IN_TEXT.finditer(line)} & hits
    return seen if readable else None


def notice(command, tool_name=None, shown=None):
    """The nudge text for unverified full-sha literals, else None.

    `shown` is the set of shas the transcript carried, or None when it could not be read; a sha in
    it was copied from real output and is left alone.
    """
    shas = shas_in(command, tool_name)
    if shown is not None:
        shas = [sha for sha in shas if sha not in shown]
    if not shas:
        return None
    listed = ", ".join(sha[:12] + "..." for sha in shas)
    return _NOTICE.format(shas=listed, where=_UNKNOWN if shown is None else _NOT_SHOWN)


def _transcripts(event):
    """The main transcript plus, inside a subagent, the subagent's own (which holds its brief)."""
    main_path = event.get("transcript_path")
    if not main_path:
        return []
    paths = [Path(main_path)]
    agent = event.get("agent_id")
    if agent:
        paths.append(Path(main_path).with_suffix("") / "subagents" / ("agent-%s.jsonl" % agent))
    return paths


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    command = (event.get("tool_input") or {}).get("command")
    tool_name = event.get("tool_name")
    candidates = shas_in(command, tool_name)
    if not candidates:
        return 0
    paths = _transcripts(event)
    shown = shown_shas(paths, candidates)
    message = notice(command, tool_name, shown)
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
