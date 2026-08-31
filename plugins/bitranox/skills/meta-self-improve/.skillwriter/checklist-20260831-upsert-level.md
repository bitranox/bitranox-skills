# skill-writer checklist - meta-self-improve (an upsert needs the owning level AND the stored slug)

Change: step 3's update instruction. "Rerun the engine `add` with the same slug/title - it upserts"
is true only from the level that owns the pointer, and only when the slug is passed explicitly. The
step now says both, with the failure each omission produces. No behaviour change, no script change.

## PLAN
- [x] Skill type: technique (a procedure with an engine command in it). The defect is in the
      procedure's own instruction, so the fix is text.
- [x] Trigger is measured, both halves, in one run of this procedure:
      - `add --slug <a slug owned by another level>` was REFUSED with
        `slug '<slug>' already exists in this tree; suggested: '<slug>-2'`. The message names the
        slug and not the level, so it reads as "this fact exists" when it means "it exists
        somewhere else", and its suggestion would create the duplicate the step exists to avoid.
      - `add` with the CURRENT TITLE and no `--slug` derived a slug from that title, which is not
        the stored one for a fact retitled since capture. There was no collision to refuse, so it
        minted a SECOND fact - pointer and body - and printed the new slug like an ordinary write.
        Caught by a line-count check on the file that should have grown.
- [x] Scope: one paragraph in step 3 plus two sub-bullets; the sibling sentence in
      `meta-dream-tree` step 6 gets its own checklist.

## RED
- [x] The RED is the engine's own behaviour, not a subagent: the shipped text was followed exactly
      and produced a refusal in one direction and a silent duplicate in the other. A pressure
      scenario would add nothing - there is no judgement to observe, only an instruction that omits
      the level and the slug.
- [x] Verified against the source rather than inferred: the update branch is entered only when the
      slug is found among the entries at `--proj`; otherwise an existing body file is a
      `SlugCollision`, and a free derived slug is a new fact.

## GREEN
- [x] The step now says which level to aim at, why the collision message misleads, that the
      `-2` suggestion must never be accepted, and that the slug must be read off the pointer line.
- [x] The `find` recipe is spelled out rather than left as "grep for it", because a session
      `grep -r` skips `CLAUDE.local.md` as gitignored - the reader would get an empty result and
      conclude the fact has no owner.
- [x] Each half names its OWN failure mode. A reader who only skims takes away "level, and slug",
      which is the whole rule.

## REFACTOR
- [x] Kept in the step rather than moved to the backend reference: the sentence that was wrong is
      the one a reader acts on, and a pointer to another document is what let it stay wrong.
- [x] Declined: proposing an engine change that refuses a NEW slug whose title matches an existing
      entry elsewhere in the tree. It would have caught the duplicate mechanically, but it is a
      behaviour change to the single write path, and it belongs in its own change with its own RED
      rather than riding along with a doc fix. Recorded in the contribution queue.
- [x] Declined: documenting `rename` here as the way out of a stale slug. Renaming rewrites every
      `[[ref]]` and is a structural move a dream proposes rather than applies; naming it in the
      capture step would invite it as routine.

## Quality
- [x] Frontmatter untouched; no description change, so no routing keyword moved.
- [x] No session narrative, scratch paths, or machine-specific values in the skill or here - the
      measurements are stated as what the engine does, not as what happened to whom.
- [x] Tell sweep and table reformat run clean on the changed Markdown.
