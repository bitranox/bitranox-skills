# skill-writer checklist - process-plan-writing-plans (2026-11-08, task ids and Self-Review 8-11)

A note after the Task Structure template: task ids start with a digit, a milestone label goes in
the name. Self-Review gains item 8 (each task imports, collects and lints on its own; a `tests/`
helper is made importable in the task that creates it), item 9 (extract and run the plan's code,
run a prescribed mutation battery against it, a substring assertion must fail with the guarded
code deleted), item 10 (platform claims agree with the CI OS matrix; HOME isolation also sets
USERPROFILE) and item 11 (DETAILED code against the MID plan's behavioural sentences).

Decisions: d-20261108-c598a63f, d-20261108-0b306991

- [x] Step 0b: one live rejected entry (d-20261108-0c4e895e, no numbers in item 7); this change
      does not touch it.
- [x] RED by text check, pre-edit text: `grep -ciE` printed 0 for each of USERPROFILE,
      "OS matrix|windows", "import-mode|unused import|F401", "mutation|mutant", "extract", "dig.t";
      "MID|DETAILED" hit only the three-altitude section's "Check each lower plan against the one
      above it" (no line-by-line code check). A behavioural RED was not used: the probe machine's
      always-loaded memory index already teaches the HOME/USERPROFILE and mutation-arm lessons.
- [x] Mechanism claims checked against code before probing: `task_brief.py` on a plan headed
      `### Task M2.1:` exits 1 with "the plan has no 'Task <id>' headings at all", and on
      `### Task 2.1: M2 parser` writes the brief (rc 0); `ntpath.expanduser` reads `USERPROFILE`
      first; `mutation_arm.py --help` lists `--battery SPEC.json`.
- [x] GREEN, the note and items 8-11 pasted, opus and haiku. Seeded plan: M-prefixed ids, a
      Task 1 import block for later modules with "keep the unused imports", a `tests/` helper
      under `--import-mode=importlib` without a conftest, "Linux only" against a three-OS matrix,
      HOME-only isolation, an unrun mutation battery, a flag-name substring assertion, `continue`
      where the MID text says drop the rest; a control task with an exact-equality assertion.
      Both tiers found every seeded defect and quoted the deciding item; haiku called the control
      clean, opus flagged it only for the shared undefined fixture. 2 tiers, 2 cells.
- [x] Gaps declined: a task without complete code (covered: "No Placeholders" and Remember
      "Complete code in every step", SKILL.md); a conftest missing from the Files line (covered:
      the Files block and the STOP condition "the change turns out to need a file that is not
      listed in **Files:**"); a HOME setenv that serves no purpose, genuinely one-OS code, a MID
      sentence that does not settle a case, an undefined fixture (judgement for the reviewer;
      item 8's "collects" and item 10's "skips with a stated reason" already decide the fixture
      and the one-OS test); file encoding (out of scope, owned by the language skills).
- [x] Width and fence check over the added lines: the four Self-Review items are one long line
      each like items 1-7 (file style); the task-id note is wrapped under 100 columns; no fence
      touched. The paragraph after each insertion ("## No Placeholders", "If you find issues, fix
      them inline") keeps its meaning. ASCII only.
