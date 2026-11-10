# skill-writer checklist - meta-dream-crosstree (back up and verify with store_manifest)

Covers SKILL.md steps 1 and 8.

- [x] Change: step 1 takes one `store_manifest.py backup --from <that tree's anchor> --scope tree
      --out ~/.claude/self-improve-audit/backups/<key>-<ts>` per tree the run may write, never a
      hand-rolled snapshot; a native `memory/` dir is copied beside the backup by hand. Step 8 runs
      `store_manifest.py verify --out <that tree's step 1 dir>` once per tree and copies its
      `pointer blocks` lines into the report as printed, per tree, naming the slugs that arrived
      at each tree top from `data.levels[]` under `--json`.
- [x] Step 0b: `skill_decisions.py show meta-dream-crosstree --kind rejected,removed --full` and
      plain `show` print nothing; no decision is reversed.
- [x] Contract test `test_every_dream_backs_up_and_verifies_with_store_manifest`
      (hooks/tests/test_dream_skill_contracts.py): RED before the edit, 2 failed with
      "meta-dream-crosstree hand-rolls its backup" and "meta-dream-crosstree-deep hand-rolls its
      backup" (nap and tree passed); GREEN after, 19 passed.
- [x] Mechanism claims checked against store_manifest.py: `backup` takes `--from`, `--scope
      tree|chain`, `--out` and copies the anchor's store plus every in-scope `CLAUDE.local.md`
      (`backup`), and nothing else, so a native `memory/` is not covered; `verify` takes `--out`
      only and reads the scope from the manifest; the text form prints per changed level
      `bytes A -> B  pointers A -> B  arrived N  left N` (`_render_costs`), the slugs only under
      `--json` in `data.levels[]`. A promotion goes to "the lowest common ancestor WITHIN ITS
      TREE" (step 5), so the tree's own verify reports its arrival.
- [x] Commands executed on two scratch trees before the GREEN probe: `backup --from <tree>
      --scope tree --out <dir>` for each (rc 0, "backed up 2 pointer(s) (tree scope)"); after a
      slug was moved to one tree's top, that tree's `verify --out` exited 1 with `moved` and the
      top line `pointers 1 -> 2  arrived 1  left 0`, the other tree's exited 0 with
      `pointer blocks: no level changed`; `--json` listed the slug under `arrived`.
- [x] RED (opus, pre-edit steps 1 and 8 pasted): Q1 hand-built `cp -a` and `find | xargs cp
      --parents` commands ("The text gives a destination and a scope, not a command"); Q2 "NOT
      STATED" for the pointer-block change; Q3 "NONE" for a loss check; Q4 nap scope "NOT STATED".
- [x] GREEN (opus and haiku, edited steps 1 and 8 plus the cited meta-dream-tree step 2 and the
      dream-core report contract pasted; 5 questions x 2 tiers): Q1 `store_manifest.py backup
      --from /work --scope tree --out ~/.claude/self-improve-audit/backups/work-<ts>` and the same
      for /lab; Q2 the `pointer blocks` lines as printed, per tree, slug names from
      `data.levels[]` under `--json`; Q3 `verify --out <that tree's step 1 dir>` per tree; Q4
      control: "a nap does NOT use --scope tree ... (a nap uses `--scope chain`)"; Q5 "copy it
      beside the backup by hand". Neither arm called any tool but ReportFindings.
- [x] GREEN gap closed: opus reported that "a promotion to a common ancestor" could sit above
      both trees, outside every backup. Step 8 now says the ancestor "lies within its tree
      (step 5), so that tree's verify reports it". Quote-back re-probe (opus, effort medium)
      quoted that sentence and "promote it to the lowest common ancestor WITHIN ITS TREE"; no new
      gap.
- [x] GREEN gaps declined: the two count lists (dream-core's report counts vs step 8's
      crosstree counts) and the undescribed one-time whole-store backup predate this change and
      sit in steps out of this change's scope; `<key>` and `<ts>` are the family's shared backup
      path placeholders (dream-core.md writes the same `backups/<key>-<ts>/`); whether verify needs
      `--scope`: it has no such flag, the scope comes from the manifest (store_manifest.py,
      `verify` parser takes `--out` and `--json` only); step 4b and the jev receipt are outside
      the pasted excerpt and stated in the skill.
- [x] Width and fence check over the added lines prints nothing after the reflow that rejoined
      two code spans split across lines; ASCII only.
- [x] Decisions: d-20261110-bcf1ef3c
