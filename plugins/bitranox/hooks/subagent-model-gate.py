#!/usr/bin/env python3
"""PreToolUse(Task|Agent) gate: subagents must carry an explicit model tier.

The Agent tool takes a subagent's model from the dispatch's `model`, else from the agent type's
own definition (`model:` in its frontmatter), else from the default - the session's model unless a
default subagent model is configured, which may be a premium tier or a weaker one. Landing on
that default silently defeats per-role model tiering.
bitranox:process-agents-subagent-driven-development ("Concrete tiers") requires pinning the tier
explicitly: `haiku` (purely mechanical work / scan) or `opus` (everything else). Effort is set
per dispatch with the Agent tool's `effort` field when a skill or the user asks (every review
does), or by the agent type / a Workflow `agent()` call.

A REVIEW-shaped dispatch (its description or agent type reads as a judging review: task/final/code
review, skeptic or adversarial lens, verify, adjudication, quote-back, audit, judge panel) must run
on `model: opus` with `effort: medium` (the skill's "Review dispatches" rule). One that does not
warns - or, when the dispatch is also unpinned while a plan is armed, the deny names it too. A
review sent as a `fork` warns (never denies): a fork ignores `model` and `effort`. A RED/GREEN
probe, baseline or pressure arm is the thing under test, not a review, and keeps its own tier;
a fixer or implementer (a description leading with fix/implement/apply/address, or naming a
"review fix round/wave/batch" with no review verb in front) is out of scope and stays silent, and
so is a synthesis (it keeps `xhigh`/`max`) unless a review verb leads its description. A `haiku`
dispatch that reads as a review still warns, since a review mis-tiered to haiku is what the rule
catches; the message tells a mechanical scan that makes no judgment to ignore it.

A dispatch that IS pinned, but to a sonnet model (on the dispatch, or in its agent type's
definition), is warned about at every level and never denied: it satisfies the pin rule, but the
tier mapping excludes sonnet because across a whole job it costs more than opus.

Two enforcement levels for an UNPINNED dispatch:
- Normally: WARN (additionalContext on stdout, exit 0) - some dispatches legitimately inherit
  (a `fork` always inherits by design, and sometimes the session model is genuinely right). The
  warn rides `hookSpecificOutput.additionalContext` (no `permissionDecision`), which reaches the
  model as a system-reminder without blocking the dispatch; exit-0 stderr would not reach it.
- While a PLAN EXECUTION is armed in THIS session (a fresh `plan-execution` receipt written by
  `skill_receipt.py start plan-execution` in the session the event comes from - the
  plan-execution skills arm it at their step 0 and disarm with `skill_receipt.py end
  plan-execution` when the plan completes): DENY the dispatch with a reason, so no plan task runs
  on an unpinned model. Another session's plan never arms it here.

A dispatch counts as pinned when it carries `model`, or when its agent type's definition pins
one (anything but `inherit`). Definitions are resolved from three places, first match wins:
- `<plugin>:<name>` for THIS plugin -> `<plugin root>/agents/*.md`;
- a bare `<name>` -> `<project>/.claude/agents/*.md` (project from CLAUDE_PROJECT_DIR, else the
  event's `cwd`), then `~/.claude/agents/*.md` - a project definition shadows a user one.
Only the top level of each agents dir is read, and a definition is matched by its frontmatter
`name`. Another plugin's `<plugin>:<name>`, and any type found nowhere, is treated as unpinned -
the warn/deny below still applies to it.

Contract: reads a PreToolUse event JSON on stdin. Fail-open: any parse/IO error -> exit 0 (a
broken gate must never wedge a turn). Pure standard library; launched via run-python.sh so it
works on Windows too. ASCII only.
"""
import json
import os
import re
import sys
from pathlib import Path

import skill_receipt

SUBAGENT_TOOLS = {"Task", "Agent"}
PLAN_RECEIPT = "plan-execution"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
# Bounds for reading definitions: an agents dir is a handful of small files, so these only stop a
# pathological directory from making every dispatch slow.
_MAX_DEFINITIONS = 500
_FRONTMATTER_BYTES = 64 * 1024

