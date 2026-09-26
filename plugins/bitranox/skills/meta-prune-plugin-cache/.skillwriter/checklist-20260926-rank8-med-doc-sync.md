# skill-writer checklist - meta-prune-plugin-cache (2026-09-26, doc sync for the 7.25.4 script fixes)

pluginprune recognises a pin whatever names the home or config directory, never counts a symlinked sibling toward "sole", and prints a JSON envelope on every exit 2. The --json comment and the keep-rules paragraph say so.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a question whose answer depends on the
      changed behaviour, answered ONLY from the pasted text, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q6 (a pin spelled `"$HOME"/...`; the --json envelope on exit 2) answered NONE for both halves (the listed spellings did not include the quoted form).
- [x] Skill gaps asked for: the missing exit codes and cases above were listed as guesses.

## GREEN
- [x] New passages pasted, same model and questions: kept, and an envelope with ok false / data null / error, quoting "quoted or not" and "on every exit (on 2: ok false, data null, error)".
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
