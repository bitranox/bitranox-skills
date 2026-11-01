# skill-writer checklist - coding-python-pwshpy (sweep 5: mapped-drive refusal, timer reads, empty switch values)

- [x] Rule 1 ([390]): `elevate()` and `pwshpy --elevate` on Windows refuse a directory on a `net use` drive before any
      prompt, naming its UNC path (`ElevationDirectoryError`, not a `NativeCallError`; CLI exit 70, the `pwshpy: cannot
      elevate:` line); a local path or that UNC path as `cwd=` goes on; a script file on the drive started from a local
      directory is not refused and returns the child's non-zero code.
      Where: SKILL.md, the error list and the exit codes. Backed by: adapters/native/elevation.py
      (`refuse_a_mapped_drive`), adapters/cli/root.py, tests/test_elevation.py, and real consents on VM 24000 (loopback
      share; a real remote server not measured).
- [x] Rule 2 ([380] [410]): the scheduled-task verbs raise `NativeCallError` when a read of the unit file state, the
      unit or its `ActiveState` fails; the `get_scheduled_task` listing keeps a field's default.
      Where: SKILL.md, the error-model bullet. Backed by: adapters/native/systemd_timers.py (`_info`, `read_state`), the
      fake-bus tests, and the mutating suite on a real systemd (CT 24001).
- [x] Rule 3 ([400]): an empty `-PwshPyUv` / `--pwshpy-uv` is exit 64, like a relative one.
      Where: SKILL.md, the exit codes and the packed-runner paragraph. Backed by: templates/pack_runner.ps1 and
      tests/test_pack_e2e.py.
- [x] Receipt held (skill_receipt.py start meta-skill-writer before the first edit).
- [x] Inherited context: this machine's project instructions can state these rules, so a behavioural RED could pass from
      context. Route taken: a coverage check against the skill FILE, every answer a verbatim quote of the given text or NONE.
- [x] RED, text check on the pre-edit SKILL.md: 0 hits for `ElevationDirectoryError`, `relative or empty` and `unit file
      state`.
- [x] GREEN, opus and haiku, 9 questions, passages as probed: all correct and quoted on both tiers. Gaps closed in the
      text: "raise the same way" now names `NativeCallError`, "(same line)" now names the line; each replaces a referent
      with its own word, so no second round. Declined: `subst` (the text names `net use`; a `subst` drive is simply not
      mentioned, and it is not refused).
- [x] Mirror: regenerated from the pwshpy repo with `git merge-file`; the only divergence is the `name:` line.
