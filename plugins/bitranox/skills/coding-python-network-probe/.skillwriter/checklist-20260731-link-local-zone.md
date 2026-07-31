# skill-writer checklist - coding-python-network-probe (2026-07-31, link-local zone)

Change: two sections. Both directions of the MAC-to-interface mapping are many-to-one, and reaching
an IPv6 link-local address needs the RFC 4007 zone - why `interface.index` is the only portable
spelling of it, and that a lookup's own answer (`Neighbour.scoped`, `find_ip_by_mac`) already
carries one. Frontmatter gains one trigger. Ships with plugin 5.117.1.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED at the library level: every probe to a link-local address reported the host as
      unreachable, measured against a real neighbour - the system ping answered in 1.01 ms while
      `ping()` returned `reached=False`.
- [x] RED at the skill level: a subagent given only the pre-change SKILL.md and a `Neighbour`
      record wrote `ping(entry.ip)`, the bare address the library refuses.
- [x] GREEN: the same scenario against the updated SKILL.md produced `ping(entry.scoped)`, with
      the reason - "entry.ip has no zone and is refused by every probe call".
- [x] REFACTOR, on the loophole the executed check found: told to name the interface by index, a
      subagent on the old text stripped the zone and rejoined the index. That code works, but it
      declared itself not confident, naming the gap - the text never said `ping()` accepts a
      `%<index>` suffix. On the new text: `ping(found[0])`, confident, explaining unprompted that
      appending would double-zone it and be refused.
- [x] One scenario did not discriminate: asked to ping an already-scoped answer, both arms passed
      it straight through, because the prompt showed the zone. Recorded, not counted as a pass.
- [x] Every code block executed against the real library, not reviewed: `entry.scoped` and
      `find_ip_by_mac(...)[0]` both accepted by `ping`, the double zone refused by name, an IPv4
      answer byte-identical to `entry.ip`.
- [x] Cross-platform claims measured on the platform they name: on Windows an interface name fails
      as a zone while an index succeeds, `local_interfaces()` reports a friendly name from a
      different namespace than `if_nametoindex`, and the zoned ping answered in 0.8 ms through
      `Icmp6SendEcho2`.
- [x] CSO: one trigger added for an IPv6 link-local address needing its interface zone, which
      nothing in the description matched. Triggers only, no workflow summary. Frontmatter 929 of
      1024 chars.
- [x] Security scan: every address and MAC in the new text is a documentation literal - the RFC
      7042 range `00:00:5e:00:53:xx` and its EUI-64 link-local forms. One pre-existing real-looking
      MAC in the CLI examples replaced with the same range while here.
- [x] Copies byte-identical apart from the `name:` line; token budget unchanged in kind, the body
      remains an index over the library's surface.
