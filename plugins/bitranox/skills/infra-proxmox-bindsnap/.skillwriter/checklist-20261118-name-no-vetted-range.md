# skill-writer checklist - infra-proxmox-bindsnap (2026-11-18, name no vetted range)

Entries: user decision 2026-11-18 "Skill stops naming a range". The skill points at
docs/compatible-versions.md for the vetted builds and names no range or release; a node accepts
only the rows its installed release holds.

Decisions: d-20261118-f2cb4ad9

- [x] Step 0b `skill_decisions.py show infra-proxmox-bindsnap` read before the edit (two live rules, no rejected or removed entries).
- [x] Edit applied byte-identically to the tool repo twin (pve-bindsnap skills/proxmox-bindsnap/SKILL.md); pre-edit texts compared identical with diff.
- [x] Live anchors kept: "Judge a node from its journal line, never by comparing its" still occurs (skill_decisions.py check).
- [x] Added lines checked: ASCII only, no history wording, description unchanged.
- [x] Claims checked in the skill itself: section 1 names `apt-get upgrade` for the package and `install.sh` for the script install.
- [x] GREEN quote-back probe (opus, text only) on the new passage: named no range, sent the list question to compatible-versions.md, refused a quoted range, and read a listed row plus TEST mode as an installed release that lacks the row (update with apt-get upgrade, then re-read the journal line). No RED: the change removes a range by user decision, it does not close a reader gap.
