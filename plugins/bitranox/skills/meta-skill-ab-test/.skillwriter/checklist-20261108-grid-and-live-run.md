# skill-writer checklist - meta-skill-ab-test (2026-11-08, grid design and live-run budget)

Two new sections at the end of SKILL.md. "Designing the grid": a verbatim-source arm when the
variants rewrite a source document (built as a `dir` overlay holding the shipped frontmatter and
the document); a `remove_skill` arm is not a dynamic-workflow arm, and the removed skill's name
in other skills' prose is a PREREG confound; a fix round does not converge, so hunt afresh after
every round. "Before and during a live run": `deadline_s` sized from the longest arm and set
before `seal`; a PREREG amendment committed at once; usage windows (weekly cost, two long arms per
5-hour window, a limit notice sets the attempt aside, `run` cannot stop after N arms); a dry run
runs the full floor and is never run beside a live arm. Description unchanged (it already names
pre-registration, PREREG, seal, floor and re-running a paid arm).

Decisions: d-20261108-7cef89c5, d-20261108-7d4404d6, d-20261108-6151b597, d-20261108-7f43aae1, d-20261108-8055e056, d-20261108-bd0eddc2, d-20261108-64aff0c0

- [x] Step 0b `show meta-skill-ab-test --kind rejected,removed --full`: the skill had no ledger.
- [x] RED, text check: the pre-edit skill held none of the seven rules (grep for deadline_s,
      source document, Workflow, rate_limit_event, amendment, fresh hunt, "is not light": 0 each);
      it said "after a clean `--dry-run`" with no cost.
- [x] Claims checked against the scripts: skeleton `deadline_s = 14400` (abprofile.py); the
      login-vs-deadline pause (abtest.py `_login_lapses`, PAUSE_EXPIRY); `_require_seal_intact`
      refuses uncommitted and committed-since-seal changes to abtest.toml, task files, variants/
      and sealed/, and PREREG.md may only grow; `seal` refuses an already sealed run dir; a limit
      notice sets the attempt aside (`_set_aside`); `--only` takes one arm and there is no
      stop-after-N option; a variant `dir` is an overlay replacing skill-relative files
      (abarm.py `_apply_overlay`). Measured figures come from the queue entries' recorded runs.
- [x] GREEN (opus x1, haiku x1; S7, a reorder-only variant, was the control). Both added the
      verbatim-source arm, added a Workflow arm with its own task_file and the PREREG confound,
      set 7200 and committed the amendment, stated the weekly cost and two arms per window,
      refused a dry run beside a live arm, refused to call the 12-to-19 arm converged, and gave
      the control no extra arm.
- [x] Gaps from GREEN, decided:
  - CLOSED: how the verbatim-source arm is built (opus, haiku) - "a `[[variant]]` whose `dir`
    holds a `SKILL.md` made of the shipped frontmatter and that document, unchanged".
  - CLOSED: whether `deadline_s` can change after `seal` (opus, haiku) - "Set it before `seal`
    ... a wrong value then means a new run dir" (read from `_refuse_changed_since_seal`).
  - CLOSED: what the 7 "points" are out of (opus) - "percentage points of the 7-day window's
    utilization".
  - CLOSED: how to hold `run` to two arms per window (opus) - `run` has no such option; "fit the
    grid to the room left in the windows before the user starts it".
  - CLOSED: whether "beside one" covers another run dir (opus, haiku) - "for this run dir or any
    other".
  - DECLINED, judgement: whether the Workflow arm also removes the skill, and whether Vbare stays
    beside it (a design choice per question); an acceptable weekly total (the user's call, which
    is why the cost is stated to them); a positive convergence criterion (none is measured).
  - DECLINED, harness feature, not text: resuming a limit-paused arm instead of setting the
    attempt aside, and a dry mode that skips the floor (entries 51 and 62 offered both as
    options); recorded as open for the harness owner.
- [x] Re-probe on the final text (haiku), with a 3.5-hour-arm control for the deadline rule:
      built the source arm as a frontmatter-plus-document overlay; refused to edit a sealed
      abtest.toml and took a new run dir; with `seven_day` at 80 percent said six long arms
      (about 42 points) do not fit and put shrink-or-wait to the user; refused a dry run beside a
      live arm of another run dir; the control kept the deadline above 3.5 hours, not 7200.
      Remaining gaps (markers for the source arm, a margin above the longest arm, which arms to
      drop) are judgement and were declined.
- [x] Width check: every added line is at most 99 columns; no non-ASCII; each ledger anchor
      occurs once, on one line.
