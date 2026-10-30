# skill-writer checklist - compuse-bash (multi-name command -v, fallible wait read, reboot row)

Entries covered: dash `command -v a b c` reports only the first name (two queued entries, one
row); a negated or `||` wait test over a remote read lands on success when the read fails; the
reboot row also names `systemctl is-active` reading the old boot.

- [x] Change: two new quick-reference rows (`command -v a b c`; a wait loop whose done-test reads
      a remote or fallible source) and the reboot row now lists `systemctl is-active` beside port
      22 and `ssh host true`.
- [x] Mechanism claims measured (dash 0.5.12, bash): `dash -c 'command -v ls nonexistent_xyz cat'`
      printed `/usr/bin/ls`, rc 0; `dash -c 'command -v nonexistent_xyz ls'` printed nothing, rc
      127; `bash -c 'command -v ls nonexistent_xyz'` rc 0; `! false | grep -q .` rc 0;
      `out=$(false) && ...` takes the failed branch (rc 1).
- [x] RED: an opus baseline-probe given the scenarios with no skill text answered Q1 and Q3
      correctly from inherited context (it named dash's first-argument rule and the boot_id
      method), so the behavioural RED is contaminated; the evidence is the text check: `command -v
      a b c` HEAD 0 now 1, `fallible source` HEAD 0 now 1.
- [x] GREEN (opus and haiku, edited rows pasted): both probed tiers wrote a one-name-per-call loop
      and a wait loop that captures `out=$(ssh ...)` and keeps waiting on a failed read, quoting
      "Probe one name per call" and "Capture the read and require its OWN exit status before
      testing the content". Q3 quoted "can all still come from the OLD boot". 2 tiers x 3
      questions.
- [x] Skill gaps reported and decided: poll bound and interval (declined: the "Waiting for an
      event" row in this SKILL.md sets the ceiling rule); recovery when boot_id was not captured
      before the reboot (declined: out of scope, `journalctl --list-boots` is already named).
- [x] Width and fence check over added lines: no output. Paragraph after each insertion read: the
      next rows (`Check/kill a process by name`, `Arming a waiter`) bind to nothing new.
- [x] Table canonical (reformat_tables.py: Unchanged); diff is 3 added, 1 changed line.
- [x] ASCII only, present tense (history finder: 0 hits in added lines), no private host or path.
