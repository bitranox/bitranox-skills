# skill-writer checklist - python-network-probe (2026-10-26, documentation addresses)

Change: three example lines (`find-ip`, `arp-scan`, `scan-ports` in the CLI block) move from
values taken from a real network and private-range placeholders to RFC 5737 / RFC 7042
documentation values. No rule, trigger, description or instruction changes.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The change is example values only, so the test is whether the shipped
      text still carries a value that names a real network.
- [x] Inherited-context check: `redcheck --corpus-cascade` reports STRONG inherited coverage, and
      the cascade does state the lesson (a memory index line: use reserved documentation ranges,
      never values a terminal showed). A behavioural arm cannot fail honestly, so the evidence is a
      text check of the skill file, pre-edit against edit.
- [x] RED (text): the pre-edit SKILL.md has 3 lines matching the non-documentation pattern
      (`dc:b2:2f:44:34:59|192\.168\.[0-9]+\.[0-9]+|10\.0\.0\.[0-9]+|aa:bb:cc:dd:ee:ff|4b42:61c4`),
      against 37 lines naming `ipscout` as the control that the grep read the file.
- [x] GREEN (text): the edited SKILL.md has 0 such lines, the control still 37.
- [x] The address check from "An example from a real scenario is not a real address" finds no
      value outside the documentation ranges, loopback, the public resolver targets and the RFC
      7042 `02:00:5e:10` range.
- [x] Twin parity: both copies carry the same set of IPv4 literals with the same counts.
- [x] Describes the latest release only: the change adds no prose, so no history line is added.
- [x] No session narrative or private provenance in the skill or this artifact.
- [x] Gaps: none reported - no probe was dispatched, since the inherited cascade makes a probe's
      answer uninformative here; recorded as the route above rather than as a pass.
