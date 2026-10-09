---
name: infra-modulejail
description: Use when hardening a Linux host by preventing the kernel from loading modules it does not need - kernel-module allowlist or blacklist, modprobe install override, reducing request_module/autoload attack surface, CIS module-blacklisting - especially on a remote or relocating host with no console and no out-of-band power, where a wrong module list can leave it unbootable and unreachable. Also use when a module silently refuses to load on an already-jailed host - modprobe exits 0 having loaded nothing, lsmod stays empty, a systemd unit fails with "Dependency failed", or journalctl logs the module as "blocked".
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
2. **The block reaches early boot, and it is computed for ONE kernel.** On Debian/Proxmox
   every initramfs built after the file exists carries it, so a wrong entry can stop the
   boot before SSH. Gate every NEW kernel's dependency closure before booting it, and keep
   the proven kernel pinned until a guarded boot of the new one succeeds (see "The blacklist
   is in the initramfs, and it is per-kernel").
3. **Gate the exact file you will install BEFORE it goes near `/etc/modprobe.d`**, and
   validate the gate against a known-negative.
4. **A host with no console/OOB power is not hardened until a real reboot proved it while
   you could still recover it.**

## When to use / not

Use when: locking down a server, appliance, hypervisor (Proxmox/KVM host), or an
about-to-relocate box; responding to a `request_module()`/autoload CVE class (obscure
network protocols - `sctp`, `rds`, `tipc`, and `dccp` on kernels that still ship it - or
filesystems autoloaded on mount).

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
# `tr` to the underscore form: module FILE names are hyphenated (snd-hda-intel.ko) while
# lsmod/modprobe names are underscored, and `comm` below compares the two sets literally.
# Two reads, unioned: with the system config (softdeps from modprobe.d), and with -C /dev/null
# (no config) - when regenerating on a jailed host, an installed `install` line can stand in
# for a blocked dependency's insmod line, and that dependency would stay blocked.
resolve() { { modprobe --show-depends "$1"; modprobe --show-depends -C /dev/null "$1"; } \
            2>/dev/null | awk '/^insmod/{print $2}' \
            | xargs -rn1 basename | sed 's/\.ko.*//' | tr '-' '_'; }
```

Feed each name through `resolve` and re-feed new names until the set stops growing. That is
the loop, and it has to WRITE the file the next step reads:

```bash
# Call `resolve` in THIS shell. Never hand it to a child through `xargs sh -c`: on Debian and
# Proxmox `sh` is dash, which never sees an exported bash function, so every call fails
# "resolve: not found", the set never grows, and the kept modules' dependencies land in block.list.
LC_ALL=C sort -u keep.raw > keep.closure
while :; do
  before=$(wc -l < keep.closure)
  while read -r m; do resolve "$m"; done < keep.closure \
    | cat - keep.closure | LC_ALL=C sort -u > keep.next
  mv keep.next keep.closure
  [ "$(wc -l < keep.closure)" = "$before" ] && break
done
```

`comm` needs BOTH inputs sorted under the SAME collation and in the same name form. Sort
both with `LC_ALL=C sort -u` and normalise both to the underscore form - a mismatch on
either axis silently puts a KEPT module into `block.list`.

**The three KEEP inputs are not equally durable, and you must be able to tell them apart.**

| Source of coverage      | Durable?                                                   |
|-------------------------|------------------------------------------------------------|
| your explicit whitelist | yes - survives any regeneration                            |
| the baseline profile    | yes, but implementation-defined; READ it, do not assume it |
| currently loaded        | NO - only true of the moment the set was built             |

A module kept solely because it happened to be loaded is covered by accident. Regenerate from a
cold boot, or with the service stopped, and it moves to BLOCK - on a node nobody changed, failing
silently the next time something asks for it.

So "is this module covered?" is answered by the whitelist and the baseline, never by `lsmod` and
never by the feature working. Read the baseline rather than guessing at it - if you drive this with a generator script,
it is usually a plain variable in that script:

```bash
grep -nE "^[A-Z_]*(MINIMAL|CONSERVATIVE|DESKTOP|BASELINE)[A-Z_]*=" <your-generator>.sh
```

Measured on one node: `overlay` appears in both the whitelist and the baseline, `xt_addrtype` and
`zfs` in the whitelist only, while `ip_tables`, `iptable_nat`, `iptable_filter` and `xt_conntrack`
appear in NEITHER - they were unblocked purely because docker had them loaded when the blacklist
was last built.

### 2. BLOCK = all installed modules MINUS the KEEP closure

```bash
# Strip exactly the four real suffixes and drop anything else `*.ko*` caught (e.g. a
# stray .ko.xz.sig), then normalise to the underscore form so this set and keep.closure
# are comparable. A `[gxz]+` character class does NOT match `.zst`.
find "/lib/modules/$(uname -r)" -name '*.ko*' \
  | awk '{ n=$0; sub(/.*\//,"",n)
           if (!sub(/\.ko\.gz$/,"",n) && !sub(/\.ko\.xz$/,"",n) \
            && !sub(/\.ko\.zst$/,"",n) && !sub(/\.ko$/,"",n)) next
           gsub(/-/,"_",n); print n }' | LC_ALL=C sort -u > all.mods
