# Review checklist 2026-10-30: pve-bindsnap 1.3.0 vetted range

Change: section 5's "As of pve-bindsnap 1.2.0 it holds pve-container 6.1.10 and 6.1.12" names
the 1.3.0 range, pve-container 6.0.18 to 6.1.16, each with the libpve-guest-common-perl version
it shipped with. Mirror of the same edit in pve-bindsnap's `skills/proxmox-bindsnap/SKILL.md`.

Files: `SKILL.md` (one paragraph in section 5).

## Claims and their evidence

- [x] Range and both guards: pve-bindsnap 1.3.0 `%KNOWN_GOOD_CHECKSUMS` (11 keys) and
      `%KNOWN_GOOD_CLONE_CHECKSUMS` (9 keys); each key was measured on its own nested PVE node
      (15 nodes, 6.0.18 to 6.1.16) and every case of docs/testing.md passed there, then again
      with the release module (pve-bindsnap docs/test-results.md, 1.3.0 section).
- [x] "PVE 9.1 and 9.2": `pveversion -v` on the nodes, pve-manager 9.1.1 and 9.2.2 to 9.2.25.
- [x] The pairing caveat: the snapshot checksum hashes `AbstractConfig.pm` from
      libpve-guest-common-perl; measured offline, 6.1.0 with guest-common 6.0.2 hashes to a
      listed key and with 6.0.3 to none.

## Mechanical checks

- [x] Edited lines ASCII only and at most 97 columns; description unchanged.
- [x] Body identical to the pve-bindsnap twin past the frontmatter (`diff`).

## Probes (bitranox:baseline-probe, text only, opus)

- [x] RED on the first 1.3.0 wording ("every guard state from 6.0.18 to 6.1.16"): the reader
      took 6.1.3 with guest-common 6.0.2 as "likely vetted" from the version range alone and
      flagged that the range names pve-container only while the checksum also depends on
      guest-common.
- [x] GREEN on the final wording: for 6.1.3 with guest-common 6.0.3 the reader no longer claims
      vetted and routes to the list row and the node's journal line; for the shipped pairing it
      reads the claim as covered and still defers to the overlay. Remaining gaps it named
      (section 2, the two guards, TEST mode) are defined elsewhere in the skill, outside the
      excerpt given.
