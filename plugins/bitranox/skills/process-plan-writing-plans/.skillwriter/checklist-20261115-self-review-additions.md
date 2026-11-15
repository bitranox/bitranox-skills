# checklist - Self-Review additions: time bound, per-task state, run-the-code traps, changelog task

Self-Review gains: item 7 bounds TIME as well as memory (a cap check stops reading once the cap
is passed, tested with a counting generator); item 8 says how to prove it (rebuild each task's
state alone, above all when one file is split across tasks); item 9 lists three ways the run can
check the wrong thing (a per-task battery naming a later task's test, an editable install making
tools import the main checkout's source, the plan file's own fenced blocks never format-checked);
new item 15 requires a changelog task for a user-visible change.

Decisions: d-20261115-1420f291, d-20261115-f7b6150c, d-20261115-3141273e, d-20261115-460de832, d-20261115-e8e35ce5, d-20261115-019bf03e

## RED

- [x] Skill decisions read first: one rejected entry (no fixed numbers in item 7). The time-bound
      addition prescribes a cap-plus-one assertion and no sizes, so it does not reopen it.
- [x] Coverage check on the pre-edit text with an inert quote-back probe (opus): the six questions
      (editable install and import-linter; battery file scope; format-checking the plan file;
      proving a split task alone; time bound on a cap check; who writes the changelog) answered
      NONE for four, the bare item 8 property for the split task (no method), and a loose
      "fold documentation steps into the task" line for the changelog, which the probe itself
      flagged as not naming a changelog.

## GREEN

- [x] Same questions on the edited text, opus and haiku: all six quoted verbatim from the new
      text on both tiers, each with a concrete action.
- [x] Re-probe after the battery wording fix (test functions, not only files), haiku: quoted the
      new sentence and ruled out an arm relying on a test function a later task adds to an
      earlier file.
- [x] GREEN diffed against RED: no baseline result lost (the item 8 property line still stands).

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; all lists recorded and decided.
- [x] Closed: a battery arm relying on a later task's test FUNCTION in an existing file - the
      rule now names test files and test functions.
- [x] Declined: "how to check pytest's own path handling" - the `__file__` probe in the same
      environment is the check; how a project configures pytest's path is the project's.
- [x] Declined: "a changelog task in a three-altitude plan" - the existing rule after item 15
      keeps a milestone past the next checkpoint without tasks; its changelog task comes with the
      milestone that ships the change.
- [x] Declined: "the literal unreleased heading name" - repo convention, not this skill's.
- [x] Declined: "no CPU ceiling" - the item bounds work by items read, which is the measurable
      form; no fixed number, per decision d-20261108-0c4e895e.
- [x] Width, fence and non-ASCII check over the added lines printed nothing; the paragraphs after
      each insertion point read (items 8, 9 and 10 and "If you find issues"), no back-reference
      re-bound; "Three ways" matches its three bullets.
- [x] All decisions recorded with `skill_decisions.py add` (rule entries with anchors).
