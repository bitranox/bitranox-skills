# skill-writer checklist - meta-dream-crosstree (backup dir per tree, relocate to a tree top)

Covers SKILL.md step 1 (the `<key>` and `<ts>` of the backup dir), step 4b (a relocate whose
target is a tree top) and step 8 (a relocate as an expected verify difference).

- [x] Change: step 1 defines `<key>` as `crosstree-<name of that tree's anchor dir>` (a number
      added when two anchors share a name) and `<ts>` as the time that backup starts,
      `YYYYMMDD-HHMM`, and says a second tree never reuses a backup dir, because a backup into a
      dir that holds one replaces it. Step 4b lists a relocate whose target is that tree's top as
      a misplacement re-home to the tree top with its cost (the UTF-8 length of its pointer line
      plus the newline, dream-core.md Mode), proposed in `propose`, applied in `auto`. Step 8
      names a 4b relocate as an expected difference: removed in its source tree's verify, added in
      its target tree's. The sentence after it starts "Verify's `pointer blocks` lines", since
      "Its" would now bind to the relocate.
- [x] Step 0b: `show --kind rejected,removed --full` printed nothing; plain `show` listed one rule
      (d-20261110-bcf1ef3c), whose anchor is untouched. No decision is reversed.
- [x] Mechanism claim checked against store_manifest.py `_check_out`: an `--out` dir that holds a
      `manifest.json` is accepted as an earlier backup, and a re-backup clears its `store/` and
      `levels/` first, so a second tree backed up into it replaces the first tree's backup.
- [x] `off`: the skill's Mode section says "`off` skips this skill entirely", so 4b states no
      `off` behaviour for a relocate to a top (recorded as rejected, d-20261110-8ee5b8fa).
- [x] RED (opus, HEAD text of steps 1, 4b and 8 plus dream-core Mode pasted): `<key>` NONE and
      the consequence of sharing a dir NONE; a relocate's `removed x` classed as a decided move
      only by its own reading, with the gap "C does not describe how a cross-tree relocate
      appears in verify"; a relocate to beta's top proposed, cost NONE ("B says nothing about a
      cost and doesn't point to D").
- [x] GREEN (opus and haiku, edited text pasted, 7 questions x 2 tiers): `<key>` crosstree-alpha
      and crosstree-beta, sharing refused with "A second tree never reuses a backup dir" quoted;
      `removed x` an expected difference, "A 4b relocate is an expected difference" quoted; the
      relocate to beta's top proposed with the UTF-8 pointer-line cost quoted. No arm called a tool
      other than its hand-back.
- [x] GREEN gaps closed: both tiers reported the `<ts>` format undefined and "tree dir name" not
      tied to the anchor; step 1 now gives `YYYYMMDD-HHMM` and "name of that tree's anchor dir".
      Opus reported a contradiction between 4b's "under `off`" and the Mode section's skip; the
      clause is removed.
- [x] Re-probe on the final text (opus and haiku, Mode line plus steps 1 and 4b, 6 questions x 2
      tiers): both build `crosstree-alpha-20261110-1405` and `crosstree-beta-20261110-1407`;
      relocate to a top proposed in `propose`, applied in `auto`, cost quoted; under `off`, "step
      4b does NOT run", quoting "`off` skips this skill entirely". No new undecided gap.
- [x] Declined re-probe gaps: the format of the number for two same-named anchors and the
      timezone of `<ts>` (only distinctness matters, and both trees of one run use one clock);
      which pointer line is measured (the text says "the bytes it adds to the top block", the
      target's); the destination of a hand-copied native `memory/` dir (unchanged step 1 text,
      not part of this change); docs/reference.md's `off` "manual run" beside this skill's skip
      (that row describes the knob for the dream family and mirrors dream-core Mode's `off`
      bullet; this skill's Mode states its own exception).
- [x] Width and fence check over the added lines printed nothing; the paragraphs after each
      insertion were read (the step 8 back-reference fixed above).
- [x] Decisions: d-20261110-ebf3dda9, d-20261110-09225128, d-20261110-37ae62b5, d-20261110-8ee5b8fa
