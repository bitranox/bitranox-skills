# Review checklist 2026-10-30: bump step, git-URL floors, strict markers

Entries covered:

- E5/E6: pytest 9.2 with strict markers exits 4 on an unregistered marker that bmk's `-m` names.
- E8: choose the bump step from everything unreleased, not from the change just made.
- E12: bmk's cooldown floor pins never see the floors a git-URL dependency declares.

Files: `SKILL.md` (one bullet in the bump section, one bullet in the cooldown section, one
paragraph in the test section, one troubleshooting row).

## Claims and their evidence

- [x] E5/E6: measured in a scratch project with `--strict-markers` in `addopts` and
      `-m "not integration"`: pytest 9.1.1 exit 0, pytest 9.2.0 exit 4 with
      `Unknown marker(s) in '-m' expression: integration`; `strict = true` also exit 4; with
      `markers = ["integration: ..."]` registered, exit 0.
- [x] E8: argued. Nothing in the skill told the reader to pick the bump step from what is
      unreleased; the bullet sits after "Before a bump, check whether the current version was
      ever released". `git describe --tags --abbrev=0` and `git log --oneline <tag>..HEAD` are
      standard git; both were run in the bmk repo (3.33.1 tag, 0 commits since).
- [x] E12: read bmk 3.33.1 source: `_FloorDemand.add` takes requirements only from
      `_releases_of(name)`, which reads PyPI; no `.url` handling exists in `_dependencies.py` or
      `_supply_chain.py`, so a git source's floor is never walked.

## Mechanical checks

- [x] Text check against HEAD: each new rule's key phrase ("Choose the bump step from everything
      unreleased", "invisible to those pins", "Register every marker the", the `exits 4` row) has
      0 hits in `git show HEAD:...` and 1 hit now.
- [x] Added lines ASCII only (grep -P for non-ASCII: 0), none over 100 columns outside the table
      row, table canonical.
- [x] The same text applies to the bmk tool repo's twin (`patch --dry-run` clean there).

## Probes (bitranox:baseline-probe, text only)

- [x] RED: an opus arm without the text answered several questions from knowledge it already had,
      so it was contaminated; the text check above stands in for it.
- [x] GREEN: opus and haiku arms with the edited text answered the batch's questions correctly
      with quote-backs, including the strict-marker exit 4 and the git-URL floor.
