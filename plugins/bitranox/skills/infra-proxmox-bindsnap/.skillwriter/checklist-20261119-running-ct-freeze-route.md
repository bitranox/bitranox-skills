# skill-writer checklist - infra-proxmox-bindsnap (2026-11-19, running-CT freeze route)

Entry: user decision 2026-11-19 "Add freeze route (Recommended)". A RUNNING CT whose managed volumes
are all on ZFS gets a raw snapshot taken inside `lxc-freeze` / `lxc-unfreeze` (trap), in one script
on the node, instead of being sent to `vzdump`. Also: the untested-build gate covers creating a
snapshot only.

Decisions: d-20261119-4b2e2736, d-20261119-d6420b25, d-20261119-aaa8765c

- [x] Step 0b: `skill_decisions.py show infra-proxmox-bindsnap --kind rejected,removed --full`
      read before the first edit (none). The live rule d-20261117-049f37d4 (stopped CT only,
      running CT to vzdump) is amended on the user decision; d-20261119-4b2e2736 supersedes it and
      says what changed in its `why`.
- [x] Premises checked: stock pve-container 6.1.24 `Config.pm` `__snapshot_freeze` freezes the CT
      (cgroup freezer, 30 s timeout), syncs its mount namespace, snapshots each volume, thaws;
      `PVE::Storage::Plugin::volume_snapshot_needs_fsfreeze` returns 0 and the ZFS plugin does not
      override it. Overlay `lib/PVE/LXC/BindSnap.pm`: the `snapshot_delete` and
      `snapshot_rollback` wrappers carry no checksum or running check (only `snapshot_create`
      gates); the rollback wrapper's comment reads "upstream stops the CT itself".
- [x] The procedure was run on a nested test node (pve-container 6.1.24, rootfs plus a volume
      `mp1`, a writer in the CT), 11 of 11 checks PASS: FROZEN during the snapshot, RUNNING after,
      config copied, both volumes in ONE `zfs snapshot`, equal counters on both volumes for a
      write-then-rename writer, writer continued after the thaw, not in `pct listsnapshot`, a
      duplicate name failed ("no snapshots were created") and the trap still thawed the CT, stop
      plus `zfs rollback` per volume plus start restored the snapshot state. A first run with a
      truncate-then-write writer caught the rootfs file EMPTY: the crash-consistent caveat.
- [x] The script as shipped in SKILL.md (config copy path changed to `/root/<vmid>.conf.<name>` to
      match the rollback text, diagnostic echo dropped) executed against a fake node (stub `pct`,
      `pvesm`, `zfs`, `lxc-freeze`, `lxc-unfreeze`; `/etc/pve` and `/root` bound to scratch):
      - all-ZFS CT with a bind `mp0` and a `dev0`: rc 0, the bind and device skipped, call order
        `lxc-freeze`, one `zfs snapshot` of both datasets, `lxc-unfreeze`; config copy written.
      - `zfs snapshot` failing (duplicate name): rc 1, `lxc-unfreeze` still called.
      - rootfs on `local-lvm`: rc 2 "not on ZFS: local-lvm:...", before any freeze.
      - fed through `bash -s <vmid> <name>` on stdin: rc 0, same calls.
- [x] RED, contamination check: `redcheck --corpus-cascade` returned STRONG on a memory fact that
      prescribes a raw snapshot WITHOUT a freeze and on unrelated refquota and E2E facts; none
      states the freeze route. Route taken: text check of the pre-edit file plus a behavioural arm.
- [x] RED text check (pre-edit `git show HEAD:`): 0 hits for `lxc-freeze` / `lxc-unfreeze`; step 1
      sent a running CT to `vzdump`.
- [x] RED behavioural (opus, pre-edit full text, running all-ZFS CT that must not stop): "The skill
      gives no route that meets all three of the owner's conditions at once"; chose `vzdump`, offered
      an unfrozen raw snapshot only as an afterthought. Gaps listed: no route fits, atomicity
      unstated, quiescing never mentioned, `backup=1` handling, no store, no restore commands.
- [x] GREEN (opus and haiku, edited full text, 2 tiers x 2 scenarios): both ran the script route
      for the all-ZFS running CT, quoted the table row and the step-1 line, stated crash-consistent
      with the empty-file example, sent the lvmthin-rootfs CT to `vzdump`, and answered that
      `pct delsnapshot` works on the untested build by quoting the new gate sentence. Nothing the RED
      produced is missing from GREEN (the `backup=1` check stayed).
- [x] REFACTOR, closed from GREEN gaps: rollback needs the CT stopped (bold-lead sentence of the
      raw route); `pct delsnapshot` works with the CT running (scoped in the gate sentence);
      one dataset-mapping method (step 3 now uses `pvesm path` like the script); from inside the
      CT, copy the script to the node and start it with one ssh call (no stdin streaming); a
      duplicate name exits non-zero and overwrites the saved config copy of that name.
- [x] Quote-back (opus medium and haiku, 7 questions on the final text before the last two
      fixes): every answer a verbatim quote. Final re-probe (haiku) on the questions the last
      fixes touched (rollback stop, from inside the CT, duplicate name): each answered with a
      verbatim quote; its remaining gaps (zfs error text, an unreachable node mid-call, a trap that
      fails to run) are declined below.
- [x] Declined: a FUSE or CIFS HOST source behind a bind mount stalling the freeze (mechanism not
      measured; the stall sentence matches section 4's existing wording); `backup=1` how-to, the
      backup store and restore commands (pre-existing vzdump paragraph, tracked in the tool repo's
      backlog; restore belongs to bitranox:infra-proxmox); an instant route for lvmthin and a
      hybrid of vzdump plus raw ZFS (declined on 2026-11-17, judgement left to the operator); which
      of raw ZFS and vzdump to prefer (the section 3 rows separate them by state and storage);
      snapshot naming (the existing "a name no later `pct snapshot` will use" rule); zfs's own error
      text and the exact exit code (the sentence says non-zero; the text quoted by the run is
      enough); a node lost mid-call or a trap that fails (no measurement; the EXIT trap is the
      only thaw path and the text says so).
- [x] Width and fence check over the added lines printed nothing; ASCII only; history-phrase finder
      over the added lines found nothing; no private host names.
- [x] Description untouched (no YAML change).
- [x] Tool repo twin `skills/proxmox-bindsnap/SKILL.md` written with the same body; mirror verdict
      from `repo-gate.py --mirrors`.
