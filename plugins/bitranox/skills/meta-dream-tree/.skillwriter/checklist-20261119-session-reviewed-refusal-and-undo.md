# skill-writer checklist - meta-dream-tree (2026-11-19, bare session-reviewed refusal and --to offset)

- [x] Receipt fresh; Step 0b `show --kind rejected,removed --full` run: neither rejected entry
      (`ref-map-after-dropped-move`, `rederive-batch-after-scratch-review`) concerns the review
      watermark.
- [x] Premises checked against `dream_state.py`: `_mark_target` refuses a bare call when this
      session recorded no session-review for the cwd, or its transcript is gone, and never
      resolves a transcript itself; `_session_reviewed` prints
      `review watermark advanced from X to Y for <path>`, X being the mark before the call;
      `_rewind` refuses an offset past the current mark with exit 2. `tests/test_dream_state.py`
      and `tests/test_dream_state_prose.py` pass.
- [x] SKILL.md checked for the same description: it never mentions session-reviewed or `--to`;
      only `references/dream-core.md` changes here (the nap's copy changes in its own skill).
- [x] RED (opus and haiku, pre-edit dream-core and nap text): both answered NONE for where the
      `--to` offset comes from and read a bare call with no review as a silent no-op.
- [x] GREEN and a final re-probe (opus and haiku): both quoted "X, the "from" value, is where
      the mark stood before" and the bare-form refusal sentence, exit 2.
- [x] Gaps declined: recovering X when the success line was not captured (no dream_state verb
      prints a watermark, `dream_state.py --help`); `--prose` with `--to` (the rewind ignores
      it, `_session_reviewed` returns through `_rewind` before reading it).
- [x] Width and fence check over the added lines prints nothing; ASCII only; no machine path.
- [x] Decisions: d-20261119-8206749e
