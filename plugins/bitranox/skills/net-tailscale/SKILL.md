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
where you cannot grant the device, userspace networking runs without a kernel tun device at
lower throughput. It is a `tailscaled` DAEMON flag, not a `tailscale up` flag, and the value
is `userspace-networking`, not `userspace`: put `FLAGS="--tun=userspace-networking"` in
`/etc/default/tailscaled` (or the unit's `ExecStart`), restart the daemon, then run
`tailscale up` as normal. Confirm the `tun` module is available on the HOST (all containers
share the host kernel).

## Boot ordering and staying up

`tailscaled` can start before the network is up and lose the boot race. Order it after the
network:

```ini
# /etc/systemd/system/tailscaled.service.d/override.conf
[Unit]
After=network-online.target
Wants=network-online.target
```

`tailscaled` reconnects on its own via DERP, so no extra keepalive is needed for basic
connectivity. For unattended fleet nodes, add a small watchdog that restarts `tailscaled`
when its control long-poll goes dead (not merely when the process exists - Tailscale issue
12021 is exactly this failure, still open, where the daemon logs "control: map response
long-poll timed out!" and never reconnects on its own). Key it on what the daemon reports:

- Run `tailscale status --json` with a timeout (20 s). A call that times out means `tailscaled`
  did not answer on its local socket at all, which is evidence about the daemon: restart, with
  no JSON left to read. A call that exits non-zero without timing out, a refused socket
  included, is a probe failure (last bullet).
- Read `BackendState` before `Health`. Anything but `Running` (`Stopped` after `tailscale down`,
  `NeedsLogin`) is left alone whatever `Health` says: a restart fixes none of them, and
  restarting a stopped node undoes a deliberate `down`.
- With `Running`, restart only when an entry of the `Health` list (an array of strings; a
  missing key counts as empty) contains the text "Unable to connect to the Tailscale
  coordination server" (the wording 1.98 and 1.104 print), matched as a substring of the
  entry. `tailscaled` raises that warning only after the control connection has been gone for
  8 minutes, so the watchdog reacts no faster than that.
- Do not look for a "last control contact" time: no LocalAPI endpoint reports it, and a probe
  built on one gets 404 and fails every run.
- Keep a failure of the PROBE apart from a failure of the DAEMON. When the CLI is missing, the
  call exits non-zero, its output does not parse or has no `BackendState`, or a helper the probe
  needs (`jq`) is absent, report that and do not restart. No fallback value may match the
  restart condition, or every probe failure becomes a restart: a probe whose missing-`jq`
  fallback emitted a string the restart pattern matched restarted a healthy `tailscaled` on
  every 5-minute run, about 270 times a day.

Build it self-healing per `bitranox:coding-resilience` (timeout, backoff, a stderr note on
failure).

## DNS: MagicDNS on quad-100 is platform-asymmetric

MagicDNS answers on `100.100.100.100` (quad-100), but WHO answers it depends on the node's OS.
On Linux, quad-100 is served by the LOCAL `tailscaled`, so it answers even with
`accept-dns=false` (that flag only keeps `tailscaled` out of `/etc/resolv.conf`, though switching
it off writes that file once more, see below; it does not disable MagicDNS). On FreeBSD,
including pfSense, `tailscaled` is reported NOT to serve quad-100: the tailnet route to
`100.100.100.100` still exists, but a query against it times out. Verify that on the
node itself before designing around it - `dig +time=3 +tries=1 @100.100.100.100
<host>.<tailnet>.ts.net` answers on Linux, and a timeout there is the real tell.
Do NOT use `tailscale dns status` as the tell: its `Tailscale DNS: disabled.` line reports the
`accept-dns` pref (upstream reads `prefs.CorpDNS`), not the platform, so it says the same thing
on a Linux node where quad-100 resolves perfectly well - and this skill tells you to run
pfSense with `accept-dns=false` anyway. That platform gap is the
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

**To make tailnet names resolve for the LAN anyway**, with Accept DNS still off on the
FreeBSD/pfSense node: point its forward zone at a LINUX tailnet node that runs a small forwarder
for the tailnet domain (with dnsmasq, `server=/<tailnet>.ts.net/100.100.100.100`), since quad-100
answers on that node. Check four things in that fix:

- Target an address of that node the firewall reaches, and prove it from the firewall before
  editing the zone: `host -W 3 <host>.<tailnet>.ts.net <node-address>` must answer.
- The coordination server's published split route for `ts.net` is no substitute target: its
  resolver answered REFUSED to direct queries (observed once).
- The answers are `100.x` tailnet addresses, so a LAN client with no route into `100.64.0.0/10`
  resolves the name and then fails to connect. A resolving name is not a reachable host.
- Tailnet-wide DNS settings in the admin console reach EVERY node but take effect only where
  Accept DNS is on. An entry there pointing at a LAN-only resolver is a trap for any node off that
  LAN that later turns Accept DNS on, so keep the forward on the LAN resolver.

### Switching accept-dns off on Linux writes resolv.conf one more time

While `accept-dns` is on and `tailscaled` writes `/etc/resolv.conf` itself, it keeps the previous
file as `/etc/resolv.pre-tailscale-backup.conf`. `tailscale set --accept-dns=false` writes that
backup back over `/etc/resolv.conf` within seconds and deletes the backup, while the daemon stays
connected (`BackendState` remains `Running`). That is a single measurement. So when you also
deploy a managed `/etc/resolv.conf`:

1. Before switching, check what relies on the node's current DNS: confirm nothing on the node
   itself needs tailnet names. On a Proxmox host, every container without its own nameserver is
   handed the host's resolver (`nameserver 100.100.100.100`) when it starts, and it gets the
   managed file only at its next start. A container whose `pct config <id> | grep nameserver`
   prints nothing is one of those: give it its own nameserver (`pct set <id> --nameserver <ip>`),
   or plan its restart after the switch.
2. Switch `accept-dns` off FIRST, then deploy the managed file. A file deployed before the switch
   is expected to be replaced by the backup's content (inferred from the observed write, not
   tested in that order).
3. Verify: `grep -v '^#' /etc/resolv.conf` shows the managed resolvers, `getent hosts <name>`
   resolves on the node and inside a guest, and `/etc/resolv.pre-tailscale-backup.conf` is gone.

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
| A watchdog whose probe-failure fallback matches its restart pattern  | Restarts `tailscaled` on every tick wherever the probe tool is missing  |
| Forwarding a resolver's zone to `100.100.100.100` on FreeBSD/pfSense | `tailscaled` does not serve quad-100 there; SERVFAIL, not a broken zone |
| Setting `accept-dns=true` on FreeBSD/pfSense to "fix" DNS            | Rewrites `resolv.conf`; breaks `pkg` and system upgrades there          |
| Deploying a managed `resolv.conf` before `accept-dns=false`          | The switch writes Tailscale's backup over it                            |
