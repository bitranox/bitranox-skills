# skill-writer checklist - meta-dream-crosstree (off semantics, backup refusals, promotion cost)

- [x] Change: Mode says a manual run under `off` consolidates private memory only (no CLAUDE.md
      edit, contributions queued, every 4b relocate proposed); step 1 names the refusals of a
      backup into another tree's dir and of an empty scope, with the next step; step 8 lists each
      promotion to a tree top with its cost; body text says tree top, not global.
- [x] Decisions: d-20261119-998a845e, d-20261119-205f6721, d-20261119-cc073a1a
      (the first supersedes d-20261110-8ee5b8fa)
- [x] Mechanism executed: the step 8 cost command `grep -F '(mem:<slug>)' <top>/CLAUDE.local.md | wc -c`
      printed the UTF-8 length plus newline of a scratch pointer line holding a two-byte character
      (37 = 37); store_manifest's refusals are pinned by tests in meta-dream-tree/tests.
- [x] Step 0b: `skill_decisions.py show meta-dream-crosstree` read before the first edit; the one
      rejected entry (relocate-to-top-under-off) rested on the Mode line this change replaces, and
      its reopen_if is met, so it is superseded with the reason.
- [x] RED: opus and haiku text probes on the pre-edit text reported the off contradiction (Mode
      against dream-core), answered NONE for the empty-scope next step, said a second backup into
      the first tree's dir silently replaces it, and named the per-promotion cost a gap.
- [x] GREEN: opus and haiku probes on the edited text quoted the new lines for every question; the
      one gap they raised about relocates below the top was closed in the Mode line wording.
- [x] Contract tests in hooks/tests/test_dream_skill_contracts.py fail on the pre-edit text and
      pass on the edited text.
- [x] Width and fence check over the added lines printed nothing; description unchanged.
- [x] Present tense, no history lines, no private hosts, paths or personal data.
