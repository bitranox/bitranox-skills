# skill-writer checklist - coding-python-network-probe (2026-07-29, command coverage)

Change: add the shell section listing all eighteen subcommands, and three quick-reference rows for
`normalise_mac`, `parse_ports` and `trace_path`/`atrace_path`. Shipped in plugin 5.100.4.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED, found by a coverage check run against the CLI and `__all__` rather than by reading: six
      of eighteen subcommands appeared nowhere in the skill (`arp-scan`, `capabilities`,
      `find-ip`, `ping-many`, `reverse-dns`, `scan-ports`) and five of thirty callables were
      absent. The skill routed flag questions to `--help`, which is right, but an agent has to
      know a command EXISTS before it can ask for its help.
- [x] This is the same failure class as the "no MAC surface yet" line the previous revision fixed:
      an agent does not reach for what the skill does not mention. Naming the commands is the
      whole remedy; the flag lists stay with `--help`, which cannot go stale.
- [x] GREEN: the check now reports zero missing commands and one missing callable, `print_info` -
      a metadata printer behind the `info` command, which is listed. Left out deliberately;
      documenting it as an API call would be noise, and the skill already tells the reader to
      check `ipscout.__all__`.
- [x] `capabilities` called out by name in prose: it answers "what can this host do" without
      provoking an error, which is the thing a caller otherwise learns the hard way.
- [x] Verified by script against the live `--help` output and `__all__`, not by reading.
- [x] Scope: shared/general - documentation literals only.
- [x] Security scan: prose plus public commands, ASCII, no secrets/hosts/paths/PII.
- [x] CSO description: unchanged (body addition, frontmatter untouched).
- [x] Token budget: 1508 words, up from 1316. A reference skill with four tables; still one file.
- [x] Byte-identical to the ipscout copy, synced AFTER that repo's formatter ran - the ordering
      that previously left the two differing by a space.
