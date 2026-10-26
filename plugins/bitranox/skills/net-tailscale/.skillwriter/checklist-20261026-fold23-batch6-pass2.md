# skill-writer checklist - net-tailscale (memory rules folded in)

- [x] Rule: Point the firewall's forward zone at a Linux tailnet node running a small forwarder
      (e.g. dnsmasq server=/<tailnet>.ts.net/100.100.100.100), because quad-100 answers there but
      not on FreeBSD/pfSense; do not use the coordination server's published ts.net resolver (it
      answers REFUSED); remember the answers are 100.x addresses, so LAN clients need a route into
      100.64.0.0/10; and avoid a tailnet-wide DNS entry pointing at a LAN-only resolver, which
      traps any off-LAN node that later turns Accept DNS on.
      Where: SKILL.md, 'DNS: MagicDNS on quad-100 is platform-asymmetric', new paragraph after the 'Do
      NOT "fix" it by setting accept-dns=true' paragraph
- [x] Rule: Run tailscale set --accept-dns=false first, because it writes /etc/resolv.pre-
      tailscale-backup.conf back over /etc/resolv.conf and deletes the backup (so a file deployed
      earlier gets overwritten), then deploy the managed resolv.conf; before switching check that
      no container relies on host DNS (pct config <id> | grep nameserver) since CTs without their
      own nameserver inherit the host resolver; verify with grep -v '^#' /etc/resolv.conf and
      getent hosts on the host and in a guest.
      Where: SKILL.md, 'DNS: MagicDNS on quad-100 is platform-asymmetric' (reconciled parenthetical) +
      new subsection '### Switching accept-dns off on Linux writes resolv.conf one more time' +
      one 'Common mistakes' table row
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. The rules
      under test are recorded in this machine's memory store, so a behavioural arm would be
      contaminated; only a verbatim quote from the snapshot counts.
- [x] GREEN quote-back on haiku and opus against the edited files (5 questions), again after the
      review fixes for every question, and a third time for the 1 questions the fix-delta fixes
      touched: every answer quoted the edited text, no NONE. Quotes were substring-checked against
      the files; the pre-edit snapshots fail the same check.
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per question per tier per round.
- [x] Independent review of the full diff, then of the fix delta alone; every finding fixed or
      declined with evidence by the fixer, and the fix delta re-reviewed.
- [x] Each GREEN Skill gaps list triaged: 5 closed in the text, 7 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
