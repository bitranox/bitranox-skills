# skill-writer checklist - infra-windows-servicing (2026-08-11, fix: /XJ is not the fix)

Corrects the guidance shipped hours earlier in the same day, which told readers `/XJ` makes
`robocopy /MIR` safe against a `Windows.old`. It does not. The earlier text was written from a
mechanism that sounded right and was never tested; this one is measured.

## RED

Given the PUBLISHED text and asked whether the command as written can delete anything outside
`C:\Windows.old`:

> "**No**, per the text's own reasoning. ... The command as written includes `/XJ`. The text states
> flatly: '`/XJ` is not optional - without it this destroys the live installation' - by the text's
> own construction, that means with it the mechanism it describes for reaching outside the tree is
> turned off."

It would have run the command. Its own gaps list named the defect precisely:

> "it is an inference from the text, not a stated verified outcome. ... It never states an
> equivalent positive confirmation such as 'with `/XJ`, `C:\ProgramData` was checked afterward and
> found intact.'"

That is the whole failure: an asserted fix, never verified, published as measured fact.

## Ground truth

Scratch fixture: a tree containing one JUNCTION and one SYMLINKD to a victim directory of 5 files.

| Method                                         | Victim files left | Verdict     |
|------------------------------------------------|-------------------|-------------|
| `robocopy $empty tree /MIR /XJ`                | 0 of 5            | DESTRUCTIVE |
| `rd /s /q tree`                                | 5 of 5            | safe        |
| `Remove-Item tree -Recurse -Force`             | 5 of 5            | safe        |
| strip reparse points, then `robocopy /MIR /XJ` | 5 of 5            | safe        |

Mechanism: `/MIR` is `/E` plus `/PURGE`. `/XJ` governs SOURCE traversal; the purge walks the
DESTINATION for extras and follows reparse points there regardless.

Corroborated on a real 25H2 guest: `Users\All Users` is a SYMLINKD to `C:\ProgramData`, and a
`/MIR /XJ` run took `C:\ProgramData` from 21 directories to 18 and `C:\Users\Default` from 29
entries to 0 before it was stopped.

## GREEN

Same scenario and pressure against the new text. Answer to the decisive question flips to "Yes",
with the mechanism, and the confidence answer is now anchored to evidence rather than to success:

> "It explicitly rules out two things as proof: 'the delete finished' and 'robocopy exited 0-7' ...
> The only basis for confidence the text offers is the before/after count of link-target contents
> being equal."

Rationalization defence held: told "just add /XJ, that's the documented fix", it answered that
`/MIR /XJ` alone deleted all 5 victim files, same as no flag, and that stripping the reparse points
is the actual fix.

Contamination: the GREEN prompt contains the conclusion, so GREEN shows the text is unambiguous,
not that a reader derives it unaided. RED is the load-bearing arm.

## GREEN gaps - closed or declined

- CLOSED: no concrete counting command. The verification step was prose; a reader who cannot run
  it will skip it. Now ships the exact PowerShell hashtable over all five counts.
- CLOSED: "snapshot" named no tool. Now states hypervisor snapshot / VSS and requires the guest be
  stopped or frozen.
- DECLINED: no rollback detail beyond restoring the snapshot - that IS the procedure, and it is
  platform-specific.
- DECLINED: fixture is small (1 junction, 1 symlink, 5 files) rather than production scale. The
  failure is a traversal mechanism, not a volume effect, and the real-guest counts above corroborate
  it at scale.
- DECLINED: silent on remote-execution mechanics - owned by `bitranox:compuse-ssh`.
- DECLINED: does not state that time pressure cannot override the snapshot and count steps. GREEN
  inferred that correctly unaided; adding it would restate the scenario rather than the rule.

## Checks

- [x] RED run against the PUBLISHED text and recorded verbatim; it chose the destructive command
- [x] Both arms asked for a `Skill gaps` section; both lists recorded, each item closed or declined
- [x] Every method in the table executed on a real guest against a scratch fixture, not reasoned
- [x] The claim being corrected is stated as measured-false, not softened
- [x] `/XJ` no longer appears anywhere as the safety mechanism; red flags name the real cause
- [x] Verification step is runnable as written, not prose
- [x] No hostnames, addresses, credentials or private paths - drive letters and link targets only
- [x] Version bumped MINOR: corrects published behaviour-affecting guidance
