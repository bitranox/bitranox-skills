# skill-writer checklist - coding-python-performance-review (2026-11-09, queued contributions)

Entries: C18, C19, C20, C22. Step 3 profiles with the repo invocation and treats a suite as a proxy, import-time findings need the SELF column, compare_performance takes pytest args, the cache finder sees I/O through helpers.

Decisions: none - additive rules, no recorded decision is reversed (skill_decisions.py show coding-python-performance-review run first)

- [x] Step 0b `skill_decisions.py show coding-python-performance-review --kind rejected,removed --full` read before the first edit; rule entries read, none reversed.
- [x] RED, text check against the pre-edit file (`git show HEAD:<path>`): none of the new rule phrases are present (A suite profile is a proxy, Import-time findings, after --, named path overrides).
- [x] Every command or snippet the edit adds was executed: the Step 3 detector printed an empty path for testpaths and for --doctest-modules, tests for neither; compare_performance with -- -m and the finder on a real dotenv loader (0 candidates) both ran; each new test killed under mutation_arm.
- [x] GREEN, quote-back on the final text: one haiku probe arm (26 questions over the whole batch, text pasted, no skill loaded) returned the governing sentence for each rule of this skill; a control question the text does not cover returned NONE. No opus arm ran. Gaps it reported: only that some sentences are stated in an example rather than prose; declined, the heading or row states the rule.
- [x] Added lines checked: ASCII only, no history wording, prose lines within 100 columns, description unchanged.
- [x] Deployment: the change is committed on a worktree branch; the marketplace maintainer integrates, bumps and pushes.
