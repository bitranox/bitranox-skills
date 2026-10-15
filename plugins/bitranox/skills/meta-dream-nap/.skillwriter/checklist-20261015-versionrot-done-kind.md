# meta-dream-nap: versionrot in the prune step, done --kind nap

Change: step 5 runs `versionrot.py scan --chain` and handles each on-chain candidate as
meta-dream-tree step 7, question 3 says; step 6 and the common-mistakes line run
`dream_state.py done --kind nap`, which `dream_state.py` now requires. Skill type: technique.

## Verification

- [x] The RED and GREEN evidence is shared with meta-dream-tree and recorded in
      `meta-dream-tree/.skillwriter/red-20261015-version-rot-and-jev-receipt.md` and
      `meta-dream-tree/.skillwriter/checklist-20261015-versionrot-and-jev-receipt.md`; this text
      delegates the outcomes to meta-dream-tree step 7 rather than restating them.
- [x] The prior text's bare `dream_state.py done` is refused by the current `dream_state.py`
      ("done needs --kind nap|tree"), so leaving it would ship a step that cannot run.
- [x] `versionrot.py scan --chain` exists with that flag (`versionrot.py scan --help`).

## Quality checks

- [x] ASCII only; no new addresses, hostnames or private paths; no session narrative.
- [x] Frontmatter and description untouched.
