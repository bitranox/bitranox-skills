# skill-writer checklist - meta-dream-tree (2026-09-02, statusrot and factedit)

Change: the Reference files section gains a paragraph naming the five tools this skill ships, two
of which arrive with this change - `statusrot.py` and `factedit.py`, migrated out of a personal
toolbox. No frontmatter change, so no routing keyword moved.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session)
- [x] Skill type: REFERENCE (the paragraph is an index entry, not a rule), so the test is whether a
      reader can find the tool and whether what the paragraph SAYS about it is true.
- [x] The paragraph's claims were checked against each tool's own behaviour, not against memory of
      it. That check found a defect: the first draft said `statusrot` "reports CANDIDATES, never
      verdicts", and the tool's own docstring says a hit is a candidate WITH ONE EXCEPTION - "a
      slug saying 'blocked' under a hook" saying otherwise is a self-contradiction, and
      `Exit codes: 0 = no self-contradictions, 1 = at least one`. The absolute was wrong and is
      now stated with its exception.
- [x] `factedit`'s claim likewise checked against `factedit.py --help`, which describes `show`,
      `check` and recomposition through the engine; the paragraph now says the guard denies a
      direct Write or Edit, which is why the engine is the path, rather than asserting a bare
      "only path".
- [x] Retrieval is served by the compuse-toolbox index too: both tools have a row there pointing at
      `../meta-dream-tree/`, the convention that skill already uses for `wtclean`, `redcheck` and
      `claudemd_variance`. The RED/GREEN retrieval arms for those rows are recorded in
      `compuse-toolbox/.skillwriter/checklist-20260902-four-migrated-tools.md`.
- [x] The PreToolUse nudge resolves both tools to this skill and names it: `_tool_invocation`
      returns "the shipped `bitranox:meta-dream-tree` skill" for each. That required a resolver fix
      - it globbed `*/scripts/<tool>.py` only, and this skill keeps its tools at the skill root, so
      a rule naming either one resolved nowhere. Silence is indistinguishable from having no rule,
      so nothing would have reported it; a test now covers the root layout and the owner name.
- [x] No frontmatter change: `git diff` shows no `description:` line for this file, and
      `build_skill_triggers.py --check` reports the map in sync (82 skills).
- [x] Scripts ship with tests that pass: `tests/test_statusrot.py`,
      `tests/test_statusrot_baseline.py` and `tests/test_factedit.py` moved with the tools, 69
      cases green in their new home. Their subprocess tests resolved the tool through a hard-coded
      `tools/` path that does not exist here; they now resolve it from the imported module, which
      is layout-independent. Before that fix the failure surfaced as the CLI exiting 2, not as a
      missing file.
- [x] Present tense, no session narrative.
