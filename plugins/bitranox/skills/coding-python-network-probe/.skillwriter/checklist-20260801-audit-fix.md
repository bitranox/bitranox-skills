# skill-writer checklist - coding-python-network-probe (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled, so no finding could come from
this machine's memory store. Ships with plugin 5.125.0.

- [x] DRIFT, caught by the mirror gate rather than by a reviewer: the marketplace copy was 10 lines
      BEHIND its ipscout twin, missing `family=` on the three calls that return addresses, the
      `-4`/`-6` CLI flags, and the note that asking for a family the target lacks is an empty result
      rather than an error. Direction matters: the shop was describing an API the tool had moved
      past. Regenerated from the twin, re-applying the one by-convention divergence for this pair -
      the `name:` field (H1 is shared and neither copy carries a self-install blockquote).
- [x] Two STALE findings DECLINED with reason: the reviewer wanted version/date stamps on the
      Windows link-local-zone and connect-scan claims. Both follow from the platform API rather
      than a build number, so dating them would imply they might change, and dated provenance in a
      skill is the narrative this repo's docs rule excludes.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every finding's QUOTE was checked against the real file before acting - a reviewer's quote is
      a claim, not evidence. All quotes verified.
- [x] No finding was accepted on the reviewer's say-so where it could be executed instead.
- [x] Fix is scoped to the defect; no adjacent rewriting.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
