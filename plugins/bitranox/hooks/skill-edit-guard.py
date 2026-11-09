#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit|Bash|PowerShell) guard: a SKILL.md edit must go through the skill-writer process.

Editing a shipped `SKILL.md` by hand - skipping `bitranox:meta-skill-writer`'s RED-GREEN-REFACTOR / Iron
Law (baseline test first, sibling tests for any bundled script) - is the exact miss this guard prevents.
A skill grows into a mess by accretion when edits bypass that process; the standing "use the applicable
skill" rule is advisory prose that loses under momentum, so this is the deterministic backstop.

Decision on an `Edit`/`Write`/`MultiEdit`/`NotebookEdit` whose target (`file_path`, or
`notebook_path` for NotebookEdit) is a `.../skills/<name>/SKILL.md`, matched ignoring letter case and
after backslashes become `/` and `.`/`..` segments collapse:
  - BLOCK (exit 2): the tool call is denied and the reason is fed back to the MODEL, which then redirects
    itself to meta-skill-writer. The user is NOT prompted (enforced, not asked).
  - UNLESS BOTH of these hold:
    1. this session holds a fresh meta-skill-writer receipt: `skill_receipt.is_fresh`, keyed by the
       event's `session_id`, valid for 8 hours. Step 0 of meta-skill-writer arms it by running
       `skill_receipt.py start meta-skill-writer`, and its last step's `end` disarms it.
    2. the EDITING AGENT loaded meta-skill-writer: its own transcript holds the record the harness
       writes when a skill loads - a `type: user`, `isMeta: true` message whose text starts
       `Base directory for this skill: <dir>`, with `<dir>`'s last segment `meta-skill-writer`.
       Written the same way for a Skill tool call and a typed slash command.
    The receipt alone is not proof, because it is keyed by session and a subagent shares its
    parent's: probed on Claude Code 2.1.295, a subagent's PreToolUse event carries the MAIN
    session's `session_id` and `transcript_path` plus its own `agent_id`, and its Bash sees the
    parent's CLAUDE_CODE_SESSION_ID. So a subagent running `start` by hand armed every agent in the
    session without any of them loading the skill. The editing agent's transcript is the main one,
    or, when `agent_id` is set, `<transcript_path minus .jsonl>/subagents/agent-<agent_id>.jsonl`
    (a Task subagent) or `.../subagents/workflows/<wf_id>/agent-<agent_id>.jsonl` (a Workflow
    agent), resolved by `transcript_siblings.agent_transcript`.
  - UNLESS the env `BITRANOX_SKILL_WRITER` is set: the emergency bypass. NOTE: a shell `export` in a
    Bash tool call does NOT reach this hook (separate process) - the env must be set at SESSION start.
  - AFTER both checks pass, once per (session, agent, skill): when the skill's ledger holds a
    live rejected or removed entry and the editing agent's transcript shows no
    `skill_decisions.py show <skill>` call, the first edit is refused with those entries
    (`render_brief`) and a `show` command naming this install's script and the skill's own dir
    (`show_command`), so it runs from any cwd; the re-send passes. A tool repo's twin of a
    mirrored skill holds no ledger of its own, so its edit gets the marketplace copy's
    (`ledger_dir`, via the `mirrored_skills` table). This direction fails OPEN: an
    unreadable ledger, a missing module or an unstorable flag lets the edit through, because the
    commit gate owns ledger integrity and this refusal only delivers reading.

Decisions:
- Refuse once, not every time, and never when the agent ran `show`: the user chose the
  refuse-once form for EnterWorktree and the question-premise hook (2026-10-12), and an agent
  that followed the procedure must never pay for it. Priced on 2026-11-06 by replaying the
  transcript corpus: 5679 transcripts scanned, 487 first SKILL.md edits per (agent, skill), in
  121 sessions; 482 of those edits (118 sessions) fell in the last 30 days, and none followed a
  `show` call. The corpus itself reaches back only to 2026-10-06 (one stray transcript from
  2026-05-22 aside), about the transcript retention window, so the 482 is close to the whole
  visible history, not a rate sampled from a longer one. That is the upper bound once every
  skill has a ledger; only a skill holding a live rejected or removed entry can refuse. Reopen
  if the refusal log shows agents re-sending unchanged edits without reading the brief.
