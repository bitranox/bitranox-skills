# skill-writer checklist - meta-dream-tree (a voice rewrite needs the owning level and the stored slug)

Change: step 6's parenthetical. "slug-stable via `add --slug`" now says WHICH slug and WHICH level,
because the voice pass is the one place a dream rewrites many facts in a row and the failure it
invites is silent. Text only; the sibling instruction in `meta-self-improve` step 3 has its own
checklist.

## PLAN
- [x] Skill type: technique (a numbered procedure). One parenthetical, in the pass that rewrites
      stored facts.
- [x] Trigger is measured in this pass's own run, not imagined: an `add` carrying a fact's CURRENT
      TITLE with no `--slug` derived a different slug - the fact had been retitled since capture -
      and minted a second pointer and body, printing the new slug like an ordinary write. An `add`
      aimed at a level that does not own the pointer is refused instead, naming the slug and not
      the level.
- [x] Scope: one parenthetical. The step's own advice (do not rewrite a hook merely for exceeding
      the soft cap) is unchanged.

## RED
- [x] The failure is the engine's behaviour under the shipped wording, observed twice in one run,
      so the RED is that record rather than a subagent arm: there is no judgement to watch, only an
      instruction with two omissions. `--slug` alone, which is what the old parenthetical said,
      does not prevent either one.
- [x] Non-vacuous: the duplicate was caught by a line count on the file that should have grown, not
      by the engine, which reported success both times.

## GREEN
- [x] The parenthetical now carries all three parts a caller needs - the stored slug, the owning
      level, and what each omission costs - in one line, so the step stays scannable.
- [x] Consistent with `meta-self-improve` step 3, which states the same rule in full for the
      capture path. This skill points at the behaviour rather than restating the recipe, matching
      how it already defers the engine command table to the backend reference.

## REFACTOR
- [x] The voice pass is the right place for it: it is where a dream loops over stored facts, so a
      wrong upsert there multiplies rather than happening once.
- [x] Declined: repeating the `find` recipe for locating the owning level here. It lives in
      `meta-self-improve` step 3, which this skill already names as required background, and a
      second copy is what drifts.
- [x] Checked step 5's `move` guidance for the same omission: it takes `--from-level` and
      `--to-level` explicitly, so it cannot make this mistake and needs no change.

## Quality
- [x] Frontmatter untouched; no description change, so no routing keyword moved.
- [x] The dream-family contract test still passes, so no shared literal was duplicated into this
      SKILL.md by the edit.
- [x] No session narrative, scratch paths, or machine-specific values in the skill or here.
- [x] Tell sweep and table reformat run clean on the changed Markdown.
