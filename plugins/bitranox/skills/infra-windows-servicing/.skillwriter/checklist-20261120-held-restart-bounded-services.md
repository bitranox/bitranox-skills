# checklist - held restart, bounded service transitions, ceiling per guest class

Three queued contributions: two false-signal rows (a restart held by
TiWorker; a remote cleanup that timed out with no output), a subsection "Bound every service stop
and start in a servicing script" with a PowerShell snippet that logs each phase to a file, a
Durations paragraph sizing ceilings per guest class (install and held restart) with the commands
to sample TiWorker CPU and RebootPending, and two red-flag lines.

Decisions: d-20261120-c9b399cf, d-20261120-b61da803, d-20261120-1d862938

## RED

- [x] Skill decisions read first: one rejected entry (backup-slot product key), unrelated.
- [x] Text check of the pre-edit file (`git show HEAD:.../SKILL.md`): `WaitForStatus`, `HELD`,
      `TiWorker` CPU as a reboot-wait clock, and a re-offered KB are all absent (0 hits each). The
      lessons are already in this machine's context and memory, so a behavioural baseline here
      would measure the probe's context, not the skill; a text check is the RED.

## GREEN

- [x] Quote-back probe (opus, haiku) on the edited text, three questions (held restart, bounded
      BITS stop, re-offered KB): every answer quoted the new lines; no NONE.

## REFACTOR

- [x] Closed (opus, haiku): `-and` short-circuit left `wuauserv` stopped when BITS failed; the
      snippet now stops each, deletes only when both stopped, and starts both either way.
- [x] Closed (opus): the 120 s bound against a 20-minute BITS start; the text now says the bound
      is not a verdict, a start past it keeps going on its own and is logged.
- [x] Closed (opus, haiku): no command for "TiWorker CPU progress"; the paragraph now gives
      `(Get-Process TiWorker).CPU` and the RebootPending `Test-Path`, sampled every minute.
- [x] Closed (opus): the `UBR` cannot judge a .NET update; the text now reads each round's
      result code (both were 2, succeeded) and says the UBR does not answer this case. ARGUED:
      .NET updates not moving the OS UBR is general knowledge, not measured here.
- [x] Declined: a numeric window for "flat" - the measurement gives none; the text names the
      sampling rate and leaves the window to the caller's guest class.
- [x] Width and fence check on the added lines: no prose line over 100 characters, all ASCII,
      fences balanced. The PowerShell snippet was not executed (no Windows host in this session).
