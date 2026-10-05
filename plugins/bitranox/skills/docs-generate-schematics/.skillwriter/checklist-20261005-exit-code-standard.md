# skill-writer checklist - docs-generate-schematics (2026-10-05, exit-code standard 0/1/2)

generate_schematic_ai.py now exits 2 when the quality question could not be answered (no
image, an unreviewed image, no API key, httpx2 missing, an unexpected error) and keeps 1 for
a best score below the threshold; a NEEDS_IMPROVEMENT verdict at or above the threshold is a
[WARN] on stderr. The wrapper passes the code through and exits 2 on its own failures. The
requirements bullet and the exit-status paragraph move with the code.

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
      Q1 (every generation fails) and Q2 (the only review fails) answered 1, quoting the old
      table; Q3 gave exit 0 but NONE for the stream; Q4 (wrapper, no key) NONE.
- [x] Skill gaps asked for: the missing codes and causes above were listed as gaps.

## GREEN
- [x] New passages pasted, same model and questions: Q1 and Q2 answered 2, quoting "2 the quality question could not be answered - no image at
      all, an image whose review failed with no earlier reviewed image to fall back on";
      Q3 stderr, quoting "that verdict is printed as a `[WARN]` on stderr"; Q4 2, quoting
      "exits 2 itself when the key is missing".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right
      (the exit-0 cases, compare_performance's exit 2); nothing a baseline answered was lost.
- [x] Skill gaps asked for again. Declined: "HTTP 429 is not named" - every generation failing IS no image at all, which the
      text names; listing HTTP statuses would date the paragraph.
- [x] Every stated behaviour checked against the script it describes (its docstring, epilog or
      `main()`), and each script change is pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
