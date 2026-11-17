# meta-claude-hooks: a Python hook handler is written with the data-architecture and performance skills

Change: item 8 in "Before you write a hook, answer these". A handler whose logic is Python (a
`.py` started through a launcher shim counts) is written and edited with
`bitranox:coding-python-data-architecture` and `bitranox:coding-python-performance-review`: a
new hook as a whole, an edit for the code it touches. Handler logic in bash follows the two bash
skills.

- [x] Decisions read first: `skill_decisions.py show meta-claude-hooks --kind rejected,removed
      --full` lists one rejected entry (a ledger file for code); it does not concern which coding
      skills a hook's author loads.
- [x] Skill type: reference; test approach: retrieval by quote-back.
- [x] RED route: text check of the skill files, because the always-loaded context on the
      authoring machine already names a data-architecture skill for Python work, so a behavioural
      baseline cannot fail honestly. `grep -n "coding-python-data-architecture\|coding-python-performance-review"`
      over the pre-change SKILL.md and `references/*.md` printed nothing.
- [x] RED probe (`opus`, pre-change items 6 and 7): "You are changing one matcher in an existing
      Python hook. Which other skills must you load, and what scope?" answered NONE.
- [x] GREEN probes (`opus` and `haiku`, 2 cells, first wording of item 8): both named the two
      skills and quoted the scope sentence; both answered that a bash handler does not take the
      Python skills.
- [x] GREEN diffed against RED in both directions: RED produced no result that GREEN lacks.
- [x] Gap closed: "the bash skills" named no skill. Item 8 now names
      `bitranox:coding-bash-clean-architecture` and `bitranox:coding-bash-reference`; both
      directories exist under `plugins/bitranox/skills/`.
- [x] Gap closed: a bash shim that starts a `.py` was not classified. Item 8 now asks whether the
      handler's LOGIC is Python and says "A `.py` started through a launcher shim counts."
- [x] Re-probe on the final text (`opus` and `haiku`, 2 cells, 3 questions): shim plus `.py` ->
      both quoted "A `.py` started through a launcher shim counts."; all-bash logic -> both
      quoted "Handler logic written in bash follows `bitranox:coding-bash-clean-architecture` and
      `bitranox:coding-bash-reference` instead."; edit scope -> both quoted "Apply both to a new
      hook as a whole, and on an edit to an existing hook to the code the edit touches." No new
      gap that changes an answer.
- [x] Gap declined: "the code the edit touches" has no stated granularity. Judgement the skill
      leaves open.
- [x] Gap declined: a handler split between real bash logic and Python. Judgement the skill
      leaves open; each sentence of item 8 names its language.
- [x] Gap declined: whether a matcher held in `hooks.json` is code. Out of scope: item 8 is about
      the handler's Python code.
- [x] Gap declined: handlers in other languages and handler types with no script. Out of scope
      for this rule.
- [x] Gap declined: whether the bash skills take the same new-versus-edit scope and timing.
      Owned by the bash skills.
- [x] Case left unstated on purpose: `references/authoring.md`, "Your handler runs with no
      dependency provisioning", prefers a standard-library handler, where a third-party model
      library is absent; item 8 takes no position on how that meets the data-architecture skill.
- [x] Mechanical check: the seven added lines are at most 99 columns in a file whose prose runs
      to about 115, backticks balanced per item, no fence added. The list is introduced by the
      heading "Before you write a hook, answer these", which carries no count. The section after
      the insertion opens with its own heading.
- [x] No address, host, path or private name added. ASCII only.
- Decisions: d-20261117-afa2c172
