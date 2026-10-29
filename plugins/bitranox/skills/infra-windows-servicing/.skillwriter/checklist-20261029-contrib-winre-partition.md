# skill-writer checklist - infra-windows-servicing (growing C: past WinRE, reagentc 1614)

- [x] Premise: installing a KB by hand from the Update Catalog is already covered ("A cumulative
      update Windows Update will not offer", "Fetching the .msu"); the WinRE partition and 1614
      parts were missing.
- [x] Change: new section "Growing C: when the Recovery partition is in the way, and re-enabling
      WinRE" (rescan, reagentc /disable first, positive identification, delete, resize leaving
      ~1 GB, recreate and enable; seeding Winre.wim with wimlib-imagex for 1614).
- [x] Not reproducible here (needs a Windows guest); the steps are the measured procedure,
      worded generically (no guest ids).
- [x] RED text check (origin/master): `reagentc` 0, `Get-PartitionSupportedSize` 0.
- [x] GREEN quote-back: "`reagentc /disable`. This is the step that copies `Winre.wim` OUT of the
      recovery partition"; "**`reagentc /enable` fails 1614 ...** ... seed the image from
      installation media of the same release".
- [x] Description: two triggers added (C: will not extend after the disk was enlarged, reagentc
      /enable fails 1614); measured 686 chars. Routing unverified.
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
