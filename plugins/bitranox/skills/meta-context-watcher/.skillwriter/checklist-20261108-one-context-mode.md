# Checklist 2026-11-08 - one context mode

Change: handover mode is gone, so the watcher always asks for a checkpoint and the session goes
on. "Two modes" became "Checkpoint or handover": a watcher checkpoint (steps 1-6, then 7c) and a
handover the user asks for (steps 1-8). "Compact-mode checkpoint" is now "watcher checkpoint"
throughout. The description loses its "Stop nudge reports the handover threshold" trigger, and
references/when-it-fires.md loses both handover-mode paragraphs. User decision 2026-11-08,
"Purge it".

- [x] Decisions: d-20261108-30fb78a4
- [x] Step 0b: `skill_decisions.py show meta-context-watcher` listed two rules
      (backlog-tool-in-linked-worktree, uncommitted-checkpoint-protection). Neither anchor is in
      the changed text, and neither rule depends on a mode.
- [x] Skill type: a discipline rule inside a technique skill, changed by removing a branch. Tested
      with two application scenarios: a watcher request with a stored `context_mode=handover`, and
      a typed handover request.

## RED

- [x] `redcheck --corpus-cascade` (exit 1) matched the tree-top CLAUDE.local.md and several
      facts only on ordinary words (handover, turn, setting, clear). No fact in the cascade names
      `context_mode`. The answer also leaks from the scenario: the hook text itself says CONTINUE.
      A behavioural RED therefore cannot isolate this change. The removal is checked as text
      instead: a repo-wide grep for `context_mode`, `handover mode` and `compact mode` finds no
      shipped instruction (CHANGELOG history excepted). The remaining hits are the hook docstring
      saying a stored `context_mode` is not read, and the tests that pin that.

## GREEN (new text, text-only probe agent)

- [x] Opus: on the watcher request, saved the checkpoint and went back to the task without
      mentioning `/clear`. It said the stored setting is not a request made in this session. On
      the typed request, it stopped with the `/clear` nudge, and the no-commit exception did not
      apply.
- [x] Haiku: gave the same two answers. It assumed the setting has no effect because the text
      never names it.

## Skill gaps and their disposition

- [x] Closed: "context_mode is never mentioned" and "does a standing setting count as asking?"
      (opus, haiku). Added "No setting changes this." to the checkpoint paragraph; it is the
      ledger anchor.
- [x] Declined, excerpt artefact: steps 1-6, the commit rule and what "the limit" means were cut
      from the probe excerpt. The full skill has them.
- [x] Declined, covered elsewhere: how the Stop-hook request relates to the pre-compaction timing
      is in "When it fires on its own" and references/when-it-fires.md.
- [x] Declined, outside the change: the 7c numbering, and what to do when the next action is
      blocked. Both are unchanged by this edit.

## Mechanical checks

- [x] No line added over 100 columns, no fence left open, no non-ASCII added. Checked with a scan
      of the added diff lines.
- [x] Description still under 1024 characters. `build_skill_triggers.py` output is unchanged,
      and `build_skill_docs.py` rewrote docs/skills.md.
- [x] No version-history wording, no private paths or hosts added.
