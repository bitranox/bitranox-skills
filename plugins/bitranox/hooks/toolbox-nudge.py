#!/usr/bin/env python3
"""PreToolUse(Bash|Write|Edit|MultiEdit) nudge: when a tool call looks like a hand-rolled chore
that the local toolbox already has a tested tool for, inject a non-blocking additionalContext
pointer ("use the jig") - once per tool per session. Silent if the toolbox (or the specific tool)
is not installed.

Why: the local toolbox only helps if the model remembers it BEFORE hand-rolling. A chore hides in
one of two places - a Bash one-liner (the command line) or a script authored via Write/Edit (the
file CONTENT). Scanning only Bash left a blind spot: writing the same logic into a .py file and
running it slipped past. So we scan the new text of Write/Edit/MultiEdit too, against the same
signatures. This catches the hand-roll at the moment it reaches for the raw materials and points at
the tool - the closest thing Claude Code offers to "a supervisor noticing and saying: we have a
tool for that". additionalContext reaches the model as a system-reminder (probe-verified), never
blocks.
"""
import json
import os
import re
import sys
from pathlib import Path

# Shared with the other command-scanning guards: a heredoc body is DATA, and scanning it makes a
# guard fire on prose that merely mentions the chore it watches for. Re-exported so callers and
# tests can keep reaching it as `toolbox_nudge.strip_heredoc_bodies`.
from shell_text import blank_unexpanded_text, is_shell_tool, strip_heredoc_bodies  # noqa: F401

# (regex over the command, tool name, one-line "why"). First match wins. STRONG signatures only, to
# keep false positives + noise low; the per-session dedup then nudges each tool at most once.
_RULES = [
    (re.compile(r"<{7}|>{7}"), "conflict_scan", "scanning for git conflict markers"),
    (re.compile(r"\.jsonl\b.*(?:json\.loads|json\.load|for line in)"
                r"|(?:json\.loads|json\.load).*\.jsonl", re.S), "jsonl_grep",
     "parsing a JSONL transcript by hand"),
    # Names the SHIPPED tool, not the local `sshf.py` twin it was contributed from: the gate
    # below sweeps shipped scripts, so a rule naming only the local name left `fleet_ssh`
    # reading as unrouted forever, and anyone without that local file got silence.
    (re.compile(r"\bssh\b[^|]*(?:StrictHostKeyChecking|anyhost_nopass|BatchMode=)"), "fleet_ssh",
     "building an ssh fleet one-liner"),
    (re.compile(r"(?:cargo (?:build|test|clippy)|gh run (?:view|watch))\b.*(?:\|\s*(?:grep|sed|awk)|2>&1)",
                re.S), "ci_triage", "hand-piping a build/CI log for errors"),
    (re.compile(r"for\b.*\bgit -C\b.*\bstatus\b|git rev-parse --abbrev-ref HEAD"), "git_state",
     "checking git branch/status across repo(s)"),
    (re.compile(r"\b(?:pkill|pgrep)\s+[^\n]*-f\b"), "procsig",
     "hand-rolling pgrep/pkill -f (self-match risk)"),
    (re.compile(r"\bip\s+neigh\b|getent\s+hosts\s+OVM-|tcpdump[^\n]*\btap"), "guestip",
     "resolving a guest IP by hand"),
    (re.compile(r"/var/log/openvmm/"), "ovmlog", "reading an openvmm per-VM log by hand"),
    # LAST, so a more specific rule above keeps its own shape. A `grep` carrying -c/-l/-L is being
    # asked "is this THERE?", and its NEGATIVE answer is the one that cannot be trusted: `grep -c`
    # exits 1 on zero and prints file:count under -r, `-l` prints nothing for both "absent" and
    # "never looked". Each of those produced a confident false ABSENT in one session. The pipe and
    # semicolon exclusions keep the flag search inside this command, so `... | wc -l` is not read as
    # grep's own flag.
    (re.compile(r"\bgrep\b[^\n|;&]*?\s-[A-Za-z]*[clL]"), "claim_check",
     "deciding whether text is PRESENT from a raw grep count/list, whose negative cannot be trusted"),
]