- `ran_show` credits any Bash command in the agent's transcript that names `skill_decisions.py`
  and then `show` directly followed by the skill's name, whatever else the command holds (an
  `echo` quoting it, a pipe, other flags) and whichever ledger it read. It is a cheap check for
  a refuse-once nudge, accepted as such: an agent that wants to dodge one refusal can, and the
  commit gate, not this guard, is what holds the recorded decisions.

A Bash call that writes a SKILL.md is held to the same rule: a redirect (`> .../SKILL.md`, `tee`),
`sed -i`, or `cp`/`mv`/`install` onto one is refused without the receipt and the skill load. A
Python program that names a SKILL.md path and calls a write only gets a NUDGE, because replaying
202k recorded Bash calls found 131 such programs outside a skill-writer session, many writing
another file and only mentioning the path, while the 10 shell-shape firings were all real writes.
A script merely GIVEN a path is not judged: a reader and a writer look identical from outside it.

Errors split by direction. Unparseable stdin and any error escaping `main` fail OPEN (exit 0): a broken
guard must never wedge a turn. An error while consulting the receipt store, a transcript that cannot
be read, and an `agent_id` that is not a plain name or matches in two workflows all fail CLOSED: they
count as no evidence and the edit is blocked, because evidence that cannot be read must not disarm
the guard.
Pure standard library; launched via run-python.sh so it works on Windows too.
"""
import hashlib
import json
import os
import posixpath
import re
import shlex
import sys
from pathlib import Path

import shell_text
import splice_span
from transcript_siblings import agent_transcript

# IGNORECASE because macOS and Windows filesystems are case-insensitive: there `Skills/x/skill.md`
# opens the real SKILL.md, and the guard cannot tell from a path string which filesystem it names.
_SKILL_MD = re.compile(r"(?:^|/)skills/[^/]+/SKILL\.md$", re.IGNORECASE)
_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
_BYPASS_ENV = "BITRANOX_SKILL_WRITER"
_SKILL = "meta-skill-writer"
_LOAD_PREFIX = "Base directory for this skill:"


def _agent_transcript(event):
    """The editing agent's own transcript path, or None when it cannot be named safely."""
    main = event.get("transcript_path")
    if not main:
        return None
    if "agent_id" not in event or event["agent_id"] is None:
        return Path(main)
    return agent_transcript(main, event["agent_id"])


def _texts(record):
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b.get("text") or "" for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return []


def _is_load_of(record, skill):
    if not isinstance(record, dict) or record.get("type") != "user" or record.get("isMeta") is not True:
        return False
    for text in _texts(record):
        if not text.startswith(_LOAD_PREFIX):
            continue
        skill_dir = text[len(_LOAD_PREFIX):].split("\n", 1)[0].strip().replace("\\", "/").rstrip("/")
        if skill_dir.rsplit("/", 1)[-1] == skill:
            return True
    return False


