# skill-writer checklist - infra-windows-servicing (2026-10-19, unoffered KB, VSS capture, upgrade markers)

Change: a new section on a cumulative update Windows Update will not offer (class check, `UBR`
not `Get-HotFix`, fetching the .msu from the Update Catalog, checkpoint CUs by build, `dism.log`
over the DISM exit text); a new section with a VSS-shadow recipe for capturing a live install; the
in-place-upgrade monitoring paragraph gains the `setupact.log` phase markers and `SetupHost` CPU as
the rate signal; three false-signal rows and three red flags carry the triggers.

- [x] Skill type: reference/technique - tested by quote-back (verbatim quote, or NONE).
- [x] RED (text as it stood, opus): the unoffered-KB scenario NONE; VSS capture and upgrade
      monitoring PARTIAL (a one-line VSS hint in Common mistakes, a generic monitoring rule).
- [x] GREEN (new text, opus and haiku): all three scenarios answered by a direct quote.
- [x] Claims re-checked, not copied: the checkpoint-CU rule was re-read on Microsoft Learn ("DISM
      merges the checkpoints present in the folder"), so "target as the only .msu" is stated only
      for a build at or past the checkpoint, with the not-yet-on-it case beside it.
- [x] REFACTOR, from the GREEN gaps: a localised console string was replaced by the error number.
- [x] Skill gaps, declined: which principal the DISM task runs as (the SYSTEM-task section already
      covers the trade-off), a numeric stall threshold for `SetupHost` CPU (one measured run, no
      calibrated value), shadow Create failure handling (VSS disabled is out of this recipe's scope).
- [x] Lost-result diff: every RED quote survives in GREEN; nothing missing.
- [x] Description unchanged; new table rows padded to the existing widths (`reformat_tables.py
      --check` clean).
- [x] Security: no host names, VM ids or private paths; example paths are generic (`D:\out.wim`).
