# checklist - a stored copy of an outside value coming back in is a boundary

The APPLIES list gains a stored copy of an outside value re-entering (a cache hit, an HTTP 304
served from an ETag cache, state or a next-page URL read back from disk), and the quick checklist
a line for it. The fix itself is structural and lives in bitranox:coding-data-architecture's
Definition of Done (the check sits in the boundary model every read-back passes through); this
skill points there instead of restating it.

Decisions: d-20261116-98703d7c

## RED

- [x] Skill decisions read first: no rejected or removed entries.
- [x] Text check on the pre-edit SKILL.md: `grep -ciE "read-back|cache hit|304|stored copy|comes
      back in"` = 0. The only stored-value lines (the canonical origin, the checklist line under
      URL host checks) are about what to store, and "DOES NOT APPLY - internal seams" can be read
      as "a cached value is trusted".
- [x] Source of the lesson: the coding-data-architecture fixer's report of a cached next-page URL
      on a 304 skipping the host check the live 200 path applied (inherited, a review finding).

## GREEN

- [x] The APPLIES bullet names the three shapes and points at the data-architecture DoD item
      (coding-data-architecture SKILL.md, Definition of Done list), which exists on this branch.
- [x] The quick checklist line asks the same question in one line.
- [x] ASCII only; bullet indentation matches its neighbours.
