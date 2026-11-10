# skill-writer checklist - meta-dream-tree (cost side: a move to the tree top follows the mode)

Covers SKILL.md and references/dream-core.md.

- [x] Change: a move of a fact to the tree top follows the dream mode (propose and a manual run
      under `off` propose it with its cost, auto applies it and prints its cost; a re-home below
      the top is applied in every mode), in the misplacement bullet, the promotion branch, the
      rationalization row, dream-core's Mode, Boundaries, misplacement row and the paragraph after
      it. The firing check never rewrites a hook for its length; a long hook at a broad level is
      reported as a shortening proposal. Step 8 and the report contract carry verify's
      `pointer blocks` lines and name the slugs that arrived at the tree top.
- [x] Step 0b: `skill_decisions.py show meta-dream-tree --kind rejected,removed --full` lists one
      rejected entry (ref-map-after-dropped-move), unrelated; no live decision is reversed.
- [x] Contract tests (tests/test_dream_skill_contracts.py): two added, RED before the text edit
      (2 failed with "report contract lost the cost lines" and "propose mode lost its carve-out"),
      GREEN after (15 passed). The cost-lines test quotes the report contract's own clause: the
      bare words "pointer blocks" also occur in the walk-pruning note, so a bare-substring check
      passed against the unedited file.
- [x] Every mechanism claim checked against the code: verify prints the `pointer blocks` lines
      under the diff, top first, with arrived/left COUNTS (`_render_costs`); the slug lists are in
      `data.levels[]` under `--json` (`LevelCost.as_dict`); a level without a backup copy prints
      `?` and a `block bytes before not known` line, `null` under `--json` (`cost_report`); the
      350/500 caps are `HOOK_SOFT_MAX`/`HOOK_HARD_MAX` in hooks/uuid_store.py; dream-passes.md's
      removal policy says "Size pressure is met by representation".
- [x] RED (opus, pre-edit passages pasted): A (propose) and A2 (auto) re-home F to the tree top
      with no cost in the report; A3 (`off`, manual) leaves F in place on "PRIVATE memory only";
      C1/C2 (below the top) re-home to /t/team; B leaves a 430-character hook and reports
      "Nothing is required"; D "Yes. After the backup it is applied without a prompt"; E
      "Per-level bytes: NONE ... The report gives only counts".
- [x] GREEN (opus and haiku, edited passages pasted; 9 questions x 2 tiers): A "propose mode
      lists the move in the report with its cost ... and does not apply it"; A2 "auto mode
      applies it and prints its cost in the report"; A3 "a manual run under `off` proposes it";
      C1/C2 "A re-home to any level below the top is applied in every mode"; B "never rewrites a
      hook for exceeding the 350 SOFT cap" and "shortening proposal, never shortened unasked"; D
      "EXCEPT a move of a fact to the tree top (the anchor), which it PROPOSES"; E the verify lines
      as printed, the top's arrivals named, `?` never 0.
- [x] GREEN gap closed: both tiers reported that "`promote`: move it to the tree top" disagreed
      with the Mode carve-out. The promotion branch now reads "move it to the tree top as the mode
      says" and runs `promoted` "once it has moved". Re-probe (opus and haiku, 5 questions x 2
      tiers): P (propose) proposes G and does not run `promoted`; P2 (auto) moves G and runs it;
      opus "Do any two lines disagree? NONE", haiku "These do not conflict once the 'as the mode
      says' clause is read".
- [x] GREEN gap closed: both tiers could not compute a proposed move's cost. Mode now defines it
      as "the UTF-8 length of its pointer line plus the newline"; re-probe K gives 313 bytes for a
      312-character ASCII line on both tiers.
- [x] Gap declined (judgement the user has not ruled on): what applies an approved proposal and
      when. The decision fixes that a top move is listed for approval in propose mode and under
      `off`; the timing of an approved move is left unstated rather than invented.
- [x] Gaps declined (covered elsewhere in the skill): the move command
      (SKILL.md placement step, "`move --from-level A --to-level B --slug s`"); the sighting's path
      argument (promotion bullet, "`dream_state.py saw-promotable <slug> <ABSOLUTE path of the
      project the fact came from>`"); classifying before the verdict ("write the class down per
      fact BEFORE reading its `should-promote` verdict"); the misplacement row (dream-core.md,
      "a misplacement | re-home it, and record the sighting anyway; to the tree top as the mode
      says"); the excerpts' truncation and the two-row table are excerpt artifacts.
- [x] Gaps declined (owned outside this decision): whether `promoted` runs after a misplacement
      re-home to the top, and whether a pointer-block rewrite counts as a CLAUDE.md file to
      report, predate this edit and are sighting and Boundaries bookkeeping the decision does not
      touch; "broad level" stays a judgement, since the step only reports and changes no store.
- [x] GREEN diffed against RED both ways: every RED answer is still answered; nothing RED
      produced is missing (the sighting is still recorded, below-top re-homes still apply).
- [x] After each fix round: the width and fence check over the added lines prints nothing (a
      split `dream_state.py done` code span in the report-contract paragraph, older than this
      edit, is rejoined in the reflow); the paragraph after each insertion was read ("Queue
      offenders" now names the FIRING offenders so it cannot bind to the long-hook sentence).
- [x] Tables re-padded with reformat_tables.py (SKILL.md rationalization table,
      dream-core.md misplacement table).
- [x] Description unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      prints nothing); ASCII only; present tense; no private host, path or repo name added.
- [x] Mirror check: `repo-gate.py --mirrors` lists 12 pairs, none of them this skill.
- Decisions: d-20261110-d3af596b, d-20261110-cba0045b, d-20261110-10169b53, d-20261110-50088a4b
