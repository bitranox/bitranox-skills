# skill-writer checklist - coding-python-pwshpy (sweep 4: dbus_error_name, service read-back, mapped drive)

- [x] Rule 1 ([340]): `.dbus_error_name` holds the error name of a failed D-Bus call and is `None` for any
      other failure; branch on it, never on the message.
      Where: SKILL.md, the error-model bullet. Backed by: src/pwshpy/adapters/native/dbus_errors.py
      (`reply_error`) and domain/errors.py.
- [x] Rule 2 ([350]): the wait and read-back of a Linux service verb, `stop_service(wait=False)` included,
      raise `NativeCallError` when systemd does not answer; only `NoSuchUnit` reads as stopped; the
      `get_service` listing keeps a field's default.
      Where: SKILL.md, the error-model bullet. Backed by: adapters/native/systemd_services.py (`_get_one`),
      systemd_dbus.py (`unit_path`, `live_active_state`, `_live_property`), the fake-bus tests, and the mutating
      suite on a real systemd (CT 24001).
- [x] Rule 3 ([330]): an elevated process does not see a `net use` drive unless `EnableLinkedConnections` is
      set; the runner does not switch to the share; a directory on one: exit 70 naming the UNC path; a runner
      on one: cannot start, the child's own exit code, the parent names the UNC path; the UNC hazards.
      Where: SKILL.md, the packed-runner paragraph. Backed by: templates/pack_runner.ps1
      (`Get-PwshPyMappedUncPath`, the relaunch and its messages), tests/test_pack_e2e.py, and a real UAC consent
      on VM 24000 under Windows PowerShell 5.1 and pwsh 7 (loopback share; a real remote server not measured).
- [x] Receipt held (skill_receipt.py start meta-skill-writer before the first edit).
- [x] Inherited context: this machine's project instructions state `dbus_error_name`, so a behavioural RED could
      pass from context. Route taken: a coverage check against the skill FILE, every answer a verbatim quote of
      the given text or NONE.
- [x] RED, text check on the pre-edit SKILL.md: 0 hits for `dbus_error_name`, for `EnableLinkedConnections`, for
      `reads back too` and for `net use`, so all three rules were absent.
- [x] GREEN round 1, opus and haiku, 7 questions, passages as probed: all correct and quoted on both tiers.
      Gaps closed in the text: `stop_service(wait=False)` reads back; a runner on the drive gets no exit 70, and
      `.\tool.ps1` run on the drive is that case. Declined: the default of `EnableLinkedConnections` (off, and the
      probes read it so); which class carries `NoSuchUnit` (the bullet is about `NativeCallError`); how a bare name
      resolves (the risk is what the reader needs).
- [x] GREEN round 2, opus and haiku, 3 questions on the changed sentences, final text: all correct and quoted.
      Declined: the number of the child's exit code (-196608 measured, a host value, not a contract).
- [x] Mirror: regenerated from the pwshpy repo with `git merge-file`; the only divergence is the `name:` line.
