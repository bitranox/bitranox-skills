---
name: infra-windows-servicing
description: Use when a Windows machine will not install a cumulative update, its component store is damaged, DISM or setup.exe fails with an opaque code (0x800F0915, 0xC1900200, 0xC190010E, 0xC1420127, 0x80070020), a delete of Windows.old refuses with "Access is denied" / "Zugriff verweigert" despite takeown and icacls succeeding, a long servicing job looks hung, or an in-place repair upgrade is being planned or run.
---

# Windows servicing and repair: the traps

Repairing a Windows component store is not hard to execute - the commands are well known. It
is hard because several distinct failures all surface as **"Access is denied"**, a **quiet log**,
or a **clean health report**, so a competent operator confidently fixes the wrong thing. This
skill is the set of those false signals, each with the measurement behind it.

Assume you already know `DISM`, `takeown`, `icacls` and `setup.exe`. Read this for what they
do not tell you.

## The false signals

| Symptom                                         | The obvious reading               | What it usually is                                                                  |
|-------------------------------------------------|-----------------------------------|-------------------------------------------------------------------------------------|
| Update fails, `ScanHealth` clean                | not corruption, so look elsewhere | **disk headroom** - a cumulative update needs far more free space than its own size |
| "Access is denied" on a delete                  | ACL or ownership                  | the **read-only attribute** - not a permission, so `takeown`/`icacls` cannot fix it |
| Permission command says success, op still fails | need a bigger permission pass     | the **diagnosis is wrong** - inspect the object                                     |
| Access denied under a SYSTEM task               | not privileged enough             | **SYSTEM is a different principal** and often has less access than an admin         |
| Log silent for 40 minutes                       | hung, kill it                     | a **phase handover** - the next step writes to a different log                      |
| Delete stopped with N dirs left                 | N separate failures               | **one blocker** - the walk abandoned at the first                                   |
| Windows.old is 25 GB, deleting frees 11         | the delete was incomplete         | **hard links counted once each** - the byte total was never the reclaimable size    |

## A clean health check does not mean an update will install

`ScanHealth` measures component-store INTEGRITY. Whether a given update can install is a
different question, and the two diverge in both directions. Check free space first: a
cumulative update needs room for the download, the expanded payload and the rollback copy, so
20-25 GB free is a reasonable floor.

**Order for "the update fails and rolls back", cheapest discriminator first:**

```powershell
Get-PSDrive C | Select-Object @{n='FreeGB';e={[math]::Round($_.Free/1GB,1)}}   # 1. headroom
Get-WinEvent -FilterHashtable @{LogName='Setup'} -MaxEvents 40                  # 2. the real code
Select-String 'C:\Windows\Logs\CBS\CBS.log' -Pattern 'Error|0x8' | Select-Object -Last 40
DISM /Online /Cleanup-Image /ScanHealth /LogPath:C:\Temp\scan.log               # 3. ruling-OUT only
```

`0x80070070` / `ERROR_DISK_FULL` in those logs is the headroom fault. `ScanHealth` comes third
and only weakens or strengthens the corruption hypothesis - running it first is what leads to
treating a clean result as "not corruption, so look elsewhere" and missing the space.

Two distinct faults present identically as "the update fails and rolls back". Measured across a
17-machine fleet: two machines had a corrupt store, the rest simply had no room. A survey that
found the two corrupt ones was reported as the answer to "why won't the update install", and it
was true and off-target - the update had failed on healthy machines too.

Survey before repairing, though: it is the highest-value step on a fleet. It cut that job from
16 in-place upgrades to 2.

## "Access is denied" is usually the read-only attribute

The attribute is not a permission. It sits beside the DACL and is checked separately, so
`takeown` and `icacls` cannot clear it and every escalation is wasted.

It bites hardest because the error names permissions, so the fix that comes to mind is
permissions - and then `takeown` reports success and `icacls` reports 0 errors while the
operation keeps failing. That reads as a stubborn ACL rather than a wrong diagnosis, and invites
a bigger pass.

**A permission command that succeeds while the operation still fails means the diagnosis is
wrong.** Inspect the object:

```powershell
(Get-Item $path).Attributes      # ReadOnly? that is your answer
Remove-Item $path -Force         # -Force clears it; rd /s /q does not
```

Files inherit it from any read-only source. Copy off an ISO or a mounted image and the copy
looks fine, then `DISM /Mount-Wim` fails `0xC1420127` claiming you only have read permissions -
about a file you own. Clear it after any such copy.