# Rules for the tools that shipped without one. Kept in a second list so the measured, long-lived
# rules above are not reshuffled by an addition, and appended AFTER them so none of those loses its
# own shape. Every pattern here was priced over a frozen corpus of 79,052 authored calls from 493
# sessions and adjudicated against the calls it fires on - a match count cannot say whether a rule
# is right, because every hit matches by construction. The bar is the shipped `claim_check` rule,
# which already speaks in 57.6% of sessions: what disqualifies a rule is PRECISION, not volume
# (`newest` fired 2,591 times and none of the sampled firings was a which-is-latest question, so
# it ships narrowed to the sort-by-name shape that actually goes wrong).
#
# ORDER IS BEHAVIOUR: first match wins. `pushcheck` precedes `gate` because publishing something
# private outranks a masked exit status, and `ci_wait` precedes `backstop` because a CI poll loop
# carries both shapes and only one of them answers the question being asked.
#
# SHELL-ONLY is this LIST, not a field on the rule: every entry here describes a command being
# RUN, so the same words inside an authored file are a script being written rather than the chore
# itself. Unscoped, `git push` sitting in a Write body was the dominant firing of the pushcheck
# rule. A chore that is equally real when authored belongs in `_ANY_TOOL_RULES` below.
_SHELL_ONLY_RULES = [
    (re.compile(r"(?:^|[;&|]\s*|\bdo\s+|&&\s*)git\s+push\b|\bmake\s+push\b|\bgh\s+pr\s+create\b"),
     "pushcheck", "about to push - whether this repo is public, and what the push would publish"),
    (re.compile(r"\bgh\s+run\s+(?:watch|list|view)\b|\bgh\s+pr\s+checks\b"), "ci_wait",
     "waiting on CI for the commit you just pushed"),
    (re.compile(r"\bsleep\s+\d{2,}\b|\bnohup\b|\bsetsid\b"), "backstop",
     "a long job with a hand-rolled wait loop that cannot tell hung from finished"),
    # Before anchor_edit, which claims every `sed -i`: measured, all 23 firings of this shape were
    # swallowed by that broader rule, so listed after it this one would be dead on arrival.
    (re.compile(r"\bsed\s+-i[^\n]*s/[A-Za-z_][A-Za-z0-9_]{3,}/"), "renamescope",
     "renaming an identifier across a file, without knowing which functions the hits land in"),
    (re.compile(r"\bsed\s+-i\b"), "anchor_edit",
     "editing a file in place, where a computed span or a double-apply goes wrong silently"),
    (re.compile(r"\bfind\b[^|\n]*-name[^|\n]*\|\s*wc\s+-l"), "srccount",
     "counting a codebase's source files, where the exclusion list is what goes wrong"),
    (re.compile(r"\bls\b[^|\n]*\|\s*sort\b[^|\n]*\|\s*(?:tail|head)\b"
                r"|\bls\b[^|\n]*\|\s*(?:tail|head)\s+-n?\s*1\b"), "newest",
     "picking the latest by NAME, where a longer name sharing the prefix sorts after a newer one"),
    (re.compile(r"\biconv\b|\bstrings\s+-e\b"), "winlog",
     "reading a Windows log whose encoding grep cannot search"),
    (re.compile(r"--limit-rate\b|--bwlimit\b"), "transfer",
     "a rate-capped transfer whose unit means something different per tool"),
    (re.compile(r"\bgit\s+worktree\s+(?:remove|prune)\b|\bdu\b[^|\n]*\|\s*sort\s+-[a-z]*h"),
     "wtclean", "reclaiming the disk a deleted worktree never gave back"),
    (re.compile(r"\bgit\s+stash\b[^\n]*&&[^\n]*pytest|pytest[^\n]*&&[^\n]*git\s+checkout\s+--"),
     "mutation_arm", "proving a test is not vacuous by breaking the code under it"),
    # LAST of the shell-only rules: its shape is broad (5.2% of calls), so every more specific
    # rule above keeps its own. Adjudicated 8 of 8 - each firing really did read a filter's exit
    # status instead of the gate's.
    (re.compile(r"(?:make\s+(?:test|push|release)|pytest|ruff\s+check|pyright)\b[^\n;]*"
                r"(?:\|\s*(?:grep|tail|head)|&&)"), "gate",
     "running a gate then acting on the result, where the pipe's exit status is not the gate's"),
]

