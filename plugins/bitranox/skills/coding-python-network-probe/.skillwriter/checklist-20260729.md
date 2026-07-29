# skill-writer checklist - coding-python-network-probe (2026-07-29, new skill)

Change: new skill routing Python network probing (ICMP ping, reachability sweeps, RTT and packet
loss, traceroute, local interface enumeration) to `ipscout`, for the case that keeps going wrong:
the work must run as an ordinary user with no root, sudo, Administrator or CAP_NET_RAW, and must
not shell out to `ping`/`tracert`. Mirrored from the ipscout repo's own `python-network-probe`
plugin; the name carries the `coding-python-` category prefix required by this marketplace's
`skill-taxonomy.json`. Shipped in plugin 5.99.0.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: baseline agent, no skill, asked for unprivileged ICMP in Python. It selected `icmplib`
      and asserted `privileged=False` makes it run without admin **on Windows too**. That is false,
      and it is the exact failure this skill exists to stop.
- [x] RED verified against source, not memory: icmplib `sockets.py` reads
      `self._privileged = privileged or PLATFORM_WINDOWS` and then opens `SOCK_RAW`, so on Windows
      the flag is overridden and Administrator is required whatever the caller passes. The skill
      quotes that line so a future reader can re-check it rather than trust the claim.
- [x] GREEN: agent with the skill selected ipscout, did not repeat the icmplib claim, and when it
      needed a MAC address it read `ipscout.__all__` instead of inventing a call - then reached for
      `/proc/net/arp` plus `GetIpNetTable2` via ctypes rather than a subprocess around `arp -a`.
- [x] REFACTOR: the first draft documented ten functions that do not exist in this release
      (`get_mac_address`, `lookup_mac`, `neighbours`, `arp_scan`, `find_ip_by_mac`, `scan_ports`,
      `subnet_info`, `wake_on_lan`, `path_mtu`, `default_gateway` - the MAC/ARP layer is still
      unbuilt). Caught by checking every name against `ipscout.__all__`. Rewritten to document only
      what ships, plus an explicit "no MAC, ARP or port-scan surface yet, do not invent calls for
      them, check `dir(ipscout)`" entry so the same gap cannot be filled in by guesswork.
- [x] Platform limits are measured, not assumed: macOS traceroute raises `IPScoutUnsupportedError`
      (a CI probe showed neither `MSG_ERRQUEUE` nor a plain receive surfaces Time Exceeded to an
      unprivileged process there), and Windows async is executor-backed because `IcmpSendEcho` is a
      blocking C call. Both are stated as limits rather than omitted.
- [x] Scope: shared/general - any Python caller needing reachability data without elevation. No
      machine-specific content, no host names, no internal addresses beyond documentation literals
      (`1.1.1.1`, `8.8.8.8`, RFC 5737 `203.0.113.0/24`).
- [x] Security scan: prose plus public API examples, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: triggering conditions only ("Use when ... must run as an ordinary user ...,
      also use when reaching for icmplib, scapy, python-nmap, or subprocess"). No workflow summary,
      so the body is read rather than shortcut.
- [x] Token budget: 843 words, within the <500-word target's tolerance for a reference skill that
      carries an alternatives table and a measured-limits section; no supporting files.
- [x] Authoritative-source discipline: the skill routes flag and subcommand questions to
      `ipscout --help` and states plainly that a flag list copied into any document, including the
      skill itself, is not to be trusted.
