# checklist - fan-out hand-offs: renames, edit-stop folds, forwarded items, extensions, typed seams

Four queued contributions. Added: a typed-module / Protocol-view bullet under the partition rules;
two bullets under "Review and Integrate" (an idle notification after an extension can be the first
round's; forwarding open items moves ownership); under "Landing fixer branches by cherry-pick", an
edit-stop fold for a gate that refuses unbumped commits (item 3) and a grep for old names after a
rename (the "Branches green alone can be red together" paragraph).

Decisions: d-20261121-6adc7361, d-20261121-0ac6498c, d-20261121-e9dbb746, d-20261121-17fb3f03

## RED

- [x] Skill decisions read first: one rejected nudge (missing-wait-line), unrelated to all four.
- [x] Route: text check of the skill file (quote-back), since the lessons sit near memory-index
      entries on this machine; a quote must come from the text under test, so inherited context
      cannot produce one.
- [x] Quote-back (opus, pre-edit text from `git show HEAD:`): Q1 rename grep NONE, Q2 fold under a
      bump-only gate NONE, Q3 forwarded items NONE, Q4 extension notification NONE, Q5 Protocol
      views quoted only the general shared-signature bullet (no type-check cross-check).

## GREEN

- [x] Edit-stop fold executed in a scratch repo: `GIT_SEQUENCE_EDITOR` pick->edit, repair, `git
      add`, `git rebase --continue`; the stopped commit's diff held the repair, the later commit
      was unchanged. `git grep -nw <name>` executed (rc 0, hit printed).
- [x] Quote-back (opus medium, haiku): all five quoted from the new text on both tiers.

## REFACTOR

- [x] Gaps from the first GREEN closed: which commit a rename hit folds into (named) and a pointer
      to item 3; the grep command; the timestamp test in the extension bullet replaced by "names
      only first-round work"; where the planted control goes (a copy of the module) and where the
      view copies come from (the named branches).
- [x] Re-probe on the final text (opus medium, haiku): all five quoted on both tiers, 10 cells.
- [x] Declined gaps: tell-vs-stop choice for forwarded items (both remove the second writer; left
      to judgement); no covering report ever arrives (covered by "An agent that stopped mid-task
      left no report"); filtering a grep hit on a common word (reader judgement); whether the
      backup diff applies to an edit-stop fold (the backup rule is scoped to "any step meant to
      change only history"); who resolves a view mismatch (owner and caller, by the partition
      rules above).
- [x] Width/fence check over added lines prints nothing; added lines are ASCII; the paragraph
      after each insertion point read, no re-bound reference.
