# Skill-writer checklist: the blacklist is in the initramfs and per-kernel; a proven blocked control (2026-10-09)

Scope: core principle 2, step 1 `resolve`, step 4 control line, step 5, the former "Why
runtime-only, not initramfs" section (replaced), Verify, Common mistakes, Real-world impact.

Corrected claims, each against a measurement on a Proxmox VE node (kernel 7.0.14-5-pve):

- `lsinitramfs /boot/initrd.img-$(uname -r)` lists `etc/modprobe.d/modulejail-blacklist.conf`:
  initramfs-tools copies `/etc/modprobe.d` into every initramfs built after the file exists. The
  text claimed the block was runtime-only and told the reader not to rebuild the initramfs.
- `modinfo -n dccp` -> "Module dccp not found"; `sctp`, `rds`, `tipc` resolve. The text used
  `dccp` as the known-BLOCKED control.
- A list generated on 7.0.14-14 blocked `phylink`; on 7.0.14-20 the kept `r8169` depends on it and
  the NIC failed at boot with `Unknown symbol`. The text had no per-kernel guard.

## PLAN

- [x] Skill type: technique (operational procedure). Test approach: application scenario (a
      jailed off-site node about to receive a kernel upgrade) with three concrete questions:
      initramfs membership, what to do around the reboot, the differential verify control.
- [x] Scope: self-contained SKILL.md; no supporting files added.

## RED

- [x] Arm A, pre-edit text (sonnet, inert baseline-probe): doubted "runtime-only" from its own
      knowledge, but the text steered it into a workaround to keep the file OUT of the initramfs
      ("mv /etc/modprobe.d/modulejail-blacklist.conf ... the hook now builds the initrd without
      the jail", then "Restore the jail as runtime-only") and to forbid any update-initramfs. No
      persistent kernel-install guard, a one-off check of lsmod plus named modules only, run with
      the blacklist applied (`-C $C`), and dccp flagged as stale only "from memory". Its Skill gaps
      named the initramfs contradiction, the unaddressed per-kernel list and the stale dccp.
- [x] Arm B, no skill (sonnet): knew initramfs-tools copies modprobe.d, pinned the kernel and
      checked the closure by hand once; offered stripping the file from the initramfs as an
      option; no persistent kernel-install hook; guessed `ax25` as a control.
- [x] Inherited-context check: the lesson is not in this machine's cascade; the installed copy of
      this skill teaches the OLD claim, so a RED arm reading it fails in the expected direction and
      the GREEN arms were told not to load it and were judged on quoted excerpt lines.

## GREEN

- [x] Principle 2 rewritten: the block reaches early boot and is computed for one kernel.
- [x] Step 5: install, then `update-initramfs -u -k all` + `proxmox-boot-tool refresh` + an
      `lsinitramfs` check, so the step-6 reboot tests the boot every later initramfs has; install
      the kernel guard and pin in the same session.
- [x] New section "The blacklist is in the initramfs, and it is per-kernel": a
      `/etc/kernel/postinst.d/05-modulejail-closure` hook (closure of keep.list on the NEW kernel
      via `modprobe -S <ver> --show-depends -C /dev/null`, refuses with exit 1 and "DO NOT boot"),
      a self-test of the hook against a copy of the blacklist, rebuilding for an unbooted kernel,
      and `proxmox-boot-tool kernel pin` / `--next-boot` with the recovery-path requirement.
- [x] Step 1 `resolve` unions a config-free read so an installed `install` line cannot hide a
      blocked dependency during regeneration.
- [x] dccp replaced by `sctp`; new "Proving the blocked control" check: exists on this kernel
      (`--show-depends -C /dev/null` prints an insmod line), is named by the blacklist, and
      modprobe returns the `install` line - each failure prints CONTROL INVALID / JAIL BROKEN and
      exits 1 inside a subshell.
- [x] GREEN arm (sonnet, edited excerpt): Q1 yes, not runtime-only, quoting "not running
      `update-initramfs` yourself keeps nothing out"; no move-aside; pinned 7.0.14-5, installed
      and self-tested the hook, re-ran it for 7.0.15-1, refused the trial boot without a recovery
      path; ran the control subshell with sctp and said not to use dccp.
- [x] Hook verified by execution, not review: a fake `modprobe` replaying per-kernel dependency
      maps; old kernel with phylink blocked -> rc 0; new kernel where r8169 needs phylink -> rc 1
      naming phylink; a kept module absent on the new kernel -> rc 1 naming it; nothing blocked
      in the closure -> rc 0. All shell blocks pass `shellcheck -S warning`.

## REFACTOR

- [x] Skill gaps from GREEN, decided:
  - CLOSED: keep.list contents and retrofit on an already-jailed host (whitelist + baseline +
    boot-critical tier, never lsmod; write it before the next kernel update).
  - CLOSED: the boot-critical tier is part of keep.list, so the hook covers storage and NIC.
  - CLOSED: pinning after the upgrade but before any reboot is still valid.
  - DECLINED: hook ordering against the initramfs build and whether a failing hook aborts the
    package - the text makes the message the guard, deliberately independent of both.
  - DECLINED: proxmox-boot-tool on hosts without it - out of scope for this correction.
  - DECLINED: a remote fallback for the trial boot - the skill's posture is that a host with no
    recovery path does not boot an unproven kernel; adding one would loosen it.
- [x] RED vs GREEN, both directions: GREEN lost the no-skill arm's watchdog/dead-man idea, which
      the skill does not prescribe (a boot that hangs in the initramfs is not covered by it);
      nothing the pre-edit arm got right is missing from GREEN.
- [x] Quote-back on haiku (an already-jailed node, kernel installed, not rebooted): each of four
      answers quoted the governing line - initramfs carries it and no move-aside; keep.list is
      whitelist + baseline + boot-critical, not lsmod; pin after the upgrade is still valid;
      `--show-depends dccp` returning an install line is not proof, run the sctp control subshell.
      Two gaps it reported were CLOSED: run the hook by hand for a kernel installed before it
      existed; moving the file out of `/etc/modprobe.d` around an upgrade is named alongside
      stripping it from the initramfs. Its other gaps came from the shortened excerpt it was
      given (undefined baseline/tier, hook body omitted) and are answered by the full text.

## Security and hygiene

- [x] No secret, real hostname, address or private path in the diff; kernel versions are generic
      Proxmox release strings.
- [x] No frontmatter, `name` or description change; no derived artifact to regenerate.
- [x] Added lines ASCII only.
