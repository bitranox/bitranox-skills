# skill-writer checklist - coding-python-gitignore (2026-10-22, asterisk-run segments)

igittigitt 2.2.9 reads a path segment of three or more asterisks as `**`, as git does; earlier
releases read it as a single `*`. The "When to reach for this" section gains one paragraph stating
the rule, its cases and the version. The paragraph is regenerated from the twin in
`libs/igittigitt/skills/python-gitignore/`, with the conventional divergences (name field,
self-install blockquote) re-applied; the H1 is identical in both.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: a retrieval scenario of three questions (what `***/build`
      ignores; whether `a***b` matches `a/b` and `aXYb`; whether upgrading from 2.2.8 changes
      `***/build`), each answered with a direct quote or NONE, plus a `Skill gaps` section.
- [x] Scope: one new paragraph under "When to reach for this". Frontmatter, table and every other
      section unchanged.

## Ground truth (git check-ignore, git 2.53; igittigitt 2.2.8 and the 2.2.9 change)
- [x] `***/build`: git ignores `build`, `x/build`, `x/y/build`, not `xbuild`; 2.2.9 agrees; 2.2.8
      ignored only `x/build`.
- [x] `a/****/b` and `a/***/b`: git ignores `a/b`, `a/x/b`, `a/x/y/b`; 2.2.9 agrees; 2.2.8 matched
      only `a/x/b`.
- [x] `logs/***` behaves like `logs/**` in git and in both releases.
- [x] `a***b`: git ignores `ab`, `aXb`, `aXYb`, `d/aXb`, not `a/b` or `aX/Yb`, identical to `a*b`;
      2.2.9 agrees.

## RED
- [x] `redcheck --corpus-cascade` over the igittigitt directory: no inherited coverage of the
      lesson, so the behavioural arm stands.
- [x] haiku and opus `baseline-probe`, given the pre-change section: NONE for all three questions.
      haiku guessed that `***/build` ignores only `build` (wrong); opus guessed the git behaviour
      correctly from memory but could not answer the version question.

## GREEN
- [x] haiku and opus, given the new section: each question answered with a direct quote of the
      new paragraph, all answers correct.
- [x] GREEN skill gaps: `xbuild` not stated (CLOSED: "(but not `xbuild`)" added); behaviour of
      other patterns before 2.2.9 not stated (CLOSED: "Earlier releases read such a segment as a
      single `*`" plus the `a/***/b` case); `IgnoreParser.match` not named in the excerpt (DECLINED:
      the full skill names it in "Library usage"; the probe saw an excerpt); slash-less patterns
      matching at any depth, file vs directory paths (DECLINED: general gitignore semantics, not
      what this paragraph is for).
- [x] RED against GREEN, both directions: no RED answer is lost; every GREEN answer is quoted.

## REFACTOR
- [x] Quote-back on the final text, haiku: `xbuild` not ignored on 2.2.9; `a/b` and `a/x/y/b` not
      ignored by `a/***/b` on 2.2.8; `a/x/y/b` ignored on 2.2.9, each with a direct quote.
      Remaining gaps (the literal reading of "only", `a/**/b` spanning any depth, `x***/build`)
      DECLINED: the first two are correct readings of general semantics, the third is covered by
      "a run inside a longer segment". No undecided gap left.
- [x] Tiers: haiku and opus for RED and GREEN (4 cells), haiku for the quote-back (1 cell).

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved.
- [x] Mirrored skill: the twin under `libs/igittigitt/` carries the same paragraph.
