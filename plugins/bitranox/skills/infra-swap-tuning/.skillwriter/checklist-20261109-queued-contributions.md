# skill-writer checklist - infra-swap-tuning (2026-11-09, queued contributions)

- [x] Entries covered: D30.
- [x] Mechanism: The `grep VmSwap /proc/[0-9]*/status | sort -k2 -n | tail` line was run and sorts by kB; `zfs set volsize` and mkswap on a live zvol were not run (taken from the queued observation).
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `Resizing an active disk swap zvol` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
