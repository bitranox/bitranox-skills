# skill-writer checklist - process-review-enhance-code-quality (collection check, fix-range sweeps, re-sweep dispatch)

- [x] Change: Step 3 Testing - before scoring, compare the files pytest collects from with the test
      files on disk and report every file that collected nothing (a `python_files` pattern with a
      path in it skips every file directly in `tests/`), with a bash block; the aspect checklist's
      Tests row points back at it. Step 7 - each re-sweep dispatches reviewers as Step 3 does
      (`model: "opus"` AND `effort: "medium"`, the synthesis pass keeping its own effort); a
      fix-range sweep settles its batch but never ends the loop. The severity table gained a
      `full / fix-range` column and the workflow diagram branches on full versus fix range.
- [x] Decisions: d-20261117-bfb92441, d-20261117-1906ebdd, d-20261117-7d38d9a9
- [x] Step 0b: the skill had no ledger entries (show printed nothing for both calls).
- [x] Premise verified: a scratch project with `python_files = ["tests/**/test_*.py"]` collected
      `tests/sub/test_deep.py` and not `tests/test_top.py`; with `["test_*.py"]` both.
- [x] Every added command executed: the bash block, extracted verbatim from the edited SKILL.md,
      ran in four arms on that project: path pattern printed `tests/test_top.py` (rc 0); control
      printed nothing (rc 0); zero collected (pytest rc 5) listed every file on disk (rc 0); a
      collection error printed `REFUSE: collection failed (rc=2), see collect.log` (rc 1).
- [x] RED as a text check: an opus quote-back (effort medium) against the pre-edit text answered
      NONE for the collection check and the Step 7 dispatch shape, found no full/fix-range column,
      and could only derive the fix-range case from two separate rules.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: every answer
      quoted the new sentences, the new table header and the block. Round 2 after the fixes below,
      same two tiers, re-asked the touched questions: all quoted, no NONE. Tiers haiku and opus,
      2 rounds, 4 + 4 questions on this skill per tier.
- [x] GREEN gaps closed: the workflow diagram ended the loop on any clean sweep (now branches on
      full versus fix range); Step 7's dispatch line left the synthesis effort open (now says the
      synthesis keeps its Step 3 effort); the Tests checklist row did not prompt the check (now
      does); the block refused a zero-test collection (rc 5 now passes and lists every file); the
      prose said "per directory" for a flat list (reworded) and did not say to run from the
      rootdir or to use the project's own `python_files` patterns in the `find` (now does).
- [x] Declined gaps: `exit 1` closes an interactive shell (the skill's other gate blocks use the
      same refusal form, the commit-time unchained-gate hook requires one); `cut -d:` on a path
      containing a colon (pytest node ids use `::`, a colon in a test file path is outside the
      documented use); the concrete synthesis effort value (owned by
      bitranox:process-agents-subagent-driven-development, pointed at, not copied).
- [x] GREEN diffed against RED both ways: the RED's partial Q2 quotes ("only a full sweep with no
      gate-holding finding ends the loop", "Stop after a full sweep") are still in the text.
- [x] Width and fence check over the added lines: no prose over 100 columns, no split code span,
      every fence closes. The three added diagram lines use the box-drawing and arrow characters
      of the existing diagram. Tables canonical (`reformat_tables.py --check --strict`).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] Present tense, no history lines, no private hosts, paths or personal data.
