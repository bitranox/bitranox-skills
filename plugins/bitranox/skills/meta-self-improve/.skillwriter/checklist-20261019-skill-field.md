# skill-writer checklist - meta-self-improve (2026-10-19, skill field)

Change: step 2 says a fact written beside a fix queued against a skill passes `--skill <name>` to
the engine `add`, and that the field is the record; the step-4 command and the deliverables box
show the flag. `references/memory-backend.md` documents `--skill`.

- [x] Skill type: technique - tested with an application scenario (write the engine command for a
      fact written beside a queued compuse-git fix).
- [x] RED (step 2 as it stood, with the flag documented beside it): haiku passed `--skill`, but
      named the skill in the body as well and reported it could not tell whether the body, the
      field or both must carry the tie - the old sentence said "name the queued skill in the
      fact's body".
- [x] GREEN (new sentence): haiku passed `--skill bitranox:compuse-git`, answered that the body need
      not name it with a direct quote ("the field is the record, the body need not repeat it"),
      and for a release check learned under devops-bmk wrote no fact, quoting the deciding line.
- [x] Lost-result diff: the RED arm's flag use survives in GREEN; nothing missing.
- [x] Skill gaps, declined: `<plugin>`/tmpfile placeholders, case definitions and hook caps were
      outside the excerpt by construction; whether `--skill` takes the prefixed form is answered by
      the example and by the engine's validator.
- [x] Engine: 18 tests written first, all RED before the change (16 at first run, 2 bridge cases
      added after); all pass with it, and 173 pass across the engine, bridge and hook-file suites.
- [x] Description unchanged, so skill_triggers.json and the docs catalogue need no regeneration.
- [x] Reference table row edited within its existing column width; no other row re-padded.
- [x] Security: the value lands in frontmatter, so it is validated with fullmatch on lower-case
      classes (no newline can inject a key); no secrets, hosts or private paths added.
