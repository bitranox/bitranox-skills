# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-10-02, error surface)

One gap: the workflow declared done on "0 violations + gate green". When the refactor moves
WHERE input is validated into a boundary model, the observable error surface changes (exception
type and, through a CLI wrapper, exit code; message wording and redaction; multi-fault order)
while every test stays green, because the tests assert on the new path.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: discipline step in a process skill. Scope: one STEP C item plus its DoD line,
      DO NOT STOP condition, execution-summary line and one rationalization row.

## RED
- [x] Behavioural RED not used: `redcheck --corpus-cascade` on a de-telegraphed scenario returned
      verdict `inherited` (STRONG) - the lesson is already in this machine's memory store, so a
      dispatched agent would answer from there. Route taken: coverage check of the skill file.
- [x] Coverage RED with a positive control: control `SerializeAsAny` 3 hits; `exit code` 0,
      `error surface` 0, `exception type` 0, `single-fault` 0, `redact` 0, `CHANGELOG` 0.

## GREEN
- [x] Same instrument after the edit: control 3; `exit code` 6, `error surface` 2,
      `exception type` 5, `single-fault` 2, `redact` 3, `CHANGELOG` 3.
- [x] Quote-back through an inert probe (no file or shell tools), each answer a direct quote or
      NONE: done-or-not (DO NOT STOP list), ValidationError vs ValueError/exit 22 (the keep-it
      sentence), getting HEAD's source (`git archive HEAD src`), trusting an all-identical diff
      (the must-differ input), multi-fault order (document, do not fight) - all quoted.

## REFACTOR
- [x] Skill gaps from the first quote-back, all closed in the text: the negative case (a
      refactor that leaves every refusal where it was does not need the item); what counts as
      "moved" (a model check added in front of one that still exists counts); what a CHANGELOG
      entry must hold (the input, the old result, the new one).
- [x] Gap found while editing, closed: `error.errors()[i]["msg"]` carries pydantic's
      `Value error, ` prefix, which must be stripped to reproduce the old text.
- [x] Re-test of only the touched questions by quote-back: rename-only (does not apply),
      model added in front of a kept check (applies), CHANGELOG content, the `Value error, `
      prefix - all quoted.
- [x] Skill gaps from the re-test: a refusal with several errors (closed: one line per entry);
      "does it apply" answered from descriptive sentences rather than a yes/no rule (declined: the
      trigger sentence and the exclusion were both quoted correctly); what counts as the
      validator's own text (declined: the instruction names its source, `error.errors()`).
- [x] Diff against RED in both directions: two existing lines are extended (the STEP C exit
      gate now also requires the error-surface diff; the TEST summary line names it), everything
      else is added; no existing step, row or rule was removed (checked with `git diff -U0`).

## Quality
- [x] Present tense; no session narrative, no scratch paths, no project or host names.
- [x] No machine values (grep for addresses, /home/, /tmp/ returns nothing).
- [x] Frontmatter untouched, so the trigger map needs no rebuild.
- [x] Tables reformatted with docs-md-table-formatting; every row keeps two columns.
- [x] Version bumped MINOR (new required step): plugin.json and pyproject.toml 7.33.0.
