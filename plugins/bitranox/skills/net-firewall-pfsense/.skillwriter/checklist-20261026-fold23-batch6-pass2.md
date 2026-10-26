# skill-writer checklist - net-firewall-pfsense (memory rules folded in)

- [x] Rule: Run the skill's pfsense.py snort check on the target (then snort why for the firing
      SID) instead of diagnosing by hand. If snort2c has blocked it, apply all three parts:
      suppress the SID, add a LITERAL CIDR to the Snort pass list (an alias entry does not protect
      anything), and clear the table, then verify against the running instance.
      Where: no text change (already covered)
- [x] Rule: Check the firewall's own /etc/resolv.conf. If Tailscale's Accept DNS has pointed it at
      100.100.100.100, set the package's acceptdns config to empty or off (its code default is
      on), resync, and also run tailscale set --accept-dns=false, because a package restart does
      not re-apply the flag. Then verify resolv.conf, the prefs and a repo fetch. Treat the
      upgrade lock message as a symptom of the DNS failure and do not just clear the lock.
      Where: SKILL.md, Diagnose first (table row 'Another instance...' changed) and Traps (two new
      paragraphs after the pkg-upgrade trap)
- [x] Rule: Snapshot first (the VM or hypervisor snapshot plus a config.xml backup). Write the PHP
      to a script file and run it with pfSsh.php playback, never piped into pfSsh.php over
      interactive stdin, which hangs and leaves zombies. After services_unbound_configure(),
      always run svc restart unbound and immediately check that names resolve, because unbound can
      be left down.
      Where: SKILL.md, Verbs (snapshot paragraph), Traps (two new paragraphs), Not covered here (out-of-
      band edit paragraph extended)
- [x] Rule: Check whether the rules have a per-rule gateway (policy routing), because pfSense
      silently ignores limiters on those rules (dnctl sched show stays at 0 active), so attach
      limiters only to rules without a gateway. Write the FQ-CoDel parameters explicitly in the
      dnshaper XML, because on a cold dummynet module the defaults resolve empty and dnctl aborts.
      pfctl -sq indents queue names, so grep for them loosely.
      Where: limiters.md (new) plus routing line in SKILL.md, SKILL.md 'Not covered here' (routing line);
      references/limiters.md (whole file)
- [x] Rule: Parse config.xml with an XML parser for the host's IP and hostname, grouped by parent
      path, and put the full list in the question: unbound/hosts (including public-name aliases),
      dnsmasq/hosts, nat/rule port forwards, and the SEPARATE filter/rule pass rules, which
      deleting a forward does not remove. Remove them by content through the config API, never by
      index, reload the filter and restart unbound, then confirm that pfctl and host_entries show
      nothing left for the IP.
      Where: SKILL.md, new section '## Retiring a host' (between Traps and Not covered here)
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
- [x] Each GREEN Skill gaps list triaged: 5 closed in the text, 12 declined with a reason (covered
      elsewhere with file:line, out of scope, owned by another skill, or a judgement the skill
      leaves open).
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, tables canonical (reformat_tables.py --check --strict), added
      prose wrapped like the surrounding text, no code span split across lines.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; addresses are
      documentation ranges or placeholders.