# Chores that are just as real when AUTHORED into a file as when typed, so these are not
# shell-only: a script walking the transcript corpus or the memory levels by hand is exactly the
# hand-roll the tool replaces.
_ANY_TOOL_RULES = [
    (re.compile(r"\.claude/projects\b"), "transcript_index",
     "walking past Claude Code transcripts by hand"),
    (re.compile(r"(?:grep|find|glob|rglob)[^\n]*CLAUDE\.local\.md"
                r"|CLAUDE\.local\.md[^\n]*\bmem:"), "mem_levels",
     "walking the curated memory levels with a hand-rolled mem: regex"),
    # LOCAL tools. Their rules ship here like `guestip` and `ovmlog` already do: the resolver
    # falls back to silence for anyone without the file, and the alternative - keeping the rule
    # only on the machine that has the tool - is a rule nobody can review. statusrot in
    # particular was hand-rolled twice in sessions where it existed and nothing named it.
    (re.compile(r"\.claude-memory[^\n]*(?:shipped|deployed|TODO|not started)"
                r"|(?:shipped|deployed)[^\n]*\.claude-memory"), "statusrot",
     "sweeping the fact store for status claims that shipped and were never updated"),
    (re.compile(r"\.claude-memory/facts/[^\n]*\.md"), "factedit",
     "editing a memory fact by hand - which level owns the slug, and is the hook under the cap"),
    (re.compile(r"\bfold\s+-[sw]|textwrap\.(?:fill|wrap)"), "mdwrap",
     "reflowing one markdown paragraph without touching the rest of the file"),
    (re.compile(r"\bfind\b[^\n]*-name\s+['\"]?CLAUDE\.md"
                r"|\bgrep\s+-[A-Za-z]*r[A-Za-z]*\b[^\n]*CLAUDE\.md"), "claudemd_variance",
     "finding duplicated CLAUDE.md sections by hand"),
]


#: Shipped tools that deliberately carry NO rule, mapped to (reason, evidence). The repo gate
#: reads this map, so an omission cannot pass as a decision: adding a tool with neither a rule nor
#: an entry here FAILS the gate. That is the whole point - five tools shipped unrouted while every
#: gate stayed green, because the description lint beside it only ever looked at CHANGED files.
#:
#: BOTH fields are required, and the gate rejects an entry missing either. An exemption is the
#: lazy path out of writing a rule, so it has to cost something: `evidence` states what was
#: actually TRIED - the candidate pattern and what it measured, or that no shape exists and why
#: the chore cannot appear on a command line. A reason alone is an opinion, and a gate satisfied
#: by an opinion is advice.
#:
#: Two kinds of reason appear below and they are different. "No command shape" means the chore is
#: a QUESTION someone asks, not a command they type. "Costs more than the channel carries" means a
#: shape exists and was measured too broad to ship.
NO_COMMAND_SHAPE = {
    "grep_all": (
        "an ordinary `grep -r` is most of a session's searching, and no part of the command says "
        "whether THIS one must be complete. `claim_check` already claims the -c/-l variant, where "
        "the negative answer is the untrustworthy one.",
        "candidate `grep -[A-Za-z]*r` measured 5,592 matches in 342 of 493 sessions (69%), above "
        "what any shipped rule costs - the highest being claim_check at 57.6%."),
    "transcript_tail": (
        "its chore sits inside the `transcript_index` rule's shape (both touch ~/.claude/projects) "
        "and the two differ by INTENT - search a corpus versus read one session.",
        "no candidate separates them: the intent is not on the command line, so any pattern that "
        "catches this one also catches every transcript_index call and would shadow it."),
    "enforced": (
        "the chore is 'does any code DECIDE on this setting, or is it only parsed?' - a question "
        "asked while reading.",
        "no shape exists: the chore is triggered by reading a config field, which produces no "
        "command of its own, and the grep that follows is indistinguishable from any other."),
    "confound": (
        "the chore is 'can this A/B table attribute the difference at all?' - asked of a results "
        "table, not typed as a command.",
        "no shape exists: the trigger is a results table already in context, and nothing is run "
        "at the moment the question arises."),
    "diffbehave": (
        "the chore is 'do old and new BEHAVE the same?'",
        "the hand-rolled form is an ad-hoc loop with no stable shape - candidates keyed on a "
        "for-loop plus a diff matched ordinary scripted work, and the deliberate form is already "
        "this tool being run."),
    "adjudicate": (
        "the chore is confirming a claim ABOUT a guard, which is reasoning over a result.",
        "no shape exists: the input is a firing already observed, so the person is reading output "
        "rather than authoring a command."),
    "guard_replay": (
        "the chore is shipping a hook on the strength of its unit tests - a decision, not a "
        "command.",
        "the nearest shape, editing a file under hooks/, is invisible here: the nudge scans a "
        "Write's CONTENT and never its file_path, so the path carrying the signal never reaches "
        "the matcher."),
}


