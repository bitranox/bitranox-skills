---
name: infra-windows-servicing
description: Use when a Windows machine will not install a cumulative update, its component store is damaged, DISM or setup.exe fails with an opaque code (0x800F0915, 0xC1900200, 0xC190010E, 0xC1420127, 0x80070020), an in-place upgrade reverts itself on the apply reboot ("undoing changes", "Vorgenommene Aenderungen werden rueckgaengig gemacht"), a delete of Windows.old refuses with "Access is denied" / "Zugriff verweigert" despite takeown and icacls succeeding, a CBS log search returns nothing for an update that provably failed, a long servicing job looks hung, or an in-place repair upgrade is being planned or run.
---

# Windows servicing and repair: the traps

Repairing a Windows component store is not hard to execute - the commands are well known. It
is hard because several distinct failures all surface as **"Access is denied"**, a **quiet log**,
or a **clean health report**, so a competent operator confidently fixes the wrong thing. This
skill is the set of those false signals, each with the measurement behind it.

Assume you already know `DISM`, `takeown`, `icacls` and `setup.exe`. Read this for what they
do not tell you.

## The false signals

| Symptom                                         | The obvious reading               | What it usually is                                                                        |
|-------------------------------------------------|-----------------------------------|-------------------------------------------------------------------------------------------|
| Update fails, `ScanHealth` clean                | not corruption, so look elsewhere | **disk headroom** - a cumulative update needs far more free space than its own size       |
| "Access is denied" on a delete                  | ACL or ownership                  | the **read-only attribute** - not a permission, so `takeown`/`icacls` cannot fix it       |
| Permission command says success, op still fails | need a bigger permission pass     | the **diagnosis is wrong** - inspect the object                                           |
| Access denied under a SYSTEM task               | not privileged enough             | **SYSTEM is a different principal** and often has less access than an admin               |
| Log silent for 40 minutes                       | hung, kill it                     | a **phase handover** - the next step writes to a different log                            |
| Delete stopped with N dirs left                 | N separate failures               | **one blocker** - the walk abandoned at the first                                         |
| Windows.old is 25 GB, deleting frees 11         | the delete was incomplete         | **hard links counted once each** - the byte total was never the reclaimable size          |
| Upgrade reverts on reboot, down-level was `0x0` | the upgrade failed, retry it      | **the apply was cut off** - `0x0` says the down-level was fine, so check the reboot       |
| Monitor reports an unknown build for hours      | the upgrade is stuck              | **the monitor was deleted** - it was staged under a path the upgrade replaces             |
| `wmic` prints nothing at all                    | the machine has no such objects   | **`wmic` is removed in 25H2** - it returns EMPTY, not an error                            |
| A wrapper says the job wrote no verdict         | the job failed                    | **a failed READ of the log** - ask the guest, whose log may say success                   |
| Strip pass "completed", 48 of 51 links removed  | 3 benign leftovers                | **the 3 the encoding mangled** - and those are the ones pointing out of the tree          |
| Week-old failure, `CBS.log` grep finds nothing  | no evidence, so not the store     | **the live logs cover days** - the history is in `CbsPersist_*.cab`, unreadable by a grep |
| `0xC1900200` survives the MoSetup waiver        | the key did not take effect       | **several blocks at once** - and the key does not waive an ABSENT TPM                     |

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
#    ^ live logs only: for anything older than a couple of days, expand the cabs first
DISM /Online /Cleanup-Image /ScanHealth /LogPath:C:\Temp\scan.log               # 3. ruling-OUT only
```

`0x80070070` / `ERROR_DISK_FULL` in those logs is the headroom fault. `ScanHealth` comes third
and only weakens or strengthens the corruption hypothesis - running it first is what leads to
treating a clean result as "not corruption, so look elsewhere" and missing the space.

This order is for an update that FAILED. An in-place upgrade whose down-level phase logged
`[Setup360Result]=[0x0]` and which then reverted on the reboot did not fail here, and none of
these three reads will show anything: see "An interrupted apply reverts the WHOLE upgrade".

Two distinct faults present identically as "the update fails and rolls back". Measured across a
17-machine fleet: two machines had a corrupt store, the rest simply had no room. A survey that
found the two corrupt ones was reported as the answer to "why won't the update install", and it
was true and off-target - the update had failed on healthy machines too.

Survey before repairing, though: it is the highest-value step on a fleet. It cut that job from
16 in-place upgrades to 2.

### The CBS log you can grep covers only a few days

`C:\Windows\Logs\CBS` keeps a couple of live `.log` files spanning a few days. Everything older is
rolled into `CbsPersist_<timestamp>.cab`, and a `.cab` is an ARCHIVE - `Select-String` cannot read
it. So on a machine whose update provably failed last week, a grep of the `.log` files returns
ZERO hits, which reads exactly like a clean store. Expand the cabs FIRST, then search:

```powershell
New-Item -ItemType Directory C:\cbs-extract -Force | Out-Null
Get-ChildItem C:\Windows\Logs\CBS -Filter *.cab | ForEach-Object {
    expand.exe -F:* $_.FullName C:\cbs-extract          # never into Out-Null - see below
}
Select-String C:\cbs-extract\* -Pattern 'failure source:|ERROR_'
```

**Never pipe `expand.exe` into `Out-Null`.** It then reports "extracted: 0 logs" and gives no reason
at all. Show its output and `$LASTEXITCODE`, and list a cab's contents with `expand -D <cab>` when it
extracts nothing - discarding the output of the very tool you are diagnosing is what makes the
failure unreadable.

The size gap is the tell that a zero-hit grep is a missed search rather than a clean store: a 138 MB
`CBS.log` inside a 1.4 GB `CBS` directory means the other 1.2 GB is history you have not read. How
far back the live logs reach is not a fixed number of days - it follows how much servicing traffic
the machine has generated - which is why the gap, and not a date arithmetic, is what tells you.

The broader pattern is deliberate: `failure source:|ERROR_` catches the SYMBOLIC names across the
whole expanded set, where `Error|0x8` on the live log is a numeric-code scan. If the expanded search
is also empty, the retained cabs do not reach back to the failure - CBS history for that date is
gone, and the `Setup` event log entry plus the Panther logs are all that is left of it.

Take the SYMBOLIC error name CBS prints beside the HRESULT rather than looking the number up: the
line reads `[HRESULT = 0x80071a2d - ERROR_TRANSACTION_NOT_ACTIVE]`, and the name is the part that
tells you what happened.

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
$rp = @(Get-ChildItem C:\Windows.old -Recurse -Directory -Force -Attributes ReparsePoint -EA SilentlyContinue)
foreach ($d in $rp) {
    # recurse:$false removes the link ENTRY and never descends into the target, same as rd /q
    try { [System.IO.Directory]::Delete($d.FullName, $false) }
    catch { Write-Warning "LEFT: $($d.FullName) - $($_.Exception.Message)" }
}

# 1b. GATE: re-enumerate and abort if any survived. Do not trust the loop's own tally.
$left = @(Get-ChildItem C:\Windows.old -Recurse -Directory -Force -Attributes ReparsePoint -EA SilentlyContinue)
if ($left.Count) { $left.FullName; throw "$($left.Count) reparse point(s) remain - the mirror is NOT safe" }

# 2. now the purge cannot leave the tree
$empty = Join-Path $env:TEMP ([guid]::NewGuid())
New-Item -ItemType Directory $empty | Out-Null
robocopy $empty C:\Windows.old /MIR /XJ /R:0 /W:0 /MT:16 /NFL /NDL /NJH /NP
cmd /c rd /s /q C:\Windows.old               # removes the emptied shell
```

