# skill-writer checklist - coding-python-performance-review (2026-09-26, doc sync for the 7.25.4 script fixes)

compare_performance prints the branch, the stash sha and the recovery commands when the restore fails; profile_with_cache_template times 5 interleaved rounds per arm and rejects a gain inside the run-to-run spread. The compare_performance bullet and the cache-candidate step say so.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a question whose answer depends on the
      changed behaviour, answered ONLY from the pasted text, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q7 (restore failed: where are my changes, how do I get back?), Q8 (7% gain, 60% hits, overlapping runs: verdict, runs per arm) answered Q7 NONE; Q8 RECOMMEND with one run per arm (both wrong).
- [x] Skill gaps asked for: the missing exit codes and cases above were listed as guesses.

## GREEN
- [x] New passages pasted, same model and questions: Q7 run the printed commands, which name the branch and the stash sha; Q8 REJECT, 5 runs per arm - each with a direct quote.
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
