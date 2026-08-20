#!/usr/bin/env python3
"""Action ledger for the overwatcher: what a session DID, one line per tool call.

WHY THIS EXISTS, next to jig-repetition-nudge.py. That hook answers "is this the same job again?"
by comparing SCRIPT TEXT - token shingles, shared purpose words, numbered stems. Measured over 97
real sessions its nudges were 41% true, 27% partial, 32% false. The tax is structural, not a
tuning miss: a rewrite is DEFINED by looking different while meaning the same, so a lexical proxy
must either miss the rewrite or fire on every pair of PowerShell scripts.

This module answers a different question and answers it about ACTIONS rather than text: "are we
failing repeatedly at the same thing?" The evidence for that is not in what a script SAYS, it is
in what happened when it RAN - the same target touched again, the same error again, and above all
a RECOVERY action, because rolling a machine back is the session admitting the last attempt made
things worse. A script rewrite that works first time leaves no trace here, which is the point.

WHAT A RECORD HOLDS, and why each field earns its line. The ledger is read by a cheap classifier,
so every character is paid for on every call:

    index    ordinal of the tool call, so a verdict can cite WHICH events it used.
    tool     Bash / Write / Edit / Read / Agent - the coarse kind of act.
    target   what was acted ON, normalised so two spellings of one thing collide: a VM id, a
             remote host, a script basename, a repo-relative file. Repetition is invisible unless
             the target NAME is stable, and the same VM appears as `qm stop 4242`, inside an ssh
             one-liner, and as a scp destination.
    intent   a short human string. For Bash this is the agent's OWN `description` field, which is
             the cheapest high-signal intent available anywhere in a transcript - it was written
             to say what the call is for, before the result was known.
    outcome  ok / err. An error is the only thing that distinguishes "doing this a lot" from
             "failing at this a lot", and those want opposite advice.
    marker   RECOVERY when the act undoes prior state (rollback, restore, revert, reset --hard).

Records render as ONE line. Measured over 122 real windows, a 60-record window plus the whole
instruction block averages 6.5 kB, about 1.8k input tokens - small enough that the classifier
payload is never what a call costs.

PURE, no I/O beyond reading a transcript path; every classifier here is unit-testable.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from shell_text import is_shell_tool, strip_heredoc_bodies  # noqa: E402 - shared with the other command guards

__all__ = [
    "LedgerRecord",
    "build_ledger",
    "iter_tool_events",
    "ledger_line",
    "normalise_target",
    "outcome_of",
    "parse_verdict",
    "recovery_marker",
    "render_window",
    "build_prompt",
    "STOP_VERDICTS",
    "VERDICTS",
]

VERDICTS = ("none", "repeating_job", "repeating_failure")
# STOP-class: the session is not converging and should stop rather than write attempt N+1.
# `repeating_job` is the jig case - it works, it is just being rebuilt - and must NOT stop anyone.
STOP_VERDICTS = ("repeating_failure",)

INTENT_WIDTH = 80
TARGET_WIDTH = 34

SCRIPT_SUFFIXES = {".ps1", ".py", ".sh", ".bash", ".psm1", ".cmd", ".bat"}

# ------------------------------------------------------------------ target extraction

# `qm rollback 4242 snap` / `pct stop 105` - a PVE guest id is the most stable target name a
# fleet session has: it survives being embedded in an ssh one-liner, which a hostname does not.
_GUEST = re.compile(r"\b(?:qm|pct)\s+(?:[a-z-]+)\s+(\d{3,6})\b")
# `root@node.example.com` / `admin@host.example.com` - the login target of an ssh/scp.
_SSHHOST = re.compile(r"(?<![\w.-])[a-z_][\w.-]*@([a-z0-9][\w.-]*)", re.I)
# `cat > purge.ps1 <<'EOS'` and `scp foo.ps1 host:` both name a script; take the basename.
_REDIRECT_SCRIPT = re.compile(r">>?\s*(['\"]?)([^\s'\";|&<>]+)\1")
_GIT = re.compile(r"\bgit\s+(?:-[^\s]+\s+)*([a-z][a-z-]*)")

# Acts that UNDO prior state. Rolling back is the strongest single signal in a transcript that an
# attempt made things worse, which is exactly what "should we stop?" turns on. Kept narrow on
# purpose: `qm snapshot` (taking one) is NOT recovery, and neither is `git restore --staged`
# without a path, so the patterns require the undo form.
_RECOVERY = re.compile(
    r"""(?xi)
      \b(?:qm|pct)\s+rollback\b
    | \bzfs\s+rollback\b
    | \bgit\s+reset\s+--hard\b
    | \bgit\s+revert\b
    | \bgit\s+checkout\s+--\s
    | \bgit\s+restore\s+(?!--staged\b)
    | \bgit\s+stash\s+pop\b
    | \bRestore-(?:Computer|VMSnapshot|VMCheckpoint)\b
    | \bvirsh\s+snapshot-revert\b
    | \bvboxmanage\s+snapshot\s+\S+\s+restore\b
    | \bcp\s+-a?\s*\S*\.(?:bak|orig)\b
    """
)


def _basename(path: str) -> str:
    """Last path component, kept short. PURE."""
    return Path(str(path)).name[:TARGET_WIDTH] or str(path)[:TARGET_WIDTH]


def _script_written(command: str) -> str:
    """Basename of a script this command AUTHORS via redirect, else "". PURE.

    Scripts in a real session are overwhelmingly written as `cat > x.ps1 <<'EOS'`, not with the
    Write tool, so a target extractor that only reads `file_path` sees none of them. Take the LAST
    script-suffixed redirect target: a command routinely carries an unrelated `2>/dev/null` first.
    """
    found = [
        m.group(2)
        for m in _REDIRECT_SCRIPT.finditer(command or "")
        if Path(m.group(2)).suffix.lower() in SCRIPT_SUFFIXES
    ]
    return _basename(found[-1]) if found else ""


def normalise_target(tool: str, tool_input: dict) -> str:
    """One stable name for the thing this call acted on. PURE.

    Order matters and encodes what repetition is ABOUT. A guest id beats a hostname because the
    same broken VM is the subject even when the ssh hop changes; a script name beats the host it
    was copied to because rewriting the script is the repetition being hunted.
    """
    tool_input = tool_input or {}
    if tool in ("Write", "Edit", "Read", "NotebookEdit"):
        return _basename(tool_input.get("file_path") or "")
    if tool == "Skill":
        return str(tool_input.get("skill") or "")[:TARGET_WIDTH]
    if tool == "Agent":
        return "agent:" + str(tool_input.get("subagent_type") or "task")[:TARGET_WIDTH]
    if not is_shell_tool(tool):
        return tool.lower()

    command = _strip_leading_cd(str(tool_input.get("command") or ""))
    script = _script_written(command)
    if script:
        return script
    guest = _GUEST.search(command)
    if guest:
        return "vm:" + guest.group(1)
    git = _GIT.search(command)
    if git:
        return "git:" + git.group(1)
    host = _ssh_host(command)
    if host:
        return "host:" + host
    first = command.strip().split()
    return (first[0][:TARGET_WIDTH] if first else "sh")


# `cd /long/scratch/path && <the command that matters>`. Almost every Bash call in a real session
# opens this way, and without stripping it EVERY such call reports the target `cd`, collapsing a
# session's distinct work into one giant look-alike group.
_LEADING_CD = re.compile(r"^\s*cd\s+(?:'[^']*'|\"[^\"]*\"|[^\s;&|\n]+)\s*(?:&&|;|\n)\s*")


def _strip_leading_cd(command: str) -> str:
    """Drop a leading `cd <dir> &&` chain so the real command is what gets classified. PURE."""
    previous = None
    while previous != command:
        previous = command
        command = _LEADING_CD.sub("", command, count=1)
    return command


def _ssh_host(command: str) -> str:
    """Login host of an ssh/scp in `command`, else "". PURE.

    Every candidate is checked, not just the first: the fleet's own key is named
    `root@shared_nopass.key`, so the FIRST `user@thing` on a real ssh line is a KEY PATH. Taking
    only the first match and rejecting it dropped the host from every fleet command in the corpus.
    """
    for match in _SSHHOST.finditer(command or ""):
        candidate = match.group(1)
        if "/" in candidate or candidate.endswith((".key", ".pem", ".pub")):
            continue
        return candidate[:TARGET_WIDTH]
    return ""


# ------------------------------------------------------------------ outcome + intent


# A search pattern is DATA, not a command. `grep 'qm rollback' session.jsonl` inspects rollbacks,
# it does not perform one, and counting it as recovery is the same self-match that makes a
# command-scanning guard fire on its own documentation. Strip the quoted argument of the search
# family before looking for undo verbs.
_SEARCH_ARG = re.compile(
    r"\b(?:grep|egrep|fgrep|rg|ag|ack|awk|sed|echo|printf)\b[^|;&\n]*?(?:'[^']*'|\"[^\"]*\")"
)


def recovery_marker(tool: str, tool_input: dict) -> bool:
    """True when this call UNDOES prior state. PURE.

    Both data regions are stripped first, heredoc BODY included: a Bash call that embeds an
    analysis program (`python3 - <<'PY' ... re.finditer(r'qm rollback ...') ... PY`) reads about
    rollbacks and performs none, and it self-matched here until the body was removed.
    """
    if not is_shell_tool(tool):
        return False
    command = strip_heredoc_bodies(str((tool_input or {}).get("command") or ""))
    return bool(_RECOVERY.search(_SEARCH_ARG.sub(" ", command)))


def outcome_of(result: dict) -> str:
    """"ok" or "err" for a tool_result payload. PURE.

    Three independent signals, because no single one is complete: the harness `is_error` flag
    covers blocked and malformed calls; a Bash non-zero exit arrives as an `Exit code N` preamble
    in the result TEXT with the flag unset; and a `<tool_use_error>` wrapper marks a rejected call.
    Counting only the flag on one real session found 30 failures where all three found far more.
    """
    result = result or {}
    if result.get("is_error"):
        return "err"
    content = result.get("content")
    text = content if isinstance(content, str) else json.dumps(content or "")[:4000]
    head = text.lstrip()[:220]
    if head.startswith("<tool_use_error>"):
        return "err"
    if re.match(r"Exit code\s+[1-9]", head):
        return "err"
    return "ok"


def _intent(tool: str, tool_input: dict) -> str:
    """Short human string saying what this call is FOR. PURE."""
    tool_input = tool_input or {}
    if is_shell_tool(tool):
        said = str(tool_input.get("description") or "").strip()
        if said:
            return said[:INTENT_WIDTH]
        return " ".join(str(tool_input.get("command") or "").split())[:INTENT_WIDTH]
    if tool == "Agent":
        return str(tool_input.get("description") or "")[:INTENT_WIDTH]
    if tool in ("Write", "Edit"):
        return ("write " if tool == "Write" else "edit ") + _basename(tool_input.get("file_path") or "")
    if tool == "Read":
        return "read " + _basename(tool_input.get("file_path") or "")
    return tool.lower()


# ------------------------------------------------------------------ records


class LedgerRecord:
    """One tool call, reduced to what a repetition judgement needs.

    A plain class with a typed __init__ rather than a dataclass: pyright strict infers Unknown for
    a bare default_factory, and this type is read by a hook that must never raise.
    """

    __slots__ = ("index", "tool", "target", "intent", "outcome", "recovery")

    def __init__(
        self,
        index: int,
        tool: str,
        target: str,
        intent: str,
        outcome: str,
        recovery: bool = False,
    ) -> None:
        self.index = index
        self.tool = tool
        self.target = target
        self.intent = intent
        self.outcome = outcome
        self.recovery = recovery

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<LedgerRecord {ledger_line(self)}>"


def ledger_line(record: LedgerRecord) -> str:
    """Render one record as a single pipe-delimited line. PURE.

    Pipe-delimited rather than JSON: a 40-record JSON window costs about twice the tokens for the
    same fields, and the classifier is charged per call.
    """
    marker = " RECOVERY" if record.recovery else ""
    return (
        f"{record.index}|{record.tool}|{record.target}|"
        f"{record.intent}|{record.outcome}{marker}"
    )


def iter_tool_events(transcript: Path | str):
    """Yield (tool_name, tool_input, tool_use_id) for every tool call, in order. PURE-ish (reads).

    Sidechain (subagent) entries are skipped: a subagent's own tool calls are not the main
    session's actions, and folding them in makes one dispatched agent look like a repetition burst.
    """
    for raw in Path(transcript).read_text(encoding="utf-8", errors="replace").splitlines():
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
                yield block.get("name") or "?", block.get("input") or {}, block.get("id") or ""


def _results_by_id(transcript: Path | str) -> dict:
    """Map tool_use_id -> the tool_result block. PURE-ish (reads)."""
    out: dict = {}
    for raw in Path(transcript).read_text(encoding="utf-8", errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        message = entry.get("message")
        blocks = (message or {}).get("content") if isinstance(message, dict) else None
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                out[block.get("tool_use_id")] = block
    return out


def build_ledger(transcript: Path | str) -> list:
    """Full action ledger for a transcript, one record per tool call, 1-indexed."""
    results = _results_by_id(transcript)
    ledger = []
    for position, (tool, tool_input, use_id) in enumerate(iter_tool_events(transcript), start=1):
        ledger.append(
            LedgerRecord(
                index=position,
                tool=tool,
                target=normalise_target(tool, tool_input),
                intent=_intent(tool, tool_input),
                outcome=outcome_of(results.get(use_id) or {}),
                recovery=recovery_marker(tool, tool_input),
            )
        )
    return ledger


def render_window(ledger: list, end: int, size: int, pending: LedgerRecord | None = None) -> str:
    """The `size` records ending at position `end` (1-indexed, inclusive), as text. PURE.

    `pending` renders the action the session is ABOUT to take as a final `PENDING` line. This is
    what makes a PreToolUse deployment different in kind from a periodic one, and the difference
    is decisive rather than cosmetic: whether a session is "still on" a target it had to roll back
    is often not visible in the history at all - the session moves through unrelated work and then
    returns. Measured on the reference session, the history alone gave no signal 2 events before
    the guest was destroyed a second time; the pending action is the signal.
    """
    lo = max(0, end - size)
    lines = [ledger_line(r) for r in ledger[lo:end]]
    if pending is not None:
        lines.append(
            f"PENDING|{pending.tool}|{pending.target}|{pending.intent}|(not yet run)"
        )
    return "\n".join(lines)


# ------------------------------------------------------------------ the classifier contract

PROMPT = """\
You are an overwatcher for a coding/ops session. Below is an ACTION LEDGER: one line per tool
call, oldest first. Fields are pipe-delimited:

  index|tool|target|intent|outcome

