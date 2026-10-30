# Review: uvx floor names 0.3.7 (mirror of the tool repo's release)

Change: the five `uvx --from 'btx-skill-jev-judge>=0.3.6'` lines now read `>=0.3.7`. No other
text changes; the description is untouched.

- [x] Premise measured: PyPI serves 0.3.7 (`pypi.org/pypi/btx-skill-jev-judge/json` lists it,
      latest 0.3.7), published by the tool repo's release run on tag v0.3.7, so the floor resolves.
- [x] Why the floor moves: the tool repo's `test_every_skill_floor_names_the_release_version`
      requires the skill to name the version it is released with; its 0.3.7 commit raises the
      floor, and this twin must match it byte for byte.
- [x] Count: `grep -c "btx-skill-jev-judge>=0.3.7" SKILL.md` is 5 on both sides, 0.3.6 is 0.
- [x] Mirror: `repo-gate.py --mirrors` reports the pair in sync after this change.
- [x] No behavioural probe arm: a version floor carries no instruction a reader could follow
      differently; the evidence is the resolve check above.
