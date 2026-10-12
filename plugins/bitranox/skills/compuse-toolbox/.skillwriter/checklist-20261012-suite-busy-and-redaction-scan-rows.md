# skill-writer checklist - compuse-toolbox (2026-10-12, suite_busy and redaction_scan rows)

Two rows are new in the tool table, `suite_busy` (after `procsig`) and `redaction_scan` (after
`pushcheck`), and two notes are new under "Why a jig over a one-liner". Frontmatter unchanged.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed text, answered only from a copy of the document, with a verbatim quote or NONE.
- [x] Scope: the two new rows and the two new notes; no existing row or note reworded.
- [x] Inherited-context route: the arms read a staged copy of the old and new document and were
      told not to invoke a skill or read anything else, so the answer is a text check of the
      document, not of the installed skill or the machine's memory.

## RED (pre-change document, haiku)
- [x] Q1 is a suite already running in this repo or any worktree: `procsig`, with "The doc never
      says procsig scopes a search to a repository or its git worktrees".
- [x] Q2 can the tool report the shell that ran it: partly, quoting procsig's sibling-shell note.
- [x] Q3 on macOS: exit 2, inferred from procsig's "no /proc".
- [x] Q4 do the commits since origin/main ADD a name from a `#`-commented, `name==>x` list:
      `pushcheck --denylist-file`, with "The doc does not give the denylist line format".
- [x] Q5 a name only in a removed line: not a hit (pushcheck's removal rule).
- [x] Q6 a flag that keeps the private names out of the output: NONE.
- [x] Q7 exit code for a list holding only comments: NONE.
- [x] Q8 (control) kill a stray process by command line without killing your shell: `procsig`.
- [x] Skill gaps asked for: RED listed Q1, Q4, Q6 and Q7 as unaddressed.

## GREEN (new document, same model and questions)
- [x] Q1 `suite_busy` with its command, quoting "examines the repo's main checkout AND every
      worktree"; Q3 exit 2, quoting "Linux only: without /proc it says so and exits 2"; Q4
      `redaction_scan --list names.txt --range origin/main..HEAD`; Q5 not a hit, quoting "ADDED
      lines only"; Q6 `--redact-hits`; Q7 exit 2, quoting "2 could not run: zero patterns" with the
      comment rule beside it; Q8 still `procsig`.
- [x] GREEN gap worked: Q2 was answered by inference ("the doc never says a shell running the
      check is not a suite", and whether a `bash -c` wrapper counts). The `suite_busy` row now
      says so ("neither it nor the shell that ran it is ever reported; a `bash -c '... pytest
      ...'` string is one token and never matches, while the suite that shell starts is its own
      process and is found").
- [x] Gaps declined, with reasons: what the macOS refusal prints (the exit code is the contract,
      the wording is the tool's `--help`); what `--range A..B` covers (git's range semantics, and
      the row already says it reads every commit); a line removed in one commit and re-added in
      another (each commit's added lines are read, which the row states).
- [x] REFACTOR quote-back on the reworded row: both questions answered with a direct quote of
      the new sentence.
- [x] GREEN diffed against RED in both directions: the control (Q8) is unchanged, and Q5 gives the
      same answer from the new row; the answers that changed are the ones the new rows exist for.

## Code the text describes
- [x] Every claim in the two rows is a behaviour of the shipped jig with a test behind it: real
      child processes in a temp repository with a linked and a nested worktree, a substring-only
      name, the self-and-shell exclusion through `bash -c ... pytest`, the `--wait-s` free and
      deadline paths; the `#` comment line, the `==>` rule, case-insensitivity, added-only lines,
      the liveness control, an empty list, `--redact-hits`.
- [x] A 14-arm mutation battery over both jigs was killed in full (no arm survived).

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added; list and repo names are placeholders.
- [x] Frontmatter untouched: no routing keyword moved (the description is at its cap's margin, so
      the new jigs are reached through the table and the toolbox nudge, not the description).
- [x] Tables canonical (`reformat_tables.py` leaves the file unchanged); every row has three cells
      and an even backtick count.
