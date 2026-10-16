# skill-writer checklist - coding-input-sanitization (2026-10-16, fold23)

- [x] Change: the "Bound length and size" bullet now says a whole-document or request-body cap does
      not bound any single field inside it; every text field on a boundary model gets its own
      `max_length` and every collection an item-count bound, at least where the field reaches
      parsing, formatting or allocation; a field only compared for equality needs none.
- [x] Receipt held (coordinator ran skill_receipt.py start meta-skill-writer); this agent loaded
      the skill
- [x] RED (text check of the artifact): before this edit the bullet listed "Max string length" and
      "request-body size" side by side; the verifier found nothing saying a document ceiling leaves
      each field unbounded, no per-field bound rule, no failure mode and no equality-only exception.
      Behavioural RED replaced on purpose because the rule is in the always-loaded memory index of
      the authoring machine (inherited coverage)
- [x] GREEN quote-back (fresh-context verifier, answered from skill files only): per-field bound
      -> SKILL.md:39-43 "A whole-document or request-body cap does NOT bound any single field
      inside it: ... So give every text field on a boundary model its own `max_length` and every
      collection an item-count bound, at least where the field reaches parsing, formatting or
      allocation (a field only compared for equality needs none)." Scenario (64 MB file cap, plain
      `str` id that is int-parsed, hex-reformatted and walked per character) -> not bounded enough;
      give that field its own `max_length`. Step-4 scan of SKILL.md: no non-ASCII punctuation, no
      private hosts or paths, no memory/session mentions.
- [x] Gaps closed or declined: none blocking. Cosmetic only: SKILL.md:42 runs past the file's wrap
      width (the trailing "For the wider ..." sentence was not re-wrapped).
- [x] Description measured: unchanged (538 characters)
- [x] Security scan: prose only, no secrets, hostnames, paths or PII
