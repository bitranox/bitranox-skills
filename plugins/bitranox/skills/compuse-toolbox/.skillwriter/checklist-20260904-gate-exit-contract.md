# skill-writer checklist - compuse-toolbox (2026-09-04, gate exit contract)

- [x] Change: the `gate` row now states the exit contract (the single failing gate's OWN code, so
      a taxonomy code such as 2 survives, else 1) and names a THIRD way a correct exit status still
      proves nothing - a background completion notification reports the RUNNER's status, not the
      gate's. The row previously stated two such ways and no exit contract at all.
- [x] Receipt held (skill_receipt.py, this session)
- [x] RED, measured rather than simulated: an agent reading the previous row treated a runner exit
      of 1 as the gate's own code, concluded a shipped tool violated its documented "exit 2 =
      regressed" contract, and spent four tool calls tracing an exit-plumbing defect that does not
      exist. Verbatim: "exit code 1, not 2 - that's an error, not a regression verdict." The row it
      read carried no exit contract to consult, which is the gap this closes.
- [x] Accuracy check (table -> behaviour) by EXECUTION, not review. Every claim in the row run
      against the shipped script:
      single gate exiting 2 -> runner exits 2;
      two gates exiting 2 and 3 -> runner exits 1;
      zero-test refusal, gate itself exited 0 -> runner exits 1.
- [x] Coverage check (behaviour -> table): the three branches of `red_status` are the three
      outcomes named in the row. No fourth branch exists.
- [x] Suites green: compuse-toolbox 753 collected (745 before the 8 added here), repo gate
      `--ci` 4704 passed / 14 skipped / 1 xfailed.
- [x] Security scan: one table row of prose plus a docstring; no secrets, addresses, hostnames or
      private paths added.
- [x] Token budget: hub skill, body remains a routing index; the change is one row, net +2 lines.
