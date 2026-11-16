# skill-writer checklist - infra-proxmox (2026-11-16, a lock does not show external use)

Entries: queued contribution e8eb69253790161d entry 2. New troubleshooting row beside "VM won't start": `qm status` and the lock cannot tell whether a script or harness drives a VM.

Decisions: d-20261116-a685c29a

- [x] Step 0b `skill_decisions.py show infra-proxmox --kind rejected,removed --full` read before the first edit (no entries).
- [x] RED, text check against the pre-edit SKILL.md: no mention of a harness or external tool (grep count 0); the row said only "Check lock".
- [x] Claim checked: ch10-qemu/locks.md says online migrations, snapshots and backups set a lock; the "identical to idle" observation is the incident's (ledger tier inherited).
- [x] GREEN, text check: the new row is present once and fits the table's column widths (row length equals its neighbours'); no live subagent probe was run.
- [x] Added lines checked: ASCII only, no history wording, description unchanged.
- [x] Deployment: infra-proxmox has no twin; the plugin version is bumped.
