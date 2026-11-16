# skill-writer checklist - infra-proxmox-bindsnap (2026-11-16, checksum not version)

Entries: queued contribution d813dd7b434eaea7. A build newer than the list is not untested on that ground alone; judge from the journal line.

Decisions: d-20261116-0270e232

- [x] Step 0b `skill_decisions.py show <skill> --kind rejected,removed --full` read before the first edit (no entries).
- [x] RED, quote-back probe (opus, text only) on the pre-edit text: could not tell whether matching is by checksum or by version.
- [x] GREEN, quote-back probes (opus, then haiku after closing the gaps opus named) answered from the new text.
- [x] Added lines checked: ASCII only, no history wording, description unchanged.
- [x] Deployment: the marketplace copy and the tool repo twin carry the same text (repo-gate --mirrors: in sync) and both versions are bumped.
- [x] Claim checked in lib/PVE/LXC/BindSnap.pm: the known-good key is the combined sha256 of @GUARDED_FILES, per guard.
