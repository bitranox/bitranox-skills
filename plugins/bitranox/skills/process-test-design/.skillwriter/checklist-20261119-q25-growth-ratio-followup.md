# skill-writer checklist - process-test-design (2026-11-19, growth-ratio follow-up: order, clocks, faults)

- [x] Change 1: references/silent-test-defeaters.md, growth-ratio point 4 now says which comes
      first: give the cheap negative case an input that drives the costly path (`" " * N` for
      `^\s+x`), sized above the clock's step; the floor plus `small > 0` is only the backstop
      for an arm that is still too fast.
- [x] Change 2: point 1 names `getrusage(RUSAGE_SELF).ru_utime` for POSIX, macOS included (keep
      other threads idle), with the measured Linux misreads of `RUSAGE_THREAD` and
      `os.times().user`; on Windows every CPU-time clock steps 15.625 ms, so arms run hundreds of
      milliseconds, with `perf_counter()` only as the fallback; a clock is checked against a
      busy-loop arm of known length.
- [x] Change 3: point 3 resolves the page-fault/user-time conflict: fault handling is kernel time,
      so a test whose cost IS faulting reads `ru_utime + ru_stime` and gives every arm fresh pages.
- [x] Decisions: d-20261119-7cfa4de2 (supersedes d-20261119-c53688a1), d-20261119-b45d947a
      (supersedes d-20261119-326aca14)
- [x] Step 0b: the two superseded entries were this change's own earlier rules; no rejected or
      removed entry touched.
- [x] Commands executed: clockstep.py shipped to the Windows dev box (Windows 11 26200, Python 3.14.6):
      os.times().user, process_time and thread_time each stepped 0.015625 s; a 2 ms busy arm read
      0.0 in 18 of 20 runs. Linux busy-loop arms: RUSAGE_SELF read 0.1 ms as 0.10-0.11 ms,
      RUSAGE_THREAD 0.0 or about 1 ms, os.times().user 0.0. 256 MiB of fresh mmap pages: 0.086 s
      system, 0.008 s user; a reused buffer 0 faults. `^\s+x` over `" " * N`: 0.06 / 0.42 / 4.3 ms
      user per pass at 50k / 400k / 4M; over `"a" * N` 0.0 in both arms.
- [x] F811 against this repo's own config: no ruff.toml, no `[tool.ruff]` in pyproject.toml and no
      ruff step in CI, so ruff runs on defaults (`--show-settings` printed the default
      `dummy_variable_rgx`); a scratch dir under hooks/tests run without `--isolated` reported the
      plain `helper` redefinition (control) and not the `_helper` one, as the text says.
- [x] GREEN quote-back on opus (effort medium) and haiku against the final text: both quoted
      "First give the case an input that drives the costly path" and named the floor a backstop
      (Q1), RUSAGE_SELF (Q2), longer Windows arms (Q3), `ru_utime + ru_stime` for fault cost (Q4),
      no contradiction (Q5). Their gaps (macOS clock unnamed, Windows default unclear) were closed
      with "macOS included" and "fall back to perf_counter only where". Declined: numeric margins,
      N and k, and the floor's value depend on the code under test; the closing "RED each" line
      predates this change.
