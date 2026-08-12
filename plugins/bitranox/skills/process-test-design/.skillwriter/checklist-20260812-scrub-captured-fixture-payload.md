# skill-writer checklist - process-test-design (2026-08-12, scrub captured-artifact payload before it becomes a fixture)

- [x] Change: added a new section "Scrub a captured artifact fully before it becomes a fixture"
  after "Adversarial inputs at the boundary" and before "Deterministic and order-independent". A
  header-level scrub of a committed capture/log/config-dump fixture (packet capture, protocol
  exchange, log or config dump) can look complete while the structured payload underneath (options,
  TLVs, nested records) still carries site topology (internal hostnames, domain names, subnets,
  device identifiers, vendor/serial data). States this is general practice across formats (DHCP,
  DNS, LLDP, SNMP, logs, configs), then requires asserting the shipped fixture's fields in a test so
  the scrub is enforced by the suite rather than remembered by a person. Prose-only; frontmatter
  `description` unchanged.
- [x] Receipt held (skill_receipt.py, this session)
- [x] RED (baseline-probe, sonnet, pre-change text): given a scenario committing a device-protocol
  capture as a fixture, having already stripped header IPs and one noticed hostname, with an
  unexamined nested TLV block (serial, firmware, VLAN id). The agent independently proposed treating
  the serial (and possibly a MAC) as sensitive and asserting known values in the test - but explicitly
  disclaimed this as "general engineering judgment... The skill is otherwise silent on binary capture
  files as a fixture type," and never connected the VLAN id / management network identifier to site
  topology at all.
- [x] GREEN (baseline-probe, sonnet, new text): given the identical scenario plus the new text, opened
  by naming the scenario "exactly the case it describes," quoted the governing clause verbatim -
  "Assert the shipped fixture's fields in a test, not only once by eye before committing... so the
  scrub is enforced by the suite rather than remembered by a person" - and explicitly mapped the
  management VLAN id to the skill's own "subnets" example of site topology ("the skill's list names
  'subnets' as sensitive site topology; a management VLAN id is the same category of internal-network
  fact"), a link the RED arm missed entirely.
- [x] Skill gaps (RED): no explicit statement that a structured/nested payload block below the header
  needs scrubbing, no naming of VLAN/subnet-shaped fields as site topology, and no assert-the-fixture
  requirement grounded in the skill (the RED arm's mention of asserting values was framed as its own
  judgment, not skill-derived).
- [x] Diff RED to GREEN: GREEN kept every RED action (treat identifying fields as sensitive, assert
  known values, preserve structural validity) and added two things RED did not reach: the explicit
  VLAN-id-to-topology mapping, and grounding the assert-in-test requirement in the skill's own text
  as the mechanism that keeps a re-captured/re-exported fixture from silently regressing. No RED
  result was lost.
- [x] RED did not fully flip (honest note): the model's general security instinct already produced
  much of the technical content (redact identifying binary fields, assert exact values) without the
  skill's help - consistent with the brief's "may legitimately NOT flip if the surrounding skill
  already generalizes." The observed diff is in grounding (skill-derived vs ad hoc) and in one
  concrete category (VLAN/subnet as topology) that RED missed outright, not in a binary pass/fail.
- [x] CSO / description: unchanged - `build_skill_docs.py` run to confirm `docs/skills.md` stays in
  sync; no rebuild needed since the one-line description text did not change.
- [x] Security scan: prose-only note; no secrets, private hostnames, absolute machine paths, or
  internal project codenames - the example uses generic protocol/device-capture placeholders (DHCP,
  DNS, LLDP, SNMP as protocol families, "internal hostnames" / "device identifiers" as categories),
  never a real capture or site value. The motivating incident (a private capture) is referenced only
  by category in the task brief, not reproduced in the shipped text.
