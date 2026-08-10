# skill-writer checklist - infra-proxmox: ifreload dry-run flag fix (2026-08-10)

Fix: the Safety table recommended `ifreload -a --test`, a flag ifupdown2 does not have.

## PLAN
- [x] Skill type: REFERENCE cell (a concrete command) - the test is ground-truth execution
      on a real node, not a pressure scenario.
- [x] Scope: one-cell wording fix in the existing SKILL.md; no new supporting file.

## RED - baseline / ground truth
- [x] Verified on a live PVE 9 node (ifupdown2): `ifreload -a --test` ->
      `error: unrecognized arguments: --test` (rc=2); `ifreload -a -n` -> rc=0. The shipped
      text told the reader to run a command that fails closed on the target.

## GREEN
- [x] The cell now recommends `ifreload -a -n` (the actual no-act/dry-run flag) and notes
      ifupdown2 has no `--test`, so a later reader does not revert it.
- [x] Frontmatter untouched; description still trigger-first.
- [x] No `@` links; command names only.
- [x] ASCII only, no typographic tells.

## REFACTOR
- [x] Checked every ifreload mention in the skill (SKILL.md + appendices): only this cell
      carried `--test`; the appendix already used plain `ifreload -a`.

## Quality
- [x] Present tense; no session narrative or private provenance.
- [x] No real host/IP/path - command flags only.
- [x] Table row realigned by the table formatter.

## Deployment
- [x] Security review: a flag change, no secrets, hostnames, or PII.
- [x] Plugin version bumped (PATCH) in the same change.
- [x] Derived artifacts unaffected (name/description unchanged); regenerated and verified no
      drift.
- [x] repo-gate.py --ci green.
- [x] Additive commit to master; history append-only, no force-push.
