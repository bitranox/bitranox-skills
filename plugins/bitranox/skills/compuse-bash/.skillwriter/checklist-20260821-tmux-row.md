# skill-writer checklist - compuse-bash (tmux row and section)

Change: one Quick-reference row and one section for the work a one-shot Bash call cannot do - shell
state across calls, an interactive prompt, a full-screen TUI - plus the two traps that make a
working tmux session look broken.

## PLAN
- [x] Skill type: reference (situation -> rule table with short explanatory sections). The change
      adds a situation the table did not cover at all, not a refinement of one it did.
- [x] Trigger is a real gap, not a hypothetical: the table's fifteen rows all assume a command that
      starts, finishes and returns. Nothing in the skill answers "the program is waiting for input"
      or "the output is a full-screen redraw".
- [x] Checked it is not already shipped: `grep -ci tmux` over the SKILL.md returned 0 before the
      edit. No sibling `compuse-*` skill carries it either.
- [x] Scope: one table row, one section, no script, no new skill.

## RED
- [x] Both documented traps are failure modes I can state precisely because they were measured, not
      guessed: `send-keys` returns before the program is ready or finished, and `capture-pane` pads
      to the pane height so a `tail` of it shows blank lines while the content sits above.
- [x] The RED is the absence itself: with no tmux row, the table's process guidance points at
      `pgrep -f`, which the skill's own process row already warns self-matches the shell running
      the check. A reader looking for "is my session alive" had only the answer the skill forbids.

## GREEN
- [x] Every mechanical claim in the new text executed against real tmux 3.6 before it was written,
      not reviewed: the `tmux wait-for -S` / `timeout N tmux wait-for` pair returned without any
      sleep; a raw `capture-pane -p | tail -3` printed three empty lines while the same capture
      filtered with `grep -c .` counted 16 non-empty ones; `has-session` and
      `list-panes -F '#{pane_current_command}'` both answered without a process scan.
- [x] The code block is complete and runnable as written, not a template with placeholders.
- [x] Table reformatted with the docs-md-table-formatting script, so the row is in canonical form
      and cannot re-dirty the tree on a later hook run.

## Design decisions
- [x] A row AND a section, not just a row. The row is the router - it has to be findable from
      "interactive prompt" or "TUI" - but the two traps need a sentence of mechanism each, and the
      table cell would have become unreadable.
- [x] The barrier is a signal, never a sleep. A `sleep N` after `send-keys` is the obvious-looking
      alternative and it is wrong in both directions: too short and the read races the program, too
      long and every call pays for the worst case.
- [x] Identity via `has-session` / `list-panes`, explicitly NOT `pgrep -f`. The section points back
      at the existing process row rather than restating why, so the two cannot drift apart.
- [x] Not covered, deliberately: attaching interactively, window/pane layout management, and
      sending control characters. They are tmux features, not gaps in what the Bash tool can do,
      and this skill is about the latter.

## Quality
- [x] Token budget: 1178 -> 1493 words. Over the 500-word process-skill target, but this is a
      reference skill whose body IS the table; the addition is one row and one section in a file
      already structured that way.
- [x] ASCII only in the row, the section and this file; verified by byte scan.
- [x] No hostnames, addresses, usernames or private paths - the example uses a generic session name.
- [x] Present tense, no session narrative; the measurements are stated as facts about tmux.

## Deliverables
- [x] SKILL.md: one Quick-reference row, one "When the Bash tool is the wrong shape: tmux" section.
- [x] From the upstream contribution queue; version bumped and CHANGELOG entry added in the same
      change.
