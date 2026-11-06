# skill-writer checklist - meta-claude-hooks (2026-11-06, the Decisions block's wording matches its form)

Wording fixes so the prose matches the block form it teaches:

- SKILL.md, "Before you write a hook" item 7: "each entry pinned by a test" becomes "each decision
  naming the test that pins it (or why no test can) and each rejected alternative as a
  `- Rejected:` entry" (the form allows `Pinned by: none - <why>`, and a `- Rejected:` bullet has
  no `Pinned by`).
- references/authoring.md, "Record a decision in the module docstring": "that entry's `Rejected:`
  line" and "the `Rejected:` line" become "a `- Rejected:` entry", matching the template's
  separate bullet; "which commit changed it is git's job" becomes "with no history narrative: a
  commit is named only as the source of a reason", matching the shipped blocks that cite a sha as
  a reason's source.

Decisions: none - wording fixes that align the prose with the block form already recorded as d-20261106-259b781f; no rule added, removed or rejected

- [x] Receipt fresh; Step 0b `show meta-claude-hooks --kind rejected,removed --full` printed one
      live entry (d-20261106-a18893ae, a ledger for hooks and jigs); untouched. The anchored
      sentence "Pin each decision with a test that fails when the decision is reverted" is
      unchanged: `skill_decisions.py check` reports 0 findings.
- [x] Not mirrored (`repo-gate.py --mirrors`).
- [x] Each finding verified against the file first (SKILL.md:107, authoring.md:368-375); the
      shipped blocks in `hooks/secret_patterns.py` and `hooks/memory_engine.py` use a separate
      `- Rejected:` bullet and cite shas as sources.
- [x] Re-probe on the final text, haiku x1 (loosening a matcher whose entry's `Reopen if:` is met):
      rewrote the entry, kept the replaced form as a `- Rejected:` entry beside it, refused a
      "changed in commit ... by ..." line quoting "with no history narrative: a commit is named
      only as the source of a reason", and gave the `Pinned by: none - <why>` form. Gaps: whether
      a met-condition `- Rejected:` entry stays (the text says it stays); an untouched decision
      with no entry (only a reversal requires recovery, as stated); placeholders the scenario did
      not supply. No new undecided gap.
- [x] No command added. Width and fence check over the added lines printed nothing; ASCII only;
      history-phrase finder: one hit, "that reason no longer holds", a sentence about a reason,
      not version history.
