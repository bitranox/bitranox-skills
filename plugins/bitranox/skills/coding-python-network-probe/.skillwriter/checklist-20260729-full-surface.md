# skill-writer checklist - coding-python-network-probe (2026-07-29, full API surface)

Change: the skill documented 8 of the 30 callables ipscout now exports, and stated as fact that
there is "no MAC, ARP or port-scan surface yet". That became false when the MAC/neighbour/route
layer and the scan/subnet/wake/MTU layer shipped. Rewritten against `ipscout.__all__`: the quick
reference now covers all of it, the routed-MAC scope rule gets its own section, and a table states
which three operations need privilege and what they do instead of degrading. Shipped in plugin
5.100.2.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, and this one is the worst kind: the skill did not merely omit the new functions, it
      ASSERTED they do not exist. An agent trusting it would refuse a task ipscout can do, or
      reach for scapy. The original wording was written precisely to stop an agent inventing
      calls; left stale it inverted into stopping an agent from using real ones.
- [x] GREEN: every symbol the document names is checked against `ipscout.__all__` by script, not
      by reading. 23 symbols named, 0 unaccounted for (the two non-exports are `scapy.arping` and
      `scapy.sr1`, which appear only in the do-not-use column).
- [x] The check that caught the original error is now the check that keeps it correct - a lesson
      applied rather than just recorded.
- [x] Privilege table states the three that need rights (SYN scan, active resolution, macOS
      traceroute), each with the exact requirement, and the two guarantees they honour: never
      silently degrade, and always name the unprivileged alternative in the message.
- [x] Platform limits remain measured, not assumed: Windows raw TCP blocked since XP SP2, Windows
      async executor-backed, macOS traceroute needing a raw socket, DHCP fields absent off Linux.
- [x] Scope: shared/general. Documentation literals only (`1.1.1.1`, `8.8.8.8`, RFC 5737 ranges);
      no host names, no internal addresses.
- [x] Security scan: prose plus public API examples, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: still triggering conditions only, widened to the new tasks (port scan, MAC,
      ARP cache, routes, subnets, wake-on-LAN, path MTU) and the new tools worth intercepting
      (`netifaces`, `arp`, `ip`, `ifconfig`, `netstat`). No workflow summary.
- [x] Token budget: 1316 words, up from 839. A reference skill carrying a routing table, an
      alternatives table and a privilege table; still one file, no supporting files.
- [x] Kept byte-identical to the copy shipped in the ipscout repo, modulo the name prefix this
      marketplace's taxonomy requires.
