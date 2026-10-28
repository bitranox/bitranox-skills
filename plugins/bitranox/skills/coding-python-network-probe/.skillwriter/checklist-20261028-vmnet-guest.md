# skill-writer checklist - python-network-probe (2026-10-28, vmnet guest measured)

Change: the macOS capture paragraph says a separate guest VM booting behind a macOS bridge is
measured (ipscout 2.5.4), and names a physical network card as the case still unmeasured.
Frontmatter unchanged; no other section touched.

- [x] Receipt held (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: reference. Test: RED as a text check of the pre-edit file (an EDIT; the
      installed copy is the old text), GREEN as a quote-back retrieval probe.
- [x] RED (text, `git show HEAD:skills/python-network-probe/SKILL.md`): the paragraph reads
      "A separate guest VM booting behind a macOS bridge is not yet measured." - the claim the
      measurement now contradicts.
- [x] Mechanism claims checked against the measurement, not the prose:
      `tests/test_dhcp_macos_vmnet_live.py` (QEMU on `-netdev vmnet-shared`, capture on the
      `vmenetN` member of `bridge100`, offered address asserted equal to the bootpd lease in
      `/var/db/dhcpd_leases`, `bridge100` refused) passed 2 of 2, 0 skipped, in 3 consecutive
      rounds on each of macos-15-intel and macos-26-intel (`-accel hvf`) and macos-latest and
      macos-26 (arm64, `-accel tcg`): 24 test passes.
- [x] GREEN quote-back, `opus` (effort medium) and `haiku`, 5 questions each on the macOS
      capture section (10 cells): both quoted the governing sentence for "is a guest behind a
      macOS bridge measured" ("A separate guest VM booting behind a macOS bridge is measured
      too (ipscout 2.5.4, checked 2026-10-28)"), the member port plus "`ifconfig bridgeN` lists
      the members" for which interface to name, "A physical network card is not yet measured."
      for what is open, and NONE for an unmeasured Wi-Fi/Windows-guest case.
- [x] Gap both tiers reported, CLOSED: the runner kind for the guest measurement was unstated;
      the sentence now reads "on both Intel and Apple Silicon runner VMs". Re-probe on the final
      text, both tiers (4 cells): Q4 quoted "on both Intel and Apple Silicon runner VMs." and
      read it as virtual machines; "measured on physical Mac hardware" answered NONE / "not on
      physical hardware". No new undecided gap.
- [x] Gaps DECLINED: UTM is not named (only QEMU on `vmnet-shared` was measured; the skill
      claims nothing beyond it); telling several `vmenetN` members apart (not measured, and
      "confirm the first capture you depend on" already covers it); privilege for the guest
      capture (covered above in the same section: "root on macOS"); guest architecture,
      runner images and bridged vmnet modes (not measured, no claim made); the headline's
      version scope (both measurements are runner VMs, which the sentences now each state).
- [x] Version-history finder over the added lines: no hit.
- [x] Address sweep over the added lines: no address, MAC, home or temp path.
- [x] No session narrative or private provenance in the skill or this artifact.
