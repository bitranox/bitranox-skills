# skill-writer checklist - write-humanize-en (2026-07-17, both procedural lists run the mandatory script; tell examples preserved in code spans)

Change: The mandatory 'run this first' deterministic pass appeared in NEITHER procedural list ('Your Task' and
'Process'), so an agent following either skipped it. Separately the tell-sweep hook blocked the file on
pre-existing tells - and inspection showed a past strip had already flattened the curly-quote example into
'curly quotes ("...") instead of straight quotes ("...")', two identical halves teaching nothing.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read both lists against the 'run this first' section - neither mentions the script; and read line
      330, where both sides of the curly-vs-straight contrast were already identical ASCII
- [x] GREEN: the script run is now step 1 of both lists; prose tells fixed to ASCII; every teaching example
      moved into a code span/fenced block (which the hook skips), restoring the flattened example and
      making the characters survive a future strip; the mechanism is documented in the pass section
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
