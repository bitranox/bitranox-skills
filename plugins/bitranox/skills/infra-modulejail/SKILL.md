---
name: infra-modulejail
description: Use when hardening a Linux host by preventing the kernel from loading modules it does not need - kernel-module allowlist or blacklist, modprobe install override, reducing request_module/autoload attack surface, CIS module-blacklisting - especially on a remote or relocating host with no console and no out-of-band power, where a wrong module list can leave it unbootable and unreachable.
---

# infra-modulejail

## Overview

Reduce a host's kernel attack surface by blocking every module except a proven-needed
set ("jailing" the module namespace). The danger is not the blocking, it is bricking a
host you cannot reach. This skill is the safe procedure.

**Core principles:**

1. **Allowlist, then block the complement.** Do NOT hand-pick a short blocklist of
   "obviously unused" modules (gpu, sound, bluetooth) - that barely dents the surface.
   Build the KEEP set, then block everything else. A real jail blocks the large majority
   of the tree.
2. **Keep the block RUNTIME-ONLY. Never bake it into the initramfs.** This is what makes
   a mistake survivable (see "Why runtime-only").
3. **Prove three invariants against a dry-run before you apply**, and validate the gate
   against a known-negative.
4. **A host with no console/OOB power is not hardened until a real reboot proved it while
   you could still recover it.**

## When to use / not

Use when: locking down a server, appliance, hypervisor (Proxmox/KVM host), or an
about-to-relocate box; responding to a `request_module()`/autoload CVE class (obscure
network protocols - `dccp`, `sctp`, `rds`, `tipc` - or filesystems autoloaded on mount).

Do NOT use on a machine whose exact hardware/workload you cannot enumerate and reboot-test
first, or where you have no way to recover a bad boot (no console, no OOB power, no on-site
hands) - fix the recovery path first.

## The safe method

### 1. Build the KEEP set, then its dependency closure

KEEP = (currently loaded) UNION (a baseline profile) UNION (your explicit whitelist).

```bash
# loaded right now - bring up every service/guest and exercise both NICs first
lsmod | awk 'NR>1{print $1}' | sort -u > keep.raw
# add a baseline (boot + net + storage + your stack) and your hardware whitelist to keep.raw
```

Then expand EVERY keep module to its full dependency closure and keep the closure too -
blocking a dependency of a kept module silently breaks the kept module:

```bash
# resolve depends recursively to convergence
resolve() { modprobe --show-depends "$1" 2>/dev/null | awk '/^insmod/{print $2}' \
            | xargs -rn1 basename | sed 's/\.ko.*//'; }
```

Feed each name through `resolve` and re-feed new names until the set stops growing.

### 2. BLOCK = all installed modules MINUS the KEEP closure

```bash
find "/lib/modules/$(uname -r)" -name '*.ko*' \
  | sed -E 's#.*/##; s#\.ko(\.[gxz]+)?$##' | sort -u > all.mods
comm -23 all.mods keep.closure > block.list
```

### 3. Apply as a RUNTIME modprobe override - not the initramfs

```bash
# one directive per line; comments on their OWN line (modprobe.d does not parse
# a trailing inline #). /bin/true = exit 0, silent; use /bin/false to make a
# manual `modprobe X` fail loudly and leave a journal trace.
awk '{print "install", $1, "/bin/true"}' block.list \
  > /etc/modprobe.d/modulejail-blacklist.conf
depmod -a
```

Do **not** run `update-initramfs`/`proxmox-boot-tool refresh` to "make it permanent" - the
runtime file already blocks every post-boot load. `install` overrides only intercept FUTURE
loads, so nothing already running is touched and the live host is safe by construction. The
file takes effect on the NEXT load attempt immediately - `modprobe` re-reads `modprobe.d` on
every call - so no reboot is needed to START blocking; the reboot in step 5 only proves the
host still BOOTS with the block in place.

### 4. The invariant gate (run against the dry-run BEFORE trusting it)

