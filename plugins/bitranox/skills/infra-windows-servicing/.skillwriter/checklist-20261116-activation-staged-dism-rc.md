# skill-writer checklist - infra-windows-servicing (2026-11-16, queued lessons)

Four additions: an "Activation: read it before and after a repair upgrade" subsection (compare
`LicenseStatus` and the installed key's `PartialProductKey`, never `BackupProductKeyDefault`; get
the error from `slmgr /ato`; `0x803F7001` on a MAK is retried before a key swap; mask `/ipk`
output case-insensitively); "Record DISM's exit code with the redirect FIRST" under the cumulative
update install; a subsection on Setup-log `Staged` lines (target state, and the KB can be the
servicing stack update); and a `DISM /Add-Package` ceiling paragraph under "Durations". Three
false-signal rows and four red flags point at them. Description unchanged.

Decisions: d-20261116-6512bf26, d-20261116-a1ebc75f, d-20261116-a57cf377, d-20261116-3c4fcf87, d-20261116-5ff2c0ae, d-20261116-55616c72, d-20261116-ac3b9858

- [x] Step 0b: `show --kind rejected,removed --full` printed nothing; the two live rules
      (repair-source-by-revision, scanhealth-timeout-no-verdict) are untouched.
- [x] Queue reconciliation: the claim that the repaired guest "kept the same key (matches
      Windows.old BackupProductKeyDefault)" is not shipped - that check read the backup slot on both
      sides. The theory that the backup-slot key was invalid and caused `0x803F7001` is not
      shipped - the same key later activated; recorded as a `rejected` ledger entry. Only the
      measured part ships: the backup slot can differ from the installed key.
- [x] RED by text check of the pre-edit file (`git show HEAD:`): `LicenseStatus`,
      `PartialProductKey`, `BackupProductKeyDefault`, `slmgr`, `0x803F7001`, `0x80131500`,
      `Staged state`, `ServicingStack` 0 hits each; `ERRORLEVEL` 1 hit (the `wmic` paragraph,
      unrelated); no ceiling or exit-code-file guidance for `/Add-Package`.
- [x] Snippets executed where possible: the masking line ran in pwsh on a fake key-shaped string
      held in lower case with an upper-case print: `-replace [regex]::Escape($key)` masked it,
      `String.Replace` left it in (hence the case-insensitive wording). The CIM query, slmgr and
      the cmd redirect are Windows-only and were not run here; their behaviour rests on the queued
      measurements.
- [x] GREEN quote-back, opus and haiku, 8 questions (16 cells): every answer quoted the new text
      and was correct, including "do not swap the MAK on the first 0x803F7001" and "rc.txt is
      empty for exit 2".
- [x] Gaps closed after GREEN: where the full key comes from and that an unchanged
      `PartialProductKey` needs only `/ato` (both tiers); that `-replace` ignores case (both);
      that redirect-first holds for every exit code (haiku); that an EMPTY exit code file means
      DISM ended, not a running install, so "keep reading the marker" cannot loop on it (opus).
- [x] Gaps declined: how to read the `UBR` - covered, "Read the build from the registry `UBR`
      (hex, see "Monitoring")" in "A cumulative update Windows Update will not offer"; how to
      search the rotated cabs - covered, "The CBS log you can grep covers only a few days"; a
      numeric ceiling - the section's rule is to calibrate against a measured run; other
      `LicenseStatus` values and KMS/retail channels - only MAK and values 1 and 5 were measured;
      whether the later boot is part of the `0x803F7001` recovery - not measured, the text says
      only "after a later boot"; the table row "the machine is as it was" - it is the column of
      obvious (wrong) readings, by design.
- [x] Re-probe 1 (haiku, the four touched questions): all four quoted the new sentences and
      answered right; it found one new gap, "the install it cut off is still running" against
      "DISM has ended" for an empty file. Fixed by splitting the cases: no file yet means the
      install may still be running; an existing empty file means DISM ended.
- [x] Re-probe 2 (opus and haiku, the ceiling paragraph): both answered both cases right; both
      questioned the inference "the echo has run, so DISM has ended". Fixed by stating that the
      redirect sits on the echo line after the DISM call, and adding: delete the file before each
      run. Declined from that round: when the `UBR` counts as done - covered, "Done means the
      `UBR` reached the target build"; what exit 3010 means - covered, "(exit 3010 is success with
      a reboot pending)"; an upper bound on waiting - covered by "Monitoring" (phase markers plus
      worker CPU); reading the file at the instant the echo opens it - a millisecond window, not
      worth a rule.
- [x] Re-probe 3 (haiku, final text of the ceiling paragraph): quoted "the file appears only
      once DISM has ended" and "Delete the file before each run" and answered both cases right;
      called the logic consistent. Its remaining gaps were all outside the excerpt and covered:
      exit 0 and other codes - "The redirect-first form has no digit before `>`, so it holds for
      every exit code"; 3010 - "(exit 3010 is success with a reboot pending)"; the target `UBR` -
      "Done means the `UBR` reached the target build". No new undecided gap.
- [x] Width, fence and ASCII check over the added lines: no output. No private host names, VMIDs,
      product keys or key fragments.
