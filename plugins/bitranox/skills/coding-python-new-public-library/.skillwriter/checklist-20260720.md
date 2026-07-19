# coding-python-new-public-library checklist - 2026-07-20

Change: fix the Reference section. It pointed at the template repo's docs by bare `docs/*.md` paths -
dangling on any machine that installed the skill (those files ship with the TEMPLATE repo, not the
skill). Applied the meta-skill-writer "install-reachable references" rule.

Skill type: reference (workflow around a template repo).

- [x] Defect verified: bare `docs/installation.md` etc. paths; the skill dir bundles no such files.
- [x] Fixed: tag-anchored template-repo URL
      `github.com/bitranox/bitranox_template_py_lib/blob/v1.1.2/docs/` the reader re-pins to the
      template release they scaffolded from, and a note that a repo generated FROM the template
      carries these files locally (so `docs/...` resolves inside the new project).
- [x] Re-ran the verify grep: only URL references remain (plus the correctly-local note).
- [x] SKILL.md still self-sufficient for the common path.
- [x] ASCII only; repo-gate --ci run before commit.
