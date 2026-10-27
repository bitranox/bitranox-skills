# skill-writer checklist - python-network-probe (2026-10-27, surface audit)

Change: audit the skill against the installed package (2.5.1 plus Unreleased) and the source;
correct the claims the source contradicts and add the parts of the surface the skill omitted.
Frontmatter unchanged.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: RED as a text check of the pre-edit file (an EDIT; the
      installed copy is the old text), GREEN as a quote-back retrieval probe.
- [x] Surface enumerated: `ipscout.__all__` with `inspect.signature`, and `--help` for the CLI
      group and all 23 subcommands.
- [x] RED (text, pre-edit file): 0 matches each for `raise_on_error`, `ping_group_range`,
      `before the command`, an IPv4-only sweep, `to_thread`, completion order, `only on Linux`,
      `"error": null`, `resolve_names`, `make_hop_transport`; 8 for `1.1.1.1|8.8.8.8`; control
      `ping` 27.
- [x] Claims corrected, each checked by running it or by reading the branch:
      - `ping_many` does not raise for a per-probe argument (`times=0` lands on `.error`); only
        a bare-string `targets` or `concurrency` below 1 raise (run).
      - `except IPScoutError` does not catch a plain argument `ValueError` or the in-loop
        `RuntimeError` (MRO printed).
      - A bare `fe80::` address: the sending calls raise `IPScoutResolutionError`, `grab_banners`
        and `read_snmp_system` report `UNREACHABLE`, `is_reachable` is `False`, while
        `query_route` and a passive `lookup_mac` answer without refusing (run).
      - Traceroute on unprivileged macOS raises `IPScoutUnsupportedError`, not a permission
        error (`traceroute.py` `_require_walkable`); SYN scan is IPv4 only (`portscan.py`
        `_half_open`).
      - `observe_dhcp`'s refusal names only `subnet_info()` (message read in all three
        backends); the bridge-host pointer is gone.
      - `subnet_info()` DHCP fields are filled only on Linux (`subnet.py` `_lease_for` returns an
        empty lease elsewhere).
      - The JSON success envelope carries `"error": null`; `--json` must come before the
        command (`ipscout reachable 127.0.0.1 --json` exits 2, NoSuchOption).
      - Exit `1` listed for every command, from each `ctx.exit(EXIT_NOT_REACHED)` in `cli.py`.
- [x] Surface added: `raise_on_error` and its defaults, `settle=` and `--settle`, the default DHCP
      interface, single-use sessions, `family=` on banners/SNMP, empty `farewell` and the
      255-character community refusals, `resolve_names`, `factory.make_hop_transport` for
      `trace_path`, `mac --strict`, a sweep returns only entries inside IPv4 default networks,
      `arp_scan`/`find_ip_by_mac(scan=True)` raise in a loop and have no async twin
      (`asyncio.to_thread` run), `scan_ports` result order, the `ping_group_range` remedy, the TCP
      fallback applying only when ICMP is unavailable, CLI report models.
- [x] Example values: `1.1.1.1`, `8.8.8.8` and the `02:00:5e:10:00:00` MAC replaced by
      `192.0.2.x`, `203.0.113.7`, `example.com` and `00:00:5e:00:53:10`.
- [x] Every non-privileged code and CLI example executed with targets swapped for
      `127.0.0.1` / `::1` / `localhost`; the DHCP session, `set_neighbour` and SYN examples were
      run to their unprivileged refusal and checked against the source for the privileged path.
- [x] GREEN quote-back, opus (effort medium) and haiku, eight questions on the edited text
      pasted in: both tiers answered every question with a verbatim quote matching the source
      behaviour. Cells: 2 tiers x 8 questions.
- [x] Gaps from GREEN closed: "takes" read as "refuses" for `query_route` (now "accepts"); the
      IPv6-sweep budget vs a link-local `/64` (now stated: never fits, use the cache); the
      `to_thread` example implied `network` is required (now shown without it); the
      `raise_on_error` defaults; which bad arguments are a bare `ValueError`.
- [x] Gaps declined: whether `find_ip_by_mac` returns a zoned link-local address - covered in
      "Writing a link-local address" (`find_ip_by_mac` returns that form); the guest's re-ask
      pause - not a library constant, left to the caller; the `mtu` output wording - the exit
      code list says "no path MTU".
- [x] Re-probe on the final text after the gap fixes (opus, effort medium, SKILL.md only): ten
      questions on the corrected claims (`ping_many` per-probe errors, what `except IPScoutError`
      misses, zone-less link-local in `grab_banners`, `--json` position, Linux-only DHCP fields,
      connect-scan order, default sweeps and IPv6, macOS traceroute refusal, `arp_scan` in a loop,
      envelope keys). All ten answered correctly; each quote was found verbatim in the file
      (whitespace-normalised), and a planted non-sentence was not.
- [x] Version-history finder over the skill dir: one hit, "ref**used to**o", not history.
- [x] Non-ASCII grep: none. Frontmatter parses (`name`, `description` only); description
      untouched (1015 characters).
