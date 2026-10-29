# Model tiers: the effort channels and the fixed session model

Supporting reference for `SKILL.md`, sections "Reasoning effort: the channels and the levels"
and "The session model is fixed". SKILL.md keeps the rules; this file keeps how the harness
behaves underneath them.

## The three effort channels

**Three channels set a subagent's reasoning effort; only the Agent tool's own
field needs an explicit ask.** (1) The Agent tool's own `effort`
field (`low`, `medium`, `high`, `xhigh`, `max`): the tool permits it ONLY when
the user, or instructions such as CLAUDE.md or a skill, explicitly ask that the
agent run at a specific level, never on the dispatcher's own judgment; otherwise
omit it and the agent runs at its usual effort. It is ignored for a `fork`, which
runs at the parent's effort. A skill step that names the effort for a dispatch it
prescribes is such an ask. That restriction is the Agent tool's own and binds
this channel only: for an Agent-tool dispatch the effort table in SKILL.md is not itself an
ask, it says which level fits once one is asked for, while channels (2) and (3)
take the table's level directly. (2) The agent-type definition
(`.claude/agents/*.md` frontmatter, key `effort`; the agent roster is fixed when
the session STARTS, so a definition added mid-session cannot be dispatched until
a NEW session - measured on Claude Code 2.1.250, where a new project agents dir
and a new file in the already-loaded user dir both failed with "Agent type not
found" while definitions present at session start resolved). (3) A Workflow
`agent()` call (`opts.effort`). Probe-verified: the knob swings the same
model's thinking budget by orders of magnitude, so it cuts both ways - set it
only at the EXTREMES and leave everything else at the default (inherit).
Pinning `low` broadly silently degrades tasks that occasionally need depth,
which costs more than the tokens it saves. Reviews are the one exception to
"extremes only": every review carries `medium` (see "Review dispatches").

## Why the session model cannot be switched from inside

The MAIN (session) agent's model is FIXED for the turn and CANNOT be self-switched. There is no
read-your-model or set-your-model primitive exposed to the model, no `$CLAUDE_MODEL` env var, and
no hook can make or choose a switch. Hooks only observe or veto one: `SessionStart` may see `model`
(not reliably), and from CLI 2.1.251 `PreModelSwitch` can block a switch the user or a client
REQUESTED, while `PostModelSwitch` sees `from_model`/`to_model` after every change. No hook calls the
model (see `bitranox:meta-claude-hooks`, `references/events.md` "Model switches").
So the ONLY way to run a sub-task on a different tier is to dispatch a
subagent, which carries its own pinned `model`; inline work necessarily runs on the session model.
"Save the model, switch, switch back" is NOT implementable - never write a skill step that assumes it.
A USER-driven `/model` switch mid-session, however, PRESERVES the conversation (context is not
lost), so offering one is legitimate in BOTH directions: switch UP when the session tier is below
what an inline deep judgment warrants (below opus-class before placement/synthesis), and switch
DOWN for cost when a premium session (fable) faces a long routine stretch - fable is
premium-priced on paid API credits, so parking it on mechanical work burns money for nothing.
Either way it is the USER's call: offer switch-model-or-continue, never demand.