_TIERS = (
    "Pin the tier per bitranox:process-agents-subagent-driven-development (Concrete tiers): "
    "`haiku` = purely mechanical work (transcription, scan, formatting), `opus` = everything else "
    "(fan-out, bounded judgment, deep reasoning) - the `opus` alias always resolves to the latest "
    "Opus. Effort is set per dispatch with the Agent tool's `effort` field when a skill or the "
    "user asks (every review does), or by the agent type / a Workflow `agent()` call."
)

_SONNET_MESSAGE = (
    "Subagent pinned to a sonnet model. sonnet is not a dispatch tier: across a whole job it costs "
    "more than `opus` (more turns and more reasoning tokens for the same work). " + _TIERS +
    " Re-dispatch with `model: opus`, or `haiku` for purely mechanical work."
)

_WARN_MESSAGE = (
    "Subagent dispatched without an explicit `model`. " + _TIERS +
    " With no `model` on the dispatch and none pinned in the agent type's own definition, the"
    " subagent runs on the default model - the session model unless a default subagent model is"
    " configured, often the priciest - which silently defeats tiering. (Definitions are read from"
    " this plugin's agents/, <project>/.claude/agents and ~/.claude/agents; another plugin's agent"
    " types are not resolved.)"
)

_DENY_MESSAGE = (
    "DENIED: a plan execution is armed (fresh `plan-execution` receipt), and every dispatched "
    "subagent MUST pin `model` - on the dispatch, or in its agent type's own definition. "
    + _TIERS +
    " Re-dispatch with `model` set. When the plan is complete, disarm with "
    "`skill_receipt.py end plan-execution`."
)

# Judging-review vocabulary, matched on the description and agent type only: the prompt carries
# the reviewed text itself, which names these words for reasons of its own. Probe words win:
# a RED/GREEN probe subject is the thing under test and keeps its tier pair.
# RED and GREEN stay case-sensitive so the colour words in ordinary prose do not count.
_REVIEW_RE = re.compile(
    r"\b(re-?review\w*|review\w*|skeptic\w*|adversarial|verif\w*|audit\w*|adjudicat\w*|"
    r"judge\w*|quote-back|red-team\w*|second opinion|cross-check\w*)\b", re.I)
_PROBE_RE = re.compile(r"\b((?i:probe\w*|baseline|pressure)|RED|GREEN)\b")
_PROBE_TYPES = ("baseline-probe", "probe-effort")
_REVIEW_EFFORT = "medium"
# Only the head of the description and agent type is read: a review is named in its first words,
# and several of these patterns backtrack quadratically, so a pathological 50k-character
# description must not cost the turn seconds.
_MAX_LABEL_CHARS = 512
# Fixers and implementers are out of scope: a dispatch whose description LEADS with
# fix/implement/apply/address acts on review findings rather than judging, so the nudge would be
# wrong advice. The verb must be followed by whitespace, so "Fix-wave re-review" stays a review.
# An optional bracket tag ("[29] Fix ...") and an optional "<label>:" prefix of up to 30
# characters ("Task 15: Fix ...") are skipped first.
_LABEL = r"^\W*(?:\[[^\]]{1,30}\]\s*)?(?:[^:]{1,30}:\s*)?"
_FIXER_RE = re.compile(_LABEL + r"(?:fix|implement|apply|address)\s", re.I)
# "Final-review fix round" names the fix round, not a review of it - unless a review verb leads.
_REVIEW_FIX_RE = re.compile(r"\breview\w*[ -]fix(?:es)?\b(?:\s+(?:round|wave|batch)\b|\s*$)",
                            re.I)
_LEADING_REVIEW_RE = re.compile(_LABEL + _REVIEW_RE.pattern, re.I)
# A synthesis merges reviewers' findings into one verdict and keeps `xhigh`/`max` per the skill's
# effort table, so it is not a review - unless a review verb leads ("Review the synthesis draft"
# judges a finished draft). Synthesis words only: "synthetic" and "synthesizer" name no synthesis.
_SYNTHESIS_RE = re.compile(r"\bsynthes(?:[ei]s|i[sz](?:e[sd]?|ing))\b", re.I)
# The jev-judge product name (btx-skill-jev-judge, ai-llm-jev-judge) is not the act of judging.
_PRODUCT_RE = re.compile(r"[\w:-]*jev-judge[\w-]*", re.I)

