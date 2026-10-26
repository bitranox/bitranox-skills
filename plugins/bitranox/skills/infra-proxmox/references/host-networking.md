# Host Networking Pitfalls (ifupdown2 on Proxmox VE)

Field notes for changing `/etc/network/interfaces`, bonds and the DHCP client on a PVE node,
especially one reached only over SSH. Each trap below reads as a different problem than it is.
Behaviour marked "observed" was measured with ifupdown2 3.3.0 (the PVE 9 build).

## Dry run, DHCP and dhclient.conf

- The dry run is `ifreload -a -n` (no-act). ifupdown2 has no `--test`; it exits 2 on that
  argument.
- **A `-n` run reports a DHCP failure it never had.** On an interface being switched to
  `inet dhcp`, `ifreload -a -n` prints
  `error: <iface>: dhclient: timeout failed to detect new ip addresses` and still exits 0. No-act
  never applies the stanza, so the addon waits for an address that cannot appear. Treat that line
  as a no-act artifact, never as "DHCP does not work on this LAN".
- **Prove DHCP separately, without touching the interface:** `dhclient -1 -sf /bin/true -v <iface>`
  runs the full DISCOVER/OFFER/REQUEST/ACK exchange; look for `DHCPOFFER` and `DHCPACK` in its
  output. `-sf /bin/true` replaces the script that would configure the address. A successful probe
  DAEMONIZES (`-1` governs failure only), so kill it by PID afterwards, or it lingers as a second
  client on the interface. AppArmor confines dhclient to its own paths, so `-lf`/`-pf` outside
  `/var/lib/dhcp` are denied; read the lease from the `-v` output.
- **A `/etc/dhcp/dhclient.conf` edit needs a FRESH client.** Neither `ifreload -a` nor
  `ifreload -a -f` restarts a running dhclient whose interface stanza is unchanged (observed), so an
  `append domain-name-servers` or `supersede` line changes nothing until the client restarts, in
  practice at the next reboot. Plan the edit as a reboot, and verify it by the CONTENT of
  `/etc/resolv.conf` plus a changed mtime, never by the reload's exit code.

## Applying a change on a remote node

Never run the apply from the SSH session the bridge carries: a dropped session can leave the bridge
half-configured. Arm a rollback first, apply detached, and cancel the rollback only after the new
config is verified from a fresh session:

```bash
cp /etc/network/interfaces /root/interfaces.bak
# edit /etc/network/interfaces, then dry-run it: ifreload -a -n
systemd-run --on-active=300 --unit=net-rollback \
    /bin/sh -c 'cp /root/interfaces.bak /etc/network/interfaces && ifreload -a'
systemd-run --no-block --unit=net-apply ifreload -a
# reconnect, verify address, route and DNS, then cancel the rollback:
systemctl stop net-rollback.timer
```

A node reached over a VPN that rides the default route loses the tunnel together with the LAN when
the change fails, so the armed rollback is the way back on a node with no console.

## A bond that must survive a missing slave NIC

When a slave NIC can be absent (a driver that fails to load after a kernel update), do NOT put
`bond-primary` in the bond stanza. ifupdown2 resolves it to an interface index while building the
bond; with that NIC absent it logs `error: ifname <nic> not present in cache`, then
`vmbr0: bridge port bond0 does not exist`, and aborts the WHOLE bond, so the bridge has no port and
the backup slave carries nothing (observed). A missing `bond-slaves` entry, by contrast, is only
skipped (`skipping slave <nic>, does not exist`). Set the preference after the bond exists:

```text
auto bond0
iface bond0 inet manual
	bond-slaves <nic> <backup-slave>
	bond-miimon 100
	bond-mode active-backup
	post-up echo <nic> > /sys/class/net/bond0/bonding/primary 2>/dev/null || true
```

`ifquery -a -i <file>` checks the syntax only; it cannot exercise a missing NIC. A node with no
console is otherwise first tested by its next boot, so prove the missing-NIC case before that boot
by running the node's own ifupdown2 against the old file (RED) and the new one (GREEN) in an
isolated mount and network namespace, which touches no real interface:

1. Copy the node's `/usr/share/ifupdown2`, `/usr/sbin/ifup` and `/etc/network/ifupdown2` into a
   scratch directory. Point `IFUPDOWN2_ADDON_DROPIN_FOLDER` (in `ifupdown/config.py`) at the
   scratch addons and set `template_enable=0`, so no mako is needed.
