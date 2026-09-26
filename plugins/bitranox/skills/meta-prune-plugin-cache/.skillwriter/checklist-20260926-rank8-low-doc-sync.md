# skill-writer checklist - meta-prune-plugin-cache (2026-09-26, doc sync for the LOW-batch script fixes)

pluginprune labels a plan-time refusal REFUSED and an attempted removal that failed FAILED, also
under `--apply`, and on Windows finds a pin whatever its letter case. The paragraph on what is
reported and the keep-rules paragraph say so.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a question whose answer depends on the
      changed behaviour, answered ONLY from the pasted text, with a direct quote or NONE.
- [x] Scope: the two passages that describe the changed behaviour; no frontmatter change.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q1 (the label of a plan-time refusal under `--apply`) answered NONE, the only label on offer
      being FAILED for "a directory that failed to delete"; Q2 (a pin spelled in another letter
      case on Windows) answered NONE.
- [x] Skill gaps asked for: both questions were listed as silent. The second gap it named, whether
      a pinned FILE keeps its version directory, is already answered by the keep-rules passage
      GREEN quoted, and GREEN raised no gap on it.

## GREEN
- [x] New passages pasted, same model and questions: Q1 answered REFUSED, quoting "a directory the
      plan refused, and so never attempted, is reported REFUSED"; Q2 answered kept, quoting "and on
      Windows in any letter case".
- [x] GREEN diffed against RED in both directions: nothing a baseline answered correctly was lost.
- [x] Skill gaps asked for again: none reported.
- [x] Every stated behaviour checked against the script it describes (`_run` and
      `pinning_settings`), and each script change is pinned by tests that failed on the previous
      source (`test_apply_labels_a_plan_time_refusal_refused_not_failed`,
      `test_a_windows_pin_in_another_letter_case_is_found`).

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved, description cap unaffected.
- [x] No table row changed.
