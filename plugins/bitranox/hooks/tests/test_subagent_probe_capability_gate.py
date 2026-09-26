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
    # Safe is only half of it: the agent must also be SPAWNABLE. An unrecognised tool name is
    # dropped silently, and a list that drops to empty makes the harness refuse the dispatch with
    # "would be spawned with zero tools" - so the guard would deny work and point at a type that
    # cannot run. Shipped exactly that way once (tools: TodoWrite, unrecognised here).
    KNOWN_INERT = {"ReportFindings", "Skill", "ToolSearch"}
    assert granted & KNOWN_INERT, (
        f"{granted} contains no tool name observed in a real agent's tool set; the agent would "
        f"resolve to zero tools and the harness would refuse to spawn it")


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


# --- findings 1, 2 and 8 from the 2026-08-28 script-wave audit of this hook ---------------------

RIGHT_SINGLE_QUOTE = chr(0x2019)


@pytest.mark.parametrize("prompt", [
    "- Do not use any tools.",
    "* Do not use any tools.",
    "1. Do not use any tools.",
    "IMPORTANT: Do not use any tools.",
    "Note: reply with text only.",
    "  - Answer from this prompt alone.",
])
def test_a_declaration_behind_a_bullet_or_label_still_denies(prompt):
    """A declaration still OPENS the line when a list bullet or a short label precedes it. The
    matcher anchored on the raw stripped chunk, so one character of list syntax was enough to let
    through exactly the dispatch this gate exists to deny."""
    action, _ = G.assess("Agent", {"subagent_type": "general-purpose", "prompt": prompt})
    assert action == "deny"


def test_a_typographic_apostrophe_still_denies():
    """`don'?t` covered U+0027 only, so the apostrophe any word processor produces bypassed it."""
    action, _ = G.assess("Agent", {"subagent_type": "general-purpose",
                                   "prompt": f"Don{RIGHT_SINGLE_QUOTE}t use any tools."})
    assert action == "deny"


@pytest.mark.parametrize("prompt", [
    "Do not use any tools other than Read and Grep. Investigate the parser.",
    "Do not use any tools except Read.",
    "Do not use any tools besides Bash.",
    "Do not use any tools apart from Read and Glob.",
])
def test_a_declaration_with_an_exception_clause_is_not_text_only(prompt):
    """It says the opposite: this dispatch DOES need tools, and names them. Denying it points the
    caller at an inert agent type that has none of what the prompt just asked for."""
    action, _ = G.assess("Agent", {"subagent_type": "general-purpose", "prompt": prompt})
    assert action is None


@pytest.mark.parametrize("prompt", [
    "It changes how we do not use tools that reach the network.",
    "The reviewer explained why teams do not use tools like this.",
    "Explain the rule that says do not use any tools during a probe.",
])
def test_prose_that_merely_discusses_tool_use_still_passes(prompt):
    """The direction the widening must NOT reach. A guard that fires on text MENTIONING the
    footgun it guards is the classic failure, and these are the cases the bullet and label
    stripping could plausibly have broken."""
    action, _ = G.assess("Agent", {"subagent_type": "general-purpose", "prompt": prompt})
    assert action is None


def test_the_plain_declaration_still_denies():
    """The case the gate was built for, kept as a permanent control beside every widening."""
    action, _ = G.assess("Agent", {"subagent_type": "general-purpose",
                                   "prompt": "Answer from this prompt alone. Do not use any tools."})
    assert action == "deny"


@pytest.mark.parametrize("prompt", [
    "Instructions for this dispatch: Do not use any tools.",
    "Context you should know before starting: reply with text only.",
    "What I need from you here: answer from this prompt alone.",
])
def test_a_long_label_does_not_escape_the_matcher(prompt):
    """The label prefix carried a 22-character cap picked by hand, and it failed by MISSING - the
    direction nobody notices. A label is a label whatever its length."""
    action, _ = G.assess("Agent", {"subagent_type": "general-purpose", "prompt": prompt})
    assert action == "deny"


def test_an_accepted_cost_of_stripping_any_label_length():
    """The trade this widening makes, recorded as a test rather than left to be rediscovered: a
    sentence whose subject happens to end in a colon now reads as a label, so discussion prose in
    that shape DENIES. That is the loud direction, and the caller can reword; the alternative was
    an arbitrary length silently deciding a security-shaped verdict."""
    action, _ = G.assess("Agent", {"subagent_type": "general-purpose",
                                   "prompt": "The rule we broke last week was: do not use any tools."})
    assert action == "deny"


# --- rank 10 re-adjudication: politeness lead-in, far-off exception word, relative clause, main() -

def _verdict(prompt, subagent_type="general-purpose"):
    return G.assess("Agent", {"subagent_type": subagent_type, "prompt": prompt})[0]


@pytest.mark.parametrize("prompt", [
    "Please answer from this message alone.",
    "Please, do not use any tools.",
    "Kindly reply with text only.",
    "- Please answer from this message alone.",
    "* Please, do not use any tools.",
    "IMPORTANT: Please do not use any tools.",
    "Note: kindly, reply with text only.",
    f"Please don{RIGHT_SINGLE_QUOTE}t use any tools.",
    f"- Please, don{RIGHT_SINGLE_QUOTE}t use any tools.",
])
def test_a_declaration_behind_a_politeness_lead_in_still_denies(prompt):
    """"Please" opens the sentence as surely as a bullet does, and it carries no colon, so the
    label stripping never reached it: the politest spelling of the declaration was the one that
    walked through."""
    assert _verdict(prompt) == "deny"