**Do the removals in-process. Never write those paths through an ASCII layer.** Emitting one
removal line per link into a `.cmd` batch mangles every non-ASCII name, and on a localised install
the interesting names are exactly the non-ASCII ones. Measured on a German guest: of 51 reparse
points 48 were removed and 3 SURVIVED - `Zubehoer` and two `Startmenue`, whose real names carry
umlauts - and all three pointed INTO the live OS:

```
Windows.old\Program Files\Windows NT\<Accessories, localised>  ->  C:\Program Files\Windows NT\Accessories
Windows.old\Users\<user>\<Start Menu, localised>               ->  C:\Users\<user>\AppData\Roaming\Microsoft\Windows\Start Menu
```

A strip pass that silently skips exactly the dangerous links is WORSE than no strip pass, because
the mirror that follows assumes it worked. That is what step 1b is for: it re-counts rather than
believing the pass, and it names each survivor instead of reporting a bare number.

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

**Four of the five are STRICT; one CHURNS on its own and needs a tolerance.** A live `C:\ProgramData`
gains and loses files with nothing touching it: measured 147707 to 147709 over 60 IDLE seconds. Compare
that counter with strict inequality and you manufacture an ESCAPED verdict on a clean delete, and the
remedy for ESCAPED is destroying a good machine.

