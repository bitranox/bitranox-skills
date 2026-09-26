# skill-writer checklist - compuse-toolbox (2026-09-26, doc sync for the 7.25.4 script fixes)

Four behaviour changes reached this SKILL.md: conflict_scan skips a dangling or looping symlink; ci_triage `--step` matches the gh step-name column in every job; ci_triage, transfer and diffbehave are launched with plain python3 (they declare `LAUNCH_WITH = "python3"`); grep_all judges "ignored" from the search root and reports UNKNOWN for a repo git refuses to read. The conflict_scan, ci_triage, transfer and diffbehave rows, the gate launch bullet and the grep_all bullet say so.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a question whose answer depends on the
      changed behaviour, answered ONLY from the pasted text, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q3 (dangling symlink exit code), Q4 (`--step` by gh step name, matrix job), Q9 (uv run or python3 for ci_triage --cmd and diffbehave), Q10 (a match in an outer-ignored linked worktree; dubious ownership) answered Q3 exit 2 (wrong, quoting "2 a path or directory could not be read"); Q4 NONE; Q9 `uv run` for both (wrong, quoting "only this one runs other commands"); Q10 a guess the text did not decide.
- [x] Skill gaps asked for: the missing exit codes and cases above were listed as guesses.

## GREEN
- [x] New passages pasted, same model and questions: Q3 exit 0; Q4 yes to both; Q9 plain python3 for both; Q10 counted as missed, and UNKNOWN with exit 2 - each with a direct quote of the new text.
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
