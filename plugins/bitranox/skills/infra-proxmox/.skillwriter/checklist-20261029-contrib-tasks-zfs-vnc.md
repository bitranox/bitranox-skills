# skill-writer checklist - infra-proxmox (four reference files, eight rows)

- [x] Change: references/pve-tasks.md (CLI blocking, detaching and polling a UPID, config lock
      after stop, filing your own task), references/running-vm-config-and-exit.md (qm set on a
      running VM hot-plugs, IDE/SATA CD-ROM cold start, qmeventd -v and the tap unregistering
      line), references/external-vnc-viewer.md, references/zfs-guest-disks.md (storage ID vs
      dataset, rollback only to the newest snapshot, full clone from a snapshot, un-template,
      growing a ZFS-root guest disk); troubleshooting rows for each plus apt-repository toggle
      and PBS namespace 0 KiB; the snapshot row gains the carve-out (editing keys in a qm-made
      section is fine, hand-making one is not); four routing rows in "Which File Do I Need?".
- [x] Not reproducible here (no PVE node may be touched): every claim is the measured result
      carried by the entry, with the release named in each file, and private hosts, VMIDs and
      storage names replaced (the dataset example uses the default `local-zfs` -> `rpool/data`).
- [x] Consistency with the existing "NEVER a manual zfs snapshot" rule: the ZFS-root grow recipe
      takes a `qm snapshot`, not a hand-made zfs snapshot.
- [x] Vendored chapter files (ch03 package-repositories.md and others) left untouched; new
      material lives in references/ and the SKILL.md tables.
- [x] RED text check (whole skill dir, origin/master): fork_worker, RPCEnvironment, qmeventd,
      unregistering, LC_PVE_TICKET, vmconfig_hotplug_pending, "most recent snapshot", __base__,
      "zpool online -e", apt/repositories, media=cdrom, "setsid -f" all 0 hits.
- [x] GREEN quote-back: "`qm set <vmid> -<key> <value>` against a running VM runs
      `vmconfig_hotplug_pending`"; "`qm rollback <vmid> <snap>` to an earlier snapshot ... refuses";
      "Editing KEYS inside a section `qm snapshot` made is fine"; "`pvesh set` on that path is the
      ADD-a-standard-repository call".
- [x] Routing table: each new reference file has a row naming its topics; every file named in a
      row exists (`ls references/`).
- [x] Description: unchanged (300 chars).
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the first SKILL.md edit.
- [x] Behavioural probes: none dispatched (this batch ran under a no-subagent rule), so RED and
      GREEN are TEXT checks of the skill file: each rule's key fragment counted in
      `git show origin/master:<file>` (0) and in the edited file (>=1). Recorded as a text check,
      not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] ASCII only (no byte above 0x7F in the diff), present tense (history-phrase finder: 0 hits in
      added lines), no private host, VMID, cluster or repo name in the added text.
