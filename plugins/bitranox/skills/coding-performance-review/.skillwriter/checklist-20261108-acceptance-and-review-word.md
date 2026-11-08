# Checklist 2026-11-08 - accepted skips and the "review" trigger

Change: the untrusted-structured-input item ends "unless the project has deliberately accepted
skipping it" again; the clause was in the Python skill's checklist and was lost when the
checklist moved here. The description keeps "review": dropping it was checked and rejected.

- [x] Decisions: d-20261108-5c2b46ef, d-20261108-6ab8272b
- [x] Step 0b: `skill_decisions.py show coding-performance-review` listed four earlier entries
      (three-skill-shape, method-and-checklist, description-trigger-words, claim-without-before-
      figure). None is touched: the description is unchanged and the checklist only gains a
      clause.
- [x] Skill type: a discipline item in a technique skill's checklist.

## RED

- [x] The old text is the RED: without the clause the item has no exception, so a recorded
      acceptance would be flagged anyway. `git show 39a4745f` shows the removed Python text
      ending with the clause. `redcheck --corpus-cascade` matched only ordinary words.
- [x] Description: replayed skill-router `match()` over 8,341 typed prompts with the committed
      skill_triggers.json. The skill was nominated 7 times, 5 of them "performance review"
      requests that reach two hits only through "review"; no non-performance prompt.

## GREEN (new text, text-only probe agent)

- [x] Opus and haiku: an internal admin endpoint whose CLAUDE.md records "payload shape
      validation deliberately skipped" is not flagged; both named the recorded acceptance.

## Skill gaps and their disposition

- [x] Declined, outside the change: where an acceptance must be recorded is defined by the
      Python skill's step 1 and the projects' own CLAUDE.md conventions.

## Mechanical checks

- [x] No non-ASCII added, no line over 100 columns.
- [x] Description unchanged; derived artifacts not regenerated.
- [x] No version-history wording, no private paths or hosts added.
