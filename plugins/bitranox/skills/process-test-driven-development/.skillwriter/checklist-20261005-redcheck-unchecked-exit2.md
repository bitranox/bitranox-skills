# skill-writer checklist - process-test-driven-development (2026-10-05, redcheck unchecked -> exit 2, D-12/D-11)

The redcheck exit table's "3 = unchecked" row removed; row 2 ("usage or IO error") now also
covers unchecked, distinguished by `data.unchecked`; the paragraph explaining why unchecked is
its own outcome moves from "Exit 3" to "exit 2, with `data.unchecked` true".

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test approach: retrieval - one question answered with a direct quote
      or NONE.
- [x] RED (pre-change text, pasted): "If `redcheck.py`'s corpus assembles 0 documents, what exit
      code does it give, and how would `--json` distinguish that from a usage error?" - direct
      quote of the OLD text: exit 3, with no stated `--json` field (the old table lists exit 2
      for "usage or IO error" and exit 3 for "unchecked" as SEPARATE codes, so the question's
      second half had no answer in the old text).
- [x] Verified against `redcheck.py` source: "Unchecked is 'could not answer', so it shares
      EXIT_ERROR's code; data.unchecked keeps it apart" and `elif result.unchecked:` returning
      the same code as the usage/IO branch - matches the new text exactly.
- [x] GREEN (new text pasted): same question now answers with a direct quote ("usage or IO
      error, or unchecked... `data.unchecked` tells them apart").
- [x] GREEN diffed against RED in both directions: nothing removed (the merged row keeps both
      original meanings), the stale code and the missing JSON-field answer both closed.
- [x] Description unchanged - no routing keyword moved.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
