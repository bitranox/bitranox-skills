# Skill-writer checklist: drop the no-op `depmod -a` after a modprobe.d install (2026-10-05)

Scope: step 5, "Apply as a RUNTIME modprobe override". Before, the install command was followed
by a bare `depmod -a` with no explanation. After: `depmod -a` is removed from the command block
and the prose explicitly says not to run it, stating why (it rebuilds `modules.dep` from the
module files under `/lib/modules/$(uname -r)`, which a `modprobe.d` blacklist/install directive
never touches).

## PLAN

- [x] Skill type: reference/technique (an operational procedure). Test approach: verify the
      factual claim (does `depmod -a` affect `modprobe.d` blacklist/install directives) against
      what each tool actually reads, not a pressure scenario.
- [x] Re-checked the claim: `depmod` rebuilds the kernel module dependency database
      (`modules.dep` and friends) from the `.ko` files present under `/lib/modules/<kernel>`; a
      `modprobe.d` blacklist/install override is read by `modprobe` directly at load time and
      never consulted by `depmod`. Installing a new `/etc/modprobe.d/*.conf` file changes neither
      the module files nor their recorded dependencies, so `depmod -a` has nothing to do here.
      This matches the step's own later sentence ("modprobe re-reads modprobe.d on every call"),
      which already says no rebuild step is needed for the override to take effect.

## GREEN (the fix)

- [x] Removed `depmod -a` from the `install -m 0644 ...` command block.
- [x] Added one sentence to the surrounding "do not" prose, explaining what `depmod -a` actually
      does and why it is a no-op for this install, right beside the existing "do not run
      update-initramfs" guidance it now reads alongside.

## Verification

- [x] Re-read the whole step after the edit: the command block now installs the file only, and
      the prose consistently argues that nothing beyond the `install` is needed (no reboot
      needed to start blocking, no depmod needed, no initramfs rebuild needed) - no contradiction
      left between the removed command and the step's own explanation.

## Security and hygiene

- [x] No secret, real hostname, address or private path in the diff.
- [x] No frontmatter, `name`, or trigger text changed; no derived artifact needs regeneration.
- [x] Added lines ASCII only.
