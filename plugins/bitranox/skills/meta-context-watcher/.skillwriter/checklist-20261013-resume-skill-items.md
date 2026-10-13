# skill-writer checklist - meta-context-watcher (resume a skill's procedure by invoking the skill)

Change: one paragraph under "When you are the one READING a handover". An item that continues a
skill's procedure (a review sweep, a plan being executed) is resumed by invoking that skill again,
and where the item's wording and the skill's current text disagree, the skill wins. When writing
such an item, name the skill and record where the work stands, never restate its rules. Shipped
in plugin 8.18.0.

## PLAN

- [x] Skill type: discipline (a resume rule). Test approach: a "what next" scenario whose top
      backlog line paraphrases a skill's exit rule.
- [x] Motivation, from session transcripts: a review's backlog line stated the exit rule as it
      stood the day it was written. Later sessions resumed with "what next" from that line, quoted
      its rule as the skill's, and ran another sweep, after the skill had changed that rule.

## RED

- [x] Neutral directory (cascade assembles 0 documents), no tools, text pasted into the prompt.
- [x] RED, old text, sonnet and haiku: both named the Skill call before sweeping, so the action did
      not flip. The scenario told them the skill might have changed, which TELEGRAPHS the action.
      The governing-rule question did flip: both answered NONE and reported "No rule for which
      source wins" / "the watcher skill does not decide it". The transcripts above are the
      untelegraphed RED for the action.

## GREEN

- [x] Sonnet and haiku: Skill call first, quoting "where the item's wording and the skill's current
      text disagree, the skill wins"; neither applies the backlog line's exit rule.

## REFACTOR

- [x] Declined, with reasons: the arms' other gaps (owning repo unknown, the whole backlog not
      visible, no git in the scratch directory) are artefacts of the scenario, covered by the
      skill's existing reading procedure.

## Quality

- [x] ASCII only, present tense, no session narrative, no private paths or project names.
      Frontmatter unchanged.

## Deliverables

- [x] `SKILL.md` paragraph; version 8.18.0, `pyproject.toml` matched, CHANGELOG entry.