2. Give a venv `six` and `setuptools`, plus a stub `systemd.journal.JournalHandler`.
3. As root, `unshare -mn`: bind the scratch over `/etc/network` and `/run/network`, mount a fresh
   sysfs, create veth pairs named like the real NICs (the `dummy` module is often blocked on a host
   with a kernel-module allowlist; veth works), switch the bridge to `inet manual`, and run
   `ifup -a`.
4. Run it once with the NIC absent and once with it present. Absent must give a bond on the backup
   slave with the bridge on top; present must give both slaves with that NIC as primary
   (`cat /sys/class/net/bond0/bonding/primary`).

## Bridge over an active-backup bond with a WLAN standby slave

A WiFi station may transmit only frames carrying its own MAC. A WLAN standby slave therefore needs
two settings, and the failure without either looks the same: the bond fails over within seconds,
the WLAN is associated, and the gateway stays unreachable for the whole failover.

1. **`fail_over_mac=1` as a bonding MODULE option**, in `/etc/modprobe.d/bonding.conf`:
   `options bonding fail_over_mac=1`. ifupdown2 has no attribute for it, so written in
   `/etc/network/interfaces` it is silently ignored. Without it an active-backup bond forces every
   slave to the bond's MAC, and the WLAN slave associates carrying the wired NIC's MAC. Check with
   `cat /sys/class/net/bond0/bonding/fail_over_mac` (`active 1`). A modprobe.d option takes
   effect only when the bonding module next loads, so it too needs the reboot below.
2. **Unpin the bridge MAC.** PVE ships
   `/var/lib/ifupdown2/policy.d/proxmox-bridge-mac-from-port.json` with
   `bridge_set_static_mac_from_port: yes`, so ifupdown2 pins vmbr0 to the wired NIC's MAC.
   With the bond on the radio, every frame then leaves with a foreign source address and the AP
   drops it. Diagnose with `cat /sys/class/net/vmbr0/addr_assign_type`: `3` means set by userspace,
   that is pinned. Override it in `/etc/network/ifupdown2/policy.d/<name>.json` (a file there
   overrides the shipped default):

   ```json
   {"bridge": {"module_globals": {"bridge_set_static_mac_from_port": "no"}}}
   ```

   Then REBOOT. The kernel skips the bridge's MAC recalculation while `addr_assign_type` is 3, so
   `ifreload` cannot unpin a live bridge; only recreating it clears the pin. An unpinned bridge
   takes the lowest port MAC and follows the bond's MAC changes.

Verify after the reboot: `addr_assign_type` reads `1` and vmbr0's MAC equals bond0's. Then test
the failover behind an automatic restore: arm `systemd-run --on-active=120 ip link set <nic> up`
first (`<nic>` is the wired slave), then run `ip link set <nic> down`, and watch the bridge MAC
switch to the radio's. Two limits hold either way. Bridged guests stay dark on the WLAN slave,
because a station cannot carry their MACs, so it is a host management lifeline only. And the
host's DHCP address may change on failover, since the new MAC renews its own lease, so reach the
node by a stable address (a static one, or a VPN address).

## WLAN that must stay associated: run the supplicant as a unit

Do not associate a WLAN interface that must stay up (a bond slave, a management lifeline) with a
`wpa-conf` line in `/etc/network/interfaces`. It works at boot (`ifup -a`), so a reboot test
passes, but under `ifreload -a` the ifupdown hook starts the supplicant and kills it again within
the same second (observed): the journal shows `Successfully initialized`, then `nl80211: deinit`
and `CTRL-EVENT-TERMINATING`, `/run/wpa_supplicant*` is gone, and nothing reports an error.

Use the packaged unit instead:

- the config at `/etc/wpa_supplicant/wpa_supplicant-<iface>.conf`;
- `systemctl enable --now wpa_supplicant@<iface>`;
- a drop-in `/etc/systemd/system/wpa_supplicant@<iface>.service.d/restart.conf` holding
  `[Service]`, `Restart=on-failure` and `RestartSec=10`, because the packaged unit has no
  `Restart=` at all;
- the stanza `iface <iface> inet manual`, with no `wpa-conf` line.

The unit runs the supplicant in the foreground, survives reload and reboot, and re-associates on
its own.

**A handshake failing with `4-Way Handshake failed - pre-shared key may be incorrect`** (often
after `WPA: Failed to set PTK to the driver`) on a host with a kernel-module allowlist is usually a
blocked cipher module, not a wrong passphrase. mac80211 requests the CCMP cipher from the crypto
API by alias at handshake time, so it appears in no static dependency list. Read the allowlist's
log before touching the passphrase (`journalctl -t modulejail --since -10m` shows `blocked: ccm`
per attempt) and allow `ccm cmac gcm` with the wireless driver's closure; see
`bitranox:infra-modulejail`.
