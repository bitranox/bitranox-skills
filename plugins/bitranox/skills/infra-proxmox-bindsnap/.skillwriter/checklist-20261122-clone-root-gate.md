# checklist - clone carries bind mounts for root@pam only; a bind rootfs is never cloned

Quick reference row "Clone a bind-mount CT", section 6 and Troubleshooting follow pve-bindsnap
1.10.0: only `root@pam` carries a bind/device `mpN` (any other user is refused unless every bind
is excluded), and a CT whose rootfs is a bind/device mount is never cloned. Troubleshooting splits
the bare `unable to clone mountpoint 'mpN' (type bind)` (override not active) from the new
root@pam refusal and the rootfs refusal. Same change in the twin (pve-bindsnap
`skills/proxmox-bindsnap`).

Decisions: d-20261122-96b7fd40, d-20261122-bfd7abbb, d-20261122-4251c6ec

## RED

- [x] Skill decisions read first (`skill_decisions.py show`, rejected/removed in full): live rules
      judge-by-checksum-not-version, name-no-vetted-range, raw-zfs-safety-snapshot,
      gate-covers-create-only, vzdump-backup-flag, vzdump-restore-over-ct; none touches clone.
- [x] Behaviour measured first on a pve-container 6.1.26 lab node (stock, 1.9.2, 1.10.0 build):
      a non-root API token with VM.Clone got `mp0` carried under 1.9.2 and HTTP 500 with the
      root@pam message under 1.10.0; with `BINDSNAP-EXCLUDE: mp0` its clone succeeded without
      `mp0`; `pct clone` as root@pam carried `mp0`; a bind-rootfs CT cloned into a shared rootfs
      under 1.9.2 and was refused (rc 2, no CT) under 1.10.0. The source's hostname file was NOT
      rewritten by the 1.9.2 clone, so no text claims that.
- [x] RED (opus and haiku, the installed skill, two situations: alice@pve hits the root@pam
      refusal; root clones a CT with `rootfs: /opt/ct305-root`): neither found the root@pam rule
      in the skill (opus: "The skill never mentions that carrying a bind/device mount in a clone
      is limited to root@pam"); both saw the Troubleshooting row "not installed / build untested"
      contradicted by the journal; both called the rootfs case undefined (haiku guessed it is
      carried).

## GREEN

- [x] GREEN (opus and haiku, edited sections pasted, same two situations): both told alice the
      overlay works and gave the two routes (root@pam, or exclude every bind mount); both
      refused to reinstall or vet for the rootfs case, quoting the new rootfs row.
- [x] Closed from GREEN gaps: the quick-reference row read as "a non-root clone drops the binds"
      (opus) -> now "any other user is refused unless every bind is excluded"; the bare-message
      row could swallow the rootfs message (both) -> "(`mpN`, never `rootfs`)"; root@pam tokens
      ambiguous (opus) -> rule stated as "whoever may set a bind mount may carry it"; leftovers of
      a rootfs refusal (both) -> "creates nothing".
- [x] Quote-back (opus and haiku, 5 questions: non-root without exclude, rootfs cause, leftovers,
      the rule, non-root with every bind excluded): 5 of 5 verbatim on each tier.

## REFACTOR

- [x] Declined, covered elsewhere in the skill: where the exclude goes and its syntax (section 4
      bullet and the section 6 Notes paragraph, both left out of the quote-back excerpt); that a
      Notes directive also governs later snapshots (section 4, "overrides the Notes default").
- [x] Declined, owned by bitranox:infra-proxmox: which roles may edit CT Notes, the clone
      privileges a non-root user needs besides root, copying a host-directory rootfs by hand.
- [x] Declined, stock behaviour the overlay does not change: `devN` lines go through upstream's
      own "copy everything else" branch (read in upstream's `clone_vm`, not tested); not part of
      this rule.
- [x] Width and fence check over the added lines printed nothing (the 117-column refusal message
      moved into a fenced block); tables reformatted; ASCII only; no private host names.
- [x] Description untouched (no YAML change).
- [x] Tool repo twin `skills/proxmox-bindsnap/SKILL.md` written with the same body;
      `repo-gate.py --mirrors` run after the copy.

## Round 2 (docs/skill review and PR #2 audit, before release)

- [x] Review findings fixed in section 6, 7, Quick reference and Troubleshooting: a `--snapname`
      clone reads the directive frozen into that snapshot (Notes before the snapshot, or the
      description given when taking it, never an existing snapshot's description); a managed
      `mpN` that snapshot excluded is left out with `TASK WARNINGS` (pve-bindsnap 1.10.0 fix,
      t/18); a `root@pam` API token counts as another user (exact `$authuser eq 'root@pam'`
      compare, read in the code); `devN` lines are copied by stock code and cannot be excluded
      (read in upstream `clone_vm`); a refused clone starts no task; uninstall: act on bind-CT
      snapshots first (stock delete/rollback die on the bind path, per the repo's design notes);
      troubleshooting rows match `(type bind|device)`; install-apt link is a GitHub URL; the
      description names the new "only allowed for root@pam" refusal.
- [x] Quote-back (opus and haiku, 7 questions: root API token, stale snapshot vs new Notes
      line, left-out volume, devN, before uninstall, type device, where a refused clone's log
      is): 7 of 7 answered from the right line on each tier. Both asked whether adding the line
      to an existing snapshot's description works -> now stated: never.
- [x] Tool repo twin carries `name: proxmox-bindsnap` (its dir name, as its README invokes it);
      it had carried this copy's `infra-` name since 1.2.2. `repo-gate.py --mirrors`: in sync.
- [x] Description 664 characters; ASCII only; tables reformatted.
