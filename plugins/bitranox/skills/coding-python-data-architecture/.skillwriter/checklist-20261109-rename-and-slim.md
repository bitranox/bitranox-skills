# skill-writer checklist - coding-python-data-architecture (2026-11-09, rename and slim)

The skill is renamed from `coding-python-enforce-data-architecture-strict` with `git mv` (its
`.skillwriter/` history and `references/validation-error-messages.md` moved with it), `name:` and
the H1 changed, and the body slimmed to the Python mechanisms. A first section, "Load
bitranox:coding-data-architecture alongside this skill", states once that the generic rules
(Core Principles 1-7, the anti-pattern list, the Instructions checklist, the Workflow STEP A-D and
its state file) live there. Kept here: the Python forms of the principles and the "What to Use
When" table, every mechanism section (str-Enum and datetime 3.10/3.11 forms, bare `BaseModel`
field, `model_dump_json()` on an existing wire, three alias settings, discriminated unions,
unions without a discriminator, `AwareDatetime`, strict `IntEnum`, str-to-Enum parameter
conversion), the Python anti-pattern code block with the NamedTuple, `model_copy` revalidation and
refusal-text paragraphs, Python additions to the Instructions checklist, Python violation
patterns, "Python tooling for the Workflow" (pyproject.toml, candidate grep, analyser patterns,
StrEnum/NamedTuple type-checker trap, STEP C commands, the PYTHONPATH and `python -I` harness
detail, STEP D greps), the example transformation, the pyright define-the-types section with all
worked examples, and the StrEnum rationalization row.

Decisions: d-20261109-a163b897

- [x] Receipt fresh, skill loaded via the Skill tool; `show
      coding-python-enforce-data-architecture-strict --kind rejected,removed --full` printed
      nothing, and the skill had no `decisions.jsonl` (no live rule anchors to keep).
- [x] Not mirrored (`MIRRORED_SKILLS` does not list it).
- [x] Heading list saved before the edit (`grep -n '^#' SKILL.md`, 33 unique lines including code
      comments such as `# BAD: Dict parameter`). Diff A, pre-edit headings missing from the
      slimmed Python skill (`comm -23 before python`):

      # Data Architecture Enforcement
      ## Execution Summary
      ## Instructions
      ## Workflow
      ### Core Principles

      Diff B, of those, missing from the generic skill too (`comm -23 A generic`):

      # Data Architecture Enforcement

      So every Python-specific heading is still in the Python skill, every moved heading is in
      `coding-data-architecture`, and the only heading in neither is the renamed H1 (now "Data
      architecture in Python").
- [x] Line-level loss check: every non-blank line of the pre-edit text was searched
      (whitespace-normalised) in the two new files; 85 were not found verbatim. Each was read:
      the front matter and H1, the principles restated without Pydantic, three re-pointed
      references, and Python lines moved into the Python sections in reworded form. Two details
      were found missing and restored: "no `Any`, no `object`" for the lookup table value type
      (Python skill) and "Any conversion that does not add value" (generic skill).
- [x] Cross-references in kept text re-pointed: "guidance above" now names "Python violation
      patterns"; "Rule 5" and "Rules 2 and 5" now read "Core Principle 5" and "Core Principles 2
      and 5"; the opening section says every Core Principle, STEP, Instructions and Workflow
      reference names the generic skill's text.
- [x] Test: `test_the_python_data_architecture_skill_holds_no_copy_of_the_generic_rules` in
      `hooks/tests/test_build_skill_docs.py` passes on the new text; the same check
      (`_defers_to_the_generic_skill`) returns False on the pre-edit text, which holds all four
      generic markers.
- [x] Retrieval probe on the two files (opus and haiku, Skill tool forbidden), seven questions:
      str-Enum f-string on 3.11+, why never `python -I`, state file and STEP A grep, Enum-keyed
      table construction, bare `BaseModel` field fix, where the DoD and workflow live, reviewer
      LGTM. Both tiers answered all seven with quotes from the right file, and both quoted the
      "Load bitranox:coding-data-architecture alongside this skill" section for Q6.
- [x] Probe skill gaps, decided:
  - "Three" (Python read-only parts) against "four" (generic conditions) for the lookup table
    (opus): CLOSED, the Python paragraph now says all four generic conditions hold and the three
    are its read-only part.
  - The module-level table grep sits only under STEP D (both tiers): DECLINED, unchanged from the
    source skill, where it was a STEP D check by design.
  - `git archive ... src` against the generic `git archive ...` (opus): DECLINED, the Python form
    is the src-layout case of the generic step.
  - Plain dataclass versus "prefer Pydantic" (opus): DECLINED, both lines are the source skill's
    text unchanged.
  - The reference file and other skills were not in the probe (both): DECLINED, outside the
    probe by construction; `references/validation-error-messages.md` ships in this skill dir.
- [x] Tiers and cells: retrieval opus x1, haiku x1.
- [x] Description: starts "Use when", triggers only, 493 characters measured with `len()`.
- [x] Width check: the added lines over 100 columns are the description and three lines carried
      verbatim from the source text; the two paragraphs this edit rewrapped are under 100.
      15 fences, all closed; no non-ASCII byte.
- [x] History-phrase finder: two hits ("previously-written state entry", "a problem you no longer
      have"), both behaviour, not history.
- [x] Every live reference to the old name re-pointed (uncapped grep, every spelling); the new
      test `test_no_live_file_names_a_retired_skill` guards it and failed with one planted
      occurrence in a scratch file under this skill dir before the file was removed.
- [x] Security review of the diff: documentation and tests only.
