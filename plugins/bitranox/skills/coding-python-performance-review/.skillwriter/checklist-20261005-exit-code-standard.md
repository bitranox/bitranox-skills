# skill-writer checklist - coding-python-performance-review (2026-10-05, exit-code standard 0/1/2)

profile_with_cache_template.py ABORTs with exit 2 before any suite run when pytest is
missing or MODULE_NAME / FUNCTION_NAME do not import; compare_performance.py exits 2 when
git is missing. The ABORT step and the compare_performance bullet name the new causes.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed exit codes, answered ONLY from the pasted passages, with a direct quote or NONE.
- [x] Scope: the passages that state the changed behaviour; no frontmatter change.
- [x] Inherited coverage: not a behavioural arm. The questions ask for the CURRENT exit codes,
      which only the pasted text can supply, so a probe answering from inherited context would
      quote text absent from the passages - none did.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q8 (a MODULE_NAME that does not import) answered NONE; Q9 (git missing) answered 2 by
      inferring "a git step failed".
- [x] Skill gaps asked for: the missing codes and causes above were listed as gaps.

## GREEN
- [x] New passages pasted, same model and questions: Q8: 2, quoting "`MODULE_NAME` / `FUNCTION_NAME` do not import. The ABORT line names
      which"; Q9: 2, quoting "git is missing".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right
      (the exit-0 cases, compare_performance's exit 2); nothing a baseline answered was lost.
- [x] Skill gaps asked for again. None reported for this skill's passages.
- [x] Every stated behaviour checked against the script it describes (its docstring, epilog or
      `main()`), and each script change is pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
