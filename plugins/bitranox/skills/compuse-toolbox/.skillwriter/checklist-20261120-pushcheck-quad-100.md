# checklist - pushcheck: Tailscale's resolver 100.100.100.100 is not a finding

One queued contribution, delivered in part. pushcheck flagged 100.100.100.100 as private_ip because
it lies inside CGNAT 100.64.0.0/10; it is the same on every tailnet and names no machine, so it now
joins the documentation-safe values (module docstring, `_WELL_KNOWN_ADDRESSES`, SKILL.md row). Not
delivered: "any value already present on the pushed default branch is a notice" - that is a policy
change for every finding kind, left for a decision.

Decisions: none - extends the existing documentation-safe list; the policy half is not delivered

## RED

- [x] Measured before the change: `scan_text("nameserver 100.100.100.100")` gave one private_ip.
- [x] New test KILLED by mutation_arm with the `_WELL_KNOWN_ADDRESSES` check removed.

## GREEN

- [x] 90 tests pass in tests/test_pushcheck.py; a node address (100.101.7.12) and the neighbour
      100.100.100.101 are still findings.

## REFACTOR

- [x] Table re-padded by the formatter; ASCII check clean.
