# skill-writer checklist - python-network-probe (2026-10-26, SNMP system read)

Change: document `read_snmp_system` / `aread_snmp_system` and the `snmp-system` subcommand
(ipscout 2.2.0). New quick-reference row, async row, subcommand grid (twenty-three), a CLI
example, a section "Reading a device's SNMP system group", error-contract, exit-code and
common-mistakes lines. The description gains the SNMP trigger and was rewritten rather than
appended to stay under the cap.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: retrieval and application scenarios, plus an over-trigger
      control.
- [x] Inherited-context check: `redcheck --corpus-cascade` named the tree-top CLAUDE.local.md and
      two facts, all on generic terms; a grep found none mentioning `read_snmp_system` or
      `snmp-system`, and the one fact naming SNMP names it only as a payload to scrub. Not
      inherited. Because this is an EDIT, the primary RED is a text check of the pre-edit file.
- [x] RED (text): the pre-edit SKILL.md has 0 matches for `snmp|uptime|sysname`, against 26 for
      `ping` as the control that the grep read the file.
- [x] RED (behaviour), opus + haiku, pre-edit text pasted: both answered NONE for SNMP and would
      hand-roll pysnmp (opus also named puresnmp); both said a down host and a wrong community
      cannot be told apart. Control question (FTP greeting): both chose `grab_banners`. Opus
      noted the git status in its environment named the feature and did not rely on it.
- [x] GREEN, opus + haiku, edited text pasted, five questions: both chose `read_snmp_system` with
      verbatim quotes; restart = a smaller uptime across two reads; wrong community, down host,
      no agent and the other version all `SILENT`; a bare string and bad arguments raise
      `ValueError`; the shell passes the community as `IPSCOUT_SNMP_COMMUNITY`, not
      `--community`. Over-trigger control (FTP greeting): both chose `grab_banners`, not the SNMP
      read. Cells: 2 tiers x 5 questions GREEN, 2 x 2 RED.
- [x] GREEN gaps closed: the library defaults (community, port, timeout, concurrency, version);
      host strings, not a network, and what a network string does (`UNREACHABLE`, measured);
      `port=` and the CLI `--version v1|v2c` / `--port` flags; the restart test's three holes
      (the 497-day wrap, `uptime_seconds` `None`, no `ANSWERED` baseline before the action);
      the other `SILENT` causes (a UDP 161 filter, a too-short timeout, the other version) and
      `is_reachable` to separate a down host; no agent is `REFUSED` only when the ICMP reply
      arrives; `read_snmp_system` in the many-host bad-name line of the error contract; the
      in-loop `RuntimeError`; `snmp-system` exit codes; keyed exactly as given, a repeat read
      once. Each new claim was checked by running it: an unresolvable name and a network string
      both `UNREACHABLE`, a repeated host read once, `RuntimeError` inside a loop, exit 1 with no
      agent answering and exit 2 for `--port 0`.
- [x] Gaps declined, with reason:
      - Where the community should come from (a keyfile, a vault): a deployment choice, not the
        library's; the text names the env var and why not argv.
      - Whether the environment is visible to other users per platform: the text claims only
        that argv is visible.
      - `aread_snmp_system` signature not spelled out: the async row and the "await ... there"
        line name it, and the arguments match the sync call.
      - A second read that is not `ANSWERED`: follows from the stated rule that only an
        `ANSWERED` value carries an uptime.
      - Pre-existing banner gaps a RED arm raised (the `startswith` example, Windows closed-port
        state for `grab_banners`): outside this change.
- [x] Quote-back after the fix round, opus (effort medium) + haiku: every touched question (Q2-Q7)
      answered with a verbatim quote of the new text. Both arms named one remaining gap, what a
      network string inside the list does; it was measured (`UNREACHABLE`, "cannot resolve") and
      the sentence added, with no undecided gap left.
- [x] Every code block executed against the real library: the SNMP example ran with the hosts
      swapped for a local fake agent, and the CLI example's community and network handling were
      checked through the CLI tests.
- [x] Description measured with `len()`: 1015 (cap 1024). Rewritten, not appended; "greeting",
      dropped in a first rewrite, was restored. `build_skill_triggers.py --check`: in sync.
- [x] Version-history finder over the skill dir: no hits.
- [x] Values added are documentation values (`192.0.2.x`, `192.0.2.0/24`, `192.0.2.0/28`); the
      remaining `192.168.1.x` and `1.1.1.1` lines predate this change.
- [x] No secrets, hosts, private paths or PII in the change; the community shown is the protocol
      default `public`.
- [x] Kept identical to the copy mirrored into the bitranox-skills marketplace, apart from that
      copy's name prefix.
