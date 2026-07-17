# skill-writer checklist - infra-proxmox (2026-07-17, routing rows now match the files: VM vs CT migration split, appendix-g routed)

Change: Two hub-routing defects. The row 'Migrate a VM/CT (online/offline/HA) -> ch10-qemu/migration.md' promised
container coverage from a file with ZERO container/pct mentions; real CT migration lives in
ch11-containers/backup-migration-config.md, which had no row. And appendix-g-markdown-primer.md existed
with no routing row anywhere, while its siblings appendix-a through -f all have one.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: grep -ci 'container|pct' ch10-qemu/migration.md returned 0, so the row routes a CT question to a
      VM-only file; grep -c 'appendix-g' SKILL.md returned 0 against an existing file
- [x] GREEN: split the row into a VM row and a CT row pointing at the file that has the content; added an
      appendix-g row. Verified the rest of the two-tier structure is intact (chapters route via
      _index.md, so per-chapter files stay reachable)
- [x] Verified against ground truth before editing (not taken from the review agent's report on faith)
- [x] CSO description: unchanged (body edit only)
- [x] Security scan: prose/doc change only, no secrets, hostnames, or private paths
- [x] Docs describe current state: no legacy/migration narrative introduced
