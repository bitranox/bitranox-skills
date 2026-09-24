# Skill-writer checklist: meta-context-watcher reading-side trigger (2026-09-24)

Scope: the frontmatter `description` only. The body's "When you are the one READING a handover"
section is unchanged; the description gains the reading trigger it never had, keeps every existing
trigger, and swaps the closing "what is still open" example (moved into the reading clause) for
"clean up the backlog". Tested as a ROUTING change: the question is whether a router judging from
descriptions offers the skill, not whether an agent follows the body.

## RED (old description)

- [x] Router RED: on a fresh 40-prompt handover/backlog set, `classifier_eval.py replay` with the
      recorded wording caught context-watcher on 11 of the 32 turns a blind panel says need it, the
      same in two runs. Reading turns scored 0.10 to 0.44 on it ("read the handover and telkl me the
      open points about the jev project" 0.16, "read handover but dont start anything - just tell me
      whats next inthe todo list" 0.10) and lost to `none_needed`.
- [x] Native RED: two haiku `baseline-probe` routers given a 9-skill listing (the skill renamed
      `session-continuity`, so the installed copy cannot answer for it) chose NONE for 8 of 8
      reading prompts, both runs. Stated reason, verbatim: "None of the available skills cover
      reading files and reporting project status."
- [x] Inherited-coverage check: not applicable to the router arm, whose model never sees this
      machine's CLAUDE.md cascade or memory. The native arm used a renamed skill and a pasted
      listing, so an installed or remembered description cannot supply the answer.

## GREEN (new description, the exact text shipped)

- [x] The candidate text was fixed before the held-out set was built. The shipped field is
      byte-identical to the tested text, checked by comparing the parsed `description` against the
      candidate file: 637 characters, equal.
- [x] Router GREEN, same prompts, alternating runs: 21 of 32 caught in both runs; wrong picks 1 to
      0; picks on prompts needing no skill 1 to 1.
- [x] Native GREEN: 8 of 8 routed to the skill, both runs.
- [x] Labels for the held-out set came from five blind opus judges shown a NEUTRAL summary of what
      the body covers, never either wording, since the wording is the variable under test.

## REFACTOR

- [x] GREEN diffed against RED in both directions. Lost on the held-out set: `tfbpr` on "what next ?
      can we release ?" and `process-review-uncertain-decisions` on one long status turn; the panel
      marked both defensible at most and context-watcher right on the first, so neither is a lost
      correct result. On the training set one real displacement: "read handover and <a hardware
      question>" picked context-watcher where the task skill belonged (1 of 2 runs), because the
      choice arm returns one winner. Accepted: a single-choice router cannot name two skills, and the
      reading turn does want this skill too.
- [x] Noise check on the two earlier labelled sets first failed: picks on needs-no-skill rows rose
      3 to 7 and 8 to 13, every added pick context-watcher on a "read the handover" turn. Those
      panels had judged with the OLD description visible. The 11 disputed rows plus 4 unrelated
      controls went to a fresh blind panel with the neutral summary: 11 of 11 unanimous right, 0 of 4
      controls. Relabelled, the new wording has 0 wrong context-watcher picks on any set.
- [x] DECLINED: extending the description to "what next for <project>" turns (context-watcher under
      0.1 there). The held-out set has now been read, so a further change could only be fitted to
      it; it needs prompts it was not written from.

## Quality checks

- [x] `description` starts "Use when", third person, triggers only, no workflow summary.
- [x] 637 characters, under the 1024 cap (measured with `len()`).
- [x] `skill_triggers.json` and `docs/skills.md` regenerated; the only trigger added is
      `handover.md`.
- [x] No body line, name or other field changed (diff: line 3 only).
- [x] No machine-specific addresses, paths or hostnames added.
