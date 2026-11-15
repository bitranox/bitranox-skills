# skill-writer checklist - infra-proxmox (2026-11-15, queued lessons)

Six additions. SKILL.md troubleshooting table: the "Docker in an UNPRIVILEGED CT" row states the
divert ORDER; new rows "CT resolv.conf/hosts reset on start" (`/etc/.pve-ignore.<name>` and the
inert `pct set --nameserver` once it exists) and "Cloned CT shows `size=0T`" (no limit on a ZFS
subvol). `references/restored-guest-identity.md`: leave a dbus machine-id symlink alone and never
write through it from the host; rewrite `/etc/mailname` and postfix `myhostname`.
`references/zfs-guest-disks.md`: a full clone of a running VM with `tpmstate0` is refused, step 2
names the dataset rather than the storage id, step 3 leaves `smbios1` and `vmgenid` out and checks
free memory before starting the clone. The table widened, so the formatter re-padded every row of
it; only the three rows above changed content.

Decisions: d-20261115-6211df01, d-20261115-78fe16c2, d-20261115-a4b45427, d-20261115-7c9c11a4, d-20261115-86eb8025

- [x] Receipt fresh. Step 0b: the skill had no ledger entries; nothing to reverse.
- [x] RED by text check of the pre-edit files: `pve-ignore`, `size=0`, `BEFORE installing`,
      `mailname`, `symlink` and `vmgenid` occur 0 times; `TPM state` occurred only in an
      unrelated place.
- [x] Mechanism claims checked against the installed sources on a PVE node, read-only
      (pve-container 6.1.20, qemu-server 9.2.15): `ct_is_file_ignored` returns
      `-f "$path/.pve-ignore.$name"` and `set_dns` writes `/etc/resolv.conf` through
      `ct_modify_file`, which returns early when ignored; `copy_volume` sizes the new volume from
      `volume_size_info`, which reports a subvol with `refquota=none` as 0, and a size-0 subvol
      is created with `refquota=none`; `cannot clone TPM state while VM is running` dies for a
      full clone of a running VM without a snapshot name; `qm create` generates `smbios1` and
      `vmgenid` when they are absent.
- [x] GREEN quote-back, opus and haiku, 5 questions on this skill: both tiers quoted the new text
      and answered correctly, including `<pool>` = the pool line's dataset for a given storage.
- [x] Gaps from GREEN, closed: the ignore-file names for hosts and hostname were only implied
      (opus) - now listed. Re-probe on haiku: quoted and answered correctly.
- [x] Gaps declined: whether `pct resize` grows from size 0 like any other (opus) - not measured
      here, the row only says how to set a limit; the snapshot-route reason elided in the excerpt
      - present in the full reference.
- [x] Width and fence check over the added lines of all three files: no output. ASCII only; no
      private host, container or storage names.