@pytest.mark.parametrize("prompt", [
    "Please read src/main.py and summarise it.",
    "Please use any tools you need.",
    "- Please use any tools you need.",
    "IMPORTANT: Please use any tools you need.",
    f"Please don{RIGHT_SINGLE_QUOTE}t hesitate to use any tools.",
    "Please explain the rule that says do not use any tools.",
])
def test_a_politeness_lead_in_on_an_ordinary_dispatch_still_passes(prompt):
    """The opposite instruction in the same words, and discussion prose behind the same lead-in,
    must stay untouched: stripping "please" may only expose a declaration, never invent one."""
    assert _verdict(prompt) is None


def test_a_politeness_declaration_on_the_inert_type_passes():
    """The re-dispatch the deny asks for must go through."""
    assert _verdict("Please answer from this message alone.", "bitranox:baseline-probe") is None


@pytest.mark.parametrize("prompt", [
    "Do not use any tools, and write in English except for code identifiers.",
    "Do not use any tools, and keep every answer under 50 words apart from the summary.",
    "- Do not use any tools; write in English except for code identifiers.",
    "Note: do not use any tools, and list nothing besides the verdict.",
    f"Don{RIGHT_SINGLE_QUOTE}t use any tools, and write in English except for code identifiers.",
])
def test_an_exception_word_later_in_the_sentence_does_not_cancel_the_declaration(prompt):
    """An exception grants tools only when it names them, which means it follows "tools"
    directly. Searched over the rest of the sentence, any later "except" turned a genuine
    text-only declaration into an ALLOW - the silent direction."""
    assert _verdict(prompt) == "deny"


@pytest.mark.parametrize("prompt", [
    "Do not use any tools other than Read and Grep.",
    "- Do not use any tools other than Read and Grep.",
    "Note: do not use any tools, except Read.",
    f"Don{RIGHT_SINGLE_QUOTE}t use any tools besides Read.",
])
def test_an_exception_directly_after_tools_still_passes(prompt):
    """The control for the anchoring: the named exception it exists for keeps its allow."""
    assert _verdict(prompt) is None


RESTRICTIONS = [
    "Do not use tools that write to the store. Read and grep are fine.",
    "Do not use tools that modify files.",
    "- Do not use tools which modify files.",
    "IMPORTANT: do not use any tools that write.",
    f"Don{RIGHT_SINGLE_QUOTE}t use tools that modify files.",
]


@pytest.mark.parametrize("prompt", RESTRICTIONS)
def test_a_relative_clause_restriction_denies_with_the_rewording_that_passes(prompt):
    """"tools that <verb>" may be a restriction ("that write") or every tool there is ("that
    touch the filesystem"), and the gate cannot tell which. It denies - the loud direction - but
    it must not send a caller who needs Read to an agent type that has no Read, so this deny names
    the exception spelling instead."""
    action, message = G.assess("Agent", {"subagent_type": "general-purpose", "prompt": prompt})
    assert action == "deny"
    assert "other than" in message, "the deny must name the spelling a Read-needing caller uses"
    assert "Do not simply re-word" not in message, "rewording is exactly the remedy here"


def test_the_rewording_the_restriction_deny_names_actually_passes():
    """A remedy in an error message is untested prose until the route is run."""
    _, message = G.assess("Agent", _dispatch(RESTRICTIONS[1]))
    quoted = message.split('"')[1::2]
    assert len(quoted) == 1 and "other than" in quoted[0], quoted
    assert _verdict(quoted[0]) is None


@pytest.mark.parametrize("prompt", [
    "Use tools that modify files.",
    "- Use tools that modify files.",
    "IMPORTANT: use tools that write.",
])
def test_the_opposite_of_a_restriction_passes(prompt):
    assert _verdict(prompt) is None


def test_a_plain_declaration_keeps_the_probe_deny_beside_a_restriction():
    """A genuine text-only declaration anywhere in the prompt wins over a restriction elsewhere,
    and gets the deny that points at the inert type."""
    action, message = G.assess("Agent", _dispatch(
        "Do not use tools that modify files. Do not use any tools."))
    assert action == "deny"
    assert "bitranox:baseline-probe" in message and "Do not simply re-word" in message
    action, message = G.assess("Agent", _dispatch("Do not use any tools."))
    assert action == "deny" and "Do not simply re-word" in message


def test_main_emits_the_deny_envelope_for_a_text_only_dispatch(monkeypatch, capsys):
    """main() is the only code that turns a verdict into what Claude Code reads. Every other deny
    assertion calls assess(), so a wrong key or event name here would ship green."""
    import io
    import json
    event = {"tool_name": "Agent",
             "tool_input": {"subagent_type": "general-purpose", "prompt": "Do not use any tools."}}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    rc = G.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert out.endswith("\n") and out.count("\n") == 1
    _, expected_reason = G.assess(event["tool_name"], event["tool_input"])
    assert json.loads(out) == {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": expected_reason,
    }}
    assert expected_reason.startswith("TEXT-ONLY PROBE ON A TOOL-CAPABLE AGENT.")
