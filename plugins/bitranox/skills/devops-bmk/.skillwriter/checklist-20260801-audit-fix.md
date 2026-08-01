# skill-writer checklist - devops-bmk (2026-08-01, isolated-audit fix)

Source: the first clean-room sweep run by `bitranox:meta-skill-audit`. Ships with plugin 5.127.0.

- [x] WRONG: the skill justified `--refresh-package bmk` by saying a release published minutes ago
      would otherwise stay invisible. `uv tool install --help` documents `--reinstall` as already
      implying `--refresh`, so the flag was redundant and its rationale false. Flag dropped and the
      prose corrected to state what uv actually guarantees.
- [x] WRONG: section 2's bootstrap ran bare `bmk install` while section 1 and the troubleshooting
      row both say `uvx bmk install` is what works before bmk is on PATH. A reader starting at the
      section titled "Bootstrap the Makefile" got command-not-found.
- [x] UNEXECUTABLE: the private-GitHub-deps row ended `.insteadOf ...` with a literal ellipsis,
      which git would take as the rewrite target. Completed with the real URL form.
- [x] MIRRORED skill: same three fixes in `apps/utils/bmk/skills/devops-bmk`.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`, this session).
- [x] Every QUOTE checked against the real file; every executable claim re-run rather than trusted.
- [x] No session narrative or private provenance added; no machine paths, addresses or hostnames.