def ruled_tools():
    """Every tool name any rule can name. The gate's source of truth, so it cannot drift."""
    return {tool for _rx, tool, _why in _RULES + _SHELL_ONLY_RULES + _ANY_TOOL_RULES}


def match_tool(command, tool_name=None):
    """(tool, why) for the first rule matching `command`, else None. PURE - unit-testable.

    `tool_name` decides whether the shell-only rules apply. It defaults to None meaning "treat
    this as a command", which is what every caller before the scope existed meant - so a rule
    that must not fire on authored text has to be listed as shell-only AND be given the real
    tool name by its caller.
    """
    scanning_a_command = tool_name is None or is_shell_tool(tool_name)
    ordered = _RULES + (_SHELL_ONLY_RULES if scanning_a_command else []) + _ANY_TOOL_RULES
    for rx, tool, why in ordered:
        if rx.search(command or ""):
            return tool, why
    return None


# Tools whose call we scan, and WHERE each hides the chore. Bash puts it on the command line;
# Write/Edit/MultiEdit put it in the NEW text being written (never old_string - that is what is
# being removed, not authored). Anything else (Read, Grep, ...) is not a place a chore is authored.
_SCANNED_TOOLS = ("Bash", "PowerShell", "Write", "Edit", "MultiEdit")


def extract_text(tool_name, tool_input):
    """The text to scan for a hand-rolled chore, per tool. PURE - unit-testable.

    Returns None for a tool we do not scan, so `match_tool(None)` short-circuits to no nudge.
    """
    ti = tool_input or {}
    if is_shell_tool(tool_name):
        # Only the command LINES are a chore being hand-rolled. A heredoc body is content being
        # written, so scanning it nudges about prose that merely names the tool - which is how
        # documenting a footgun trips the guard that watches for it.
        # blank_unexpanded_text too: a single-quoted commit message DESCRIBING a trap is not
        # an instance of it, and nudging there blocks the writing of the guidance itself.
        return blank_unexpanded_text(strip_heredoc_bodies(ti.get("command", "")))
    if tool_name == "Write":
        return ti.get("content", "")
    if tool_name == "Edit":
        return ti.get("new_string", "")
    if tool_name == "MultiEdit":
        return "\n".join(e.get("new_string", "") for e in ti.get("edits", []) if isinstance(e, dict))
    return None


def _toolbox_dir():
    """The local toolbox tools dir (resolved at call time so HOME can be overridden in tests)."""
    return Path(os.path.expanduser("~")) / ".claude" / "skills" / "toolbox" / "tools"


def _shipped_dir():
    """The compuse-toolbox scripts dir INSIDE THIS PLUGIN, resolved relative to this hook.

    Relative, so it names whichever plugin version is actually running - a path with a version in
    it would rot at the next update, and the installed cache dir for the old version is pruned."""
    return Path(__file__).resolve().parent.parent / "skills" / "compuse-toolbox" / "scripts"


