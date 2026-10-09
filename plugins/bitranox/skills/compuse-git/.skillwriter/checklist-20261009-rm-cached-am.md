# checklist-20261009 - `git rm --cached` refusing an AM/MM file

## What the change is

A Quick reference row: `git rm --cached` refuses a file whose index version differs from both
HEAD and the working tree, and the `-f` it suggests drops that index version. Save it with
`git show :<file>` first.

## RED

- [x] Reproduced in a throwaway repo, git 2.53.0, `LC_ALL=C`, for both `AM` (new file staged then
      edited) and `MM` (tracked file staged then edited): exit 1,
      `error: the following file has staged content different from both the file and the HEAD`,
      `(use -f to force removal)`.
- [x] Without `LC_ALL=C` on a de_AT locale the message is German, so the row keys on the status
      code and the exit, not the text.
- [x] After `git rm -f --cached`, the working-tree copy survives and the staged content is
      reachable only as an unreachable blob in `git fsck --unreachable`.
- [x] Behavioural arms (sonnet, haiku) chose to save the staged blob before forcing. redcheck
      `--corpus-cascade` reports STRONG inherited coverage: the lesson is already in this
      machine's memory index, so the behavioural arm cannot fail honestly. Route taken: a text
      check of the skill file - the shipped text has no row covering the refusal.

## GREEN

- [x] Quote-back (haiku, the new file only, a German-locale variant of the scenario): it quoted
      the new row and answered `git show :<file> > <copy>` then `git rm -f --cached <file>`.

## REFACTOR

- [x] Gap closed: the row said the staged version is discarded "for good"; measured, it lingers
      as an unreachable blob until `git gc`, and the row now says so.
- [x] Declined: where to put the saved copy (the reader's choice); post-removal steps such as a
      `.gitignore` entry (covered by the build-artifacts section).

## Quality

- [x] Present tense; no session narrative, no scratch paths.
- [x] `name` and `description` unchanged; one table row added, no other line changed.