## Batch tools abandon the whole walk at the first bad entry

`rd /s /q` and `attrib /S` both stop at the first entry they cannot handle. So a partial result
is ONE blocker, not N failures, and re-running reproduces the same stop in the same place.

Work per entry with error continuation, and the run reports every blocker instead of the first:

```powershell
foreach ($f in Get-ChildItem $root -Recurse -File -Force) {
    try { Set-ItemProperty $f.FullName IsReadOnly $false -EA Stop } catch { }
    try { Remove-Item $f.FullName -Force -EA Stop } catch { <# record, continue #> }
}
```

Order matters when both faults are present: `attrib` itself needs access, so ownership and
rights come first - `takeown /r`, then `icacls /grant`, then the attribute, then the delete.

## Never `icacls /reset` a Windows.old

An in-place upgrade builds `Windows.old` largely from **hard links** to the live installation,
and an ACL belongs to the file, not the directory entry. `/reset` strips explicit ACEs through
every link, so it rewrites what the RUNNING system sees.

Measured: `icacls C:\Windows.old /reset /t` stripped the explicit ACEs from the SSH host keys and
a user profile. sshd then refused every host key ("Permissions are too open",
`no hostkeys available -- exiting`) and the machine dropped off the network, needing console
recovery. `/grant` is additive and cannot remove an ACE a service depends on. Use it.

Deleting a hard link is safe - it only decrements the link count. Rewriting permissions through
one is not. That is the whole distinction.

## Deleting a Windows.old: the fast path, and what it really reclaims

**Discard a mounted image inside the tree before deleting anything.** An interrupted servicing
run can leave a WIM mounted at `C:\Windows.old\$WinREAgent\Scratch\Mount`, and deleting a tree
around a live mount corrupts the mount state. It survives reboots and reports `Status : Invalid`,
so nothing draws attention to it:

```powershell
dism /English /Get-MountedImageInfo          # any Mount Dir under the target?
dism /English /Cleanup-Mountpoints           # discards stale/invalid mounts
```

Abort rather than delete if a mount is still listed afterwards.

**A `Windows.old` contains links that point OUT of the tree.** Measured on a 25H2 guest:

```
C:\Windows.old\Users\All Users      <SYMLINKD>  ->  C:\ProgramData
C:\Windows.old\Users\Default User   <JUNCTION>  ->  C:\Users\Default
C:\Windows.old\ProgramData\Desktop  <reparse>   ->  C:\Users\Public\Desktop
```

Anything that RECURSES through one reaches the live OS - the same failure family as
`icacls /reset`. `robocopy /MIR` does, and **`/XJ` does NOT stop it.** Measured on a scratch
fixture (a tree holding one JUNCTION and one SYMLINKD to a victim directory of 5 files):

| Method                                         | Victim files left | Verdict     |
|------------------------------------------------|-------------------|-------------|
| `robocopy $empty tree /MIR /XJ`                | 0 of 5            | DESTRUCTIVE |
| `rd /s /q tree`                                | 5 of 5            | safe        |
| `Remove-Item tree -Recurse -Force`             | 5 of 5            | safe        |
| strip reparse points, then `robocopy /MIR /XJ` | 5 of 5            | safe        |

`/MIR` is `/E` plus `/PURGE`. `/XJ` governs the SOURCE traversal; the purge walks the DESTINATION
to find extras to delete and follows reparse points there regardless. So `/XJ` reads like
protection and provides none - do not reach for it as the fix.

On a real guest the mirror walks `All Users` into the live `C:\ProgramData` and empties it while
reporting success. The first symptom is not a file error: SSH starts refusing the key, because
`C:\ProgramData\ssh` holds the host keys and `administrators_authorized_keys`. Then the console
goes black and the guest is recoverable only from a snapshot. **Snapshot before any of this.**

**The safe fast path: strip the link ENTRIES first, then mirror.** `rd /q` on a junction or
directory symlink removes the link, never its target:

```powershell
# 1. remove every reparse point in the tree - THIS is what makes the mirror safe, not /XJ
Get-ChildItem C:\Windows.old -Recurse -Directory -Force -Attributes ReparsePoint -EA SilentlyContinue |
    ForEach-Object { cmd /c rd /q "`"$($_.FullName)`"" }

