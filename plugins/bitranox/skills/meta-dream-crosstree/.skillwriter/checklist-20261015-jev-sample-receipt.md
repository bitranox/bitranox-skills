# meta-dream-crosstree: Jev shadow sample, dream tag and receipt

Change: step 4b's shadow bullet names the run (`crosstree-<YYYYMMDD-HHMM>`), samples with
`items --sample 40 --seed <dream id>` and tags `run --dream <dream id>`; step 8 runs
`jev_shadow.py receipt --dream <dream id> --site crosstree-misplaced` before the report, and the
report line gains the `skipped (<reason>)` form. Skill type: technique.

## Verification

- [x] The RED and GREEN evidence for the sample-and-receipt mechanism is shared with
      meta-dream-tree (`meta-dream-tree/.skillwriter/red-20261015-version-rot-and-jev-receipt.md`
      and `checklist-20261015-versionrot-and-jev-receipt.md`): RED, an agent with no receipt
      marked the dream done with every site `off`; GREEN, opus and haiku both refused to skip for
      "no time" and fed every site.
- [x] The flags exist as written: `jev_shadow.py items --help` lists `--sample` and `--seed`,
      `run --help` lists `--dream`, `receipt --help` lists `--dream`, `--site`, `--skip`.
- [x] The all-trees-empty case is covered: `items` exits 1 on a tree with no candidate, so no
      rows exist, and the text names `--skip crosstree-misplaced=no items on any tree`.

## Quality checks

- [x] ASCII only; no new addresses, hostnames or private paths; no session narrative.
- [x] Frontmatter and description untouched.
