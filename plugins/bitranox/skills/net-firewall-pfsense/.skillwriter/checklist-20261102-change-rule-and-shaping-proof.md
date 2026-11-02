# skill-writer checklist - net-firewall-pfsense (site change rule, shaping proof, ALTQ queue)

- [x] Type: technique and reference. Tested with application and retrieval scenarios.
- [x] Measured input (pfSense 2.8.1, 10 Mbit FQ-CoDel limiters on a rule without a gateway): a
      download capped at 9.5 Mbit/s against a same-LAN control at 19 Mbit/s, `dnctl sched show`
      `0 buckets 0 active` on both pipes, `dnctl pipe show` 5.9 MB and 36 queued packets. Not
      reproducible here (needs a pfSense box); each figure is worded as measured.
- [x] redcheck --corpus-cascade: exit 1, inherited coverage (a memory fact on this machine records
      the limiter measurements). Route taken: the coverage check against the skill FILE is the
      evidence; the behavioural arms below are supporting.
- [x] RED text check (pre-edit SKILL.md + limiters.md): `change rule`, `private state`,
      `backup folder`, `measured rate`, `does not prove`, `pipe flush`, `different server`,
      `tagged <tag>`, `pfctl -vsq`, `re-test it` all 0.
- [x] RED behavioural (opus, pre-edit text pasted, 5 scenarios): no change rule mentioned before an
      `--apply`; quoted "The proof is `dnctl pipe show` ... and `dnctl sched show`" and called the
      capped run unresolved; read leftover pipes as "the removal has not reached the kernel" (NONE);
      built a WF2Q+ limiter for "give way, no cap" (NONE).
- [x] GREEN behavioural (opus and haiku, edited text, same 5 scenarios, 2 cells): both read the
      change rule first, answered the backup-folder question from "which is not the site's backup
      folder", called the capped run shaping and the gateway claim unsettled, read the pipes as
      leftovers, discarded the 0-byte control, built the low-share ALTQ queue and cleared the queue
      on both rules for the A/B.
- [x] Diff GREEN against RED in both directions: nothing lost. RED's calibration ideas (move the
      cap, interleave arms) are its own reasoning, not text the edit displaced.
- [x] Commands executed with a fake ssh, default state dir, `snapshot --dir <d>` and
      `--snapshot-dir <d> snapshot` each write the file where stated, without `--apply`.
      `--snapshot-dir` on `dhcp add` confirmed in `dhcp add --help`. The `dnctl` and `pfctl` commands were not run here (no pfSense box); they
      are quoted from the measurement.
- [x] Gaps closed from GREEN: flat "pfSense ignores" heading and the unconditional attach advice
      now marked as a report and conditional on the re-test; the measurement names its rule as
      gateway-less; `dnctl pipe show` says what missing and listed each mean; `--dir` versus
      `--snapshot-dir` reduced to the one that also covers `--apply`; "control 15 to 16" given a
      direction; "Everything is a dry run" narrowed (`snapshot` writes without `--apply`, run above;
      reported by RED).
- [x] Gaps declined: what clears a leftover pipe (not established by the measurement); share values,
      queue GUI fields, a pass threshold for the re-test and an A/B run count (no measurement here,
      left to the reader's own method); how to check for live calls (site-specific); the snapshot
      path (the tool prints it, `do_snapshot` return value and `cmd_snapshot` output).
- [x] Final re-probe (opus and haiku, 6 quote-back questions, 2 cells) on the final wording: all six
      answered by quote or a stated inference, no new undecided gap.
- [x] Width and fence check over added lines prints nothing; paragraph after each insertion read.
- [x] Description unchanged (314 chars). Routing therefore not retested.
- [x] Cases decided beyond the report: a site rule outranks these defaults (stated in the report as
      mandatory); no other new policy.
- [x] ASCII only, present tense, no private host, repo or path in the added text.
