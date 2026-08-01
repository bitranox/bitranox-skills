# skill-writer checklist - coding-python-clean-architecture (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled, so no finding could come from
this machine's memory store. Ships with plugin 5.125.0.

- [x] WRONG: the canonical `Account` entity was `@dataclass(slots=True)` with mutating
      `withdraw`/`deposit`, in a skill stating "no mutable state in the domain is a non-negotiable".
      The canonical example is what readers copy, so the contradiction ships as practice. Entity is
      now `frozen=True`, its methods return a new `Account` via `replace`, and the one call site
      rebinds.
- [x] WRONG: `UnitOfWork.run()` in SKILL.md omitted `timeout`, which `port-contracts.md` defines -
      the file SKILL.md itself names as the source for the standard port definitions. Signatures
      now agree.
- [x] WRONG: `script-mode.md`'s flagship example returns exit code 1, absent from that file's own
      exit-code table. Added as "Check ran, result negative" rather than changing the example,
      since a negative check result is a real outcome distinct from the error codes.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every finding's QUOTE was checked against the real file before acting - a reviewer's quote is
      a claim, not evidence. All quotes verified.
- [x] No finding was accepted on the reviewer's say-so where it could be executed instead.
- [x] Fix is scoped to the defect; no adjacent rewriting.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