`outcome` is ok or err. A trailing ` RECOVERY` means the action UNDID prior state (a VM rollback,
a git reset --hard, a snapshot restore) - i.e. something earlier had to be taken back.

A final line beginning `PENDING` is the action the session is ABOUT to take and has not run yet.
When it is present, judge whether THAT action should proceed.

Decide ONE verdict about the MOST RECENT stretch of work:

  none              - normal progress. Includes repeated actions that are simply the job
                      (running a test suite repeatedly, editing many files, a long build loop,
                      a survey that touches many hosts). Also includes isolated errors that were
                      then fixed, and iteration that is making progress.
  repeating_job     - the SAME job is being solved from scratch again and again with different
                      code, and it mostly WORKS. Worth building a reusable tool. Not urgent.
  repeating_failure - the session is NOT converging on one target: an attempt at some goal had to
                      be UNDONE or keeps failing, and the session is still pursuing that same goal.
                      This is the STOP case - the next attempt should not be written blind.

Judge repeating_failure on these two conditions. Require BOTH:
  (a) DAMAGE OR A STUCK LOOP: an earlier attempt had to be undone (a RECOVERY line on that
      target), or the same target failed two or more times.
  (b) STILL ON IT: the session has not moved on - it is still acting on that same target or goal
      after the undo/failures.
