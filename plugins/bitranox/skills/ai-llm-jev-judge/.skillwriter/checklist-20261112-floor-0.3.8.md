# Review: uvx floor names 0.3.8 (mirror of the tool repo's release)

Change: the five `uvx --from 'btx-skill-jev-judge>=0.3.7'` lines now read `>=0.3.8`. No other
text changes; the description is untouched.

- [x] Premise measured: PyPI serves 0.3.8 on both the JSON API and the Simple index
      (scratchpad pypi_wait.py: json=True simple=True), published by the tool repo's release run
      on tag v0.3.8 (CI green on a4c86eb), so the floor resolves; a verbatim run of the Commands
      lines resolved 0.3.8 (tool repo docs/skill-review.md, "Release check (0.3.8)").
- [x] Why the floor moves: the tool repo's `test_every_skill_floor_names_the_release_version`
      requires the skill to name the version it is released with; its 0.3.8 commit raises the
      floor, and this twin must match it.
- [x] Count: `grep -c "btx-skill-jev-judge>=0.3.8" SKILL.md` is 5 on both sides, 0.3.7 is 0.
- [x] `JEV_JUDGE_FLOOR` in meta-self-improve/jev_shadow.py follows to 0.3.8; its pin test
      (`test_the_floor_constant_matches_the_jev_judge_skill`) passes with it raised.
- [x] Mirror: `repo-gate.py --mirror-of` reports the pair in sync after this change, and
      `diff -r -x .skillwriter` differs only in the `name:` line.
- [x] No behavioural probe arm: a version floor carries no instruction a reader could follow
      differently; the evidence is the resolve check above.

Decisions: none - no ledger entry added; the floor follows the release mechanically.
