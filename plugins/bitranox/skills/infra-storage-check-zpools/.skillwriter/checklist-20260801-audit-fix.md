# skill-writer checklist - infra-storage-check-zpools (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG: the production-install block ran `service-install` and `alias-create` unconditionally,
      two paragraphs after the skill states that the first needs systemd and the second is
      Linux-only - in a skill that treats FreeBSD, macOS and WSL as valid ZFS hosts. Both lines are
      now annotated in the block, and the prose says to drop them on a non-Linux host and schedule
      the check with whatever that host uses.
- [x] MIRRORED skill: same fix in `apps/utils/check_zpools/skills/check-zpools`.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