| Counter                 | Comparison                     | Why                                           |
|-------------------------|--------------------------------|-----------------------------------------------|
| `PD` ProgramData dirs   | STRICT - any drop is an escape | install points; runtime never adds or removes |
| `Ssh` ssh key files     | STRICT                         | host keys; never churns                       |
| `Deflt` Users\Default   | STRICT                         | template profile; Windows does not write it   |
| `Pub` Public\Desktop    | STRICT                         | changes only on an explicit admin action      |
| `PDf` ProgramData files | TOLERANT - allow `max(50, 1%)` | drifts unprompted on a live machine           |

The tolerance costs no detection, because **an escape is never subtle**. In the real one, `PD` went
21 dirs to 18 and `Users\Default` went 29 entries to 0. Nothing about that needs a fine threshold.

Each row returns a VERDICT, not just a number. A `PDf` move inside the tolerance is NOT an escape
and is not a reason to hesitate: say so and move on. Treating it as an amber signal to weigh is how
a clean delete still ends up restored from a snapshot.

Read a STRICT drop as escaped: restore the guest from the snapshot taken above (hypervisor
snapshot, VSS, whatever the platform provides - take it while the guest is stopped or
filesystem-frozen). Do not try to repair `C:\ProgramData` in place.

Two cheap corroborations before you act on a verdict that expensive. Compare against a
BUILD-MATCHED healthy peer rather than against the counter alone, so you can tell this machine's
normal from a loss. And check the machine still serves SSH: `C:\ProgramData\ssh` is inside the
blast radius, so sshd is the canary and it dies within seconds of a real escape. A delete whose
structure matches a healthy peer, whose sshd is still answering, and which had zero reparse points
before the mirror, did not escape - an escape was structurally impossible.

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

A third measured run lands between them: the mirror of an emptied tree ran 58.7 min and took free
space from 33.98 GB to 54.13 GB, so 20.15 GB came back. `robocopy` exited `rc=2`. That is a normal
exit in the 0-7 band and it says nothing about whether the run stayed inside the tree - read the
counters, not the code.

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
OS". `/dynamicupdate disable` keeps the run reproducible.

### `0xC1900200` is a LIST of blocks, and the waiver does not cover an ABSENT TPM

When `0xC1900200` survives the waiver, the order is: read CompatData for the blocks that are
ACTUALLY set, fix each on its own terms, then re-read CompatData to confirm the scan re-ran. Do not
re-run `setup.exe` between those steps hoping the key took this time.

The documented `AllowUpgradesWithUnsupportedTPMOrCPU = 1` (DWORD) under `HKLM\SYSTEM\Setup\MoSetup`
waives an unsupported CPU and an unsupported TPM **version**. It is NOT the LabConfig `Bypass*Check`
family, and it leaves TPM and Secure Boot enforcement in the running OS alone. It is also not the
whole answer, because `0xC1900200` is a compat hard block that can be SEVERAL blocks at once. Read
which ones instead of assuming the one you have a fix for:

```powershell
[xml]$x = Get-Content (Get-ChildItem 'C:\$WINDOWS.~BT\Sources\Panther' -Filter 'CompatData*.xml' |
                       Sort-Object LastWriteTime -Descending)[0].FullName
$x.SelectNodes('//*[local-name()="HardwareItem"]') | ForEach-Object {
    $bt = ($_.SelectSingleNode('*[local-name()="CompatibilityInfo"]')).BlockingType
    if ($bt -and $bt -ne 'None') { "$($_.HardwareType) = $bt" }
}
```

Measured on a PVE guest with `cpu: host` and no `tpmstate0`: two hard blocks, `CpuFms` and
`TpmVersion`, everything else `None`. The key cleared `CpuFms` only. `TpmVersion` survived because
the guest had **no TPM at all** (`TpmPresent = False`), and the key waives an UNSUPPORTED version,
never an ABSENT device. Setup logs the tell:

```
UnrecognizedCompatBlockEncountered = [TpmVersion]
```

That one takes real hardware, not a registry value - on Proxmox VE, `qm set <vmid> -tpmstate0
<storage>:1,version=v2.0`, which needs a clean shutdown first. Verify with `(Get-Tpm).TpmPresent`
before relaunching.

