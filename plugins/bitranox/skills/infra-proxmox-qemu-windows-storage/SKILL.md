---
name: infra-proxmox-qemu-windows-storage
description: Use when a Windows VM on Proxmox with QEMU and ZFS zvol storage is slow, wastes pool space, or will not boot after a disk change - moving a boot disk to virtio-scsi without INACCESSIBLE_BOOT_DEVICE 0x7B or recovery 0xc0000001, choosing virtio-scsi over SATA/AHCI, sizing volblocksize against the guest's write size, discard and ssd emulation, why TRIM frees nothing while a snapshot exists, why BitLocker makes ZFS compression useless, and iothreads. Covers QEMU/KVM guests only, not OpenVMM. Prefer this over reasoning from read-modify-write or hand-rolling a diskspd run.
---

# Windows guest storage on Proxmox, QEMU and ZFS

Scoped to **QEMU/KVM** guests. Proxmox can also run OpenVMM guests, which present storvsc, NVMe
and virtio-blk instead, so the controller half of this does not transfer:

| Applies to                                                                                        | Transfers to OpenVMM        |
|---------------------------------------------------------------------------------------------------|-----------------------------|
| Controller choice, `scsihw`, scsi-index-to-PCI-address mapping, `vioscsi`, AHCI, `iothread`       | No - different device model |
| `volblocksize`, `discard`/TRIM, snapshots pinning trimmed blocks, BitLocker, the benchmark method | Yes - ZFS and guest side    |

Numbers below are measurements on a single-vdev NVMe pool, `ashift=12`, QEMU 11, DiskSpd 2.2,
16 threads at QD8, ARC evicted cold, three interleaved reps. Treat them as directions with an
order of magnitude, not as constants.

## The false signals

| Symptom                                          | Obvious reading             | What it usually is                                      |
|--------------------------------------------------|-----------------------------|---------------------------------------------------------|
| 0x7B / 0xc0000001 after moving to virtio-scsi    | driver not installed        | driver fine; the target scsi INDEX was never enumerated |
| `vioscsi Start=0`, controller Status OK          | ready to move the boot disk | proves PnP-time binding, says nothing about boot time   |
| Guest frees 100 GB, pool frees nothing           | TRIM is broken              | a snapshot pins every trimmed block                     |
| `compressratio 1.00x` on a Windows disk          | data is incompressible      | BitLocker; ciphertext cannot compress                   |
| Small random writes are slow                     | volblocksize too large      | maybe the reverse - see the fill rule                   |
| `CM_PROB_NORMAL_CONFLICT` on a virtio controller | driver or resource fault    | you hotplugged it; reboot reassigns PCI resources       |
| VM stops seconds after `qm start`                | start failed                | it booted, failed, and powered off - read the console   |

## Moving a boot disk to virtio-scsi

**With `scsihw=virtio-scsi-single`, PVE creates one virtio-scsi-pci controller PER DISK, and the
PCI address comes from the scsi INDEX.** Windows records each controller as its own device
instance, and **the boot loader can only bind `vioscsi` to an instance it has already
enumerated.**

| conf key | QEMU controller | PCI addr | Windows Enum instance suffix |
|----------|-----------------|----------|------------------------------|
| `scsi0`  | `virtioscsi0`   | `0x1`    | `0820F0`                     |
| `scsi1`  | `virtioscsi1`   | `0x2`    | `1020F0`                     |
| `scsi2`  | `virtioscsi2`   | `0x3`    | `1820F0`                     |
| `scsi3`  | `virtioscsi3`   | `0x4`    | `2020F0`                     |

Beyond the table the rule is `device = index + 1`, and the suffix is that device number shifted
left three bits: `scsi4` is device 5, `0x28`, suffix `2820F0`.

So the pre-bind scratch disk **must occupy the same scsi index the boot disk will end up on.**
Pre-binding on `scsi1` and then moving the boot disk to `scsi0` enumerates the wrong controller
and bugchecks 0x7B. The index is not cosmetic and it is not "invisible to Windows".

What makes this trap convincing: the scratch disk on the wrong index **looks perfectly healthy the
entire time.** It appears in the guest, the controller reports `Status OK`, the driver binds. Every
check passes, and none of them is a check on the index the boot disk is actually going to.

This whole mechanism is specific to `virtio-scsi-single`. Plain `virtio-scsi` puts every disk on
one shared controller, so there is only ever one instance to enumerate and the index stops
mattering - but you also lose per-disk `iothread`, which is most of the reason to be here.

```bash
# 0. scsihw must be SET. Absent means PVE defaults to lsi53c895a, not virtio.
qm config 100 | grep -c '^scsihw' || qm set 100 --scsihw virtio-scsi-single

# 1. Scratch disk AT THE TARGET INDEX (boot disk will become scsi0, so scratch goes to scsi0).
qm set 100 --scsi0 local-zfs:2,iothread=1,discard=on,ssd=1,backup=0
qm start 100
```

