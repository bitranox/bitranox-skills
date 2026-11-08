# Review checklist 2026-11-08: one run per run dir, SIGTERM, build_prerequisite_missing (meta-skill-ab-test)

Change: `run` holds an exclusive flock on `<run dir>/run.lock` (pid written in it, `run.lock` in the
run dir's `.gitignore` for new runs) and turns SIGTERM into the Ctrl-C path while it runs; the
floor-step classifier in `scripts/abtrace.py` gains `build_prerequisite_missing` (a build script
that failed for want of protoc), checked before the rustc codes, and `score` classifies the gate
step as well (`floor_gate` in scores.json, `gate=` on the text line). Existing score and result
keys are unchanged; `floor_suite` gains a `prerequisite` key. SKILL.md: the score paragraph gains
the `gate=` and `build_prerequisite_missing` sentences, and "Before and during a live run" gains
one bullet. The description is untouched.

## Claims and their evidence

- [x] Description unchanged (481 characters, measured with `len()` of the YAML field); SKILL.md,
      the scripts, the tests and the new fixture are ASCII only (non-ASCII byte scan printed
      nothing).
- [x] RED, code: on the old `abtest.py` the second `run` on a held run dir went on and failed on
      the first arm's removed worktree (`git rev-list failed rc=128 ... cannot change to
      .../abx-run1-r1-C`), and a finished run left no `run.lock`; the abtrace tests failed with
      `KeyError: 'prerequisite'` and the missing `step_outcome`/`SUITE_PREREQ_MISSING`.
      `mutation_arm.py --revert scripts/abtest.py HEAD` reports KILLED for
      `test_a_second_run_on_a_held_run_dir_is_refused_and_sigterm_ends_the_first_like_ctrl_c`,
      `test_a_run_takes_the_lock_and_frees_it_and_the_sigterm_handler_at_its_end` and
      `test_ctrl_c_still_writes_result_and_journal_then_reraises` (its new lock assertion).
- [x] Mutation batteries (`mutation_arm.py --battery`, baseline green first and last), every arm
      KILLED: no SIGTERM handler, handler not restored, lock taken after the cfg sweep; no
      prerequisite branch, prerequisite without the build-script line, prerequisite without the
      protoc line, prerequisite checked before rc 0, the "failed to invoke protoc" wording dropped
      (survived first, because the NotFound wording also matches the path alternative; a
      PermissionDenied case was added, then killed), gate not classified, describe ignoring the
      prerequisite.
- [x] Executed, not reviewed: a child `abtest.py run` held mid-session, a second in-process `run`
      exits 2 naming `run.lock` and the child's pid with the held arm's cfg intact and no attempt
      set aside; SIGTERM to the child exits 130 with an `interrupted` row, `result.json`
      stop_reason `interrupted`, cfg deleted and the lock free. Full suite with CI's dependency
      set: 374 passed, 1 skipped.
- [x] RED, text: an opus `baseline-probe` given the pre-edit SKILL.md answered NONE to all seven
      questions (lock, signal, protoc in the gate log, plus the four for the next two changes) and
      guessed SIGINT and "probably `does_not_compile` or `failed`" for the protoc case. The two
      later sections were pasted as one-line summaries; the score paragraph and the table were
      verbatim. A first dispatch received no text at all (the prompt carried a literal `$(cat)`):
      VOID, not counted.
- [x] GREEN (opus x1, haiku x1, Q1 to Q3 on the new passages): both quoted the lock sentence for
      Q1, the SIGTERM sentence for Q2 and the `build_prerequisite_missing(protoc)` sentence for Q3.
- [x] Gaps from GREEN, decided:
  - CLOSED: the stale pid in `run.lock` after the run ends (opus, haiku) - "the file keeps the last
    pid: check that pid is still an `abtest.py run` before signalling it".
  - CLOSED: the exit code and how to resume (opus) - "`run` exits 130, and the same command
    resumes with that arm from scratch".
  - CLOSED: pid or process group (opus) - "(the harness ends the session's process group itself)".
  - CLOSED: what "removed" covers (opus) - "its config dir with the credentials copy is deleted".
  - CLOSED: SIGKILL (opus) - "SIGKILL skips the Ctrl-C path; the next `run` deletes the config dir
    it left and sets the attempt aside" (`_sweep_cfgs` and `_set_aside` in `scripts/abtest.py`).
  - CLOSED: what `suite=` shows after a failed gate (opus, haiku) - "a failed gate runs no suite,
    so `suite=-` then" (`run_floor` in `scripts/abscore.py` skips the suite once the gate failed).
  - CLOSED: the matched wordings, precedence over rustc codes, another missing tool (opus, haiku) -
    the three wordings named, "checked before the rustc codes", "Only protoc is recognised;
    another missing tool reads `failed`".
  - DECLINED, probe artifact: "the `does_not_compile(...)` format is garbled" (haiku) - the probe
    was given an excerpt; the full paragraph states the format.
  - DECLINED, judgement left to the reader: whether an arm whose floor never compiled should run
    again (opus) - the fields inform and never void, stated in the same paragraph.
- [x] Re-probe on the revised text (haiku: Q1, Q2, a pid read an hour later, SIGKILL, and a gate
      log with protoc, with libclang instead, and with protoc plus rustc E0425): every answer a
      direct quote ("exits 2 naming that pid", "`run` exits 130", "a failed gate runs no suite, so
      `suite=-` then", "Only protoc is recognised; another missing tool reads `failed`", "checked
      before the rustc codes"). New gaps, decided:
  - CLOSED: "the lock goes with the process" read against "the file keeps the last pid" as a
    contradiction - now "The kernel releases the lock when the process ends, however it ends ...;
    the file itself stays and keeps the last pid".
  - CLOSED: what SIGKILL leaves - "no `result.json` and no journal row for the arm, and under
    `sandbox = "none"` the session may keep running in its own process group; bwrap ends it with
    the run" (`abarm._start` uses `start_new_session=True`; the bwrap base carries
    `--die-with-parent`), and the next `run` "renames the attempt to `<label>.attempt-<k>` and
    runs the arm again from scratch" (`_set_aside` in `scripts/abtest.py`).
  - DECLINED, judgement: how to check that a pid is an `abtest.py run` (`/proc/<pid>/cmdline` or
    an equivalent is the reader's own tool choice).
- [x] Quote-back on the two fixes (haiku, final text, one SIGKILL question in four parts): all four
      parts answered by direct quotes ("no `result.json` and no journal row for the arm", "the
      session may keep running in its own process group", "renames the attempt to
      `<label>.attempt-<k>` and runs the arm again from scratch", "The kernel releases the lock").
      Its leftover gaps are DECLINED as outside what the harness does: how to find and stop an
      orphaned `sandbox = "none"` session after a SIGKILL (the bullet names SIGTERM as the stop;
      the harness keeps no handle on a session whose run was killed), and which lock primitive
      the kernel uses (a reader acts the same either way). Tiers: opus (RED x1, GREEN x1), haiku
      (GREEN x1, re-probe x1, quote-back x2).
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion point ("Do not judge a variant from transcripts", the `--dry-run` bullet) holds no
      back-reference that now binds to the new text.
- [x] Decisions: none - the text documents behaviour this change's code and tests carry; the lock,
      SIGTERM and prerequisite behaviour were set by the task, not chosen in the text.
