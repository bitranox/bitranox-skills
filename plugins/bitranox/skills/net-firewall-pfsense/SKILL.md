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
| "Another instance of pfSense-upgrade is running"                          | broken box DNS, the lock is a symptom - `doctor`    |
| A name resolves to the wrong address                                      | `dns list`                                          |
| A dummynet limiter is on a rule but shapes nothing                        | `references/limiters.md`                            |

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
| `dhcp list` / `add` / `rename` / `rm` / `rm-static-arp`   | reservations, and the static-ARP fix                  |
| `dns list` / `add` / `rm`                                 | unbound host overrides                                |
| `arp [--permanent]`                                       | the live ARP table                                    |
| `table list` / `show` / `test` / `del`                    | any pf table - snort2c, ISP aliases, bogons           |
| `rules [--counters] [--nat]`                              | the live ruleset, with per-rule counters              |
| `snort check` / `why` / `unblock` / `verify` / `fixsteps` | a Snort block and its durable fix                     |

Everything is a dry run until `--apply`. The six verbs that edit `config.xml` (`dhcp add`,
`dhcp rename`, `dhcp rm`, `dhcp rm-static-arp`, `dns add`, `dns rm`) snapshot it first and abort if
the snapshot fails. `dhcp add --mac M --ip A --hostname H` refuses a MAC or address that is already
reserved and an address outside the interface's subnet (the interface is the one holding the
address, or `--interface lan`); `dhcp rename --mac M --hostname H` sets one reservation's
hostname. Both take a hostname as one label (letters, digits, inner hyphens), as the GUI does.
`table del` and `snort unblock` change LIVE pf state, which a `config.xml` snapshot neither
captures nor restores, so they take none - undo those by re-adding the entry.

With `--json` every verb prints `{ok, command, data, skipped}`, including on exit 2; `ok` means it
ran without error, so it stays true on a well-formed "no" (exit 1) such as `doctor` findings and
is false on exit 2.

A removal that removed nothing is a failed action, exit 2, not a "no": `dhcp rm`,
`dhcp rm-static-arp` or `dns rm` whose entry matched but whose write changed nothing, and a
`table del` or `snort unblock` that leaves every requested address present - a single address
included. Only some of several addresses left present is a partial outcome: exit 1, naming them.

A snapshot is a whole `config.xml`, with password hashes, private keys and certificates in it, so
it is written to a private per-user state directory (`--snapshot-dir` to choose another). Writing
one into a git work tree is refused unless you pass `--allow-repo-snapshot`. On a firewall that
runs as a VM, also take a hypervisor snapshot before a change: `snapshot` saves the config, not
the disk.

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

**A `pkg` upgrade of a base component does not restart it.** `pkg-static upgrade` of unbound or
openvpn replaces the binary on disk while the running daemon keeps executing the old one: pkg runs
no pfSense service hook for base components (observed: only `pfSense-pkg-*` packages resync), so
"upgraded" in its output does not mean the fix is active. Restart the service the pfSense way,
`pfSsh.php playback svc restart unbound` (a playback script, never interactive `pfSsh.php` on
stdin, which can hang), then confirm the daemon started after the upgrade
(`ps -axo lstart,command | grep '[u]nbound'`) and that `drill @127.0.0.1 example.com` still
resolves. The unbound restart interrupts DNS for every LAN
client for a moment. A daemon with no running process picks up the new binary at its next start.

**Run `pfSsh.php` as `playback <script>`, never with PHP piped to its stdin.** It does not exit on
EOF: the call hangs until the command timeout and leaves `pfSsh.php` processes behind. By then
`write_config()` and the reconfigure may already have run, so the timeout says nothing about
whether the change applied; read the state back. Feeding a script to the `php` CLI on stdin, as
`pfsense.py` does, exits normally.

**After `services_unbound_configure()`, restart unbound and check that it answers.** It has left
unbound stopped (observed: `unbound-checkconf` clean, every lookup timing out, and running the
reconfigure again did not bring it back). `dns add` and `dns rm` with `--apply` do this
themselves: after the write they restart unbound and resolve a name through `127.0.0.1` (the added
name; after a removal, an override that remains, else `localhost.`), and when unbound does not
answer they exit 2 saying the change is already in `config.xml`, so repair the resolver rather than
retry the edit. After a hand edit or any other call of the reconfigure, do it yourself: run
`pfSsh.php playback svc restart unbound`, then resolve a name on the box
(`host <name> 127.0.0.1`) and from another host, with a timeout. Reach the firewall by IP for
this: once unbound is down, its own name does not resolve either.

**A `php -f` script that calls `filter_configure_sync()` itself can die after `write_config()`.**
Observed on pfSense 2.8.1: the call fatal-errors on an undefined `filter_generate_dummynet_rules()`
(`filter.inc` line 380) unless the script also includes `shaper.inc`, which the GUI loads and a
bare script does not. By then `config.xml` already holds the change while pf and unbound still run
the old rules, and pfSense mails a PHP crash report. Do not reload from inside the script: after
`write_config()`, run `/etc/rc.filter_configure_sync` and `pfSsh.php playback svc restart unbound`
as separate commands, then read the live state back (`rules`, `rules --nat`,
`/var/unbound/host_entries.conf`) rather than trusting the script's exit.

