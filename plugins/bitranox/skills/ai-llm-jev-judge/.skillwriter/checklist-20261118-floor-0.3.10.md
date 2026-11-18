# Review: uvx floor names 0.3.10 (mirror of the tool repo's release)

Change: the five `uvx --from 'btx-skill-jev-judge>=0.3.9'` lines now read `>=0.3.10`. No other
text changes; the description is untouched.

- [x] Premise measured: PyPI serves 0.3.10 on both the JSON API and the Simple index
      (json=0.3.10, simple=True), published by the tool repo's release run on tag v0.3.10 (CI
      green on cc3250a), so the floor resolves.
- [x] Why the floor moves: the tool repo's `test_every_skill_floor_names_the_release_version`
      requires the skill to name the version it is released with (9 passed in
      tests/test_metadata_sync.py with the raised floor); 0.3.10 imports `DeployAction` from the
      lib_layered_config root instead of the `lib_layered_config.examples` shim.
- [x] Count: `grep -c "btx-skill-jev-judge>=0.3.10" SKILL.md` is 5 on both sides, 0.3.9 is 0.
- [x] `JEV_JUDGE_FLOOR` in meta-self-improve/jev_shadow.py follows to 0.3.10; its pin test
      (`test_the_floor_constant_matches_the_jev_judge_skill`) passes with it raised.
- [x] Mirror: `diff -r -x .skillwriter` between the two skill directories differs only in the
      `name:` line.
- [x] No behavioural probe arm: a version floor carries no instruction a reader could follow
      differently; the evidence is the resolve check above.
- [x] Latest-release finder (the line pass) over the skill's Markdown outside `.skillwriter/`:
      no hits.

Decisions: none - no ledger entry added; the floor follows the release mechanically.
