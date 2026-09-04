#!/usr/bin/env python3
"""PreToolUse nudge: a work session is about to fix the plugin source in place. Queue it instead.

The shape it catches: a session whose cwd is some project's work (not a plugin marketplace repo,
not the memory store) writes into a marketplace repo - an Edit or Write whose path is inside one,
or a Bash write verb naming a path inside one (`sed -i`, a redirect, `tee`, `cp`/`mv`, a Python
heredoc calling `write_text`, or a `git commit`/`push`/`add` run there). Measured over 21 days of
transcripts (2026-09-04): 93 such episodes of three or more edit, commit or test calls into the
marketplace from work projects, and the tool fixed in place was then gated, bumped, pushed and
CI-watched from a project that had nothing to do with it - 2,096 minutes of skills-repo detours,
a third of all instrumentation time in work sessions, and the share grew week on week.

What it asks for is the other route: `contrib_queue.py add` with the symptom, then back to the
work; the dream drains the queue. It is a NUDGE, because the user may well have asked for the fix
- non-blocking additionalContext, once per session, and silent in a session that invoked a
`meta-dream-*` skill, whose job the maintenance IS.

The room test is structural, never a directory name. The plugin's SOURCE is the marketplace repo
whose `.claude-plugin/marketplace.json` carries the name of the marketplace this plugin runs from
(CLAUDE_PLUGIN_ROOT is `<cache>/<marketplace>/<plugin>/<version>`, so the name is two levels up);
a linked worktree of it carries its own marketplace.json and is the same room. A repo that merely
ships its own usage skill is a marketplace too, and is NOT the plugin's source - measured on the
corpus, treating every marketplace.json as the source made ordinary work in those tool repos read
as a detour. The store is the directory named MEMORY_DIRNAME. With no plugin root to name the
source, the hook is silent rather than guessing by directory name.

Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import self_improve_signals as sig
from shell_text import is_shell_tool, iter_segments, mask_data_regions, strip_heredoc_bodies

_MARKETPLACE_MARKER = Path(".claude-plugin") / "marketplace.json"
_EDIT_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})
_DREAM_SKILL = re.compile(r"meta-dream-")

# A statement is a WRITE when one of these sits in it. Redirections count because `printf x > f`
# is how a one-liner overwrites a hook (a redirect to /dev/null lands nothing); `tee` and `cp`/`mv`
# because they land a file; the git verbs because a commit or push in the marketplace is the
# detour's last step and the one that ships it. A verb must END at the word (`merge`, not
# `merge-base`): the read-only question was measured firing as the write.
_WRITE_VERB = re.compile(
    r"(?:^|[\s;&|(])(?:sed\s+(?:-[a-zA-Z]*i|--in-place)|tee|cp|mv|rm|rsync|install)\b"
    r"|(?:^|[\s;&|(])git\b.*?\s(?:commit|push|add|apply|am|cherry-pick|rebase|merge|checkout)(?=\s|$)"
)
# A redirect is judged on its own TARGET, never on the rest of the statement: `python3 <shipped
# script> > scratch.log` names the tool and writes the log. Measured 35 of 549 corpus firings.
#: `->` and `=>` are prose arrows, not redirects; a `$VAR` target cannot be resolved, so it is
#: never claimed to land in the repo.
_REDIRECT_TARGET = re.compile(r"(?<![<>=-])>>?\s*(?!&)['\"]?(?!\$)([^\s'\";|&()<>]+)")
# Inside a heredoc body, a Python or shell write to a path is the shape that edits a shipped file.
_BODY_WRITE = re.compile(r"write_text\(|write_bytes\(|open\([^)]*['\"][wa]|\.write\(|sed\s+-i|>\s*['\"]?/")
_PATH_TOKEN = re.compile(r"(?<![\w./-])(/[^\s'\";|&()<>]+|~/[^\s'\";|&()<>]+|\.{0,2}/[^\s'\";|&()<>]+)")
_CD = re.compile(r"cd\s+(['\"]?[^\s'\";|&]+)")
_GIT_VERB = re.compile(r"(?:^|[\s;&|(])git\b")

_NOTICE = (
    "TOOLING DETOUR: this call writes into the plugin source at %(root)s from a session whose "
    "project is %(cwd)s. Unless the user asked for this fix, do not make it here: record the "
    "symptom in one line with `contrib_queue.py add --what ... --target <hook|skill> --why ...` "
    "(home: `<plugin>/skills/meta-self-improve/`, launch via `hooks/run-python.sh`) and return "
    "to the work - the dream drains the queue. Measured over three weeks: a tool fixed in place "
    "from a work session was then gated, bumped, pushed and CI-watched there, a third of all "
    "instrumentation time in work sessions. This is said once per session."
)


def own_marketplace_name():
    """The name of the marketplace this plugin runs from, read off CLAUDE_PLUGIN_ROOT; None when
    the hook runs outside a plugin install, in which case nothing can be the plugin's source."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or ""
    if not root:
        return None
    try:
        return Path(root).resolve().parents[1].name or None
    except (IndexError, OSError):
        return None


