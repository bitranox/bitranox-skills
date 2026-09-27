# skill-writer checklist - docs-generate-schematics (2026-09-27, model IDs named, overridable)

SKILL.md never named the two OpenRouter model IDs, when they were checked, or how to list the
current ones, and a retired preview ID could only be replaced by editing the script.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference plus a bundled script. Test approach: executed probes of the CLI and
      the list command, and pytest cases for the new flags written before the code.
- [x] Scope: one SKILL.md paragraph plus a code block; `--image-model` / `--review-model` on both
      scripts. Frontmatter unchanged.

## RED
- [x] Executed: the previous `generate_schematic_ai.py` given `--image-model vendor/x` exits 2,
      `unrecognized arguments`. SKILL.md grep for the model IDs, a date or the list command: none.
- [x] Five new tests failed on the previous source (no `DEFAULT_*_MODEL`, no flags, SKILL.md
      without the IDs).

## GREEN
- [x] All 100 tests in `tests/` pass under CI's dependency set. The requests name the defaults when
      no flag is given and the override IDs when it is; the wrapper forwards only an explicit
      choice, as `--flag=VALUE`; a test pins that SKILL.md names the IDs the script sends.
- [x] `--help` of both scripts lists the flags with their defaults. The same parse now reaches the
      API-key check instead of a usage error.
- [x] List command executed without credentials: HTTP 200, 458 IDs, both default IDs present
      (the date stated in SKILL.md and the script). No key and no identifying header was sent.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
