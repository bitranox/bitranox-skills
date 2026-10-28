# skill-writer checklist - coding-python-gitignore (2026-10-28, check -v git-exact, CLI and API gaps)

igittigitt 2.4.0 makes `check -v` print what `git check-ignore -v` prints. The skill is regenerated
from the twin in `libs/igittigitt/skills/python-gitignore/` with the conventional divergences (name
field, self-install blockquote) re-applied; the H1 is identical in both. Changed sections: the
`IgnoreParser` method list, an `IncludeParser` note, the CLI and Bash usage blocks with their option
notes, the performance-defaults version line, and "Default patterns".

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: a retrieval scenario of six questions on the CLI sections (is a
      negation-re-included path printed by `check -v` and with which exit code; is the rule file
      absolute or relative to `-C`; field separation under `-v -z`; does `filter --include` read
      `.gitignore` files; does the CLI load git's user ignore file by default; the exit code when
      the reader closes the pipe), each answered with a direct quote or NONE, plus `Skill gaps`.
- [x] Scope: the sections listed above. Frontmatter unchanged.

## Ground truth (igittigitt 2.4.0 and git 2.53)
- [x] Every library and CLI example executed against igittigitt 2.4.0 and its output asserted.
- [x] `*.log` then `!keep.log`: `check -v keep.log` prints `.gitignore:2:!keep.log<TAB>keep.log`,
      exit 0; `check keep.log` prints nothing, exit 1. `git check-ignore` gives the same in both
      forms.
- [x] `-v -z` emits four NUL-terminated fields, as git does; pinned by
      `tests/test_git_compat.py::test_check_verbose_zero_separates_every_field_like_git`.
- [x] The source is named relative to `-C`; pinned by
      `test_check_verbose_prints_what_git_prints` (every-path, only-a-negated-path, no-match).

## RED
- [x] haiku and opus `baseline-probe`, given the pre-change CLI sections: NONE for all six
      questions. opus guessed exit 1 for the negation case (wrong; git and igittigitt give 0) and
      guessed that `--default-patterns` adds a built-in pattern set (wrong).

## GREEN
- [x] haiku and opus, given the new sections: questions 2 to 6 answered with a direct quote, all
      correct. Question 1 (printed: yes) answered with a quote, but both models named the exit code
      only as an inference: "counts for the exit code" never states the value.
- [x] GREEN skill gaps: the negation exit code (CLOSED: the line now says the listing makes the
      exit 0, and that without `-v` the same path exits 1, and shows the `src:line:pattern<TAB>path`
      form; the same wording went into the twin and igittigitt's README); the path of git's user
      ignore file in the CLI section (DECLINED: "Default patterns" names
      `$XDG_CONFIG_HOME/git/ignore`; the probe saw an excerpt); `--scan` default, error exit codes,
      `-r` source column, path resolution, Windows exit for a closed pipe (DECLINED: outside what
      this change touches; the CLI's `--help` and README carry them).
- [x] RED against GREEN, both directions: no RED answer is lost; every GREEN answer is quoted.

## REFACTOR
- [x] The closed gap was checked against the CLI and git before the wording went in (exit 0 with
      `-v`, 1 without, in both). No further probe round: the change states a measured value where
      the GREEN text left it to inference.
- [x] Tiers: haiku and opus for RED and GREEN (4 cells).

## Quality
- [x] Present tense; no session narrative, no scratch paths.
- [x] No address, MAC, hostname or machine path added; example paths are `/path/to/repo`.
- [x] Frontmatter untouched: no routing keyword moved.
- [x] Mirrored skill: `repo-gate.py --mirror-of` reports the pair in sync.
