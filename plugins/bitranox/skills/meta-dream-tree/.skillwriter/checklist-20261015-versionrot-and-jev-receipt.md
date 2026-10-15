# meta-dream-tree: version-bound facts in the prune step, Jev shadow sample and receipt

Change: step 7 asks a third question of every fact (is its lesson tied to one past version?),
answered with `versionrot.py scan --tree`, with three outcomes after a re-check against the
current release (reword, archive or drop one line, merge) and the non-candidates named. Step 0c
names the dream (`tree-<YYYYMMDD-HHMM>`) and moves the three shadow sites to a sample of 40,
tagged with that id; the step 5/6/7 shadow bullets build with `--sample 40 --seed <dream id>` and
run with `--dream <dream id>`. Step 11 runs `dream_state.py done --kind tree --dream <dream id>`
with its home and launch, says what its exit 1 means and when `--jev-skip` is allowed, and the
report gains the versionrot outcomes and the `skipped (<reason>)` form. References follow:
`dream-passes.md` removal policy, `dream-core.md` script homes and verification contract,
meta-self-improve `references/jev-shadow.md` (sample, tag and receipt; report form; dream-prune's
`version_bound`; `dream_id`; receipt exit codes). Skill type: technique. Test approach:
application scenarios, text-only `bitranox:baseline-probe` arms on opus and haiku.

## Verification

- [x] RED (recorded in `red-20261015-version-rot-and-jev-receipt.md`, opus, the old step text):
      probe 1 "the text gives no instruction or command to compare a fact's cited version against
      the installed one" (NONE); probe 2 marked the dream done with every site `off`: "Nothing
      stops it."
- [x] Inherited coverage: the RED arms answered NONE for the detector and for the precondition,
      and `versionrot.py`, `--sample`, `--dream` and `receipt` exist only on this branch, so no
      cascade or memory text could supply them.
- [x] GREEN probe 1, opus, new step 7: F1 "archive it"
      (`reconcile_memory_index.py --archive <F1-slug> /path/to/tree`), F2 reworded "with the
      version history dropped", F3 "drop that line ... and keep the fact"; finder quoted "find them
      with `versionrot.py scan --tree <anchor> --json`"; exit 2 quoted "an error to report, never a
      clean tree".
- [x] GREEN probe 1, haiku: the same three outcomes with the same quotes; level taken from "each
      with the level that owns its pointer".
- [x] GREEN probe 2, opus, new steps 0c/7/11: id `tree-20261015-1405` from "Name this dream now";
      `done` "exits 1 having marked NOTHING done"; refused the no-time skip quoting "A skip is
      reported, so "no time" is not a reason."; fed all three sites, then re-ran `done`.
- [x] GREEN probe 2, haiku: the same command and id, the same refusal, the same quote against the
      no-time skip, fed every site.
- [x] RED vs GREEN diffed both ways: RED's reading of the test snapshot as task-state became a
      one-line drop, its build-tool archive stayed an archive (now from the text, not its own
      reading), and RED's `off` report became fed sites. Nothing RED produced is missing.
- [x] Quote-back after REFACTOR (haiku, the changed passages): body input quoted "`factedit.py
      apply --slug <slug> --level <its level> --body-file <f>`, adding `--hook-file <f2>` when the
      HOOK names the version too"; a pre-ask `run` failure quoted "logged nothing - fix the input
      and run it again". It answered NONE on whether a jev-judge timeout logs rows; the text now
      names the timeout among the after-asking failures (matching `references/jev-shadow.md`,
      which lists it with "records still logged"), and the `--jev-skip` example no longer uses a
      timeout, which is a fed site, not a skipped one.

## Skill gaps reported by GREEN, each decided

- [x] How `factedit.py apply` takes the new body: CLOSED - `show --body ... --level`, edit in a
      file, `apply ... --body-file <f>`.
- [x] A version left in the HOOK after a body-only edit: CLOSED - `--hook-file <f2>` when the hook
      names the version, with the reason (the always-loaded line keeps saying it).
- [x] Skip versus error when `run` fails: CLOSED - an exit 2 after asking still logged rows (fed,
      reported `error <message>`); one before asking logged nothing (fix the input, run again).
- [x] A fixed-bug fact still useful to someone on an old version: DECLINED - the store describes
      the installed tooling; the archive is recoverable from `.archive/`, which the text now says.
- [x] Feeding the shadow late, at step 11, from a store the prune already changed: DECLINED - the
      seed reproduces the sample over the facts that exist then, `run` accepts a tagged run at any
      time, and the text already sends the agent back to feed the site.
- [x] Propose-first versus "do exactly one of": DECLINED - the dream's mode (off/auto/propose)
      governs every write and is defined once in `references/dream-core.md`.
- [x] Questions 1 and 2 have no scanner: DECLINED - pre-existing, judgement questions; out of
      this change's scope.
- [x] `<plugin>`/`<anchor>` placeholders: DECLINED - the skill's existing convention, defined in
      `references/dream-core.md` "Script homes".
- [x] Report "per site" read as including `crosstree-misplaced`: DECLINED - step 0c names the
      three tree sites; crosstree reports its own.

## Quality checks

- [x] ASCII only in the changed text and this file.
- [x] No new addresses, hostnames or private paths; the scenario used `/path/to/tree`.
- [x] Frontmatter and description untouched.
- [x] Full plugin suite green with CI's dependency set: 12533 passed, 35 skipped, 1 xfailed.
- [x] Every command in the text checked against its `--help`: `versionrot.py scan`,
      `factedit.py show/apply`, `jev_shadow.py items/run/receipt`, `dream_state.py done`.