**A faster second failure is not a cached verdict.** The obvious reading of "same code, 43 s instead
of 79 s" is that setup never re-ran the appraisal, or tripped an earlier gate - both send you to
clear `$WINDOWS.~BT` and retry, which changes nothing. Compare the CompatData file's timestamp
instead, which answers it either way: measured here it was FRESH, so the scan had genuinely re-run
and was faster because one of the two blocks was genuinely gone. A timestamp still matching the
PREVIOUS run is the case where setup never re-appraised, and only then is clearing `$WINDOWS.~BT`
the right move.

### An interrupted apply reverts the WHOLE upgrade

`/noreboot` arms a ONE-SHOT BCD `bootsequence` pointing at
`\$WINDOWS.~BT\NewOS\...\winload.efi`. The second stage runs only if the machine boots that entry,
and it is interruptible: cut it off partway and Windows reverts the entire upgrade, not just the
interrupted step.

**Read the down-level result before concluding the upgrade failed.** Measured on a reverted guest:

```
Overall progress: [100%]
Finalize: Reporting result value: [0x0]
[Setup360Result] = [0x0]                 # and registry RollbackCount = 1, InstallAttempts = 1
```

`Setup360Result = 0x0` means the down-level SUCCEEDED. A revert carrying `0x0` therefore says the
APPLY was cut off, so investigate how the machine rebooted rather than re-diagnosing the upgrade -
which is exactly where the obvious reading sends you. The whole point of the grep is that nothing
else announces this as a reboot problem: on a VM the machine is running afterwards, so every
host-side check reads normal, and only the console shows the revert, as "undoing changes made"
("Vorgenommene Aenderungen werden rueckgaengig gemacht").

On a VM, check ONE THING about your platform before the apply: does a guest-initiated reboot
genuinely restart the guest, or does it tear the VM down? Read the VM PROCESS identity across an
ordinary in-guest reboot - a genuine restart keeps the same hypervisor process, a teardown returns
a NEW one (on Proxmox VE, the PID column of `qm list`). Do it once, on any guest, well before you
need it; it costs a reboot and it is the only signal that separates the two, since the VM is
running afterwards either way. Where it tears the VM down, an in-guest
`shutdown /r` cuts the apply off mid-write and produces exactly the revert above; use the
hypervisor's clean stop plus start instead, since the boot entry lives in BCD ON DISK and survives
that. This is a property of the platform to verify once, NOT a general rule that in-guest reboots
are unsafe - it was one host's temporary behaviour and it was later fixed there. On Proxmox VE the
hypervisor form is:

```
qm shutdown <vmid>      # ACPI - the OS closes cleanly and flushes
qm status <vmid>        # wait for: stopped
qm start <vmid>         # fresh boot, honours the one-shot bootsequence
```

What no platform survives is being cut off mid-write - so **never a hard stop** (`qm stop` and its
equivalents), unconditionally. That is the documented way component stores get damaged, and the
store is the thing under repair.

**A rollback DELETES the staged NewOS, so re-arming the boot entry boots into nothing.** Measured
on a reverted guest: `$WINDOWS.~BT` still present (10.3 GB, 1567 files) but `$WINDOWS.~BT\NewOS`
ABSENT, the one-shot entry consumed, build back at its original value. Re-arming with `bcdedit` is
the tempting two-minute fix and it is a dead end. **This check is the decision, not a formality:**

```
if exist "C:\$WINDOWS.~BT\NewOS\Windows\System32\winload.efi" (echo REARMABLE) else (echo RERUN)
```

Present: re-arm and boot it. Absent: re-run the entire down-level from `setup.exe`. After a
rollback it is always the latter.

Before spending those hours again, settle WHY it reverted, because the re-run only helps if the
reboot was the cause. If the apply reboot was guest-initiated AND you have confirmed that route
tears the VM down on this platform, that is the cause and rebooting the other way fixes it. If the
reboot was already a clean stop/start, or the in-guest route restarts the guest properly here, do
not re-run blind - the revert has some other cause, and the down-level's own Panther log is where
it is recorded, not in the reads under "A clean health check".

## Monitoring: what a quiet log means

DISM's log path is **per-invocation**. A step that omits `/LogPath` falls back to the default
log, so a monitor pinned to one file watches something nothing writes any more - and a phase
handover looks exactly like a freeze. Pass `/LogPath` to EVERY invocation.

A quiet log is not a stall. Read its last lines: a clean
`DISM.EXE: <----- Ending Dism.exe session ----->` means that phase SUCCEEDED.

Watch phase markers plus worker CPU, never disk delta or log size - both go flat for long
stretches during real work. Choose a log by `LastWriteTime`, never by size: size correlates with
age, so "biggest" actively selects the stalest file. Print the chosen path with its age.

