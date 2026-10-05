# skill-writer checklist - sec-appsec-web-baseline (2026-10-05, --json envelope)

audit_headers.py --json prints the plugin-wide {ok, command, data, skipped} envelope on
every exit, exit 2 included; exit codes are unchanged. A one-label frame-ancestors
wildcard is a MINOR finding whose text states the public-suffix gap. The bundled-scripts
row describes the envelope.

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
      Q7 (stdout on an unfetchable URL, key of the findings) answered NONE for both.
- [x] Skill gaps asked for: the missing codes and causes above were listed as gaps.

## GREEN
- [x] New passages pasted, same model and questions: Q7: an envelope with ok false, data null and an error, findings under `data`, quoting
      "`--json` prints a `{ok, command, data, skipped}` envelope on every exit".
- [x] GREEN diffed against RED in both directions: every RED answer that was right stayed right
      (the exit-0 cases, compare_performance's exit 2); nothing a baseline answered was lost.
- [x] Skill gaps asked for again. Declined: the one-label wildcard grading is not restated in the skill text; the finding
      itself names the gap at the moment a reader meets it.
- [x] Every stated behaviour checked against the script it describes (its docstring, epilog or
      `main()`), and each script change is pinned by tests that failed on the previous source.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
