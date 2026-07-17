# skill-writer checklist - coding-bash-clean-architecture (2026-07-17, domain stderr rule made consistent; refactor path reaches its gate; red-flags table added)

Change: Three places forbade the domain writing to the terminal while the Error Handling table (line 162) and
the shipped canonical-example.md both have the domain emit `echo "error: ..." >&2`. REVIEW mode would
flag the skill's own reference implementation. Also: the 9-step Refactoring Path ended without the two
non-negotiables (trap cleanup, `shellcheck -x`), and review-checklists.md's exit-code enumeration
dropped code 1 while the line above it says "0=ok, 1=error".

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: read canonical-example.md: domain__validate_service_def emits four `>&2` error lines, which the
      layer table + Observability + Non-Negotiables checklist all forbid - the skill contradicts its
      own example, so either the example or the rule had to be wrong
- [x] GREEN: separated LOGGING (adapter-only) from ERROR REPORTING (domain stderr allowed) in all four
      places; added steps 10-11 (trap + shellcheck) to the path; added 1 to the exit-code list;
      added a rationalization table for the '<30 lines, layers are overkill' exemption
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
