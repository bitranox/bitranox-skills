# skill-writer checklist - process-test-design (contribution batch, 15 entries)

- [x] Change: `references/silent-test-defeaters.md` gains 15 rules: a fake clock frozen during a
      read; a FIFO writer thread alive after its write (teardown hang, `O_RDONLY | O_NONBLOCK`
      release); a doctest that echoes an absolute path renders backslashes on Windows; a test
      input computed from the mutated constant; `match=` on the validator's own phrase, never an
      echoed input value; `tests/conftest.py` fixtures never reach `src/` doctests (rootdir
      conftest, `testpaths`, pyright environments, `DoctestItem` fixture probe); porting a
      template's autouse fixtures (AST diff script); new section "Child processes, nested runners
      and shared files" (nested runner inherits `PYTEST_XDIST_WORKER`, concurrent appends tear on
      Windows, put the tool's reason in the assertion message); new section "Tests that must not
      reach the outside, or leak into it" (an autouse `subprocess.Popen` guard raising a
      `BaseException` subclass, the `unshare -rn` audit and its undercount; a self-skipping test
      must decide without touching the resource, dead `DBUS_SESSION_BUS_ADDRESS`; a secrets gate
      test leaking through `--tb=long -vv -l`); under "Gates and guards": same-machine ratio over
      an absolute budget, growth-ratio check (user CPU time, equal windows, fresh mmap), verifying
      a rare-flake fix with a base rate and an amplified interleaved A/B.
- [x] SKILL.md: "Reproducing a flake" gains a short paragraph on verifying the FIX with a routing
      line to the reference; the routing paragraph before "Quick checklist" and the reference's
      own intro list the new triggers; the description's keyword list gains `autouse, conftest,
      doctest` (measured with len(): 686 chars, under 1024; routing change recorded as
      unverified live, per the skill-writer rule, evidence is the text check).
- [x] Receipt: `skill_receipt.py start meta-skill-writer` ran (it was stale-or-missing), the
      editing agent loaded bitranox:meta-skill-writer through the Skill tool first; `end` not run.
- [x] RED as a text check (subagent arms are out of scope for this batch): before the edit,
      `grep -rniEc` over both skill dirs returned 0 hits for each of `BaseException`, `unshare`,
      `get_exec_path`, `tb=long|assertion rewriting`, `DBUS|keyring`, `PYTEST_XDIST_WORKER`,
      `O_APPEND`, `assertion message|assert ok,`, `testpaths`, `DoctestItem`,
      `autouse.*(port|template)`, `base rate`, `pytest-repeat|--count`, `thread_time`,
      `mmap threshold`, `as_posix`, `O_RDONLY`, `echoes? the input`, `computed from the constant`.
      The only `is_alive` hit was the check-then-open entry (a different race), the only `ratio`
      hit the cost-guard calibration entry (no absolute-budget or growth-ratio rule).
- [x] GREEN quote-back by grep on the final text, one hit per rule, e.g.
      "### A self-skipping test must decide without touching the resource",
      "### Assert a same-machine ratio, never an absolute wall-clock budget",
      "Match the VALIDATOR's own phrase for the rule under test, never a number or other piece of
      the input", "**Verifying the FIX of a rare flake is a separate question from finding it.**"
- [x] Every code block executed, not reviewed: the Popen guard extracted from the shipped file ran
      against 9 tests (refuses `ssh` plain, under `timeout`, `env ... nice`, `&&`, `;`,
      `bash -c`, and when the stub is not first on PATH; allows a first-on-PATH stub and an
      unrelated command) on Python 3.15 and 3.10: 9 passed; with the `raise` deleted, 7 failed.
      The doctest probe printed `src/pkg/mod.py::pkg.mod.f []` for a doctest beside a
      `tests/conftest.py` autouse fixture (doctest FAILED, test passed), and both passed once the
      fixture moved to a root conftest; without `testpaths` a root plus a `tests/` conftest
      errored at collection ("import file mismatch"), with it 2 passed. The autouse diff script
      named the missing fixture (exit 1) and reported none for identical files (exit 0).
- [x] Mechanism claims probed: a non-blocking read open released a writer blocked in a FIFO
      `open()`; pydantic quotes `input_value=11` in an `extra_forbidden` refusal and says "less
      than or equal to 10" for the bound; a naive token test printed the planted fake token 8
      times under `--tb=long -vv -l`, the helper-based form 0 times. Arithmetic: (25/26)^2 = 0.92,
      ln(0.1)/ln(25/26) = 58.7, 8 of 8 failures in one arm by chance = 0.5^8 = 0.004.
- [x] Claims carried from the contribution and not re-measured here: the Windows append loss
      counts, the page-fault and kernel-time shares, the 0.507 s and 1.01x/10.7x ratio figures,
      the 8/2800 A/B; each is stated as measured.
- [x] Mirror: `repo-gate.py --mirrors` lists no twin for process-test-design.
- [x] ASCII only in added lines; present tense; no version-history phrasing (finder over the
      added lines: one hit, inside code, not history); no tables added; no private host, repo or
      customer name in the added text (grep of the diff for the source projects' names: none).
