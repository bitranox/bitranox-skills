# skill-writer checklist - coding-python-pwshpy (a description that is not valid YAML)

Change: the front-matter `description:` is a plain YAML scalar carrying `: `, which makes the
whole block parse as a nested mapping instead of a string, so the front matter is not valid YAML.
`prefer pwshpy instead: a genuinely Pythonic PowerShell` becomes `instead - a genuinely`.

## PLAN

- [x] Skill type: reference. The change is mechanical - a YAML-correctness fix to one field - so
      the test approach is a failing check over the real file, not a subagent pressure scenario.
      The skill-writer rule that mechanical constraints belong in automation rather than prose is
      what decides this: the defect is regex-detectable, so it earns a gate, not a paragraph.
- [x] Scenario drafted before editing: run a real YAML parser over the front matter of every
      shipped skill and require it to load as a mapping whose `description` is a string.
- [x] Scope: the `description:` value only. No body change, no supporting files, no `name:` change.

## RED

- [x] One breaking colon, at offset 156 of a 615-character description. `yaml.safe_load` over the front-matter block raises
      `mapping values are not allowed here` and names the exact column.
- [x] The defect is invisible to every existing check: `frontmatter_problems()` returns no entry
      for this file, and `frontmatter_name()` / `frontmatter_description()` both recover the intended
      value, because each reader is a regex over `text.split("---", 2)[1]` rather than a YAML parse.
- [x] Tests written before the fix and watched to fail:
      `test_frontmatter_scalar_colon_spots_an_unquoted_colon_space` and
      `test_frontmatter_problems_flags_a_colon_that_breaks_the_yaml` both error with
      `AttributeError: module 'harness_checks' has no attribute 'frontmatter_scalar_colon'`.

## GREEN

- [x] The reword lands and `yaml.safe_load` accepts the block. Swept across all 81 shipped skills
      and their 10 mirrored twins: 91 files, 0 invalid.
- [x] `frontmatter_scalar_colon()` added to `harness_checks.py` and wired into
      `frontmatter_problems()`. Run against the real skills directory before the fix it named
      exactly the three affected skills and nothing else - the case the check was built for, and 78
      known-good files as the control.
- [x] Router keywords preserved: `build_skill_triggers.py` regenerates `skill_triggers.json`
      byte-identical, so the distilled triggers this skill routes on are unchanged by the reword.

## REFACTOR

- [x] Gap "does ` - ` corrupt a colon that is part of quoted content?" - CLOSED for the one place it
      arises. A quoted log string is reworded rather than dash-substituted, because
      `"blocked - <module>"` would misquote what the tool actually prints while
      `logs the module as "blocked"` keeps the searchable keyword and stays true.
- [x] Gap "should the checker just parse YAML?" - DECLINED. A hook gets a bare interpreter with no
      dependency provisioning, so a hard `import yaml` would fail open and silently check nothing.
      The shipped check is a stdlib structural rule over plain scalars, which needs no library and
      cannot degrade to a false pass.
- [x] Quoted and block scalars are exempt from the new check, since the colon is inside the quoting
      there; the CSO rules already reject those styles for a description on separate grounds.
- [x] Length re-measured after the edit: 616 characters, under the 1024 cap the commit gate
      enforces.

## Quality

- [x] ASCII only across the whole file, verified after editing. No em-dashes, no curly quotes.
- [x] No address, MAC, hostname or machine path added - verified over the file, zero hits.
- [x] Present tense, no session narrative, no record of how the field read before this change
      beyond the one line naming the substitution, which is the change itself.
- [x] Description still states triggers only and summarises no workflow.

## Deliverables

- [x] `SKILL.md` front-matter `description:`, applied.
- [x] `harness_checks.py` gains `frontmatter_scalar_colon()` and `frontmatter_second_block()`, both
      wired into `frontmatter_problems()`, with sibling tests in
      `hooks/tests/test_harness_checks.py`.
- [x] `docs/skills.md` regenerated from the new descriptions.
- [x] Version bumped in `plugin.json`; the three description fixes and the gate ship under the same
      number.
