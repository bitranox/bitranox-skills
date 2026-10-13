# skill-writer checklist - ai-llm-jev-judge (2026-10-13, mirror of jev-judge 0.2.6)

Source: the `jev-judge` skill of `bitranox/btx-skill-jev-judge` at tag `v0.2.6`
(`skills/jev-judge/SKILL.md`). The only change is the five `uvx --from 'btx-skill-jev-judge>=X'`
floors, `0.2.5` -> `0.2.6`; no instruction text, frontmatter or name changed.

- [x] Skill type: technique; this change is a version floor, so there is no new behaviour for a
      RED/GREEN arm to fail on.
- [x] The twin's own diff for this release touches only the five floor lines in SKILL.md (its other
      files are package metadata, the committed uv.lock and the Python 3.15 classifier), checked
      line by line.
- [x] The floor names a version PyPI serves: the JSON API and the simple index both list `0.2.6`.
- [x] `uvx --no-cache --from 'btx-skill-jev-judge>=0.2.6' jev-judge --version` prints
      `btx-skill-jev-judge version 0.2.6`, and `--help` lists `check-key`, `run` and `summarize`,
      the three commands the skill runs. The commands themselves were not executed: they call the
      TypeSafe API and need a key. A uvx that resolved the index minutes before the release can
      still report only `<=0.2.5` until its cached index expires; `--no-cache` or a later run fixes it.
- [x] `repo-gate.py --mirror-of <tool repo>` reports `in sync` (exit 0) after the change.
- [x] Frontmatter untouched: no routing keyword moved, so the derived trigger and catalogue
      artifacts are unchanged.
- [x] No address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
