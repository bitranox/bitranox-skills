# Skill-writer checklist: write-humanize-de strip-script coverage sentence (2026-09-18)

Scope: the one sentence describing what `strip_typographic_tells.py` replaces. It went false when
German quotation marks left `tell_chars.RANGES` in plugin 6.14.0: it promised a rewrite of curly
quotes and guillemets that the script no longer performs. Reference-type edit, no workflow, name,
frontmatter or trigger changed.

## RED (baseline, pre-change text)

- [x] The behavioural arm was REPLACED by a text check of the artifact, and this is why:
      `redcheck.py --corpus-cascade` over the directory a dispatched agent inherits read 1167
      documents and reported STRONG inherited coverage, naming
      `/media/srv-main-softdev/CLAUDE.local.md` (8 shared terms), the memory facts
      `feedback-fix-tells-on-the-way` and `no-em-dashes`, and this project's own `CLAUDE.md`.
      Those documents teach the OLD answer, so a subagent would have answered from them in both
      arms: RED would pass for the wrong reason and GREEN could fail while the text was correct.
      The skill-writer's stated route for inherited coverage is a text check of the artifact, and
      that is what was built.
- [x] RED proven, not assumed: `test_the_skill_claims_no_rewrite_the_table_does_not_perform`
      failed against the pre-change text naming the exact over-claims -
      `write-humanize-en promises a rewrite the script no longer does: ['guillemets', 'curly
      quotes']` and the German pair for `write-humanize-de`.
- [x] A first run of that test failed with `NameError: name 'Path' is not defined` - an instrument
      failure, not a result. Fixed and re-run before the failure was read as RED.
- [x] Two control tests in the same pair passed throughout
      (`test_the_coverage_sentence_still_names_something_the_table_does`), so the guard cannot
      pass by matching an empty or vanished sentence.

## GREEN (post-change text)

- [x] Both sentences now name what the script actually rewrites - the curly apostrophe and the
      closing quotation marks - and both state positively that German quotation marks and
      guillemets are left alone, with the reason.
- [x] Full hook suite green: 2887 passed, 1 skipped, 1 xfailed, exit code read from a file rather
      than a pipe.
- [x] The guard is keyed to `mod.TABLE`, not to a second copy of the character list, so the
      sentence and the code cannot drift apart again without a named failure.

## REFACTOR

- [x] The generic phrases are what the guard rejects, deliberately: the script still rewrites two
      of the four English curly quotes, so "curly quotes" as a blanket term is now an over-claim
      whichever language says it. The fix is specificity, and the test enforces it.
- [x] DECLINED: section 20 of the German skill still advises flattening typographic quotes to
      straight ones. That is a style recommendation about ChatGPT's inconsistency, not a claim
      about the script, so it is not false - but it now sits against a house decision that the
      characters are correct German. Changing published advice is a separate judgement and is
      recorded for the user rather than taken here.
- [x] DECLINED: restating the full permitted set in each skill. `tell_chars.py` is the canonical
      list and both skills point at it; a second copy is the drift this change exists to end.

## Security and hygiene

- [x] Diff reviewed: prose only in both SKILL.md files, no secrets, no credentials, no private
      hostname, address or path. The test file adds no non-ASCII source - the one German term it
      needs is built with `chr(0x00FC)`.
- [x] No session narrative, operator instruction or scratch path in the skill text or this
      artifact.
