# skill-writer checklist - python-network-probe (2026-10-26, macOS capture and neighbour write measured)

Change: the macOS DHCP capture paragraph says the `/dev/bpf` capture is measured as root on a macOS runner VM
(a `feth` pair end to end), not on physical hardware and not yet against a real guest boot on a bridge, and
tells the reader to confirm the first capture they depend on. Its `lo0` sentence now says the refusal comes from
the link type and raises `IPScoutUnsupportedError` (it said "refused by name", which no code does:
`dhcp_macos.py` checks `BIOCGDLT`). The `set_neighbour` / `remove_neighbour` privilege row says the macOS routing
socket write, replace and remove round trip passed as root on a macOS runner VM, and that the unprivileged
`False` without `interface=` holds on every platform. Twin sync of the tool repo's skills/python-network-probe.
No rule, trigger or description changes.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is retrieval: can a reader tell from the text what was measured, where,
      and what is still unmeasured.
- [x] RED (text): the pre-edit SKILL.md has 3 lines calling the macOS paths untested and 0 naming the runner
      VM, against the `remove_neighbour` row present as the control that the grep read the file.
- [x] GREEN (text): the edited SKILL.md has 0 untested lines and 2 naming the runner VM; the `remove_neighbour`
      row is intact.
- [x] GREEN (retrieval, quote-back), first text: both tiers (opus, haiku; 2 cells) answered where and as what
      the capture ran, whether the neighbour write ran, and what is not yet run, each with a direct quote. Gaps
      CLOSED in the final text: the Windows scope of the unprivileged `False` ("on every platform", checked
      against `static_neighbours.remove_neighbour`), the neighbour write's outcome ("round trip passed"), the
      missing check before relying on a capture, and "device path" vs "capture".
- [x] GREEN (retrieval, quote-back), final text, same questions in full plus "what to do before relying on a
      capture": both tiers (opus, haiku; 2 cells) answered all four correctly with direct quotes.
- [x] GREEN (retrieval, quote-back), corrected `lo0` sentence: both tiers (opus, haiku; 2 cells) answered that
      `lo0` is refused with `IPScoutUnsupportedError` and that the link type, not the name, decides it.
- [x] Twin parity: `repo-gate.py --mirror-of` on the tool repo reports `in sync`.
- [x] Describes the latest release only: no history wording (no longer, previously, used to, formerly) in the
      added lines.
- [x] No address, hostname or path added; no session narrative or private provenance here.
- [x] Skill gaps reported by the probes, each decided:
      - "DHCP" is not named in the paragraph (both tiers): DECLINED - an excerpt artefact; the paragraph sits
        under "Finding a machine that has not got an address yet", which introduces `observe_dhcp`.
      - No method for "confirm the first capture returns the address you expect" (both tiers): DECLINED - the
        reader compares the address `observe_dhcp` returns with the one the machine reports; which source they
        trust is theirs to choose.
      - Which bridge or interface name to use on macOS (haiku): DECLINED - host-specific; `local_interfaces()`
        lists them and the error message names it.
      - The provenance line's two readings (both tiers): DECLINED - the version-and-date form is the
        catalogue's standard provenance stamp.
      - No Linux figure (opus): DECLINED - outside this change; the Linux path is documented above.
      - Unprivileged `remove_neighbour` with `interface=`, or with an entry listed (both tiers): DECLINED -
        covered at SKILL.md "`remove_neighbour` with `interface=` always asks the kernel: unprivileged it raises
        `IPScoutPermissionError`".
      - Same VM and macOS version for both tests (haiku): DECLINED - "a macOS runner VM" is the claim made; the
        version is not something a reader acts on.
      - The exception's import path and base class (both tiers, `lo0` probe): DECLINED - covered at SKILL.md
        "`except IPScoutError` catches every one of" and `import ipscout` in the setup example.
      - When the refusal is raised, and other non-Ethernet link types (both tiers): DECLINED - the reason given
        (not Ethernet-framed) is the rule; the timing does not change the handler.
      - "name a bridge or physical interface" read as name-based (both tiers): DECLINED - the same sentence
        gives link type as the reason, and both tiers answered the mechanism correctly.
