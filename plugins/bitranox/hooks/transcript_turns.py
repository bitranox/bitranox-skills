"""Read the last turn out of a Claude Code transcript: the typed prompt, the reply, and the reply
the prompt answered.

Shared by the Stop gate (which judges the turn) and the classifier sites (which need the message a
short prompt like "yes" or "check it again" is answering). Pure standard library; every failure
reads as empty text, so a caller never wedges a turn on a missing or odd transcript.
"""

import json
import os
import re
from typing import NamedTuple

# Transcripts grow to many MB, so only the tail is read: 64 KiB first, widened 4x at a time until
# the window holds the human prompt AND the reply it answered (or the prompt before it, past which
# there is nothing to find). A single tool output can be larger than the first window, and it can
# sit on either side of the prompt. The cap bounds a pathological file; a miss only costs recall,
# never a wedged turn.
TAIL_BYTES = 65536
MAX_TAIL_BYTES = 16 * 1024 * 1024

# Records that carry `type: user` and text but were not typed by the person, for transcripts
# old enough to lack the `origin` field: slash-command echoes and their output, background-task
# notifications and teammate messages. Hook feedback and skill bodies are marked `isMeta`
# instead, and tool results carry no text block at all.
#
# `<bash-input` and `<bash-stdout` are the `!` shell escape and its output: the person typed the
# COMMAND, but not prose any of these readers should score. `<pasted_content` is deliberately
# absent and must stay absent - a person pasting a question wraps it in exactly that, so no
# blanket "opens with a tag" rule may be written here.
#
# `<agent-message` is a subagent's hand-back as the UserPromptSubmit hook receives it: bare. The
# transcript stores the same turn behind "Another Claude session sent a message", so a reader of
# the file was covered while every prompt-time hook scored the envelope as a typed request.
# `<cross-session-message` is the same gap for a message from another session: the hook receives
# the bare envelope, the transcript the "Another Claude session" form.
NOT_TYPED_PREFIXES = ("<command-", "<local-command", "<task-notification",
                      "Another Claude session sent a message", "<agent-message",
                      "<cross-session-message",
                      "<teammate-message", "[Request interrupted", "<bash-input", "<bash-stdout")

# The shapes a prefix structurally cannot reach. This one opens with a COUNT, so there is no
# literal to list. Measured over the corpus: 112 of 1,409 turns these readers called typed were
# the harness talking, 14 of them this shape, and each one costs a keyword match, a classifier
# request and a skill's once-per-session nudge.
NOT_TYPED_PATTERNS = (re.compile(r"^\d+\s+background\s+agents?\s+(?:were|was)\s+stopped\b"),)


def looks_typed(text):
    """False for a turn the harness produced rather than the person.

    One registry, two mechanisms: the cheap prefix tuple, then the patterns for shapes no prefix
    can match. Callers ask this rather than reading either collection, so a shape added for one
    reader is never missing from another.
    """
    head = (text or "").lstrip()
    if head.startswith(NOT_TYPED_PREFIXES):
        return False
    return not any(pattern.match(head) for pattern in NOT_TYPED_PATTERNS)

EXCERPT_MARK = " [...] "

# A blocking Stop hook's message is written as an `isMeta` user record with this prefix, and the
# assistant then answers the HOOK, often in one line. That answer is not what the person reads and
# replies to, so it must not displace the reply before it. Skill bodies are `isMeta` too, and the
# text after one IS the reply, so this matches the prefix, never `isMeta` alone.
HOOK_FEEDBACK_PREFIXES = ("Stop hook feedback:",)


class Turn(NamedTuple):
    prompt: str               # the last message the person typed
    reply: str                # the newest assistant text
    reply_before_prompt: str  # the assistant text the prompt answered


def _content(obj):
    """The `message.content` of a record, or None - whatever shape the line turned out to have."""
    message = obj.get("message") if isinstance(obj, dict) else None
    return message.get("content") if isinstance(message, dict) else None