comm -23 all.mods keep.closure > block.list
```

### 3. Build the candidate file - in the working directory, NOT in /etc

Write the file you intend to apply into the working directory, and nothing else. Nothing under
`/etc/modprobe.d` changes until the gate in step 4 has passed on THIS file, so a failing gate
leaves the host exactly as it was.

```bash
# one directive per line; comments on their OWN line (modprobe.d does not parse
# a trailing inline #). Two forms, and the choice decides whether the runtime-discovery
# step further down has anything to read at all:
#   /bin/true           -> exit 0, silent, and NOTHING is logged anywhere
#   the logger form     -> exit 0 to the caller, one syslog line per refusal
# Use the logger form unless /usr/bin/logger is absent. With a bare /bin/true jail,
# `journalctl -t modulejail` is empty FOREVER - and "the list is empty" is exactly the
# stop condition of the discovery loop, so it terminates on its first pass and reports
# the jail finished.
awk '{printf "install %s /bin/sh -c '"'"'/usr/bin/logger -t modulejail \"blocked: %s\" 2>/dev/null; exit 0'"'"'\n", $1, $1}' block.list \
  > candidate.conf
```

### 4. The invariant gate - on candidate.conf, BEFORE anything is written

Gate the file step 5 will install, not the list it was built from: read the blocked names back
OUT of `candidate.conf`, so a generator bug between `block.list` and the file cannot pass
unseen. Refuse to apply unless ALL hold:

- **No currently-loaded module is blocked by `candidate.conf`.**
- **No whitelisted module or anything in its dependency closure is blocked.**
- **No boot-critical module is blocked** (see the tier below).
- **The file is non-empty, and in the logger form unless `/usr/bin/logger` is absent** (an
  empty file means the pipeline failed and you have a false "success"; a `/bin/true` file
  silences the discovery step).

**Capture the dry-run from the right STREAM.** A tool that prints its would-be blacklist to
STDERR hands a stdout-reading verifier an EMPTY set, and then every invariant above passes
vacuously - including the non-empty check, which is the one meant to catch exactly this.
Measured on one implementation: stdout carried 1 summary line and 0 `install` lines while stderr
carried 6725. Redirect both and assert the parsed count is what the summary claims.

```bash
# the names this FILE blocks, read back out of it
awk '$1=="install"{print $2}' candidate.conf | LC_ALL=C sort -u > candidate.names
wc -l < block.list; wc -l < candidate.names   # must be equal, and non-zero
grep -c 'logger -t modulejail' candidate.conf  # must be that same number (logger form)
lsmod | awk 'NR>1{print $1}' | LC_ALL=C sort -u | LC_ALL=C comm -12 - candidate.names  # must print nothing
LC_ALL=C comm -12 keep.closure candidate.names                                         # must print nothing
# repeat that comm against your boot-critical list (see the tier below)
# Dry run of THIS file alone (-C), loads nothing. Use --show-depends, not -n -v: -n -v
# prints NOTHING for a module that is already loaded, which reads like a missing module.
modprobe --show-depends -C candidate.conf sctp   # blocked -> the logger `install` line
modprobe --show-depends -C candidate.conf veth   # kept    -> an insmod path
# The blocked control must be PROVEN, not assumed - see "Proving the blocked control".
# If you drive this with a generator instead, capture BOTH streams and count both - some
# print the would-be blacklist to stderr:
#   <your-generator> --dry-run >out.txt 2>err.txt
#   grep -c '^install ' out.txt err.txt
```

**Validate the gate against a known-negative:** drop one obviously-required module (e.g.
`veth` on an LXC host, or your root-disk controller) from the KEEP set, rebuild
`candidate.conf`, and re-run the gate - it MUST flag it. A gate that passes your removal is not
checking anything. See `bitranox:process-review-verification-before-completion`.

### 5. Install the override, then rebuild the initramfs so the reboot tests the real boot

Only after step 4 passed, install the file the gate checked, unchanged, and rebuild the
initramfs at once:

```bash
install -m 0644 candidate.conf /etc/modprobe.d/modulejail-blacklist.conf
update-initramfs -u -k all
proxmox-boot-tool refresh          # Proxmox with proxmox-boot-tool-managed ESPs only
lsinitramfs "/boot/initrd.img-$(uname -r)" | grep -c 'modprobe.d/modulejail-blacklist.conf'  # must be 1
```

The rebuild is not optional and not a way to "make it permanent": the next kernel, zfs or
dkms update rebuilds the initramfs anyway, and it copies `/etc/modprobe.d` in (see "The
blacklist is in the initramfs, and it is per-kernel"). Rebuilding NOW makes the step-6 reboot
exercise the boot path every later initramfs will have, while you can still recover; skipping
it means the first boot with the block in early userspace happens at some later update. Do
**not** run `depmod -a`: it only rebuilds `modules.dep` from the module files under
`/lib/modules/$(uname -r)`, which a `modprobe.d` blacklist/install directive never touches, so
it is a no-op here. On the running system `install` overrides only intercept FUTURE loads, so
nothing already loaded is touched; the file takes effect on the NEXT load attempt immediately -
`modprobe` re-reads `modprobe.d` on every call. The reboot in step 6 proves the host still
BOOTS with the block in place.

In the same session, install the kernel-upgrade guard and pin the proven kernel (both in "The
blacklist is in the initramfs, and it is per-kernel"). A jailed host without them is one
unattended kernel update away from a NIC that does not come up.

### 6. The reboot-while-recoverable gate (mandatory)

Before the host ever goes somewhere you cannot reach it: `reboot` it for real (at least one
cold power cycle), while you still have console or power access, and confirm afterward - SSH
reachable, every service/guest up, storage healthy, both NICs up, `journalctl -k -b` clean
of new module errors, and a differential check that a blocked module refuses while a kept one
still loads (below). Repeat 2-3 times. A config that was only written, never cold-booted, is
not validated.

## The blacklist is in the initramfs, and it is per-kernel

**It reaches early boot whatever you do.** Debian's initramfs-tools (Proxmox included) copies
all of `/etc/modprobe.d` into every initramfs it builds, and a kernel install, a zfs or dkms
update, or `proxmox-boot-tool refresh` builds one. So once the file exists, every later
initramfs carries it - not running `update-initramfs` yourself keeps nothing out. Check rather
than assume: `lsinitramfs /boot/initrd.img-<version> | grep modulejail`. A wrong entry can
therefore stop the machine BEFORE the root disk or the NIC driver is up - dead before SSH. Do
not "fix" that by stripping the file out of the initramfs, or by moving it out of
`/etc/modprobe.d` around an upgrade: the NIC driver is often loaded by
udev after the switch to the real root, under the same file, and early boot would then load
unjailed. The safety is the step-4 gate, the step-6 reboot, and the per-kernel check below.

**The list is computed against ONE kernel's dependency graph.** A kernel upgrade can give a
KEPT module a new dependency that the old list blocks. Measured on an off-site host: a list
generated on kernel 7.0.14-14 blocked `phylink`; on 7.0.14-20 the kept NIC driver `r8169`
depends on `phylink`, so the NIC failed at boot with `Unknown symbol` - four failed boots of a
host nobody could reach. Two guards, both mandatory on a host without a console:

**1. Check the closure of every kept module against each NEW kernel when it is installed.**
Persist the KEEP inputs that are not `lsmod` - the whitelist, the baseline and the boot-critical
tier below, one name per line, in `/etc/modulejail/keep.list` - and install a hook that kernel
packages run for every new kernel, with its version as `$1`. On a host jailed before this guard
existed, write both now, before its next kernel update; a module you rely on that is in none of
the three lists belongs in the whitelist first.

```sh
#!/bin/sh
# /etc/kernel/postinst.d/05-modulejail-closure   (root:root 0755)
# Fails when the installed jail blocks a dependency of a kept module ON THE NEW KERNEL,
# or when a kept module does not exist there. -C /dev/null reads the dependency graph
# without the blacklist, whose install lines would otherwise hide the very edge we check.
set -eu
new="$1"
keep=/etc/modulejail/keep.list
bl=${MODULEJAIL_BLACKLIST:-/etc/modprobe.d/modulejail-blacklist.conf}
work=$(mktemp -d); trap 'rm -rf "$work"' EXIT
awk '$1=="install"{print $2}' "$bl" | LC_ALL=C sort -u > "$work/blocked"
LC_ALL=C sort -u "$keep" > "$work/closure"
missing=""
while read -r m; do
  modprobe -S "$new" --show-depends -C /dev/null "$m" >/dev/null 2>&1 || missing="$missing $m"
