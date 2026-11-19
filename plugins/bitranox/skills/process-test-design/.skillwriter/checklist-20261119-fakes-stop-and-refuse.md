# skill-writer checklist - process-test-design (2026-11-19, fakes honour the stop and refuse what the tool refuses)

- [x] Change 1: SKILL.md, a bullet in the seam-shape list - a hand-written fake of a CLI refuses
      every input the real tool refuses, with the same usage error and exit code; for an owned
      tool the fake calls the tool's validator, or one test runs the real tool on a scratch tree.
- [x] Change 2: references/silent-test-defeaters.md, "Bound every loop" - a fake waiter, poller
      or child process honours the stop condition the real one has, counted in its own polls or
      calls, and answers with the real tool's timed-out result; otherwise the mutant removing the
      code's own stop hangs instead of failing.
- [x] Change 3: same reference, "Pin the environment an output premise depends on" - the
      `setenv` / `delenv` mention and the rich-click "delenv loop" now point at the
      setenv-then-delenv paragraph in the same entry instead of naming `delenv` bare.
- [x] Decisions: d-20261119-3c8f9255, d-20261119-5921bd66
- [x] Step 0b: no rejected or removed entries; no live rule's anchor touched.
- [x] Already covered, not added: "run it ONCE against the real callable" (seam-shape list) is the
      run-the-real-tool half of change 1; the new bullet adds argument values and exit codes.
- [x] RED as a text check: opus (effort medium) and haiku quote-backs against the pre-edit text
      answered NONE for the fake-honours-timeout and fake-refuses-argument-values questions; for
      the removal form both quoted only "(`monkeypatch.setenv` / `delenv`)" and opus proposed
      `delenv(..., raising=False)`, the form the same entry warns against.
- [x] GREEN quote-back on opus (effort medium) and haiku against the edited text: both quoted the
      new sentences and answered `setenv("NO_COLOR", "x")` then `delenv("NO_COLOR")`.
- [x] GREEN gap closed: the count rule versus a `--timeout` (the fake now counts its own polls or
      calls). Round 2 on both tiers quoted it and found no contradiction.
- [x] Declined gaps: how a seconds value maps to a poll count and what the real tool's timed-out
      result looks like (both depend on the tool being faked; read them off the real tool);
      whether to do both the validator call and the real-tool run (either suffices as written).
- [x] Width and fence check over the added lines printed nothing after reflowing the two touched
      paragraphs whole; the bullet after the new SKILL.md bullet and the sentences after each
      reference insertion were read.
- [x] ASCII only, present tense, no private paths or hosts.