In the guest, confirm the instance now exists and is healthy before going further:

```powershell
Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Enum\PCI' |
  Where-Object { $_.PSChildName -match 'DEV_1004' } |
  ForEach-Object { Get-ChildItem $_.PSPath | ForEach-Object { $_.PSChildName } }
Get-PnpDevice -Class SCSIAdapter | Where-Object { $_.InstanceId -match 'DEV_1004' } |
  Select-Object Status, Problem
```

Require the target suffix in the list and `Status OK` / `CM_PROB_NONE`. Then swap:

```bash
qm shutdown 100                       # wait for status: stopped
qm set 100 --delete scsi0             # detaches the scratch into unusedN
qm set 100 --delete unused0           # frees the scratch volume
qm set 100 --scsi0 local-zfs:vm-100-disk-1,iothread=1,discard=on,ssd=1
qm set 100 --boot order=scsi0
qm set 100 --delete sata0
qm start 100
```

Confirm with a **second** reboot: one success can be a repaired binding rather than a stable one.
"Booted" means the guest's actual workload came back, not that it reached a logon screen or that
`qm status` reads running.

**Tell the two failure screens apart, they point different ways.** `0x7B` is a kernel-stage
bugcheck: firmware and `bootmgfw.efi` found the disk, and the storage driver then failed - the
index problem above. Recovery `0xc0000001` before the kernel loads points instead at the boot
entry or BCD. If the disk is not visible in a WinRE `diskpart`, it is the driver after all.

**Not sufficient, individually or together:** `vioscsi Start=0`; the driver installed and the
controller reporting `Status OK` at PnP time; a `CriticalDeviceDatabase` entry for
`pci#ven_1af4&dev_1004`. All three can hold while the move still fails.

**If it already failed:** one Safe Mode boot repairs the binding for the instance that exists.
Afterwards clear the flag, or the guest boots Safe Mode forever:

```powershell
bcdedit /enum "{current}" | Select-String safeboot     # expect no match
bcdedit /deletevalue "{current}" safeboot              # only if one is set
```

**Do not set `cache=` while moving.** The disk arrives with whatever cache mode the old key had;
adding one changes two variables and makes any before/after unattributable.

## Controller choice

| Profile         | virtio-scsi | SATA/AHCI | Gain  |
|-----------------|-------------|-----------|-------|
| 4K random write | 30,510      | 12,306    | +148% |
| 8K random write | 41,333      | 11,942    | +246% |
| 4K random read  | 82,626      | 12,501    | +561% |

AHCI pins every profile near 12,000 IOPS. PVE also refuses `iothread` on anything but
`virtio-blk` or `virtio-scsi-single`, so an AHCI disk additionally runs its I/O on the QEMU main
loop. This is the largest single lever; do it before tuning anything underneath it.

## volblocksize: match the write, not the cluster

**Whichever block size the write FILLS wins**, because a full-block write skips the
read-modify-write. Measured on virtio-scsi: 8K writes on an 8K zvol beat a 16K zvol by +152%
(ranges non-overlapping); 4K writes and 4K reads sat inside the noise floor. The read-modify-write
argument alone predicts the wrong answer, because halving the block also doubles block count and
metadata.

Size it from what the guest actually writes, not from the 4K NTFS cluster:

```powershell
$a = Get-CimInstance Win32_PerfRawData_PerfDisk_PhysicalDisk | ? Name -ne '_Total'
Start-Sleep 30
$b = Get-CimInstance Win32_PerfRawData_PerfDisk_PhysicalDisk | ? Name -ne '_Total'
# avg bytes per write = delta DiskWriteBytesPersec / delta DiskWritesPersec
```

`volblocksize` cannot be changed in place - it needs the zvol recreated and the data copied. On
AHCI the two block sizes differed by 1.3%, so block size is only worth tuning once the controller
is right.

## discard and ssd: both load-bearing

- Without `discard=on`, guest TRIM never reaches the zvol and freed space accrues as dead blocks
  that `logicalreferenced` keeps charging for.
- Without `ssd=1`, Windows reports the disk as rotational and its scheduled Optimize Drives job
  runs a **defragmentation**, which on a copy-on-write zvol rewrites blocks that snapshots share.

Verify from the guest with `Get-PhysicalDisk | Select MediaType` (expect `SSD`) and
`fsutil behavior query DisableDeleteNotify` (expect 0).

## TRIM frees nothing while a snapshot exists

TRIM moves blocks out of `referenced` and into `usedbysnapshots`; the pool gets nothing back
until the snapshots are destroyed. Two snapshots covering the same blocks each hold the full set,
so **deleting one of them frees nothing.** After destroying them, ZFS releases asynchronously -
read `zpool get freeing` before concluding the space did not come back.

