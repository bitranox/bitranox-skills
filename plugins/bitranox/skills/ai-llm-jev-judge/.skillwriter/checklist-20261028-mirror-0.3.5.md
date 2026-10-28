# skill-writer checklist - ai-llm-jev-judge (2026-10-28, mirror of jev-judge 0.3.5)

Source: the `jev-judge` skill of `bitranox/btx-skill-jev-judge` at tag `v0.3.5`
(`skills/jev-judge/SKILL.md`), regenerated here with only the `name:` line changed. Frontmatter is
byte-identical; the body changes in one sentence and the five version floors.

- [x] Skill type: technique. RED: 0.3.5 changes the CLI the skill describes. Measured on 0.3.4 from
      PyPI in a scratch HOME: `--set judge.api_key=x config`, `--set judge.workers=0 config` and
      `--set judge.api_key=x config --section judge` all exit 0, so the skill's advice to use
      `config --section judge` for a `judge.*` problem described a command that showed the value
      but never said it was wrong.
- [x] GREEN: on the 0.3.5 build, `config --section judge` still shows the layer of each value and
      then exits 78 with `Error: judge.<key>: <reason>`; the skill sentence now says exactly that
      ("then exits 78 naming the problem"). Pinned by seven tests in the tool repo's
      `tests/test_cli_config.py` and a live CLI probe (json and human format, `--section`,
      `--profile`).
- [x] The five `uvx --from 'btx-skill-jev-judge>=0.3.5'` floors name a version PyPI serves.
- [x] `meta-self-improve/jev_shadow.py` `JEV_JUDGE_FLOOR` follows the floor (pinned by
      `test_jev_shadow.py`).
- [x] Frontmatter untouched: routing keywords unchanged.
- [x] No version-history wording; ASCII only; no address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
