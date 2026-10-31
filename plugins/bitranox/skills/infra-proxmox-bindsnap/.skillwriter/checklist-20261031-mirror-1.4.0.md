# skill-writer checklist - infra-proxmox-bindsnap (2026-10-31, mirror of pve-bindsnap 1.4.0)

Source: `skills/proxmox-bindsnap/SKILL.md` of `bitranox/pve-bindsnap`, branch `deb-1.4.0`
(commit 296342c, not yet pushed or released). The copy is byte-identical to the source; the
`name:` line is the same on both sides. It also brings the 1.3.0 text this mirror never got
(the `snapshot feature is not available` symptom and the 6.0.18 to 6.1.16 range).

- [x] Skill type: reference. The change documents a second install method (the apt package via
      `install-apt.sh`), its removal, the per-build clone variants, and corrects two older slips
      (a section reference, the known-BAD advice omitting libpve-guest-common-perl).
- [x] GREEN probe: an agent given only this SKILL.md answered the operator questions correctly:
      the apt install command, migrating an install.sh node, full removal after a curl install
      (`| bash -s -- --remove --purge`), uninstall.sh refusing while the package is installed,
      reading the clone variant from the journal, and that a clone behaves like the node's own.
      Its gaps (no explicit "do not uninstall first", unexplained `--no-install` / `--remove`
      alone, "same files" without the package path, "Either" after three methods) were fixed
      in the source before this copy was taken. No RED arm: the apt method did not exist before,
      so any agent without the text fails it by construction.
- [x] Every option named matches `install-apt.sh --help` on the branch, and every path matches
      the package payload and `install.sh` (`/usr/share/perl5`, `/usr/local/lib/site_perl`).
- [x] `repo-gate.py --mirror-of` reports DRIFT (exit 1) against the published twin, which is
      still 1.3.0: expected until pve-bindsnap 1.4.0 is pushed. Against the branch text the
      two files compare equal (`cmp` exit 0).
- [x] Frontmatter untouched: `description` unchanged (553 characters), so no routing keyword
      moved.
- [x] ASCII only (no character above 0x7F); tables re-padded with reformat_tables.py.
- [x] No address, MAC, hostname or private path added.
- [x] No session narrative or private provenance added.
