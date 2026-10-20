# skill-writer checklist - compuse-toolbox (2026-10-20, conflict_resolve row)

One row is new in the tool table, `conflict_resolve` (after `conflict_scan`), for a new jig that
resolves the merge-conflict hunks of one file by an explicit rule per hunk. The toolbox nudge gains
a rule naming it. Frontmatter unchanged.

## PLAN
- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - questions whose answer depends on the
      changed text, answered only from a copy of the document, with a verbatim quote or NONE.
- [x] Scope: the one new row; no existing row or note reworded.
- [x] Inherited-context route: the arms read a staged copy of the old and new document and are
      told not to invoke a skill or read anything else, so the answer is a text check of the
      document, not of the installed skill or the machine's memory.
- [x] Frontmatter: the description is at 1017 of 1024 characters, so no trigger phrase fits; the
      jig is reached through the table and the toolbox nudge, not the description.

## RED (pre-change document)
- [x] One question per agent, whole index readable, NONE stated as acceptable: "Rebasing left 3
      conflict hunks in CHANGELOG.md; I want both entries in each, the incoming one on top, and to
      be sure none are left - what do I run?" (opus, the agent read only the document).
- [x] Resolving the hunks: NONE - "No row in the index merges or rewrites conflict hunks"; it would
      hand-roll a Python script walking the markers. It found `conflict_scan` for the last half.

## GREEN (new document, same model and questions)
- [x] Named `conflict_resolve`, quoting its row "**you are resolving a merge conflict hunk by
      hunk** - keep ours or theirs, keep both sides of a CHANGELOG conflict with the newer entry
      on top", and ran `conflict_resolve.py CHANGELOG.md --all both-theirs-first --expect-hunks 3`
      after `--list`.
- [x] GREEN gap closed - which side is `theirs` in a rebase, and the order `both` writes: the row
      and the script's rule docs now say `ours` is the `<<<<<<<` side and `theirs` the `>>>>>>>`
      side, so in a rebase `theirs` is the commit being replayed, and `both` puts ours first.
- [x] GREEN gap declined - whether the `both*` rules drop a diff3 base section: the rule list
      names `base` as its own rule; the tests pin that `both` writes only the two sides.
- [x] GREEN gap declined - duplicate lines shared by both sides: the tool concatenates by design;
      deduplicating would be a merge strategy, out of this jig's scope.
- [x] GREEN gap declined - running from the skill dir: the row's usage column follows the table's
      convention for every jig.
- [x] GREEN diffed against RED in both directions: RED's `conflict_scan` follow-up survives in
      GREEN as the optional second check; nothing RED produced was lost.

## Code the text describes
- [x] `scripts/conflict_resolve.py` ships with `tests/test_conflict_resolve.py`: every rule kind
      (ours, theirs, base, both, both-theirs-first, file:), a diff3 base section, a CRLF file kept
      byte for byte, a hunk closing a file with no final newline, a BOM and non-UTF-8 bytes
      passing through, `--match` by either side's text, every refusal path with the file's bytes
      asserted unchanged and no temp file left, `--list` writing nothing and showing three lines
      per side, the `--json` envelope shape, a file with no hunks (exit 0, not written), the
      re-scan reporting a marker a replacement carried (exit 1), the file mode kept and a symlink
      written through.
- [x] The tests were written first and failed for want of the module; then green.
- [x] A 17-arm mutation battery over the jig was killed in full after one survivor (the last-`=`
      split of `REGEX=RULE`) was pinned by a test.
- [x] Run once against conflicts git itself produced (a diff3 merge of a CHANGELOG with three
      hunks): `--list` showed them, and `--hunk 1=both-theirs-first --match ...=theirs --hunk
      3=base --expect-hunks 3` resolved them with no marker left.
- [x] The jig imports and its tests pass in an environment holding only pytest (standard library
      only).
- [x] Exit codes follow the toolbox standard stated at the top of SKILL.md: a refusal of the whole
      action is 2 with `data.refused`, 1 is a written file the re-scan still finds markers in.
- [x] The toolbox nudge rule (`_CONFLICT_RESOLVER_RX`: all three markers on one line plus a
      write-back) was priced through the hook's own decision path over the transcript corpus:
      148 of 156,539 Bash calls (0.095%), 11 of 8,449 Write bodies, 2 of 12,533 Edit fragments.
      Every firing was read: 156 of 161 are hand-rolled resolvers, the other 5 are test fixtures
      or a merge writer emitting markers. Before the rule, 106 of the Bash firings got no nudge
      and 42 were sent to `anchor_edit`; the Write and Edit firings went to `conflict_scan`.

## Quality
- [x] Present tense; no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added; file names are placeholders.
- [x] Tables canonical (`reformat_tables.py --check` reports the file unchanged); the new row has
      three cells, an even backtick count and no pipe inside a cell.
