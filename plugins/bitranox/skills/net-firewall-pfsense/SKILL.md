---
name: net-firewall-pfsense
description: Use when working on a pfSense firewall - a host reachable inside its subnet but dead beyond it with nothing logged, "ARP Table Static Entry", DHCP reservations, unbound host overrides, pfctl tables, snort2c blocking a CDN, a config.xml snapshot, or any change you would otherwise make by hand-writing PHP over SSH.
---

# pfSense from the command line

pfSense has no CLI for its own configuration, so changes get made by hand-writing PHP and pushing
it over SSH through four quoting layers. `scripts/pfsense.py` does that part, so the effort goes
into deciding what to change.

## Diagnose first

| Symptom                                                                   | Look at                                             |
|---------------------------------------------------------------------------|-----------------------------------------------------|
| Reachable inside its subnet, dead beyond it, nothing logged anywhere      | a DHCP reservation with static ARP armed - `doctor` |
| An address answers, but for hardware no reservation names                 | a reservation that outlived its device - `doctor`   |
| A download or CDN times out after DNS resolves and the redirect is served | `snort check <host>`, then `snort why <ip>`         |
| `pkg` and system upgrades fail to resolve                                 | Tailscale Accept DNS rewrote resolv.conf - `doctor` |
| "Another instance of pfSense-upgrade is running"                          | a stale lock - `doctor`                             |
| A name resolves to the wrong address                                      | `dns list`                                          |

**The first row is the one that gets missed.** Every instinct points at firewall rules, aliases,
policy routing and gateways, and none of them is it.

Ticking "ARP Table Static Entry" on a reservation pins ONE MAC to that address permanently. It
breaks whenever that is not the MAC currently using the address, which happens more ways than it
sounds: a device with several interfaces answering from the other one (a speaker with `eth0` and
`wlan0`, a managed switch, a laptop docked and undocked), hardware replaced, a NIC changed by a
firmware update. The firewall then sends to a MAC that no longer answers.

Traffic inside the subnet keeps working, because peers ARP each other directly on the wire and
never consult the firewall. Anything beyond the subnet has to traverse it, and dies. This fails at
layer 2, before a rule is ever evaluated, so no rule matched, no counter moved and no log line
exists. It stays broken until someone thinks to look at ARP.

Leave that box unticked unless you can name the single interface it belongs to.

## Verbs

Run `pfsense.py --help` and `pfsense.py <verb> --help` for the current flags.

| Verb                                                      | Answers                                               |
|-----------------------------------------------------------|-------------------------------------------------------|
| `doctor`                                                  | what is quietly wrong, live or from a snapshot file   |
| `info`                                                    | version, DHCP backend, resolver, interfaces, packages |
| `snapshot`                                                | save `/conf/config.xml` under a timestamped name      |
| `dhcp list` / `rm` / `rm-static-arp`                      | reservations, and the static-ARP fix                  |
| `dns list` / `add` / `rm`                                 | unbound host overrides                                |
| `arp [--permanent]`                                       | the live ARP table                                    |
| `table list` / `show` / `test` / `del`                    | any pf table - snort2c, ISP aliases, bogons           |
| `rules [--counters] [--nat]`                              | the live ruleset, with per-rule counters              |
| `snort check` / `why` / `unblock` / `verify` / `fixsteps` | a Snort block and its durable fix                     |

Everything is a dry run until `--apply`. The four verbs that edit `config.xml` (`dhcp rm`,
`dhcp rm-static-arp`, `dns add`, `dns rm`) snapshot it first and abort if the snapshot fails.
`table del` and `snort unblock` change LIVE pf state, which a `config.xml` snapshot neither
captures nor restores, so they take none - undo those by re-adding the entry.

A snapshot is a whole `config.xml`, with password hashes, private keys and certificates in it, so
it is written to a private per-user state directory (`--snapshot-dir` to choose another). Writing
one into a git work tree is refused unless you pass `--allow-repo-snapshot`.

```bash
pfsense.py --host 192.0.2.1 --user admin --ssh "ssh -i /path/to/key" doctor
pfsense.py --fw home dns add --name nas.example.com --ip 192.0.2.10 --apply
pfsense.py doctor --config config-20260101.xml      # a saved snapshot, no network
```

`--fw <name>` reads a target from `~/.config/bitranox/pfsense.ini`; there is deliberately no
default host, because the wrong firewall is one careless run away.

```ini
[home]
host = 192.0.2.1
user = admin
ssh = ssh -i /path/to/key -o BatchMode=yes
```

## Traps

**Never merge the streams.** The ssh client's post-quantum warning is on stderr. `2>&1 | grep -v`
is not the fix, it is the damage: it splices client diagnostics into whatever the parser reads,
then filters some of them back out. Keep them apart and there is nothing to filter.

**An empty tag means enabled.** `<enable></enable>` reads back as `""`, so
`if (config_get_path("unbound/enable"))` is false for a running resolver. Compare against `null`.

**Host overrides live at `unbound/hosts`.** The GUI calls them Host Overrides, and
`unbound/hostoverride` returns an empty list rather than an error, so the mistake looks like
"there are none".

**Check the DHCP backend before reloading it.** 2.8 can run ISC dhcpd or Kea, and they need
different service calls. `info` reports which.

**`snort2c` exists even with no Snort installed**, so an empty table means nothing is blocked, not
that Snort is watching. `info` lists the packages.

## Not covered here

pfBlockerNG, certificate and acme renewal, and traffic shaping are inspection-shaped and change
between releases. Drive them from the GUI or `pfSsh.php playback`, and take a `snapshot` first.

If you edited `config.xml` out of band rather than through the config API, the running config is
stale until `rm -f /tmp/config.cache && /etc/rc.filter_configure_sync`. Going through the API
instead avoids this.

## Common mistakes

- Deleting an entry by its position in a listing. Every later position shifts, so the next delete
  from the same listing hits the wrong row and still exits 0. Select by MAC or by name.
- Reading ARP absence as "the device is gone". ARP is a cache that expires after minutes of
  silence, and a fixed-address reservation leaves no DHCP lease either, so neither source can
  prove absence. ARP is good for positive evidence only.
- Clearing `snort2c` and calling it fixed. The rule re-adds the address on the next packet;
  `snort fixsteps` prints the three parts that make it stick.
