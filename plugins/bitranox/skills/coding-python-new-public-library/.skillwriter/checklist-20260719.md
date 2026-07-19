# skill-writer checklist - coding-python-new-public-library (2026-07-19, new skill)

Change: NEW reference/technique skill. Teaches scaffolding a new public bitranox Python
library from the bitranox_template_py_lib template (clone, rename via the shipped
rename_dry.sh/rename.sh, fresh git init on main), installing it, using its rich-click CLI
and library API, and developing/releasing it with bmk. Also flags that a repo which ships a
skill is a marketplace (protect the branch, bump the plugin version).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] Skill type identified: reference/technique (how-to). Test approach: retrieval/application.
- [x] RED baseline: a sonnet subagent, WITHOUT the skill, was asked to scaffold a new public
      lib. It invented `./rename.sh lib_wombat` (the script takes NO arg - the word is
      ignored), skipped the shipped `rename_dry.sh` preview, and hand-rolled `rm -rf .git`
      instead of the intended flow. (It did get `main` and "do not edit .github/*" from
      ambient memory.)
- [x] GREEN: same scenario WITH the skill. The subagent ran `rename_dry.sh` first, then
      `rename.sh` with NO argument (explicitly noted the arg is ignored), used `main`, and
      left `.github/*` untouched. All three baseline failures fixed; no new rationalization.
- [x] REFACTOR: the three failures are pinned in the Common mistakes table as explicit
      counters (rename arg, skipping the dry-run, git init on master).
- [x] Name: `coding-python-new-public-library` - top-level prefix `coding` is in
      skill-taxonomy.json; sub `python`; verb/trigger-style name part.
- [x] CSO description: trigger-first ("Use when creating or scaffolding a NEW public bitranox
      Python library..."), single-line plain scalar, well over 3 distinctive keywords
      (scaffold, template, rename-project, bmk, make release, uv pip install).
- [x] Self-contained: names the template repo by URL; no dependency on local files. No
      bundled scripts, so no tests required (check_tests_exist n/a).
- [x] Security scan: prose + generic example commands (lib_wombat, example package names);
      no secrets, no private hosts/IPs/paths.
- [x] Token budget: reference skill, body is a lean scaffold-install-use-release sequence
      plus a mistakes table; no supporting files needed.
- [x] Registry: `coding-*` grouping in meta-using-bitranox-skills already covers it
      (per-skill listing is not enforced; category exemplars only).
- [x] Version: plugins/bitranox/.claude-plugin/plugin.json bumped 5.91.0 -> 5.92.0 (MINOR, new skill).
- [x] Trigger map rebuilt (build_skill_triggers.py) and repo-gate.py run clean before commit.
- [x] Mirrored: identical body ships in the source repo bitranox_template_py_lib at
      skills/new-public-python-library/ (repo copy keeps its own name, per the mirror convention).
