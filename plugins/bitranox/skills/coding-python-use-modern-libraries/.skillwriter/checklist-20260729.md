# skill-writer checklist - coding-python-use-modern-libraries (2026-07-29, ipscout row)

Change: add one routing row for the ICMP ping / reachability / traceroute task, pointing at
`ipscout` and listing what to reach for instead of (`icmplib`, `scapy`, `subprocess` around
`ping`/`tracert`), with a cross-reference to `bitranox:coding-python-network-probe` for the detail.
Shipped in plugin 5.99.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the table had no row for this task at all, so an agent consulting it for a network-probe
      question got no steer and fell through to its own recall - which selected `icmplib` and
      claimed, wrongly, that `privileged=False` avoids admin on Windows.
- [x] GREEN: with the row present the task routes to ipscout, and the "instead of" column names
      icmplib explicitly with the reason (forces raw sockets on Windows, needs Administrator), so
      the wrong answer is refused by name rather than merely left unmentioned.
- [x] Claim verified from source before it was written down: icmplib `sockets.py` sets
      `self._privileged = privileged or PLATFORM_WINDOWS`, then opens `SOCK_RAW`.
- [x] Placement: inserted before the `Layered / cross-platform app config` row, keeping the table's
      existing grouping intact. No other row touched.
- [x] Scope: shared/general - no machine-specific content.
- [x] Security scan: one prose table row, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body table addition, frontmatter untouched).
- [x] Token budget: one row added to an existing routing table.
