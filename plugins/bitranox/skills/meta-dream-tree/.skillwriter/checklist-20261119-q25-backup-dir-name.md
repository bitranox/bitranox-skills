# skill-writer checklist - meta-dream-tree (2026-11-19, the tree dream's backup dir name)

- [x] Change 1: SKILL.md step 2 defines `<key>-<ts>`: `<key>` is `tree-<name of the anchor dir>`,
      `<ts>` the `YYYYMMDD-HHMM` of the dream id from step 0c, with an example, and says a backup
      into a dir that already holds one replaces it with exit 0.
- [x] Change 2: references/dream-core.md, "Backup + manifest": `<key>-<ts>` is named by the
      calling skill (store_manifest.py writes to whatever `--out` it gets), with the tree, nap and
      crosstree forms. The nap form is the one meta-dream-nap step 2 already prescribes, the
      crosstree form the one meta-dream-crosstree step 1 already defines.
- [x] Change 3: same paragraph, the manifest tuple listed (level, slug, title, pin) while
      SKILL.md and store_manifest.py's `Entry` record hook and body digests too; it now lists all
      six fields.
- [x] Decisions: d-20261119-7582f2c0
- [x] Step 0b: two rejected entries (ref_map after a dropped move, scratch-tree re-derivation);
      neither concerns this change; no live rule's anchor touched.
- [x] Command executed: on a scratch tree with one fact,
      `store_manifest.py backup --from <tree> --scope tree --out <dir>/tree-<anchor>-<ts>` exited
      0 and wrote manifest.json, levels/ and store/; a second backup into the same dir exited 0
      and replaced it; verify reported IDENTICAL.
- [x] RED as a text check against the pre-edit text (`git show HEAD:`): `<key>` appears in
      SKILL.md step 2 and twice in dream-core.md and is defined nowhere in the skill.
- [x] GREEN quote-back on opus (effort medium) and haiku: both built
      `tree-projects-20261119-1407` for an anchor dir named `projects`, quoted that the script
      writes to whatever `--out` it is given and that a second backup replaces the first.
- [x] GREEN gap closed: the two files disagreed on the manifest's fields (change 3); the
      "keeps two runs apart" claim was too broad (two runs in one minute on same-named anchors
      collide), now "only a new name keeps the earlier backup".
- [x] Declined gaps: the dream id's clock and time zone belong to step 0c, which this edit does
      not change; `~` is expanded by the shell in the command as shown; the nap's timestamp
      format is in meta-dream-nap SKILL.md step 2 (`date +%Y%m%d-%H%M%S`).
- [x] Re-probe on the final text, opus and haiku: same path built, both files agree on six
      fields, no new undecided gap.
- [x] Width and fence check over the added lines printed nothing; the sentence after each
      insertion point was read.
- [x] ASCII only, present tense, no private paths or hosts.
