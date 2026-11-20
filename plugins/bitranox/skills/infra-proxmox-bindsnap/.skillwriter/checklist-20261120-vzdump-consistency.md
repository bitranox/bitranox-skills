# checklist - what consistency vzdump snapshot mode gives a running CT

One queued contribution delivered (the vzdump paragraph); its sibling entry (one managed volume ->
plain zfs snapshot, no freeze) not delivered: d-20261119-aaa8765c records why the freeze stays
for a single volume. Same change in the twin (pve-bindsnap skills/proxmox-bindsnap).

Decisions: none - states stock behaviour the overlay passes through; d-20261119-aaa8765c unchanged

## RED

- [x] Skill decisions read first: d-20261119-aaa8765c contradicts the sibling entry.
- [x] Verified on proxmox06 (pve-container 6.1.24): VZDump/LXC.pm snapshot() calls
      snapshot_create($vmid, 'vzdump', ...); BindSnap.pm hands 'vzdump' to the original;
      AbstractConfig::snapshot_create freezes a running CT; a volume on storage without snapshot
      support makes LXC.pm raise "mode failure" and VZDump.pm fall back to suspend.
- [x] Text check at HEAD: "crash-consistent, the same as the freeze route" 0 hits.

## GREEN

- [x] Quote-back probe (haiku): consistency, the suspend fallback and the trade-off answered by
      quotes.

## REFACTOR

- [x] ASCII check clean.
