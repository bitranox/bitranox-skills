# skill-writer checklist - net-firewall-pfsense (Snort GID:SID for why, fixsteps, verify)

- [x] Type: technique and reference. Tested with application scenarios and quote-back.
- [x] Measured input (pfSense 2.8.1 Snort alert CSV): `11/16/26-01:54:17.521185 ,125,9,1,"(ftp_telnet)
      Evasive (incomplete) TELNET CMD on FTP Command Channel",TCP,...`. Field 1 is the generator
      id, which the parser never read: `snort why` printed `SID(s) 9` and `fixsteps --sid 9`
      printed `suppress gen_id 1, sig_id 9`, a different rule. The same line (addresses replaced
      with RFC 5737 values) is the test fixture `ALERT_GID_125`.
- [x] Step 0b: `skill_decisions.py show net-firewall-pfsense --kind rejected,removed --full` and
      `show net-firewall-pfsense` both printed nothing (no ledger yet).
- [x] RED text check (pre-edit SKILL.md from `git show HEAD:`): `GID` 0, `gen_id` 0, `GID:SID` 0,
      `125:9` 0, `--sid` 0.
- [x] RED behavioural (pre-edit excerpt pasted, scenario "ftp_telnet alert, SID 9, write the fix
      commands and the suppress line", opus and haiku, 2 cells): haiku wrote
      `suppress gen_id 1, sig_id 9, ...` and said gen_id 1 was its assumption; opus wrote
      `gen_id 125` from its own Snort knowledge and reported that the excerpt names no generator.
- [x] GREEN behavioural (edited text, same scenario, opus and haiku, 2 cells): both ran
      `snort why` first, used `--sid 125:9` for `fixsteps` and `verify`, and quoted
      "Given only a SID, run `snort why <ip>` for the GID before writing the fix."
- [x] Diff GREEN against RED in both directions: nothing lost; RED's other answers (pass-list
      range, unblock) are unchanged in GREEN.
- [x] Gaps closed from GREEN: haiku read `125:9` as the GID of every preprocessor alert, so the
      example now names ftp_telnet and says each preprocessor has its own GID; opus asked what to
      do when `snort why` finds no alert, so the text says the GID is then unknown and is not
      guessed.
- [x] Final re-probe (haiku, 2 questions: an http_inspect SID 4 report, and `snort why` finding no
      alert) on the final wording: answered "No" (no 125:4, run `snort why`) and "stop, the GID is
      unknown", each with a verbatim quote of the edited sentence. No new undecided gap.
- [x] Gaps declined: the `--fw` profile, launch path, resync command and dry-run behaviour (the
      probes saw an excerpt; SKILL.md lines 55, 69 and 97 cover `--help`, the `--apply` dry run
      and `--fw`); suppress scope (all sources versus `track by_src`) and the pass-list range (the
      text and `fixsteps` leave them to the reader's review, unchanged by this edit); confirming
      a block is a false positive before suppressing (judgement the skill leaves open); a table of
      GIDs per preprocessor (the text requires a lookup through `snort why` instead); what to do
      next when no alert is found (site-specific); one SID under several GIDs (`snort why` lists
      every GID:SID pair, `test_snort_why_lists_each_gid_sid_pair_in_numeric_order`).
- [x] Commands executed: `pfsense.py snort fixsteps --sid 125:9` printed
      `'suppress gen_id 125, sig_id 9'` and `snort verify --sid 125:9`; `--sid 9` printed
      `gen_id 1` plus the assumption note; `snort verify --help` shows `--sid GID:SID`.
      `snort why` and `verify` against a live box were not run here (no pfSense box); they are
      covered by the fake-ssh tests in `tests/test_pfsense.py`.
- [x] Width and fence check over the added lines prints nothing; the item is the last in Common
      mistakes, so no back-reference or list count re-binds.
- [x] Description unchanged. Routing therefore not retested.
- [x] Cases decided beyond the report: a bare SID keeps working and means gen_id 1 (the previous
      meaning of the suppress line `fixsteps` printed), and `verify` with a bare SID now checks
      gen_id 1 only instead of any generator.
- [x] Decisions: d-20261116-de07bbd9
- [x] ASCII only, present tense, no private host, repo or path in the added text.
