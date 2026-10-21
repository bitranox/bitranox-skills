# skill-writer checklist - devops-bmk (2026-10-21, sync-failure-visible)

- [x] Change: section 1, the version-mismatch paragraph. The claim that JSON mode hides the
      provisioning output, with its advice to re-run with `BMK_OUTPUT_FORMAT=text`, is replaced:
      a failed sync prints `[venv] uv sync from uv.lock failed for <venv> (exit <rc>; venv
      afterwards: <state>)` in every output mode, followed in JSON mode by all of uv's stderr,
      indented, and after uv's live output in text mode. The reader reads that line from the run
      that failed; `<state>` says where the gates ran; a `[venv] uv lock failed` line marks the
      `pyproject.toml` fallback; a re-run is only for when no failed run's stderr was kept, with
      stderr sent to a file. The fallback sentence above it now says the gates keep a venv the
      failed sync left behind and use bmk's interpreter only when no real venv is left.
- [x] Every claim checked against bmk source (`adapters/stagerunner/venv.py`): `_report_failed_sync`
      always writes the header to stderr, adds a colon and the SGR-stripped, indented uv stderr
      when quiet (JSON mode), and only the header after live output when not quiet; `_venv_state`
      returns exactly `venv`, `directory without pyvenv.cfg`, `empty directory` or `absent`;
      `_sync_from_lock` prints the `uv lock failed ... from pyproject.toml instead` line
      unconditionally and skips the sync. `context.build_context` pins `VIRTUAL_ENV` at any path
      that still passes `is_venv`, else `PIPAPI_PYTHON_LOCATION` at `sys.executable`, which is why
      `<state>` decides what pip-audit audited. Matches CHANGELOG [3.22.2].
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: `redcheck --corpus-cascade` reported STRONG inherited coverage from the bmk repo's
      own CLAUDE.md, so a behavioural RED could not fail honestly. Replaced by a text check of the
      artifact: the pre-change SKILL.md at HEAD contains "JSON mode hides the provisioning output"
      (1 match), which the code above contradicts.
- [x] GREEN quote-back, first text: haiku and opus, four questions (re-run in text mode, where uv's
      error is, `empty directory`, `venv`). Both answered all four correctly with quotes from the
      pasted text.
- [x] Gaps closed after GREEN: the re-run sentence pulled against "read that run's stderr" (now
      "the stderr of a run that showed it"); stderr not kept (now: send it to a file for an
      unattended run, and re-run only when none was kept); "no venv" against `empty directory`
      (now "no real venv (no `pyvenv.cfg`)"); what bmk's interpreter means for the audit (now:
      pip-audit audited bmk's packages); a mismatch with no sync-failed line (now names the
      `uv lock failed` line).
- [x] Re-probe on the final text, haiku, the touched questions (no stderr kept, text mode, the
      re-run sentences): it re-ran once in JSON mode with stderr to a file, kept JSON mode quoting
      "text mode adds nothing, since the line prints in JSON mode too", and read the conditional
      re-run sentence as the rule for that case. No new undecided gap.
- [x] Gaps declined: the exact redirect syntax (generic shell); remedies for each uv error (uv's
      domain, not bmk's); what "bmk's own interpreter" is (defined in section 1 of the skill, not in
      the excerpt probed); which targets are env-touching (same); causes of a mismatch with no
      `[venv]` line at all (outside this paragraph).
- [x] GREEN diffed against RED both ways: nothing the old text taught is lost except the text-mode
      re-run, which is the claim removed.
- [x] Tiers and cells: haiku x2 (first text, final text), opus x1 (first text).
- [x] Description measured: unchanged (440 characters).
- [x] Mirror: `repo-gate.py --mirrors` reports devops-bmk in sync with the tool repo's copy.
- [x] Security scan: prose only; no secrets, hostnames, private paths or addresses.
