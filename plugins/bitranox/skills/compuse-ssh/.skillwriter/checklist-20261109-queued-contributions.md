# skill-writer checklist - compuse-ssh (2026-11-09, queued contributions)

- [x] Entries covered: D8.
- [x] Mechanism: Commands executed: a `while read` loop over three lines with an inner stdin reader ran one item, with `</dev/null` three (real ssh not used; the same stdin inheritance applies).
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `while read ... done < list` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
