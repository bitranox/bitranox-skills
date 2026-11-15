# Backup only by store_manifest, nap after an in-flight store run, sibling-change attribution

Three queued contributions to the nap: step 2's backup must be the tool's own, an owed nap waits
for a store run that is between its backup and its verify, and a sibling pointer change on a live
tree is attributed before the nap is called clean.

- [x] Step 0b: rejected and removed decisions read; the one rejected entry (reconcile verify step)
      is not touched by this change.
- [x] Premise checks: the backups root holds hand-rolled nap backups in several layouts (one with
      `manifest.json`); `store_manifest.load_manifest` refuses a dir without `manifest.json`
      ("cannot read <out>/manifest.json"); `memory_engine._write_lock` takes no lock and writes
      nothing on a dry run.
- [x] RED route: `redcheck --corpus-cascade` flagged inherited coverage for two scenarios, so the
      evidence is a text check of the pre-edit text (quote or NONE), not a behavioural arm. RED on
      opus and haiku: Q1 quoted only the command (no sentence that a hand copy fails), Q2 and Q3
      answered NONE.
- [x] GREEN on opus and haiku with the edited text: Q1 quoted "Only that command's backup counts",
      Q2 quoted "finish that run's verify and store commit first, then nap", Q3 quoted "A dry run
      writes nothing, so never attribute a change to one".
- [x] Gap closed: both tiers reported that "a change no peer write accounts for is the nap's"
      ignored the capture carve-out, and haiku that the window was undefined; the sentence now
      excludes the step 1 carve-out and names the window (start to step 6 verify). Re-probe of the
      attribution questions on haiku and opus: carve-out case answered "not a violation" by quote.
- [x] Gaps declined: how to list sessions and find their transcripts (a search the reader already
      knows; the rule is what counts as a write), how to get past the Stop gate while finishing
      the run (a blocked Stop only keeps the turn going, the work continues), and every question
      whose answer sits in the elided core or step 1 text.
- [x] Decisions: d-20261115-e026a585, d-20261115-de48ad34, d-20261115-eb4b62c0
- [x] Tiers: opus and haiku, text-only agent type, pasted text; 2 RED + 2 GREEN + 2 re-probe cells.
- [x] Width and fence check over the added lines printed nothing; the paragraph after each
      insertion read for a re-bound reference.
- [x] Finder for version-history wording over the added lines: no hit. ASCII only, no private
      host or path.
