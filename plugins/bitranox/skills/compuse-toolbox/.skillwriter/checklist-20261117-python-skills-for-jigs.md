# compuse-toolbox: a jig's Python code is written with the data-architecture and performance skills

Change: one paragraph in "Building or enhancing a jig" naming
`bitranox:coding-python-data-architecture` and `bitranox:coding-python-performance-review` as
required sub-skills for writing or editing a jig, with the scope (a new jig as a whole, an edit
for the code it touches) and the bash launcher routed to the two bash skills.

- [x] Decisions read first: `skill_decisions.py show compuse-toolbox --kind rejected,removed
      --full` lists three rejected entries (code ledger file, ci_wait verdict line, gate --name
      help); none concerns which coding skills a jig's author loads.
- [x] Skill type: reference; test approach: retrieval by quote-back.
- [x] RED route: text check of the skill file, because the always-loaded context on the
      authoring machine already names a data-architecture skill for Python work, so a behavioural
      baseline cannot fail honestly. `grep -n "coding-python-data-architecture\|coding-python-performance-review"`
      over the pre-change SKILL.md printed nothing.
- [x] RED probe (`opus`, pre-change section text): "Which other skills must you load first, and
      to how much of the jig's code do you apply them?" answered NONE. Skill gaps reported: no
      skill named, no scope given.
- [x] GREEN probes (`opus` and `haiku`, 2 cells, changed section text): both named the two skills
      and quoted "Apply both to a new jig as a whole, and on an edit to an existing jig to the
      code the edit touches."
- [x] GREEN diffed against RED in both directions: RED produced no result that GREEN lacks.
- [x] Gap closed: "the bash skills" named no skill. The sentence now names
      `bitranox:coding-bash-clean-architecture` and `bitranox:coding-bash-reference`; both
      directories exist under `plugins/bitranox/skills/`. The same sentence form was re-probed on
      `opus` and `haiku` in the meta-claude-hooks change of this release and quoted back by both;
      this file's copy of it was checked by reading, not by a probe of its own.
- [x] Gap declined: "the code the edit touches" has no stated granularity (lines, function,
      callees). Judgement the skill leaves open.
- [x] Gap declined: whether a jig that is not being edited must be brought in line. Out of scope
      for this rule, which covers writing and editing.
- [x] Gap declined: what evidence shows the two skills were applied. Owned by those two skills.
- [x] Case left unstated on purpose: a jig that must import in a bare environment cannot rely on
      a third-party model library; the text takes no position on it.
- [x] Mechanical check: the six added lines are 83 to 97 columns, backticks balanced, no fence
      added. The paragraph after the insertion ("When a hook or jig settles a choice ...") holds
      no back-reference that re-binds.
- [x] No address, host, path or private name added. ASCII only.
- Decisions: d-20261117-936e0485
