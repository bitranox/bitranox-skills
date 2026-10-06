#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit) nudge: when a tool call looks like a hand-rolled chore
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
import ast
import json
import os
import re
import sys
from pathlib import Path

# Shared with the other command-scanning guards: a heredoc body is DATA, and scanning it makes a
# guard fire on prose that merely mentions the chore it watches for. Re-exported so callers and
# tests can keep reaching it as `toolbox_nudge.strip_heredoc_bodies`.
from shell_text import (  # noqa: F401
    blank_unexpanded_text, heredoc_bodies, is_shell_tool, strip_heredoc_bodies,
)

# How far apart the two halves of a two-part rule may sit. These rules also scan AUTHORED text (a
# Write body, an Edit), so an unbounded `.*` under re.S joined a `cargo build` on line 1 to a
# `| grep` 200 lines later. A PIPELINE lives on one logical line - a backslash continuation joins
# lines, nothing else does. A hand-rolled JSONL READER is a few lines of script, so it gets a window
# of about twenty lines: replayed over the recorded Write/Edit bodies, 800 characters kept 185 of
# 220 firings, and the ones it dropped were mostly a `.jsonl` mention kilobytes away from a
# `json.loads` of some other file.
_ONE_LOGICAL_LINE = r"(?:[^\n\\]|\\.|\\\n)*"
_SCRIPT_WINDOW = r".{0,800}"


def _names_referenced(text, names):
    """True when `text` expands any of `names` as `$name` or `${name}`."""
    return bool(names) and re.search(
        r"\$\{?(?:" + "|".join(map(re.escape, sorted(names))) + r")\b", text) is not None


# Named because `_RepoSweep` defers to them as well as listing them as rules. A push is a
# STATEMENT, so it is anchored to where a statement starts: a line start (multi-line, since a
# command is often several lines) or a separator, then any run of the words that open a statement
# without being one - `if`, `then`, `elif`, `else`, `do`, `while`, `until`, `!`, a subshell `(` or
# a group `{`. Each keyword must itself follow the anchor, so `echo if git push` stays prose; a
# push under `if` (a loop pushing each repo only when its check passes) was un-nudged while the
# anchor took `do` alone. Environment prefixes (`LC_ALL=C`, `env -u X`) and git's own global
# options (`git -C <repo> -c k=v`) may sit between that anchor and `push`. Measured over 79,213
# recorded calls: a push on a later line or behind one of those prefixes was about 30 un-nudged
# pushes. Quoted option values reach this pattern blanked to spaces, hence the quoted alternatives.
_PUSHCHECK_RX = re.compile(r"(?m)(?:^|[;&|])\s*"
                           r"(?:(?:if|then|elif|else|do|while|until|!)\s+|[({]\s*)*"
                           r"(?:(?:[A-Za-z_]\w*=\S*|env(?:\s+-u\s+\w+)*)\s+)*"
                           r"git(?:\s+-[Cc]\s+(?:[^\s'\"]|'[^']*'|\"[^\"]*\")+)*\s+push\b"
                           r"|\bmake\s+push\b|\bgh\s+pr\s+create\b")
_CI_WAIT_RX = re.compile(r"\bgh\s+run\s+(?:watch|list|view)\b|\bgh\s+pr\s+checks\b")


