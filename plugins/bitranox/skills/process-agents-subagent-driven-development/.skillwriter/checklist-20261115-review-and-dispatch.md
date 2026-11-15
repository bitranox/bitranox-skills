# checklist - gate freshness, refused actions, fix remedies, split final review, dispatch wording

Seven additions: the implementer report quotes the gate file's path and modification time and
the controller checks it is newer than BASE before the review; an action refused for a subagent
and handed back goes to the human, never applied on its behalf; a fix's prescribed remedy is
checked against the user's recorded requirements before dispatch; the final whole-branch review
is split by system when the branch touches several external systems; a requirement a dispatch
adds from a source document is quoted verbatim with its section; a test a dispatch requires names
the mutant it must kill, not its shape; a fix round that adds something a later task must carry
is written into that task's plan section at once.

Decisions: d-20261115-a6dc7e8b, d-20261115-2a9080b7, d-20261115-a7014084, d-20261115-ef57a3d3, d-20261115-8be03fd2, d-20261115-6be51388, d-20261115-f3928582

## RED

- [x] Skill decisions read first: two rejected entries (headless plan-text routing); none of the
      additions touches that routing.
- [x] Coverage check on the pre-edit SKILL.md and implementer-prompt.md with an inert quote-back
      probe (opus): gate freshness, wiring-test wording, split final review, fix remedy against
      the user's requirements and the refused patch all answered NONE. The source-document
      question found only the reviewer constraints block (verbatim from Global Constraints, not
      a dispatch's added requirement); the later-task question found only the generic "Amend
      the PLAN" and "forward as short rules" lines, with no trigger for an ADDED requirement.

## GREEN

- [x] Same questions on the edited text, opus and haiku: all seven quoted verbatim from the new
      text on both tiers, each with a concrete action.
- [x] Re-probe after the split-review fix, haiku: quoted the new sentence that every reviewer
      reports DEFECTS and one of them alone takes PLAN CHANGES and the Minor triage.
- [x] GREEN diffed against RED: no baseline result lost; the reviewer-constraints and stale-brief
      lines RED found are unchanged.

## REFACTOR

- [x] Every dispatch asked for a `Skill gaps` section; all lists recorded and decided.
- [x] Closed: split reviewers duplicating PLAN CHANGES and the Minor triage - one reviewer takes
      both; the singular "Dispatch it to a fresh `opus` agent" now points at the split.
- [x] Declined: "which reviewer takes PLAN CHANGES" - any one; the choice changes nothing.
- [x] Declined: "a gate run with no file to stat" - gate.py always writes a log and prints its
      path on a `log:` line (`skills/compuse-toolbox/scripts/gate.py`, `format_report`, and
      `default_log_path` when no `--log` is given).
- [x] Declined: "comparing `stat -c %y` with `git log --format=%ci`" - both print a date, time and
      UTC offset; the comparison is direct.
- [x] Declined: "a ledger line for the later-task requirement" - the plan amendment is the record
      the next brief is generated from; the ledger rule for accepted deviations is unchanged.
- [x] Declined: "the headless branch for a remedy against a user requirement" - it is routed as a
      fix that changes the plan text, and "When No Human Can Answer" already routes those.
- [x] Declined: "a refused action handed back in a headless run" - no default is set here; which
      way an unattended run should go is a user decision this change does not make.
- [x] Width, fence and non-ASCII check over the added lines printed nothing (SKILL.md and
      implementer-prompt.md); the paragraph after each insertion point read, no back-reference
      re-bound; the stale-brief list intro states no count.
- [x] All decisions recorded with `skill_decisions.py add` (rule entries with anchors).
