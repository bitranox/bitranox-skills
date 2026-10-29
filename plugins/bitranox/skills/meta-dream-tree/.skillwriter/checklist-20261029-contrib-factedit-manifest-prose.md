# skill-writer checklist - meta-dream-tree (factedit, store_manifest, session-review --prose)

- [x] Change (code, TDD in tests/test_factedit_round_trip.py, test_store_manifest.py,
      test_dream_state_prose.py): `factedit.py apply` refuses a pinned fact without
      `--allow-pinned`; `show --body` prints the body alone on stdout; a body file carrying the
      show header is refused; a slug the chain walk misses names its owning level; `store_manifest`
      refuses an `--out` inside the knowledge tree and records hook/body digests that `verify`
      compares; `dream_state.py session-review --prose`.
- [x] RED (text): at HEAD the skill and references do not say it - `git show HEAD:<file> | grep -c`
      gave 0 for "allow-pinned", "header on stderr", "exact `--level <dir>` retry", "inside the
      knowledge tree", "hook digest, body digest", "hooks and bodies not compared" (SKILL.md),
      "--prose" and "transcript_tail" (references/dream-core.md), "skillwriter"
      (references/dream-passes.md).
- [x] GREEN (quote-back, same greps on the edited files: 2,1,1,1,1,1,5,1,2): SKILL.md "`apply`
      writes a pinned fact only with `--allow-pinned`, a human's call, and `--dry-run` stages and
      prints the change without it"; step 2 "So is an `--out` anywhere inside the knowledge tree";
      step 8 "a change names its fields (`title`, `pin`, `hook`, `body`)" and "a body digest says
      THAT a body changed, never whether its `type:` did"; dream-core.md "A multi-MB stretch: read
      it with `--prose`"; dream-passes.md excludes `*/.skillwriter/*` when proving coverage.
- [x] Placement: each rule sits where the reader meets it - the factedit paragraph, step 2
      (backup), step 8 (verify), the pinned checklist line, Capture-first in dream-core.md, the
      "Point a rule at its skill or HOOK" section of dream-passes.md.
- [x] Every claim checked against the code: verify output `changed  <slug>  (<fields>)` from
      `_render_diff`; the older-manifest note text from `main`; the 64 MB window from
      `PROSE_CHUNK_BYTES`.
- [x] Description measured: unchanged (`git diff -U0 -- '*SKILL.md' | grep -E '^[+-](name|description):'`
      printed nothing).
- [x] ASCII only (`git diff -U0 | grep '^+' | grep -P '[^\x00-\x7F]'` printed nothing), present
      tense, no private host, repo or customer names in the added lines.
- [x] Mirror check: `repo-gate.py --mirrors` lists 12 pairs, none of them this skill.
