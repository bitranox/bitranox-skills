# Handover - 2026-10-29 15:10, [23] batch 9 (tree top) release staged

## In flight

- [23] batch 9: 13 tree-top rows folded into 7 skills (6 changed; process-test-design already
  covered its row). GREEN 13/13 on haiku and opus, opus review fixed, round-2 quote-back 5/5 on
  both tiers (quotecheck 15 OK, planted negative MISMATCH). Checklists written
  (`.skillwriter/checklist-20261029-fold23-batch9.md` in each changed skill and both twins).
  Release staged as 10.4.1 with twins bmk (devops-bmk) and btx_lib_mail (python-send-mail),
  both in sync per `repo-gate.py --mirrors`.
- Version collision: the `lib_layered_config` peer session has 73a7d4db (10.4.1) committed on
  the main checkout's local master, unpushed; it was messaged. Whoever pushes second rebases and
  re-bumps (assert the old value). Its twin is why `--mirrors` shows coding-python-layered-config
  DRIFT; not this work.
- After the push: bmk twin bump 3.32.2 -> 3.32.3 (plugin.json + SKILL.md + checklist);
  btx_lib_mail 4.6.2 -> 4.6.3 via `make bump-patch`, CHANGELOG, `make test`, commit only own
  paths (a peer's uncommitted handover.md sits there); push both; CI on all three; user installs;
  quote-check the installed cache; archive 9 facts and cut 4 hooks (`.plan/fold-23/batch9/
  dispositions.json`; store backup OUTSIDE the tree); end the skill receipt.

## Decided

- USER 2026-10-29 chose "Tree top (Recommended)" for batch 9 (verbatim in the main checkout's
  EXECUTION-USER-REVIEW.md); one fold round for archive and cut rows (autonomous, logged there).
- feedback-public-push-review-and-humanize stays a fact (5 inbound refs).
- Declined review items: the venv lock timeout (already stated in devops-bmk), a second envelope
  from the Makefile regeneration (its pre-steps run no pipeline), restoring devops-bmk's
  cross-plugin pointer (the bmk twin installs alone).

## Still open, untouched

- Everything else: `OPEN-WORK.md`.

## Next action

Read the lib_layered_config peer's answer, settle the version, commit the marketplace worktree
(own paths, `-F` message), commit bmk, push the marketplace, push bmk, release btx_lib_mail.

## How to verify

- `python3 plugins/bitranox/hooks/repo-gate.py --mirrors` (devops-bmk and send-mail in sync).
- `reconcile_memory_index.py --check-tree /media/srv-main-softdev` reports 0 problems.

## Lessons for the next nap

- When backing up the memory tree with store_manifest.py, write --out OUTSIDE the tree (the
  session scratchpad): a backup under the tree adds its copied CLAUDE.local.md files as duplicate
  levels, and --check-tree then reports one problem per pointer.
- When a peer session pushes a plugin version while yours is staged, restore only the shared
  files (CHANGELOG, plugin.json, pyproject) to HEAD, fast-forward, and re-insert your entry under
  the next number with an assert on the old one.
- When a peer COMMITS a version bump on the main checkout without pushing, it is invisible to a
  fetch of origin: check `git log master` in the main checkout before picking a number.
- tooling: the SessionStart hook after a compaction creates empty CLAUDE.md/CLAUDE.local.md in a
  gitignored scratch dir under .plan (contrib queued).