done < "$work/closure"
while :; do
  before=$(wc -l < "$work/closure")
  while read -r m; do
    modprobe -S "$new" --show-depends -C /dev/null "$m" 2>/dev/null \
      | awk '/^insmod/{print $2}' | xargs -rn1 basename | sed 's/\.ko.*//' | tr '-' '_'
  done < "$work/closure" | cat - "$work/closure" | LC_ALL=C sort -u > "$work/next"
  mv "$work/next" "$work/closure"
  [ "$(wc -l < "$work/closure")" = "$before" ] && break
done
hit=$(LC_ALL=C comm -12 "$work/closure" "$work/blocked" | paste -sd' ' -)
[ -z "$hit$missing" ] && exit 0
echo "modulejail: kernel $new - blocked dependencies: ${hit:-none}; missing kept:${missing:- none}" >&2
echo "modulejail: DO NOT boot $new - rebuild the list for it (steps 1-5, with $new for uname -r)" >&2
exit 1
```

A kernel installed before the hook existed was never checked: run the hook for it by hand,
`sh /etc/kernel/postinst.d/05-modulejail-closure <version>`, before booting it. Read the hook's
output after every kernel install, and treat a failure as "do not boot this kernel", not as an install error to clear: whether a failing hook also aborts the package
depends on how the package calls its hooks, so the message is the guard, not the abort. Prove
the hook can fire before trusting its silence - block one dependency of your NIC driver
(`modinfo -F depends <driver>`) in a COPY of the blacklist and run the hook against it; it must
exit 1 naming that module:

```bash
{ cat /etc/modprobe.d/modulejail-blacklist.conf; echo "install <dep> /bin/true"; } > /root/bl.test
MODULEJAIL_BLACKLIST=/root/bl.test sh /etc/kernel/postinst.d/05-modulejail-closure "$(uname -r)"
echo "rc=$?"   # must be 1, and the message must name <dep>
```

To rebuild the list for a kernel you have not booted yet, add `-S <version>` to every
`modprobe` call in steps 1 and 4 and use `/lib/modules/<version>` in step 2, then re-run the
hook for that version until it exits 0. One file serves every installed kernel, so a list
rebuilt for the new kernel must still pass the hook for the pinned one.

**2. Keep the proven kernel pinned until a guarded boot of the new one succeeds.**

```bash
proxmox-boot-tool kernel pin "$(uname -r)"           # before the upgrade (or right after it,
                                                     # before any reboot): the default stays
