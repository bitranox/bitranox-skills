# skill-writer checklist - net-firewall-pfsense (2026-10-05, exit-code unification)

The verb table and the mutation paragraph name `dhcp add` and `dhcp rename` (six config.xml edits now), with their refusals; a sentence states that `--json` `ok` means "ran without error" and stays true on exit 1.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is a retrieval scenario: eleven questions over the eight
      SKILL.md files this change touches, each answered with a DIRECT QUOTE of the governing text
      or the single word NONE. The question for this skill is quoted below.
- [x] Arms pinned to the least inferential tier (haiku) on the inert `bitranox:baseline-probe`
      type, the old and the new excerpts (the changed hunks with wide context) pasted, Skill
      invocation forbidden, so neither arm could answer from the installed copy.
- [x] `redcheck --corpus-cascade` over the worktree flagged INHERITED COVERAGE on shared terms
      that are function words of the memory index (coverage, envelope, findings, marketplace),
      not the lesson; the route taken is the text check of the artifact - quote-back of the
      excerpt - which inherited context cannot satisfy, and RED did not answer from it.
- [x] Question for this skill: How do you add a DHCP reservation and change one's hostname? Is `ok` true on a `doctor --json` that exits 1?
- [x] RED (pre-change excerpt): NONE for both verbs; `ok` NONE.
- [x] GREEN (new excerpt): `dhcp add --mac M --ip A --hostname H` and `dhcp rename --mac M --hostname H`; true.
- [x] The statement matches the code: `cmd_dhcp_add`, `cmd_dhcp_rename`, `php_add_reservation`, `php_rename_reservation`, `interface_for_ip`, `valid_hostname`; the PHP payloads pass `php -l` on a real box with a planted-error control failing; pinned by the dhcp add/rename tests and `test_a_doctor_with_findings_exits_1_with_ok_true`.
- [x] Both dispatches asked for a `Skill gaps` section. RED listed this question among its
      silent or old answers; GREEN reported none. Diffed in both directions: GREEN lost nothing RED
      produced - every RED answer was the old behaviour or NONE.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
