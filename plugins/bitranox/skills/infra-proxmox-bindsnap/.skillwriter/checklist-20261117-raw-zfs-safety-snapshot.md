# skill-writer checklist - infra-proxmox-bindsnap (2026-11-17, raw ZFS safety snapshot)

Entry: queued contribution 30d053075443448d (target skill:infra-proxmox-bindsnap). On a build the
guard refuses, offer a raw ZFS snapshot of a STOPPED CT before `BINDSNAP-UNSUPPORTED`, and name the
refusal text in the description.

Decisions: d-20261117-049f37d4

- [x] Step 0b: `skill_decisions.py show infra-proxmox-bindsnap --kind rejected,removed --full`
      read before the first edit (no entries; one live rule, untouched by this edit).
- [x] Premises checked in `lib/PVE/LXC/BindSnap.pm` (overlay 1.4.1): `snapshot_create` dies with
      `"$TAG: snapshot gated -- pve-container $vlabel is untested; add BINDSNAP-UNSUPPORTED or
      update pve-container (details in the task log)"`, `$TAG` is `pve-bindsnap`; the known-BAD die
      comes first and the running-CT die after; all three die before the upstream create runs, so
      nothing is left behind (also `docs/test-results.md`, "no zfs snapshot leaked"). The known-good
      table ends at `6.1.15, 6.1.16`. `BINDSNAP-UNSUPPORTED` only lifts the untested gate and lets the
      overlay's bind filter run on the unvetted build. Exit 255 is from the queue entry's
      measurement, not re-run here.
- [x] ZFS/Proxmox claims are documented or source-read, not run on a node: `zfs rollback` refuses
      past a newer snapshot and `-r` destroys them; a second snapshot of one name is refused;
      Proxmox's ZFS plugin (`volume_rollback_is_possible`) refuses a rollback that is not to the
      most recent snapshot. The skill text says which parts are seen and which documented.
- [x] RED, contamination check: `redcheck --corpus-cascade` returned `inherited` (strong) on term
      overlap with unrelated refquota and NAV-test-db facts; none states the gated-build fallback.
      Route taken: text check of the pre-edit file plus a behavioural arm on the pre-edit text.
- [x] RED text check (pre-edit `git show HEAD:` copy): 0 hits each for `pct config`, `pvesm`,
      `listsnapshot`, `zfs rollback`, `snapshot gated`.
- [x] RED behavioural (opus, pre-edit excerpt): reached the raw ZFS route by inference and listed as
      gaps: the ZFS line sits in "Not for", names only `disk-0` (mp0 added on its own), no rollback
      or cleanup commands, no config copy, `<pool>` unexplained, the table's untested-build answer
      is the slow `vzdump`.
- [x] Commands exercised where possible: both `grep` patterns run against a fake `zfs list` output
      (`subvol-12-disk-` does not match `subvol-123-disk-0`; `/subvol-123-disk-` does not match
      `subvol-1234-`). No `zfs`/`pct` call was run on a node (none available here).
- [x] GREEN (opus and haiku, new excerpt, 2 tiers x 2 scenarios): both snapshotted rootfs and mp0
      in one command, saved the config, sent an lvmthin rootfs to `vzdump`, and quoted the
      `pct rollback` interaction. Scenario B had no bind mount, so its "would not be gated" remark
      is a scenario defect, not a skill gap.
- [x] REFACTOR from GREEN gaps, closed: "Not for" now requires ALL managed volumes on ZFS (opus read
      it as allowing a partial snapshot); the refusal leaves nothing behind; `pct start` and a
      concrete `diff` command in the rollback; `zfs list -t filesystem` so a pool with
      `listsnapshots=on` lists no snapshots as datasets.
- [x] Re-probe (haiku, quote-back, final text except the `diff` command): Q1-Q4 each answered with a
      verbatim quote; its one remaining gap (which files to diff) is closed by the `diff` command.
- [x] Declined: a `pct restore` command and the `backup=1` default for the vzdump route (pre-existing
      vzdump paragraph; restore of a bind-mount CT belongs to bitranox:infra-proxmox); a hybrid
      route (vzdump rootfs plus raw ZFS of mp0): a mixed copy taken by two tools at two moments is a
      judgement left to the operator; a snapshot naming convention (the rule "a name no later
      `pct snapshot` will use" is enough).
- [x] Width and fence check over the added lines printed nothing; ASCII only; finder hit
      `from 6.0.18 to 6.1.16` is a range, not history; "As of 1.4.0" rewritten for the 1.4.1 list.
- [x] Description measured with `len()`, under 1024; YAML front matter parses (`['description',
      'name']`).
- [x] Tool repo twin `skills/proxmox-bindsnap/` written with the same text; mirror verdict from
      `repo-gate.py --mirror-of`.
