# skill-writer checklist - meta-adopting-external-skills (license gate reads every id; exit codes)

Change: one paragraph added to Step 2 stating what the helper's license gate now does (every
declared id counts, one copyleft id anywhere rejects, an unrecognised LICENSE text or id stops it
for a human) and its exit codes (0 adopted, 1 gate stopped it, 2 error).

- [x] Skill type: reference/technique. The defect class is a factual claim about the helper, so the
      RED is a ground-truth check against the code, not a pressure scenario. This skill is
      installed on this machine, so a behavioural probe would answer from the shipped wording.
- [x] RED (measured on the pre-fix helper): a GPL-3.0 package.json plus an MIT SPDX header was
      ACCEPTED as MIT; a proprietary LICENSE plus an MIT SPDX header was ACCEPTED with the
      proprietary text recorded as "MIT License text"; the verdict between an MIT and a GPL SPDX
      file depended on walk order; every error exited 1, the same code as a gate refusal.
- [x] GREEN: `tests/test_adopt_skill.py` pins each case (`test_a_gpl_manifest_beats_an_mit_spdx_header`,
      `test_a_proprietary_license_file_is_not_overridden_by_an_mit_spdx_header`,
      `test_any_gpl_spdx_header_rejects_whatever_the_walk_order` in both orders,
      `test_an_unrecognised_declared_id_needs_a_human`,
      `test_the_license_gate_stop_exits_one_and_an_error_exits_two`), and the new paragraph
      states exactly those outcomes.
- [x] The Step 1 policy text (accept the permissive family, reject copyleft and proprietary, never
      assume MIT) is unchanged; the helper now enforces it where it previously could not.
- [x] Present tense, no session narrative, no machine paths added.
- [x] Frontmatter untouched: no `name` or `description` change.
