#!/usr/bin/env python3
"""PreToolUse(Bash|Write|Edit) gate: this call REPEATS a destructive act that already had to be undone.

WHY THIS EXISTS, next to jig-repetition-nudge.py. That hook asks "is this the same job again?" and
answers it from SCRIPT TEXT - shingles, shared purpose words, numbered stems. Measured over 97 real
sessions its nudges were 41% true / 27% partial / 32% false, and the tax is structural: a rewrite is
DEFINED by looking different while meaning the same, so a lexical proxy must either miss the rewrite
or fire on every pair of PowerShell scripts.

This gate asks a different question about ACTIONS, not text: "did the last attempt at this have to be
TAKEN BACK, and are we about to do it again?" A rewrite that works first time leaves no trace here -
that is the point. It is deterministic end to end; no model call, no classifier. The JUDGEMENT is
delegated to the session's own model by handing it evidence and a skill pointer.

THE PREDICATE, and what each clause is for. All four must hold. Every count below is from replaying
this module over the main-session transcripts on this machine (507 files, 56k tool events, 99 machine
undos). Read those counts against the ELIGIBLE population, never the file count: of 1426 transcripts,
93 hold a recovery of any kind, 22 hold the machine undo this gate reads, 7 ever arm, and 1 fires. A
per-transcript rate is diluted by stubs and by 919 subagent transcripts the sidechain skip makes it
structurally blind to.

  1. UNDONE       an earlier event UNDID MACHINE state: `qm/pct rollback`, `zfs rollback`,
                  `virsh snapshot-revert`, `Restore-VMSnapshot`. Nothing else - see below.
  2. DAMAGE       something DESTRUCTIVE ran within BLAST_RADIUS events before that undo (a /MIR
                  mirror, a recursive delete, an ACL rewrite, a format, a package removal). This is
                  what separates damage from a RESET LOOP: `qm rollback <vm> clean` before each
                  redeploy is a METHOD, and it is the common case - 79 of the 99 undos arm nothing
                  because no destructive act precedes them. Ablating this clause changes no firing
                  in the corpus, because clause 4 excludes the same events by a different route; it
                  is kept so that a reset loop is silent structurally rather than by luck of which
                  verbs are in the vocabulary.
  3. SAME SUBJECT this call names a MACHINE the damaged work named - a guest id, a host or an IP.
                  Machines only: the undo was of machine state, so a file named in the same command
                  is a tool rather than the victim, and allowing file subjects added 3 firings, all
                  of them a routine reset followed by an ordinary edit of a script. Identifiers that
                  are UBIQUITOUS in the session are dropped first (COMMON_ID_FRACTION), or the
                  hypervisor host - a quarter of a fleet session's commands - links everything.
  4. SAME ACT     this call runs one of the same destructive OPERATIONS. Without it the gate fires
                  on the aftermath of the undo - booting the restored guest, verifying it, stopping
                  it, diagnosing it - and the corpus goes from 5 firings to 43, including the
                  read-only "is the guest fully restored?" check two events after the rollback.

WHAT IT WILL NOT SEE. It is blind to damage undone by hand (re-installing, re-typing a file), to
every repo-level undo (`git stash` / `git checkout --` / `git restore` are how a session proves a
test RED - 101 of the 127 git undos here - and admitting the harder-looking `git reset --hard`,
`git revert` and `cp` back from a .bak added firings that were all mutate-test-restore proofs), and
to anything in a subagent transcript (sidechain entries are skipped, as in the ledger).

Non-blocking (additionalContext), one message per undo event, capped per session, silent on any error.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from overwatch_ledger import _strip_leading_cd as strip_leading_cd  # noqa: E402 - shared normaliser
from shell_text import strip_heredoc_bodies                          # noqa: E402 - shared with the guards

__all__ = [
    "arm_recovery",
    "build_message",
    "destructive_ops",
    "matching_recovery",
    "mentions",
    "recovery_class",
    "strip_comment_lines",
]

# ----------------------------------------------------------------------------- constants
#
# Every number here is a measured floor plus headroom, not a guess. The floors come from replaying
# the reference session (a guest destroyed, rolled back, then destroyed again 36 events later) and
# the 506-session corpus on this machine.

# How long after an undo a repeat still counts as "the same stretch of work". FLOOR 36: the second
# destruction of the reference guest lands 36 events after its rollback, and 30 misses it. 60 gives
# headroom and costs nothing measured - 40, 60 and 120 all fire on exactly the same 5 events corpus-wide.
LOOKBACK_EVENTS = 60

# How far back from the undo to look for the act that CAUSED it. FLOOR 19: the failing delete sits 19
# events before its rollback, with unrelated work (a second guest, a repo edit) interleaved. 10 misses
# it; 25, 30 and 40 all give the same corpus result, so 25 is the floor plus headroom.
BLAST_RADIUS = 25

# An identifier mentioned in more than this fraction of the session's events is treated as scenery
# rather than a subject. Measured on the reference session: the identifier that carries the true
# firing appears in 3.8% and 4.8% of events at the two arming points, while the hypervisor host -
# which would link every guest to every other - appears in 26%. 0.05 sits a hair above the real
# carrier and 0.03 loses the case entirely, so the gap is where the threshold belongs.
COMMON_ID_FRACTION = 0.10
# A count below this is never "scenery", whatever the fraction says. A young session has no scenery
# yet, and the subject of a destroy-undo-retry sequence collects mentions from that sequence itself:
# at 3 the third cycle of a short session drops its own subject and the gate goes quiet exactly where
# it should speak. Above it the fraction takes over, so this cannot loosen a long session.
COMMON_ID_FLOOR = 8

FIRE_CAP = 3                 # messages per session; one undo event can produce at most one of them
STATE_VERSION = 1
MAX_SEEN_IDS = 4000          # bound the state file on a marathon session
GATED_TOOLS = ("Bash", "Write", "Edit")

# ----------------------------------------------------------------------------- text regions

# A whole-line comment is PROSE. A guard that scans a script body must strip it or a comment warning
# "robocopy /MIR follows junctions unless /XJ is passed" reads as running a mirror - measured: that
# exact line in a read-only diagnostic script produced the reference session's only spurious firing.
COMMENT_LINE = re.compile(r"^\s*(?:#|//|REM\b|::|<\#|\*)", re.I)


def strip_comment_lines(text: str) -> str:
    """Drop whole-line comments, keeping code. PURE."""
    return "\n".join(line for line in (text or "").split("\n") if not COMMENT_LINE.match(line))


# ----------------------------------------------------------------------------- destructive acts

# Acts that DESTROY or overwrite state that was already there. Deliberately excludes lifecycle verbs
# (`qm stop`/`start`, `systemctl restart`, taking a snapshot) and deployment (`cp -f` of a binary,
# `chown -R` of your own tree): those are how a session cleans up, verifies and iterates AFTER an
# undo, and counting them made the gate fire on its own aftermath and on every redeploy in a
# rollback-per-iteration loop.
_OPS = (
    ("mirror", r"\brobocopy\b[^\n]*?/(?:mir|purge)\b"),
    ("rmtree", (r"\brm\s+-[a-z]*[rR][a-z]*f|\brm\s+-[a-z]*f[a-z]*[rR]|\bRemove-Item\b"
                r"|\brmdir\s+/s|\brd\s+/s|\bdel\s+/[sq]")),
    ("chattr", r"\btakeown\b|\bicacls\b|\bSet-Acl\b"),
    ("wipefs", r"\bmkfs\b|\bdd\s+if=|\bformat\s+[a-z]:|\bdiskpart\b|\bwipefs\b"),
    ("regdel", r"\breg\s+delete\b|\bRemove-ItemProperty\b"),
    ("destroy", r"\b(?:zfs|zpool)\s+destroy\b|\b(?:qm|pct)\s+destroy\b|\blvremove\b|\bvgremove\b"),
    ("pkgrm", (r"\bRemove-Appx\w*\b|\bUninstall-\w+\b|\bapt(?:-get)?\s+(?:purge|remove)\b"
               r"|\bdism\b[^\n]*/(?:remove|cleanup|reset)")),
    ("dbdrop", r"\bDROP\s+(?:TABLE|DATABASE|SCHEMA)\b|\bTRUNCATE\s+TABLE\b|\bDELETE\s+FROM\b"),
    ("gitwipe", r"\bgit\s+clean\s+-[a-z]*[fd]|\bgit\s+push\s+[^\n]*--force\b|\bgit\s+reset\s+--hard\b"),
)
_OPS = tuple((name, re.compile(pattern, re.I)) for name, pattern in _OPS)


def destructive_ops(text: str) -> set:
    """Canonical names of the destructive operations `text` performs. PURE.

    The heredoc BODY is read here, unlike in the ledger's target extraction: a script authored as
    `cat > purge.ps1 <<'EOS' ... EOS` is where the destruction lives, and the shell line around it
    says nothing. Comments are stripped first for the same reason the ledger strips heredocs.
    """
    return {name for name, pattern in _OPS if pattern.search(strip_comment_lines(text))}


# ----------------------------------------------------------------------------- undo detection

# Undo of MACHINE state only. Every other kind of undo in this corpus is a METHOD rather than damage,
# and the exclusion is measured, not taste: `git stash` / `git checkout --` / `git restore` are the
# RED-proof idiom (park the fix, prove the test fails, restore) at 101 of 127 git undos, and admitting
# the harder-looking forms too - `git reset --hard`, `git revert`, a `cp` back from a .bak - took the
# corpus from 1 firing session to 5, where all four additions were a mutate-test-restore proof and
# none was damage. The price is real and is stated in the header: damage undone inside a repo, or by
# hand, is invisible here.
_UNDO = (
    ("guest", r"\b(?:qm|pct)\s+rollback\b"),
    ("zfs", r"\bzfs\s+rollback\b"),
    ("vm", (r"\bRestore-(?:Computer|VMSnapshot|VMCheckpoint)\b|\bvirsh\s+snapshot-revert\b"
            r"|\bvboxmanage\s+snapshot\s+\S+\s+restore\b")),
)
_UNDO = tuple((name, re.compile(pattern, re.I)) for name, pattern in _UNDO)

# A search pattern is DATA. `grep 'qm rollback' log.jsonl` inspects rollbacks and performs none; the
# ledger learned this the same way, by self-matching on its own investigation.
_SEARCH_ARG = re.compile(
    r"\b(?:grep|egrep|fgrep|rg|ag|ack|awk|sed|echo|printf)\b[^|;&\n]*?(?:'[^']*'|\"[^\"]*\")"
)


def recovery_class(tool: str, tool_input: dict) -> str:
    """Which kind of undo this call performs, or "" for none. PURE."""
    if tool != "Bash":
        return ""
    command = strip_heredoc_bodies(str((tool_input or {}).get("command") or ""))
    command = strip_comment_lines(_SEARCH_ARG.sub(" ", command))
    for name, pattern in _UNDO:
        if pattern.search(command):
            return name
    return ""


# ----------------------------------------------------------------------------- subjects

_GUEST = re.compile(r"\b(?:qm|pct)\s+[a-z-]+\s+(\d{3,6})\b")
_SSHHOST = re.compile(r"(?<![\w.-])[a-z_][\w.-]*@([a-z0-9][\w.-]*)", re.I)
_IPV4 = re.compile(r"(?<![\w.])((?:\d{1,3}\.){3}\d{1,3})(?![\w.])")
_FILEISH = re.compile(r"[\w./\\~-]+\.(?:ps1|py|sh|bash|psm1|cmd|bat)\b")
# `ssh-ed25519 AAAA... root@buildhost` - the trailing word of a public key is its COMMENT, not a
# host. Installing fleet keys made every such command "mention" the same phantom host, and that
# phantom carried a false firing in the corpus.
_PUBKEY = re.compile(r"\bssh-(?:rsa|ed25519|dss)\s+AAAA[\w+/=]+(?:\s+\S+@\S+)?")
# `user@thing` only names a LOGIN TARGET inside a remote-shell command. Everywhere else it is an
# address: `git -c user.email="dev@example.com" commit` made the mail provider a subject, and a
# subject that appears in every commit would link unrelated stretches of work.
_REMOTE_VERB = re.compile(r"\b(?:ssh|scp|sftp|rsync)\b")


def _basename(path: str) -> str:
    return re.split(r"[\\/]", str(path or ""))[-1]


def mentions(tool: str, tool_input: dict) -> set:
    """Every identifiable SUBJECT this call names: guests, hosts, files. PURE.

    Not the ledger's single normalised target. Repetition on a fleet crosses spellings - the guest is
    `qm rollback 4242` to the hypervisor and an IP to the ssh that runs the script - and a one-target
    key cannot see that the two are the same machine. Heredoc bodies are stripped: a script's own
    internal paths are not what it is being run against.
    """
    tool_input = tool_input or {}
    if tool in ("Write", "Edit", "NotebookEdit"):
        name = _basename(tool_input.get("file_path") or "")
        return {"f:" + name} if name else set()
    if tool != "Bash":
        return set()
    command = _PUBKEY.sub(" ", strip_leading_cd(strip_heredoc_bodies(str(tool_input.get("command") or ""))))
    found = {"vm:" + m.group(1) for m in _GUEST.finditer(command)}
    found |= {"host:" + m.group(1) for m in _IPV4.finditer(command)}
    if _REMOTE_VERB.search(command):
        for match in _SSHHOST.finditer(command):
            host = match.group(1)
            if "/" not in host and not host.endswith((".key", ".pem", ".pub")):
                found.add("host:" + host.lower())
    found |= {"f:" + _basename(m.group(0)) for m in _FILEISH.finditer(command)}
    return {identifier for identifier in found if len(identifier) < 80}


def acting_text(tool: str, tool_input: dict) -> str:
    """The text whose destructive operations count for this call. PURE."""
    tool_input = tool_input or {}
    if tool == "Bash":
        return str(tool_input.get("command") or "")
    if tool == "Write":
        return str(tool_input.get("content") or "")
    if tool == "Edit":
        return str(tool_input.get("new_string") or "")
    return ""


# ----------------------------------------------------------------------------- the rule

def arm_recovery(window: list, undo_mentions: set, seen: dict, position: int) -> tuple:
    """(subject ids, destructive ops) an undo at `position` should watch for. PURE.

    `window` is the BLAST_RADIUS records before the undo as (mentions, ops) pairs. An undo with no
    destructive act behind it arms NOTHING - that is a reset to baseline, which is a method rather
    than damage, and it is what keeps the gate silent through a rollback-per-iteration loop.
    """
    ids: set = set()
    ops: set = set()
    for record_mentions, record_ops in window:
        if record_ops:
            ids |= set(record_mentions)
            ops |= set(record_ops)
    if not ops:
        return set(), set()
    ids |= set(undo_mentions)
    limit = max(COMMON_ID_FLOOR, int(position * COMMON_ID_FRACTION))
    # A MACHINE-state undo damaged a MACHINE, so a machine is the subject that has to match. A file
    # named in the same breath is a tool, not the victim: allowing file subjects fired on two
    # reset-to-baseline loops in the corpus, where a routine `qm rollback <vm> clean` followed a
    # command that happened to contain `rm -rf` and the session then edited the script it named.
    return {i for i in ids if i.startswith(("vm:", "host:")) and int(seen.get(i, 0)) <= limit}, ops


def matching_recovery(armed: list, pending_ids: set, pending_ops: set, position: int):
    """The most recent armed undo this pending call re-attempts, or None. PURE.

    `armed` is [(index, ids, ops)], oldest first. Newest first here because the freshest undo is the
    one worth citing, and one message is all a call gets.
    """
    for index, ids, ops in reversed(armed):
        if position - index > LOOKBACK_EVENTS:
            break
        shared_ids = pending_ids & set(ids)
        shared_ops = pending_ops & set(ops)
        if shared_ids and shared_ops:
            return index, sorted(shared_ids), sorted(shared_ops)
    return None


# ----------------------------------------------------------------------------- transcript state

def _state_path(session: str) -> Path:
    from self_improve_signals import _audit_dir           # noqa: PLC0415 - shared audit dir helper
    return _audit_dir() / (str(session) + ".recovery-gate.json")


def _load(session: str) -> dict:
    try:
        state = json.loads(_state_path(session).read_text(encoding="utf-8"))
    except Exception:                                     # noqa: BLE001 - absent/corrupt: start fresh
        return {}
    if not isinstance(state, dict) or state.get("v") != STATE_VERSION:
        return {}
    return state


def _save(session: str, state: dict) -> None:
    try:
        path = _state_path(session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
    except Exception:                                     # noqa: BLE001 - state must never break the hook
        pass


def _tool_calls(chunk: str):
    """(tool, tool_input) for every MAIN-session tool call in a transcript chunk. PURE.

    Sidechain entries are skipped exactly as the ledger skips them: a subagent's calls are not this
    session's actions, and folding them in makes one dispatched agent look like a burst of repeats.
    """
    for raw in chunk.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("isSidechain"):
            continue
        message = entry.get("message")
        blocks = (message or {}).get("content") if isinstance(message, dict) else None
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name") or "?", block.get("input") or {}


def _read_new_lines(transcript: str, offset: int) -> tuple:
    """(complete new text, new offset). Reads only the tail written since `offset`.

    Rebuilding the whole ledger per call costs 400-500 ms on the largest transcripts on this machine
    (50 MB, 1600 records) and this hook runs on EVERY Bash, Write and Edit. A partial trailing line is
    left for the next call - the file is being appended to while this reads.
    """
    try:
        size = os.path.getsize(transcript)
    except OSError:
        return "", offset
    if size < offset:                                     # rotated or truncated: start over
        offset = 0
    if size == offset:
        return "", offset
    try:
        with open(transcript, "rb") as handle:
            handle.seek(offset)
            raw = handle.read(size - offset)
    except OSError:
        return "", offset
    cut = raw.rfind(b"\n")
    if cut < 0:
        return "", offset
    return raw[:cut + 1].decode("utf-8", errors="replace"), offset + cut + 1


def split_pending(records: list, pending_key: tuple) -> tuple:
    """(history, trailing pending record or None). PURE.

    The call being gated is usually ALREADY in the transcript when PreToolUse runs - the assistant
    message carrying the tool_use block is written before the tool executes. It must be judged
    against the events BEFORE it and then absorbed exactly once, so it is split off here rather than
    discarded: dropping it outright let `off` advance past it and the running state counted 64 of 766
    events, which no in-process replay could see because only the real subprocess advances `off`.
    """
    if not records or pending_key is None:
        return records, None
    tool, tool_input = records[-1]
    if (tool, acting_text(tool, tool_input)) == pending_key:
        return records[:-1], records[-1]
    return records, None


def _absorb(state: dict, records: list) -> dict:
    """Fold parsed records into the running state. Impure only in that it mutates `state`."""
    seen = state.setdefault("seen", {})
    armed = state.setdefault("armed", [])
    window = [tuple(pair) for pair in state.get("window") or []]
    for tool, tool_input in records:
        state["n"] = int(state.get("n") or 0) + 1
        position = state["n"]
        record_mentions = mentions(tool, tool_input)
        record_ops = destructive_ops(acting_text(tool, tool_input))
        undo = recovery_class(tool, tool_input)
        if undo:
            ids, ops = arm_recovery(window, record_mentions, seen, position)
            if ids:
                armed.append([position, sorted(ids), sorted(ops)])
        for identifier in record_mentions:
            seen[identifier] = int(seen.get(identifier, 0)) + 1
        window.append([sorted(record_mentions), sorted(record_ops)])
        window = window[-BLAST_RADIUS:]
    state["window"] = [[list(m), list(o)] for m, o in window]
    state["armed"] = [a for a in armed if int(state.get("n") or 0) - int(a[0]) <= LOOKBACK_EVENTS][-40:]
    if len(seen) > MAX_SEEN_IDS:                          # bound the file; singletons are the bulk
        state["seen"] = {k: v for k, v in seen.items() if v > 1}
    return state


# ----------------------------------------------------------------------------- the handover

def build_message(damage_index: int, subjects: list, ops: list, gap: int) -> str:
    """The additionalContext handed to the model. PURE - so its content is testable.

    Evidence and a question, not a verdict: the gate knows an undo happened and that this call
    repeats the act on the same subject, and it cannot know whether THIS attempt is different.
    """
    return (
        "STOP-CHECK - this call repeats an act that already had to be UNDONE this session.\n"
        "  event %d UNDID the state of: %s\n"
        "  the act being repeated: %s (about %d events later)\n"
        "An undo means the previous attempt made things WORSE, not merely that it did not work, so "
        "the moment to stop is BEFORE attempt N+1. State what is DIFFERENT this time and what proves "
        "it - a test, a dry run, a narrower scope - or do not run it. "
        "Read bitranox:process-stop-repeating-failure first.\n"
        "If this call is the DIAGNOSIS rather than the retry, ignore this and say nothing about it."
        % (damage_index, ", ".join(subjects[:4]), ", ".join(ops[:4]), gap)
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    tool = event.get("tool_name") or ""
    session = event.get("session_id") or ""
    transcript = event.get("transcript_path") or ""
    if tool not in GATED_TOOLS or not session or not transcript:
        return 0

    tool_input = event.get("tool_input") or {}
    text = acting_text(tool, tool_input)
    state = _load(session) or {"v": STATE_VERSION, "off": 0, "n": 0}
    chunk, offset = _read_new_lines(transcript, int(state.get("off") or 0))
    state["off"] = offset
    history, pending_record = split_pending(list(_tool_calls(chunk)), (tool, text))
    state = _absorb(state, history)

    hit = None
    if int(state.get("fires") or 0) < FIRE_CAP and not recovery_class(tool, tool_input):
        armed = [a for a in state.get("armed") or [] if int(a[0]) not in set(state.get("cited") or [])]
        hit = matching_recovery(armed, mentions(tool, tool_input), destructive_ops(text),
                                int(state.get("n") or 0) + 1)
    if hit:
        index, subjects, ops = hit
        state["fires"] = int(state.get("fires") or 0) + 1
        state["cited"] = sorted(set(state.get("cited") or []) | {index})
    if pending_record is not None:                        # judged above, now part of the history
        state = _absorb(state, [pending_record])
    _save(session, state)

    if hit:
        index, subjects, ops = hit
        message = build_message(index, subjects, ops, int(state.get("n") or 0) + 1 - index)
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext": message}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                     # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
