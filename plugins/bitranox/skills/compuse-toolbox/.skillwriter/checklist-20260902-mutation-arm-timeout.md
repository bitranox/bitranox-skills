# skill-writer checklist - compuse-toolbox (2026-09-02, mutation_arm --timeout)

Change: `mutation_arm.py` gains `--timeout`, a `timeout` verdict distinct from `killed`/`survived`,
and a `timeout_s` field in the envelope. The index row and the tool docstring gain the symptom that
sends a reader here.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] The gap is a MEASURED failure of the shipped tool, not a hypothetical. `run_arm` called
      `subprocess.run` with no timeout, so a mutation that makes a test SPIN rather than fail hangs
      the tool. Two such mutations were hit in one sweep against a slot-filling loop whose only
      exit was the token ceiling being mutated out; the arm ran at 97% CPU until killed by hand,
      and killing it skipped the `finally` restore, leaving a mutated file on disk.
- [x] ENHANCED the shipped tool rather than building a local twin. A local `mutcheck` was the
      first plan and was dropped on finding `mutation_arm` already owns mutate/run/restore: two
      copies drift, and this skill's own index records eight tools that drifted exactly that way.
- [x] RED: three tests written first and watched fail. The spin test fails on
      `unrecognized arguments: --timeout`, which is a harness failure rather than the behaviour
      owed, so it was re-run after the flag existed and required to fail on the VERDICT before the
      implementation landed.
- [x] A timeout is its own verdict, never `killed`. Folding it into `killed` would credit the arm
      with catching a mutation it never reached - the same false all-clear `verdict_for` already
      refuses for pytest exit 5. `verdict_for(None) == "timeout"` and `exit_code_for("timeout") == 2`
      are pinned by a test.
- [x] The restore runs when the timeout fires. The copy is taken before the first edit and put back
      in a `finally`, and the test asserts `restored is True` and byte-compares the file after a
      timed-out arm.
- [x] `TimeoutExpired.stdout` is bytes even when the call asked for text, and either stream can be
      None, so the partial output is decoded defensively - a bare concatenation would raise inside
      the timeout handler and lose the verdict.
- [x] A control pins that the bound does not fire during a healthy arm: the same mutation at
      `--timeout 120` still reports `killed`. A bound that can fire on a good arm is not a bound,
      it is a flaky tool.
- [x] RETRIEVAL RED, against the pre-change row: an isolated agent asked about a batch that stalled
      on one spinning mutation found `mutation_arm` but answered that the timeout half is absent -
      "nothing in that row, or anywhere else in the index, mentions a timeout, a deadline, or a way
      to stop/kill a hung arm" - and said it would "just wrap the test invocation in a real timeout
      myself". That is the hand-rolling the row now prevents.
- [x] RETRIEVAL GREEN, against the new row: the same question returned `mutation_arm`, quoted the
      new sentence verbatim, and derived the exit-code contract correctly.
- [x] Both probes were asked for a `Skill gaps` section and both reported the SAME gap: the row did
      not say whether the restore is reached when the arm is killed at the timeout. RED called it
      unverifiable from the text, GREEN called it "an inference, not a quoted guarantee". Closed by
      stating the guarantee in the row and the docstring, then verified by quote-back.
- [x] GREEN diffed against RED in both directions. Nothing the RED probe produced is missing from
      GREEN: RED's correct identification of the tool, its restore-from-copy quote and its reading
      of the exit codes all survive, and GREEN adds the timeout half. RED's `backstop` cross-check
      (correctly declined as alert-only) is absent from GREEN because GREEN no longer needs a
      neighbour - not a lost result.
- [x] Gaps DECLINED, with reasons: recovering a file left mutated by an EXTERNAL kill is out of
      scope (`git restore` handles it, and the timeout removes the usual cause); batch-level
      chaining and resumption across several arms is a different tool - `mutation_arm` is one arm
      per call by design, so that stays a caller's loop.
- [x] Index row registered with the user's own noun ("a mutation can make a test SPIN rather than
      fail", "hangs the whole battery"), not the mechanism, and the usage cell carries a real
      runnable value (`--timeout 90`) because it gets copied verbatim.
- [x] No session narrative, no operator instructions, no scratch paths, no machine-specific
      addresses in the skill or this artifact.
- [x] Full CI-parity gate green (`repo-gate.py --ci`), and re-run after the final row edit.