class _RepoSweep:
    """A loop over REPOS asking each one for its state - git_state's chore.

    Recognised by the loop variable being the `git -C` target, not by the subcommand: the same
    sweep asks for the branch or the ahead/behind count as often as for `status`, while a loop
    over commits or files inside ONE repo uses `git -C` too and is not the chore. The target is
    usually DERIVED first (`d=/srv/$r; git -C $d status`), so a variable assigned from a loop
    variable counts as one. Only the questions git_state answers count - branch, sync, dirty -
    which leaves out history (`log -p`), remotes and "which repo is this" (`rev-parse
    --show-toplevel`); `log` counts only over an upstream range.

    A sweep that also pushes or waits on CI is left to that rule: the push or the CI result is
    the question it has to answer. That is decided here rather than by list order because this
    rule must still outrank `claim_check`, which sits in the same list - replayed, real sweeps
    carrying an incidental `grep -c` were otherwise handed to it.

    Known wrong shape: the same sweep run on REMOTE hosts inside an ssh command string reads
    identically from here, and git_state cannot reach those repos. Replayed over the recorded
    Bash calls it was 3 of the firings; telling it apart needs the quoting, not a pattern.

    Regex-shaped on purpose: `match_tool` needs nothing but `.search(text)`.
    """

    _LOOP = re.compile(r"\bfor\s+([A-Za-z_]\w*)\s+in\b"
                       r"|\bwhile\s+(?:IFS=\S*\s+)?read\s+(?:-r\s+)?([A-Za-z_]\w*(?:[ \t]+[A-Za-z_]\w*)*)")
    _ASSIGN = re.compile(r"(?<![\w$-])([A-Za-z_]\w*)=(\"[^\"]*\"|'[^']*'|[^\s;&|]*)")
    _GIT_C = re.compile(r"\bgit\s+-C\s+(\"[^\"]*\"|'[^']*'|[^\s;&|]+)\s+(?:-c\s+\S+\s+)*"
                        r"([a-z][a-z-]*)([^\n;&|]*)")
    _STATE = frozenset({"status", "rev-parse", "rev-list", "branch", "symbolic-ref"})
    # A range joins two revisions with no space, so a prose ellipsis (" ...") is not one.
    _UPSTREAM_RANGE = re.compile(r"@\{u(?:pstream)?\}|[\w}~^]\.{2,3}[\w@]")
    _REPO_IDENTITY = re.compile(r"--(?:show-toplevel|git-dir|absolute-git-dir|git-common-dir"
                                r"|is-inside-\w+|show-prefix|show-cdup)\b")

    def __init__(self, defer_to=()):
        self._defer_to = tuple(defer_to)

    def _loop_names(self, text):
        names = set()
        for single, many in self._LOOP.findall(text):
            names.update((single or many).split())
        grew = bool(names)
        while grew:
            before = len(names)
            names.update(name for name, value in self._ASSIGN.findall(text)
                         if _names_referenced(value, names))
            grew = len(names) > before
        return names

    def _asks_state(self, sub, rest):
        if sub == "log":
            return self._UPSTREAM_RANGE.search(rest) is not None
        if sub == "rev-parse":
            return self._REPO_IDENTITY.search(rest) is None
        return sub in self._STATE

    def search(self, text):
        if any(rx.search(text) for rx in self._defer_to):
            return None
        names = self._loop_names(text)
        if not names:
            return None
        for hit in self._GIT_C.finditer(text):
            target, sub, rest = hit.groups()
            if _names_referenced(target, names) and self._asks_state(sub, rest):
                return hit
        return None


