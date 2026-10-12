# skill-writer checklist - coding-python-new-public-library (2026-10-12, CI range 3.10-3.15)

Change: the frontmatter description's CI range moves from "Python 3.10-3.14" to "Python 3.10-3.15",
mirroring `libs/bitranox_template_py_lib/skills/new-public-python-library`. The template now carries
the `Programming Language :: Python :: 3.15` classifier, which drives both its CI matrix and
`bmk test-all`; `make test-all` passed there on 3.10 through 3.15.0.

- [x] Skill type: reference. Test approach: retrieval - can an agent answer "does a library
      scaffolded from this template get CI on Python 3.15?" from the description alone.
- [x] RED (old description, inert probe agent, haiku): answered NO, quoting "CI across Python
      3.10-3.14 on Linux/macOS/Windows".
- [x] GREEN (new description, same prompt): answered YES, quoting "CI across Python 3.10-3.15 on
      Linux/macOS/Windows".
- [x] Both arms asked for a "Skill gaps" section. Gaps reported and decided:
      - "does not say how the matrix is built (classifiers vs workflow)": DECLINED - a description
        is a trigger surface; how the matrix is derived belongs to the template's own docs.
      - "a claim about the skill, not verified against the template": CLOSED outside the text - the
        template's classifiers list 3.15 and its `make test-all` passed on 3.15.0.
      - "two listings disagree": an artifact of the probe running beside the installed older
        plugin; the shipped text after this change is the 3.10-3.15 one.
- [x] Description length measured with len(): unchanged (one digit).
- [x] `skill_triggers.json` and `docs/skills.md` regenerated; trigger map check passes.
- [x] MIRRORED skill: twin carries the identical description line.
- [x] No body line, `name:` or trigger keyword added or removed beyond the version digit.
- [x] No session narrative, machine paths, addresses or hostnames added.
