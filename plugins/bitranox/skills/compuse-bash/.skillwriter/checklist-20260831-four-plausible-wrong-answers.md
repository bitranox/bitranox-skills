# skill-writer checklist - compuse-bash (2026-08-31, four plausible-wrong-answer traps)

Change: four Quick-reference rows, each a shell construct whose failure is a PLAUSIBLE WRONG ANSWER
rather than an error. (1) `${VAR:-default}` fires on unset OR EMPTY, so an allowlist that blanks an
unlisted name selects the default and fails OPEN. (2) The chained
`command -v X >/dev/null && X ... || echo "(not installed)"` still misreports, because `||` catches
X's FINDING exit as well as its absence. (3) A path beginning with `-` is parsed as OPTIONS by
cat/tar/stat/ls/grep/dirname, and `--` does not help inside a `for` loop. (4) Files that were MOVED
are found by ctime (`-newerct`), never mtime.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED route: COVERAGE CHECK AGAINST THE FILE, not a behavioural baseline. All four lessons are
      already in this machine's always-loaded memory index (`a-blanked-variable-and-an-absent-one-
      both-select-the-default`, `feedback-never-attach-a-diagnosis-to-a-bare-...`, the leading-dash
      note inside `python-over-adhoc-shell`), so a dispatched agent here inherits them and cannot
      fail honestly - the contamination case this skill names. Pre-change `grep` over SKILL.md for
      `:-`, `command -v`, `newerct` and a leading-dash rule returns nothing: the rows were absent.
- [x] Evidence each row carries is measured, not reasoned:
      - the chained guard printed `(diff not installed)` directly after `diff` printed a real diff,
        and printed the identical sentence when the tool was genuinely absent;
      - `-newermt` returned 0 files for 27 notes archived that same day;
      - the leading-dash trap hit three times in one session, every time from globbing a directory
        whose entries begin with a dash.
- [x] GREEN: each row states the trigger, the mechanism, and the safe form. The `${VAR:-}` row also
      carries the matching TEST trap, because an assertion on absence is green before the fix,
      after it, and after a regression.
- [x] Scope: general POSIX shell semantics; nothing machine- or project-specific.
- [x] Security scan: prose only. No hosts, addresses, credentials or private paths.
- [x] CSO description: unchanged. "interpreting their exit codes and output" and "its result looks
      ambiguous" already cover retrieval for all four; no new trigger needed.
- [x] Table integrity: every row parses as exactly two cells with pipes inside code spans escaped -
      an unescaped `|` splits the cell and GFM drops the surplus silently.
- [x] Token budget: four rows on an existing table; the skill stays a compact reference card.
