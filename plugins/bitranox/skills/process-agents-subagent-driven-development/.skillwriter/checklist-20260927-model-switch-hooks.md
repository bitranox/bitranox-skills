# skill-writer checklist - process-agents-subagent-driven-development (2026-09-27, model-switch hooks)

"The session model is fixed" said hooks cannot help because only a `SessionStart` hook may see a
`model` field. Upstream Claude Code now has two model-switch hook events, so that clause was stale.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: process/reference paragraph; the change is a factual correction, so the RED is a
      text check against the upstream source, not a pressure scenario.
- [x] RED: SKILL.md:198 read "hooks cannot help (only a `SessionStart` hook may see a `model` field".
      Upstream hooks.md (fetched 2026-09-27): "`PreModelSwitch` and `PostModelSwitch` hooks receive
      `from_model` and `to_model` instead, so use a PostModelSwitch hook to follow the model as it
      changes during a session", and "PreModelSwitch requires Claude Code v2.1.251 or later".
- [x] GREEN: the paragraph now says no hook can make or choose a switch; `SessionStart` may see
      `model` unreliably; `PreModelSwitch` (2.1.251+) can block a REQUESTED switch; `PostModelSwitch`
      sees `from_model`/`to_model` after every change; no hook calls the model. It points at
      `bitranox:meta-claude-hooks` `references/events.md` "Model switches", which exists (`##` heading).
- [x] The conclusion is unchanged and still true: the session agent cannot self-switch, so a
      different tier means a pinned subagent or a user-driven `/model`.
- [x] No other hook-and-model claim in the skill: `grep -i hook | grep -i model` over its Markdown
      finds only this paragraph and the unrelated `subagent-model-gate` line.
- [x] Description unchanged, so no routing keyword moved. ASCII only in the added text; no address,
      hostname or machine path added. Present tense, no session narrative.
