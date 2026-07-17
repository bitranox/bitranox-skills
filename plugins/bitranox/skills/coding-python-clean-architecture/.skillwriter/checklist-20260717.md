# skill-writer checklist - coding-python-clean-architecture (2026-07-17, ports rule, immutability strength, SCRIPT-mode routing, import-linter step, config-leak check)

Change: Five defects: 'Ports use stdlib types only' forbade the skill's own canonical port (`amount: Money`)
and its UoW port (`RequestContext`); 'Prefer immutability' vs the non-negotiable 'no mutable state';
'When NOT to use: single-file scripts' dropped the skill for work SCRIPT mode (one of its four modes)
owns; the 8-step Refactoring Path never added the import-linter contract it calls non-negotiable; the
Non-Negotiables checklist had no row for the config-leak rule the skill calls testable.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read the canonical port at line 185 (`amount: Money`) against the rule at 677 ('stdlib types
      only') - the rule forbids the skill's own example; the other four verified the same way
- [x] GREEN: restated ports as 'no framework/driver types; domain types and DTOs are fine'; aligned
      immutability to the non-negotiable; routed SCRIPT mode instead of exiting the skill; added the
      import-linter step and the config-leak checklist row
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
