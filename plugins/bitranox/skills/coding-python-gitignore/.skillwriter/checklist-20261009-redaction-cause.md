# skill-writer checklist - coding-python-gitignore (2026-10-09, the component that masks max_token_bytes)

The `[performance]` paragraph said `igittigitt config` masks `max_token_bytes` because "the log
scrubber masks any key containing token". The log scrubber does not mask it: lib_layered_config's
`is_sensitive()` does, from the key name alone.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The defect is a wrong cause, so the test is a retrieval scenario
      (which component masks it, and can a setting stop it) plus executed controls on the real tool.
- [x] Scope: the redaction sentence under the confirm command. Table, one-liner and frontmatter
      unchanged.

## Ground truth (igittigitt 2.2.4, lib_layered_config 7.0.1)
- [x] `lib_layered_config.is_sensitive('max_token_bytes')` is True, `'stdin_chunk_bytes'` False;
      the pattern in `lib_layered_config/domain/redaction.py` matches `token`, `password`,
      `secret`, `credential`, `apikey` and similar as a substring of the key name.
- [x] Control removing the log scrubber's `token` pattern
      (`IGITTIGITT___LIB_LOG_RICH__SCRUB_PATTERNS__TOKEN=`): the value stays masked.
- [x] `igittigitt config --help` lists no unredact or reveal option.
- [x] `igittigitt config --section performance --format json` also prints
      `"max_token_bytes": "***REDACTED***"`.

## RED
- [x] `redcheck --corpus-cascade .` reported inherited coverage on the tree-top memory index; the
      shared terms are general words (masks, setting, performance) and that file never mentions
      `is_sensitive` or the masking cause, so the behavioural arm stands.
- [x] Haiku baseline-probe given the old paragraph named "the log scrubber", guessed it is
      `lib_log_rich`'s, and advised against weakening it. Skill gaps it reported: the scrubber is not
      named, no setting is named, `--format json` behaviour unstated.

## GREEN
- [x] Haiku baseline-probe given the new paragraph quoted "through lib_layered_config's
      `is_sensitive()`" as the masking component, said the log scrubber is not involved and no
      setting stops it, and named the one-liner as the route to the value.
- [x] GREEN skill gap "does `--format json` also mask it" closed in the text after the executed
      check above.
- [x] Declined gap: "no non-Python route to the default". The table directly below gives the
      default, and the one-liner covers an installed version that differs.
- [x] RED against GREEN, both directions: nothing RED produced is missing from GREEN except the
      advice not to weaken the scrubber, which no longer applies once the scrubber is not the cause.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved.
- [x] Mirrored skill: the same SKILL.md change is in the twin under `libs/igittigitt/`;
      `repo-gate.py --mirrors` reports the pair in sync.
