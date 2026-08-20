"""hooks.json matcher invariants.

A hook's matcher decides whether it runs at all, so a matcher defect is invisible in every other
test in this suite: the script under test keeps passing while the shipped hook never fires. These
assertions are about the config, not about any one hook's logic.

The rules encoded here come from the Claude Code hooks reference (see the `meta-claude-hooks`
skill):

* a matcher containing any character outside letters, digits, `_`, `-`, space, `,` and `|` is
  evaluated as an UNANCHORED JavaScript regex, so `Edit.*` also matches `NotebookEdit`. Every
  matcher here is meant to be an exact-match list, so none may leave that character set.
* Claude routes shell commands through the `PowerShell` tool on Windows, so any matcher naming
  `Bash` must name `PowerShell` too.
* a matcher on an event with no matcher support is silently ignored, so those events must not
  carry one and gain a false air of being filtered.
"""

import json
import re
import string
from pathlib import Path

import pytest

HOOKS_JSON = Path(__file__).resolve().parent.parent / "hooks.json"
CONFIG = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]

# The exact-match character set. Anything else switches the matcher to the regex path.
EXACT_MATCH_CHARS = set(string.ascii_letters + string.digits + "_- ,|")

# Events whose matcher filters something other than a tool name.
NON_TOOL_EVENTS = {"SessionStart", "SessionEnd", "PreCompact", "PostCompact",
                   "SubagentStart", "SubagentStop", "Notification", "ConfigChange"}

# Events that accept no matcher at all.
NO_MATCHER_EVENTS = {"UserPromptSubmit", "Stop", "PostToolBatch", "CwdChanged", "TeammateIdle",
                     "TaskCreated", "TaskCompleted", "WorktreeCreate", "WorktreeRemove",
                     "MessageDisplay"}

GROUPS = [(event, group) for event, groups in CONFIG.items() for group in groups]
TOOL_GROUPS = [(e, g) for e, g in GROUPS if e not in NON_TOOL_EVENTS and g.get("matcher")]


@pytest.mark.parametrize("event,group", GROUPS, ids=[f"{e}:{g.get('matcher','')}" for e, g in GROUPS])
def test_no_matcher_silently_becomes_a_regex(event, group):
    stray = set(group.get("matcher", "")) - EXACT_MATCH_CHARS
    assert not stray, (
        f"{event} matcher {group.get('matcher')!r} contains {sorted(stray)}, which makes it an "
        f"UNANCHORED regex rather than an exact-match list"
    )


@pytest.mark.parametrize("event,group", TOOL_GROUPS, ids=[f"{e}:{g['matcher']}" for e, g in TOOL_GROUPS])
def test_bash_is_always_paired_with_powershell(event, group):
    tools = group["matcher"].split("|")
    if "Bash" in tools:
        assert "PowerShell" in tools, (
            f"{event} matcher {group['matcher']!r} names Bash without PowerShell, so these hooks "
            f"never run on a Windows session that routes shell commands through the PowerShell tool"
        )


def test_events_without_matcher_support_do_not_carry_one():
    for event, group in GROUPS:
        if event in NO_MATCHER_EVENTS:
            assert "matcher" not in group, (
                f"{event} has no matcher support; a matcher there is silently ignored"
            )


def test_no_event_repeats_a_matcher_across_groups():
    """Two groups with the same matcher are one group written twice - merge them."""
    for event, groups in CONFIG.items():
        matchers = [g.get("matcher", "") for g in groups]
        assert len(matchers) == len(set(matchers)), f"{event} repeats a matcher: {matchers}"


def test_every_handler_points_at_a_script_that_exists():
    """A missing script exits 127 and reads as a silently disabled gate, not as an error."""
    hooks_dir = HOOKS_JSON.parent
    for event, group in GROUPS:
        for handler in group["hooks"]:
            script = re.search(r"hooks/([\w.-]+\.py)", handler["command"])
            assert script, f"{event}: cannot find a script name in {handler['command']!r}"
            assert (hooks_dir / script.group(1)).is_file(), f"{event}: missing {script.group(1)}"
