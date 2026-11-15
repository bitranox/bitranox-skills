# skill-writer checklist - compuse-toolbox (2026-11-15, ci_wait remote check and --min-attempt)

- [x] Receipt issued; Step 0b `show` run: `ci-wait-verdict-line` (rejected) is about where the
      CI_RC= line lands, not touched here; the live rule d-20261115-2f4b0cfe (where `--ref`
      resolves) keeps its anchor.
- [x] Premise checked: three queued incidents of `--ref` polled against the wrong repository.
      The `--repo DIR` case was already fixed and documented the same day (d-20261115-2f4b0cfe),
      after those incidents; what was left is `--ref` with an `OWNER/NAME` `--repo` from a
      checkout of a different repository, which still ended `no-runs` after the grace period.
      The earlier checklist noted no cross-check existed; the queued entries ask for one.
- [x] Code: `scripts/ci_wait.py` refuses (exit 2, before any poll) when the cwd has remotes and
      none names the `--repo` (segment match, case-insensitive, host checked for HOST/OWNER/NAME);
      a cwd with no remotes, or a failing git, is not refused. `--min-attempt N` reports a run
      whose attempt is below N as `attempt K, waiting for attempt N` (not terminal).
- [x] RED for the code: `TestRefAgainstAnOwnerNameRepo`, `TestNamesRepository`, `TestMinAttempt`
      in `tests/test_ci_wait.py` fail on the pre-fix script; the refusal tests assert the error
      text, since the fake poll's own failure also exits 2.
- [x] RED for the text: the pre-edit row says nothing about a rerun's stale attempt and has no
      way to wait for the new attempt (text check).
- [x] GREEN (opus and haiku quote-back): both answered `--min-attempt <old attempt + 1>` quoting
      the new sentence. Opus answered the OWNER/NAME case as a refusal; haiku could not tell
      whether "remotes all name another repository" meant another than the cwd's or the
      `--repo` - closed by "a repository other than that `--repo`". Both asked where the old
      attempt number comes from - closed with `gh run view <id> --json attempt` (that field
      checked on gh 2.92.0). A pre-existing missing period ("says why) The default") flagged by
      opus is fixed.
- [x] Gaps declined: the cwd-with-no-remotes case is not refused (a scratch repo cannot be judged);
      the row says "all name", which already excludes it.
- [x] Width and fence check over the added lines printed nothing; table re-run through
      `reformat_tables.py`; the no-runs bullet reflowed to the file's width.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261115-d4354ad9