proxmox-boot-tool kernel pin <new-version> --next-boot  # one trial boot, only while recoverable
# after the trial: NIC up, SSH, storage healthy, guests up, journalctl -k -b without
# 'Unknown symbol' -> then pin the new kernel (or unpin)
```

`--next-boot` falls back to the pinned kernel only on the NEXT reset, and a boot that hangs
does not reset itself. So the trial boot of a new kernel needs the same recovery path as the
step-6 reboot (console, OOB power, or hands on site); without one, the new kernel stays
installed but not booted, and a reboot for any other reason still lands on the pinned one.

## Boot-critical tier - hard-exempt, never block

Identify and exempt (verify, do not assume): the root-disk controller
(`ethtool -i`/`readlink /sys/.../driver`; `ahci`, `nvme`, ...), the storage stack
(`zfs`/`spl` matched to the running kernel; md/dm/lvm), the NIC driver actually carrying
your SSH, and - if WiFi is the post-move uplink - its driver plus `cfg80211`/`mac80211`/
`rfkill`. On a bridged/LXC host also keep `bridge`, `veth`, `8021q`, and the netfilter
modules your firewall uses. On a KVM host keep `kvm`, `kvm_intel`/`kvm_amd`, `vhost_net`,
`tun`, `vfio*`.

## The closure misses runtime-loaded modules - discover those by EXERCISING

`modprobe --show-depends` reports only the STATIC dependencies recorded in `modules.dep`. A
kernel subsystem that asks for a helper at runtime through `request_module()` - the crypto API
above all, but also filesystem crypto and netfilter helpers - names it by ALIAS at the moment of
use, so no closure of the KEEP set can predict it. Whitelist the feature, watch it still fail,
and the failure has MOVED rather than resolved.

The block is silent to the caller by construction. An `install X <command>` line runs the
command INSTEAD of inserting the module - the step-3 logger command, or a bare `/bin/true` - so
`modprobe X` prints nothing and exits 0 while loading nothing - success by every signal a caller
can test. The logger form leaves one syslog line under the `modulejail` tag; `/bin/true` leaves
no trace at all. The symptom then surfaces somewhere else entirely and never mentions a module.

Two different failures come out of one jail, and they look nothing alike:

| What is blocked                      | How it fails                                            |
|--------------------------------------|---------------------------------------------------------|
| the module you asked for             | `modprobe` silent, exit 0, `lsmod` empty                |
| a DEPENDENCY of a whitelisted module | `modprobe: ERROR: could not insert 'X': Unknown symbol` |

The second reads like a broken module or a kernel mismatch rather than a policy decision, so
sweep every whitelist entry's own `modinfo -F depends` rather than trusting the entry alone.

**Method: exercise the real code path, read what was refused, add it, repeat.**

```bash
# Refusals are logged under this syslog tag - the discovery channel. This works ONLY if
# the installed file is in the logger form (step 3); with bare `install X /bin/true`
# lines nothing is written and the query below is empty on a fully-blocking jail.
# Verify before you trust an empty result:
#   grep -c logger /etc/modprobe.d/modulejail-blacklist.conf
journalctl -t modulejail --since "-1h" \
  | sed -n 's/.*blocked: \([a-zA-Z0-9_-]*\).*/\1/p' | sort | uniq -c | sort -rn