_REVIEW_MESSAGE = (
    "Review-shaped dispatch: every judging review (task/final/code review, skeptic or adversarial "
    "lens, verify, adjudication, quote-back, audit, judge panel) runs on `model: opus` with "
    "`effort: medium` - the review rule in bitranox:process-agents-subagent-driven-development "
    "\"Review dispatches\". Pass both fields; an omitted effort inherits the session or settings "
    "default, which is often higher. Ignore this if the dispatch is not a review, or is a "
    "`haiku` mechanical scan that makes no judgment.")

_FORK_REVIEW_MESSAGE = (
    "Review-shaped dispatch sent as a `fork`: a fork inherits the parent's model and effort and "
    "ignores `model` and `effort` even when they are passed, so it cannot run the review on opus "
    "at effort medium. Re-dispatch it as a non-fork subagent (e.g. `general-purpose`). "
    + _REVIEW_MESSAGE)


def review_shaped(tool_input):
    """True when the dispatch's description or agent type reads as a judging review - not a
    probe, not a fixer or implementer acting on review findings, not a synthesis, not the
    jev-judge name."""
    agent_type = str(tool_input.get("subagent_type") or "")[:_MAX_LABEL_CHARS].lower()
    if any(p in agent_type for p in _PROBE_TYPES):
        return False
    description = _PRODUCT_RE.sub(
        " ", str(tool_input.get("description") or "")[:_MAX_LABEL_CHARS])
    if _FIXER_RE.match(description):
        return False
    leads_with_review = bool(_LEADING_REVIEW_RE.match(description))
    if _REVIEW_FIX_RE.search(description) and not leads_with_review:
        return False
    if _SYNTHESIS_RE.search(description) and not leads_with_review:
        return False
    label = "%s %s" % (description, agent_type)
    return bool(_REVIEW_RE.search(label)) and not _PROBE_RE.search(label)


def _review_compliant(tool_input, definition_model):
    """A review runs on an opus model (the dispatch's, else its definition's) at effort medium."""
    model = tool_input.get("model")
    effective = model if isinstance(model, str) and model.strip() else definition_model
    effort = str(tool_input.get("effort") or "").strip().lower()
    return isinstance(effective, str) and "opus" in effective.lower() and effort == _REVIEW_EFFORT


