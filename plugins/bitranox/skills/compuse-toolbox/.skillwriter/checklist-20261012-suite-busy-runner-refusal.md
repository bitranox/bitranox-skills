# skill-writer checklist - compuse-toolbox (2026-10-12, suite_busy refusal on a CI runner)

One sentence of the `suite_busy` row changes. It said "It reports how many processes and
checkouts it examined, and zero is a refusal", which the jig no longer does: zero EXAMINED is now
a valid FREE answer when every readable process is the jig's own chain (a hosted CI runner), and
the refusal fires only when not one cwd could be read. The row now names `processes_excluded`, the
`skipped` count, and both exit codes. No other row or note changes; frontmatter unchanged.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed sentence, answered only from a copy of the row and the `suite_busy` note, with a
      verbatim quote or NONE.
- [x] Scope: one sentence in one table cell.
- [x] Inherited-context route: `redcheck --corpus-cascade` over the skill directory reported
      `clean` (1503 documents; WEAK evidence, a clean result means not caught). Both arms ran on the
      inert `bitranox:baseline-probe` type with the document pasted into the prompt, so the answer
      is a text check of the supplied row, not of the installed skill or the machine's memory.

## RED (pre-change row, haiku)
- [x] Q1 hosted runner, every readable process is the jig's own chain, nothing running: exit 2,
      quoting "It reports how many processes and checkouts it examined, and zero is a refusal."
      This is the wrong answer the jig itself gave on CI.
- [x] Q2 /proc present, not one cwd readable, the jig's own included: exit 2, by inference from
      the same sentence plus "2 could not answer".
- [x] Q3 (control) macOS: exit 2, quoting "Linux only: without /proc it says so and exits 2".
- [x] Q4 which count is the jig's own chain set aside: NONE.
- [x] Skill gaps asked for: RED reported that the text is silent on whether an unreadable cwd
      counts as examined, whether the excluded chain counts, and which exit a refusal takes.

## GREEN (new row, same model and questions)
- [x] Q1 FREE, exit 0, quoting "on a CI runner whose only readable processes are its own chain,
      the answer is FREE (exit 0), not a refusal."
- [x] Q2 exit 2, now quoting "It refuses (exit 2) only when not one cwd could be read, its own
      chain included" instead of inferring it.
- [x] Q3 exit 2, same quote as RED.
- [x] Q4 `processes_excluded`, quoting "how many of its own chain it set aside
      (`processes_excluded`)".
- [x] RED's three gaps are closed by the new sentence: unreadable processes are "counted in
      `skipped`", the excluded chain has its own count, and the refusal's exit code is stated.
- [x] Gaps GREEN reported, declined with reasons: the JSON envelope's key layout (the `--json`
      output and the tool's `--help` carry it, and the table row stays a pointer, not a schema);
      a readable process outside every checkout (the row already says a process is attributed to
      the checkout holding its cwd, and that wording did not change); whether an unreadable
      ancestor lands in `skipped` (it does not; a set-aside process cannot be the missed suite, and
      the refusal rule reads the same either way, so the row leaves it to the docstring); the exit
      code for a mixed readable/unreadable table (the command cell's 0/1/2 already decides it).
- [x] GREEN diffed against RED in both directions: the control (Q3) is unchanged, Q2 keeps its
      answer with a direct quote where it had an inference, and the answers that changed (Q1,
      Q4) are the ones the edit exists for. No RED result is missing from GREEN.

## Code the text describes
- [x] Every claim in the new sentence is a behaviour of the shipped jig with a test behind it: a
      fake /proc in the runner shape answers FREE with `processes_excluded` 4 and one unreadable
      process in `skipped`; a fake /proc where no cwd at all is readable, the jig's chain
      included, refuses with exit 2.
- [x] A six-arm mutation battery over the new counting was killed in full, including the arm
      that restores the old zero-examined basis.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added.
- [x] Frontmatter untouched: no routing keyword moved.
- [x] Tables canonical (`reformat_tables.py` leaves the file unchanged); the row keeps three cells
      and an even backtick count.
