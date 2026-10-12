# skill-writer checklist - ai-llm-jev-judge (2026-10-12, mirror of jev-judge 0.2.5)

Source: the `jev-judge` skill of `bitranox/btx-skill-jev-judge` at tag `v0.2.5`
(`skills/jev-judge/SKILL.md`). The only change is the five `uvx --from 'btx-skill-jev-judge>=X'`
floors, `0.2.4` -> `0.2.5`; no instruction text, frontmatter or name changed.

- [x] Skill type: technique; this change is a version floor, so there is no new behaviour for a
      RED/GREEN arm to fail on.
- [x] The twin's own diff for this release touches only the five floor lines in SKILL.md (its other
      files are package metadata), checked line by line.
- [x] The floor names a version PyPI serves: the simple index lists `0.2.5` with its wheel and sdist,
      so the commands do not point at an unpublished version.
- [x] The twin's release ran the SKILL.md command lines against the published 0.2.5 (its
      `docs/skill-review.md` records that GREEN check).
- [x] `repo-gate.py --mirror-of <tool repo>` reports `in sync` (exit 0) after the change.
- [x] Frontmatter untouched: no routing keyword moved, so the derived trigger and catalogue
      artifacts are unchanged.
- [x] No address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
