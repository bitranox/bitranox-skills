# skill-writer checklist - compuse-toolbox (2026-11-09, queued contributions)

- [x] Entries covered: D10, D11, D12, D13, D37 (D9 and D38 in the scripts).
- [x] Mechanism: Commands executed: `gate.py --gate "true" --gate-cwd /tmp --gate-env A=B` passed, and `mdwrap` span wrap at width 50; description measured at 1024 characters (cap 1024). `test_gate.py`, `test_mdwrap.py` pass; the new `test_the_help_shows_the_per_gate_flags_after_their_gate` and `test_an_inline_code_span_is_never_split_across_lines` are KILLED by `mutation_arm --revert` on the prior gate.py and mdwrap.py.
- [x] RED text check (fragment counts, pre-edit HEAD vs edited file): `read assistant records only` 0->1; `bare dotless internal hostname` 0->1; `gate-env MSG=@msgfile` 1->2; `resolving a conflict hunk` 0->1; `missing proves the helper` 0->1.
- [x] GREEN text check: every fragment is present in the edited file at the place a reader of that situation meets it.
- [x] Behavioural probes: none dispatched in this batch, so RED and GREEN are TEXT checks of the skill file, not a behavioural pass; no "X does not happen" verdict is claimed.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each insertion was read.
- [x] ASCII only, present tense (history-phrase finder over the added lines: no hit), no private host or repo name.
- [x] Skill decisions read first (`skill_decisions.py show`); no rejected or removed decision reversed.
- [x] Decisions: none - additive guidance from queued contributions, no recorded decision is reversed.
