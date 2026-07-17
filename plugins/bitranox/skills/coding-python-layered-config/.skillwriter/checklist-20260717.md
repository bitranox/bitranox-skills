# skill-writer checklist - coding-python-layered-config (2026-07-17, default_file shown, since it is the only way to supply the layer the skill says not to forget)

Change: The skill says "Do not forget `defaults` (the lowest layer, seeded from an explicit `default_file`)" but
no example, bullet, or CLI flag ever showed default_file - while the real read_config signature takes it.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read the real signature at libs/lib_layered_config/src/lib_layered_config/core.py:62 - default_file
      is a real parameter, and grep showed it in no example in the skill
- [x] GREEN: added default_file to the read_config example and a bullet stating it is the ONLY mechanism for
      that layer
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