```

Start the service, mount the filesystem, select the algorithm - then read that list. Anything on
it is a runtime request the closure did not predict. Add it to KEEP, regenerate, repeat until the
list is empty while the feature works.

Worked example - a zram swap device configured for `zstd`:

| Module set                                                         | Found by                |
|--------------------------------------------------------------------|-------------------------|
| `zram`                                                             | your explicit whitelist |
| `lz4_compress`, `lz4hc_compress`, `842_compress`, `842_decompress` | `--show-depends zram`   |
| `zstd`                                                             | ONLY the modulejail log |

`zstd` is the crypto-API backend requested when `zstd` is written to `comp_algorithm`, and is
invisible to `--show-depends` at any depth.

Worked example - WPA on a wireless link with `ccm` blocked: `wpa_supplicant` reports
`Failed to set PTK` and then `4-Way Handshake failed - pre-shared key may be incorrect`, which
reads exactly like a wrong password, not a module policy. Only `journalctl -t modulejail` shows
`blocked: ccm` - the crypto API requested it at the moment of the handshake, and no static
dependency closure of the wireless driver predicted it. Whitelist `ccm cmac gcm` together with the
wireless driver's own closure (`cfg80211`/`mac80211`/the vendor driver), then retry the handshake.

**Run `--show-depends` on YOUR kernel; do not copy that list.** It is kernel-specific, and the
plausible guesses are wrong often enough to be worth naming. Two measured on one 7.0.x build,
both of which a competent reader would assume the other way:

- `zsmalloc` is a module on that kernel, yet is NOT a dependency of `zram` and is never needed -
  it is a wrong guess, not a module to go and find.
- The only zstd object on disk is `zstd.ko`. There is no `zstd_compress.ko` or
  `zstd_decompress.ko`, although `modinfo zstd_compress` still answers, because it resolves the
  name through an alias. `modinfo` succeeding is not evidence that a distinct module exists.

**A working feature is not proof nothing is blocked.** On that same host zram selected `[zstd]`
and compressed correctly while the `zstd` module was still refused, because the kernel also
carries a built-in zstd backend - the only evidence was dozens of refusals in the log. A kernel
without that built-in path fails outright on the identical configuration. Treat a non-empty
refusal list as unfinished work even when the feature looks healthy.

## Verify (differential, not by inspection)

```bash
# --show-depends, not -n -v: -n -v prints NOTHING for a module that is already loaded
modprobe --show-depends sctp   # a BLOCKED name -> an `install` line (the step-3 logger
                               #                   command, or /bin/true), never an insmod path
