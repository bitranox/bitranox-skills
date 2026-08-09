"""A self-declared text-only subagent probe must be enforced by CAPABILITY, not by asking nicely.

Measured: a dispatch whose prompt opened "ANSWER FROM THIS MESSAGE ALONE. Do not use any tools."
went to `general-purpose`, which explored the real tree, rewrote a memory fact, and committed to
two git repos. Separately measured: `Explore` has no Write tool and still created a file with
`echo BREACH > path`, so Bash alone is enough and "read-only agent type" is not write-safe.
"""
import importlib.util
import pathlib

import pytest

_HOOK = pathlib.Path(__file__).resolve().parent.parent / "subagent-probe-capability-gate.py"
_spec = importlib.util.spec_from_file_location("probe_capability_gate", _HOOK)
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def _dispatch(prompt, subagent_type="general-purpose"):
    return {"prompt": prompt, "subagent_type": subagent_type}


TEXT_ONLY_PROMPTS = [
    "ANSWER FROM THIS MESSAGE ALONE. Do not use any tools.",
    "Do not use tools. Reply with text only.",
    "answer from this message alone - nothing here is real",
    "Do NOT read files, run commands, or search anything.",
    "Reply with text only; this is a written exercise.",
]


@pytest.mark.parametrize("prompt", TEXT_ONLY_PROMPTS)
def test_a_text_only_prompt_on_a_tool_capable_type_is_denied(prompt):
    action, message = G.assess("Agent", _dispatch(prompt))
    assert action == "deny", "declaring 'no tools' in prose is exactly what already failed"
    assert "baseline-probe" in message, "the deny must name the safe form, not just refuse"


@pytest.mark.parametrize("atype", ["baseline-probe", "bitranox:baseline-probe", "Bitranox:Baseline-Probe"])
def test_the_inert_agent_type_is_allowed(atype):
    """Plugin agents are addressed namespaced, so both spellings must pass, case-insensitively."""
    for prompt in TEXT_ONLY_PROMPTS:
        action, _ = G.assess("Agent", _dispatch(prompt, subagent_type=atype))
        assert action is None, "the whole point is that the inert type is the way through"


def test_the_shipped_inert_agent_really_excludes_the_dangerous_tools():
    """The guard names a safe form; that form must actually BE safe, or the deny is theatre."""
    agent = (pathlib.Path(__file__).resolve().parent.parent.parent / "agents" / "baseline-probe.md")
    text = agent.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.startswith("tools:")]
    assert lines, "the inert agent must declare a tools list - an ABSENT or EMPTY list means ALL"
    # Compare TOKENS, never substrings: 'Write' is a substring of the harmless 'TodoWrite'.
    granted = {t.strip() for t in lines[0].split(":", 1)[1].split(",") if t.strip()}
    assert granted, "an empty tools list means unrestricted, which is the opposite of inert"
    assert granted.isdisjoint({"Bash", "Write", "Edit", "MultiEdit", "Read", "NotebookEdit",
                               "Agent", "Task"}), f"{granted} would defeat the whole guard"


def test_an_ordinary_dispatch_is_untouched():
    """The negative must be reachable, or the gate blocks normal work."""
    action, _ = G.assess("Agent", _dispatch("Explore the repo and report the test layout."))
    assert action is None
    action, _ = G.assess("Agent", _dispatch("Read src/main.py and summarise it."))
    assert action is None


def test_a_prompt_merely_discussing_tools_is_not_a_declaration():
    """Talking ABOUT tool use must not trip it - that is prose, not a self-declared probe."""
    action, _ = G.assess("Agent", _dispatch(
        "Review this diff. It changes how we do not use tools that write to the store."))
    assert action is None


def test_non_subagent_tools_and_junk_are_ignored():
    assert G.assess("Bash", _dispatch("Do not use any tools.")) == (None, "")
    assert G.assess("Agent", None) == (None, "")
    assert G.assess("Agent", "not a dict") == (None, "")
    assert G.assess(None, None) == (None, "")


def test_explore_is_not_accepted_as_safe():
    """Explore has no Write and still wrote a file via Bash - it is not an inert type."""
    action, _ = G.assess("Agent", _dispatch(TEXT_ONLY_PROMPTS[0], subagent_type="Explore"))
    assert action == "deny"
