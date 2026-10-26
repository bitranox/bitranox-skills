# skill-writer checklist - python-network-probe (2026-10-26, macOS bridge refused, member port)

Change: the DHCP capture paragraph said "On Linux and macOS the capture binds to a bridge and sees the traffic
the bridge forwards". Measured as root on a macOS runner VM, a macOS bridge's BPF sees only frames delivered to
this host (0 frames without a bridge address, broadcasts only with one, never a unicast reply forwarded to a
member; `tcpdump` on the bridge agreed), while each member port sees the whole exchange. ipscout 2.5.1 refuses
a `bridgeN` interface with `IPScoutUnsupportedError` naming the member port. The paragraph now says Linux
names the bridge and macOS the guest's member port, and the measurement line says what ran (the VM's own DHCP
client on a `feth`, captured on its peer, the bridge member) and that a separate guest VM behind a macOS bridge
is not yet measured. Twin sync of the tool repo's skills/python-network-probe. No rule, trigger or description
changes.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. The test is retrieval: can a reader tell which interface to name on each OS,
      what happens with a macOS bridge, and what was measured.
- [x] RED (text): the pre-edit SKILL.md has 1 line "On Linux and macOS the capture binds to a bridge" and 0
      lines naming a member port, against the `remove_neighbour` lines (4) as the control that the grep read
      the file.
- [x] GREEN (text): the edited SKILL.md has 0 such lines and 3 naming a member port; control unchanged (4).
- [x] GREEN (retrieval, quote-back), first text: both tiers (opus, haiku; 2 cells) answered which interface on
      macOS and Linux, what a macOS bridge does and why, what was measured, and what to do first, each with a
      direct quote. Gap CLOSED: opus read "the real macOS DHCP client" as possibly a guest VM; the text now
      says it was the VM's own client and that a separate guest is not yet measured.
- [x] GREEN (retrieval, quote-back), second text: both tiers (opus, haiku; 2 cells) answered all three
      questions correctly with direct quotes. Gaps CLOSED in the final text: which interface the capture ran
      on (the `feth` peer, the bridge member) and that the forwarded-replies claim was measured (the bridge
      saw none of them, `tcpdump` agreeing).
- [x] Twin parity: the repo gate allowed the tool-repo commit against this side's text.
- [x] Describes the latest release only: no history wording (no longer, previously, used to, formerly) in the
      added lines.
- [x] No address, hostname or path added; no session narrative or private provenance here.
- [x] Skill gaps reported by the probes, each decided:
      - How to tell which member of a bridge is the guest's (both tiers): DECLINED - host-specific; the
        hypervisor names its ports, `ifconfig bridgeN` lists them, and the refusal message names the remedy.
      - The literal "pass br0" on Linux (haiku): DECLINED - "binds to a bridge" plus `interface="br0"` in the
        example above the paragraph already shows it.
      - Call signature and what `dhcp_capture_available()` checks (both tiers): DECLINED - covered earlier in
        the same section (`observe_dhcp_first_reachable(mac, interface="br0")`, "Ask
        `dhcp_capture_available()` first").
      - Whether the refusal is name-based and macOS-only, and when it fires (opus): DECLINED - the sentence
        sits under "On macOS" and names the `bridgeN` pattern; timing does not change the handler.
      - The provenance stamp's two readings (both tiers): DECLINED - the catalogue's standard version-and-date
        stamp.
      - Runner provider, macOS version and topology details (both tiers): DECLINED - "a macOS runner VM" is the
        claim made; the reader does not act on the version, and the topology lives in the tool repo's live
        test.
      - How to "confirm" the first capture (both tiers): DECLINED - as in the previous checklist; the reader
        compares the address returned with the one the machine reports.
