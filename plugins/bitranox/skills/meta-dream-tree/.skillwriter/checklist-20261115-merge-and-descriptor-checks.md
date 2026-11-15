# Checklist 2026-11-15: merged hook vs live member hooks; descriptor STACK/CHILDREN on disk

Two edits: `references/dream-core.md` (Dedup semantics) gains a paragraph on checking a merged
hook against each member's live pointer hook, keeping triggers up to the hard cap, settling a
member contradiction with an instrument, and reading bodies with `factedit.py show --prose-only`
for a loss check. `SKILL.md` step 0b checks every level's STACK and CHILDREN against disk, and
its "only synthesize" list names that check. A missing verb in the Dedup semantics opening
sentence ("cross-links") is fixed on the way.

- [x] Step 0b: `skill_decisions.py show meta-dream-tree --kind rejected,removed --full` read; the
      one rejected entry (ref-map-after-dropped-move) is unrelated to both edits.
- [x] Decisions: d-20261115-fe2e96b1, d-20261115-62e1031b, d-20261115-08722a50

## RED (pre-edit text, opus and haiku, text-only baseline-probe, quote or NONE)

- [x] What a merged hook is checked against: opus inferred "each member's current text" with no
      governing quote for review drafts; haiku answered NONE for a hook-specific check.
- [x] Soft cap versus a trigger at 430 chars: both NONE (both chose to keep it by reasoning).
- [x] Two members contradict: both NONE for a resolution step.
- [x] STACK floor mismatch on a non-template level: both said STACK is not a listed trigger; the
      level was synthesized only because CHILDREN also mismatched.
- [x] Tool or event lists against their source: both NONE.
- [x] The `show --body` loss-check question is VOID in RED: the prompt's setup line stated that
      the body's frame repeats the hook, which hands the answer over. Evidence for that clause is
      the file text instead: the pre-edit skill names neither `--prose-only` nor the frame.
- [x] Coverage: the lesson is a mix of existing text (a trigger-coverage skeptic lens; CHILDREN
      versus subdirectories) and new text; RED was asked for a quote of the supplied excerpt, so
      inherited context could not answer for it.

## GREEN (new text, opus and haiku)

- [x] All six questions answered with a direct quote of the new text on both tiers: live hooks via
      `factedit.py show --slug`, keep the trigger up to the hard cap, settle with an instrument,
      `show --prose-only` for the loss check, STACK mismatch re-synthesized, tool lists checked.
- [x] Control (a 300-char hook that keeps every trigger): both tiers left it as is; the cap
      sentence is permissive, not a target.
- [x] `factedit.py show --slug no-em-dashes --prose-only` run against a real tree: rc 0, the body
      prose printed with no `description:` line.

## REFACTOR

- [x] Both GREEN tiers reported that the "only synthesize" list lacked STACK while the new
      sentence synthesized a STACK mismatch: the list now reads "CHILDREN list or STACK (named
      tool and event lists included) disagrees with disk (below)", and the new sentence ends "a
      mismatch is stale". A haiku re-probe then reported "Those first three test STRUCTURE only"
      clashing with a disk check and the tool-list case missing from the list: both closed in the
      same sentence ("test STRUCTURE and disk facts only"); final haiku re-probe below.
- [x] Declined: "trigger" undefined (SKILL.md defines trigger-first hooks, "When <situation>,
      <directive>"); a merge whose live triggers exceed the hard cap (the existing "whether it is
      really one fact" skeptic lens covers a split, and factedit's refusal names moving detail
      into the body); requires-python versus classifiers disagreeing, which key holds a tool list,
      a repo with no README, "giveaway phrasing" undefined (pre-existing, outside these edits).
- [x] Width and fence check over the added lines of both files printed nothing after the reflow;
      the paragraph after each insertion point was read (a heading in dream-core.md; the dispatch
      sentence in SKILL.md, which still continues the new sentence correctly).
- [x] Final haiku re-probe on the final text: no sentence contradicts another about which levels
      are synthesized; a STACK event list the wiring file does not match is synthesized (quote:
      "a named event or tool list against the source file that wires it; a mismatch is stale");
      control (everything matches disk) is not. Its remaining gaps are outside the excerpt or
      predate the edit (how MEANING is detected for a non-template level, whole versus per-key
      re-synthesis) and are declined as out of scope.
- [x] Tiers: opus and haiku for RED and GREEN (two cells each), plus two haiku re-probes on the
      reconciled list.