```bash
zfs get used,referenced,logicalreferenced,usedbysnapshots <pool>/vm-100-disk-1
```

`logicalreferenced` far above the guest's used figure is the tell that TRIM has never reached the
zvol.

## BitLocker defeats ZFS compression

Ciphertext does not compress. A BitLocker-encrypted Windows disk measured `compressratio`
**1.00x**; decrypting it took the same disk to **1.33x** and shrank it further on its own, because
decryption rewrites every block as plaintext.

Check `ProtectionStatus` and the key protectors, not just `VolumeStatus`: a volume can sit
`FullyEncrypted` with `ProtectionStatus Off` and **no key protectors at all**, which is every cost
of encryption and none of the protection.

```powershell
Get-BitLockerVolume | Select MountPoint, VolumeStatus, ProtectionStatus, KeyProtector
```

## iothreads: measure, do not reason

At identical total load (16 threads, QD8 either way), one iothread measured **42,517** IOPS
against **36,157** for two - more iothreads were *slower*. The busy iothread peaked near 65% of
one core, so the ceiling is the ZFS backend, not the queue.

Do not argue from utilisation in either direction. "Not saturated, so nothing to gain" is invalid,
and so is the queueing-theory correction to it (an M/M/1 server at rho=0.65 already waits about
1.9x service time). Only the A/B settles it.

QEMU 11 auto-sizes virtio-scsi `num_queues` to the vCPU count already; read it back as
`vectors = num_queues + 3` in `info qtree`. PVE exposes a `queues=` disk option, but only for
`virtio-scsi-single`, and it is not needed.

## Benchmarking this stack

- **`-Z1G`** or DiskSpd writes a compressible pattern and you measure lz4, not the disk.
- **`-Sh`** (unbuffered, writethrough), not `-Su`. With `-Su` a sequential run reported
  7,723 MiB/s on a device whose PCIe 3.0 x4 ceiling is about 3.9 GB/s - that was ARC, not storage.
- **Evict ARC before every run.** Lower `zfs_arc_min` **and** `zfs_arc_max`, *then*
  `echo 3 > /proc/sys/vm/drop_caches`. Either half alone does nothing: `arc_max` is clamped by
  `arc_min`, and `drop_caches` alone floors at `arc_min`.
- **Verify the fixture.** Every arm must show matching `logicalreferenced` and `compressratio`
  near 1.00x, or the arms are not comparable.
- **Prove the guest-disk-to-zvol mapping** with a differential write probe (write a different
  amount to each disk, then read the zvol sizes) before trusting any number. A swapped mapping
  inverts the conclusion silently.
- **Interleave arms within each rep** and report a noise floor. Discard profiles that will not
  hold still - a 70/30 random mix measured about 50% spread on both arms and was bimodal.

An automated verdict rule fails in both directions: comparing an effect against a spread called a
non-overlapping result "noise" because one arm had an outlier, and called a bimodal 50%-spread
result a 74% winner. Look at the reps.

## Diagnosis

**Read the console.** `qm monitor` plus `screendump` is the reliable way to see what a guest is
actually showing; an SSH or agent timeout is a reachability failure, not a boot failure.

```bash
echo "screendump /tmp/vm.ppm" | qm monitor 100
```

An empty or all-black dump means the VM is not running, not that the screen is blank.

**Diff against a known-good guest first.** When one VM boots from virtio-scsi and another does
not, dump both guests' `Enum\PCI` instances, `Services\vioscsi`, and `CriticalDeviceDatabase` side
by side. The enumerated-instance difference is invisible to every single-guest check.

`CM_PROB_NORMAL_CONFLICT` (code 12) on a freshly hotplugged virtio controller is PCI resource
exhaustion from the hotplug itself, not a driver fault. Reboot and re-read it.

## Common mistakes

| Mistake                                                           | Consequence                                                                           |
|-------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| Pre-binding the scratch disk at a different index than the target | 0x7B on the move, with the driver perfectly installed                                 |
| Treating the scsi index as cosmetic                               | same, and the reasoning survives review because it sounds right                       |
| Assuming `scsihw` unset means virtio                              | disk lands on an LSI controller                                                       |
| `qm set --delete scsiN` expecting the volume to be freed          | it detaches into `unusedN`; destroying the zvol behind it leaves a dangling reference |
| Verifying the config with a filtered grep                         | `unusedN` lines and `parent:` snapshots never appear                                  |
| Reading pool free space immediately after destroying snapshots    | ZFS frees asynchronously; check `zpool get freeing`                                   |
| Quoting an elapsed time from a duration-limited benchmark run     | it measures the `-d` value you chose, not throughput                                  |
