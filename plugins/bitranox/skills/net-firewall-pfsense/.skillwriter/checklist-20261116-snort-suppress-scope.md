# skill-writer checklist - net-firewall-pfsense (scope of a Snort suppress line)

- [x] Type: technique and reference. Tested with a code RED/GREEN, a mutation battery, a text
      check and quote-back probes.
- [x] Step 0b: `skill_decisions.py show net-firewall-pfsense --kind rejected,removed --full`
      printed nothing; `show` listed one live rule (d-20261116-de07bbd9, GID:SID), which this
      change keeps.
- [x] Source for the semantics: Snort's README.filters (snort.org/faq/readme-filters). The plain
      `suppress gen_id G, sig_id S` suppresses the event completely; `..., track by_src|by_dst,
      ip <ip>` restricts it to that side of the alert; `ip` takes a single address or a CIDR
      block; track and ip must come together. Bracketed lists are documented only in Snort
      mailing-list replies, so they are read member by member; variables and `!` negations are
      not evaluated and read NO.
- [x] RED code: `test_snort_verify_without_an_address_does_not_call_a_scoped_suppression_complete`
      failed on the unchanged script (`assert 0 == 1`: verify said yes for a line scoped to
      `track by_src, ip 192.0.2.146`). The existing test asserting exit 0 for that scoped line with
      no address encoded the defect and now passes `--ip 192.0.2.146`.
- [x] RED text (pre-edit SKILL.md from `git show HEAD:`): `track` 0, `by_src` 0, `by_dst` 0,
      `scope` 0, `scoped` 0, `every address` 0.
- [x] GREEN code: all 215 tests in `tests/test_pfsense.py` pass with CI's dependency set.
      Mutation battery (compuse-toolbox `mutation_arm.py --battery`, baseline green first and
      last): subnet check dropped, unreadable-scope guard dropped, verdict forced to yes, by_dst
      fixsteps line dropped - all four KILLED. The guard arm first SURVIVED; an `ip` without
      `track` line was added to the track-without-ip test, and it is KILLED since.
- [x] Commands executed: `pfsense.py snort fixsteps --sid 125:9 --cidr 198.51.100.0/22` prints the
      all-addresses line, a note that it covers every address, and the two scoped lines
      `suppress gen_id 125, sig_id 9, track by_src, ip 198.51.100.0/22` and the `by_dst` twin.
      `snort verify --help` lists `--ip ADDRESS` (repeatable). verify against a fake ssh with a
      by_src line and a `$HOME_NET` by_dst line printed `NO - only for track by_src, ip
      192.0.2.146; track by_dst, ip $HOME_NET (scope not understood)`, and with `--ip` one line
      per address (`yes (track by_src ...)` / `NO - outside every scoped suppression`).
      No real firewall was contacted.
- [x] GREEN probe (edited excerpt, opus and haiku, 5 questions each, 10 cells): both answered
      "no" for an address outside the scope, wrote `snort verify --sid 125:9 --ip 192.0.2.7`,
      answered NO without `--ip`, NO for `$HOME_NET`, and two scoped lines from
      `fixsteps --cidr`, each with a verbatim quote.
- [x] Gaps closed from GREEN: haiku inferred, not read, the NO for a named address outside the
      scope, and opus asked what a yes from a `by_dst` line means for alerts with the address as
      source and whether an address inside a CIDR line counts. The text now states the NO for an
      outside address and range, that an address inside a line's address or CIDR reads yes with
      its side named, and that a `by_dst` yes leaves the source-side alerts blocking.
- [x] Final re-probe on the final wording (haiku, 4 questions: an address outside a by_src
      line, an address inside a by_dst CIDR line and whether it is then safe, an address outside
      that CIDR, no `--ip`): NO, "yes, covered on the dst side, NOT safe from every block", NO,
      NO, each with a verbatim quote of the edited item. No new undecided gap: its remaining
      notes are a single-address `ip` matching exactly (the plain reading of "address"), a mixed
      scoped and unscoped file (the item's first sentence: the plain line "silences the rule for
      every address"), and the exact output strings (the tool prints them; `--help` per verb).
- [x] Gaps declined, each covered elsewhere: exit codes (SKILL.md "With `--json` every verb
      prints" paragraph: a well-formed "no" is exit 1); invocation, target and flags (SKILL.md
      "Run `pfsense.py --help` and `pfsense.py <verb> --help` for the current flags"); resync and
      `snort unblock --apply` (the "Clearing `snort2c` and calling it fixed" item); whether
      verify reads the pass list (`snort verify --help`: "is the SID suppressed and the CIDR
      pass-listed, in the LIVE instance?"); which side of an alert snort2c blocks (a Snort
      blocking setting, outside this tool; the text says the range can be either side).
- [x] Width and fence check over the added lines prints nothing; the item is appended last in
      Common mistakes, so no back-reference or list count re-binds.
- [x] Description unchanged; routing not retested. Frontmatter parses (`['description', 'name']`).
- [x] Cases decided beyond the report: `verify` without `--ip`/`--cidr` now answers NO (exit 1)
      when every matching line is scoped, instead of yes; an unparsable `--cidr` stays accepted
      (it is still compared verbatim with the pass list) and covers no scoped line; an `--ip` that
      is not an address is refused with exit 2; `fixsteps` with an unparsable `--cidr` prints no
      scoped line and says so.
- [x] Decisions: d-20261116-f718b574
- [x] ASCII only, present tense, RFC 5737 addresses only, no private host, repo or path.