Refuse to apply unless ALL hold:

- **No currently-loaded module is in `block.list`.**
- **No whitelisted module or anything in its dependency closure is in `block.list`.**
- **No boot-critical module is in `block.list`** (see the tier below).
- **`block.list` is non-empty** (an empty list means the pipeline failed and you have a
  false "success").

**Validate the gate against a known-negative:** drop one obviously-required module (e.g.
`veth` on an LXC host, or your root-disk controller) from the KEEP set and re-run the gate -
it MUST flag it. A gate that passes your removal is not checking anything. See
`bitranox:process-review-verification-before-completion`.

### 5. The reboot-while-recoverable gate (mandatory)

Before the host ever goes somewhere you cannot reach it: `reboot` it for real (at least one
cold power cycle), while you still have console or power access, and confirm afterward - SSH
reachable, every service/guest up, storage healthy, both NICs up, `journalctl -k -b` clean
of new module errors, and a differential check that a blocked module refuses while a kept one
still loads (below). Repeat 2-3 times. A config that was only written, never cold-booted, is
not validated.

## Why runtime-only, not initramfs

A runtime `/etc/modprobe.d` block takes effect AFTER the kernel and initramfs have already
mounted root and started userspace. So the worst case of a wrong entry is: the host boots,
the network comes up, SSH works, and you fix the file over SSH. Bake the same block into the
initramfs and a wrong entry can stop the machine BEFORE the root disk or the NIC driver
loads - dead before SSH, and on a console-less/no-OOB-power host that is unrecoverable. The
whole point of keeping it runtime-only is that a mistake stays an SSH-fixable annoyance
instead of a brick.

## Boot-critical tier - hard-exempt, never block

Identify and exempt (verify, do not assume): the root-disk controller
(`ethtool -i`/`readlink /sys/.../driver`; `ahci`, `nvme`, ...), the storage stack
(`zfs`/`spl` matched to the running kernel; md/dm/lvm), the NIC driver actually carrying
your SSH, and - if WiFi is the post-move uplink - its driver plus `cfg80211`/`mac80211`/
`rfkill`. On a bridged/LXC host also keep `bridge`, `veth`, `8021q`, and the netfilter
modules your firewall uses. On a KVM host keep `kvm`, `kvm_intel`/`kvm_amd`, `vhost_net`,
`tun`, `vfio*`.

## Verify (differential, not by inspection)

```bash
modprobe -n -v dccp     # a BLOCKED name -> resolves to /bin/true (or /bin/false); does not load
modprobe -n -v veth     # a KEPT name    -> resolves to a real insmod path
```

Re-run any whitelist change through steps 1-4 and regenerate the file; the generated
`/etc/modprobe.d/modulejail-blacklist.conf` is host-specific and per-kernel.

## Common mistakes

| Mistake                                          | Consequence                                                  |
|--------------------------------------------------|--------------------------------------------------------------|
| Baking the block into the initramfs              | A wrong entry bricks early boot before SSH - unrecoverable   |
| Hand-picking a short blocklist                   | Barely reduces attack surface; misses the autoloaded classes |
| Blocking by name without the dependency closure  | Kills a dependency of a kept module; kept driver breaks      |
| `blacklist X` instead of `install X /bin/true`   | `blacklist` only stops alias autoload, not an explicit load  |
| Trailing inline `# comment` on an `install` line | modprobe.d mis-parses it; block silently wrong               |
| Empty `block.list` read as success               | Pipeline failed; you hardened nothing and think you did      |
| Relocating before a real cold-reboot test        | First real boot at the unreachable site is the test          |

## Real-world impact

On a 2-NIC LXC host, this jailed ~97% of the module tree (thousands of modules blocked)
with every guest, both NICs, and the pool unaffected across repeated cold reboots. The
safety came entirely from runtime-only + the invariant gate + the reboot-recoverable gate,
not from the block itself.
