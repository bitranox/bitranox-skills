# skill-writer checklist - compuse-toolbox (2026-11-15, gate.py writes its verdict into --log)

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`); Step 0b `show` run: the
      rejected `ci-wait-verdict-line` and `gate-name-help-text` entries are about other
      sentences; nothing rejected covers the gate log.
- [x] Premise checked, not taken from the queue: the old row already said the verdict lines
      "are printed THERE only, never into `--log`", and agents still polled the log for
      `ALL GATES PASSED` (two queued incidents) - the text described the trap and the trap kept
      firing. `markerwatch.py`'s own docstring example watches `gate.log` for that line. So the
      fix is in the tool, not more text.
- [x] Code: `scripts/gate.py` appends the report to `--log` after printing it (`append_verdict`,
      an OSError becomes a stderr warning) and writes `cwd:` and `repo:` under each
      `##### gate run` header, plus a `cwd:` line under a gate that sets its own cwd.
- [x] RED for the code: `tests/test_gate.py::TestTheLogCarriesTheVerdictAndWhereItRan`, 8 tests,
      failed on the pre-fix script and pass after.
- [x] RED for the text: the pre-edit row tells a reader the log holds no verdict; a reader
      following it cannot use the log as a verdict source and has no way to tell whose log is
      whose (text check, the old row has no `cwd:`/`repo:` line).
- [x] GREEN (new text excerpt, opus and haiku quote-back): both answered "yes, the log gets the
      closing line" and "read the `cwd:`/`repo:` lines", each quoting the new sentences.
- [x] Gaps from GREEN: opus asked whether the log is an equal source to stdout - the row says the
      log receives "the same lines"; declined as covered. The second-exit rule for a dead gate is
      pre-existing text this change does not touch.
- [x] Width and fence check over the added lines printed nothing; table re-run through
      `reformat_tables.py`.
- [x] Description unchanged; no address, MAC, hostname or machine path added; ASCII only.
- [x] Decisions: d-20261115-7eb0de13
