# Review checklist 2026-10-30: a remote command that reboots, and the cmd.exe digit redirect

Entries covered:

- E8: a remote command whose last step reboots the host loses its exit code and output.
- E10: `echo RC=%ERRORLEVEL%>> file` in cmd.exe never writes the RC line.

Files: `SKILL.md` (one Quick reference row after "Long remote reload/restart over SSH", one
paragraph after "The default ssh shell on Windows is `cmd.exe`").

## Claims and their evidence

- [x] E8 is argued from ssh behaviour already stated in this skill (exit 255 = ssh itself
      failed, a dropped session); `/proc/sys/kernel/random/boot_id` changes on every boot (Linux
      kernel documentation; the infra-proxmox zfs-guest-disks reference uses the same check).
- [x] E10: ss64 redirection page: a command line "will fail to work properly if there is a single
      numeral at the end, anything from 0 to 9" and "Moving the redirection operator to the front
      of the line completely avoids this issue". Not run on a Windows host (no VM was touched).
- [x] The existing row "Long remote reload/restart over SSH" covers a step that outlives a
      dropped session but not one that ENDS by rebooting; RED (below) confirmed no line covers it.

## Mechanical checks

- [x] Row padded to the existing widths (95 / 1001); the table is unchanged by the formatter.
- [x] Width and fence check over added lines prints nothing.
- [x] ASCII only, no history-finder hit, no private path or address in added text.
- [x] Paragraph after each insertion point read: the next row ("Scripted ssh") and the next
      section ("## Hook / script") do not refer back to the inserted text.
- [x] redcheck --corpus-cascade: reboot and cmd scenarios both `clean` (not caught).

## Probes (bitranox:baseline-probe, text only)

- [x] RED (opus, pre-edit text): Q10 quoted only "Never infer failure from a dropped SSH
      connection" and reported the gap "does not cover a tool whose last step reboots the host";
      Q11 answered NONE ("The only cmd line is 'The default ssh shell on Windows is cmd.exe'").
- [x] GREEN (opus, edited text): Q10 and Q11 each answered with a direct quote of the new text.
- [x] GREEN gaps: "silent on what to do if the tool has no no-reboot mode" -> closed (write the
      result to a file on the host, read it once the host is back); "only the ERRORLEVEL 0 case"
      -> closed ("Any single-digit code is eaten the same way (`RC=1>>` appends `RC=` with no
      digit)").
- [x] Re-probe on the final text (opus): Q10 quoted "with no such mode, have it write its result
      to a file on the host and read that once the host is back"; Q11 answered "rc.txt gets `RC=`
      with no digit". Remaining gaps declined: how to capture a result when the installer offers
      no result file at all, and whether to launch detached (the existing row "Backgrounding a
      remote command" covers `setsid ... &`; deciding per installer stays with the reader).
- [x] Haiku arm on the final text: Q10 quoted the split-and-boot_id row and ran the tool with
      its no-reboot mode then a separate `systemctl reboot`; Q11 "No, it does not record the exit
      code" and wrote `>> rc.txt echo RC=%ERRORLEVEL%`. Gaps declined: recovering a run that
      already rebooted (the row says to compare boot_id and read the real state; no general rule
      exists), multi-digit codes (only a lone digit before `>` is affected, which the text says).
- [x] Tiers: opus RED, opus GREEN, opus re-probe, haiku final (4 cells).
