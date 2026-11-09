# skill-writer checklist - coding-python-enforce-data-architecture-strict (2026-07-17, frontmatter enum rule, Pydantic target, counter race, single todo list, honest stop-condition)

Change: The always-loaded frontmatter said 'Enums/IntEnum for all fixed string values' while rule 4 reserves
IntEnum for integers-on-the-wire and mandates StrEnum for strings - the description outranks the body at
trigger time. Plus: 'convert dict inputs to dataclasses' vs 'Prefer Pydantic'; 'Decrement
total_violations' vs the subagent template's 'Recalculate as sum' (and decrementing races across
parallel subagents); two competing TodoWrite lists; and 'Final verification grep finds nothing' re-arming
exactly the raw-match-count gate STEP D forbids ('a hit is a lead, not proof').

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read line 3 against line 23: the frontmatter prescribes IntEnum for STRING values, which rule 4
      explicitly forbids; verified the other four contradictions by reading both sides in the file
- [x] GREEN: frontmatter now says 'Enums for all fixed categorical values'; dict->Pydantic; recalculate-as-sum
      with the race named; one extended list; stop-condition now requires a judged verdict, not a count
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: corrected (enum rule)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