# (regex over the command, tool name, one-line "why"). First match wins. STRONG signatures only, to
# keep false positives + noise low; the per-session dedup then nudges each tool at most once.
_RULES = [
    (re.compile(r"<{7}|>{7}"), "conflict_scan", "scanning for git conflict markers"),
    (re.compile(r"\.jsonl\b" + _SCRIPT_WINDOW + r"(?:json\.loads|json\.load|for line in)"
                r"|(?:json\.loads|json\.load)" + _SCRIPT_WINDOW + r"\.jsonl", re.S), "jsonl_grep",
     "parsing a JSONL transcript by hand"),
    # Names the SHIPPED tool, not the local `sshf.py` twin it was contributed from: the gate
    # below sweeps shipped scripts, so a rule naming only the local name left `fleet_ssh`
    # reading as unrouted forever, and anyone without that local file got silence.
    (re.compile(r"\bssh\b[^|]*(?:StrictHostKeyChecking|anyhost_nopass|BatchMode=)"), "fleet_ssh",
     "building an ssh fleet one-liner"),
    (re.compile(r"(?:cargo (?:build|test|clippy)|gh run (?:view|watch))\b" + _ONE_LOGICAL_LINE
                + r"(?:\|\s*(?:grep|sed|awk)|2>&1)"), "ci_triage",
     "hand-piping a build/CI log for errors"),
    (_RepoSweep(defer_to=(_PUSHCHECK_RX, _CI_WAIT_RX)), "git_state",
     "checking git branch/status across repo(s)"),
    (re.compile(r"git rev-parse --abbrev-ref HEAD"), "git_state",
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
    (_PUSHCHECK_RX, "pushcheck",
     "about to push - whether this repo is public, and what the push would publish"),
    (_CI_WAIT_RX, "ci_wait", "waiting on CI for the commit you just pushed"),
    # Three shapes of one chore. A long `sleep`, a detached job, and the two measured as missing:
    # a polling loop whose `sleep` sits inside its body however short (a poll sleeps 3-6 seconds a
    # turn - about 38 recorded calls), and a process-table check that reads "gone" as "finished"
    # (28 calls), which a crash satisfies just as well. The loop body stops at `done`, so a sleep
    # after the loop ended does not make it a poll.
    (re.compile(r"\bsleep\s+\d{2,}\b|\bnohup\b|\bsetsid\b"
                r"|(?s:\b(?:until|while)\b[^\n]*?(?:;|\n)\s*do\b(?:(?!\bdone\b).){0,400}?"
                r"\bsleep\s+\d)"
                r"|\bps\b[^\n|]*\|\s*grep\b[^\n]*\|\|\s*\{?\s*echo\s+[\"']?(?:FINISHED|DONE|finished|done)\b"),
     "backstop", "a long job with a hand-rolled wait loop that cannot tell hung from finished"),
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
    # A hand-rolled plan DRY-RUN: a driver that pulls a plan's python fences out with a regex or an
    # index() and then writes and checks them. The extraction call on a literal python fence is
    # the shape; a plan that merely CONTAINS python blocks is not. Priced over the transcript
    # corpus: 21 of 106,395 Bash calls (0.02%), 7 of 6,676 Write bodies and 1 of 10,267 Edit
    # fragments, and every firing read pulled python blocks out of a plan, a brief, a README or
    # a SKILL.md to run or check them. The broader candidate "a python fence, a check tool and a
    # .md in one text" was mostly plan documents being WRITTEN, which is not the chore. Listed
    # before the span rule, because such a driver usually also splices its blocks into a file.
    (re.compile(r"\b(?:findall|finditer|search|match|split|index|find|compile)\(\s*(?:rb?|f)?"
                r"[\"']{1,3}(?:`{3}|~{3})(?:python|py)\b"), "plan_codecheck",
     "extracting a plan's python blocks to prove them, where each hand-written driver carries the "
     "last one's quirks"),
    # The COMPUTED-SPAN spelling of anchor_edit's chore: two `.index()`/`.find()` anchors, then
    # `s[:a] + new + s[b:]` written back. It carries no `.replace(`, so the exact-text rule below
    # never saw it, and it is the costlier mistake - a wrong end anchor, or a `.find` that returned
    # -1, deletes a region silently and the file still parses. Every part of the shape is required
    # (two finds, a head slice glued with `+`, a tail slice, a write), so reading a span or prose
    # describing one is not a firing. Priced over the transcript corpus: the shape is in 471 of
    # 106,293 Bash calls (0.44%), this rule's reason is the one given on 262 (0.25%), and 122 of
    # those (0.11%) are calls the hook said nothing about before; 22 of 6,668 Write bodies (7 new)
    # and 1 of 10,258 Edit fragments. The new firings read, bucketed, were hand-rolled splices. Listed before the
    # exact-text rule so a script doing both gets the span reason. `\A` anchors the lookaheads,
    # as on the rule below: unanchored, `search` retries them at every offset and an 880 KB Write
    # cost minutes per call.
    (re.compile(r"(?s)\A(?=.*\.r?(?:index|find)\(.*\.r?(?:index|find)\()"
                r"(?=.*\b\w+\[\s*:[^\]\n]+\]\s*\+)"
                r"(?=.*\+\s*\w+\[[^\]\n:]+:\s*\])"
                r"(?=.*(?:write_text\(|\.write\())"), "anchor_edit",
     "splicing a file region between two found anchors (s[:a] + new + s[b:]), where a wrong end "
     "anchor or a find() of -1 deletes text silently - use its replace-span"),
    # The Python spelling of anchor_edit's chore. Its other rule is `sed -i`, and measured over 60
    # recorded calls this is how the chore is actually written - a read, an exact-text replace and
    # a write-back - usually inside a heredoc, where NO command rule can see it. Both CALL shapes
    # are required so that prose naming the trap ("read_text then write_text with a replace") is
    # not an instance of it.
    (re.compile(r"(?s)\A(?=.*\.replace\()(?=.*write_text\()"), "anchor_edit",
     "replacing a file region by exact text, where a computed span or a double-apply goes wrong "
     "silently"),
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
    "fanout_crosscheck": (
        "the chore is 'did an agent of this fan-out write into a sibling's target?', which arises "
        "when a fan-out FINISHES - an Agent result, not a command - so its channel is the "
        "Verification step of process-agents-dispatching-parallel.",
        "measured over 113,472 recorded Bash calls: candidate two-or-more `git -C <path> diff` in "
        "one command fires 8 times (0.007%), and the sampled firings are multi-repo status and "
        "--stat reviews, not a search for one target's name in another's added lines; the intent "
        "is not on the command line."),
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
    "corpus_prompts": (
        "the chore is pricing a PROMPT-side rule over real history - a decision taken while "
        "reading, and the walk it produces is the one `guard_replay` and `transcript_index` "
        "already make over the same corpus. What separates them is which records you want, "
        "which is intent and is not on the command line.",
        "measured over 84,968 recorded Bash calls: candidate `\\.claude/projects.*'user'` fires "
        "30 times (0.035%) and overlaps `jsonl_grep --type user`, which already claims that "
        "shape; candidate `rglob\\('\\*\\.jsonl` fires 56 times (0.066%) and is the shared corpus "
        "WALK, so it names guard_replay's chore as readily as this one; the path alone fires 824 "
        "times (0.970%) for every purpose at once."),
    "instrument_share": (
        "the chore is re-measuring how much session time the instrumentation takes - a question "
        "asked about the corpus, and the walk it produces is the one `transcript_index` already "
        "claims through `.claude/projects`, so the intent is not on the command line.",
        "measured over the transcript corpus: candidate `\\.claude/projects` plus an ISO-week "
        "computation (`isocalendar`, `%V`) fires 0 times in 106,324 Bash calls and once in 6,670 "
        "Write bodies, that one being this jig's own source; the path alone is transcript_index's "
        "rule and names every corpus walk at once."),
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


def match_authored(text):
    """(tool, why) for the first ANY-TOOL rule matching authored `text`, else None. PURE.

    Authored text is a program being written rather than a command being run, so only the rules
    marked real-when-authored apply - the same split that lets Write and Edit content be scanned
    without a shell-only rule firing on a document that merely quotes a command.
    """
    for rx, tool, why in _ANY_TOOL_RULES:
        if rx.search(text or ""):
            return tool, why
    return None


# Tools whose call we scan, and WHERE each hides the chore. Bash puts it on the command line;
# Write/Edit/MultiEdit put it in the NEW text being written (never old_string - that is what is
# being removed, not authored), and NotebookEdit in the new cell source. Anything else (Read,
# Grep, ...) is not a place a chore is authored. This list must cover every tool hooks.json
# registers the hook for, or a registered call is dropped before it is read.
_SCANNED_TOOLS = ("Bash", "PowerShell", "Write", "Edit", "MultiEdit", "NotebookEdit")


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
        # Under the event's own shell: PowerShell escapes with a backtick, not a backslash.
        return blank_unexpanded_text(strip_heredoc_bodies(ti.get("command", "")),
                                     tool_name=tool_name)
    if tool_name == "Write":
        return ti.get("content", "")
    if tool_name == "Edit":
        return ti.get("new_string", "")
    if tool_name == "MultiEdit":
        return "\n".join(e.get("new_string", "") for e in ti.get("edits", []) if isinstance(e, dict))
    if tool_name == "NotebookEdit":
        return ti.get("new_source", "")       # absent for a cell delete: nothing authored
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
    """(where it lives, its path, the path as shown) for `tool`: the local copy if there is one,
    else the shipped one, else None.

    A tool broadly useful enough to be contributed upstream gets DELETED locally (one source of
    truth), and those are precisely the ones most worth nudging about - so keying the nudge on the
    local file alone would turn every successful contribution into a silently lost guard."""
    local = _toolbox_dir() / (tool + ".py")
    if local.is_file():
        return "the local `toolbox` skill", local, "~/.claude/skills/toolbox/tools/%s.py" % tool
    shipped = _shipped_dir() / (tool + ".py")
    if shipped.is_file():
        return "the shipped `bitranox:compuse-toolbox` skill", shipped, "%s/%s.py" % (
            _shipped_dir(), tool)
    sibling = _sibling_skill_script(tool)
    if sibling is not None:
        # Name the skill that actually owns it: pointing a reader at compuse-toolbox for a tool
        # that lives elsewhere sends them to a directory the file is not in. The owner is the
        # component directly under `skills/`, never `parent.parent` - that is the skill only for
        # the scripts/ layout and resolves to `skills` itself for a tool kept at the skill root.
        owner = sibling.relative_to(_shipped_dir().parent.parent).parts[0]
        return "the shipped `bitranox:%s` skill" % owner, sibling, str(sibling)
    return None


#: How a tool asks to be LAUNCHED: a top-level `LAUNCH_WITH = "<key>"` in its own source, else
#: the launch its own docstring shows being used on the tool itself (see `documented_launch`),
#: both read here without importing it. Neither means "uv".
#:
#: The launch belongs to the tool, not to this hook: `uv run` gives a script an isolated
#: interpreter, which is right for almost every tool and wrong for two kinds. One whose work is
#: the project's pytest (mutation_arm): it falls back to ./.venv's python by itself, but run from
#: anywhere else, or in a project with no .venv, under `uv run` it has neither pytest nor the
#: project and every arm reads INCONCLUSIVE. One that runs a command the CALLER supplies (gate): `uv run` puts its build env
#: first on the PATH that command inherits, so a `python3 -m pytest` gate dies with `No module
#: named pytest` and reads RED - gate.py's docstring says so, and this hook suggested `uv run`
#: anyway because it read declarations only. A special case here would be forgotten by the next
#: such tool; a declaration, or a documented launch, travels with it.
#:
#: Each entry is (command template, note appended after the command).
LAUNCHERS = {
    "uv": ("uv run %s --help", ""),
    # `python` on Windows: there `python3` is usually the Microsoft Store stub, which exits
    # non-zero without running anything.
    "python3": (
        ("python" if os.name == "nt" else "python3") + " %s --help",
        (" - launch it with a plain interpreter, NOT `uv run`: it runs YOUR commands, and `uv run` "
         "puts its own isolated interpreter first on the PATH they inherit, so a child "
         "`python3 -m pytest` dies with `No module named pytest` and reads as a false RED")),
    "project-python": (
        (".venv\\Scripts\\python.exe" if os.name == "nt" else ".venv/bin/python") + " %s --help",
        (" - launch it with the PROJECT's own interpreter (or pass `--python PATH`): its work "
         "runs the project's pytest, and only an interpreter with pytest and the project "
         "installed gives a verdict; launched through uv it finds one only in ./.venv")),
}

#: Resolved key for a docstring that shows the tool launched two different non-uv ways.
AMBIGUOUS = "ambiguous"

#: A launch written in a docstring, as (LAUNCHERS key, pattern for the words before the path).
#: The plugin's run-python.sh shim is a plain interpreter too, so it counts as "python3".
_DOCUMENTED_LAUNCHERS = (
    ("project-python", r"\S*\.venv[\\/](?:bin[\\/]python3?|Scripts[\\/]python(?:\.exe)?)"),
    ("python3", r"(?:bash\s+\S*run-python\.sh|python3?|py\s+-3)"),
    ("uv", r"uv\s+run"),
)


def _parse_source(path):
    """The tool's module AST, or None when it cannot be read or parsed."""
    try:
        return ast.parse(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError, ValueError):
        return None


def _launch_declaration(tree):
    """The string assigned to a top-level `LAUNCH_WITH`, or None."""
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else [])
        value = getattr(node, "value", None)
        if (any(isinstance(t, ast.Name) and t.id == "LAUNCH_WITH" for t in targets)
                and isinstance(value, ast.Constant) and isinstance(value.value, str)):
            return value.value
    return None


def declared_launch(path):
    """The tool's `LAUNCH_WITH` value, read by parsing its source (never executing it); "uv" when
    it declares none or cannot be read. A hook must not run arbitrary module-level code."""
    tree = _parse_source(path)
    declared = _launch_declaration(tree) if tree is not None else None
    return declared if declared is not None else "uv"


def documented_launch(tree, filename):
    """The LAUNCHERS key the module docstring shows running `filename` itself, or None. PURE.

    Only a launcher immediately followed by a path ENDING in this file counts, so an example that
    runs some other file (`--a "python3 old.py"`) says nothing about this one. A non-uv launch
    wins over `uv run`, because a docstring that names a non-default launch for itself does so on
    purpose, while a `uv run` beside it is usually the counter-example ("NOT uv run"). Two
    different non-uv launches are AMBIGUOUS: guessing one is the wrong-interpreter suggestion."""
    doc = ast.get_docstring(tree) or ""
    path_tail = r"\s+(?:\S*[\\/])?" + re.escape(filename) + r"(?![\w.])"
    said = {key for key, launcher in _DOCUMENTED_LAUNCHERS
            if re.search(r"(?:^|(?<=[\s`(\"']))" + launcher + path_tail, doc, re.M)}
    non_uv = said - {"uv"}
    if len(non_uv) > 1:
        return AMBIGUOUS
    return next(iter(non_uv), "uv" if said else None)


def resolve_launch(path):
    """The LAUNCHERS key (or an unknown declared value, or AMBIGUOUS) for the tool at `path`: its
    `LAUNCH_WITH`, else the launch its docstring documents for itself, else "uv"."""
    tree = _parse_source(path)
    if tree is None:
        return "uv"
    return (_launch_declaration(tree) or documented_launch(tree, Path(path).name) or "uv")


def launch_command(path, shown=None):
    """(command, note) to suggest for the tool at `path`, shown as `shown` (default: the path).

    A declaration this hook does not know, or a docstring showing two different launches, is a
    requirement it cannot honour, so it never falls back to `uv run` - that would be the
    wrong-interpreter suggestion this exists to prevent."""
    shown = shown or str(path)
    launch = resolve_launch(path)
    if launch == AMBIGUOUS:
        return f"{shown} --help", (" - launch it as its docstring says: it documents more than "
                                   "one launch for itself, so read which one applies")
    if launch not in LAUNCHERS:
        note = (f" - launch it as its docstring says: it declares LAUNCH_WITH={launch!r}, "
                f"which this hook does not know")
        return f"{shown} --help", note
    template, note = LAUNCHERS[launch]
    return template % shown, note


def _nudge_flag(session):
    """Where this session's already-nudged tool list lives - a named helper so the path is testable
    rather than built inline, and so the id passes through the shared confinement on the way."""
    from self_improve_signals import session_state_path   # noqa: PLC0415 - shared, confines the id
    return session_state_path(session, ".toolbox-nudged")


def _already_nudged(session, tool):
    """Per-session dedup: True if `tool` was already nudged this session; else record it. Best-effort.

    With no session id there is nothing to dedup within, so every matching call nudges. Claude Code
    always sends one; a fallback key would be shared by every sessionless caller for as long as
    the state file lives, turning a missing field into permanent silence, and a repeated nudge is
    the safer failure (pinned by test_without_a_session_id_every_matching_call_nudges)."""
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
    tool_input = event.get("tool_input") or {}
    text = extract_text(event.get("tool_name"), tool_input)
    hit = match_tool(text, event.get("tool_name"))
    if not hit and is_shell_tool(event.get("tool_name")):
        # Second reading of the SAME call: a heredoc body is stripped from the command because it
        # is data, and it is also where a program gets authored. The command reading keeps
        # precedence - it is the shipped, measured one - so this only reaches text nothing saw.
        hit = match_authored(heredoc_bodies(tool_input.get("command", "")))
    if not hit:
        return 0
    tool, why = hit
    found = _tool_invocation(tool)
    if not found:                                        # nowhere local, nowhere shipped -> silent
        return 0
    home, path, shown = found
    invoke, note = launch_command(path, shown)
    if _already_nudged(event.get("session_id") or "", tool):
        return 0
    msg = ("%s has a tested tool for this (%s): `%s`%s. Prefer it over hand-rolling; if it "
           "falls short, ENHANCE it (propose-first, per bitranox:meta-self-improve) rather than "
           "working around it." % (home.capitalize() if home.startswith("the") else home, why,
                                   invoke, note))
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": msg}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
