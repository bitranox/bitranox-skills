# skill-writer checklist - meta-dream-tree (2026-09-04, a pinned fact's kind is reachable)

Change: the `factedit.py` clause in the Reference-files tool paragraph is corrected. It said
`--type` is "refused on a pinned fact, whose `amend-pinned` verb has no such flag"; it now says a
PINNED fact is included, because `amend-pinned` carries `--type` and is the only route to a pinned
fact's kind, since `add` refuses a pinned entry outright. No frontmatter change.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Skill type: REFERENCE. The clause is an index entry, so the test that applies is whether what
      it says is TRUE of the shipped tools.
- [x] The correction is required, not cosmetic: as shipped in 6.3.0 the clause was accurate about
      the code and the code was wrong. `--type` existed only on `add`, `add` raises `PinnedEntry`,
      and `amend-pinned` accepted no `--type`, so `factedit`'s refusal message directed the reader
      to "re-type it with the engine directly", a route that did not exist. Verified against the
      6.3.0 source before the fix, not inferred from the message.
- [x] The defect was not visible from the change that introduced it. The refusal was correct about
      `amend-pinned` at the time, its test asserted exactly that refusal and passed, and the whole
      gate was green - so the surrounding evidence agreed with a message that could not be followed.
      What surfaced it was asking whether the route the message names exists.
- [x] ACCURACY of the corrected clause, pinned by tests that fail against the pre-change source:
      `amend_pinned_entry` keeps the stored type when none is given; it changes the type when one
      is given and leaves `pin` set; and `factedit apply --type` on a pinned fact now FORWARDS,
      reaching the engine as `amend-pinned` with `--type`, where the previous test asserted a
      refusal.
- [x] Forwarding was chosen over a corrected refusal. A refusal with an accurate message would have
      documented the dead end rather than removed it, and 6.3.0 had just closed the only accidental
      way a pinned fact's kind could change - so the fact most in need of a correct kind would have
      been the one that could never get one.
- [x] Scope of the new flag, stated because the pin gate exists to stay narrow: `amend-pinned` is
      already the one deliberate way through for a pinned fact's title and content, and `--type`
      joins those on the same verb. Nothing else gains a route, and `add` still refuses a pinned
      entry.
- [x] No frontmatter change: 0 frontmatter lines in the committed diff for this file, so no routing
      keyword moved.
- [x] Scripts ship with tests that pass: 151 in this skill's `tests/`, and the whole-repo gate is
      green.
- [x] Present tense, no session narrative, no machine-specific address or path added.
