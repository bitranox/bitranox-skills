# skill-writer checklist - meta-memory-settings (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.128.0.

- [x] WRONG, and fixed in the CODE rather than the doc: the skill said "the CLI validates keys and
      value types". Measured - `settings.py set dream_mode notarealvalue` exited 0 and wrote the
      literal string, and `set nudges banana` silently became False, because any word outside the
      true-list coerced to false. A typo like `dream_mode of` therefore produced a config every
      reader silently falls back to a default on.
- [x] `ENUM_CHOICES` now pins the five enum knobs and bools accept only the usual spellings; an
      unknown value is refused with exit 2 and a message naming the legal choices. 7 tests written
      FIRST and observed failing, then passing: 16 pass.
- [x] WRONG: `skill_placement` was documented as controlling where a new skill lands. Grep shows it
      is read by no shipped code - only `DEFAULT_CONFIG` and this table. Relabelled ADVISORY, with
      what the authoring skills do by convention, rather than deleting a key existing configs hold.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, re-issued this session).
- [x] Every QUOTE checked against the real file; every behavioural claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths added.
