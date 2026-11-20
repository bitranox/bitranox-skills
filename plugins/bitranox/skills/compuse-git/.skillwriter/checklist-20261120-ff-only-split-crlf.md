# checklist - ff-only over an identical dirty file, splitting by hunk, CRLF-blob repos

Three queued contributions: two Quick-reference rows (`git merge --ff-only` refusing over a dirty
file whose bytes already equal the incoming blob; splitting a finished change by zero-context
hunks) and a subsection "A repo that stores CRLF blobs on purpose" (text-mode rewrites, why a
re-add does not repair it, storing exact bytes with `hash-object --no-filters` plus
`update-index --cacheinfo`, verifying with `git diff --cached --stat HEAD`).

Decisions: d-20261120-a270c385, d-20261120-36ae0bb8, d-20261120-fd24c348

## RED

- [x] Skill decisions read first: none rejected or removed that these rows touch.
- [x] Text check of the pre-edit file: `hash-object --no-filters` 0 hits, `unidiff-zero` 0 hits,
      `ff-only` only inside the unrelated `git apply --3way` row.
- [x] Claims probed in scratch repos before writing: ff_probe.sh (ff-only refuses although the
      worktree bytes equal the incoming blob; checkout plus fast-forward leaves the same bytes),
      crlf_probe.sh (after an LF blob is staged under `text=auto eol=crlf`, re-adding the restored
      CRLF file stays a whole-file diff; the `--no-filters` route shows one line). The hunk-split
      claim is inherited from the queue entry, not reproduced.

## GREEN

- [x] Quote-back probe (opus, haiku): B1, B2 and B3 answered with quotes of the new rows and
      subsection; no NONE.

## REFACTOR

- [x] Closed (opus, haiku): no fetch before comparing with `origin/main`; the row now says
      "Fetch, then compare" and names what the re-check compares (`HEAD:FILE`).
- [x] Closed (haiku): the worktree file is still LF after a text-mode script; the bullet now says
      to restore CRLF in binary mode before storing the bytes.
- [x] Declined (haiku): `origin/main` versus `master` - the row is a recipe, the branch name is
      the reader's.
- [x] Table re-padded with reformat_tables.py after a script edit; width, fence and ASCII checks
      on the added lines clean.