Note that (a) is satisfied by a SINGLE undone attempt. Needing something rolled back means that
attempt made things WORSE, not merely that it did not work, and the moment to stop is BEFORE the
next attempt at the same target - not after a second one has already been made.

These are NOT repeating_failure:
  - A RECOVERY that is the METHOD rather than damage: `git stash` / `git checkout <old>` to prove
    a test fails against the pre-fix code, then restoring. Nothing went wrong there.
  - A RECOVERY on a target the session has since ABANDONED or finished with.
  - Many errors on DIFFERENT targets, or a single failure that was then fixed.
Repetition with no failure and no undo is at most `repeating_job`, never `repeating_failure`.

Reply with JSON only, no prose, no code fence:
{{"verdict":"<one of none|repeating_job|repeating_failure>",
 "evidence":[<up to 4 ledger index numbers you used>],
 "reason":"<one short sentence>",
 "action":"<what the session should do next, one short sentence>"}}

LEDGER:
{ledger}
"""


def build_prompt(window_text: str) -> str:
    """The full classifier prompt for one ledger window. PURE."""
    return PROMPT.format(ledger=window_text)


_JSON_OBJECT = re.compile(r"\{.*\}", re.S)


def parse_verdict(reply: str) -> dict:
    """Parse a classifier reply into a verdict dict. PURE, never raises.

    Returns `{"verdict": "none", ...}` on anything unparseable: an overwatcher that cannot read
    its own classifier must stay SILENT rather than invent a stop.
    """
    fallback = {"verdict": "none", "evidence": [], "reason": "unparseable", "action": ""}
    match = _JSON_OBJECT.search(reply or "")
    if not match:
        return fallback
    try:
        parsed = json.loads(match.group(0))
    except ValueError:
        return fallback
    if not isinstance(parsed, dict):
        return fallback
    verdict = str(parsed.get("verdict") or "none").strip().lower()
    if verdict not in VERDICTS:
        verdict = "none"
    evidence = parsed.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    return {
        "verdict": verdict,
        "evidence": [e for e in evidence if isinstance(e, (int, str))][:4],
        "reason": str(parsed.get("reason") or "")[:300],
        "action": str(parsed.get("action") or "")[:300],
    }
