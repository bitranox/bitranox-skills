# skill-writer checklist - infra-windows-servicing (2026-11-09, queued contributions)

- [x] Entries covered: D31, D32, D33.
- [x] Mechanism: Not executed: no Windows guest was touched; the policy values, the 1014/1015 reading and the CheckHealth behaviour are the queued measurements, recorded as such in the queue entries, not re-run.
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `stored flag` 0->1; `Simulating a Windows Update outage` 0->1; `Setup events 1014` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
