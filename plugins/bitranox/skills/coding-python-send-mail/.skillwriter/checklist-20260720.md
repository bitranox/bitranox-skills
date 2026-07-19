# coding-python-send-mail checklist - 2026-07-20

Change: fix the Reference section. It pointed at the btx_lib_mail README and `docs/` by
package-local paths that are NOT shipped in the pip wheel (packages = src only), so they dangle on
any install. Applied the meta-skill-writer "install-reachable references" rule.

Skill type: reference (library usage).

- [x] Defect verified: `grep -nE '(docs/|README)' SKILL.md | grep -v http` showed bare package-local
      paths; the skill dir bundles no such files; the btx_lib_mail wheel excludes README/docs.
- [x] Fixed: discovery-first (`uvx btx_lib_mail --help`, `python -c "import btx_lib_mail as m; help(m)"`)
      + tag-anchored repo URLs (`blob/v1.5.0/...`) the reader re-pins to their installed version.
- [x] Re-ran the verify grep: only URL / discovery references remain, no bare package-local path.
- [x] SKILL.md still self-sufficient for the common path (reference is depth-only).
- [x] ASCII only; repo-gate --ci run before commit.
