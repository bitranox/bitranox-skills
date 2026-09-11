# skill-writer checklist - coding-python-layered-config (2026-09-12, override provenance)

One gap: the skill teaches provenance as the library's point, and says nothing about the one
call that returns a correct value beside a wrong source.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The change adds a mechanism and its remedy, not a rule to enforce,
      so the test is a coverage check against the file plus a quote-back.
- [x] Scope: one section extended. No frontmatter change, no routing keyword moved.

## RED
- [x] Behavioural RED not used, and the reason is recorded rather than assumed: this lesson is
      already a pointer line in this machine's always-loaded memory index, so any agent
      dispatched here inherits it and the arm cannot fail honestly. `redcheck --corpus-cascade`
      returned clean, which means NOT CAUGHT rather than absent, so its verdict is not the
      evidence here.
- [x] Coverage RED, with a positive control so a zero result means absent rather than a broken
      search: control `config.origin` 3 hits; `with_overrides` 0 hits; the replaced-layer
      wording 0 hits.

## GREEN
- [x] Same instrument after the edit: control 3 hits, `with_overrides` 1, replaced-layer
      wording 3.
- [x] Quote-back: the governing sentence is "A `--set` style override keeps the provenance of
      the layer it REPLACED", with the two details that decide whether the remedy lands - the
      dotted key is the section plus the key path, and a key no file defined must still record
      a source.
- [x] The end-to-end instruction is included, because the merge is correct in isolation and the
      defect exists only in what is displayed.

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added. The private repo census that prompted
      this (a template and its derived repos) is deliberately NOT shipped: the mechanism
      transfers, the inventory does not.
- [x] Frontmatter untouched, so the description cap is unaffected.
