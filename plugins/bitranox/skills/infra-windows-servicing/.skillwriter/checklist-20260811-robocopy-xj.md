# skill-writer checklist - infra-windows-servicing (2026-08-11, fix: robocopy /MIR needs /XJ)

This is an INCIDENT-DRIVEN correction, not an authored improvement. The skill shipped a command
that destroyed a live installation, and the evidence below came from that failure rather than
from a pressure test. Recording it that way on purpose: the honest provenance is the point.

## What the skill said, and what it did

Shipped text:

    robocopy $empty C:\Windows.old /MIR /R:0 /W:0 /MT:16 /NFL /NDL /NJH /NP

`/MIR` follows junctions and directory symlinks unless `/XJ` is given. Measured on a Windows 11
25H2 guest (openvmm, build 26200.8973), read-only, after the failure:

    C:\Windows.old\Users\All Users      <SYMLINKD>  ->  C:\ProgramData
    C:\Windows.old\Users\Default User   <JUNCTION>  ->  C:\Users\Default
    C:\Windows.old\ProgramData\Desktop  <reparse>   ->  C:\Users\Public\Desktop

The mirror walked `All Users` into the live `C:\ProgramData` and emptied it. Observed sequence:

1. robocopy launched, reported nothing unusual
2. ssh began refusing the key - `Permission denied (publickey,password,keyboard-interactive)`
3. console black, guest unusable; recovered only by rolling back to a pre-delete snapshot

`C:\ProgramData\ssh` holds the host keys and `administrators_authorized_keys`, which is why the
first symptom was an auth failure rather than a file error. The rollback target had been taken
before the delete, so the repair the guest had just received was preserved.

## Why the earlier "measured on two guests" claim did not catch it

One of those guests ran a per-file `Remove-Item` pass BEFORE robocopy, which had already removed
the `Users\All Users` entry - `rd` and `Remove-Item` delete a junction entry without descending
through it. So the escape route was gone by the time the mirror ran. That guest survived by
ORDERING, not by being safe, and the skill recorded the survival as evidence the command was
sound. A pass that happens to be safe is not a control.

## What shipped

- `/XJ` added to the command and to the prose heading, so a skimmer sees it
- the measured link table, the symptom order (ssh first, not a file error), and the
  ordering-is-not-safety explanation
- two red flags: `/MIR` without `/XJ`; ssh refusing the key right after a Windows.old delete
- MAX_PATH residue recorded as EXPECTED, not a permissions problem: 16 files survived
  `Remove-Item` at a longest path of 262 chars with plain `Archive` attributes, and robocopy
  cleared them in about a second

## Checks

- [x] Every `robocopy /MIR` occurrence in the file carries `/XJ` - gated by a grep over the file
- [x] That gate was run against a NEGATIVE control (a line without `/XJ`) and correctly flagged it
- [x] No other skill in the marketplace ships a `/MIR` command (grep over `plugins/`)
- [x] Link table taken from a live guest, read-only, not from documentation
- [x] Recovery verified on the damaged guest: build preserved, `C:\ProgramData` 21 dirs /
      79402 files, 9 ssh key files, shell hosts running
- [x] No hostnames, addresses, or credentials in the diff - drive letters and link targets only
- [x] Version bumped MINOR (5.175.1 -> 5.176.0): behaviour-changing safety fix, not a doc typo
- [ ] NOT pressure-tested with a subagent. The correction is a flag on a command whose failure
      mode is now measured; a comprehension test would not add evidence the incident did not
      already provide. Flagged here rather than claimed as done.
