---
name: net-tailscale
description: Use when installing or running Tailscale on Linux or in a container/LXC - joining a tailnet with tailscale up, setting a node hostname - and especially when a machine or container was CLONED from one that already had Tailscale (the clone inherits the node identity and collides with or de-authenticates the original), when tailscaled cannot create its tun device in an unprivileged container, when tailscaled drops the tailnet after a reboot, or when a resolver forwarding DNS queries to 100.100.100.100 (MagicDNS/quad-100) SERVFAILs or times out on a FreeBSD/pfSense tailnet node.
---

# net-tailscale

## Overview

Tailscale on Linux is `tailscale up` once the daemon runs. The parts that bite are not the
install: they are cloned node identity, unprivileged-container device access, and boot
ordering. This skill is those gotchas.

**Core principle for cloning: a Tailscale node's identity lives on disk. Copy the disk and
you copy the identity.** So the durable fix is upstream - never bake Tailscale into an image
or template you clone from. Install it fresh per machine, after cloning.

## When to use / not

Use when: bringing a host or container onto a tailnet; cloning a VM/container that already
had Tailscale; `tailscaled` fails with a tun/`TUNSETIFF`/permission error in an unprivileged
LXC; Tailscale drops after reboot or loses its long-poll to the control plane; a resolver
forwarding to `100.100.100.100` (MagicDNS/quad-100) SERVFAILs or times out on FreeBSD/pfSense.

For SSH auth/key mechanics see `bitranox:compuse-ssh`; for Proxmox container operations see
`bitranox:infra-proxmox`; for the pfSense-side detection and fix of the DNS trap below see
`bitranox:net-firewall-pfsense`.

## Cloning: de-clone the identity BEFORE first start

A clone carries the source's `/var/lib/tailscale/tailscaled.state` (machine key, node key,
last registration). If `tailscaled` starts with that present, it does NOT create a new
device - it resumes the SOURCE's identity. Two live daemons then fight over one node: the
original intermittently drops off the tailnet, peers reach whichever daemon last won the
control session, and `--hostname=<new>` does not help (it just renames the shared device).
Wiping first is far cheaper than untangling a live collision on a node meant to stay
untouched.

Do this on the clone before Tailscale ever runs:

```bash
systemctl stop tailscaled              # in case it auto-started
tailscale logout 2>/dev/null || true   # only if it already registered
rm -f /var/lib/tailscale/tailscaled.state   # drop the inherited node/machine key
```

A clone usually shares TWO more identities that cause collisions later and get misblamed on
Tailscale - fix them in the same pass:

```bash
# machine-id: DHCP client-id, journald, D-Bus key. Duplicate = lease/log confusion.
rm -f /etc/machine-id /var/lib/dbus/machine-id
systemd-machine-id-setup
dbus-uuidgen --ensure

# MAC: REQUIRED when the clone and source share a bridge / L2 - the usual case for two
# containers on the same host bridge - because a duplicate MAC there breaks DHCP for both.
# Only skippable if they sit on different networks. Give the clone a fresh MAC; on Proxmox
# regenerate it on the host, e.g.:
#   pct set <ctid> -net0 name=eth0,bridge=vmbr0,hwaddr=00:00:5e:00:53:af
# (use a real fresh address; 00:00:5e:00:53:00-ff is the RFC 7042 documentation range)
```

Then set the node's own hostname so `tailscale up` without `--hostname` still fingerprints
right: `hostnamectl set-hostname node-example` and fix any stale `127.0.1.1` line in
`/etc/hosts`.

## Join the tailnet

```bash
systemctl enable --now tailscaled
tailscale up --hostname=node-example --auth-key=file:/path/to/tailscale.authkey
```

Run `tailscale up --help` for the current flags; do not freeze a flag list here. Load an
auth key from a FILE (`--auth-key=file:...`), never inline on the command line where it lands
in shell history and logs - see the no-secrets-on-the-command-line rule in
`bitranox:compuse-ssh`. Prefer a fresh key issued for this node over reusing the source's
credential.

Verify from three angles: on the clone `tailscale status` shows the new hostname with a NEW
tailnet IP; the admin console shows TWO devices (source unchanged, plus the new one); and on
the source `tailscale status` still shows it online - proof it was not disturbed.

## Unprivileged LXC / container

