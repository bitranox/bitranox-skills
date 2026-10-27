# skill-writer checklist - ai-llm-jev-judge (2026-10-27, mirror of jev-judge 0.3.3)

Source: the `jev-judge` skill of `bitranox/btx-skill-jev-judge` at tag `v0.3.3`
(`skills/jev-judge/SKILL.md`). The only change is the five `uvx --from 'btx-skill-jev-judge>=X'`
floors, `0.3.2` -> `0.3.3`; no instruction text, frontmatter or name changed.

- [x] Skill type: technique; this change is a version floor, so there is no new behaviour for a
      RED/GREEN arm to fail on.
- [x] The twin's own diff for this release (`v0.3.2`-era main to `v0.3.3`) touches only the five
      floor lines in SKILL.md (its other files are package metadata, the CHANGELOG, the Makefile
      and the committed uv.lock), checked line by line.
- [x] The floor names a version PyPI serves: the JSON API and the simple index both list `0.3.3`,
      wheel and sdist.
- [x] `uvx --no-cache --from 'btx-skill-jev-judge>=0.3.3' jev-judge --version` prints
      `btx-skill-jev-judge version 0.3.3`, and `--help` lists `check-key`, `run` and `summarize`,
      the three commands the skill runs. The commands themselves were not executed: they call the
      TypeSafe API and need a key.
- [x] The marketplace copy differs from the twin only by the three allowed divergences (`name:`,
      the H1 suffix, the self-install blockquote); the floor lines are byte-identical on both sides.
- [x] Frontmatter untouched: no routing keyword moved, so the derived trigger and catalogue
      artifacts are unchanged.
- [x] No version-history prose added: the only changed lines are install floors, which the
      latest-release finder treats as not history.
- [x] No address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
