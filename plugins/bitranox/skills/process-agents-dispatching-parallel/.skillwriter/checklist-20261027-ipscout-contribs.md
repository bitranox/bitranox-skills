# skill-writer checklist - process-agents-dispatching-parallel (2026-10-27, ipscout-contribs)

- [x] Change: Verification step 7 (grep each fixer's diff for what its brief forbade) gains the
      untracked-file case. `git diff` does not show UNTRACKED files, and a fixer's new test files
      are where suppressions land, so grep them too with the same alternatives and no `^\+`
      prefix: `git ls-files -z --others --exclude-standard | xargs -0 -r grep -nHE
      'monkeypatch|patch\(|type: ignore|pyright: ignore|noqa'` (one line in the skill). A staged
      new file already shows in `git diff <base>`. `git add -N <path>` is the alternative, which
      writes the index until `git reset -- <path>` undoes it. Measured example: a suppression grep
      over `git diff -U0` missed four pyright ignores, all in new test files.
- [x] Item still open: the pre-change step 7 gives only the `git diff <base> | grep` form; no text
      on untracked files, `ls-files --others` or `git add -N` anywhere in the SKILL.md.
- [x] Claims verified in a scratch repo: with one tracked edit and one untracked
      `tests/test_new.py` holding `# pyright: ignore`, `git diff <base> | grep` and
      `git diff -U0 <base> | grep` print only the tracked line; the documented `ls-files | xargs`
      command, extracted from the edited SKILL.md and run as written, prints
      `tests/test_new.py:1:...pyright: ignore`; with no untracked files it prints nothing and
      exits 0 (`-r` skips grep); after `git add -N` the file's line appears in `git diff <base>`;
      `git reset -- <path>` returns it to untracked; a staged (`git add`) new file appears in
      `git diff <base>`.
- [x] Receipt held (skill_receipt.py start meta-skill-writer); this agent loaded the skill.
- [x] RED route: a text check of the artifact. The installed plugin carries the pre-change text,
      so a no-skill behavioural arm would measure the old version. redcheck --corpus-cascade
      reported a term overlap with the always-loaded memory index; the named lines were read and
      none states the untracked-file claim. Text check: `UNTRACKED`, `ls-files -z --others`,
      `git add -N`, `staged new file` count 0 in the pre-change file and 1 in the new one.
      Quote-back on the pre-change passage: NONE on both questions, both tiers.
- [x] GREEN quote-back, opus (effort medium) and haiku, two questions (does the `git diff` grep
      miss an unstaged new file, and what command catches it; what makes `git diff` itself list
      it). Both tiers quoted the new text and answered NONE for the old. 2 tiers x 2 questions x
      2 arms (old/new).
- [x] Gaps closed after GREEN: the `<same pattern>` placeholder (now the literal pattern);
      which form to prefer and that `git add -N` changes the index (now stated, with the undo);
      "uncommitted" versus "untracked" scope (now "untracked", plus the staged-file sentence);
      a command split across two lines (now one line, so it copies as one command).
- [x] Re-probe on the final text, haiku, two questions on the touched sentences (does the
      `git diff` grep see a staged new file; the exact command and how to undo `git add -N`).
      Both answered with quotes of the final text; no new undecided gap.
- [x] Gaps declined: files under a gitignored path (`--exclude-standard` skips them, and a fixer's
      file there is not part of the change it commits); `-U0` in the measured sentence beside
      `<base>` in the example (same command family, no different action); where `<base>` comes from
      and which directory to run in (stated by the surrounding steps, outside the probed excerpt).
- [x] Quotes checked with quotecheck against the SKILL.md: the final-text quotes OK, a planted
      false quote MISMATCH (rc 1), so the check can fail.
- [x] GREEN diffed against RED both ways: the `git diff` grep, the REQUIRED-marker check, the
      trailer grep and the strip-only-added-lines rule are unchanged; nothing removed.
- [x] Frontmatter description unchanged; no trigger map rebuild needed.
- [x] ASCII only (no non-ASCII byte in SKILL.md); no addresses, hostnames, user names or home
      paths added; no version-history wording in the added text; the file has no tables.
- [x] Repo hook tests that read skills pass (`-k "skill or description or trigger or tell"`:
      948 passed). The skill has no tests/ dir.
