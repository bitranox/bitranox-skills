# skill-writer checklist - python-network-probe (2026-10-24, neighbour state)

Change: the quick reference gains a row filtering the neighbour cache on `NeighbourState`, and a
note under the table naming every `NeighbourState` member, the default family of `neighbours()`,
the macOS limit (every entry is `OTHER`), and that a cache state is not a liveness test - probe
with `is_reachable(entry.scoped)`. Frontmatter unchanged. Mirrored into bitranox-skills, which
ships it as coding-python-network-probe.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED by text check against the skill file, the route for an edit whose old text is the
      installed copy: `NeighbourState` appeared 0 times in this copy and in the bitranox-skills
      twin, although it is in `ipscout.__all__` (it was at v1.7.0 too). The release's surface
      check (`must_be_named` over `__all__`) listed it as missing.
- [x] GREEN, retrieval with quote-back, opus and haiku (2 cells): both wrote
      `[e for e in neighbours() if e.state is NeighbourState.REACHABLE]` and quoted the new row.
- [x] REFACTOR on the gaps GREEN reported, each re-probed on opus and haiku:
  - default family of `neighbours()` and the member list were unstated -> the note now gives
    both; both tiers quoted "returns both families unless `family=` narrows it" and the six
    members (2 cells).
  - what `OTHER` means -> reading the backends showed macOS reports every entry as `OTHER` (its
    routing dump has no per-entry state) and Windows maps PROBE/DELAY to it, so a REACHABLE
    filter returns nothing on macOS. The note says so; both tiers quoted it (2 cells).
  - the row label "confirmed entries" contradicted the note (PERMANENT is dropped) -> relabelled
    "only the REACHABLE entries"; the note says a cache state is never a liveness test and names
    `is_reachable`.
  - both tiers then guessed `e.ip` for the probe, which fails for a link-local entry -> the note
    names `is_reachable(entry.scoped)`, never `entry.ip`. Closing probe, both tiers:
    `[e for e in ipscout.neighbours() if ipscout.is_reachable(e.scoped)]` (2 cells).
- [x] Declined, answered elsewhere in the skill (the probes saw an excerpt): imports
      (`import ipscout`), the value `family=` takes (`AddressFamily.IPV4` / `IPV6`, error-contract
      section), privilege (the privilege table lists no cache read), `scoped` for IPv4 ("the plain
      address for everything else"), the Windows zone namespace (interface-namespace section),
      concurrency (`ping_many`), one entry per interface (multi-homing section). Declined as the
      library's design, not the skill's: `OTHER` covering both "no state reported" and
      "unmapped state".
- [x] Tiers and cells: 10 probe cells, 5 opus + 5 haiku; every GREEN and REFACTOR claim ran on
      both.
- [x] Every code fragment executed against the real library: the REACHABLE filter returned a list
      whose entries are all REACHABLE; `is_reachable(entry.scoped)` probed scoped link-local and
      plain IPv4 entries without error; the member names match `NeighbourState`.
- [x] Security scan: no address, MAC, hostname or path added.
- [x] Token budget unchanged in kind: one table row and a five-line note; the body remains an index.
