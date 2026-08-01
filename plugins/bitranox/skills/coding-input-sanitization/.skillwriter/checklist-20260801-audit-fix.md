# skill-writer checklist - coding-input-sanitization (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit` - one reviewer per skill, in
a copy of the plugin outside the knowledge tree with recall walled, so no finding could come from
this machine's memory store. Ships with plugin 5.125.0.

- [x] WRONG, and the most serious of the sweep: the skill taught that
      `Path(base, name).resolve()` "stays under `base.resolve()`". Reproduced in Python -
      `Path('/tmp/safebase', '../../etc/passwd').resolve()` gives `/etc/passwd`, and an absolute
      component discards the base entirely. A reader implementing exactly the documented check gets
      a traversal defence that does not defend. Now resolves THEN verifies containment with
      `is_relative_to`, and the anti-pattern column names both escapes.
- [x] WRONG: `shlex` was listed under the Bash reference skill. Confirmed absent from
      `coding-bash-reference` (0 occurrences) - it is Python's stdlib and the skill already uses it
      correctly for the Python shell sink. Re-attributed.
- [x] Checked that no other traversal guidance exists in the skill: that one table row is the whole
      treatment, which is why it had to be right.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every finding's QUOTE was checked against the real file before acting - a reviewer's quote is
      a claim, not evidence. All quotes verified.
- [x] No finding was accepted on the reviewer's say-so where it could be executed instead.
- [x] Fix is scoped to the defect; no adjacent rewriting.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