def _is_marketplace_root(d: Path) -> bool:
    """True when `d` is the source repo of THIS plugin: a marketplace.json naming our marketplace."""
    own = own_marketplace_name()
    if not own:
        return False
    try:
        marker = d / _MARKETPLACE_MARKER
        if not marker.is_file():
            return False
        return json.loads(marker.read_text(encoding="utf-8")).get("name") == own
    except (OSError, ValueError, AttributeError):
        return False


def marketplace_root(path, is_root=_is_marketplace_root):
    """The nearest ancestor (or the path itself) that is a marketplace repo, else None. PURE given
    `is_root`: the filesystem question is the seam, so the shape is testable in a tmp tree."""
    try:
        p = Path(path)
    except (TypeError, ValueError):
        return None
    for d in (p, *p.parents):
        if is_root(d):
            return d
    return None


def in_dream_room(cwd, is_root=_is_marketplace_root) -> bool:
    """True when the session's cwd is inside a marketplace repo or the memory store."""
    try:
        p = Path(cwd)
    except (TypeError, ValueError):
        return False
    if any(part == sig.MEMORY_DIRNAME for part in p.parts):
        return True
    return marketplace_root(p, is_root) is not None


def _resolve(token, cwd):
    t = token.strip("'\"")
    if t.startswith("~/"):
        return Path.home() / t[2:]
    p = Path(t)
    return p if p.is_absolute() else Path(cwd) / p


def notice_path(path, cwd, is_root=_is_marketplace_root):
    """The nudge text when a write to `path` from a session at `cwd` is a detour, else None."""
    if not path or not cwd or in_dream_room(cwd, is_root):
        return None
    root = marketplace_root(_resolve(str(path), cwd), is_root)
    if root is None:
        return None
    return _NOTICE % {"root": root, "cwd": cwd}


def _heredoc_bodies(command: str) -> str:
    kept = set(strip_heredoc_bodies(command).split("\n"))
    return "\n".join(line for line in command.split("\n") if line not in kept)


def notice_bash(command, cwd, is_root=_is_marketplace_root, tool_name=None):
    """The nudge text when a shell WRITE names a path inside a marketplace repo, else None.

    Statements are judged with heredoc bodies stripped, so prose naming the tool is not a write to
    it; a body is judged on its own only when it contains a write call - the Python-heredoc edit
    that is the commonest inline fix - and names such a path.
    """
    if not command or not isinstance(command, str) or not cwd or in_dream_room(cwd, is_root):
        return None
    # A `cd` earlier in the same command moves every later statement: `cd <mkt> && git commit`
    # names no path in the statement that writes, so the effective cwd is what gets judged.
    here = cwd
    for _at, seg in iter_segments(strip_heredoc_bodies(command), tool_name):
        moved = _CD.match(seg.strip())
        if moved:
            here = str(_resolve(moved.group(1), here))
            continue
        root = None
        for target in _redirect_targets(seg):
            root = root or marketplace_root(_resolve(target, here), is_root)
        if root is None and _WRITE_VERB.search(seg):
            root = _first_marketplace_path(seg, here, is_root)
            if root is None and _GIT_VERB.search(seg):
                root = marketplace_root(here, is_root)
        if root is not None:
            return _NOTICE % {"root": root, "cwd": cwd}
    body = _heredoc_bodies(command)
    if body and _BODY_WRITE.search(body):
        root = _first_marketplace_path(body, cwd, is_root)
        if root is not None:
            return _NOTICE % {"root": root, "cwd": cwd}
    return None


def _redirect_targets(seg):
    """The targets of the redirections in one statement, with quoted regions ignored.

    A `>` inside quotes is data - a comparison in `python3 -c "... if n > 126"`, an awk program -
    and measured 56 firings before this. The mask is length-preserving, so a match found on the
    masked text is read off the RAW text at the same offsets; the target itself may be quoted
    (`> "plugins/x.py"`), which the mask hides, so the raw slice is what gets resolved.
    """
    masked = mask_data_regions(seg)
    out = []
    for m in _REDIRECT_TARGET.finditer(masked):
        raw = seg[m.start(1):m.end(1)].strip("'\"")
        if raw and not raw.startswith("$"):
            out.append(raw)
    return out


def _first_marketplace_path(text, cwd, is_root):
    for m in _PATH_TOKEN.finditer(text):
        root = marketplace_root(_resolve(m.group(1), cwd), is_root)
        if root is not None:
            return root
    return None


def _flag(session, suffix):
    return sig.session_state_path(session, suffix)


def _touch(path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("1\n", encoding="utf-8")
    except OSError:
        pass


def decide(event):
    """The nudge text for this event, or None. Handles the dream flag as a side effect."""
    session = str(event.get("session_id") or "")
    tool = event.get("tool_name")
    inp = event.get("tool_input") or {}
    if tool == "Skill":
        if session and _DREAM_SKILL.search(str(inp.get("skill") or "")):
            _touch(_flag(session, ".dream-session"))
        return None
    if session and (_flag(session, ".dream-session").exists()
                    or _flag(session, ".tooling-detour-said").exists()):
        return None
    cwd = event.get("cwd") or ""
    if tool in _EDIT_TOOLS:
        text = notice_path(inp.get("file_path"), cwd)
    elif is_shell_tool(tool):
        text = notice_bash(inp.get("command"), cwd, tool_name=tool)
    else:
        return None
    if text and session:
        _touch(_flag(session, ".tooling-detour-said"))
    return text


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    message = decide(event)
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
