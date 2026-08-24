# skill-writer checklist - compuse-git (the LAST --sort key is primary)

Change: one Quick-reference row. `git for-each-ref` and `git tag --sort` treat the LAST `--sort` key
as primary, so the natural left-to-right reading of two keys gives the wrong answer, and
`-creatordate` alone ties on same-second tags.

## PLAN

- [x] Skill type: reference table of git mechanics. Test approach: reproduce the behaviour in a
      throwaway repo, then a catalogue-wide coverage check, then a text check of the row.
- [x] Scope: one row appended to the Quick reference table. No frontmatter change.

## RED

- [x] Measured on git 2.53.0 with the fixture that can actually discriminate: `v10.0.0` dated 2020
      and `v2.0.0` dated 2026, the one shape where sort-by-version and sort-by-date disagree.
      `--sort=-creatordate --sort=-v:refname` returned `v10.0.0` first, so VERSION decided it;
      reversing to `--sort=-v:refname --sort=-creatordate` returned `v2.0.0` first, so date decided
      it. Last key is primary, confirmed in both directions.
- [x] The tie half measured separately with three tags forced to one identical timestamp: both
      `-creatordate` and `creatordate` returned them in the same order, ascending refname. So the
      `-` prefix flips only the date comparison, never the tiebreak, and the tiebreak is not
      creation order either. That is more precise than "falls back to alphabetical" and the row says
      so, because a reader who flips the prefix expecting the tie order to flip would be wrong.
- [x] Coverage checked with `claim_check.py` over all 100 `skills/*/SKILL.md` and
      `skills/*/references/*.md`, with three widening patterns (`for-each-ref`;
      `creatordate|v:refname`; a loose sort-a-tag phrasing). All ABSENT, control matched 241 times
      across 100 files, so the negative is trustworthy. The target file was also read in full.

## GREEN

- [x] The row gives the rule, the invocation that reads right, and the invocation that IS right, so
      a reader gets the fix and not only the diagnosis.
- [x] The row names the discriminating fixture shape and warns off the monotonic tag history that
      hides the bug, which is the test that would have caught the original mis-selection.
- [x] Anchor verified unique against the live file and applied by line index, with the file
      re-checked afterwards for row count and for ASCII-only content.

## REFACTOR

- [x] A sibling measurement covering `git merge-tree --write-tree` for this same skill returned
      ALREADY SHIPPED: that coverage has been in this file since 2026-08-22, a day before the pass
      that reported it missing. No second row was added, and the queue entry is dropped rather than
      shipped. The stale absence-claim is the defect there, not the skill.
- [x] Anchored at the end of the table, away from the merge-tree row, so the two in-flight
      measurements on this file could not collide.
- [x] Pure addition: no existing row reworded or removed.

## Quality

- [x] ASCII only, verified over the whole file after applying. Present tense, no session narrative,
      no machine paths.
- [x] Uses real flag and tag literals rather than placeholders, matching the table's existing style.
- [x] Frontmatter untouched.

## Deliverables

- [x] One Quick-reference row in `SKILL.md`, applied. No script, so no `tests/` change.
