# skill-writer checklist - meta-skill-writer (2026-08-01, hook hard cap refuses)

Change: four words in the durable-state section. The engine is described as enforcing "tree-unique
slugs and the 500-char hook cap" where it previously listed only the slug rule. Ships with plugin
5.120.0.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] The section's purpose is to tell an author writing a NEW skill what the memory engine
      guarantees so they do not hand-roll a backend. It listed the guarantees the engine enforces
      and omitted the one that can now fail their write, which would surface to them as an
      unexplained exit 1 from a command the skill told them was safe to call.
- [x] Verified against the shipped code before claiming it: `add_or_update_entry` enforces both -
      `SlugCollision` for a slug already owned in the tree, `HookTooLong` past 500 chars.
- [x] Scoped deliberately to a claim, not a procedure. The full mechanics (the atomicity, the
      `! refused:` output, what to do about it) live in `meta-self-improve`'s
      `references/memory-backend.md`, which this section already names as the storage spec to
      cross-reference rather than restate. Restating them here would duplicate a rule that has one
      home.
- [x] No session narrative, no private provenance, no machine values added.
- [x] Word count unchanged in practice; this remains a hub skill whose body is an index.
