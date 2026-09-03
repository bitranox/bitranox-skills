# skill-writer checklist - meta-dream-tree (2026-09-04, statusrot --slug and factedit --type)

Change: the Reference-files tool paragraph gains two clauses. `statusrot.py` gains that `clear`
records an adjudication, which is what stops an entry being re-reported until its hook changes, and
that it takes `--slug <s>` REPEATABLY - a bare `clear` certifies every candidate in scope, and a
slug that is not a flagged candidate is refused rather than recorded. `factedit.py` gains that
`show` reports the stored `type`, that an amend PRESERVES it, and that `--type` is the one
deliberate way to re-classify, refused on a pinned fact whose `amend-pinned` verb has no such flag.
No frontmatter change.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Skill type: REFERENCE. Tested by retrieval - can a reader holding only this text produce the
      right command - and by accuracy against the shipped tools.
- [x] The RED could fail honestly, checked rather than assumed. `redcheck --corpus-cascade` returned
      STRONG, and that verdict was ADJUDICATED against its named sources instead of its matched
      terms: the three documents it named contain zero occurrences of `--slug`, and across the
      1,034-file cascade no document mentions `statusrot` and `--slug` together. The overlap was
      vocabulary about the tool, not the answer. The flag did not exist anywhere before this change.
- [x] RED (pre-change text, inert probe, sonnet): concluded "Neither subcommand takes a
      per-candidate selector - no slug, no ID, no line number", explicitly refused to invent one
      ("Any per-slug or per-candidate flag (`--slug`, `--id`, `--match`, etc.) - not documented as
      existing. Inventing one would be fabricating tool behavior"), and offered exactly the bind
      this change removes: clear a whole level and over-assert, do not clear and keep the work in
      private notes, or escalate the gap to the tool's maintainer.
- [x] GREEN (post-change text, same scenario, same tier): produced
      `clear --chain --slug <s> x5 --note "..."`, citing the clause for why a bare clear is wrong
      ("that would wrongly adjudicate all 40, including the 35 you never opened") and reading the
      refusal clause correctly - that the slugs must be the verbatim flagged strings, obtained from
      `scan --json`, not paraphrases.
- [x] GREEN diffed against RED in BOTH directions. Nothing the baseline produced is missing: RED's
      level-boundary analysis and its escalate-the-gap option are moot once the capability exists,
      not lost, and RED's caution against over-asserting survives in GREEN in its own words.
- [x] Gaps reported by the test arms, each closed or declined:
      - CLOSED: GREEN said the text "never explicitly states that a later `scan` filters out or
        stops reporting a cleared slug", and that it had inferred the mechanism. The clause now
        says it. Verified by quote-back, which returned the governing text verbatim rather than a
        paraphrase or NONE: "`clear` records an adjudication, which is what stops an entry being
        re-reported until its hook changes".
      - DECLINED, pre-existing and out of scope: whether a cleared slug that changes again re-enters
        as RE-SURFACED. The bucket is named in the same paragraph and GREEN inferred it correctly;
        defining every bucket is a different change.
      - DECLINED, scenario artifact: no real slug strings were supplied, so the command uses
        placeholders. Withholding them is what made the retrieval question real.
      - DECLINED, prompt artifact: the launcher prefix and whether `--note` is mandatory came from
        the synthetic interface line in the test prompt, not from this file, which states the
        `hooks/run-python.sh` launch convention elsewhere.
      - NOTED, by design: the probe has no filesystem and could not execute the command. Execution
        is covered by the tools' own tests below.
- [x] ACCURACY: every behaviour the new clauses describe is pinned by a test that fails against the
      pre-change source. `statusrot clear --slug` - one slug leaves the others flagged, the flag is
      repeatable, a non-candidate slug is refused with nothing written, an unflagged real pointer is
      refused too, and a bare `clear` still records everything. `factedit` - `--type` is forwarded
      only when asked, absent otherwise, refused for a type the live engine does not know, refused
      on a pinned fact, and `show` reports the stored kind.
- [x] No frontmatter change: 0 frontmatter lines in the committed diff for this file, so no routing
      keyword moved.
- [x] Scripts ship with tests that pass: 151 in this skill's `tests/`, `repo-gate.py --ci` green at
      4700 passed, 8 skipped, 1 xfailed.
- [x] Present tense, no session narrative, no machine-specific address or path added.
