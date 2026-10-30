# Review checklist: meta-skill-writer, queued contribution (2026-10-30)

Entry covered: after editing a SKILL.md front matter, parse it with a real YAML loader; a `: `
inside the plain-scalar description makes the block invalid YAML while regex readers recover the
value and report nothing. Edit: the Deployment checklist line "Verify frontmatter parses: `head -5
SKILL.md`" now gives a runnable loader command and the colon-space trap.

## Evidence

- [x] Claim run: `yaml.safe_load('description: Use when drive C: will not extend, or X')` raised
      `ScannerError: mapping values are not allowed here`; `drive C - will not extend` and
      `ratio 3:1` parsed.
- [x] The command exactly as written in the checklist line was extracted from the file and run:
      on a front matter with `drive C will not extend` it printed `['description', 'name']`, rc 0;
      on `drive C: will not extend` it failed, rc 1, with the caret under the colon.
- [x] RED as a text check on the pre-edit file: `safe_load|real YAML loader` 0 hits; the old line
      said only "confirm `---` delimiters and valid YAML" after `head -5`. After: 2.
- [x] GREEN probe (`bitranox:baseline-probe`, haiku, the new checklist line pasted): asked what to
      do after adding "C: will not extend" with a passing regex length check, it quoted "Verify
      frontmatter parses with a real YAML loader after every edit to it, never by eye", ran the
      command in its plan and reworded to `drive C will not extend`.
- [x] Skill gaps: "other front matter fields" - declined: this skill supports only `name` and
      `description` (SKILL.md Structure section).
- [x] Width check: the added command line is 205 columns. Declined to wrap: a shell command
      cannot be broken inside a checklist item without changing it, and the neighbouring
      checklist lines already exceed 100 columns (115 lines in the file do).
- [x] ASCII only; front matter of this skill parses with the same command; tables canonical.
- [x] No private paths, hosts or names.
