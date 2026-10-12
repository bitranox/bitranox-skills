# skill-writer checklist - coding-python-gitignore (2026-10-12, config shows max_token_bytes)

igittigitt 2.2.5 declares `performance.max_token_bytes` not sensitive, so `igittigitt config`
prints its value. The `[performance]` paragraph said the value is always masked and that no
switch shows it - an absence claim that is false from 2.2.5 on. The paragraph is regenerated from
the twin in `libs/igittigitt/skills/python-gitignore/`, with the three conventional divergences
(name field, no H1 suffix change, self-install blockquote) re-applied.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is a stale absence claim, so the test is a retrieval
      scenario (how do I confirm a max_token_bytes override on 2.2.5) plus an executed check of
      the real tool.
- [x] Scope: the paragraph under the `[performance]` heading and its version line. Table,
      frontmatter and every other section unchanged.

## Ground truth (igittigitt 2.2.5)
- [x] `igittigitt config --section performance --format json` prints `"max_token_bytes": 1048576`.
- [x] `igittigitt config --section performance` prints `max_token_bytes = 1048576`.
- [x] The release's tests cover the JSON default, a value set with `--set`, and the human view.

## RED
- [x] The lesson is igittigitt-version-specific behaviour; no CLAUDE.md or memory text on this
      machine states what 2.2.5 prints, so the behavioural arm stands.
- [x] Haiku baseline-probe given the old paragraph and a 2.2.5 install answered that the command
      prints `"***REDACTED***"` and "cannot confirm that your .env override is in effect", quoting
      "`igittigitt config` has no switch that shows the value". Wrong for 2.2.5.

## GREEN
- [x] Haiku baseline-probe given the new paragraph answered `igittigitt config --section
      performance` and that it prints the value in effect (2097152 from the override), quoting
      the "prints all four keys as they are in effect" line, and read the redaction note as
      applying only before 2.2.5.
- [x] GREEN skill gaps, each declined with a reason: the default value (in the table directly
      below the paragraph, row `max_token_bytes`); where `.env` is read and the env-var naming
      (the layered-config section above lists the order and gives the `IGITTIGITT___` form); how
      to check the installed version (`igittigitt --version` in the install section); the exact
      output layout (the command itself shows it, and a script uses `--format json`).
- [x] RED against GREEN, both directions: RED's Python one-liner for reading the default is gone;
      the table gives the default and the command now gives the value in effect, so nothing a
      reader needs is lost.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved.
- [x] Mirrored skill: the twin under `libs/igittigitt/` carries the same paragraph;
      `repo-gate.py --mirror-of <igittigitt>` reports the pair in sync.
