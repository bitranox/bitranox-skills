# skill-writer checklist - sec-appsec-web-baseline (2026-09-26, doc sync for the 7.25.4 script fixes)

audit_headers.py now exits 2 when the URL cannot be fetched at all; the table said only "exits non-zero if not clean", and the proxy paragraph told readers NOT to gate on the exit code. The bundled-scripts row names 0 / 1 / 2, and the proxy paragraph gates proxy health on exit 2 plus a written output file.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - a question whose answer depends on the
      changed behaviour, answered ONLY from the pasted text, with a direct quote or NONE.
- [x] Scope: the passages that describe the changed behaviour; no frontmatter change.

## RED
- [x] Old passages pasted, pinned to haiku, inert probe type, told not to use the Skill tool:
      Q1 (a dead proxy: exit code, and can it tell dead from insecure?) answered NONE for the code; it quoted "Gate proxy-health on a written output file, NOT the scanner's exit code".
- [x] Skill gaps asked for: the missing exit codes and cases above were listed as guesses.

## GREEN
- [x] New passages pasted, same model and questions: exit 2, quoting "Gate proxy-health on exit 2 (the page could not be fetched - a dead proxy or an unreachable site, nothing measured)".
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
