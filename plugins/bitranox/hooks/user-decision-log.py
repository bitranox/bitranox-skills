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

Stop: the remark a user types while REJECTING a plan (ExitPlanMode) binds just as hard, and it
arrives through no hook. Read in the CLI 2.1.325 binary: the user-rejection path writes the
tool_result and runs no hook with the text (PostToolUseFailure fires only when a tool executes and
fails; PermissionDenied only for an auto-mode classifier denial). The transcript has it, as a user
record with `toolDenialKind: "user-rejected"` and `userFeedback`, so on Stop the hook reads the
transcript from the offset its previous Stop reached and logs each such remark once, as a typed
remark with no options (`kind: "plan-rejection"`, the remark in `chosen`, so readers that quote a
record by its question or chosen text find it). A record written before those fields existed is
read from the result text after "the user said:". Only ExitPlanMode is read: a remark rejecting a
single command is about that command, and logging it would bury the plan remarks in noise.

Where it writes (user decision 2026-10-12, "Own JSONL file"): `USER-DECISIONS.jsonl` at the root of
the MAIN checkout of the repository the session was LAUNCHED in - a linked worktree logs there too,
so removing the worktree does not take the log with it. The launch directory is the cwd of the
first transcript record that has one, because the event's `cwd` is where the shell sat when the
user answered, and a session that had changed into a nested repository (a sub-checkout under an
umbrella, even a public fork's checkout) would otherwise log there while every reader looks at the
session's own root. When the launch directory is unknown or in no repository the event's `cwd`
decides, and each record keeps that `cwd` either way. The name goes into the repository's own
exclude file unless git already ignores it, never into a tracked .gitignore and never skipped for
`track_private`: this log must not be committable. Outside a repository it falls back to
`~/.claude/self-improve-audit/<project-slug>.USER-DECISIONS.jsonl`. The hand-written
EXECUTION-USER-REVIEW.md is never touched.

Prints nothing, exits 0 always; any failure loses one record rather than wedging a turn.
"""

import datetime
import json
import sys
from pathlib import Path

import claude_paths
from hook_event import StopEvent, parse_stop
from self_improve_signals import git_scoped as _git
from self_improve_signals import main_checkout_root, project_slug, session_state_path

LOG_NAME = "USER-DECISIONS.jsonl"
PLAN_TOOL = "ExitPlanMode"
_SAID = "the user said:\n"
_NOTE = "\n\nNote: "
_OFFSET_SUFFIX = ".decision-log-offset"

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
    audit = claude_paths.audit_dir()
    return audit / (project_slug(str(cwd or "unknown")) + "." + LOG_NAME)


# Only the opening records are read: the launch cwd is on the first one that carries any.
_TRANSCRIPT_HEAD_LINES = 50


def launch_cwd(transcript_path):
    """The directory the session started in, from its transcript's opening records, else None."""
    if not isinstance(transcript_path, str) or not transcript_path:
        return None
    try:
        with open(transcript_path, "rb") as handle:
            for _, raw in zip(range(_TRANSCRIPT_HEAD_LINES), handle):
                try:
                    record = json.loads(raw)
                except ValueError:
                    continue
                cwd = record.get("cwd") if isinstance(record, dict) else None
                if isinstance(cwd, str) and cwd:
                    return cwd
    except OSError:
        return None
    return None


def log_cwd(event):
    """The directory whose repository owns this event's log: the launch cwd, else the event's."""
    event_cwd = event.get("cwd") if isinstance(event.get("cwd"), str) else None
    launched = launch_cwd(event.get("transcript_path"))
    return launched if launched and main_checkout_root(launched) is not None else event_cwd


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


def _result_text(block):
    content = block.get("content")
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return content if isinstance(content, str) else ""


def _remark(record, block):
    """The text the user typed with a rejection, or "" for a bare rejection or a non-rejection."""
    feedback = record.get("userFeedback")
    if record.get("toolDenialKind") == "user-rejected" and isinstance(feedback, str):
        return feedback.strip()
    text = _result_text(block)
    if not block.get("is_error") or _SAID not in text:
        return ""
    return text.split(_SAID, 1)[1].split(_NOTE, 1)[0].strip()


def _plan_title(tool_input):
    plan = tool_input.get("plan") if isinstance(tool_input, dict) else None
    for line in (plan if isinstance(plan, str) else "").splitlines():
        title = line.strip().lstrip("#").strip()
        if title:
            return "Plan rejected: " + title[:200]
    return "Plan rejected"


def plan_rejections(lines, event, now):
    """One record per plan rejection that carries a typed remark, in transcript order. PURE.

    `lines` is an iterable of raw transcript lines (bytes). The plan's tool_use precedes its
    result in the same turn, and every Stop window starts where the previous turn ended, so a
    window holds both.
    """
    plans, out = {}, []
    for raw in lines:
        if PLAN_TOOL.encode() not in raw and b"tool_result" not in raw:
            continue                                   # cheap skip: most lines are neither
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        message = record.get("message") if isinstance(record, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == PLAN_TOOL:
                plans[block.get("id")] = _plan_title(block.get("input"))
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in plans:
                remark = _remark(record, block)
                if remark:
                    out.append({
                        "ts": now, "session_id": event.get("session_id"), "cwd": event.get("cwd"),
                        "kind": "plan-rejection", "tool_use_id": block.get("tool_use_id"),
                        "question": plans[block.get("tool_use_id")],
                        "header": "Plan rejected", "multiSelect": False, "options": [],
                        "chosen": remark, "chosen_options": [], "annotation": None,
                    })
    return out


def _window(handle, progress):
    """Each complete line from the handle's position on; `progress[0]` grows by each one's size.

    A generator, so a large window is never held whole: only the remarks found are kept.
    """
    for raw in handle:
        if not raw.endswith(b"\n"):
            return                                     # mid-write: read it on the next Stop
        progress[0] += len(raw)
        yield raw


def _logged_ids(path):
    """tool_use_ids already in the log, so a lost offset cannot log a remark twice."""
    ids = set()
    try:
        with open(path, "rb") as handle:
            for raw in handle:
                if b"tool_use_id" not in raw:
                    continue
                try:
                    ids.add(json.loads(raw).get("tool_use_id"))
                except (ValueError, AttributeError):
                    continue
    except OSError:
        pass
    return ids


def on_stop(event: StopEvent, now: str) -> None:
    """Log the plan-rejection remarks the transcript gained since the previous Stop."""
    transcript, session = event.get("transcript_path"), event.get("session_id")
    if not isinstance(transcript, str) or not transcript or not isinstance(session, str):
        return
    state = session_state_path(session, _OFFSET_SUFFIX)
    try:
        start = int(state.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        start = 0
    progress = [start]
    try:
        if start > Path(transcript).stat().st_size:
            progress = [0]                             # a replaced or shrunk transcript
        with open(transcript, "rb") as handle:
            handle.seek(progress[0])
            rows = plan_rejections(_window(handle, progress), event, now)
    except OSError:
        return
    if rows:
        path = log_path(log_cwd(event))
        seen = _logged_ids(path)
        rows = [r for r in rows if r["tool_use_id"] not in seen]
        if rows:
            append(path, rows)
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(str(progress[0]) + "\n", encoding="utf-8")
    except OSError:
        pass


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
    stop = parse_stop(event)
    if stop is not None and stop.get("hook_event_name") == "Stop":
        on_stop(stop, now)
        return 0
    rows = records(event, now)
    if not rows:
        return 0
    append(log_path(log_cwd(event)), rows)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