Keep one non-log signal. When comparing a counter across samples for STALL detection use a
tolerance, never exact equality - a value that jitters resets an exact-match stall counter every
sample, so the stall branch can never fire. (The blast-radius counters above are a different job
with a different rule: four of those are strict.)

**An in-place upgrade REPLACES `C:\Windows`, so it deletes whatever you staged under
`C:\Windows\Temp`.** A monitor left there is destroyed by the exact event it exists to observe,
and it fails silently: `powershell -File <deleted path>` prints a banner and exits 0. Measured:
two guests both reached the target build while the monitor reported an unknown build for 90
minutes. Stage monitoring outside `C:\Windows` entirely, or do not stage anything at all and read
the state cmd-natively:

```
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v CurrentBuild
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v UBR
bcdedit /enum "{bootmgr}" | findstr /i bootsequence
if exist "C:\$WINDOWS.~BT\NewOS\Windows\System32\winload.efi" (echo STAGED) else (echo NOSTAGE)
```

`UBR` comes back HEX: `0x230d` is 8973, `0x21cf` is 8655. Convert it, or you will compare a build
against a number it can never equal.

**Report "cannot read" separately from "not armed".** The two look identical in a boolean and only
one of them is a result. A reboot check that collapses them makes an unreachable guest read as a
clean negative, and then you act on a state you never observed.

**A tool's verdict is not the guest's verdict.** An orchestrating script reported its upgrade
worker "exited without writing a verdict" while the guest's own log had recorded success two
minutes earlier: the script's read of that log came back empty and it could not tell a failed READ
from an absent marker. When a wrapper reports failure, ask the GUEST before believing it - its own
state log, the registry build, the boot state.

**`wmic` is GONE in 25H2 and returns EMPTY rather than an error.**
`wmic logicaldisk get DeviceID,VolumeName,Size` produces no output at all, which reads as "no
drives" rather than "the tool is missing" - so an inventory step reports a machine with no disks
and nothing raises. Use `fsutil fsinfo drives` (cmd-native), or `Get-Volume` / `Get-Partition` /
`Get-Disk`.

## Durations: measure, do not quote

Servicing is storage-bound and varies enormously. The same in-place upgrade measured **1 hour on
one machine and 5h18m on another on the same host**. A `Windows.old` teardown ran ~3h45m of
permission work that reclaimed nothing, then deleted in 11 minutes.

A delete with NO permission work at all still ranged 13.3 min to 83.0 min across two guests whose
trees differed by only 1.1x in bytes - file count drove it, not size. A third measured 58.7 min
and reclaimed 20.15 GB, landing between them; three runs of the same procedure spread over a 6x
range with nothing wrong in any of them.

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
- A `CBS.log` grep came back empty for a failure older than a couple of days and you read that
  as no evidence, without expanding `CbsPersist_*.cab`
- You are re-running `setup.exe` after the MoSetup waiver without reading CompatData for which
  blocks are ACTUALLY set, or treating a faster second failure as a cached verdict
- You are quoting a `robocopy` byte total as the space a delete will free
- You are about to delete a tree without checking for a mounted image inside it
- An upgrade reverted and you are re-diagnosing it without grepping Panther for `Setup360Result`
- You are applying a staged upgrade on a VM whose in-guest reboot you have not confirmed actually
  restarts the guest rather than tearing it down
- You are re-arming `bootsequence` after a rollback without checking `NewOS` still exists
- Your strip pass wrote link paths through a `.cmd` file, or you did not re-count after it
- You are calling a delete ESCAPED on a live machine's recursive `ProgramData` FILE count
- You staged a monitor under `C:\Windows\Temp` and are waiting on it across an upgrade
- A check reports "not armed" and you cannot tell that from "could not read the guest"
- You are believing a wrapper's failure verdict without asking the guest
- A `wmic` query came back empty and you read it as the machine having none

## Common mistakes

- Adding an exclusion for each locked file during a live capture. Snapshot instead - a VSS
  shadow copy has no open handles, so the whole failure class disappears
  (`Invoke-CimMethod Win32_ShadowCopy Create`; `vssadmin create shadow` is Server-only).
- Reading `cleanmgr`'s exit code. It returns 0 while silently declining the "Previous
  Installations" handler under a non-interactive session. Check the directory.
- Hard-stopping a guest mid-update. That is how component stores get damaged in the first place.
  A clean ACPI stop is not this: the prohibition is on cutting the guest off mid-write, not on
  stopping it at all.
