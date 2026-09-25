# skill-writer checklist - meta-skill-writer (2026-09-25, run-python.sh --hook registration)

Change: "Bundled scripts and hooks: keep them cross-platform". Where it says to reuse
`hooks/run-python.sh`, it now states the shim is strict by default (exit 3 when it cannot run the
script: missing file, no Python 3, an unexpected shell) and gives the registration form with
`--hook` as the first shim argument. The "never wedge a turn" item says that exit-0 contract holds
through the shim only with `--hook`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference section inside a technique skill. Test approach: quote-back retrieval
      arm (quote or NONE, haiku, inert `bitranox:baseline-probe`, section pasted). Moved: Q1 (the
      exact hooks.json command string), Q2 (exit code for a CLI caller given a missing script), Q3
      (exit code for the hook). Control: Q4 (line endings of a shipped `.sh`).
- [x] Scope: two list items in one section; frontmatter, `name:` and description untouched.

## RED

- [x] Inherited coverage: `redcheck --corpus-cascade` on the worktree reported STRONG on
      launcher, produce, registration, run-python from CLAUDE.local.md indexes. No index line and no
      cascade CLAUDE.md names `--hook` for the shim. Route taken: the quote-back text check.
- [x] RED, pre-change text: Q1 NONE, Q2 NONE, Q3 0 quoting "Every failure path exits 0" (which a
      registration without `--hook` does not get). Control Q4 LF with its quote. Skill gaps: no
      registration syntax, non-hook exit code unaddressed.

## GREEN

- [x] Q1 the `--hook` form, quoted; Q2 3, quoted; Q3 0, quoting the `--hook` sentence. Skill gaps:
      none reported.
- [x] Diffed against RED in both directions: Q4 unchanged with the same quote; nothing lost.

## REFACTOR

- [x] The first GREEN text quoted the full registration command. The catalogue test
      `test_no_skill_md_sends_a_cli_through_the_fail_open_launcher` (meta-skill-audit) refuses any
      SKILL.md line that launches through `run-python.sh --hook`, because a skill step copied from
      it would read a mistyped path as a clean run. The sentence now states the argument order
      (`--hook` first, before the script path), points at `hooks/hooks.json` for the exact form, and
      says a skill step never passes `--hook`.
- [x] Re-tested the touched questions by quote-back (haiku, inert probe): where `--hook` goes and
      where the form comes from, whether a skill step passes it (no), and the exit code without it
      (3) - each answered with a direct quote of the new sentence; no skill gaps reported.

## Quality

- [x] Every claim executed against the shim with a control: missing script exits 3 without
      `--hook` and 0 with it; no Python 3 on PATH exits 3 without and 0 with; a `uname -s` that
      reports an unexpected shell exits 3 without and 0 with; a script that runs exits 0 both ways. The quoted registration matches `hooks/hooks.json`: all 54 shim
      registrations pass `--hook` as the first shim argument.
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Security: prose only.
