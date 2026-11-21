# checklist - vzdump safety net: check backup=1 on each mpN, and the route back

Section 5: the vzdump bullet and the safety-net paragraph tell the reader to check every managed
`mpN` for `backup=1` before relying on the archive, how to set it, and which task-log lines show
a volume kept or left out; the paragraph gains the restore-over-the-CT commands; the quick
reference row for the vzdump route names `backup=1`. Same change in the twin (pve-bindsnap
`skills/proxmox-bindsnap`).

Decisions: d-20261121-5baab3e3, d-20261121-2da69428

## RED

- [x] Skill decisions read first (`skill_decisions.py show`, rejected/removed in full): none
      touches vzdump or restore; d-20261119-aaa8765c (raw snapshot without freeze) unchanged.
- [x] Contamination check: `redcheck --corpus-cascade` named term overlaps only; the named
      documents were read and none states the backup=1 rule. Behavioural arm kept.
- [x] Stock behaviour verified in pve-container 6.1.24 source: `PVE/LXC/Config.pm`
      `mountpoint_backup_enabled` (a volume mount point without `backup` gets reason `disabled`);
      `PVE/VZDump/LXC.pm` logs `excluding $type mount point $name ('$mount') from backup ($reason)`
      and `including mount point $name ('$mount') in backup`; `__mountpoint_config_fast_plug_safe`
      lists `backup` and `replicate` as changed live on a running CT; `PVE/API2/LXC.pm` restore:
      `force` overwrites an existing CT, a running one dies `can't overwrite running container`,
      `start` defaults to 0.
- [x] RED (opus and haiku, pre-edit section 5 excerpt from `git show HEAD:`, running Postgres CT
      with data on a Ceph `mp1` lacking `backup=1`): both found the trap only from their own
      Proxmox knowledge; opus: "The backup=1 trap isn't spelled out ... never tells you to check
      `pct config` for it, and never gives the `pct set ... backup=1` command"; haiku: "the
      default for backup= on a mount point that has none" unknown. Both guessed the log check;
      both reported no restore syntax.

## GREEN

- [x] GREEN (opus and haiku, edited text, same scenario, 2 tiers x 1 scenario): both set
      `backup=1` with the exact `pct set 120 -mp1 <current value>,backup=1`, gated the migration
      on the `including mount point mp1 ('/var/lib/postgresql') in backup` line, named the bind
      mount's expected exclusion. Quote-back 4 of 4 verbatim on each tier (default off, the set
      command, live on a running CT, the exclusion line).
- [x] Nothing the RED produced is missing from GREEN: crash-consistency, no `--mode stop`, bind
      data not covered, all kept.

## REFACTOR

- [x] Closed from RED and GREEN gaps (both arms): restore syntax. Added `pct stop`, then
      `pct restore <vmid> <archive> --force 1` with the volume ID from `pvesm list`, and the
      running-CT refusal. Quote-back (opus and haiku) 3 of 3 verbatim. Its gap "is the CT started
      after the restore" closed with "The restore leaves the CT stopped; `pct start <vmid>` brings
      it back."
- [x] Closed: the quick-reference row for the vzdump route now names `backup=1`, so a reader who
      scans only the table meets it.
- [x] Final re-probe (opus and haiku, new scenario: NFS `mp1`, table rows plus the restore
      sentences): both chose the vzdump row, set `backup=1`, restored with stop/restore/start;
      Q1 and Q2 quoted verbatim on both tiers.
- [x] Declined, covered elsewhere in the skill: the `pct set` command and the default-off fact
      (the final probe's excerpt left out the section-5 paragraph that states both: "That flag is
      OFF unless set" and "`pct set <vmid> -mpN <the current mpN value>,backup=1`"); the suspend
      fallback ("If a backed-up volume's storage cannot snapshot, vzdump falls back to
      `--mode suspend`").
- [x] Declined, environment-specific: the backup storage name, vzdump duration, whether a given
      Ceph or NFS storage snapshots.
- [x] Declined, owned by bitranox:infra-proxmox: where `pct restore` places volumes without
      `--storage`, listing an archive's contents, application-level dumps (`pg_dump`).
- [x] Declined, judgement left to the operator: whether to keep `backup=1` after the change
      (it also adds the volume to scheduled backups); saving the failed state before a restore.
- [x] Declined, consistent as written: "passes every vzdump call straight to stock code" next to
      "the overlay hands [the `vzdump` snapshot] to stock code" (both say stock code runs it).
- [x] Width and fence check over the added lines printed nothing; tables reformatted; ASCII only;
      history-phrase finder over the added lines found nothing; no private host names.
- [x] Description untouched (no YAML change).
- [x] Tool repo twin `skills/proxmox-bindsnap/SKILL.md` written with the same body;
      `repo-gate.py --mirrors`: 0 of 12 mirrored pairs have drifted.