modprobe --show-depends veth   # a KEPT name    -> a real insmod path
```

### Proving the blocked control

A blocked control proves nothing unless the module EXISTS on the running kernel. Modules
disappear between kernels - `dccp` is gone from 7.0.x Proxmox kernels (`modinfo -n dccp`:
"Module dccp not found") - and an `install` line is matched by NAME, so a list generated on
an older kernel still prints the `install` line for a module that can never load. Prove both
halves before reading the result, and stop loudly when either fails:

```bash
# A subshell, so a failing check stops here without closing your SSH session.
( ctl=sctp   # any module the list blocks; sctp, rds and tipc resolve on 7.0.x
  bl=/etc/modprobe.d/modulejail-blacklist.conf     # or candidate.conf in step 4
  modprobe --show-depends -C /dev/null "$ctl" | grep -q '^insmod ' \
    || { echo "CONTROL INVALID: $ctl is no loadable module on $(uname -r)"; exit 1; }
  awk '$1=="install"{print $2}' "$bl" | grep -qx "$ctl" \
    || { echo "CONTROL INVALID: $ctl is not blocked by $bl"; exit 1; }
  modprobe --show-depends -C "$bl" "$ctl" | grep -q '^install ' \
    || { echo "JAIL BROKEN: $ctl is listed but modprobe would load it"; exit 1; }
  echo "CONTROL OK: $ctl exists on $(uname -r) and is blocked" )
```

`-C /dev/null` reads no configuration at all, so an `insmod` line there means the module file
is really on disk for this kernel; a missing module fails with "Module <name> not found", and a
built-in one prints `builtin`, which no `install` line can block either. Pick
the replacement from `candidate.names` (or the installed file) by running the first check over
it - never by memory.

Re-run any whitelist change through steps 1-5 - rebuild `candidate.conf`, gate it, then install
it; the generated `/etc/modprobe.d/modulejail-blacklist.conf` is host-specific and per-kernel
(see "The blacklist is in the initramfs, and it is per-kernel" for the kernel-upgrade guard).

Regenerating alone is not enough: a unit that already failed on the missing module stays failed,
so the correct fix reads as ineffective. Clear it and retry. Clear the whole chain, not just the
unit named in the error - the device and swap units latch their own failed state.

```bash
systemctl reset-failed systemd-zram-setup@zram0.service dev-zram0.swap
systemctl restart systemd-zram-setup@zram0.service
swapon --show                      # the outcome; the unit going active is not the same thing
```

## Common mistakes

| Mistake                                           | Consequence                                                      |
|---------------------------------------------------|------------------------------------------------------------------|
| Believing the block stays out of the initramfs    | Every later initramfs carries it; a wrong entry stops early boot |
| Booting a new kernel on the old kernel's list     | A kept module's new dependency is blocked: `Unknown symbol`      |
| A blocked control that does not exist             | The `install` line prints by name; the check passes vacuously    |
| Hand-picking a short blocklist                    | Barely reduces attack surface; misses the autoloaded classes     |
| Blocking by name without the dependency closure   | Kills a dependency of a kept module; kept driver breaks          |
| `blacklist X` instead of `install X /bin/true`    | `blacklist` only stops alias autoload, not an explicit load      |
| Trailing inline `# comment` on an `install` line  | modprobe.d mis-parses it; block silently wrong                   |
| Empty `block.list` read as success                | Pipeline failed; you hardened nothing and think you did          |
| Writing to `/etc/modprobe.d` before the gate      | It blocks at once; a failing gate finds the host already changed |
| Relocating before a real cold-reboot test         | First real boot at the unreachable site is the test              |
| Trusting the dependency closure to be complete    | Runtime `request_module()` helpers are invisible to it           |
| Reading a working feature as "nothing is blocked" | A built-in fallback can hide a refusal that breaks elsewhere     |
| Regenerating without clearing the failed unit     | Unit stays failed; the correct fix looks ineffective             |
| Reading coverage off `lsmod` instead of the lists | Loaded-only modules are kept by accident, lost on a regen        |

## Real-world impact

On a 2-NIC LXC host, this jailed ~97% of the module tree (thousands of modules blocked)
with every guest, both NICs, and the pool unaffected across repeated cold reboots. The
safety came from the invariant gate + the reboot-recoverable gate, not from the block
itself - and on every later kernel, from re-checking the closure against that kernel before
booting it.