# 2. now the purge cannot leave the tree
$empty = Join-Path $env:TEMP ([guid]::NewGuid())
New-Item -ItemType Directory $empty | Out-Null
robocopy $empty C:\Windows.old /MIR /XJ /R:0 /W:0 /MT:16 /NFL /NDL /NJH /NP
cmd /c rd /s /q C:\Windows.old               # removes the emptied shell
```

**Prove it did not escape, every time.** Count the link TARGETS before and after. Equal counts are
the evidence; "the delete finished" and "robocopy exited 0-7" are not, because this failure reports
success. Run this before step 1 and again after step 2:

```powershell
@{ PD    = @(Get-ChildItem 'C:\ProgramData' -Directory -Force -EA SilentlyContinue).Count
   PDf   = @(Get-ChildItem 'C:\ProgramData' -Recurse -File -Force -EA SilentlyContinue).Count
   Ssh   = @(Get-ChildItem 'C:\ProgramData\ssh' -File -Force -EA SilentlyContinue).Count
   Deflt = @(Get-ChildItem 'C:\Users\Default' -Force -EA SilentlyContinue).Count
   Pub   = @(Get-ChildItem 'C:\Users\Public\Desktop' -Force -EA SilentlyContinue).Count }
```

Any count lower afterwards means it escaped: restore the guest from the snapshot taken above
(hypervisor snapshot, VSS, whatever the platform provides - take it while the guest is stopped or
filesystem-frozen). Do not try to repair `C:\ProgramData` in place.

`rd /s /q` and `Remove-Item -Recurse -Force` are safe on their own for the same reason (they
delete a link entry without descending) and need no strip pass - use them when speed does not
matter. `rd /s /q` abandons the whole walk at the first entry it cannot handle, and a measured
`Remove-Item` pass took ~73 min on a tree the two-step above clears far faster.

Then run the per-file pass only if anything survived. **Expect residue above `MAX_PATH`**:
measured, 16 files remained whose longest path was 262 characters, attributes plain `Archive` -
no permission work was warranted and none would have helped. robocopy cleared them in about a
second, because it handles long paths natively and `Remove-Item` does not.

**The byte total overstates the reclaim by two to three times.** `robocopy /L ... /BYTES` sums
FILE SIZES, and a Windows.old is full of hard links, so the same physical blocks are counted once
per link. Measured:

| Files   | Reported | Actually freed | Inflation |
|---------|----------|----------------|-----------|
| 163,835 | 22.82 GB | 7.48 GB        | 3.05x     |
| 569,731 | 25.12 GB | 11.30 GB       | 2.22x     |

Sampling 60 files under `Windows.old\Windows\System32` found 60 of 60 carrying multiple links,
every one pointing at another path INSIDE `Windows.old` (the System32-to-WinSxS pair), not into
the live install. So the space does come back - the figure was inflated, not shared. Size the
expectation from unique data, and never promise the byte total as free space.

**Time scales with FILE COUNT, not size.** Those two runs differed by 1.1x in bytes, 3.5x in file
count, and 6.2x in elapsed time (13.3 min against 83.0 min), with no permission work in either.
Count the files before estimating; a tree of comparable size can take six times longer.

## A SYSTEM task can have LESS access than an admin session

SYSTEM is a different principal from Administrators, not a superset. Servicing files commonly
grant `SYSTEM: ReadAndExecute` while Administrators and TrustedInstaller hold more, so a
scheduled task running as SYSTEM is weaker than an ordinary elevated session.

Measured on one set of 49 files, same script, same minute:

```
as SYSTEM (schtasks /ru SYSTEM /rl HIGHEST):  0 of 49 deleted
as an admin over SSH:                        49 of 49 deleted
```

The failure is an access-denied, which argues for MORE elevation - and SYSTEM looks like the
ceiling. The fix is sideways, not up: **re-run the identical command from an elevated
administrator session** (Windows OpenSSH hands an admin an unfiltered token, so
`ssh admin@host powershell -File x.ps1` is enough). Read the file's ACL first - if
Administrators or TrustedInstaller hold rights SYSTEM does not, that is your answer. Test it on
one file; it takes seconds and settles the question.

## Choosing the remedy

`RestoreHealth` PATCHES individual payloads and must resolve each at its exact revision, so it
fails `0x800F0915` when no source holds them (returned signed as `-2146498283`). An in-place
repair upgrade REPLACES the store wholesale and resolves nothing.

Light damage: repair. Widespread payload corruption: upgrade. There is no numeric threshold -
judge it by whether `RestoreHealth` can actually resolve what it wants, which is one run, so
try the repair first and let `0x800F0915` make the decision for you. On a fleet, run it on ONE
machine as a cheap probe before committing to the expensive path everywhere.

A real installed peer beats an ISO as a repair source - it carries the actual language variants
and revisions, which a single-language ISO cannot. Point `/Source:` at a mounted image or a
peer's live store, and add `/LimitAccess` only if you want to forbid the fallback to Windows
Update (usually leave it off - WU covers post-RTM payloads no local source has):

```
DISM /Online /Cleanup-Image /RestoreHealth /Source:wim:D:\sources\install.wim:1
DISM /Online /Cleanup-Image /RestoreHealth /Source:\\PEER\C$\Windows\WinSxS
```

Pick the image INDEX by matching the edition, never by position - index 1 is Home on a retail
ISO and will not repair a Pro install.

Running the upgrade unattended:

```
setup.exe /auto upgrade /quiet /eula accept /noreboot /compat ignorewarning /dynamicupdate disable
```

`/eula accept` is REQUIRED with `/quiet`. Without it setup runs about 30 seconds and exits
`0xC190010E`; the code points nowhere, while the log says "User did not accept EULA at downlevel
OS". `/dynamicupdate disable` keeps the run reproducible. On a CPU not on the supported list,
`0xC1900200` is cleared by the documented `AllowUpgradesWithUnsupportedTPMOrCPU` key under
`HKLM\SYSTEM\Setup\MoSetup` - which is NOT the LabConfig `Bypass*Check` family and leaves TPM and
Secure Boot enforcement intact.

## Monitoring: what a quiet log means

DISM's log path is **per-invocation**. A step that omits `/LogPath` falls back to the default
log, so a monitor pinned to one file watches something nothing writes any more - and a phase
handover looks exactly like a freeze. Pass `/LogPath` to EVERY invocation.

A quiet log is not a stall. Read its last lines: a clean
`DISM.EXE: <----- Ending Dism.exe session ----->` means that phase SUCCEEDED.

Watch phase markers plus worker CPU, never disk delta or log size - both go flat for long
stretches during real work. Choose a log by `LastWriteTime`, never by size: size correlates with
age, so "biggest" actively selects the stalest file. Print the chosen path with its age.

Keep one non-log signal. When comparing a counter across samples use a tolerance, never exact
equality - a value that jitters resets an exact-match stall counter every sample, so the stall
branch can never fire.

## Durations: measure, do not quote

Servicing is storage-bound and varies enormously. The same in-place upgrade measured **1 hour on
one machine and 5h18m on another on the same host**. A `Windows.old` teardown ran ~3h45m of
permission work that reclaimed nothing, then deleted in 11 minutes.

A delete with NO permission work at all still ranged 13.3 min to 83.0 min across two guests whose
trees differed by only 1.1x in bytes - file count drove it, not size.

Quote a reference figure and you will understate the expensive path and make the cheap
preparatory step (survey first, repair only what is broken) look not worth running. Calibrate
against one measured run on the target before sizing a fleet plan, or say the estimate is
unmeasured.

## Red flags - stop and re-diagnose

- A permission command reported success and the operation still fails
- You are about to run `icacls /reset` on a `Windows.old`
- You are about to run `robocopy /MIR` against a `Windows.old` whose reparse points are still there
- You are treating `/XJ` as the thing that makes that mirror safe - it is measured not to be
- You deleted a `Windows.old` and did not count `C:\ProgramData` before and after
- SSH stopped accepting the key right after a `Windows.old` delete - you emptied `C:\ProgramData`
- You are about to escalate to SYSTEM because admin was denied
- You concluded "hung" from a quiet log or flat disk without checking worker CPU
- You are quoting a duration you did not measure on this machine
- You are treating a clean `ScanHealth` as proof an update should install
- You are quoting a `robocopy` byte total as the space a delete will free
- You are about to delete a tree without checking for a mounted image inside it

## Common mistakes

- Adding an exclusion for each locked file during a live capture. Snapshot instead - a VSS
  shadow copy has no open handles, so the whole failure class disappears
  (`Invoke-CimMethod Win32_ShadowCopy Create`; `vssadmin create shadow` is Server-only).
- Reading `cleanmgr`'s exit code. It returns 0 while silently declining the "Previous
  Installations" handler under a non-interactive session. Check the directory.
- Hard-stopping a guest mid-update. That is how component stores get damaged in the first place.
