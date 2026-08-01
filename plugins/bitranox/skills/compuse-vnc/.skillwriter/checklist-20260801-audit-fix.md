# skill-writer checklist - compuse-vnc (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG: the skill sent readers to `bitranox:compuse-ssh` for SSH-tunnelling to a console port.
      That skill has zero tunnelling content (verified: 0 matches for `ssh -L`, port-forward or
      tunnel). The instruction is now self-sufficient - it gives the actual `ssh -N -L` line and
      says why the forward binds to the host's loopback.
- [x] MIRRORED skill: same fix in `apps/utils/vnc-remote-control/skills/vnc-remote-control`.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