def skill_loaded(transcript, skill=_SKILL):
    """Whether `transcript` records the harness loading `skill`. Raises OSError when unreadable."""
    with open(transcript, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            # Cheap prefilter first: a transcript runs to many MB and almost no line is a load.
            if skill not in line or _LOAD_PREFIX not in line:
                continue
            try:
                record = json.loads(line)
            except (ValueError, RecursionError):
                # A torn line is not evidence, nor one nested past the decoder's depth: escaping,
                # that RecursionError would reach main's catch-all and ALLOW the edit.
                continue
            if _is_load_of(record, skill):
                return True
    return False


def _receipt_fresh(event):
    try:
        import skill_receipt
        # The EVENT's session id, so the receipt must belong to THIS session. Without it the
        # check answered "somebody on this machine started the procedure recently" - a different
        # claim, and routinely true on a machine running several sessions at once.
        return bool(skill_receipt.is_fresh(_SKILL, session_id=event.get("session_id")))
    except Exception:  # noqa: BLE001 - a broken receipt store must not wedge; count it as no receipt
        return False


def _loaded_by_editing_agent(event):
    transcript = _agent_transcript(event)
    if transcript is None:
        return False
    try:
        return skill_loaded(transcript)
    except OSError:
        return False                                   # unreadable evidence is no evidence


_BRIEF_FLAG = ".skill-decisions-brief-"
_BRIEF = ("Before this first edit of skills/%s, read what was already decided for it. Each entry "
          "below was taken for the reason given; re-proposing one needs that reason answered, in a "
          "new ledger entry that supersedes it.\n\n%s\n\n%sNow re-send the edit, revised "
          "or unchanged; the re-send is not refused.")
_FULL_LIST = "Every field of every entry, runnable from any directory:\n%s\n\n"
_SHOW_SCRIPT = Path(__file__).resolve().parent / "skill_decisions.py"


def show_command(skill_dir):
    """The shell command printing `skill_dir`'s declined decisions in full, runnable from any cwd.

    It names this install's own script and the skill's own dir, because `show <name>` alone
    looks the name up in the cwd's repo: from a tool-repo twin, or any `skills/x/SKILL.md`
    outside the marketplace, that is a different ledger or none. The interpreter is the one
    running this hook (run-python.sh found it), since a bare `python3` is a Store stub on Windows.
    """
    skill_dir = Path(skill_dir)
    return "%s %s show %s --skill-dir %s --kind rejected,removed --full" % (
        shlex.quote(sys.executable or "python3"), shlex.quote(str(_SHOW_SCRIPT)),
        shlex.quote(skill_dir.name), shlex.quote(str(skill_dir)))


def _bash_commands(record):
    # Every level type-checked: a transcript line is data, and one odd shape raising here would
    # end the whole decision rather than this one line.
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    for block in content if isinstance(content, list) else []:
        if not (isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Bash"):
            continue
        tool_input = block.get("input")
        if isinstance(tool_input, dict):
            yield str(tool_input.get("command") or "")


def _show_pattern(skill):
    # The name as typed or as show_command quotes it, so the emitted command itself is credited.
    # The lookahead keeps `show foo` from counting for `show foo-bar`: skill names hold hyphens.
    # IGNORECASE as in _SKILL_MD (the edited path may spell the name in another case); DOTALL
    # because one Bash command may span lines.
    names = sorted({re.escape(skill), re.escape(shlex.quote(skill))})
    return re.compile(r"skill_decisions\.py\b.*\bshow\s+(?:%s)(?![\w-])" % "|".join(names),
                      re.IGNORECASE | re.DOTALL)


def ran_show(transcript, skill):
    """True when `transcript` holds a Bash call of `skill_decisions.py show <skill>`. Raises OSError."""
    wanted = _show_pattern(skill)
    with Path(transcript).open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "skill_decisions" not in line:
                continue                               # cheap prefilter, as in skill_loaded
            try:
                record = json.loads(line)
            except (ValueError, RecursionError):
                continue                               # torn, or nested past the decoder's depth
            if isinstance(record, dict) and any(wanted.search(c) for c in _bash_commands(record)):
                return True
    return False


def _refuse_once(session, agent, skill):
    """True the first time for (session, agent, skill), recording it; False after, or if unstorable."""
    try:
        from self_improve_signals import session_state_path  # noqa: PLC0415 - optional state store
        key = hashlib.sha1(("%s/%s" % (agent, skill)).encode("utf-8")).hexdigest()[:16]
        flag = session_state_path(session, _BRIEF_FLAG + key)
        if flag.exists():
            return False
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("refused\n", encoding="utf-8")
        return True
    except Exception:  # noqa: BLE001 - a flag that cannot be stored lets the edit through
        return False


_TWIN_LABEL = "%s (a tool-repo twin; its decisions are kept with the marketplace copy, %s)"


def _marketplace_skill_roots(skill_dir):
    """Where the marketplace's skills dirs may be, freshest first: the checkout under the shared
    `public/` tree holding ``skill_dir`` (where new ledger entries land), then this install's own
    skills dir (the plugin ships each `.skillwriter/` ledger, so it is there off this machine too)."""
    roots = [parent / "KI" / "bitranox-skills" / "plugins" / "bitranox" / "skills"
             for parent in Path(skill_dir).resolve().parents if parent.name == "public"][:1]
    return roots + [Path(__file__).resolve().parent.parent / "skills"]


def ledger_dir(skill_dir, ledger_path, owner=None):
    """The skill dir whose decision ledger governs an edit of ``skill_dir``.

    ``skill_dir`` itself when it holds a ledger. A tool repo's twin holds none - the mirror
    leaves `.skillwriter/` out, the marketplace copy owns it - so for a twin it is the marketplace
    copy that has one (`_marketplace_skill_roots`); without this its rejected and removed entries
    reached nobody editing the twin. ``ledger_path`` maps a skill dir to its ledger file;
    ``owner`` maps a dir to the marketplace skill it mirrors (default `mirrored_skills`).
    """
    skill_dir = Path(skill_dir)
    if ledger_path(skill_dir).is_file():
        return skill_dir
    if owner is None:
        import mirrored_skills  # noqa: PLC0415 - a missing module must not wedge the guard
        owner = mirrored_skills.marketplace_name
    name = owner(skill_dir)
    if name is None:
        return skill_dir
    for root in _marketplace_skill_roots(skill_dir):
        if ledger_path(root / name).is_file():
            return root / name
    return skill_dir


def _brief_refusal(event, path):
    """The decisions-brief refusal owed before this agent's first edit of the skill, or None."""
    session = event.get("session_id")
    if not isinstance(session, str) or not session.strip():
        return None
    edited = Path(path).parent
    try:
        import skill_decisions  # noqa: PLC0415 - a missing module must not wedge the guard
        skill_dir = ledger_dir(edited, skill_decisions.ledger_path)
        command = show_command(skill_dir)
        ledger = skill_decisions.ledger_path(skill_dir)
        brief = skill_decisions.render_brief(lambda: skill_decisions.file_lines(ledger),
                                             skill=skill_dir.name, show_command=command)
    except Exception:  # noqa: BLE001 - ledger integrity is the commit gate's job, not this guard's
        return None
    if not brief:
        return None
    transcript = _agent_transcript(event)
    try:
        if transcript is not None and ran_show(transcript, skill_dir.name):
            return None
    except OSError:
        pass                                           # unreadable: one refusal costs one re-send
    if not _refuse_once(session, event.get("agent_id") or "main", skill_dir.name):
        return None
    # When entries were left out, the brief's own trailer already names the command; say it once.
    full_list = "" if command in brief else _FULL_LIST % command
    label = edited.name if skill_dir == edited else _TWIN_LABEL % (edited.name, skill_dir.name)
    return _BRIEF % (label, brief, full_list)


_SKILL_PATH = r"""(?:[^\s'"<>|;&]*/)?skills/[^/\s'"]+/SKILL\.md"""
_REDIRECT_INTO = re.compile(r""">>?\s*['"]?(%s)""" % _SKILL_PATH, re.IGNORECASE)
_NAMES_SKILL_LITERAL = re.compile(r"""SKILL\.md['"]""")
_PY_WRITE = re.compile(r"""\bwrite_text\(|\bwrite_bytes\(|\.write\(|\bopen\([^)\n]*['"][wa]b?\+?['"]""")
_FILE_WRITERS = ("sed", "gsed", "tee", "cp", "mv", "install", "dd")


def _argv_writes_skill(tokens):
    """The SKILL.md path this argv writes, when it is sed -i, tee, or a copy/move onto one."""
    program = shell_text.basename_for_tool(tokens[0], "Bash")
    if program not in _FILE_WRITERS:
        return None
    if program in ("sed", "gsed") and not any(t.startswith("-i") or t == "--in-place" for t in tokens):
        return None
    candidates = [t for t in tokens[1:] if _SKILL_MD.search(t.replace("\\", "/"))]
    if program == "tee":
        return candidates[0] if candidates else None
    if program in ("cp", "mv", "install", "dd"):
        last = tokens[-1].replace("\\", "/")
        return tokens[-1] if _SKILL_MD.search(last) else None
    return candidates[0] if candidates else None


def python_skill_write(command):
    """True when a Python program this Bash `command` runs names a SKILL.md and calls a write."""
    if not isinstance(command, str) or "skill.md" not in command.lower():
        return False
    return any(_NAMES_SKILL_LITERAL.search(program) and _PY_WRITE.search(program)
               for program in splice_span.programs_run_by(command))


def bash_skill_write(command):
    """The SKILL.md a Bash `command` writes through a shell shape, or None. PURE.

    Examples:
        >>> bash_skill_write("sed -i 's/a/b/' plugins/x/skills/foo/SKILL.md")
        'plugins/x/skills/foo/SKILL.md'
        >>> bash_skill_write("grep -n TODO plugins/x/skills/foo/SKILL.md") is None
        True
    """
    if not isinstance(command, str) or "skill.md" not in command.lower():
        return None
    text = shell_text.strip_heredoc_bodies(command)
    for _at, segment in shell_text.iter_segments(text, "Bash"):
        redirect = _REDIRECT_INTO.search(segment)
        if redirect:
            return redirect.group(1)
        tokens = shell_text.argv_for_match(segment.strip(), "Bash")
        target = _argv_writes_skill(tokens) if tokens else None
        if target:
            return target
    return None


def _decide_bash(event, env):
    target = bash_skill_write((event.get("tool_input") or {}).get("command"))
    if target is None or env.get(_BYPASS_ENV):
        return None
    if _receipt_fresh(event) and _loaded_by_editing_agent(event):
        return None
    return ("Writing a SKILL.md through Bash is blocked for the same reason as the Edit tool: skills "
            "change ONLY through bitranox:meta-skill-writer (RED-GREEN-REFACTOR + its checklist). "
            "Invoke that skill via the Skill tool in this agent first - its step 0 issues the "
            "session receipt this guard checks. Emergency bypass: relaunch with %s=1 set in the "
            "environment (a shell `export` in a Bash tool call does NOT reach this hook). "
            "File: %s" % (_BYPASS_ENV, target))


def python_nudge(event, env):
    """additionalContext for a Python program writing a SKILL.md, else None."""
    if event.get("tool_name") != "Bash" or env.get(_BYPASS_ENV):
        return None
    if not python_skill_write((event.get("tool_input") or {}).get("command")):
        return None
    if _receipt_fresh(event) and _loaded_by_editing_agent(event):
        return None
    return ("This Python program names a SKILL.md and writes a file. If it rewrites that SKILL.md, "
            "stop and do it through bitranox:meta-skill-writer: a SKILL.md changed outside it "
            "skips the RED-GREEN steps and the checklist the commit gate expects.")


def decide(event, env):
    """Pure: (event, env) -> a block-reason string (deny the tool call), or None to allow silently."""
    if (event.get("tool_name") or "") == "Bash":
        return _decide_bash(event, env)
    if (event.get("tool_name") or "") not in _TOOLS:
        return None
    # posixpath.normpath, not os.path: the separators are already forward slashes, and
    # os.path would put Windows ones back. Without collapsing "." and ".." first, the
    # tail-anchored regex missed .../skills/<name>/./SKILL.md - the same file, unguarded.
    # NotebookEdit names its target `notebook_path`; without the fallback that registration
    # could never produce a decision.
    tool_input = event.get("tool_input") or {}
    raw = (tool_input.get("file_path") or tool_input.get("notebook_path") or "").replace("\\", "/")
    path = posixpath.normpath(raw) if raw else raw
    if not _SKILL_MD.search(path):
        return None
    if env.get(_BYPASS_ENV):
        return None                                    # emergency bypass (env at session launch)
    receipt = _receipt_fresh(event)
    if receipt and _loaded_by_editing_agent(event):
        return _brief_refusal(event, path)             # None unless the decisions brief is owed
    if receipt:
        why = ("A meta-skill-writer receipt is armed, but THIS agent never loaded the skill: a receipt "
               "is shared by every agent in the session, so a subagent cannot ride its parent's. "
               "Invoke bitranox:meta-skill-writer via the Skill tool in this agent first.")
    else:
        why = ("Skills change ONLY through bitranox:meta-skill-writer (RED-GREEN-REFACTOR + its "
               "checklist); invoke that skill via the Skill tool - its step 0 issues the session "
               "receipt this guard checks.")
    return (
        "Editing a SKILL.md directly is blocked. %s Emergency bypass: relaunch with %s=1 set in the "
        "environment (a shell `export` in a Bash tool call does NOT reach this hook). "
        "File: %s" % (why, _BYPASS_ENV, path))


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    reason = decide(event, os.environ)
    if reason is not None:
        return shell_text.refuse("SKILL-EDIT GUARD: " + reason)
    nudge = python_nudge(event, os.environ)
    if nudge:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "additionalContext": nudge}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
