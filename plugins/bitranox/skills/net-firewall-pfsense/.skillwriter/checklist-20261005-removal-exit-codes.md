# skill-writer checklist - net-firewall-pfsense (2026-10-05, removal exit codes)

A new paragraph states that a removal which removed nothing is a failed action, exit 2
(`dhcp rm`, `dhcp rm-static-arp`, `dns rm` whose matched entry was not removed; `table del` /
`snort unblock` leaving every requested address present, one address included), and that some of
several addresses left present is a partial outcome, exit 1. The `--json` sentence now also
says `ok` is false on exit 2.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: a retrieval scenario of four questions, each answered with a
      DIRECT QUOTE of the governing text or the single word NONE.
- [x] Arms pinned to the least inferential tier (haiku) on the inert `bitranox:baseline-probe`
      type, the old and the new excerpts pasted, Skill invocation forbidden, so neither arm could
      answer from the installed copy.
- [x] `redcheck --corpus-cascade` over the worktree reported INHERITED COVERAGE on subject
      vocabulary (address, dhcp, pfsense, reservation, verb), not on the exit-code lesson; the
      route taken is the text check of the artifact - quote-back of the pasted excerpt - which
      inherited context cannot satisfy.
- [x] Questions: exit code of a `dns rm` that matched and removed nothing; of a `snort unblock` of
      one address that stays blocked; of a `table del` of two addresses where one survives; `ok`
      under `--json` for the first.
- [x] RED (pre-change excerpt): NONE for all four. Skill gaps reported: the exit code for a verb
      that located its target but could not change it, and for a partial deletion, are undefined.
- [x] GREEN (new excerpt, first pass): 2, 2, 1 - each quoted; `ok` NONE. Skill gap: the text says
      `ok` stays true on exit 1 but never states its value on exit 2.
- [x] REFACTOR: the `--json` sentence gained "and is false on exit 2". Re-asked by quote-back on the
      final text: `ok` false on the exit-2 removal, true on the exit-1 partial, each with a direct
      quote; no gaps reported.
- [x] Diffed in both directions: GREEN lost nothing RED produced - every RED answer was NONE.
- [x] The statement matches the code: `_require_effect` (dhcp rm, dhcp rm-static-arp, dns rm) and
      `_removal_exit` (table del, snort unblock) in `scripts/pfsense.py`, exit 2 through `main`'s
      PfsenseError path with an `ok: false` envelope; pinned by
      `test_a_matched_removal_that_removed_nothing_is_exit_2_with_ok_false`,
      `test_table_del_of_one_address_that_survives_is_a_failed_action_exit_2`,
      `test_table_del_of_several_where_some_survive_is_partial_exit_1`,
      `test_table_del_of_several_where_all_survive_is_a_failed_action_exit_2` and the snort
      unblock trio. No live pfSense box was touched; every test drives the injected process seam.
- [x] Description unchanged - no routing keyword moved, cap not in play.
- [x] No address, MAC, hostname or machine path added.
- [x] Present tense, no session narrative, no private provenance.
