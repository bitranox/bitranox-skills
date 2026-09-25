# skill-writer checklist - compuse-ssh (2026-09-26, a changed host key is healed, never re-run)

The fleet-host-key section said a changed key "fails once" under `StrictHostKeyChecking no` and
told the reader to retry, gated on exit status plus stderr matching
`REMOTE HOST IDENTIFICATION HAS CHANGED|Host key verification failed`. Measured on OpenSSH 10.2
against a known-hosts file holding a wrong key: with `StrictHostKeyChecking=no` ssh prints the
banner and proceeds (exit from the later auth step, no "Host key verification failed"); with `yes`
and `accept-new` it prints the fatal line. So under the configuration the section recommends a
changed key never refuses, the command runs, and the only way to meet the old retry gate is a
remote command whose own inner ssh or rsync relays that text with exit 255.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: application scenario with two cases - a relayed inner
      host-key failure (exit 255) and a genuine own-host change after which a mutating command
      failed (exit 3). The correct actions are: no drop and no re-run; drop and no re-run.
- [x] Scope: the one paragraph, plus the exit-255 row of the failure table that stated 255 always
      means ssh itself failed. No frontmatter change.

## RED
- [x] Old paragraph pasted, pinned to haiku, inert probe type: it answered drop=YES and
      re-run=YES for BOTH cases, quoting "Gate that retry on the exit status AND on stderr
      matching ...", and reasoned that the mutating `apt-get -y upgrade && ./migrate.sh` "did not
      execute" because the banner was present.
- [x] Its Skill gaps: which exit codes count, how to read stderr carrying both the banner and
      other errors, what to do if the retry also fails.

## GREEN
- [x] New paragraph pasted, same model and scenario: case 1 drop=NO re-run=NO, case 2 drop=YES
      re-run=NO, each decision quoting the governing sentence.
- [x] Skill gaps asked for again after the first reply omitted the section: none, with the
      sentence checked for each of the three questions. The RED gaps are closed by "whatever the
      exit status", "NEVER re-run" and the Offending-line rule.
- [x] REFACTOR: the failure-table row "Exit 255 = ssh ITSELF failed" contradicted the new
      paragraph for the relayed case; it now says 255 is usually ssh itself and that a remote
      command can exit 255 too, so stderr decides.
- [x] The paragraph names `fleet_ssh.py --trust-changing-host-keys`, whose behaviour matches:
      its tests pin both cases, and an end-to-end run against a real sshd with a wrong-key
      known-hosts file dropped the entry and ran the command once.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] Paths in the text are the section's own `~/.ssh/known_hosts_fleet` placeholder; no address,
      MAC or hostname added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] Table re-padded by the formatter after the row edit.
