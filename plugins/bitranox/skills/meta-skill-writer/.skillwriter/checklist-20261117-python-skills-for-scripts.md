# meta-skill-writer: a bundled Python script, hook or jig is written with the data-architecture and performance skills

Change: a new subsection, "A bundled Python script or hook gets the data-architecture and
performance skills", between the cross-platform section and the docstring-decisions section. It
names `bitranox:coding-python-data-architecture` and `bitranox:coding-python-performance-review`
as required sub-skills, gives the scope (new code as a whole, an edit for the code it touches)
and routes a bash script to the two bash skills. It stands as its own subsection because the
bullet list of the cross-platform section is introduced as rules that keep Windows from breaking
a script, which this rule is not.

- [x] Decisions read first: `skill_decisions.py show meta-skill-writer --kind rejected,removed
      --full` lists three rejected entries (history file, probe hand-back rule, uncited-decline
      gate); none concerns which coding skills a script's author loads.
- [x] Skill type: reference; test approach: retrieval by quote-back.
- [x] RED route: text check of the skill file, because the always-loaded context on the
      authoring machine already names a data-architecture skill for Python work, so a behavioural
      baseline cannot fail honestly. `grep -n "coding-python-data-architecture\|coding-python-performance-review"`
      over the pre-change SKILL.md printed nothing.
- [x] RED probe (`opus`, pre-change first bullet of the cross-platform section): "Which other
      skills must you load, and to how much of it do they apply?" answered NONE. Skill gaps
      reported: no skill named, no scope given.
- [x] GREEN probes (`opus` and `haiku`, 2 cells, the new subsection): both named the two skills
      and quoted "Apply both to new code as a whole, and on an edit to an existing script to the
      code the edit touches."
- [x] GREEN diffed against RED in both directions: RED produced no result that GREEN lacks.
- [x] Gap closed: "the bash skills" named no skill. The sentence now names
      `bitranox:coding-bash-clean-architecture` and `bitranox:coding-bash-reference`; both
      directories exist under `plugins/bitranox/skills/`. The same sentence form was re-probed on
      `opus` and `haiku` in the meta-claude-hooks change of this release and quoted back by both;
      this file's copy of it was checked by reading, not by a probe of its own.
- [x] Gap declined: "bundled" is not defined in the subsection. Covered elsewhere: SKILL.md,
      "Bundled scripts and hooks: keep them cross-platform", first sentence: "Any script you ship
      inside a skill or as a hook (a `.sh`, `.py`, `.js`, scripts in `scripts/`, or a hook
      command)".
- [x] Gap declined: "the code the edit touches" has no stated granularity. Judgement the skill
      leaves open.
- [x] Gap declined: whether a script that is not being edited must be brought in line. Out of
      scope for this rule, which covers writing and editing.
- [x] Gap declined: what evidence shows the two skills were applied. Owned by those two skills.
- [x] Case left unstated on purpose: this skill requires a bundled script to import in a bare
      environment, where a third-party model library may be absent; the new text takes no
      position on how that meets the data-architecture skill.
- [x] Mechanical check: the added lines are at most 97 columns, backticks balanced, no fence
      added. The section after the insertion opens with its own heading and holds no
      back-reference that re-binds.
- [x] No address, host, path or private name added. ASCII only.
- Decisions: d-20261117-8096290d
