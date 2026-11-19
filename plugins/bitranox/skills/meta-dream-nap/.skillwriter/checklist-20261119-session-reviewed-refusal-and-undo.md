# skill-writer checklist - meta-dream-nap (2026-11-19, bare session-reviewed refusal and --to offset)

- [x] Receipt fresh; Step 0b `show --kind rejected,removed --full` run: the one rejected entry
      (`reconcile-verify-step`) is untouched. The live rule `session-reviewed-reuses-review`
      keeps its anchor "marks nothing when no review came since the last mark"; this edit adds
      the refusal case beside it.
- [x] Premises checked against `meta-dream-tree/dream_state.py`: a bare call with nothing shown
      since the last mark prints `nothing marked` and returns 0; with no session-review of this
      session for the cwd, or its transcript gone, `_mark_target` refuses and the call exits 2;
      the success line is `review watermark advanced from X to Y for <path>`.
- [x] RED (opus and haiku, pre-edit step): both read the no-review case as marking nothing with
      no exit code given, and answered NONE for the source of OFFSET.
- [x] GREEN and a final re-probe (opus and haiku): both quoted "it refuses, exit 2, and marks
      nothing" and "OFFSET is the "from" value X of that mark's success line"; the no-op case
      quoted with "(exit 0)".
- [x] Gap closed from GREEN: the exit code of the no-op case (0).
- [x] Gaps declined: recovering X when the success line was lost (no dream_state verb prints a
      watermark, `dream_state.py --help`).
- [x] Width and fence check over the added lines prints nothing; ASCII only; no machine path.
- [x] Decisions: d-20261119-da9ce742
