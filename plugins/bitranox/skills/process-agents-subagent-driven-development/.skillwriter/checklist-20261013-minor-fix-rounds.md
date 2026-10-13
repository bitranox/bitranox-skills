# skill-writer checklist - process-agents-subagent-driven-development (no minor-only fix rounds, reach in calibration)

Change: the review loop repeats only while a Critical or Important issue is open. Minors never get
a fix round of their own and a minor-only round is never the recommended option; a project rule
like "accept no technical debt" is met by the ledger and the final review. A Minor that
contradicts a user decision goes to the final review flagged for the user. The ledger records per
review how many Critical/Important/Minor it found and how many Important sit in the previous
round's code, and the controller tells the user when the review feeds on its own output (a report,
not a cap). The task-reviewer template's Calibration judges reach as well as kind: an exotic-only
path (a micro- to millisecond signal or race, input no documented use produces, a platform path
alias) is Minor unless it loses data or opens a security hole, as are a test asserting less than
it could over correct behaviour and doc wording that misleads no caller. Two Rationalizations
rows. Shipped in plugin 8.18.0.

## PLAN

- [x] Skill type: discipline (a review loop) plus a reviewer template. Test approach: controller
      decision scenario, a control where a real Important is open, and a reviewer grading scenario.
- [x] Motivation, from session transcripts: one plan task went through nine reviews and ten fix
      rounds. Fresh reviewers kept finding Ctrl-C and signal windows; the last round fixed four
      Minors alone because the controller recommended it ("the final review starts from a clean
      slate"), and its review reported three more Minors.
- [x] User decision (recorded in the decision log): keep the loop, tighten the gate; no round cap.

## RED

- [x] Contamination: same neutral directory as the code-quality change (cascade assembles 0
      documents), no tools, text pasted into the prompt.
- [x] Controller scenario: Task 10 after 8 reviews and 9 fix rounds, review 8 "Approved with
      minors" (m1-m4, m4 a ~1 ms Ctrl-C window against a user exit-code decision), project rule
      "accept no technical debt", user waiting on Task 11 and picking the recommended option.
- [x] RED, old text: haiku chose FIX ROUND with "(Recommended) Fix m1-m4 in this round", citing the
      CLAUDE.md rule as overriding the skill's "Record Minor". Sonnet chose NEXT TASK. Both reported
      "no cap or escalation" and "skill vs CLAUDE.md: silent on which wins".
- [x] Reviewer scenario (four findings: pre-existing 1 ms SIGINT window, an invalid time accepted
      with exit 0, a test missing an exit-code assertion over correct behaviour, an incomplete
      docstring): both tiers already graded the window Minor and the invalid time Important, but
      both reported guessing ("a stricter reading could argue for Important", "rubric has no line
      for a narrow-window deviation").

## GREEN

- [x] Controller sonnet and haiku: NEXT TASK, quoting "A review with no open Critical or Important
      finding completes the task"; m1-m4 to the ledger, m4 flagged for the user.
- [x] Control (haiku, review 8 also reports an Important invalid-time bug): FIX ROUND for that
      finding only, quoting "Repeat while a Critical or Important issue is open"; it records that
      the Important sits in the previous round's code and tells the user, without stopping.
- [x] Reviewer sonnet and haiku: same grades as RED, now citing the reach sentence instead of
      guessing.
- [x] Diffed against RED both ways: the m4 user flag and the per-finding ledger entries are kept;
      nothing the baseline produced is lost.

## REFACTOR

- [x] Declined, with reasons: how to report a pre-existing defect outside the diff (the template's
      WARN/Issues split predates this change and the reach rule now settles its grade); whether a
      fix round for an Important may also carry Minors (left to the controller; the ledger covers
      them); a round cap (the user declined one).
- [x] Quote-back, haiku, final text: "may the controller recommend a minor-only round" and "does
      accept-no-debt justify one" each answered with a verbatim sentence, none NONE.

## Quality

- [x] ASCII only, present tense, no session narrative, no private hosts or paths, no real project
      names. Tables canonical. Frontmatter unchanged.
- [x] Security scan: prose only.

## Deliverables

- [x] `SKILL.md` and `task-reviewer-prompt.md` edits as listed; no script change. Version 8.18.0,
      `pyproject.toml` matched, CHANGELOG entry.
