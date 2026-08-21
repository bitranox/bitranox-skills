# skill-writer checklist - meta-dream-crosstree (redirect session-review to a file)

Change: the `session-review` invocation now redirects to a file and tells the reader to read the
FILE. One sentence in this skill's step; the full explanation lives in `meta-dream-tree`'s
`references/dream-core.md`, which both skills share.

## PLAN
- [x] Skill type: process. The edit changes ONE step of a procedure, not the procedure's shape.
- [x] Trigger is measured: run inline, `session-review` is silently truncated - the harness
      persists its output and shows a preview, and that preview parses cleanly as JSONL so nothing
      signals the gap. The existing guidance was correct but started one step too late: it taught
      how to DETECT the truncation and reconstruct from a byte range, when the redirect avoids it.
- [x] Checked every place that teaches the invocation, not just the nominated one: three skills
      mention `session-review`. `meta-dream-crosstree-deep` only defers to this skill's procedure by
      name and carries no invocation, so it needed no edit - checked rather than assumed.
- [x] Scope: one line here, the dream-core.md section it points at, no script, no new skill.

## RED
- [x] The failure is recorded twice with numbers, both from real runs: a banner reporting 1,958,654
      unreviewed bytes against a persisted 244,360 - an eighth - and a 1,259,622-byte stretch
      against a 2KB preview. In both, advancing the watermark afterwards would have discarded the
      remainder permanently, because `session-reviewed` is a one-way mark.
- [x] The RED for THIS edit is that the old text's first instruction produces the truncation: a
      reader who follows it exactly gets a cut result and only then learns to detect it.

## GREEN
- [x] Verified on a real run rather than reasoned about: `session-review` redirected to a file left
      1,590,965 bytes on disk while its own banner claimed 1,590,075 unreviewed bytes - banner plus
      content, the whole stretch, in one pass and with no byte-range reconstruction.
- [x] The byte comparison is KEPT, demoted from a recovery step to a cheap confirmation. Dropping it
      would remove the only check that the redirect worked.
- [x] The inline-recovery instructions are kept too, for a reader who already ran it inline.

## Design decisions
- [x] The one-line change here points at dream-core.md rather than restating the mechanism. Both
      dream skills read that file, so a second copy of the explanation would drift.
- [x] `> review.txt 2>&1` and not `| tee`. `tee` renders the output as well, which is exactly what
      the harness truncates, so it would reintroduce the problem while looking like a fix.
- [x] Stated as "the redirect is not optional" rather than a suggestion. The failure is silent and
      the loss is permanent, so a reader weighing convenience has no signal to weigh it against.

## Quality
- [x] ASCII only; verified by byte scan. No private paths - the file name is generic.
- [x] Present tense, no session narrative; the measurements are stated as facts about the tool.
- [x] The numbers in the shipped text are byte counts only. No transcript content, no path, no
      session id was copied into the skill or this file.

## Deliverables
- [x] `meta-dream-crosstree/SKILL.md` step 1; `meta-dream-tree/references/dream-core.md` invocation
      line plus its truncation section rewritten redirect-first.
- [x] From the upstream contribution queue; version bumped and CHANGELOG entry added in the same
      change.
