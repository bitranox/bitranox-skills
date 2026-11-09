# skill-writer checklist - infra-proxmox (2026-11-09, queued contributions)

- [x] Entries covered: D27, D28, D29.
- [x] Mechanism: Mechanism taken from the queued observation (a live PVE node, not re-run here); `/sys/kernel/security/apparmor/.ns_stacked` path and `CapBnd` read on a container here; CAP_MAC_ADMIN is capability 33.
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `failed to connect to monitor socket` 0->1; `ns_stacked` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
