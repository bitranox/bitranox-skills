# skill-writer checklist - infra-proxmox (row "tc state on a VM tap gone")

- [x] Change: one new row in the troubleshooting table, after "How did the VM end?".
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the edit was committed.
- [x] Step 0b: `skill_decisions.py show infra-proxmox --kind rejected,removed --full` printed
      nothing; the edit reverses no recorded decision.
- [x] Mechanism claims measured on PVE 9.1: `qm reboot` ran a `qmreboot` then a `qmstart` task;
      the tap's ifindex changed 9 -> 41; the `post-start` hookscript logged its apply 5 s after
      the start task and both mirred redirects were back; the IFB qdisc counters kept counting
      across the restart. `tc filter replace` without a fixed handle failed
      `RTNETLINK: File exists` on a second run; `tc qdisc replace ... clsact` ran on an existing
      clsact without error on every repeat. Argued, not measured: a guest-internal reboot keeps
      the process (QEMU resets in place), `reboot: 0` makes QEMU exit, a failing `pre-start`
      stops the start, IFBs are gone after a host reboot.
- [x] RED on the pre-edit text (the installed skill had no such row): haiku answered that
      `qm reboot` keeps the filters (A, "restarts the guest inside the existing QEMU process").
      opus answered correctly from general knowledge, so the gap is on the weak tier.
- [x] GREEN with the row pasted: opus and haiku both answer B for `qm reboot`, yes with the
      default `reboot: 1` for a guest reboot, `post-start`, fixed `handle` with
      `tc filter replace`, each quoting the row.
- [x] Skill gaps from GREEN, decided. CLOSED in the row: whether IFBs survive a host reboot
      (they do not; create when missing), clsact idempotence (`tc qdisc replace` repeatable),
      hook arguments (`<file> <vmid> <phase>`), the `snippets` content type, `i<N>` = `net<N>`,
      `reboot: 0`, never `pre-start`. DECLINED: what a failing `post-start` does to the start
      task (not measured here); whether PVE restarts a VM after `reboot: 0` (outside this row);
      pref versus handle detail (the row names the field that failed).
- [x] Re-probe on the final text (haiku, quote-back, 7 questions on the closed gaps): all 7
      answered right with a direct quote. Its new gaps, decided: "VM restart" ambiguous CLOSED
      (now "`qm reboot` and stop/start"); `ip link set <ifb> up` CLOSED (as fw-cake does);
      executable snippet CLOSED (PVE GuestHelpers.pm dies "script ... is not executable").
      DECLINED: a handle value (any fixed value works; the row names the requirement), the
      snippets host path (storage-specific), an IFB naming convention (local choice).
- [x] Table re-padded with reformat_tables.py; `--check` clean; the `||` inside the code span is
      escaped so the row keeps its two cells.
- [x] Description unchanged (frontmatter not edited). ASCII only, present tense.
- [x] No private host, address or path added: `<vmid>`, `<file>`, `<tap>`, `<ifb>` placeholders.
- [x] Second re-probe after those fixes (haiku, 3 questions on them): all 3 right with a direct
      quote. Its gaps DECLINED: IFB survival is measured (the CAKE counters kept counting across
      `qm reboot`); the order of IFB setup and redirect filters follows from the row; shebang
      and ownership are ordinary script basics; a failing `post-start` stays unmeasured.
- Decisions: d-20261120-994ac191
