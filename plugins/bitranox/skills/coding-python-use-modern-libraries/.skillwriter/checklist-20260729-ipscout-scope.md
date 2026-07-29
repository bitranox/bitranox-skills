# skill-writer checklist - coding-python-use-modern-libraries (2026-07-29, ipscout row scope)

Change: the ipscout row named ICMP ping, reachability and traceroute only, which was the whole
library when the row was written and is now about a third of it. Task widened to include port
scanning, MAC/ARP lookup, routes, interfaces and subnets; `python-nmap` and `netifaces` added to
the Avoid column, since those are what an agent reaches for when the row does not mention the
task. Shipped in plugin 5.100.2.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: an agent asking this table "how do I read the ARP cache in Python" found no row, so the
      table sent it nowhere and it fell through to recall - the same failure the ipscout row was
      added to fix, just for the newer half of the library.
- [x] GREEN: the task column now names the tasks by the words an agent would search for, and the
      Avoid column names what it would otherwise pick for each.
- [x] Verified against ground truth: every capability claimed in the row is in `ipscout.__all__`
      as of this change, checked by script rather than from memory.
- [x] `netifaces` claim checked before writing: last release 0.11.0 (2021), builds from C, and is
      the usual answer to "list interfaces in Python" - so it belongs in Avoid with a reason.
- [x] One row touched; the table's grouping is unchanged. Realigned with reformat_tables.py.
- [x] Scope: shared/general - no machine-specific content.
- [x] Security scan: one prose table row, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body table edit, frontmatter untouched).
- [x] Token budget: one row, widened rather than added.
