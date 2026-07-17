# skill-writer checklist - infra-proxmox (2026-07-18, three PVE VM operational gotchas)

Change: added three rows to the Troubleshooting Quick Reference - (1) cpu:host exposes vmx so
Win11 auto-enables VBS (~25% penalty); a no-vmx model keeps it off but forces Docker process
isolation; (2) qm clone only brings configured/managed disks, so a base with app data on a
separate disk (Docker data-root on D:) loses it on clone; (3) snapshot/backup a guest ONLY via
native qm/pct + vzdump/PBS, never a manual zfs snapshot of guest zvols or a hand-edited [snapshot].

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: without these, an agent tuning a slow Windows VM misses the VBS/vmx cause, an agent
      cloning a Docker base ships a VM whose dockerd fails "Incorrect function", and an agent
      snapshotting a guest hand-rolls a zfs snapshot that desyncs from the guest config (facts
      reference-pve-win-vm-cpu-host-vbs..., reference-cloned-qemu-docker-win-vm-dockerd-data-root...,
      feedback-pve-native-snapshots-backups-not-manual-zfs).
- [x] GREEN: each row states the symptom, the cause, and the fix; generic PVE knowledge (the
      benchmark numbers are the only host-flavored detail and are stated as approximate).
- [x] Scope: general Proxmox VE operation; correct home. Rows carry no host names / VMIDs / IPs.
- [x] Security scan: prose only; no secrets, no real hostnames/IPs (generic drive letter D: only).
- [x] CSO description: unchanged (body edit; "VMs", "storage", "backups", "troubleshooting" cover retrieval).
- [x] Token budget: hub skill; three concise rows in the existing quick-reference table, body stays an index.
