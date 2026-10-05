# skill-writer checklist - compuse-toolbox (2026-10-05, the 0/1/2 exit-code standard and two new jigs)

The tool table states the exit codes the jigs now have (0 yes, 1 no, 2 could not run, with the
`{ok, command, data, skipped}` envelope on every `--json` exit), a paragraph near the top states
that standard once, the `gate` row says gates run without a shell and how to write `cd`/`VAR=`,
the `fleet_ssh` row and note describe accept-new plus one retry, and two rows are new:
`plan_codecheck` and `instrument_share`.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed text, answered only from a copy of the document, with a verbatim quote or NONE.
- [x] Scope: the tool table, the new standard paragraph, the `fleet_ssh`, `adjudicate`,
      `redcheck` and `jsonl_grep` notes; frontmatter unchanged.
- [x] Inherited-context route: the arms read a staged copy of the old and new document and were
      told not to invoke a skill, so the answer is a text check of the document, not of the
      installed skill.

## RED (pre-change document, haiku)
- [x] Q1 adjudicate, both sides fired: "exit 1", quoting the old row (now wrong).
- [x] Q2 jsonl_grep, read but no match: NONE.
- [x] Q3 gate, `cd sub && pytest`: NONE.
- [x] Q4 ci_wait and a scheduled run on the same sha: "yes, it waits" (now wrong).
- [x] Q5 `ok` on exit 1: NONE.
- [x] Q6 / Q7 a tool to prove a plan's code, a tool for time spent on instrumentation: NONE; the
      one-question arms in the user's words answered NONE and guard_replay (wrong tool).
- [x] Q8 fleet_ssh after a host-key change: "it never re-runs the command", quoting the old note.
- [x] Q9 redcheck with an empty corpus: "exit 3" (now wrong).
- [x] Skill gaps asked for: RED listed Q3, Q5, Q6 and Q7 as unaddressed.

## GREEN (new document, same model and questions)
- [x] Q1 exit 2; Q2 exit 1; Q3 `--cwd DIR` / `--gate-cwd`; Q4 no, a scheduled run is excluded;
      Q5 `ok: true`; Q6 `plan_codecheck` with its command; Q7 `instrument_share` with its
      command; Q9 exit 2 - each with a verbatim quote of the new text.
- [x] One-question arms in the user's words picked `plan_codecheck` and `instrument_share`.
- [x] GREEN gaps worked: Q8 read "retried ONCE" as two runs, and one arm read "none placed" as
      "a block marked unplaced" (which is exit 1, not 2). Both rows were reworded ("ssh REFUSES a
      changed key before the command runs ... the command's first and only run"; "not one block
      naming a path").
- [x] REFACTOR quote-back on the reworded rows: one run, exit 1 for one unplaced block, exit 2 for
      none naming a path, the real tree never touched - each a direct quote.
- [x] GREEN diffed against RED in both directions: no answer the baseline had was lost; the RED
      answers that changed were the ones the code changed.

## Code the text describes
- [x] Every exit-code delta checked against the merged code before it was written: each jig's
      docstring exit paragraph read, `gate` probed (`--gate 'cd /tmp && true'` exits 2, `--cwd`
      and `bash -c` forms exit 0), the diffbehave module-at-a-rev recipe run end to end.
- [x] The envelope paragraph checked by running every jig that takes `--json` with a bad flag:
      each printed the envelope with `ok: false` and exited 2.
- [x] `plan_codecheck.py` and `instrument_share.py` ship with sibling tests; the pytest-probe
      test was mutation-checked (KILLED, `assert 1 == 2` without the probe).

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added; dates in examples are placeholders.
- [x] Frontmatter untouched: no routing keyword moved (the description is at 1009 characters, so
      the new jigs are reached through the table and the toolbox nudge, not the description).
- [x] Tables canonical (`reformat_tables.py --check` reports the file unchanged); every row has
      three cells and an even backtick count.
