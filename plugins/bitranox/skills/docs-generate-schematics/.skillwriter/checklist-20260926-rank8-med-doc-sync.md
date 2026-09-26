# skill-writer checklist - docs-generate-schematics (2026-09-26, doc sync for the 7.25.4 script fixes)

generate_schematic_ai.py exits 1 when the best image kept is below the `--doc-type` threshold (the image is still written), and scores a review by its total. The skill stated no exit status at all; a paragraph now gives 0 / 1 / 2 and the scoring rule.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a question whose answer depends on the
      changed behaviour, answered ONLY from the pasted text, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q5 (iteration cap hit, best 7.0 against 8.5: is the image written, what exit code?) answered NONE.
- [x] Skill gaps asked for: the missing exit codes and cases above were listed as guesses.

## GREEN
- [x] New passages pasted, same model and questions: written, exit 1, quoting "a best image still below the threshold - the image is written in those last two cases".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right;
      nothing a baseline answered was lost.
- [x] Skill gaps asked for again. Declined, with reasons: per-job output format of ci_triage is
      `--help` detail, not skill text; the `REPEATS` default is stated in the template's own
      paragraph (the probe attributed it to the wrong script); a quoted pin placement and an
      ancestor-folder GPL are covered by "quoted or not" and "each folder above it ... one copyleft
      id rejects".
- [x] Every stated behaviour checked against the script it describes (its docstring, epilog or
      `main()`), and each script change is pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] Tables re-padded by the formatter where a row changed.
