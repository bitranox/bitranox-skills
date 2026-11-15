# checklist - a rename or removal needs a receipt at the old skill path

One sentence added after the per-directory checklist rule (Step 0): a rename or removal touches
the OLD directory too, so the gate wants a new checklist there, and checklists moved away with the
directory do not count. CONTRIBUTING's "When you add, rename, or remove a skill" gains the same
step.

Decisions: d-20261115-eb3c37ec, d-20261115-0a37a1d3

## RED

- [x] Skill decisions read first: one rejected entry (no narrative history file); untouched.
- [x] Mechanism checked against the gate, not assumed: `repo-gate.py`
      `_skill_mds_shipping_a_change` keeps a staged SKILL.md deletion ("differs too and stays"),
      and `skill_review_failures` counts only checklists the change ships at that skill path;
      `test_a_skill_deleted_in_what_ships_is_still_a_review_case` asserts the refusal.
- [x] Coverage check on the pre-edit receipt paragraph and CONTRIBUTING rename section, inert
      text-only probe, opus and haiku: the old-path checklist and whether moved checklists count
      there answered NONE on both tiers.

## GREEN

- [x] Same question on the edited text (a rename that also rewords two lines), opus and haiku,
      plus a control (a brand-new skill). Both tiers quoted the new sentence and the CONTRIBUTING
      step, placed a `Decisions: none - <reason>` receipt at the old path and a fresh checklist at
      the new one. Control: both asked for a checklist in the new skill only.
- [x] Quote-back: each quote is verbatim from the edited text.
- [x] GREEN diffed against RED: no baseline result lost.

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; all lists recorded and decided.
- [x] Declined: "do moved checklists count at the NEW path" - the paragraph after the edit ("A
      passing gate is not evidence the procedure ran for THIS change") already requires a section
      for the change itself, whatever the gate accepts.
- [x] Declined: "the Decisions line for the new path" - covered under Step 0b, "The checklist names
      them".
- [x] Declined: "what happens to the moved ledger" - covered in the repo CLAUDE.md ("a renamed
      skill answers to its old name's ledger at the fork point").
- [x] A second queued proposal for this skill (a baseline-probe dispatched by a subagent cannot
      hand its report back) was tested instead of written: 12 of 12 probe hand-backs reached the
      dispatching subagent while it kept working, so it is recorded as a `rejected` entry.
- [x] Width and fence check over the added lines printed nothing; the next paragraph read, no
      re-bound reference.
- [x] Decisions recorded with `skill_decisions.py add` (a rule entry with an anchor and a rejected
      entry).
