# Review checklist - bump writes a dated Keep a Changelog heading (2026-10-29)

Change: one sentence in SKILL.md ("Version pins" area): `make bump-*` renames the CHANGELOG's
`[Unreleased]` heading to `## [X.Y.Z] - YYYY-MM-DD` (Keep a Changelog, no time of day). The text is
copied byte for byte from the bmk repo's twin `skills/devops-bmk/SKILL.md` (bmk commit 3abeb6a, the
code change that makes bump write that heading).

- [x] RED (text check, measured): the pre-edit line read "renames the CHANGELOG's `[Unreleased]`
      heading and syncs", naming no heading format; `repo-gate.py --mirrors` reported the
      devops-bmk pair as DRIFT against the twin.
- [x] GREEN (text check, measured): `repo-gate.py --mirrors` reports "in sync devops-bmk" and
      "0 of 12 mirrored pairs have drifted".
- [x] The behaviour it describes is the bmk change itself (3abeb6a: `_bump_version.py` and
      `tests/test_bump_version.py`); no subagent arm was run for a one-sentence factual update.
- [x] ASCII only; description unchanged, so no derived artifact moves.