def text_of(content):
    """Flatten a transcript message's content (string, or list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b["text"] for b in content
                        if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


def human_text(obj):
    """The text of a `user` record the person actually typed, else "".

    A turn's last `user` record is almost never the prompt: every tool call is answered by a
    `user` record holding a tool_result, and hooks, skills and task notifications inject more.
    Claude Code writes `origin.kind == "human"` on a typed prompt and `origin: null` on the prompt
    of a headless `claude -p` / SDK run and on a teammate message - measured over the corpus,
    those were 244 of the 268 prompts a looser rule added, and blocking a headless run on its own
    task brief is damage, not a learning signal. Headless runs that write no `origin` key at all
    are told apart by `entrypoint: sdk-*`. A transcript old enough to have neither falls back to
    excluding the known injected shapes.

    A prompt typed while the assistant is busy is written only as an `attachment` record of type
    `queued_command`, never as a `user` record; its `origin` tells it apart from the task
    notifications, subagent hand-backs and coordinator messages the same queue carries. Measured
    over the corpus: 368 such prompts, each recorded once (every one `absorbed_mid_turn`).
    """
    if not isinstance(obj, dict):
        return ""
    # A headless SDK run writes no `origin` key; its records name the entrypoint instead.
    if str(obj.get("entrypoint") or "").startswith("sdk"):
        return ""
    if obj.get("type") == "attachment":
        return _queued_human_text(obj.get("attachment"))
    if obj.get("type") != "user" or obj.get("isMeta") or obj.get("isCompactSummary"):
        return ""
    if "origin" in obj:
        origin = obj["origin"]
        if not (isinstance(origin, dict) and origin.get("kind") == "human"):
            return ""
    text = text_of(_content(obj))
    if not text.strip() or not looks_typed(text):
        return ""
    return text


def _queued_human_text(attachment):
    """The prompt of a `queued_command` attachment the person typed, else ""."""
    if not isinstance(attachment, dict) or attachment.get("type") != "queued_command":
        return ""
    origin = attachment.get("origin")
    if not (isinstance(origin, dict) and origin.get("kind") == "human"):
        return ""
    text = attachment.get("prompt")
    if not isinstance(text, str) or not text.strip() or not looks_typed(text):
        return ""
    return text


def is_hook_feedback(obj):
    """True for the record a blocking Stop hook writes into the transcript."""
    if not isinstance(obj, dict) or obj.get("type") != "user":
        return False
    return text_of(_content(obj)).lstrip().startswith(HOOK_FEEDBACK_PREFIXES)


def _records(data):
    """The JSON objects among the complete lines of `data` (bytes); any other line is skipped."""
    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line.decode("utf-8", "replace"))
        except ValueError:
            continue
        if isinstance(obj, dict):
            yield obj


def _scan(data):
    """(Turn, number of typed prompts seen) for the complete JSONL lines of `data` (bytes)."""
    prompt = reply = before = ""
    prompts = 0
    answering_hook = False
    for obj in _records(data):
        if obj.get("type") == "assistant":
            # Each content block is its own record (thinking, text, tool_use), so skip the ones
            # with no text rather than letting a trailing tool_use blank the reply.
            if not answering_hook:
                reply = text_of(_content(obj)) or reply
            continue
        if is_hook_feedback(obj):
            answering_hook = True
            continue
        typed = human_text(obj)
        if typed:
            prompt, before, reply, answering_hook = typed, reply, "", False
            prompts += 1
    return Turn(prompt, reply or "", before), prompts


def scan(data):
    """The Turn among the complete JSONL lines of `data` (bytes)."""
    return _scan(data)[0]


def _tail(path, window):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size > window:
            fh.seek(size - window)
            fh.readline()  # drop the partial first line after the seek
        return fh.read(), size


def read_turn(transcript_path, tail_bytes=TAIL_BYTES, max_bytes=MAX_TAIL_BYTES):
    """The last Turn of the transcript, widening the tail until the turn is complete in it.

    Complete means the prompt is in the window and so is what it answered: an assistant text
    before it (the newest one is then necessarily inside the window, which is a suffix), or the
    PREVIOUS prompt, which proves the turn before had no text to find.
    """
    window = tail_bytes
    while True:
        try:
            data, size = _tail(transcript_path, window)
        except (OSError, TypeError, ValueError):
            return Turn("", "", "")
        turn, prompts = _scan(data)
        complete = bool(turn.prompt) and (bool(turn.reply_before_prompt) or prompts >= 2)
        if complete or window >= size or window >= max_bytes:
            return turn
        window *= 4


def last_reply(transcript_path, tail_bytes=TAIL_BYTES, max_bytes=MAX_TAIL_BYTES):
    """The newest assistant text in the transcript, whether or not a prompt follows it.

    At UserPromptSubmit the new prompt may not be on disk yet, so "the reply before the last
    prompt" could name the reply before the PREVIOUS one. The newest assistant text is the one
    being answered either way."""
    turn = read_turn(transcript_path, tail_bytes, max_bytes)
    return turn.reply or turn.reply_before_prompt


# Skills are looked up over a wider tail than a turn: one invoked early in a long session is still
# loaded, and the only record of it is the Skill call itself.
SKILLS_TAIL_BYTES = 1024 * 1024
_FILE_TOOLS = ("Read", "Edit", "Write", "NotebookEdit")


def _tool_calls(transcript_path, window):
    """(name, input) of every tool_use block in the transcript tail, oldest first."""
    try:
        data, _size = _tail(transcript_path, window)
    except (OSError, TypeError, ValueError):
        return []
    calls = []
    for obj in _records(data):
        if obj.get("type") != "assistant":
            continue
        content = _content(obj)
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                calls.append((str(block.get("name") or ""), inp))
    return calls


def _label(name, inp):
    """A short, safe label for one tool call. A Bash call is named by the description the model
    wrote for it, never by its command line, which can carry hostnames, paths and arguments."""
    if name == "Bash" or name in ("Agent", "Task"):
        desc = str(inp.get("description") or "").strip()
        return "%s: %s" % (name, desc) if desc else name
    if name in _FILE_TOOLS:
        path = str(inp.get("file_path") or inp.get("notebook_path") or "")
        base = path.replace("\\", "/").rsplit("/", 1)[-1]
        return "%s: %s" % (name, base) if base else name
    if name == "Skill":
        skill = str(inp.get("skill") or "").rsplit(":", 1)[-1]
        return "Skill: %s" % skill if skill else name
    return name


def recent_activity(transcript_path, n=6, cap=300, tail_bytes=TAIL_BYTES):
    """The last `n` tool calls as short labels, oldest first, trimmed to about `cap` characters:
    what "it" in a prompt like "check it again" refers to."""
    labels = [_label(name, inp) for name, inp in _tool_calls(transcript_path, tail_bytes)[-n:]]
    return excerpt("; ".join(label for label in labels if label), cap)


def skills_used(transcript_path, tail_bytes=SKILLS_TAIL_BYTES):
    """The skills invoked in the transcript tail, without their plugin prefix, sorted."""
    names = {str(inp.get("skill") or "").rsplit(":", 1)[-1]
             for name, inp in _tool_calls(transcript_path, tail_bytes) if name == "Skill"}
    return sorted(n for n in names if n)


# A CronCreate or ScheduleWakeup fire reaches UserPromptSubmit as bare text, and on CLI 2.1.283
# its payload carries the same keys as a typed prompt while its transcript record (isMeta,
# promptSource "system") is written only AFTER the hook ran. The scheduling call is the one thing
# already on disk: its `prompt` argument is the text that later arrives. Measured over the corpus,
# that call sits in the receiving transcript for 46 of 51 fires; the rest were scheduled by an
# earlier session and are not reachable from here.
SCHEDULING_TOOLS = ("CronCreate", "ScheduleWakeup")
# A cron fires long after it was created, so the WHOLE transcript is searched, not a turn tail.
# The file is scanned for the tool name as bytes and only those lines are parsed, which keeps a
# prompt with no scheduling call in its session (nearly all of them) at one byte search. The cap
# bounds a pathological file; the largest transcript here was 12.6 MB.
SCHEDULE_MAX_BYTES = 64 * 1024 * 1024


def _lines_naming(data, needle):
    """Every complete line of `data` (bytes) that contains `needle`, each once."""
    seen, start = set(), data.find(needle)
    while start != -1:
        begin = data.rfind(b"\n", 0, start) + 1
        end = data.find(b"\n", start)
        end = len(data) if end == -1 else end
        if begin not in seen:
            seen.add(begin)
            yield data[begin:end]
        start = data.find(needle, end)


def scheduled_prompts(transcript_path, max_bytes=SCHEDULE_MAX_BYTES):
    """The `prompt` argument of every CronCreate / ScheduleWakeup call in the transcript,
    stripped. Empty when the file is missing or unreadable."""
    try:
        data, _size = _tail(transcript_path, max_bytes)
    except (OSError, TypeError, ValueError):
        return set()
    found = set()
    for tool in SCHEDULING_TOOLS:
        for obj in _records(b"\n".join(_lines_naming(data, tool.encode("ascii")))):
            content = _content(obj) if obj.get("type") == "assistant" else None
            for block in content if isinstance(content, list) else []:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") == tool and isinstance(block.get("input"), dict)):
                    prompt = str(block["input"].get("prompt") or "").strip()
                    if prompt:
                        found.add(prompt)
    return found


def scheduled_by_the_session(prompt, transcript_path):
    """True when `prompt` is exactly the text a CronCreate / ScheduleWakeup call in this session
    scheduled: the harness is talking, not the person. A prompt that merely QUOTES that text is
    typed, so the comparison is whole-text, not a substring."""
    text = (prompt or "").strip()
    return bool(text) and bool(transcript_path) and text in scheduled_prompts(transcript_path)


def is_scheduled_record(obj):
    """True for the record the harness writes for a scheduled fire, AFTER the prompt-time hooks
    ran: a `user` record with promptSource "system" and a scheduledTaskId. For reading a
    transcript afterwards; a prompt-time hook cannot see it yet (use scheduled_by_the_session)."""
    return (isinstance(obj, dict) and obj.get("type") == "user"
            and obj.get("promptSource") == "system" and bool(obj.get("scheduledTaskId")))


def scheduled_text(obj):
    """The prompt text of a scheduled-fire record (see is_scheduled_record), else ""."""
    return text_of(_content(obj)) if is_scheduled_record(obj) else ""


def excerpt(text, cap):
    """`text` trimmed to about `cap` characters, keeping both ends: a reply's opening says what
    it is about and its end usually holds the question a short answer like "yes" refers to."""
    text = (text or "").strip()
    if len(text) <= cap:
        return text
    half = cap // 2
    if half == 0:  # text[-0:] would be the whole text
        return text[:max(0, cap)]
    return text[:half].rstrip() + EXCERPT_MARK + text[-half:].lstrip()
