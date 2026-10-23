# skill-writer checklist - coding-python-network-probe (2026-10-23, static neighbour entries)

- [x] Change: mirror of `libs/ipscout/skills/python-network-probe` at ipscout 1.7.0, which adds
      `set_neighbour` / `remove_neighbour` and the `set-neighbour` / `remove-neighbour` CLI
      commands. The only divergence from the twin is the `name:` line (checked with `diff`).
- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session).
- [x] RED (opus, pre-change text pasted as the complete skill): asked how a script writes a static
      ARP entry for 192.0.2.7 -> 00:00:5e:00:53:07 and undoes it, what privilege that needs, and
      whether the description covers it. Answer: NONE to all three ("The skill documents no call
      that writes, adds or deletes a neighbour/ARP entry").
- [x] GREEN (opus and haiku, new text pasted): both quoted the quick-reference rows, the privilege
      row and the description clause "or write a static (permanent) entry to it".
- [x] REFACTOR, gaps closed in the text and re-probed on the final text (opus + haiku per round,
      4 rounds, 8 GREEN cells), each answer a direct quote:
      - `interface=` optional, with the none/several-subnets refusal;
      - `set_neighbour` before the `try`, `remove_neighbour` in the `finally`;
      - an unprivileged `remove_neighbour(..., interface=...)` raises, a privileged one answers `False`;
      - the privilege table is scoped by its rows' own exceptions, not "everything above is
        unprivileged" (a first rewording, "the two rows marked (privilege)", was itself false and
        was caught by the next round);
      - a replaced entry is not restored; check the address first with
        `get_mac_address(ip, active=True)`;
      - a neighbour entry is not a route, so borrow an address inside a local subnet;
      - interface spellings accepted on Windows, and removal by any spelling of the same interface;
      - `remove-neighbour` exits 1 when there was no entry.
- [x] Declined, with reason: how to reach a device only on a foreign subnet (routing is the
      caller's, ipscout adds no routes, now stated); an up-front elevation check (the documented
      pattern is call-and-catch `IPScoutPermissionError`); whether the device accepts frames for
      an address it does not hold (device behaviour, not this library's); the macOS write path
      being untested on hardware (already stated in the text).
- [x] Every claim checked against the code (`static_neighbours.py`, `neighbours_linux.py`,
      `neighbours_windows.py`, `cli.py`); the Windows write round trip ran elevated on a Windows
      host and passed; the Linux one passed under root as reported by the implementing run (not
      re-run here).
- [x] Description measured: 929 characters, under 1024.
- [x] Security scan: prose only; documentation addresses only (RFC 5737 / RFC 7042), no secrets,
      hostnames or private paths added.
