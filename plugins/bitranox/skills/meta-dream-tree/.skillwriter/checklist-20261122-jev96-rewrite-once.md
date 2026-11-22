# checklist - Jev shadow sites after the decide rule's rewrite-once branch

The pre-registered decide rule for the Jev shadow sites gives a failing site one rewritten
question, replayed over the logged states, and drops it when it fails again. Applied here:

1. dream-placement (step 5) is dropped: v2 band 52.7%, agreement outside the band 54.0%. Step 5
   loses its shadow bullet, step 0c names two sampled sites instead of three, and `done` owes no
   rows to dream-placement.
2. dream-prune question 2 (`unlabelled_unsolved`) is dropped: its rewrite answered flat. The step-7
   shadow covers questions 1 and 3; the dream still asks question 2 of every fact.
3. dream-prune question 1 (`untestable_negative`) keeps shadowing with its rewritten wording
   (site version 3).

Step 6's shadow bullet now carries the home, launch, procedure and temp-dir details step 5's bullet
held, and step 7 points at step 6.

Decisions: d-20261122-cc62e194, d-20261122-530bc7bd

## RED

- [x] Skill decisions read first (`skill_decisions.py show meta-dream-tree`): no entry concerns the
      Jev shadow steps.
- [x] `test_every_site_a_shipped_doc_runs_has_a_site_file` failed on the pre-edit SKILL.md with
      `{'dream-placement': ['meta-dream-tree', 'meta-dream-tree']}` once the site file was removed.
- [x] New `test_every_verdict_example_names_exactly_its_sites_questions` failed on the pre-edit
      step-7 example: keys `{unlabelled_unsolved, untestable_negative, version_bound}` against the
      site's `{untestable_negative, version_bound}`.

## GREEN

- [x] Both tests pass; meta-self-improve and meta-dream-tree suites 1475 passed.
- [x] Quote-back probe on the edited step 0c, step 6 and step 7 text, opus and haiku (2 cells):
      both quoted the two-site list and the `done` rule, the two-key verdict example, "question 2
      is not shadowed, you still ask it of every fact", and "Act by your own answers, whatever
      `run` printed or exited with." No NONE on any question.

## REFACTOR

- [x] Gap closed: haiku read "both files" in step 6 as unnamed once step 5's bullet, which named
      them, was gone; step 6 now names `items.jsonl` and `verdicts.jsonl`.
- [x] Gaps declined, covered elsewhere in the skill and absent only from the excerpt: `<anchor>`
      (the tree top every step works under, steps 0a and 3) and `<backup dir>` (step 2 creates it
      and names it the dream's working dir), the base of `hooks/run-python.sh` (the
      plugin root, as everywhere in the skill), `status` exit codes (references/jev-shadow.md,
      "The report line").
- [x] Gaps declined, they predate this edit and the edit does not touch them: whether the two
      sites draw the same sample under one seed, the dream id's time zone, which `--jev-skip`
      reasons are acceptable.
- [x] Width and fence check over the added lines: the only hits are code spans that wrap across a
      line, the form the surrounding bullets already use (valid CommonMark).
