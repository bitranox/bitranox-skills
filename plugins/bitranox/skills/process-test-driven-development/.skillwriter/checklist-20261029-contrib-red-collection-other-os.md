# skill-writer checklist - process-test-driven-development (RED at collection, RED on another OS)

- [x] Change: SKILL.md "Verify RED - Watch It Fail". The "Failed, but for which reason?" item (1)
      now says an ImportError at collection is no RED even when it names the symbol under test,
      and prescribes a no-op stub carried into every RED arm; a new paragraph "A failure that
      exists only on another OS is not RED on yours" follows it.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`); the editing agent loaded
      bitranox:meta-skill-writer through the Skill tool before its first edit.
- [x] RED as a text check: the pre-edit text listed "an ImportError from a typo rather than from
      the missing module" among non-REDs, which reads as if an ImportError from the missing
      module were a valid RED (the opposite of the rule); `grep -niE 'stub|another OS|other OS'`
      found no stub-first or other-platform RED rule in the section.
- [x] GREEN quote-back: "The ImportError is no RED even when it names exactly the symbol the test
      is about" and "**A failure that exists only on another OS is not RED on yours.**"
- [x] Mechanism: pytest reports an import failure at collection as a collection ERROR for the
      whole module, before any test body runs (matches the existing skipif-at-collection rule in
      process-test-design).
- [x] Mirror: `repo-gate.py --mirrors` lists no twin for process-test-driven-development.
- [x] Description unchanged; ASCII only in added lines; present tense; no private name.
- [x] `plugins/bitranox/skills/process-test-driven-development/tests`: run with CI's dependency
      set together with the skill-content hook tests, all passed (scripts untouched).
