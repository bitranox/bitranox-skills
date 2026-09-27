# skill-writer checklist - coding-python-gitignore (2026-09-27, the confirm command shows all four limits)

The `[performance]` table told the reader to confirm its defaults with
`inspect.signature(igittigitt.IgnoreParser.__init__)`, which prints only `dir_cache_max`; the other
three keys cannot be confirmed that way.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is a command that does not show what the text says it
      shows, so the test is executing the command against the real tool, not a pressure scenario.
- [x] Scope: the confirm sentence under the table. Table values and frontmatter unchanged.

## RED
- [x] Behavioural RED not used: this skill is installed here, so a probe answers from the shipped
      wording. Executed probe instead, on igittigitt 2.2.3: the old command prints
      `(self, dir_cache_max: int = 8192) -> None` - one of the four keys.

## GREEN
- [x] `igittigitt config --section performance` executed: prints `dir_cache_max = 8192`,
      `pattern_cache_max = 4096`, `stdin_chunk_bytes = 65536`, `max_token_bytes = "***REDACTED***"`.
      `--format json` gives the same four keys as JSON.
- [x] "As they are in effect" checked: with `--set performance.dir_cache_max=32768` the command
      prints 32768, so it reports overrides, not only defaults.
- [x] The redaction is stated in the text, with a one-liner for the real value, executed:
      `PerformanceSettings.model_fields['max_token_bytes'].default` prints `1048576`, matching the table.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] Mirrored skill: the same SKILL.md change applies to the twin under `libs/igittigitt/`
      (`repo-gate.py --mirrors` compares them).
