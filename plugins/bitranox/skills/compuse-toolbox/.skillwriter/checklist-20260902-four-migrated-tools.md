# skill-writer checklist - compuse-toolbox (2026-09-02, four migrated tools)

Change: the Tools table gains four rows. `mdwrap` and `renamescope` now ship in this skill's
`scripts/`; `statusrot` and `factedit` ship in `meta-dream-tree` and are listed here the way
`wtclean`, `redcheck` and `claudemd_variance` already are - documented in this index, owned
elsewhere. No frontmatter change, so no routing keyword moved.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session)
- [x] Skill type: REFERENCE. The test approach is therefore RETRIEVAL - can a reader find the
      right tool from the row alone - not a pressure scenario.
- [x] Contamination checked before trusting the RED:
      `redcheck.py --scenario ... --corpus-cascade <repo>` read 1,008 documents and reported
      clean. Recorded as WEAK evidence per its own output: clean means NOT CAUGHT, and it
      compares distinctive terms so it cannot see a paraphrase.
- [x] RED and GREEN were two arms identical but for the four rows, each dispatched to
      `bitranox:baseline-probe` (no Bash, Read or Write, so neither arm could find the answer on
      disk), pinned to `sonnet`.
- [x] RED: given the table WITHOUT the rows, the agent answered `NONE` to both questions and named
      why the nearest rows do not fit: "`anchor_edit` ... replaces/inserts text at an anchor; it
      does not wrap or re-flow text to a column width" and "No row maps a match location (line
      number) to its enclosing function/symbol".
- [x] GREEN: given the table WITH the rows, the same two questions returned `mdwrap` and
      `renamescope`, each quoting its row verbatim. The arms differ, so the rows are what does the
      work rather than the model's prior knowledge.
- [x] Both arms were asked for a `Skill gaps` section, and both lists are recorded here.
- [x] GREEN's gap list found a REAL DEFECT rather than confirming the change: it flagged that the
      row "documents `renamescope` as a *reporting* step" while "the table does not say it performs
      the rename itself", and that it had inferred the boundary. Running `renamescope.py --help`
      showed the row was worse than ambiguous - the invocation `--from old_name --to new_name` was
      FABRICATED. The real surface is `(--name NAME | --regex REGEX) [--intended FUNC] paths`, and
      the tool reports; it never renames. `mdwrap`'s invocation was fabricated the same way: the
      real one is `--file FILE --anchor ANCHOR`, dry-run unless `--apply`, not a positional path
      with a non-existent `--dry-run`.
- [x] Both rows corrected against `--help`, then both corrected examples EXECUTED against real
      fixtures rather than reviewed. `mdwrap --file TODO.md --anchor 'NEXT STEP:' --width 100`
      reported `would rewrite lines 3-3 (1 -> 2 lines, delta +1)` and wrote nothing; a second
      paragraph in the same file was untouched. `renamescope net.py --name mac --intended
      _apply_iface` listed the hit in `_other` as the finding and the two hits in `_apply_iface`
      as intended, and renamed nothing.
- [x] RED's gap list: it reported that several table cells arrive visibly truncated mid-word
      (`gate`, `srccount`, `anchor_edit`). DECLINED as an artifact of the excerpt, not the skill:
      the arms used a 12-row excerpt with each cell trimmed to 240 characters to keep two 60kB
      prompts out of the session, and the shipped table carries the full cells.
- [x] GREEN's remaining gaps, both CLOSED in the rows: the table was silent on what `mdwrap` does
      with an ambiguous or missing anchor (it refuses - now stated), and on whether the rename is
      a separate step (it is - now stated).
- [x] Arms diffed in BOTH directions. RED produced one thing GREEN did not: an explicit account of
      why the neighbouring rows do not fit. Not a lost result - it is the shape of a NONE answer,
      and GREEN had a row to quote instead.
- [x] No frontmatter change: `git diff` over both SKILL.md files shows no `description:` line, and
      `build_skill_triggers.py --check` reports the map in sync (82 skills), so no trigger moved.
- [x] Every value added is a reserved documentation value or a fixture path - the rows use
      `TODO.md`, `src/net.py`, `_apply_iface`.
- [x] Scripts ship with tests that pass: `tests/test_mdwrap.py` and `tests/test_renamescope.py`
      moved with the tools, 62 cases green in their new home, and the full gate run is green at
      4,583 tests.
- [x] Present tense, no session narrative: this artifact records the claim tested, how, and the
      outcome.
