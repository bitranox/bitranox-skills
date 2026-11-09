# skill-writer checklist - compuse-bash (2026-11-09, queued contributions)

- [x] Entries covered: D1, D2, D3, D4.
- [x] Mechanism: Commands executed: grep with invalid bytes under C.UTF-8 and de_DE.UTF-8 (GNU grep 3.12, matched lines holding a bad byte dropped, `binary file matches` on stderr, `grep -c` and `grep -a` count all, 180000 of 200000 on a 200000-line file); `seq 1 200000 | grep -q 5` under pipefail reads false, PIPESTATUS 141 0, capture form true; `! echo x | grep -q .` under `bash -e` continues; `set -m` background setsid pid gone at once while the job runs, `setsid -f` with a job-written pidfile answers kill -0; `printf '' | xargs -r grep -l PATTERN` exits 0.
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `binary file matches` 0->1; `early-exit reader` 0->1; `xargs -r grep -l` 0->2; `setsid nohup cmd` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
