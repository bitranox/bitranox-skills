# skill-writer checklist - coding-python-gitignore (2026-08-28, audit bucket E+F)

One unanchored claim: the `[performance]` defaults table stated exact numbers with no version.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference/technique. The defect is a FACTUAL claim carrying no version or date,
      so the test is a ground-truth check against the installed package, the live catalogue or the
      running tool - not a pressure scenario.
- [x] Scope: correction only. No new capability, no procedure reshaped.

## RED
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than the draft and cannot fail honestly. The route
      taken instead is a ground-truth check, whose result is immune to inherited context.
- [x] The table gave `dir_cache_max = 8192` as fact. A reader tuning against it has no way to
      notice a later release changing the default, unlike sibling skills here that pin a
      checkable baseline.

## GREEN
- [x] The table is dated to igittigitt 2.2.3 (the current PyPI release; `_DIR_CACHE_MAX = 8192`
      read from its source) and carries a check the reader runs against their OWN install.
- [x] That check was EXECUTED before shipping, not just written:
      `python -c "import igittigitt, inspect; print(inspect.signature(igittigitt.IgnoreParser.__init__))"`
      prints `(self, dir_cache_max: int = 8192) -> None`.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched, so no routing keyword moved and the description cap is unaffected.
- [x] Mirrored skill: the twin under `libs/igittigitt/` carries the same change.
