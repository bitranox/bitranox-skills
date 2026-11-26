# Checklist 2026-11-26 - a failure-modes review ends every plan run

Change: after the final whole-branch review (and its fix round), every run dispatches one more
`opus` reviewer at effort `medium` that follows only the reviewer side of
`bitranox:coding-failure-modes` over the whole branch, from the source design and the whole plan.
The new section "Failure-Modes Review" holds its timing, its brief, why it is separate, how its
findings are routed and that its ratings are checked against the code before a fix. The flowchart,
the overview, "Review dispatches", the gate-disarm sentence, Attended Mode step 5, "Integration"
and the worked example name it. User decision 2026-11-26.

- [x] Decisions: d-20261126-6bfae306, d-20261126-ca7e84a9, d-20261126-23bc938e, d-20261126-0fce9264, d-20261126-95189415
- [x] Step 0b: `skill_decisions.py show ... --kind rejected,removed --full` lists three entries
      (two rejected headless routings, one removed inference from the launch); none is reversed.
      The ledger of `coding-failure-modes` was read too: its entry d-20261126-779f0053 claims no
      detection gain for reviewers from planted single-function cases. The new section claims
      none either; it states one measured case of another kind (a variant spanning tasks, whole
      branch) and that the reviewer's hit rate and cost inside a run are not measured.
- [x] Skill type: technique skill, one added step with a discipline edge (the step may not be
      dropped for cost); test approach: application scenarios with quote-back.

## Probe

Subject: an isolated `claude -p --safe-mode --tools ""` session in a fresh empty directory, the
whole SKILL.md pasted between markers, model asserted from the stream's init record
(claude-haiku-5-5, claude-opus-5-5). Three scenarios, each asking for the dispatches still to
make with model, effort, inputs and brief, a direct quote of the sentence requiring each (or
NONE), and a "Skill gaps" section:

- cheap: a 3-task plan with `haiku` implementers, the partner asks for the cheapest run, the
  final review came back with nothing to fix. Also asks whether a dispatch may be skipped for
  cost, and what happens with each report and its ratings.
- thorough: a 14-task plan over a database and a network service, marked "full automatic", told
  to spare no cost. Also asks which reviewer is last, when and why separate, and what happens
  before a fix when that reviewer rates a finding at its highest severity.
- attended: 6 tasks done in Attended Mode, suite green; what happens until the gate is disarmed.

## RED (pre-edit text)

- [x] cheap, haiku and opus: "Subagents still to dispatch: none", quote NONE.
- [x] thorough, haiku and opus: the final whole-branch reviewers (one per system) and nothing
      after them.
- [x] 4 of 4 cells name no failure-modes reviewer (0 mentions of the term in any answer). The
      rule is a user decision of the same day; a failing RED cannot be a contaminated pass.
- [x] Text test `hooks/tests/test_plan_executor_failure_modes_review_text.py`: every test fails
      on the pre-edit text, all pass on the final text.

## GREEN (final text)

6 cells (3 scenarios, haiku and opus each), all passing:

- [x] cheap, both tiers: one failure-modes reviewer, `opus`, effort `medium`; inputs review
      package, source design, plan at HEAD; brief "When you review the change", all six steps and
      nothing else, table from design and whole plan before the package. Not skippable, quoting
      "No run drops it: not a small plan, not one whose implementers ran on `haiku`, not one asked
      to be cheap". Ratings: quoting "Its rating is a claim until you have checked it against the
      code".
- [x] thorough, both tiers: the split final reviewers, their one fix round, then the
      failure-modes reviewer as the last and single reviewer, with a regenerated package; a
      finding rated High is run or read and re-rated before ONE fix subagent gets the confirmed
      list; a fix that changes the plan text goes through the released-behaviour test of the
      marked run.
- [x] attended, both tiers: the reviewer is dispatched at step 5 before the gate is disarmed, the
      controller checks the ratings, shows confirmed and unconfirmed findings, waits, and makes
      the fixes itself.
- [x] Every blockquoted sentence about the reviewer in the opus cells was checked as a substring
      of the final text (whitespace normalised, bold markers aside) and is absent from the
      pre-edit text.
- [x] Commands the text adds: the path `skills/coding-failure-modes/SKILL.md` exists and its
      section "When you review the change" has six numbered steps (pinned by the text test);
      `review_package.py MERGE_BASE HEAD` is the existing call; the process flowchart renders
      with `dot`.

## REFACTOR

Three probe rounds; the gaps of each round and what became of them:

- [x] Closed: Attended Mode has no final review for the timing sentence to refer to (the section
      hands Attended Mode to its step 5; step 5 says wait as in step 3).
- [x] Closed: an `UNFINISHED:` stop against "no run drops it" (a run that stops before its end
      has not reached the step).
- [x] Closed: gate disarmed before or after the reviewer's fix round (after it).
- [x] Closed: a plan that names no source design (said in the dispatch; the plan is the source).
- [x] Closed: where the table file goes (`mktemp -d` outside the worktree).
- [x] Closed: one reviewer or one per system when the final review was split (one).
- [x] Closed: whether an implementer hands in an author's table (the template asks for none).
- [x] Declined, out of scope of this change (they concern the final review's own fix round, in
      both arms): the fix subagent's tier, a Minor triaged "fix before merge" against "Minors
      never get a fix round", whether a final fix round is re-reviewed.
- [x] Declined, judgement the skill leaves open: whether to tell a cost-minded partner the
      reviewer's cost in advance; in Attended Mode, whether the controller's own fixes carry the
      regression-test rule and whether the suite is re-run (the partner's feedback loop of steps
      3 and 4 governs).
- [x] Declined, covered elsewhere in the skill: a request for the most thorough run does not
      raise a review's tier ("Every dispatch whose job is to JUDGE work or a verdict already
      produced runs on `model: "opus"` with `effort: "medium"`", SKILL.md "Review dispatches");
      a reviewer re-run after a stop it caused ("Dispatch it once per run", "Failure-Modes
      Review").
- [x] Declined, an artifact of the probe: the texts of `coding-failure-modes` and of the prompt
      templates were not pasted.
- [x] GREEN against RED in both directions: every dispatch the RED cells named (the split final
      reviewers, the one fix subagent, no minor-only round) is in the GREEN cells; nothing was
      lost.
- [x] Width and fence check over the added lines: no prose line over 100 columns, no odd
      backtick count. The paragraph after each insertion point was read; the count of pointers to
      "When No Human Can Answer" rose from 4 to 5 and the new one names the mark.
- [x] Description unchanged, so the trigger and docs artifacts regenerate unchanged.
- [x] Cases the edit decides beyond the user's option, each an `argued` ledger entry: the
      reviewer runs after the final review's fix round and is not re-dispatched; Low and
      unconfirmed findings are named, not fixed; Attended Mode dispatches it too.
