# skill-writer checklist - coding-python-rpyc (2026-09-27, removed-module caveat in docs/howto.md)

The monkey-patching recipe in `docs/howto.md` imports `telnetlib` and names `asyncore` as an example
with no version caveat, while the distilled copy in `classic-and-tutorials.md` carries one.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference (vendored upstream doc). The defect is a factual gap, tested by
      executing the imports on the interpreters the caveat names.
- [x] Scope: one caveat paragraph added above the snippet; the upstream example itself is kept
      verbatim. SKILL.md and frontmatter unchanged.

## RED
- [x] Executed: `import telnetlib` raises `ModuleNotFoundError` on 3.13.13; `import asyncore`
      raises it on 3.12.13 and 3.13.13. The howto text gave no warning of either.

## GREEN
- [x] Caveat states: `asyncore` removed in 3.12, `telnetlib` in 3.13 (PEP 594); the telnetlib
      snippets run on 3.12 and older. Control: both import on 3.11.15, `telnetlib` on 3.12.13.
- [x] Consistent with `classic-and-tutorials.md:222`; a grep of the skill for these and other
      PEP 594 module names finds no other use.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
