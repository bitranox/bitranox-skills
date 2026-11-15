# Review: sparse multi-label tagging limit and reading a FLAT label (contrib entry)

Change: the "Several labels can apply at once" bullet of Question design names sparse multi-label
tagging (rare labels, abstract meanings) as a weak spot to check against a reference labelling of
50 or more items, with several known positives per label, and gives the measured figures; step 5
says to count a FLAT question's positives in the sample before rewording it.

- Decisions: d-20261115-97d6fc37, d-20261115-cc9338e3
- [x] Step 0b: the skill had no ledger, so no rejected or removed decision applied.
- [x] Corpus check: `redcheck --corpus-cascade` reported "inherited" on term overlap; the named
      documents were opened and none states the multi-label limit or the positive count for a
      FLAT question (the nearest, a text judge cannot see whether a claim was measured, is about
      an absent signal, which step 4 already teaches). The behavioural RED stands.
- [x] Figures recomputed from the pilot's rows and reference labels, controls excluded: threshold
      0.5 gives 38/60 exact sets and 14/24 reference labels found (16 wrong extras); 0.2 gives
      31/60 exact, 19/24 found, 31 wrong extras. The 10 questions `summarize` reported FLAT each
      had 0 or 1 positives in the 65-item reference.
- [x] RED (pre-edit text pasted, opus and haiku, 2 cells): both answered NONE to "does the skill
      say how well Jev fits sparse multi-label tagging"; both checked labels only against the
      10-item pilot's known yes and no; both reasoned their own way to counting positives for a
      FLAT label and reported the text as silent on it ("Step 5's 'shown the items really are
      alike' has no method").
- [x] GREEN (edited text pasted, opus and haiku, 2 cells, plus a control question each): both
      quoted "before relying on it, label 50 or more items for reference" for the reference check
      and "count the items in the run that should be a yes" for the FLAT labels, and both kept the
      control (one noul, 30 percent true) out of the 50-item rule, quoting its sparse scope.
- [x] GREEN against RED: nothing the RED arms produced is missing from GREEN (known yes and no in
      the pilot, the state-signal check for an abstract label, the two-rewrite stop all remain).
- [x] Gap closed: both GREEN tiers said a 50-item random reference holds only 1 to 3 positives per
      rare label; the bullet now says "adding items until each label has several known
      positives". Re-probe on the final bullet (haiku) quoted that clause and refused a 50-item
      sample with three positive-less labels; it also quoted the 0.2 line against lowering the
      threshold.
- [x] Declined: a pass mark for the reference comparison, a named alternative tool, a band for
      rare labels, a number for "several", and how to find extra positives without bias. Each is
      a judgement for the reader or unmeasured; the skill gives the measured yardstick (the model
      reference figures) and leaves the call to the reader.
- [x] Declined: a numeric FLAT spread and a per-question count for the two-rewrite stop. Both
      predate this edit and belong to `summarize` and step 4, not to this entry.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion (step 6, the JSON example) holds no back-reference to the new text.
- [x] History finder over the skill directory: no hits. ASCII only. Description untouched.
- [x] Twin: tool copy regenerated from this one; only the `name:` line differs.
- [x] Floor: the five `uvx --from 'btx-skill-jev-judge>=0.3.8'` lines read `>=0.3.9` in both
      copies, because the tool repo's `test_every_skill_floor_names_the_release_version` requires
      the skill to name the version it is released with (it failed at 0.3.9 with the old floor).
      `JEV_JUDGE_FLOOR` in meta-self-improve/jev_shadow.py follows. 0.3.9 is not on PyPI until the
      tool repo releases it, so this marketplace copy ships only after that release.
