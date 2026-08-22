# skill-writer checklist - files-edit-yml (ruamel round-trips comments, not layout)

Change: correct a FALSE claim in the Library section, pin the two settings in the worked pattern,
add a "Round-tripping keeps comments, not layout" section, and add two Common mistakes rows.

## PLAN

- [x] Skill type: technique (load, edit, dump, verify). Test approach: text check of the artifact,
      because the defect is a claim the skill itself makes.
- [x] This is a CORRECTION, not an addition. The skill said ruamel "round-trips and preserves
      comments, key order, and formatting". The third item is false out of the box, and the skill's
      own verification step (re-load and assert the keys) PASSES on a fully reflowed file, so
      nothing in the documented procedure catches it.
- [x] Checked against EVERY shipped skill: `grep -rn ruamel skills/` shows
      `coding-python-use-modern-libraries` says only "round-trips comments", which is accurate and
      needs no change, and `meta-skill-writer` names ruamel as the YAML pick. files-edit-yml is the
      only place making the layout promise, so it is the only file to fix.

## RED

- [x] Behavioural RED is NOT available on this machine: `redcheck.py --corpus-cascade .` reports
      INHERITED COVERAGE naming
      `.claude-memory/facts/reference-ruamel-round-trips-comments-but-reflows-layout-unless-you-pin-indent-and-null.md`
      (6 shared terms) plus this repo's own `CLAUDE.local.md`. Route taken: TEXT CHECK of the
      artifact.
- [x] The RED that matters here is against the FILE, and it failed before the change: the Library
      section promised formatting preservation, and the worked pattern constructed a bare `YAML()`
      with no indent and no representer, so a reader following it verbatim gets the reflow.

## GREEN

- [x] Text check, all four sites: the Library bullet no longer claims layout and forward-references
      the new section; the pattern pins `yaml.indent(mapping=2, sequence=4, offset=2)` and a `None`
      representer emitting a literal `null`; the new section states both defaults and why the
      existing check misses them; the Common mistakes table gains the two rows.
- [x] Quote-back for "why the prescribed verification does not catch it": "Neither is caught by the
      re-load check above: the keys are all present and the file parses, so the `assert` passes on
      a fully reflowed document."
- [x] Quote-back for the required new step: "Pin both settings (shown in the pattern), then DIFF
      before committing and require the diff to show only what you meant to change."

## REFACTOR

- [x] The fix is in the PATTERN, not only in prose. A reader who copies the code block now gets the
      pinned settings without having read the section, which is the failure path that mattered:
      the previous prose was correct about everything it said and the code block still reflowed.
- [x] The indent triple is annotated as needing to MATCH the file rather than presented as a
      universal correct value, so a file with a different convention is not silently reformatted to
      this one.
- [x] The measured scale is kept (a two-key edit producing a 120-line diff) because it is what
      makes a reader check the diff at all; the private file it was measured on is not named.

## Quality

- [x] ASCII only, present tense, no session narrative, no machine paths.
- [x] Example path stays the existing placeholder (`traefik/dynamic/services.yml`,
      `path/to/file.yml`).

## Deliverables

- [x] `SKILL.md`: corrected Library bullet, pinned pattern, one new section, two Common mistakes
      rows. No script, so no `tests/` change.
