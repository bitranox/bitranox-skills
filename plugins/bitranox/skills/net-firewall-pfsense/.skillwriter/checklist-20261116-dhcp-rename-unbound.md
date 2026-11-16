# skill-writer checklist - net-firewall-pfsense (dhcp rename keeps the unbound name in step)

- [x] Type: technique and reference. Evidence is text checks of the skill file plus the script's
      own tests; no subagent probe was dispatched for this change.
- [x] Premise checked against the code: `php_rename_reservation` ended at
      `_php_reconfigure_dhcp()` and `cmd_dhcp_rename` ran no unbound step, and SKILL.md said
      "`dhcp rename` does not, so after a rename run the reconfigure and the restart yourself".
- [x] Step 0b: `show net-firewall-pfsense --kind rejected,removed --full` printed nothing; the
      live rule `d-20261116-922c8631` recorded rename as left to the reader, so this change
      supersedes it.
- [x] RED tests: `dhcp rename` added to the three DHCP-write tests (PHP gate in the body; restart
      plus `localhost.` check when `unbound_follows`; exit 2 with "written to config.xml" over a
      dead unbound) and to the control (no restart when it does not follow). 3 failed, the
      control passed.
- [x] GREEN tests: the whole suite, 235 passed, with CI's dependency set.
- [x] Text check: "`dhcp rename` does not" 0 after the edit (was 1); the sentence naming
      `dhcp add`, `dhcp rename` and `dhcp rm` as running the reconfigure 1.
- [x] Width and fence check over the added lines prints nothing (the paragraph was reflowed
      after the edit pushed one line over 100 columns); ASCII only.
- [x] The paragraph's anchors for the ledger rule are unchanged; "as above" still binds to the
      restart-and-check paragraph before it.
- [x] Cases decided beyond the request: none. `dhcp add` still accepts an address inside the
      pool.
- [x] Decisions: d-20261116-2c7e4d76
- [x] Present tense, no private host, repo or path in the added text.
