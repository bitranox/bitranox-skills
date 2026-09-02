#!/usr/bin/env python3
"""PreToolUse(Bash) guard against claiming success on a gate whose exit status a pipe ate.

The mistake, seen twice in one session on a rule that was already written down twice:

    cargo fmt -- --check 2>&1 | head -20 && echo "FMT-OK"
    cargo clippy -- -D warnings 2>&1 | grep -E "^error" ; git add -A && git commit -m ...

A pipeline's exit status is its LAST element's. Piping a gate into head/grep/tail
throws the gate's status away: `head` succeeds, so the `&&` fires and the `;`
sequences on regardless. The result is a printed "OK" while the gate was red, or a
commit of a red state - and the output scrolling past looks like it was checked.

This blocks exactly that shape and nothing else:
  - the command must run a recognised GATE (cargo/pytest/ruff/pyright/... );
  - that gate must sit in a pipeline where it is NOT the last element, so its
    status is masked;
  - and a LATER statement must claim success (an OK-ish echo) or commit/push.

A pipeline whose status is handled correctly is never blocked: `set -o pipefail`
and any `PIPESTATUS` reference are honoured as the fix and exit clean, as does
running the gate bare (no pipe) or ending the pipeline with the gate itself.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""

import json
import re
import sys

from shell_text import blank_unexpanded_text, mask_data_regions, strip_heredoc_bodies

# Commands whose exit status is a quality verdict worth protecting.
GATE = re.compile(
    r"\b(?:"
    r"cargo\s+(?:fmt|clippy|test|build|check|xtask)"
    r"|pytest|ruff|pyright|mypy|tsc|bandit"
    r"|go\s+(?:test|vet)"
    r"|npm\s+(?:run\s+)?(?:test|lint)"
    r"|dotnet\s+test"
    r"|make\s+\S*(?:test|check|lint)"
    r")\b"
)

# Filters that swallow the upstream status by becoming the pipeline's exit code.
FILTER = re.compile(r"^\s*(?:head|tail|grep|egrep|wc|cut|awk|sed|sort|uniq|tee)\b")

# Statements that assert the gate passed, or act as though it did.
CONSUMER = re.compile(
    r"\bgit\s+(?:commit|push|tag)\b"
    r"|\becho\b[^|;&]*\b(?:OK|PASS|PASSED|GREEN|SUCCESS|CLEAN|ALL\s+GOOD)\b",
    re.IGNORECASE,
)

# The correct handlings - if any is present the author is not making this mistake.
HANDLED = re.compile(r"pipefail|PIPESTATUS")

# A gate whose verdict a BACKGROUND job's completion notice will misreport. Broader than
# GATE: a backgrounded `make push` or `ci_wait` is read for its verdict the same way, and
# neither matches GATE's build-tool vocabulary.
BACKGROUND_GATE = re.compile(
    r"\b(?:"
    r"make\s+\S*(?:test|check|lint|push|release)"
    r"|ci_wait(?:\.py)?"
    r"|gh\s+run\s+watch"
    r")\b"
    r"|" + GATE.pattern
)

# The jig that returns the GATE's own status and can chain the follow-up itself.
JIG = re.compile(r"\bgate\.py\b")


def backgrounded_gate_without_the_jig(command: str, *, background: object) -> str | None:
    """Name the gate in a BACKGROUNDED command that does not go through gate.py.

    A background job's completion is announced as `completed (exit code 0)`, and that code
    belongs to the compound's LAST command, not to the gate inside it. Measured 2026-09-02:
    the safe redirect form was written correctly, the harness said exit code 0, that
    sentence was relayed as "the gate passed", and the log said RC=2 with a failing test.
    The rule against it was already loaded and correctly worded, and an advisory on the
    sibling pipe form was read, quoted and stepped past in the same message - so this is a
    BLOCK. Prose has failed twice; a third wording is not the fix.

    ``background`` is ``tool_input["run_in_background"]`` as it arrives, untyped on purpose.
    Only a literal ``True`` triggers, so a harness that stops sending the field, or sends
    something else, degrades to not firing rather than to blocking every gate. That field is
    DOC-VERIFIED (the hooks page documents it in the Bash ``tool_input`` example) and was not
    probed live here; the conservative reading is the price of that.

    Args:
        command: The pending Bash command.
        background: Whatever the event carried for ``run_in_background``.

    Returns:
        The matched gate text, or ``None`` when nothing should be blocked.
    """
    if background is not True:
        return None
    if JIG.search(command):
        return None
    found = BACKGROUND_GATE.search(command)
    return found.group(0) if found else None

# Split into statements on ; && || and newlines, keeping it simple and syntactic.
SPLIT = re.compile(r"\s*(?:;|&&|\|\||\n)\s*")


# A read of the previous command's status. `$?` after a pipeline is the LAST element's status,
# so a pipe into a truncating filter makes it report the filter, not the command being measured.
_STATUS_READ = re.compile(r"\$\?")


def reads_masked_status(command: str) -> bool:
    """True when a read of `$?` DIRECTLY follows a pipeline into a swallowing filter.

    Orthogonal to :func:`masks_a_gate`, which needs the command to be a RECOGNISED gate before it
    fires. That misses the other half of the same mistake: measuring a command's OWN exit code
    during verification. Measured 2026-08-09 - `tool verify --sid <absent> | tail -5;
    echo "rc=$?"` printed rc=0 while the tool had correctly exited 1, so a working negative
    control read as broken; a passing one would have been recorded as proof. The command being
    measured is arbitrary, so keying on a gate name can never catch it.

    ADJACENCY is the whole precision of this check. `$?` holds the status of the IMMEDIATELY
    preceding command, so only the statement directly after the pipeline can be reading the
    filter's status by mistake; once any other command has run, `$?` is about that one. Without
    this the guard fired on a command that piped one check into `tail` and then ran a SECOND check
    redirected to a file - the correct form it exists to recommend.

    Inert regions are blanked first: writing ABOUT the footgun is not committing it. Heredoc bodies
    were the first such region; escaped `\\$?`, single-quoted strings and `#` comments are the rest,
    and all three false-fired this guard on the day it shipped. A `$?` inside DOUBLE quotes still
    counts, because it genuinely expands there - `echo "rc=$?"` is the exact mistake this catches,
    so prose in double quotes is knowingly left as a false positive rather than lose the real case.
    """
    text = blank_unexpanded_text(strip_heredoc_bodies(command or ""))
    if HANDLED.search(text):
        return False
    statements = [s for s in SPLIT.split(text) if s.strip()]
    for index, statement in enumerate(statements):
        elements = [e for e in statement.split("|") if e.strip()]
        piped = len(elements) >= 2 and any(FILTER.match(e) for e in elements[1:])
        if not piped:
            continue
        following = statements[index + 1] if index + 1 < len(statements) else ""
        if _STATUS_READ.search(following):
            return True
    return False


def masks_a_gate(statement: str) -> bool:
    """True when a gate runs in this pipeline but is not what sets its status.

    The GATE search runs on the statement with quoted regions masked, because a gate NAME inside
    an argument is not a gate being run: `grep -rn "npm test" . | head -20` runs grep. The mask is
    scoped to this search on purpose - `CONSUMER` must still READ quoted text, since the success
    claim it looks for IS a quoted string (`echo "PASS"`), and masking there deletes the evidence.
    """
    if "|" not in statement:
        return False
    # Split on a single '|' that is not part of '||' (already handled by SPLIT).
    elements = [e for e in statement.split("|") if e.strip()]
    if len(elements) < 2:
        return False
    # Length-preserving, so the element split below still lines up with the raw text.
    masked = mask_data_regions(statement)
    masked_elements = [e for e in masked.split("|") if e.strip()]
    if not GATE.search(masked):
        return False
    # If the gate IS the last element, the pipeline's status is the gate's.
    if masked_elements and GATE.search(masked_elements[-1]):
        return False
    # Only a swallowing filter actually masks it.
    return any(FILTER.match(e) for e in elements[1:])


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    # The verification shape, which needs no recognised gate: a pipe into a truncating filter and
    # then a read of `$?`. Advisory rather than a block - measuring an exit code is legitimate
    # work, and the mistake is reading the WRONG one, so the fix is to name the right form.
    if reads_masked_status(cmd):
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                "MASKED EXIT STATUS: this pipes into a truncating filter and then reads `$?`, "
                "which is the FILTER's status, not the command's. Measured: a tool that had "
                "correctly exited 1 reported rc=0 this way, so a working negative control read "
                "as broken - and a passing one would have been recorded as proof. Use "
                "`cmd > out 2>&1; rc=$?` and read the file, or gate.py for a real gate."
            ),
        }}) + "\n")

    # A backgrounded gate that does not go through the jig: the completion notice will report
    # the compound's last command, and that is what gets believed. Checked BEFORE the heredoc
    # strip because the whole command is what runs in the background, body included.
    backgrounded = backgrounded_gate_without_the_jig(
        cmd, background=(data.get("tool_input") or {}).get("run_in_background")
    )
    if backgrounded is not None:
        print("\n".join([
            "BLOCKED: a backgrounded gate whose verdict you will be told wrongly.",
            "",
            f"  gate: {backgrounded}",
            "",
            "The completion notice says `completed (exit code N)`, and N is the LAST command of",
            "the compound - `tail`, `echo`, whatever ended it - never the gate's own. Measured",
            "2026-09-02: the redirect form was written correctly, the notice said exit code 0,",
            "that was relayed as `the gate passed`, and the log said RC=2 with a failing test.",
            "",
            "Run it through the jig, which returns the GATE's status and can chain the action:",
            "  uv run <plugin>/skills/compuse-toolbox/scripts/gate.py \\",
            "      --log /tmp/gate.log --gate '<the gate>' [--then '<the action>']",
            "",
            "Or run it in the FOREGROUND, where the exit status you see is the gate's own.",
        ]), file=sys.stderr)
        return 2

    # A heredoc BODY is stdin data, so a doc that WRITES an example of the footgun is not one.
    # Measured live: that shape blocked a real command while this guard was under investigation.
    cmd = strip_heredoc_bodies(cmd)

    # Fast path: nothing further to protect if no gate runs here.
    if not GATE.search(cmd):
        return 0
    # The author already handles the pipe's status correctly.
    if HANDLED.search(cmd):
        return 0

    statements = SPLIT.split(cmd)
    masked_at = None
    for i, st in enumerate(statements):
        if masked_at is None:
            if masks_a_gate(st):
                masked_at = i
            continue
        if CONSUMER.search(st):
            gate = GATE.search(statements[masked_at])
            msg = [
                "BLOCKED: this claims success on a gate whose exit status the pipe threw away.",
                "",
                f"  gate      : {gate.group(0) if gate else '(gate)'}",
                f"  piped into: {statements[masked_at].strip()[:100]}",
                f"  then      : {st.strip()[:100]}",
                "",
                "A pipeline exits with its LAST element's status, so head/grep/tail succeed even",
                "when the gate failed - the && fires, the ; sequences on, and you print OK or",
                "commit a red state while the real failure scrolls past.",
                "",
                "Fix it one of these ways:",
                "  - run the gate bare and let it set the status:   <gate> || exit 1",
                "  - keep the pipe but check the gate:              ${PIPESTATUS[0]}",
                "  - make the pipe propagate:                       set -o pipefail",
                "  - redirect to a file, then grep it separately:   <gate> > out.log 2>&1 || { grep ... out.log; exit 1; }",
            ]
            print("\n".join(msg), file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
