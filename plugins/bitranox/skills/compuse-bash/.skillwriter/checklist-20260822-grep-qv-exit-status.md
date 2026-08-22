# skill-writer checklist - compuse-bash (grep -qv returns the wrong exit status)

Change: one Quick reference row. In Claude Code's bash, `grep` is a shell function whose exit
status is wrong when `-q` and `-v` are combined, which silently inverts the terminal test of a
wait loop.

## PLAN

- [x] Skill type: reference (a table of shell traps and the rule for each). Test approach:
      measurement of the claim itself, then a text check that the artifact states it.
- [x] Checked against EVERY shipped skill, not the nominated target: `grep -rn` for `-qv` and
      "shell function" across `skills/` returns only `coding-bash-reference`'s generic prose about
      shell functions. The exit-status trap is stated nowhere. compuse-bash owns exit codes and
      pipelines, so it is the correct home.
- [x] Scope: one row. No new section; the table is where this skill's traps live.

## RED

- [x] Behavioural RED is NOT available on this machine: the lesson is already in the always-loaded
      memory store at
      `.claude-memory/facts/reference-claude-code-s-grep-function-returns-the-wrong-exit-status-for-q-with-v.md`,
      so a dispatched agent answers from there rather than from the scenario. Route taken, per
      meta-skill-writer: the behavioural arm is replaced by a TEXT CHECK of the artifact.
- [x] `redcheck.py --corpus-cascade .` over 775 assembled documents also flagged the first draft
      scenario for ANSWER LEAK (50% of the answer's terms appeared in the scenario: bash, claude,
      code, exit, grep, qv, status, wrong), which is a second reason that arm could not have
      failed honestly.
- [x] The CLAIM itself was measured rather than taken from the queue entry, with controls:

      file with one non-matching line   shell-func `grep -qv` -> rc=1   `/usr/bin/grep` -> rc=0
      all lines match (control)         both -> rc=1 (they agree)
      `-q` alone / `-v` alone (control) both correct

      So the defect is exactly the `-qv` combination, and the controls rule out "the function is
      broken generally".

## GREEN

- [x] Text check: the row states the environment (`grep` is a shell function here), the exact
      inverted verdict with both sides measured, that `-q` and `-v` alone are correct, and the
      remedy (`/usr/bin/grep` when the status decides anything).
- [x] Quote-back for "what breaks in practice": "It silently inverts a wait-loop's terminal test:
      `until ! grep -qv DONE status.txt` fires on the first poll and the loop treats an unfinished
      job as complete."

## REFACTOR

- [x] Row placed with the other `grep` rows (after the `grep -E` alternation row), so a reader
      scanning for grep traps meets all of them together.
- [x] Scoped to this environment rather than stated as a universal grep fact, which would be
      false: `/usr/bin/grep` is correct and the row says so.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] Frontmatter untouched; no new keywords needed (the description already covers exit codes).

## Deliverables

- [x] One Quick reference row in `SKILL.md`. No script, so no `tests/` change.
