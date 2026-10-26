# skill-writer checklist - infra-modulejail (memory rules folded in)

- [x] Rule: The agent should whitelist the whole Docker module set at once (xt_addrtype, xt_nat,
      xt_comment, xt_set, ipt_REJECT, nf_reject_ipv4, overlay, br_netfilter), because they are
      requested at runtime and otherwise fail one at a time (bridge setup first, then
      CHAIN_ADD/DNAT on port publishing). It should add a modules-load.d entry so they load at
      boot, check journalctl -t modulejail for anything else, and handle the container side
      (nesting, keyctl, iptables-legacy) through infra-proxmox.
      Where: SKILL.md, ## The closure misses runtime-loaded modules - discover those by EXERCISING: new
      worked example after the 'A working feature is not proof nothing is blocked' paragraph,
      before ## Verify
- [x] Rule: The agent should recognise a blocked module (modprobe exits 0 but loads nothing). It
      should whitelist nfsd together with its blocked dependency nfs_acl, which shows up as
      'Unknown symbol' under modprobe --ignore-install, and check modinfo -F depends nfsd on that
      kernel. Then it should add a modules-load.d entry (nfs_acl then nfsd), regenerate the jail,
      reset-failed the failed units and run systemctl enable --now nfs-server.
      Where: SKILL.md, ## The closure misses runtime-loaded modules - discover those by EXERCISING:
      worked example after the Docker example, before ## Verify
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (5 questions), again after the
      review fixes for every question, and a third time for the 2 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 4 closed in the text, 8 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
