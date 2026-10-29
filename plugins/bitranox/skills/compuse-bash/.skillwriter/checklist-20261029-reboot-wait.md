# skill-writer checklist - compuse-bash (row "Waiting for a host to come back after a reboot")

- [x] Change: one new row in the quick-reference table, after "Arming a waiter on a log a
      PREVIOUS run already wrote".
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the edit was committed.
- [x] Mechanism claim measured: a wait on ssh after a scheduled reboot matched the pre-reboot sshd,
      the next step ran on the system going down, and `journalctl --list-boots` showed the
      step's output belonged to the old boot; after waiting for a changed
      `/proc/sys/kernel/random/boot_id` the rerun landed on the new boot.
- [x] RED as a text check (opus, pre-edit text): NONE - only the generic "Waiting for an event"
      ceiling rule and the log-waiter analogue apply.
- [x] GREEN quote-back: opus and haiku both quote the row and call the port-22 wait unsound.
- [x] Skill gaps from GREEN, decided. DECLINED: a numeric bound (host-specific; the "Waiting for an
      event" row already requires an expected-duration ceiling); how to trigger the reboot over
      ssh without the call hanging (a separate question this row does not claim to answer);
      action when boot_id never changes (the same ceiling rule: stop and investigate).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, table re-padded with reformat_tables.py and canonical.
