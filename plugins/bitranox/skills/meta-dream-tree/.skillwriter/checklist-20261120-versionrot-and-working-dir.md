# checklist - versionrot attribution and topic placement; the dream's working dir

Two queued contributions.

1. versionrot.py: a fact placed by topic is reported by its topics and how many levels list it
   (JSON `level` null, `topics` and `levels` added) instead of one arbitrary level; a linker alias
   such as "plugin" binds only after filler, and a pronoun between a package and a version ends
   the search, so "codex plugin 1.0.6" no longer reads as the bitranox plugin.
2. SKILL.md step 2: the backup dir is the dream's working dir; subagents write their full result to
   a plain-named .txt file there and make scratch dirs with `mktemp -d -p <backup dir>`; the three
   jev-shadow `mktemp -d` lines use the same form.

Decisions: d-20261120-4e35e765

versionrot's own design choices are in its module docstring's Decisions block.

## RED

- [x] Skill decisions read first: nothing rejected on versionrot or subagent briefs.
- [x] Text check at HEAD: "dream's working dir" 0 hits, `mktemp -d -p <backup dir>` 0 hits.
- [x] The three new versionrot tests fail with versionrot.py reverted to HEAD (mutation_arm KILLED).
- [x] Differential over 2098 facts / 1121 claims before and after: 13 changed, all from a package to
      unresolved; 9 wrong attributions withdrawn, 3 changed only the unresolved name, 1 correct
      dated attribution lost (recorded in the docstring). A one-unknown-word limit was tried and
      dropped: it lost 3 correct attributions.

## GREEN

- [x] 62 tests pass in tests/test_versionrot.py; live `--tree` scan 50 claims / 36 facts -> 40 / 32.
- [x] Quote-back probe (haiku): results file, scratch dir, read-the-file and the null-level meaning
      all answered by quotes. Its one NONE (jev files) came from an excerpt that left that sentence's
      subject out, not from the skill.

## REFACTOR

- [x] Paragraphs re-wrapped to the file's width; ASCII check clean.
