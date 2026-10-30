# Review: vzdump as the safety net on a refused build (contrib entry)

- [x] RED: `grep -ci vzdump SKILL.md` was 0; the untested-build path offered only
      `BINDSNAP-UNSUPPORTED` or a raw `zfs snapshot`.
- [x] Source: `lib/PVE/LXC/BindSnap.pm:661` (`has_feature` delegates a backup-only query to
      stock), `:685` (`snapshot_create` returns to stock for the `vzdump` snapshot name before any
      gate), `:808` (same for delete); `docs/design.md:78-80`; `docs/test-results.md:106-109`
      (`vzdump --mode snapshot` passed through and excluded the bind mounts).
- [x] Proxmox docs (infra-proxmox skill, `ch16-backup-restore/_index.md`): stop mode stops the
      container for the backup; device and bind mounts are never backed up; extra mount points
      are included only with the backup option.
- [x] Reasoned, not run (no Proxmox host touched): that a stop-mode restart re-runs the
      container's boot units follows from the container being started again.
- [x] GREEN: `grep -n -i vzdump SKILL.md` quotes the new table row and paragraph.
- [x] Twin copied; `diff -r -x .skillwriter -x __pycache__` reports the two copies identical (the
      tool copy already carried the marketplace `name:`).
- [x] ASCII only; generic placeholders only; description untouched.
- [x] Declined, not run: subagent quote-back probes (this pass dispatched no subagents).