def _sibling_skill_script(tool):
    """The tool's path under ANY shipped skill's `scripts/`, or None. Owner-agnostic on purpose.

    compuse-toolbox's own table documents tools that live in a sibling skill - `wtclean` under
    git-worktrees, `claudemd_variance` under meta-consolidate-claude-md, `redcheck` under
    process-test-driven-development. Resolving only against compuse-toolbox made a rule naming
    any of them silent, which is indistinguishable from having no rule at all; and a tool that
    MOVES between skills would go quiet the same way, with nothing reporting it."""
    skills = _shipped_dir().parent.parent
    # BOTH layouts, because the catalogue uses both: compuse-toolbox keeps its tools in `scripts/`
    # while meta-dream-tree keeps them at the skill root beside SKILL.md. Globbing only the first
    # made a rule for a root-level tool resolve nowhere, which is silence - and silence is exactly
    # what having no rule looks like, so nothing would have reported it.
    try:
        matches = sorted(skills.glob("*/scripts/%s.py" % tool)) or sorted(
            skills.glob("*/%s.py" % tool))
    except OSError:
        return None
    return matches[0] if matches else None


def _tool_invocation(tool):
    """How to run `tool`: the local copy if there is one, else the shipped one, else None.

    A tool broadly useful enough to be contributed upstream gets DELETED locally (one source of
    truth), and those are precisely the ones most worth nudging about - so keying the nudge on the
    local file alone would turn every successful contribution into a silently lost guard."""
    if (_toolbox_dir() / (tool + ".py")).is_file():
        return "the local `toolbox` skill", "uv run ~/.claude/skills/toolbox/tools/%s.py --help" % tool
    if (_shipped_dir() / (tool + ".py")).is_file():
        return ("the shipped `bitranox:compuse-toolbox` skill",
                "uv run %s/%s.py --help" % (_shipped_dir(), tool))
    sibling = _sibling_skill_script(tool)
    if sibling is not None:
        # Name the skill that actually owns it: pointing a reader at compuse-toolbox for a tool
        # that lives elsewhere sends them to a directory the file is not in. The owner is the
        # component directly under `skills/`, never `parent.parent` - that is the skill only for
        # the scripts/ layout and resolves to `skills` itself for a tool kept at the skill root.
        owner = sibling.relative_to(_shipped_dir().parent.parent).parts[0]
        return ("the shipped `bitranox:%s` skill" % owner, "uv run %s --help" % sibling)
    return None


def _nudge_flag(session):
    """Where this session's already-nudged tool list lives - a named helper so the path is testable
    rather than built inline, and so the id passes through the shared confinement on the way."""
    from self_improve_signals import session_state_path   # noqa: PLC0415 - shared, confines the id
    return session_state_path(session, ".toolbox-nudged")


def _already_nudged(session, tool):
    """Per-session dedup: True if `tool` was already nudged this session; else record it. Best-effort."""
    if not session:
        return False
    try:
        f = _nudge_flag(session)
        seen = set(f.read_text(encoding="utf-8").split()) if f.exists() else set()
        if tool in seen:
            return True
        seen.add(tool)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(" ".join(sorted(seen)) + "\n", encoding="utf-8")
        return False
    except Exception:                                    # noqa: BLE001 - dedup must never break the hook
        return False


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                    # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or event.get("tool_name") not in _SCANNED_TOOLS:
        return 0
    text = extract_text(event.get("tool_name"), event.get("tool_input") or {})
    hit = match_tool(text, event.get("tool_name"))
    if not hit:
        return 0
    tool, why = hit
    found = _tool_invocation(tool)
    if not found:                                        # nowhere local, nowhere shipped -> silent
        return 0
    home, invoke = found
    if _already_nudged(event.get("session_id") or "", tool):
        return 0
    msg = ("%s has a tested tool for this (%s): `%s`. Prefer it over hand-rolling; if it "
           "falls short, ENHANCE it (propose-first, per bitranox:meta-self-improve) rather than "
           "working around it." % (home.capitalize() if home.startswith("the") else home, why, invoke))
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": msg}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
