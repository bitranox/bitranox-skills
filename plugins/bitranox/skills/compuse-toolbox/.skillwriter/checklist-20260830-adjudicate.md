# skill-writer checklist - compuse-toolbox (`adjudicate`)

Change: a new jig, `adjudicate`, which scores a claim about a guard by running the subject on a
probe AND a control and keeping THREE verdicts rather than two. New script, new tests, one table
row, one rationale bullet, one description trigger.

## PLAN
- [x] Skill type: reference (a tool index with a per-tool rationale).
- [x] Trigger is measured, not hypothetical: the instrument has been hand-rolled three times for one
      job across three sessions, and lost each time. It is what caught two fixes that were green in
      the full suite and had NOT closed the finding they were written for.
- [x] Checked the capability is not already shipped, in the tool AND its neighbours: `diffbehave`
      runs TWO programs on ONE input and asks whether they agree; this runs ONE program on TWO
      inputs and asks whether it discriminates - the inverse shape, and neither substitutes for the
      other. `guard_replay` measures a guard's firing RATE over a real corpus, not whether one
      stated claim holds. `claim_check` answers present/absent for TEXT, and runs no program.
- [x] Scope: one script with eight public functions, 27 tests, one table row, one rationale bullet,
      one description trigger, CHANGELOG, version bump.

## RED
- [x] Tests written first and run before the script existed: 27 failed at COLLECTION with
      `ModuleNotFoundError: No module named 'adjudicate'` - the feature missing, not a typo.
- [x] The three-bucket verdict has a test per bucket plus the asymmetric fourth case
      (`probe_fired=False, control_fired=True` is still REFUTED, because the claim said the probe
      fires). That fourth case is the one a two-bucket implementation gets right by accident.

## GREEN
- [x] 27 passed. Every public function is covered by behaviour, not by an import smoke test:
      `verdict_for`, `fired` (three modes), `subject_for_hook`, `run_once`, `adjudicate`,
      `summarize`, `load_claims`, `main`.
- [x] Verified against the REAL subject it was built for, not only fixtures: driven against the
      shipped `sed-line1-range-nudge.py` with three claims chosen so that each bucket must appear.
      Output was CONFIRMED / REFUTED / UNUSABLE in that order, exit 1.
- [x] The UNUSABLE arm uses a deliberately BROKEN control (both sides a real `sed` range). A
      harness that cannot produce this verdict would have reported it as CONFIRMED, which is the
      failure being designed out.

## REFACTOR
- [x] Exit code carries the lesson rather than the docstring alone: any UNUSABLE claim makes the
      whole run exit 1, so a report cannot be read as all-clear when its controls were broken.
      `ok` is explicitly NOT "the claims were confirmed" - an all-refuted run is a working run.
- [x] The unusable warning goes to stderr on every path including `--json`, so stdout stays a
      parseable envelope. Tested (`test_the_unusable_warning_goes_to_stderr_not_stdout`).
- [x] No command-string splitting anywhere: the subject is built as an argv LIST
      (`subject_for_hook` returns `[sys.executable, path]`). There is nothing to split, so the
      POSIX-vs-Windows quoting class of bug is unreachable rather than handled.
- [x] Declined: a `--subject-argv` for non-hook subjects. No test demanded it and no target needs
      it yet; adding it untested would violate the Iron Law. Recorded here so the next author knows
      it was a decision rather than an oversight.

## Quality
- [x] Description measured with `len()`: 1009 of 1024. Room was made by compressing two existing
      clauses, not by appending onto a full field.
- [x] Table row and rationale bullet added; tables reformatted (`reformat_tables.py`: Unchanged) and
      tell sweep run clean.
- [x] Stdlib only, so the script imports in a bare environment - the contribution gate does not
      provision PEP 723 dependencies.
- [x] No session narrative, no scratch paths, no machine-specific addresses in the script or here.
- [x] `subprocess.run` passes `encoding="utf-8", errors="replace"` - without it Windows decodes in
      a reader thread and returns stdout=None.

## Follow-up (same day, after the decision review)
- [x] The UNUSABLE message named only ONE of its two causes. A chatty subject - one that prints a
      banner on every run - produces the identical verdict under the default `--fired-when output`,
      so the original wording would send a reader to fix a control that was never wrong.
- [x] RED first: 5 tests failed on `unusable_cause` missing. One assertion was rewritten before
      implementing because it was convoluted enough to pass vacuously.
- [x] The two causes are separated by COUNT, not by inspection: every claim unusable means the
      subject fired on every input; some means a control does not discriminate. A lone unusable
      claim still reports against the control - one data point cannot show a pattern.
- [x] Verified against real subjects in both arms, not assertions alone: a banner-printing guard
      gives the subject message, and the shipped `sed-line1-range-nudge.py` with one deliberately
      broken control gives the control message.
- [x] The ADVICE was executed, not just worded: under the default a realistic chatty guard yields
      all-UNUSABLE, and following the printed suggestion (`--fired-when nonzero`) produces real
      verdicts while the broken control correctly stays UNUSABLE.
- [x] The direction where it must NOT apply has its own test: a partial-unusable run still points
      at the control, and it passed BEFORE the change, so it guards against the new branch
      over-firing.
