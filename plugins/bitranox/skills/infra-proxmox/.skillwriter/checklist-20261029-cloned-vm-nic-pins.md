# skill-writer checklist - infra-proxmox (row "Cloned VM has no network")

- [x] Change: one new row in the troubleshooting table, after "Cloned VM missing a disk".
- [x] Receipt held (skill_receipt.py start meta-skill-writer) before the edit was committed.
- [x] Mechanism claims measured, not reasoned: a linked clone of a PVE 9.1-installed template whose
      installer-written `50-pmx-nic*.link` files matched `MACAddress=` booted with ens18/ens19 and
      a port-less vmbr0; after rewriting them to `Path=` the next clone booted with nic0/nic1.
      On that clone `ip -br link` lists nic0/nic1, `bridge link` shows nic0 as a port of vmbr0,
      and the file reads `[Match] Path=pci-0000:06:12.0 Type=ether`, `[Link] Name=nic0`. The
      netplan analogue is marked "not measured here" in the row.
- [x] RED as a text check (opus, pre-edit text): NONE - the nearest row ("NIC names changed")
      points at pinning, which is the opposite of what a template needs.
- [x] GREEN quote-back: opus and haiku both quote the row for cause and fix.
- [x] Skill gaps from GREEN, decided: example file content CLOSED (`[Match]`/`[Link]` lines incl.
      `Type=ether`, taken from the live file); check on the clone CLOSED (`ip -br link`,
      `bridge link`); linked vs full clone CLOSED ("linked or full": both get new MACs).
      DECLINED: an initramfs update or udev reload before `qm template` (the template's own
      next boot and every clone's first boot apply the files; the measured clone needed no
      step); keeping the filenames (the row says rewrite each file, not rename); 9.2 coverage
      (the row says measured on 9.1).
- [x] Re-probe after the fixes: opus and haiku quote the example and the check.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense, table re-padded with reformat_tables.py and canonical.
- [x] The PCI path is a generic QEMU slot path, not a private value; no host or address added.
