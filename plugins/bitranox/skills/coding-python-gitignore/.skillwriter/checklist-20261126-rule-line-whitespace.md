# skill-writer checklist - coding-python-gitignore (2026-11-26, rule-line whitespace, issue 53)

igittigitt 2.4.3 reads a rule line exactly as git does: only the final run of unescaped spaces is
cut, leading whitespace stays, only a `#` in column 1 starts a comment, a lone trailing backslash
matches nothing, and a rule file ends a line only at `\n` (one `\r` before it dropped). The skill
is regenerated from the twin in `libs/igittigitt/skills/python-gitignore/` with the conventional
divergences (name field, self-install blockquote) re-applied. Changed sections: a new "Spaces,
backslashes and comments in a rule line" section in Library usage, and the release-history lines
removed from the glob section and the performance defaults.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Ledger read (`skill_decisions.py show`): no entries before this change.
- [x] Skill type: reference. Test: retrieval questions answered with a direct quote or NONE, plus a
      `Skill gaps` section: which name an escaped-space line matches, the four-backslash line,
      a trailing tab, an indented `*.log`, an indented `#`, whether to `.strip()` lines read by
      hand, whether `add_rule` applies the same processing as the file parser, CRLF files, a lone
      trailing backslash, `parse_rule_files` line endings, `parse_rule_file` default `base_dir`.
- [x] Scope: the sections listed above. Frontmatter unchanged.

## Ground truth (igittigitt 2.4.3 and git 2.53)
- [x] Every rule in the example block executed one at a time against igittigitt; each comment's
      claim holds, and `  # note`, `  *.log` agree with `git check-ignore`.
- [x] git-oracle scenarios `backslash_and_trailing_spaces`, `leading_whitespace` and
      `carriage_returns` in `tests/test_git_compat.py` agree with git, plain and `-v`.
- [x] A `\r` or a byte order mark passed to `add_rule` stays in the pattern (measured).
- [x] `parse_rule_file`'s `base_dir` defaults to the rule file's directory (code read).

## RED
- [x] haiku and opus `baseline-probe`, given the pre-change Library usage section: NONE for every
      rule-line question; answers were guesses (both assumed lines may be stripped).

## GREEN
- [x] haiku and opus, given the new section: all eight questions answered with a direct quote, all
      correct.
- [x] A second round on the final text (six questions incl. lone backslash, `parse_rule_files`,
      `base_dir`): both tiers quoted the governing line and answered correctly.
- [x] GREEN skill gaps: "it drops" bound grammatically to `parse_rule_file` only (CLOSED: "both
      end a line only at `\n`"); "remove a `\n` or `\r`" read as either-or (CLOSED: "the whole line
      ending ... (`\r\n` or `\n`)"); a BOM on the first line of a hand-read file (CLOSED: named
      beside the line ending); `base_path` vs `base_dir` (DECLINED: both are the real parameter
      names, shown in the method list); raw vs plain string literals in the example (DECLINED:
      each comment states the characters the rule holds); a tab inside the trailing run, and
      what happens on Windows (DECLINED: covered by "Tabs are never cut" and "final run of
      UNESCAPED spaces"; Windows cannot hold these names, which the text says).
- [x] RED against GREEN, both directions: no RED answer is lost; every GREEN answer is quoted.

## REFACTOR
- [x] An independent review of README, skill, notebook and CHANGELOG found no false example; its
      wording findings (indented negation, "removes nothing beyond git's own cut", lone CR) went
      into this text. The lone-CR finding was a code defect, fixed in igittigitt with a git-oracle
      test before the sentence went in.
- [x] Tiers: haiku and opus for RED, GREEN and the re-probe (6 cells).
- Decisions: d-20261126-95661831, d-20261126-6af759c0, d-20261126-e98ea2fc, d-20261126-f395b15b

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added; example paths are `/path/to/project`.
- [x] Frontmatter untouched: no routing keyword moved.
- [x] Mirrored skill: `repo-gate.py --mirrors` reports the pair in sync.
