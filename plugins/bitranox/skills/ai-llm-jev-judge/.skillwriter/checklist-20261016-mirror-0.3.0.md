# skill-writer checklist - ai-llm-jev-judge (2026-10-16, mirror of jev-judge 0.3.0)

Source: the `jev-judge` skill of `bitranox/btx-skill-jev-judge` at tag `v0.3.0`
(`skills/jev-judge/SKILL.md`). The only change is the five `uvx --from 'btx-skill-jev-judge>=X'`
floors, `0.2.6` -> `0.3.0`; no instruction text, frontmatter or name changed.

- [x] Skill type: technique; this change is a version floor, so there is no new behaviour for a
      RED/GREEN arm to fail on.
- [x] The twin's own diff for this release touches only the five floor lines in SKILL.md, checked
      line by line; the regenerated file differs from the source only in its `name:` line.
- [x] The floor names a version PyPI serves: the JSON API and the simple index both list `0.3.0`.
- [x] The four Commands lines, extracted from SKILL.md with grep and run unchanged on 62 items,
      all exit 0; `--version` prints `btx-skill-jev-judge version 0.3.0`. The release drops the
      `btx_skill_jev_judge` command, which SKILL.md never used (0 occurrences in either copy).
- [x] `repo-gate.py --mirror-of <tool repo>` reports `in sync` (exit 0) after the change.
- [x] Frontmatter untouched: no routing keyword moved, so the derived trigger and catalogue
      artifacts are unchanged.
- [x] No address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
