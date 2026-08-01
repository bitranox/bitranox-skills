# skill-writer checklist - compuse-toolbox (2026-08-02, git_state ships once)

Change: `git_state.py` and its tests ship once, in `compuse-toolbox`, the skill that owns the jigs.
`compuse-git` references it there instead of shipping a copy. Ships with plugin 5.136.0.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] CORRECTED A CLAIM I MADE LAST RELEASE. I recorded these two copies as "already DRIFTED (15
      differing lines)" and deferred them as a which-behaviour-wins decision. Comparing the ASTs
      with docstrings stripped shows the executable code is IDENTICAL - every one of those 15 lines
      is a docstring or comment. The consolidation was mechanical all along; I mischaracterised it
      from a line count instead of a diff.
- [x] Neither TEST file was a superset by name, so both were compared body-by-body rather than
      picked. `compuse-git`'s "unique" test turned out to be byte-identical to the toolbox's under
      a different name; the toolbox additionally has a `None`-branch regression test. So the toolbox
      file wins outright and no coverage is lost - verified by normalising the renamed test and
      diffing.
- [x] The surviving copy ABSORBED what the deleted one did better rather than simply replacing it:
      the three-line usage block, the `find_repos` docstring, and one clarifying test comment.
- [x] Owner chosen by subject, not by convenience: `compuse-toolbox` exists to ship these six jigs
      and `git_state` is one of them; `compuse-git` only borrowed it. Its reference now states the
      owning-skill home, per the cross-skill script rule.
- [x] `compuse-git` now ships no `.py` at all, so its `tests/` and `scripts/` directories are gone
      rather than left holding an orphan conftest.
- [x] Verified: duplicate `.py` basenames drop from 6 to 4, and the four that remain are benign -
      vendored `demos/`/`examples/` files the gate already excludes, plus per-directory
      `conftest.py`. Suites: 1388 plain, 1382 with the CI dependency set, gate green. The script was
      also run once from its surviving home.
- [x] No session narrative or private provenance added; no machine paths added.