**Tailscale's Accept DNS has to be turned off twice.** With it on, `tailscaled` points
`/etc/resolv.conf` at `100.100.100.100`, so the box stops resolving public names while LAN clients,
which query unbound directly, notice nothing. Set `installedpackages/tailscale/config/0/acceptdns`
to an empty value rather than deleting the element (observed: the package reads a missing one as
on), and save the package settings so it resyncs. The resync does not re-apply the flag to a node
that is already connected, so also run `tailscale set --accept-dns=false`. Verify:
`/etc/resolv.conf` lists `127.0.0.1` first, `tailscale debug prefs` shows `CorpDNS` false, a public
name resolves on the box, and `pfSense-upgrade -c` reports up to date. An unbound domain override
that forwards the tailnet's domain to `100.100.100.100` is no substitute: on FreeBSD/pfSense
quad-100 is reported not to answer, so verify that on the node first (see `bitranox:net-tailscale`).

**"Another instance of pfSense-upgrade is running" is usually a DNS symptom.** The background
package-metadata job runs `pfSense-upgrade`, hangs on a repository it cannot resolve while holding
the upgrade lock, and every later check then reports another instance. Fix the box's DNS first
(`doctor`). Remove a lock only once the box resolves public names and no `pfSense-upgrade` process
is still running (`ps -ax | grep '[p]fSense-upgrade'`).

## Retiring a host

A host reachable from outside leaves objects on up to five GUI pages, so build the list from
`config.xml` before asking to retire it, and put the whole list in the question. Take a
`snapshot` and parse it with an XML parser for the host's IP AND its names, grouped by parent path;
a plain grep also hits harmless `<username>admin@<ip></username>` audit strings. Expect:

- `unbound/hosts`: Resolver overrides, often with aliases for public names. An alias that another
  override also claims can be missing from `/var/unbound/host_entries.conf`, so read that file for
  the names an override really answers.
- `dnsmasq/hosts`: DNS Forwarder copies, inert while the Forwarder is off but still there.
- `dhcpd/<interface>/staticmap`: a DHCP reservation for the host's MAC and IP, removed with
  `dhcp rm`.
- `nat/rule`: port forwards, disabled ones included.
- `filter/rule`: pass rules. A forward whose `associated-rule-id` is empty has no linked rule, so
  any pass rule for it is a separate rule that deleting the forward leaves active. Find those by
  destination.

Remove by content (host and IP, target, destination), never by position. `dns rm` and `dhcp rm`
cover Resolver overrides and a DHCP reservation for the host; no verb removes Forwarder entries,
port forwards or rules, so do those in the GUI or in a `pfSsh.php playback` script that rebuilds
each list by content. Then reload with `/etc/rc.filter_configure_sync` and
`pfSsh.php playback svc restart unbound`. Read `/var/unbound/host_entries.conf` over ssh. Verify
that `rules`, `rules --nat` and `host_entries.conf` name the IP nowhere and that the remaining
sites still answer. Public DNS records at the registrar sit outside the firewall.

## Not covered here

pfBlockerNG, certificate and acme renewal, and traffic shaping in general are inspection-shaped
and change between releases. Drive them from the GUI or `pfSsh.php playback`, and take a
`snapshot` first. The one shaping case this skill does cover is a dummynet limiter: read
`references/limiters.md` before attaching one, or when one is on a rule but shapes nothing.

If you edited `config.xml` out of band rather than through the config API, the running config is
stale until `rm -f /tmp/config.cache && /etc/rc.filter_configure_sync`. That reloads the filter
only, not the DNS Resolver or DHCP: also run `services_unbound_configure()` (then restart unbound
and check it answers, see Traps) and the DHCP backend's own call (`services_dhcpd_configure()`
for ISC, `services_kea_configure()` for Kea). Edit the raw file with an XML parser, never sed (see
`bitranox:files-edit-xml`). Going through the API instead avoids all of this.

## Common mistakes

- Deleting an entry by its position in a listing. Every later position shifts, so the next delete
  from the same listing hits the wrong row and still exits 0. Select by MAC or by name.
- Reading ARP absence as "the device is gone". ARP is a cache that expires after minutes of
  silence, and a fixed-address reservation leaves no DHCP lease either, so neither source can
  prove absence. ARP is good for positive evidence only.
- Clearing `snort2c` and calling it fixed. The rule re-adds the address on the next packet. The
  fix that sticks has three parts, which `snort fixsteps` prints for the case at hand: suppress the
  SID that fired, add the range as a LITERAL entry in the Snort pass list (a firewall alias there
  is a no-op), and `snort unblock --apply` what is already blocked; then resync Snort and run
  `snort verify`.
