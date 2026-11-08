# meta-skill-ab-test: batch of queued improvements

Rules added: the judge is the verdict and the suite count is completeness; per-arm blind judges,
one shared checklist of single-property items, two further judges, a defect hunt per arm. `score`
prints `commits=` and one legend line under the table (test
`test_score_text_names_subagents_ideas_and_the_suite_outcome`, proved to fail on the old code).

Gaps declined:
- A compound item found after the step-3 judges scored, and whether the defect hunt feeds the
  checklist: not settled by the pilot.
- How FIXED, PRESENT, NA and PARTLY combine into one verdict, how an incomplete arm's unwritten
  items score, and who reruns a split item: not settled by the pilot, so the text stays silent.

- [x] Step 0b: `skill_decisions.py show` run for the skill before the first edit; no rejected or
      removed decision is reversed.
- [x] RED: coverage check of the pre-edit text (`git show HEAD:<path>`): every added rule's key term
      has zero hits. A behavioural RED was replaced by this text check because `redcheck
      --corpus-cascade` names the memory store and CLAUDE.md cascade as already teaching these
      lessons (rc 1, STRONG), so an agent on this machine cannot fail honestly.
- [x] GREEN: quote-back with application questions on `opus` (effort medium) and `haiku`, the edited
      text pasted inline, every dispatch ending in a `Skill gaps` section.
- [x] Every gap is closed or declined below; a decline resting on a system claim cites its source.
- [x] After the fix round the same questions were re-run on the final text on both tiers, and no
      new undecided gap appeared.
- [x] Width, fence, backtick and tell checks over the added lines printed nothing. Each list's
      introducing sentence and the paragraph after each insertion point were read.
- [x] Every mechanism claim added was checked against the code it describes.
- [x] No session narrative, private path or history line was added; the history finder's only hit
      ("no longer covering what moved") describes a test's behaviour, not the skill's past.

- [x] Decisions: d-20261108-35635893, d-20261108-25ccefb4
