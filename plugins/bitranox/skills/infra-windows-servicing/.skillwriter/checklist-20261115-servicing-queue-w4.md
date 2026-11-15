# skill-writer checklist - infra-windows-servicing (2026-11-15, queued lessons)

Two additions: "Choosing the remedy" now says to choose a repair image by the revisions it holds,
checked offline with `wimlib-imagex dir`, before a `RestoreHealth` run with it as `/Source:`;
"Durations" adds `DISM /ScanHealth` and says a probe that kills it at a timeout has no verdict.

Decisions: d-20261115-8bbdab23, d-20261115-ebb3fb5e

- [x] Receipt fresh. Step 0b: the skill has no ledger entries; nothing to reverse.
- [x] RED by text check of the pre-edit file: `wimlib-imagex dir` and `Image session has been
      closed` occur 0 times; the peer paragraph only says a source must hold the superseded
      revisions, with no way to check an image before the run.
- [x] The lead was worded "Before a repair run with an image as `/Source:`" so it does not
      contradict "try the repair first" two paragraphs up, which is about repair versus upgrade.
- [x] The `wimlib-imagex dir ... --path=` form follows the queued measurement, where it ran; it
      was not executed here (wimlib is not installed on this machine). The two greps run on any
      saved listing.
- [x] GREEN quote-back, opus and haiku, 2 questions on this skill: both tiers quoted the new text
      and answered correctly.
- [x] Gaps declined: which `<index>` to list (opus) - covered one paragraph above, "`<index>` is
      the image INDEX of the target's edition: pick it by matching the edition in
      `dism /Get-WimInfo`"; what timeout to use instead (opus, haiku) - the section's rule is to
      calibrate against a measured run, which the new paragraph sits under.
- [x] Width and fence check over the added lines: no output. ASCII only; no private names, hosts
      or build-specific paths.
