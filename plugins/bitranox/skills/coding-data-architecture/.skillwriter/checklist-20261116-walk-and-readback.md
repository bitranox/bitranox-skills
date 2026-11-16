# Review: malformed-shape behaviour of a replaced walk; a stored copy re-entering is a boundary

Change: two DoD items under Instructions step 1, Input/Output Boundaries:

1. a boundary model that replaced a `.get()` walk keeps what the walk did with every malformed
   shape (kept, skipped, defaulted, aborted the load), tabulated before the first edit and pinned
   in tests that pass on the old code first, unless the change is deliberate and in the CHANGELOG;
2. a check the live input path applies to a value also runs on every read-back of a stored copy
   (cache hit, HTTP 304 from an ETag cache, state read from disk), by living in the boundary
   model's validation.

Decisions: d-20261116-f69d9e84, d-20261116-e62f97d8

- [x] Ownership: both rules are language-neutral, so they live here; the Python skill states
      neither.
- [x] RED, item 1 (text check of the pre-edit file): the DoD covered the opposite direction only
      ("a faithful port passes every existing test while keeping the old bug"). STEP C item 5
      covers an input the old code accepted and the boundary now REFUSES, but its diff compares
      "exception type / exit code / last error line per input", which a silently dropped row or a
      value parsed to None does not change. The fixer-brief bullet "validate only the rows that
      survive the skip/filter decision" covers skip-versus-abort, not defaulted-versus-dropped.
- [x] RED, item 2 (text check): `grep -niE 'cache|stored|re-?enter|read.?back|304'` over the
      pre-edit SKILL.md hit only Core Principle 4 ("stored, forwarded or written back") and
      Core Principle 7 ("data already persisted"); nothing says a read-back is a boundary.
      `coding-input-sanitization` has no such line either (its stored-URL line is about storing
      the canonical origin, not re-checking on read).
- [x] GREEN quote-back, `opus` (effort medium) and `haiku`, 2 tiers x 3 questions (null field
      defaulted by the walk; HTTP-date header form; cached next-page URL on 304): both tiers
      answered each from the new items with verbatim quotes.
- [x] Fix round: `opus` reported no outcome for a walk that aborted the whole load on a
      wrong-type item; the outcome list now reads "kept the row, skipped it, defaulted the value
      or aborted the whole load". Re-probe on `haiku` (abort-to-skip question): classified the old
      behaviour as aborted and required a test plus keep-or-CHANGELOG, quoting the new list.
- [x] Skill gaps reported and decided:
      - other falsy values (`0`, `""`) under `or False`: declined, the shape list is examples and
        the rule is per shape the walk sees.
      - which value an HTTP-date Retry-After should parse to: declined, a protocol question; the
        rule is keep-or-list.
      - "step 3" / "STEP C item 5" not in the excerpt: declined, both exist in the whole skill
        (Instructions step 3; STEP C item 5 at SKILL.md:463).
      - how to run "passes on the OLD code" once the tree changed: covered elsewhere, SKILL.md:485
        "`git archive <HEAD or tag> | tar -x -C <tmpdir>`".
      - what a CHANGELOG listing must hold: covered elsewhere, SKILL.md:500 "listed in the
        CHANGELOG with the input, the old result and the new one".
      - cache entries written before the check existed: declined, parsing every read-back through
        the model refuses them on read.
      - logging skipped rows: declined, out of scope for this item.
- [x] Width, fence and non-ASCII check over the added lines after each fix round: no problems;
      the paragraph after the insertion ("**Internal Data Handling:**") reads unchanged.
