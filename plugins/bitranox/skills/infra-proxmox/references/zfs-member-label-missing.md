# ZFS Member UNAVAIL: "label missing or invalid" With No Partitions

Symptom: after a reboot a pool is DEGRADED, one member shows UNAVAIL with
`label missing or invalid`, and the disk itself is visible (`lsblk`, `/dev/disk/by-id/`) but none
of its partitions appeared. A passing overall SMART health check does not explain it either way.

A common cause is a corrupt PRIMARY GPT on a healthy disk. A SATA link error at boot can abort the
reads of the disk's first sectors, where the primary GPT lives, so the kernel creates no partition
devices and ZFS finds no label, while the SECONDARY GPT at the end of the disk stays intact. That
disk is recoverable in place.

## Find the cause before replacing anything

- **Kernel log of the boot where it dropped** (`journalctl -k -b`, or `-b -1` for the previous
  boot): look on the disk's ATA port for a link exception (`exception Emask`, `SErr`), an
  `Aborted Command`, and a link speed downshift (for example to 3.0 Gbps).
- **SMART counters, not the verdict** (`smartctl -A /dev/X`): 0 reallocated, pending and
  offline-uncorrectable sectors together with a non-zero `UDMA_CRC_Error_Count` mean transfer
  errors on the link, that is a cable or connector fault rather than failing media. Compare the
  siblings: members on good cables read 0.
- **The partition table:** `sgdisk -p /dev/X` warns that the main GPT header is invalid while the
  backup is valid.

## Recover in place

1. `sgdisk --backup=FILE /dev/X` saves the intact table (a read-only step). Keep FILE somewhere
   durable, never on that disk.
2. `sgdisk -p /dev/X`: check the layout is the expected one (the ZFS data partition plus the small
   reserved partition).
3. `sgdisk --load-backup=FILE /dev/X` rewrites the primary and secondary tables; `sgdisk -v /dev/X`
   must then report no problems.
4. `partprobe /dev/X && udevadm settle`: the partitions reappear.
5. `zdb -l /dev/X1` shows the label intact, and `blkid /dev/X1` shows a `UUID_SUB` equal to the
   guid `zpool status -g` lists as UNAVAIL.
6. `zpool online <pool> <guid>`, then let the resilver finish (`zpool status`; hours on large
   disks).

Never `zpool replace` this member, and never copy a sibling disk's GPT onto it: partition names
and GUIDs are disk-unique. The `sgdisk -R` then `sgdisk -G` recipe in
`ch03-host-admin/zfs-administration.md` is for a NEW replacement disk only.

## Before calling it fixed

The pool is ONLINE again, but the link fault is still there until the cable or connector is
reseated or replaced, so the member can drop again at the next boot. Fix the cable, then read
`smartctl -A /dev/<disk> | grep -i crc` on EVERY member at least twice over time and require the
count to have stopped climbing, and require `zpool status` to show the pool ONLINE with no errors
after the resilver.
