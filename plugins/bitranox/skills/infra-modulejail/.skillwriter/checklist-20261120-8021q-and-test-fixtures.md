# checklist - 8021q's dependencies and test fixtures on a jailed host

One queued contribution (corroborated by facts from two projects): after the boot-critical tier,
`8021q` needs `garp` and `mrp` (blocking them makes `type vlan` fail "Unknown device type"), and
a test fixture never justifies loosening the jail: a `veth` pair as the fake NIC, a raw
`AF_PACKET` peer for tagged frames.

Decisions: d-20261120-b87e5c68

## RED

- [x] Skill decisions read first: none rejected or removed.
- [x] Text check of the pre-edit file: `garp` 0 hits, `dummy` 0 hits, `PACKET_AUXDATA` 0 hits;
      `8021q` appeared only in the keep list.
- [x] Dependency read on a node (read-only): `modinfo -F depends 8021q` on a Proxmox node printed
      `garp,mrp`.

## GREEN

- [x] Quote-back probe (opus, haiku): M1 and M2 answered with the new lines; no NONE.

## REFACTOR

- [x] Closed (opus): the received outer tag on a veth is out of band; the text now says to read
      it from `PACKET_AUXDATA` and to set the veth MTU to 1600 (both from the measured fact).
- [x] Declined (haiku): commands to drop and restore carrier - `ip link set ... down/up` on the
      peer is standard; the paragraph names the peer as the switch.
- [x] Width, fence and ASCII checks on the added lines clean.
