#!/usr/bin/env python3
"""PostToolUse(AskUserQuestion): append every answered question to a git-ignored JSONL log.

A decision the user takes through AskUserQuestion is later relayed - into a decision log, a
subagent brief, a commit message - and a relay written from the controller's memory drops
qualifiers: twice a subagent built and green-tested the wrong rule from a one-line summary of an
option. This hook keeps the user's OWN text: the question, every option's label and description,
the chosen label, and any notes, one JSON line per question, so a relay can quote it verbatim.

Probed on interactive CLI 2.1.296: PostToolUse on AskUserQuestion receives `tool_response` with
`questions`, `answers` ({question: chosen label}) and `annotations`, and fires only for a question
that was actually shown and answered - a call refused at PreToolUse produces no event.

Where it writes (user decision 2026-10-12, "Own JSONL file"): `USER-DECISIONS.jsonl` at the root of
the MAIN checkout of the repository the session's cwd is in - a linked worktree logs there too, so
removing the worktree does not take the log with it. The name goes into the repository's own
exclude file unless git already ignores it, never into a tracked .gitignore and never skipped for
`track_private`: this log must not be committable. Outside a repository it falls back to
`~/.claude/self-improve-audit/<project-slug>.USER-DECISIONS.jsonl`. The hand-written
EXECUTION-USER-REVIEW.md is never touched.

Prints nothing, exits 0 always; any failure loses one record rather than wedging a turn.
"""

import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

from self_improve_signals import project_slug

LOG_NAME = "USER-DECISIONS.jsonl"

# Git variables that point a git call at some OTHER repository than the one -C names; a session
# launched from a git hook or a worktree push can inherit them.
_GIT_SCOPE_PREFIX = "GIT_"


def _git(cwd, *args):
    """(returncode, stdout) of one git call in `cwd` with inherited GIT_* scoping removed, or None."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(_GIT_SCOPE_PREFIX)}
    try:
        r = subprocess.run(["git", "-C", str(cwd), *args], check=False, capture_output=True,
                           timeout=5, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.returncode, os.fsdecode(r.stdout).strip()


def main_checkout_root(cwd):
    """The main checkout's root for the repository `cwd` is in, or None outside a work tree."""
    top = _git(cwd, "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir")
    if top is None or top[0] != 0:
        return None
    lines = top[1].splitlines()
    if len(lines) != 2:
        return None
    toplevel, common = Path(lines[0]), Path(lines[1])
    # A linked worktree's common dir is the main checkout's `.git`; anything else (a separate git
    # dir, a submodule's modules/ path) has no main checkout to find, so the work tree is used.
    if common.name == ".git" and common.parent.is_dir():
        return common.parent
    return toplevel


def ensure_excluded(root):
    """Add LOG_NAME to `root`'s exclude file unless git already ignores it. True when ignored."""
    asked = _git(root, "check-ignore", "-q", "--no-index", LOG_NAME)
    if asked is None:
        return False
    if asked[0] == 0:
        return True
    where = _git(root, "rev-parse", "--path-format=absolute", "--git-path", "info/exclude")
    if where is None or where[0] != 0 or not where[1]:
        return False
    exclude = Path(where[1])
    try:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        old = exclude.read_bytes() if exclude.exists() else b""
        sep = b"" if not old or old.endswith(b"\n") else b"\n"
        with open(exclude, "ab") as handle:
            handle.write(sep + LOG_NAME.encode("utf-8") + b"\n")
    except OSError:
        return False
    return True


def log_path(cwd):
    """Where this event's records go: the repo's main checkout root, else the audit dir."""
    root = main_checkout_root(cwd) if cwd else None
    if root is not None and ensure_excluded(root):
        return root / LOG_NAME
    audit = Path.home() / ".claude" / "self-improve-audit"
    return audit / (project_slug(str(cwd or "unknown")) + "." + LOG_NAME)


_JOIN = ", "


def _segmentations(text, labels):
    """Every set of distinct `labels` whose members, joined by ', ' in SOME order, spell `text`.

    A multiSelect answer arrives as the chosen labels joined by ', ', and a label may itself hold
    ', ' ("Yes, but slowly"), so splitting on the separator shatters it. The walk tries each
    unused label at each position instead; labels are few, so the search stays small.
    """
    found = set()

    def walk(at, used):
        if at == len(text):
            found.add(used)
            return
        for label in labels:
            if label in used or not text.startswith(label, at):
                continue
            end = at + len(label)
            if end == len(text):
                walk(end, used | {label})
            elif text.startswith(_JOIN, end):
                walk(end + len(_JOIN), used | {label})

    walk(0, frozenset())
    return found


def _chosen_options(question, chosen):
    """The option dicts the answer names, in option order; [] for free text or an ambiguous join."""
    options = [o for o in question.get("options") or [] if isinstance(o, dict)]
    exact = [o for o in options if o.get("label") == chosen]
    if exact or not question.get("multiSelect"):
        return exact
    labels = [o.get("label") for o in options if isinstance(o.get("label"), str) and o.get("label")]
    readings = _segmentations(chosen, labels)
    if len(readings) != 1:
        return []                                  # free text, or two readings: either is a guess
    picked = next(iter(readings))
    return [o for o in options if o.get("label") in picked]


def records(event, now):
    """One record per answered question in a PostToolUse AskUserQuestion event. PURE."""
    if not isinstance(event, dict) or event.get("tool_name") != "AskUserQuestion":
        return []
    body = event.get("tool_response")
    if not isinstance(body, dict) or "answers" not in body:
        body = event.get("tool_input")
    if not isinstance(body, dict):
        return []
    answers = body.get("answers") if isinstance(body.get("answers"), dict) else {}
    annotations = body.get("annotations") if isinstance(body.get("annotations"), dict) else {}
    out = []
    for question in body.get("questions") or []:
        if not isinstance(question, dict):
            continue
        text = question.get("question")
        chosen = answers.get(text)
        if not isinstance(chosen, str):
            continue
        out.append({
            "ts": now, "session_id": event.get("session_id"), "cwd": event.get("cwd"),
            "question": text, "header": question.get("header"),
            "multiSelect": bool(question.get("multiSelect")),
            "options": question.get("options") or [],
            "chosen": chosen, "chosen_options": _chosen_options(question, chosen),
            "annotation": annotations.get(text),
        })
    return out


def append(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    # One write call per event, in append mode: concurrent sessions interleave whole lines.
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(data)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: nothing to log
        return 0
    now = datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    rows = records(event, now)
    if not rows:
        return 0
    cwd = event.get("cwd") if isinstance(event.get("cwd"), str) else None
    append(log_path(cwd), rows)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
