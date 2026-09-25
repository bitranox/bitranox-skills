"""The part of a prompt a keyword or trigger matcher may score.

A keyword matcher sees one flat string, so it cannot tell prose from a path, an id or an XML
envelope - and a path on this machine carries project names, tool names and the word `claude`,
which are exactly the topical terms a trigger map is built from. Measured 2026-09-22 on
`skill-router.py`: a 409-character `<task-notification>` turn reached the 2-keyword threshold for
ELEVEN skills, `claude`, `code` and `bitranox` all coming from its output-file path. The nudge is
false by construction, and because a skill nudges at most once per session, every such match
silenced a skill for the prompt where it would have been right.

Two answers, and a caller needs both: `typed_by_a_person` rejects a whole machine-generated turn,
`prose` removes what is not prose from the rest, and `scorable_prose` composes them. Whitespace is
collapsed, because every consumer is a keyword scan that cannot see it.

Pure standard library; shared by `skill-router.py` and `recall-memory.py`, which take the same
input and therefore had the same defect.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import transcript_turns  # noqa: E402

# Tag markup, not the prose between tags: `<system-reminder priority="high">` carries `system`,
# `reminder`, `priority` and `high`, none of which the person said. Only a TAG-SHAPED span counts:
# a name (or `!`/`?`) right after the `<`, so a comparison ("free < 3 GB ... is > 90%", "x < y and
# y > z") keeps the words between its `<` and a later `>`. An opening tag must also not be glued
# to a word, which keeps the type in `Vec<String>`; a closing tag may be (`failed</x>`). Bounded so
# an unclosed `<` cannot swallow the rest of the line.
_TAG = re.compile(r"</[A-Za-z][^<>]{0,400}>|(?<!\w)<[A-Za-z!?][^<>]{0,400}>")

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:[\\/]")
_FILENAME_TAIL = re.compile(r"/[^/]*\.[A-Za-z0-9]{1,8}$")
# The `:12`, `:12:5` or `:84-85` a traceback, linter or `grep -n` appends to a file name, or the
# `#L12` / `#L12-L20` a GitHub URL uses for the same thing. None of it is part of the name, and
# left on it hid the file from the one-separator test and stuck to the file type.
_LINE_SUFFIX = re.compile(r"(?:(?::\d+(?:-\d+)?)+|#L\d+(?:-L\d+)?)$")

# Opaque identifiers: a uuid, a long hex run (a sha or an id fragment), a Claude tool-use id. The
# bar is 16 hex characters because the SHORT hex codes are real trigger keywords - `0xc1900200`
# and `0x7b` are what a user in trouble types verbatim, and dropping them would silence exactly
# the skill they need.
_OPAQUE_ID = re.compile(
    r"^(?:"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|[0-9a-fA-F]{16,}"
    r"|toolu[A-Za-z0-9_-]*"
    r")$")

# A dashed path slug (`-media-srv-main-softdev-projects-public`, a ~/.claude/projects key). Real
# hyphenated terms top out around three hyphens (`non-constant-time`), which is the same bar
# gather_scan._is_junk_token uses, so the two siblings agree on what an identifier looks like.
_SLUG_HYPHENS = 4

_EDGE_PUNCTUATION = "\"'`,;:.!?()[]{}<>"


def typed_by_a_person(prompt):
    """False for a whole turn the person did not type: a task notification, a slash-command echo
    or its output, a teammate message, an interruption notice, a shell escape.
    `transcript_turns.looks_typed` owns the shapes, so one added for the Stop gate is never
    missing here."""
    return transcript_turns.looks_typed(prompt)


def _looks_like_a_path(token):
    """True for a filesystem path. One separator is not enough on its own - `and/or`, `yes/no` and
    `24/7` are prose - so a single-separator token counts only when a segment names a file."""
    core = _LINE_SUFFIX.sub("", token.strip(_EDGE_PUNCTUATION))
    if not core:
        return False
    if core.startswith(("/", "~/", "./", "../")) or _WINDOWS_DRIVE.match(core):
        return True
    separators = core.count("/") + core.count("\\")
    if separators == 0:
        return False
    if separators >= 2:
        return True
    return bool(_FILENAME_TAIL.search(core.replace("\\", "/")))


def _is_not_prose(token):
    core = token.strip(_EDGE_PUNCTUATION)
    return bool(_OPAQUE_ID.match(core)) or core.count("-") >= _SLUG_HYPHENS


def _file_type(token):
    """A path's extension, which is all of it that is prose - or "" when it has none.

    Measured over 3,483 typed prompts from the transcript corpus: dropping a path whole cost one
    genuine match (a request about `src/<pkg>/defaultconfig.toml` stopped reaching
    `files-edit-toml`), and keeping the BASENAME recovered it but admitted two false firings, from
    a git branch name and a device node. Keeping only the extension recovered that match and
    admitted nothing - the directories carry project and tool names, the stem carries a branch or
    a scratch script, and the extension carries the file TYPE a request is usually about.
    """
    core = _LINE_SUFFIX.sub("", token.strip(_EDGE_PUNCTUATION))
    base = core.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[-1] if "." in base[1:] else ""


def prose(text):
    """`text` with tag markup, ids, hashes and dashed slugs removed, and each path reduced to its
    file type."""
    out = []
    for token in _TAG.sub(" ", text or "").split():
        if _looks_like_a_path(token):
            kind = _file_type(token)
            if kind and not _is_not_prose(kind):
                out.append(kind)
            continue
        if not _is_not_prose(token):
            out.append(token)
    return " ".join(out)


def scorable_prose(prompt):
    """What a keyword matcher may score in `prompt`: its prose, or "" for a machine turn."""
    return prose(prompt) if typed_by_a_person(prompt) else ""


# A task notification stores one child element per line - <task-id>, <tool-use-id>, <output-file>,
# <status>, <summary>. Only the last two say anything: the ids are opaque and the path is what
# made the envelope match eleven skills, so neither is read.
_NOTIFICATION_TAG = "<task-notification"
_NOTIFICATION_FIELDS = (("task_status", "status"), ("task_summary", "summary"))


def _element(text, name):
    """The text of the first `<name>...</name>` element, whitespace collapsed, else ""."""
    match = re.search(r"<%s>(.*?)</%s>" % (name, name), text, re.DOTALL)
    return " ".join(match.group(1).split()) if match else ""


def notification_fields(prompt):
    """A `<task-notification>` turn as the named fields worth judging, else {}.

    The envelope is not a prompt, so it must not be sent as one - but a background task that has
    just FAILED can genuinely need a skill, which is why the turn is still worth a classifier
    question. Its output file is deliberately NOT read: the path comes from the turn's own text,
    so reading it would let a forged envelope name any file on the machine and send it to the API.
    """
    text = prompt or ""
    if not text.lstrip().startswith(_NOTIFICATION_TAG):
        return {}
    fields = {name: _element(text, element) for name, element in _NOTIFICATION_FIELDS}
    return {k: v for k, v in fields.items() if v} if any(fields.values()) else {}
