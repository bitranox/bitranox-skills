"""Read the last turn out of a Claude Code transcript: the typed prompt, the reply, and the reply
the prompt answered.

Shared by the Stop gate (which judges the turn) and the classifier sites (which need the message a
short prompt like "yes" or "check it again" is answering). Pure standard library; every failure
reads as empty text, so a caller never wedges a turn on a missing or odd transcript.
"""

import json
import os
from typing import NamedTuple

# Transcripts grow to many MB, so only the tail is read: 64 KiB first, widened 4x at a time until
# the human prompt is in the window. A single tool output can be larger than the first window, and
# the prompt sits BEFORE every tool call of the turn. The cap bounds a pathological file; a miss
# only costs recall, never a wedged turn.
TAIL_BYTES = 65536
MAX_TAIL_BYTES = 16 * 1024 * 1024

# Records that carry `type: user` and text but were not typed by the person, for transcripts
# old enough to lack the `origin` field: slash-command echoes and their output, background-task
# notifications and teammate messages. Hook feedback and skill bodies are marked `isMeta`
# instead, and tool results carry no text block at all.
NOT_TYPED_PREFIXES = ("<command-", "<local-command", "<task-notification",
                      "Another Claude session sent a message", "<teammate-message")

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
    """
    if obj.get("type") != "user" or obj.get("isMeta") or obj.get("isCompactSummary"):
        return ""
    # A headless SDK run writes no `origin` key; its records name the entrypoint instead.
    if str(obj.get("entrypoint") or "").startswith("sdk"):
        return ""
    if "origin" in obj:
        origin = obj["origin"]
        if not (isinstance(origin, dict) and origin.get("kind") == "human"):
            return ""
    text = text_of(obj.get("message", {}).get("content"))
    if not text.strip() or text.lstrip().startswith(NOT_TYPED_PREFIXES):
        return ""
    return text


def is_hook_feedback(obj):
    """True for the record a blocking Stop hook writes into the transcript."""
    if obj.get("type") != "user":
        return False
    text = text_of(obj.get("message", {}).get("content")).lstrip()
    return text.startswith(HOOK_FEEDBACK_PREFIXES)


def scan(data):
    """The Turn among the complete JSONL lines of `data` (bytes)."""
    prompt = reply = before = ""
    answering_hook = False
    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line.decode("utf-8", "replace"))
        except ValueError:
            continue
        if obj.get("type") == "assistant":
            # Each content block is its own record (thinking, text, tool_use), so skip the ones
            # with no text rather than letting a trailing tool_use blank the reply.
            if not answering_hook:
                reply = text_of(obj.get("message", {}).get("content")) or reply
            continue
        if is_hook_feedback(obj):
            answering_hook = True
            continue
        typed = human_text(obj)
        if typed:
            prompt, before, reply, answering_hook = typed, reply, "", False
    return Turn(prompt, reply or "", before)


def _tail(path, window):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size > window:
            fh.seek(size - window)
            fh.readline()  # drop the partial first line after the seek
        return fh.read(), size


def read_turn(transcript_path, tail_bytes=TAIL_BYTES, max_bytes=MAX_TAIL_BYTES):
    """The last Turn of the transcript, widening the tail until the prompt is in it."""
    window = tail_bytes
    while True:
        try:
            data, size = _tail(transcript_path, window)
        except (OSError, TypeError, ValueError):
            return Turn("", "", "")
        turn = scan(data)
        if turn.prompt or window >= size or window >= max_bytes:
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
    for raw in data.splitlines():
        try:
            obj = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            continue
        if obj.get("type") != "assistant":
            continue
        content = obj.get("message", {}).get("content")
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


def excerpt(text, cap):
    """`text` trimmed to about `cap` characters, keeping both ends: a reply's opening says what
    it is about and its end usually holds the question a short answer like "yes" refers to."""
    text = (text or "").strip()
    if len(text) <= cap:
        return text
    half = cap // 2
    return text[:half].rstrip() + EXCERPT_MARK + text[-half:].lstrip()
