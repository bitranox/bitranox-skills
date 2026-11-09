# skill-writer checklist - compuse-git (2026-11-09, queued contributions)

- [x] Entries covered: D5, D6.
- [x] Mechanism: Commands executed: `git cherry-pick -q HEAD` exits 129 with the usage; `git fetch ../s master:refs/heads/imported` brings the source's tag and `--no-tags` does not; a fetch storing no ref brought none (the row is scoped to a fetch that stores a ref).
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `--no-tags` 0->1; `git cherry-pick -q` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