def _frontmatter(path):
    """Top-level `key: value` pairs of a Markdown file's leading `---` block (keys lowercased),
    or {} when the file has no closed block. Stdlib only: a hook gets a bare interpreter, so no
    YAML library is available, and these definitions only ever need flat scalar keys."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read(_FRONTMATTER_BYTES)
    except OSError:
        return {}
    # split("\n"), not splitlines(): the latter also breaks on U+2028 and form feed.
    lines = [line.rstrip("\r") for line in text.lstrip("\ufeff").split("\n")]
    if lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if line[:1].isspace() or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.split(" #", 1)[0].strip().strip("'\"").strip()
        fields.setdefault(key.strip().lower(), value)
    return {}                  # never closed: a body that merely starts with ---, not frontmatter


def _definition_in(agents_dir, name):
    """The frontmatter of the definition named `name` in `agents_dir`, or None."""
    try:
        candidates = sorted(Path(agents_dir).glob("*.md"))[:_MAX_DEFINITIONS]
    except OSError:
        return None
    for candidate in candidates:
        fields = _frontmatter(candidate)
        if fields.get("name", "").strip().lower() == name:
            return fields
    return None


def _plugin_name(plugin_root):
    try:
        data = json.loads((Path(plugin_root) / ".claude-plugin" / "plugin.json")
                          .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    name = data.get("name") if isinstance(data, dict) else None
    return name.strip().lower() if isinstance(name, str) else ""


def agent_definition_model(subagent_type, project_dir=None, home=None, plugin_root=PLUGIN_ROOT):
    """The `model:` the agent type's own definition declares, or None when it declares none or no
    definition is found where this gate looks (see the module docstring)."""
    wanted = str(subagent_type or "").strip().lower()
    if not wanted:
        return None
    if ":" in wanted:
        plugin, _, name = wanted.partition(":")
        if not name or plugin != _plugin_name(plugin_root):
            return None
        dirs = [Path(plugin_root) / "agents"]
    else:
        name = wanted
        dirs = []
        if project_dir:
            dirs.append(Path(project_dir) / ".claude" / "agents")
        dirs.append(Path(home if home is not None else Path.home()) / ".claude" / "agents")
    for agents_dir in dirs:
        fields = _definition_in(agents_dir, name)
        if fields is not None:
            # The first definition found is the one the Agent tool uses, so a shadowing project
            # definition with no model decides even when a user one of that name pins one.
            return fields.get("model") or None
    return None


def _pins(model):
    return isinstance(model, str) and bool(model.strip()) and model.strip().lower() != "inherit"


def _is_sonnet(model):
    return isinstance(model, str) and "sonnet" in model.lower()


def _tier_verdict(tool_input, plan_armed, definition_model):
    """The pin and sonnet verdict alone, as (action, message); see assess."""
    model = tool_input.get("model")
    if isinstance(model, str) and model.strip():
        return ("warn", _SONNET_MESSAGE) if _is_sonnet(model) else (None, "")
    if _pins(definition_model):
        # the agent type pins its own model, which the dispatch then uses
        return ("warn", _SONNET_MESSAGE) if _is_sonnet(definition_model) else (None, "")
    if plan_armed:
        return ("deny", _DENY_MESSAGE)
    return ("warn", _WARN_MESSAGE)


def assess(tool_name, tool_input, plan_armed=False, definition_model=None):
    """Pure: return (action, message) with action in {'deny', 'warn', None}.

    A non-fork subagent dispatch with no `model`, whose agent type's definition pins none
    (`definition_model`, resolved by the caller), warns - or denies while a plan execution is
    armed. A dispatch whose effective model (the dispatch's, else the definition's) is a sonnet
    model warns, armed or not. A review-shaped dispatch not on opus at effort medium warns, or
    adds the review advice to the deny it already earned. Everything else passes silently,
    including a tool name that is not a string: testing that against the set would raise, and the
    fail-open wrapper would turn the exception into a lost verdict.
    """
    if not isinstance(tool_name, str) or tool_name not in SUBAGENT_TOOLS:
        return (None, "")
    if not isinstance(tool_input, dict):
        return (None, "")
    subagent_type = str(tool_input.get("subagent_type") or "").strip().lower()
    if subagent_type == "fork":
        # A fork inherits the parent's model and effort and ignores both fields, so the pin rule
        # cannot bind it; only a review sent as one is worth a word, and never a deny.
        return ("warn", _FORK_REVIEW_MESSAGE) if review_shaped(tool_input) else (None, "")
    action, message = _tier_verdict(tool_input, plan_armed, definition_model)
    if not review_shaped(tool_input) or _review_compliant(tool_input, definition_model):
        return (action, message)
    if action == "deny":
        return ("deny", message + " " + _REVIEW_MESSAGE)
    return ("warn", (message + " " if message else "") + _REVIEW_MESSAGE)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        # The EVENT's session: a plan armed in another session must not deny dispatches here.
        plan_armed = skill_receipt.is_fresh(PLAN_RECEIPT, session_id=event.get("session_id"))
    except Exception:  # noqa: BLE001 - receipt trouble must not wedge a turn
        plan_armed = False
    tool_input = event.get("tool_input") or {}
    try:
        definition_model = agent_definition_model(
            tool_input.get("subagent_type") if isinstance(tool_input, dict) else None,
            project_dir=os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd"))
    except Exception:  # noqa: BLE001 - an unreadable definition leaves the dispatch unpinned
        definition_model = None
    action, message = assess(event.get("tool_name"), tool_input, plan_armed, definition_model)
    if action == "deny":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }}) + "\n")
    elif action == "warn":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": "SUBAGENT-MODEL GATE: " + message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken gate must never wedge a turn
        sys.exit(0)
