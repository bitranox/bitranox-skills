# skill-writer checklist - net-firewall-pfsense (reservation inside the pool, unbound follows DHCP)

- [x] Type: technique and reference. Evidence is text checks of the skill file plus the script's
      own tests; no subagent probe was dispatched for this change.
- [x] Premises checked against the pre-change code: `doctor_findings` had no pool check and
      neither `php_list_reservations` nor any other read returned a DHCP range;
      `php_add_reservation` and `php_rm_reservation` ended at `_php_reconfigure_dhcp()` with no
      unbound step. All three parts of the request were open.
- [x] Config shape checked on a real pfSense config.xml (tag names only): `dhcpd/<if>/enable`,
      `dhcpd/<if>/range/from|to`, `unbound/regdhcpstatic` and `unbound/regdhcp` exist as
      elements, `dhcpbackend` is `isc`. No snapshot at hand held an additional `pool`, so its
      `pool[]/range` shape is read with the same `from`/`to` layout as the main range.
- [x] Step 0b: `skill_decisions.py show net-firewall-pfsense --kind rejected,removed --full`
      printed nothing; `show` listed two live snort rules, neither touched here.
- [x] RED text check (pre-edit files): `dhcpleases`, `Dynamic and static leases`,
      `regdhcpstatic`, `dynamic pool` each 0 in SKILL.md, pfsense.py and the tests.
- [x] RED tests: the 16 new tests written first; 14 failed (missing `pools_from_config_xml`,
      `php_list_pools`, the regdhcpstatic gate, no unbound restart after a DHCP write, exit 0
      over a dead unbound) and the 2 controls passed (a write with `unbound_follows` false
      restarts nothing).
- [x] GREEN tests: the whole suite, 231 passed, with CI's dependency set.
- [x] Commands executed: `pfsense.py --json doctor --config <real snapshot>` reported no
      finding (6 static maps, none inside the pool); a scratch copy with one static map moved to
      the pool's first address reported exactly one `static_map_in_dynamic_pool` and exit 1.
      Nothing was run against a firewall.
- [x] GREEN text check: `dhcpleases` 2, `Dynamic and static leases` 1, `regdhcpstatic` 1,
      "`dhcp rename` does not" 1, the new Diagnose row 1.
- [x] Width and fence check over the added lines prints nothing; ASCII only in SKILL.md, the
      script and the tests.
- [x] Paragraph after each insertion point read: "The first row is the one that gets missed"
      still names the static-ARP row (the new row is the third); the new trap's "as above" binds
      to the restart-and-check paragraph directly before it.
- [x] Cases decided beyond the request: a DHCP server without `<enable>` contributes no pool
      (its range leases nothing); a pool on another interface never claims a reservation; pool
      ends are inclusive; the post-write unbound check resolves `localhost.`, so it proves
      unbound answers, not that it answers the reservation's own name (the text tells the reader
      to resolve that name). `dhcp rename` keeps its current behaviour and the text says so.
- [x] Gaps declined: `dhcp add` refusing an address inside the pool (a separate behaviour change
      the request did not ask for); Kea's handling of a reservation inside a pool (not observed
      here, so the finding names ISC dhcpd only).
- [x] Description unchanged, so routing not retested.
- [x] Decisions: d-20261116-922c8631
- [x] Present tense, no private host, repo or path in the added text; examples use RFC 5737
      addresses.
