# Guest disks on a `zfspool` storage: datasets, snapshots, clones and templates

PVE's `zfspool` storage keeps each guest disk as a zvol (VM) or a dataset (`subvol-...`, CT). These
are the operations where its rules differ from what the GUI suggests. Measured on PVE 9 with ZFS
storage; re-check on another release before building on a detail.

## A storage ID is not the dataset prefix

A volume id names the STORAGE, not the pool. On a default install the storage `local-zfs` points
at the dataset `rpool/data`, so `local-zfs:subvol-101-disk-0` lives in
`rpool/data/subvol-101-disk-0`, mounted at `/rpool/data/subvol-101-disk-0`. Building the dataset
name by gluing the storage ID onto the volume name gives a dataset that does not exist, and a script
that then reads `$ROOT/etc/...` with an empty `$ROOT` reads the HOST's files and reports them as
the guest's (guard it: `bitranox:compuse-bash`, "An absolute path built from a variable").

Resolve it instead:

```bash
pvesm path local-zfs:subvol-101-disk-0          # the path PVE itself uses
awk '/^zfspool: local-zfs$/,/^$/' /etc/pve/storage.cfg   # its "pool" line
zfs list -H -o name,mountpoint | grep -- '-101-disk-'    # every volume of guest 101
```

## Rollback only to the LATEST snapshot

`qm rollback <vmid> <snap>` to an earlier snapshot of a ZFS-backed VM refuses with
`... is not most recent snapshot`: ZFS rolls back only to the newest snapshot, and PVE will not
destroy the later ones for you. Delete every later snapshot first, newest first
(`qm delsnapshot <vmid> <name>`), then roll back. Those snapshots are GONE afterwards; if you may
still need one, clone it out first (next section).

## Full clone from a snapshot

`qm clone <vmid> <newid> --snapname <snap> --full` cannot copy from a `zfspool` snapshot: the
plugin offers no `copy` from a snapshot (`volume_has_feature` lists `copy` without `snap`), so the
clone refuses with `Full clone feature is not supported for a snapshot of '<volid>' (<disk>)`
before copying anything. A full clone WITHOUT `--snapname` copies the current state, never a
snapshot. Do it by hand:

1. `qm config <vmid> --snapshot <snap>` lists the disks that snapshot references, including
   `efidisk0` and `tpmstate0`.
2. For each one: `zfs send <pool>/vm-<vmid>-disk-<N>@<snap> | zfs recv <pool>/vm-<newid>-disk-<N>`.
3. `qm create <newid>` and `qm set` the snapshot's settings with the new volume ids, and a NEW MAC
   on every NIC (leave `macaddr=` out and PVE generates one), so the clone does not collide with
   the source on the network. `qm rescan --vmid <newid>` picks up anything you did not attach.
4. Remove it later with `qm destroy <newid> --purge`, then confirm with `zfs list` that no
   `vm-<newid>-` volume is left.

## Turning a template back into a normal VM

There is no un-template command, because `qm template` changed the storage, not just the config:
it renamed each `vm-<id>-disk-<N>` to `base-<id>-disk-<N>` and added a `@__base__` snapshot to
each. Undo it by hand, and ONLY when no linked clone uses the template
(`grep -rl 'base-<id>-disk' /etc/pve/nodes/*/qemu-server/` must list only the template itself):

1. Copy `/etc/pve/qemu-server/<id>.conf` to a backup OUTSIDE `/etc/pve`.
2. `zfs rename <pool>/base-<id>-disk-<N> <pool>/vm-<id>-disk-<N>` for every disk (EFI and TPM
   state included).
3. In the conf, rewrite each `base-<id>-disk-<N>` volume id to `vm-<id>-disk-<N>` and drop the
   `template: 1` line. Write the file WHOLE (read, change, write back): `sed -i` fails on pmxcfs,
   because it renames a temporary file over the original.
