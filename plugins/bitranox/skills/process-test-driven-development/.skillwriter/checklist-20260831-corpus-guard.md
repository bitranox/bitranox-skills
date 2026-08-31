# skill-writer checklist - process-test-driven-development (`--corpus` arms the unchecked verdict)

Change: `redcheck.py` treats EITHER corpus flag as the caller promising a corpus, so a `--corpus`
directory that is missing or empty now exits 3 (`unchecked`) instead of 0 (`clean`). The SKILL.md
exit-code table and the module docstring are rewritten to that truth. Three new tests, two existing
ones updated.

## PLAN
- [x] Skill type: technique, with a bundled tool. The text change is one table row and one
      paragraph; the behaviour change is in the script the row documents.
- [x] Trigger is measured, not hypothetical. Four arms on the shipped version: `--corpus` on an
      empty dir exits 0 verdict clean, `--corpus` on a nonexistent dir exits 0 verdict clean
      (stderr warns only), both `--corpus-cascade` arms exit 3. `require_corpus` was set from
      `bool(args.corpus_cascade)` alone.
- [x] The docs steered readers to the unguarded form. `--corpus` takes a path typed by hand, so it
      is the mistype-prone one; `--corpus-cascade` walks up from a directory that exists.
- [x] Scope: one predicate, one warning line, three tests, two updated tests, the exit-code table,
      the docstring.

## RED
- [x] `test_cli_exits_unchecked_when_a_named_corpus_dir_assembles_nothing` and
      `..._when_an_EMPTY_corpus_dir_is_named` both failed against the shipped script with
      `assert 0 == 3`, the exact confusion the change removes: a scenario nothing was checked
      against exiting like one that passed.
- [x] `test_cli_without_any_corpus_flag_still_exits_clean` passed BEFORE the change and is the
      direction the guard must NOT reach - passing no flag promises nothing. Kept as a permanent
      control rather than a RED.

## GREEN
- [x] 35 passed. The guard is armed by `corpus_requested = cascade_requested or bool(args.corpus)`,
      and the empty-corpus warning now distinguishes a cascade that assembled nothing from named
      dirs that assembled nothing, so the stderr line says which flag was believed.
- [x] Two existing tests asserted the old behaviour and were updated rather than deleted, each
      keeping its own subject: the stdin test drops a `--corpus` flag that was never what it was
      about, and the warnings test still proves stdout stays a parseable envelope and the reason
      reaches both channels - it now expects exit 3 and says why in its docstring.

## REFACTOR
- [x] The exit-code table row and the paragraph under it were the reason this stayed open: 5.266.0
      scoped the docs DOWN to the defect ("`--corpus` carries no such guard"). Both now state the
      rule the sentence originally promised, and name the reason a gate needs it - a gate reads the
      exit code, not the stderr warning.
- [x] The module docstring carried the same retracted claim twice (the corpus paragraph and the
      exit-code line). Both rewritten; a reader running `--help` or opening the script gets one
      answer.
- [x] Declined: a `--allow-empty-corpus` escape hatch. Nothing in the repo passes a corpus it
      expects to be empty, and the flag would restore by request the failure this closes.

## Quality
- [x] Frontmatter untouched; no description change, so no routing keyword moved.
- [x] Stdlib only, unchanged - the script's whole argument is that a tool deciding whether to trust
      a test should not itself depend on a resolver.
- [x] No session narrative, scratch paths, or machine-specific values in the skill or here.
- [x] Tell sweep and table reformat run clean on the changed Markdown.
