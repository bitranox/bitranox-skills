# skill-writer checklist - coding-python-use-modern-libraries (2026-07-17, the 'Adding an entry' rule matches the table it governs)

Change: The rule said 'Each row must carry all three of: description, replaces, and why', but ~10 of its own rows
(Enums, Terminal output, TUI, Paths, .env files, Database ODBC/MySQL, ORM, Testing, Type checking) carry no
why-parenthetical - the table contradicts its own stated requirement.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read the rule at line 18 against rows 44-56: 10 rows violate it, so the rule is either wrong or the
      table is - and a rule its own data breaks is one a reader learns to ignore
- [x] GREEN: scoped the requirement to NEW entries (the section is 'Adding an entry') and to picks that are not
      self-evident, naming both cases: an obvious swap (pathlib over os.path) needs no why; a
      trade-off pick (isal vs deflate, MySQL drivers) always does
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
