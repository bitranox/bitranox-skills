# skill-writer checklist - meta-dream-crosstree-deep (back up and verify with store_manifest)

Covers SKILL.md, "What changes vs meta-dream-crosstree", item 1.

- [x] Change: item 1 backs up with `store_manifest.py backup --scope tree`, once per tree the run
      writes, and verifies against each backup with `store_manifest.py verify` before the report,
      deferring to meta-dream-crosstree steps 1 and 8 instead of restating a hand-rolled snapshot.
- [x] Step 0b: `skill_decisions.py show meta-dream-crosstree-deep --kind rejected,removed --full`
      and plain `show` print nothing; no decision is reversed.
- [x] Contract test `test_every_dream_backs_up_and_verifies_with_store_manifest`: RED before the
      edit ("meta-dream-crosstree-deep hand-rolls its backup"), GREEN after (19 passed).
- [x] RED and GREEN: the item defers every detail to meta-dream-crosstree steps 1 and 8, so the
      behavioural probes ran on those steps (see meta-dream-crosstree's
      checklist-20261110-store-manifest-backup.md). The deep item adds no command of its own; the
      contract test pins that it names both `store_manifest.py backup` and
      `store_manifest.py verify`.
- [x] Width and fence check over the added lines prints nothing; ASCII only.
- [x] Decisions: d-20261110-37a432a8
