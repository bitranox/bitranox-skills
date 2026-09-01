# skill-writer checklist - meta-dream-crosstree (the gathered-copy exemption claim is removed)

Change: one clause in the convergence section. It stated that "gathered copies are marked exempt
from re-promotion AND re-gather". No such mark is read anywhere, so the sentence promised a
property the system does not have. It is replaced by the mechanism that does provide the debounce.

## PLAN

- [x] Skill type: technique (a procedure with a stated safety property).
- [x] Test approach: coverage check against ground truth. A false safety claim is tested by looking
      for the mechanism it names, not by a pressure scenario. Recorded as the chosen route.
- [x] Scope: one clause. The contract it referred to is removed in meta-collect-knowledge's own
      change, with its own checklist.

## RED

- [x] The claim names a provenance mark. Live store: 0 facts carry a `gathered:` source. Plugin
      hooks: 0 lines read a `gathered` mark. Nothing implements the exemption the sentence asserts.
- [x] A reader acting on the old sentence would rely on a debounce that does not run, and nothing
      would report the omission.

## GREEN

- [x] The corrected sentence names `gather_scan.py`'s `gathered-topics.tsv`, which exists and is
      referenced by that script. The stated mechanism is now one that can be found.
- [x] The claim is narrowed to what is true: the file is kept out of the store so a dream does not
      tidy it away.

## REFACTOR

- [x] No replacement promise is introduced; the sentence now points at a mechanism rather than
      asserting a property.
- [x] Undecided gap list is empty.

## Quality

- [x] Present tense, no session narrative, no operator instructions, no scratch paths.
- [x] No address, MAC, hostname or machine path added by this change.
- [x] Frontmatter untouched: no `name` or `description` change, so no routing keyword moved.