Tailscale needs `/dev/net/tun` and the ability to configure it. In an unprivileged LXC the
host config must grant the device (a `pct clone` copies the guest disk, NOT the host-side
`.conf` - verify the clone's own `.conf`):

```ini
# /etc/pve/lxc/<ctid>.conf
lxc.cgroup2.devices.allow: c 10:200 rwm
lxc.mount.entry: /dev/net/tun dev/net/tun none bind,create=file
```

If `tailscaled` still fails with `TUNSETIFF`/`operation not permitted` despite the device
being present, the AppArmor profile is blocking the ioctls: the source likely used
`lxc.apparmor.profile: unconfined`; diff the two `.conf` files rather than guessing, and add
that line to the clone's `.conf` if the source has it. Any host-side `.conf` change needs a
full `pct stop`/`pct start`, not a reload. As a fallback
where you cannot grant the device, `tailscale up --tun=userspace` runs without a kernel tun
device at lower throughput. Confirm the `tun` module is available on the HOST (all containers
share the host kernel).

## Boot ordering and staying up

`tailscaled` can start before the network is up and lose the boot race (Tailscale issue
12021). Order it after the network:

```ini
# /etc/systemd/system/tailscaled.service.d/override.conf
[Unit]
After=network-online.target
Wants=network-online.target
```

`tailscaled` reconnects on its own via DERP, so no extra keepalive is needed for basic
connectivity. For unattended fleet nodes, add a small watchdog that restarts `tailscaled`
when its control long-poll goes dead (not merely when the process exists): probe
`tailscale status --json` for a recent control-plane contact on a timer, restart the unit on
a stale/failed result. Build it self-healing per `bitranox:coding-resilience` (timeout,
backoff, a stderr note on failure).

## DNS: MagicDNS on quad-100 is platform-asymmetric

MagicDNS answers on `100.100.100.100` (quad-100), but WHO answers it depends on the node's OS.
On Linux, quad-100 is served by the LOCAL `tailscaled`, so it answers even with
`accept-dns=false` (that flag only keeps `tailscaled` out of `/etc/resolv.conf`; it does not
disable MagicDNS). On FreeBSD, including pfSense, `tailscaled` does NOT serve quad-100:
`tailscale status` there reports `Tailscale DNS: disabled`, the tailnet route to
`100.100.100.100` still exists, and a query against it just times out. That platform gap is the
trap - a resolver config that forwards to quad-100 is correct on Linux and dead on
FreeBSD/pfSense with nothing wrong in the config itself.

The tell: an unbound forward zone (or any resolver rule) pointing at `100.100.100.100`
SERVFAILs on FreeBSD/pfSense - not because the zone is misconfigured, but because its target
never answers there. Use SERVFAIL vs NXDOMAIN to tell the two apart: SERVFAIL means the zone is
configured but its target is dead (this platform gap); NXDOMAIN means the name genuinely does
not exist. SERVFAIL from a quad-100 forward zone on FreeBSD/pfSense is the asymmetry, not a
broken zone or a typo in the name - do not start there.

Do NOT "fix" it by setting `accept-dns=true` on the FreeBSD/pfSense node: that makes
`tailscaled` rewrite the node's `resolv.conf`, and pfSense's own package manager (`pkg`) reads
that file - once Tailscale owns it there, `pkg` and system upgrades stop resolving. For the
pfSense-side detection and fix (`doctor` catches a `resolv.conf` already rewritten this way),
see `bitranox:net-firewall-pfsense`.

## Common mistakes

| Mistake                                                              | Consequence                                                             |
|----------------------------------------------------------------------|-------------------------------------------------------------------------|
| Baking Tailscale into a clone base / template                        | Every clone inherits one identity; collisions forever                   |
| Starting the clone without wiping `tailscaled.state`                 | Clone resumes the SOURCE's identity; original drops off the tailnet     |
| Fixing state but not machine-id / MAC                                | DHCP-lease and journald collisions later, misblamed on Tailscale        |
| `--hostname=new` with the old state still present                    | Renames the shared device; no new node is created                       |
| Assuming `pct clone` copied the host `.conf`                         | Clone has no `/dev/net/tun` grant; tailscaled cannot start              |
| Inline `--auth-key=tskey-...` on the command line                    | Key leaks into shell history and logs                                   |
| Restarting only on process death, not a dead poll                    | A wedged daemon looks alive while the tailnet is down                   |
| Forwarding a resolver's zone to `100.100.100.100` on FreeBSD/pfSense | `tailscaled` does not serve quad-100 there; SERVFAIL, not a broken zone |
| Setting `accept-dns=true` on FreeBSD/pfSense to "fix" DNS            | Rewrites `resolv.conf`; breaks `pkg` and system upgrades there          |
