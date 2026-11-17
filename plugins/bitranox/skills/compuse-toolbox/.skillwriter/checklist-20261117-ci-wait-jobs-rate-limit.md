# skill-writer checklist - compuse-toolbox (2026-11-17, ci_wait closing job list and rate limit)

- [x] Receipt fresh; Step 0b `show --kind rejected,removed --full` run: `ci-wait-verdict-line`
      (rejected, about a CI_RC= line) is not touched; this change prints no fixed verdict line of
      its own and leaves the existing verdict line last and unchanged.
- [x] Premises checked against `scripts/ci_wait.py`: a failed verdict's summary is
      `_named(failed, "conclusion")` (runs, no jobs), and job failures appear only in
      `_job_progress`, for runs still going; a 403 from gh is `GhFailed` and retried for the whole
      `--error-grace`.
- [x] Code: a `failed` wait reads every job of every run once more (`read_run_jobs`) and prints
      them on stderr before the verdict line, failed ones first (`format_run_jobs`); JSON carries
      `data.jobs`. After each failed fetch the loop asks `gh api rate_limit`; core remaining 0 ends
      the wait as `rate-limited`, exit 2, with the reset in local time and UTC. No caller in the
      repo parses ci_wait's output (the hooks only match its command line).
- [x] RED for the code: `TestAFailedWaitNamesEveryJob`, `TestFormatRunJobs`,
      `TestASpentRateLimitEndsTheWait`, `TestRateLimitParsing` in `tests/test_ci_wait.py` fail on the
      pre-fix script (16 failed); the exhausted-limit test counted 11 run listings before, 1 after.
      The verdict-line-unchanged, green-reads-no-extra-jobs and quota-left controls pass on both.
- [x] RED for the text (opus and haiku, pre-edit row): both answered NONE for where the full failed
      list is and for a JSON job field, and read a rate-limit 403 as retried into `error`.
- [x] GREEN (opus and haiku, new row): both quoted the poll-line sentence, the rate-limit sentence
      and the `data.jobs` envelope for the three questions.
- [x] Gaps closed from GREEN: exit code of `failed` (1) and of `error` and timeout (2); the block
      also follows `--fail-on-failed-job`, with an unfinished job shown by status and the header
      showing the run's status; a 403 with requests left keeps the retry; the `data.jobs` shape;
      the block is text mode only; which conclusions count as failed (`failure`, `timed_out`).
- [x] Re-probe on the final text (opus and haiku, five questions) answered each with a quote; a last
      haiku quote-back covered the three fixes made after it.
- [x] Gaps declined: the literal status and conclusion strings are GitHub's own values, not this
      tool's; the error-grace length is in `--help` (`--error-grace`, default 300); job order
      beyond failed-first is the API's order, which `format_run_jobs` keeps.
- [x] Example output in the row (`jobs of run <id> (...): 2 of 16 failed`, `<conclusion>  <job>`)
      matches what the tests read from the real formatter.
- [x] Table re-padded by the formatter only; description unchanged; no address, MAC, hostname or
      machine path added; ASCII only.
- [x] Decisions: d-20261117-70ad17b0, d-20261117-be249de4
