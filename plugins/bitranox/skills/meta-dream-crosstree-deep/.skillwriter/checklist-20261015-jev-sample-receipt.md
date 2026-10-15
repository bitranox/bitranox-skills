# meta-dream-crosstree-deep: Jev shadow sample, dream tag and receipt

Change: step 3b's shadow bullet uses one `<dream id>` (`crosstree-deep-<YYYYMMDD-HHMM>`) for the
whole run, samples with `--sample 40 --seed <dream id>`, tags `run --dream <dream id>`, says
every candidate is still relocated or rejected (not only the sample), and runs crosstree step 8's
`jev_shadow.py receipt` before the report. Skill type: technique.

## Verification

- [x] Evidence shared with meta-dream-crosstree and meta-dream-tree (see
      `meta-dream-tree/.skillwriter/checklist-20261015-versionrot-and-jev-receipt.md`); this
      bullet delegates the receipt to crosstree step 8 rather than restating it.
- [x] The flags exist as written (`jev_shadow.py items --help`, `run --help`, `receipt --help`).

## Quality checks

- [x] ASCII only; no new addresses, hostnames or private paths; no session narrative.
- [x] Frontmatter and description untouched.
