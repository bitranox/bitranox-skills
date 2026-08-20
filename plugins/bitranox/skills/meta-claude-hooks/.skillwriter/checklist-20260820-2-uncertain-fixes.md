# skill-writer checklist - meta-claude-hooks, 2026-08-20 (second change, 5.209.0)

Change: closes three of the four items raised by the decision review on 5.208.0. Item 3 (the
`min_events` / `min_raw_bytes` control thresholds) is deliberately left open.

## What changed and why

- [x] **Per-tool `tool_input` schemas are now documented, not pointed at.** 5.208.0 sent the reader
      upstream for what `tool_input` contains per tool, and that is the highest-traffic path: most
      real hooks match `Bash` or `Edit`. `references/io-contract.md` now carries all 12 schemas,
      the `tool_response` an `Agent` call returns, and the Windows backslash trap - on Windows the
      path arrives with backslashes, so a `/src/` check never matches and the call proceeds exactly
      as if the hook had found nothing to block.
- [x] **The coverage gate is two-tier instead of all-advisory.** Names in the input/output contract
      are blocking; only per-tool example keys remain advisory.
- [x] **The stamped `max_cli_version_mentioned` is now used.** `check` reads the local
      `claude --version`, reports `cli_ahead_of_docs`, and shortens its cache window from seven days
      to one when the CLI is newer than anything the docs mention.

## RED

- [x] **Fix 2 RED is measured, not asserted.** Reproducing the pre-fix semantics (an empty
      `output_fields` set, so every JSON key was advisory) and deleting one real output-contract
      field from the references at a time, coverage reported **complete: True** for all five of
      `updatedToolOutput`, `terminalSequence`, `retry`, `worktreePath` and `displayContent`. After
      the fix, every one of the five is flagged and coverage reports **complete: False**. That is
      the whole point of the item: a newly added `hookSpecificOutput` field could have gone
      undocumented forever without failing anything.
- [x] **Fix 1 RED**: `test_io_contract_documents_every_per_tool_input_schema` fails against the
      5.208.0 file, which contained none of the 12 tool tables.
- [x] **Fix 4 RED**: `max_cli_version_mentioned` was written into the stamp by 5.208.0 and read by
      nothing. The new version tests fail against that code because the functions did not exist.
- [x] Widening a gate is the case where a first-run pass is indistinguishable from a gate that
      asserts nothing, so the control above is kept as a permanent parametrised test rather than a
      one-off check.

## Verification

- [x] 69 tests pass under CI's dependency set, up from 53. The 16 new ones cover the harvest rule,
      section scoping, the gate control, the advisory carve-out, the per-tool documentation, and
      every branch of the version signal.
- [x] `cli_ahead_of_docs` returns **None**, not False, when either side is unknown. Reporting
      "not ahead" for "could not tell" would repeat, in this signal, the not-looked/not-changed
      conflation that the `BROKEN` verdict exists to prevent.
- [x] Version comparison is numeric, not lexical, with a test that would fail on a string compare
      (2.1.240 against 2.1.99).
- [x] The signal is live rather than theoretical: on the authoring machine the CLI is 2.1.237 while
      the stamped docs mention nothing newer than v2.1.234, so `check` prints the note and drops to
      a daily window.
- [x] The version probe cannot break a verdict: no CLI on `PATH`, a non-zero exit, a timeout or
      unparseable output all yield `None`, and `--no-cli-probe` skips it entirely.
- [x] The harvest rule takes a field from a bare identifier, a dotted path
      (`hookSpecificOutput.worktreePath`) and a key-with-value (`retry: true`), and takes nothing
      from a CamelCase event name. Matching identifier-shaped words anywhere in a span was tried
      first and rejected: it fabricated fragments such as `ostToolUse` out of `PostToolUse`, which
      would then have read as undocumented fields forever.
- [x] Both stamps rebuilt, since adding a fingerprint key changes every structural digest. The
      shipped stamp still lists 31 events and 48 gated output-contract names; the fixture stamp
      still drives four distinct selftest verdicts.
- [x] `selftest` still returns CURRENT, COSMETIC, STRUCTURAL and BROKEN over the four fixtures, so
      the fingerprint change did not blunt the detector.
- [x] `coverage` complete: 31 of 31 events, 65 of 65 required names, 12 advisory names reported.
- [x] `baseline --check` in sync; the upstream content hash is unchanged, so this change edits only
      this side.

## Quality and deployment

- [x] No narrative, no operator instructions, no scratch paths. Address and path sweep over the
      shipped files returns nothing.
- [x] ASCII only; the per-tool section uses `/path/to/...` rather than upstream's sample paths.
- [x] Description unchanged, so the router trigger map is unaffected; both derived artifacts
      regenerated and the README count stays 79.
- [x] Security: the new subprocess call runs a `shutil.which`-resolved `claude --version` with an
      argv list, no shell, a timeout, and explicit `encoding="utf-8", errors="replace"` so it cannot
      raise a decode error on either platform.
- [x] `plugins/bitranox/.claude-plugin/plugin.json` bumped 5.208.0 to 5.209.0. A bump is mandatory
      even though 5.208.0 was published minutes earlier: the push consumed that number, so a
      correction under it would reach nobody.

## Deliberately left open

- [x] The `min_events` (60 percent) and `min_raw_bytes` (50 percent) control thresholds are still
      guesses. If upstream genuinely restructures below them the check reports BROKEN, "I could not
      look", when the truth is STRUCTURAL, "the API changed a lot". Nothing settles this until
      upstream restructures, and a wrong absolute floor would be no better, so it stays recorded
      rather than changed.