4. The `@__base__` snapshots moved with the rename. They are a rollback point to the templated
   state; destroy them before running `qm template` again, which creates snapshots of that name.

What changes: a normal VM gives FULL clones only (a linked clone needs a template). And its first
boot writes a machine id that was blanked before templating (an empty `/etc/machine-id` is filled
at boot), so every clone made from it copies that id: blank it again before you clone or template.

## Changing a VM's VMID

PVE has no command that renumbers a guest, and `qm clone` to the new id keeps the disks but drops
every snapshot. To keep the snapshots, rename by hand. Not for a template (a template's `base-`
volumes are what its linked clones point at). Do steps 1 and 2 first, then stop the VM:

1. Check the new id is free in the whole CLUSTER, not just on this node:
   `pvesh get /cluster/nextid --vmid <new>` returns the id when it is free and fails with
   `VM <new> already exists` when it is not.
2. Find every other place the old id is used: `grep -rnw <old> /etc/pve`, reading each hit (a
   bare number also matches sizes and ports), plus `ls /etc/pve/firewall/<old>.fw`, which
   usually names the id only in its file name. A hit in `jobs.cfg` (backup jobs), `replication.cfg`,
   `ha/resources.cfg` or `user.cfg` (pool membership) still names the old id after the rename.
   Remove the guest from HA (`ha-manager remove vm:<old>`) and replication now, and re-add it
   under the new id after step 6. Rename `firewall/<old>.fw` to `<new>.fw` and change the id in
   the job and pool entries in the same pass as step 5, writing each of those files whole too;
   inside the conf, a hit outside a volume id (the Notes, an `args:` line) is yours to decide.
3. Copy `/etc/pve/nodes/<node>/qemu-server/<old>.conf` to a backup OUTSIDE `/etc/pve`.
4. `zfs list -H -o name | grep -- '/vm-<old>-'` lists every volume: `disk-N` (EFI and TPM state
   included), `cloudinit`, and the `state-<snap>` volume of a snapshot taken with RAM. Rename each
   to `vm-<new>-...` with `zfs rename`; its `@snapshots` move with it.
5. `mv /etc/pve/nodes/<node>/qemu-server/<old>.conf <new>.conf` in the same directory, then rewrite
   every `vm-<old>-` volume id to `vm-<new>-` in the live section AND in every `[snapshot]`
   section (`vmstate:` lines too). Write the file WHOLE (read, change, write back): `sed -i` fails
   on pmxcfs.
6. Verify before relying on it: `qm listsnapshot <new>` lists the snapshots,
   `grep -c 'vm-<old>-' <new>.conf` prints 0, `qm rescan --vmid <new> --dryrun` adds no `unused`
   disk (a renamed volume the conf does not name), and the VM boots.

## Growing the disk of a guest whose root is on ZFS

`qm resize <vmid> <disk> <size>` grows only the virtual disk. A guest that keeps its root pool on
the last partition (a PVE installed in a VM, for example: `rpool` on partition 3) sees none of it
until the partition and the pool grow too. Take a `qm snapshot` first. Then in the guest, with the
disk as `/dev/sdX`:

```bash
sgdisk -i 3 /dev/sdX            # note "First sector" and "Partition unique GUID"
sgdisk -e /dev/sdX              # move the backup GPT to the new end of the disk
sgdisk -d 3 -n 3:<first-sector>:0 -t 3:BF01 -u 3:<guid> /dev/sdX
partx -u /dev/sdX               # partprobe warns on a disk in use; partx updates the kernel
zpool status -P rpool           # the device path the pool uses for that partition
zpool online -e rpool <that path>
zpool list rpool                # SIZE now shows the new capacity
```

Recreating the partition with the SAME start sector, type and unique GUID keeps the
`/dev/disk/by-id/...-part3` path the pool imports by, and the data in place. No reboot is needed;
to prove the next boot imports the grown pool, reboot once and check that
`/proc/sys/kernel/random/boot_id` changed and `zpool list` still shows the new size.
