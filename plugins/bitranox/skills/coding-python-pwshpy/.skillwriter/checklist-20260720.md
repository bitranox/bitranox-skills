# coding-python-pwshpy checklist - 2026-07-20

Change: fix the "Further reading" table. It listed the pwshpy repo docs by bare filenames
(`docs/cli-reference.md`, `COMMANDS.md`, ...) and told the reader to "use the Read tool if present
locally" - dangling on any machine that installed the skill (the docs are not shipped in the wheel).
Applied the meta-skill-writer "install-reachable references" rule.

Skill type: reference (tool usage).

- [x] Defect verified: table rows were bare package-local paths; the skill dir bundles no such files.
- [x] Fixed: discovery-first (`uvx pwshpy --help`, `python -c "import pwshpy; help(pwshpy)"`) + a
      default-branch base URL `github.com/bitranox/pwshpy/blob/master/<path>` (latest, matches the
      uv-installed version); table lists paths under that base.
- [x] Re-ran the verify grep: remaining `docs/` hits are rows under the stated pinned base URL, not
      bare "read it locally" references.
- [x] SKILL.md still self-sufficient for the common path.
- [x] ASCII only; repo-gate --ci run before commit.
