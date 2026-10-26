---
name: coding-python-network-probe
description: Use when Python code needs to ping a host, sweep hosts for reachability, measure round-trip time or packet loss, run a traceroute, scan ports, identify devices by their banner/greeting (FTP 220, SMTP, SSH version) or SNMP system group (uptime, sysName, sysDescr), find a MAC address or the host holding one, read the neighbour/ARP cache or write a static (permanent) entry to it, look up the default gateway or a route, inspect local interfaces and subnets, reach an IPv6 link-local (fe80::) address that needs its zone, send wake-on-LAN, find the path MTU, or watch a DHCP handshake to learn the address of a machine just started - especially as an ordinary user with no root, sudo, Administrator or CAP_NET_RAW, and without shelling out to ping, tracert, arp, ip, ifconfig or netstat. Also use when reaching for icmplib, scapy, python-nmap, netifaces, hand-rolled sockets for a banner grab, or subprocess around a system network command, or for tcpdump/tshark to watch a VM or container boot and find its address.
---

# Network probing from Python, unprivileged on the default paths

## Overview

Use `ipscout`. It does ICMP echo, traceroute, port scanning, banner grabs, SNMP system reads,
neighbour and route lookup, interface and subnet enumeration entirely in-process: no
subprocess, and no elevated rights on the default paths.

The two hard parts are both handled:

- **Unprivileged ICMP.** Linux and macOS use `SOCK_DGRAM`/`IPPROTO_ICMP`, the
  kernel's "ping socket". Windows goes through `iphlpapi.dll` (`IcmpSendEcho`)
  by ctypes. Neither needs elevation. Raw sockets, which the usual
  alternatives reach for, do.
- **No output parsing.** Nothing shells out to `ping`, `tracert`, `arp`, `ip`
  or `ifconfig`, so there is no locale-dependent regex to break and no process
  spawned per probe.

## Install

```bash
uv pip install ipscout      # library
uvx ipscout ping 1.1.1.1    # CLI, no install
```

Python 3.10+.

## Quick reference

| Task                                | Call                                                                                                       |
|-------------------------------------|------------------------------------------------------------------------------------------------------------|
| Ping one host                       | `ping("1.1.1.1", 4)`                                                                                       |
| Sweep many, concurrently            | `ping_many(hosts, concurrency=64)`                                                                         |
| Is it up, by any means              | `is_reachable(host)`                                                                                       |
| Path to a host                      | `traceroute(host)`                                                                                         |
| Scan ports                          | `scan_ports(host, "22,80,8000-8100")`                                                                      |
| What each host says first on a port | `grab_banners(hosts, 21, farewell=b"QUIT\r\n")` -> host: `Banner`                                          |
| Uptime, name, model over SNMP       | `read_snmp_system(hosts)` -> host: `SnmpSystem`                                                            |
| MAC of an address                   | `lookup_mac(ip)`, `get_mac_address(ip)`                                                                    |
| MAC, asked if possible, else cache  | `lookup_mac(ip, active=True, fallback_to_cache=True)` -> `.method` says which                              |
| Which host holds a MAC              | `find_ip_by_mac(mac, scan=True, family=AddressFamily.IPV4)`                                                |
| Neighbour / ARP cache               | `neighbours()`, `arp_scan(network)`; both take `family=`                                                   |
| ... only the REACHABLE entries      | `[e for e in neighbours() if e.state is NeighbourState.REACHABLE]`                                         |
| Static ARP entry, IPv4 (privilege)  | `set_neighbour(ip, mac, interface="eth0")` -> the entry read back                                          |
| ... and out again                   | `remove_neighbour(ip, interface="eth0")` -> whether there was one                                          |
| What a sweep will cover             | `sweep_scope()` -> `SweepScope(limit, networks, skipped, complete)`                                        |
| Sweep exactly that plan             | `arp_scan(scope=scope)`, `find_ip_by_mac(mac, scan=True, scope=...)`                                       |
| Default route, any route            | `default_gateway()`, `query_route(ip)`                                                                     |
| Interfaces and subnets              | `local_interfaces()`, `subnet_info()`, `local_networks()`                                                  |
| Wake a sleeping host                | `wake_on_lan(mac)`                                                                                         |
| Address of a machine just started   | `observe_dhcp(mac, interface="br0")` -> every offer, in order                                              |
| ... startable before you start it   | `with observe_dhcp_session(mac, interface="br0") as s:`                                                    |
| ... and just the one that answers   | `observe_dhcp_first_reachable(mac, interface="br0")`                                                       |
| Largest unfragmented packet         | `path_mtu(host)`                                                                                           |
| What can this host do               | `icmp_available()`, `dhcp_capture_available()`                                                             |
| Package metadata                    | `print_info()`                                                                                             |
| Name to address, and back           | `resolve(name)`, `reverse_dns(ip)`                                                                         |
| Compare two hardware addresses      | `normalise_mac(written)`                                                                                   |
| Parse a port specification          | `parse_ports("22,80,8000-8100")`                                                                           |
| Trace over your own transport       | `trace_path(transport, ...)`, `atrace_path(...)`                                                           |
| async equivalents                   | `aping`, `aping_many`, `ais_reachable`, `atraceroute`, `ascan_ports`, `agrab_banners`, `aread_snmp_system` |

`neighbours()` returns both families unless `family=` narrows it. An entry's `state` is a
`NeighbourState`: `REACHABLE`, `STALE`, `PERMANENT` (a static entry, as `set_neighbour` writes),
`INCOMPLETE`, `FAILED` or `OTHER` - a state the OS does not report or that maps to none of the
others. A REACHABLE-only filter therefore drops static entries too, and on macOS it returns
nothing: the macOS routing dump carries no per-entry state, so every entry there is `OTHER`.
A cache state says what the kernel last saw, never whether a host is up now: to decide that on
every platform, probe the entry with `is_reachable(entry.scoped)`, never `entry.ip` (see below).

```python
import ipscout

result = ipscout.ping("1.1.1.1", 4)
result.reached, result.time_avg_ms, result.packets_lost_percentage

up = [h for h, r in ipscout.ping_many(hosts, times=1, concurrency=64).items() if r.reached]
```

Run `ipscout --help` and `ipscout <command> --help` for every flag. That is the
authoritative, always-current list; do not trust a flag list copied into any
document, including this one. Check `ipscout.__all__` before assuming a
function exists.

## From the shell

Twenty-three subcommands, one per capability above:

```
ping            ping-many         reachable     traceroute    scan-ports
banners         mac               find-ip       arp-scan      neighbours
gateway         set-neighbour     remove-neighbour  subnet    interfaces
resolve         reverse-dns       mtu           wake          observe-dhcp
snmp-system     capabilities      info
```

```bash
ipscout ping 1.1.1.1 -c 4
ipscout scan-ports 192.0.2.10 --ports 22,80,443,8000-8100
ipscout banners 192.0.2.0/24 --port 21 --farewell 'QUIT\r\n'   # networks expand to hosts
ipscout snmp-system 192.0.2.0/28         # community from IPSCOUT_SNMP_COMMUNITY, else public
ipscout mac 8.8.8.8                       # the gateway's, labelled next_hop
ipscout find-ip 00:00:5e:00:53:af --scan -4   # -4/-6 on find-ip, arp-scan, neighbours too
ipscout arp-scan --network 192.0.2.0/24
ipscout observe-dhcp 02:00:5e:10:00:00 --interface br0   # needs root
ipscout capabilities                      # what this host can actually do
ipscout --json subnet                     # every command takes --json
```

`ipscout <command> --help` is the authoritative flag list for each. `capabilities` is worth
knowing about: it reports what this host can do - ICMP per family, traceroute - so a caller can
find out without provoking an error.

## Identifying a device by what it says: one connection per host

Many services speak first - FTP and SMTP send a `220` line, SSH its version string - so a device
is often identified by its greeting rather than by which port is open. `grab_banners` connects,
reads up to the first newline, sends `farewell` if a line came back, and closes, all on ONE
connection per host. It is a plain TCP connect, so it needs no privilege. It takes host strings,
not a network, so expand one yourself:

```python
import ipaddress

hosts = [str(h) for h in ipaddress.ip_network("192.0.2.0/24").hosts()]
results = ipscout.grab_banners(hosts, 21, timeout=3.0, farewell=b"QUIT\r\n", concurrency=64)
printers = [host for host, b in results.items() if b.line is not None and b.line.startswith("220 Print Server")]
```

Match the part of the greeting that names the device: every FTP server sends a `220` line, so
`startswith("220")` finds FTP servers, not the device you are after.

Never `scan_ports` first and connect again to read: some embedded servers refuse a new connect
for a moment after each session, so the second connect misses exactly the devices you wanted.

Each value is a `Banner`; its `state` is a `BannerState`: `GREETED` (`line` holds the first line,
decoded as UTF-8 with undecodable bytes replaced by U+FFFD, terminator and surrounding whitespace
removed), `SILENT` (connected, nothing sent before the deadline), `REFUSED`, or `UNREACHABLE`
(`error` says why, as text: the resolver's or the OS's message, or that no connection came within
`timeout`). `line` is set exactly when `state` is `GREETED` and `error` only when it is
`UNREACHABLE` - both are `None` otherwise - so `b.line is not None` is the same test as the state
check and narrows the type. Every distinct host STRING gets one entry, keyed exactly as given
(case included, nothing resolved or folded), at the position of its first occurrence; a repeat
is grabbed once. A name that does not resolve is `UNREACHABLE`, never a raise. A refusal is reported, not retried - retry it yourself
when the device needs it. `timeout` is one deadline per host for resolve, connect and read
together; `max_line_bytes` (512) caps the line, and a longer one is cut there and still `GREETED`.
`farewell` goes to every host that sent a line, never to a silent one, and the connection closes
right after it without waiting for a reply. A port outside 1-65535, or a `timeout`, `max_line_bytes` or `concurrency`
that is not positive, raises `ValueError` before anything connects.

## Reading a device's SNMP system group

Most printers, switches and print servers run an SNMP agent. `read_snmp_system` asks each host
for sysUpTime, sysName, sysDescr and sysObjectID in ONE GET over a connected UDP socket. Plain UDP
to port 161, so it needs no privilege. Like `grab_banners` it takes host strings, not a network:
a string such as `"192.0.2.0/28"` is read as a name that does not resolve and comes back
`UNREACHABLE`, so expand it with `ipaddress` as shown above (the `snmp-system` command expands
networks for you). The defaults are `community="public"`,
`port=161`, `timeout=3.0` seconds per host, `concurrency=64` and `version=SnmpVersion.V1`:

```python
results = ipscout.read_snmp_system(["192.0.2.10", "192.0.2.11"], community="public", timeout=3.0)
for host, s in results.items():
    if s.state is ipscout.SnmpState.ANSWERED:
        print(host, s.name, s.uptime_seconds, s.object_id)
```

The uptime is the restart detector: read it before an action that restarts the device and again
after, and a SMALLER value means it restarted, which a reachability check cannot tell you. Three
holes in that test: the counter wraps to 0 after about 497 days (TimeTicks is 32 bits of
hundredths), so a smaller value can also be a wrap; `uptime_seconds` is `None` when the agent does
not report sysUpTime; and a read that is not `ANSWERED` before the action gives you no baseline to
compare against, so check the first read's state before acting.

Each value is an `SnmpSystem`; its `state` is an `SnmpState`:

- `ANSWERED` - the agent replied; `uptime_seconds`, `name`, `description`, `object_id` are each
  `None` when the agent lacks that value.
- `SILENT` - nothing arrived before the deadline. A host that is down, a WRONG COMMUNITY (SNMP
  answers a bad community with silence), the other SNMP version, a firewall dropping UDP 161, a
  `timeout` too short for a slow agent, and no agent on a host whose port-unreachable reply is
  dropped all look like this. `is_reachable(host)` separates a down host from the rest; nothing
  separates the others from each other.
- `REFUSED` - ICMP port unreachable came back: the host is up and nothing listens on that port.
  No agent shows as `REFUSED` only when that ICMP reply reaches you; filtered, it is `SILENT`.
- `ERROR` - the agent sent an error status or a reply that is not a valid answer; `error` says which.
- `UNREACHABLE` - the name did not resolve or the network reported no route; `error` says why.

`version=SnmpVersion.V1` (the default) or `SnmpVersion.V2C`, never both: an agent that speaks only
the other version stays SILENT, which cannot be told from a dead host, so there is no automatic
fallback - pick the one the device speaks. Under v1 a GET fails as a whole when one value is
unknown, so the read asks again without it and reports it as `None`. Every distinct host STRING
gets one entry, keyed exactly as given (case included, nothing resolved or folded), at the position
of its first occurrence; a repeat is read once. A bare string as `hosts` raises `ValueError`, as
does a `port` outside 1-65535, a non-positive `timeout` or `concurrency`, or an empty `community`,
all before anything is sent. The community never appears in an error; from the shell pass it as
`IPSCOUT_SNMP_COMMUNITY`, not `--community`, which every user sees in the process list. The
command takes `--version v1|v2c` and `--port`, and exits `0` when any host ANSWERED, `1` when
none did, `2` on a bad argument.

## The error contract

Setup problems raise; network conditions do not. `except IPScoutError` catches every one of
them, and `AddressFamily.IPV4` / `IPV6` is what the `family=` argument takes - on the probes,
and on the three calls that RETURN addresses (`find_ip_by_mac`, `neighbours`, `arp_scan`).

Those three differ from `resolve` in one way worth knowing: asking for a family the target
does not have is an **empty result, not an error**. For `resolve` an empty list would be
indistinguishable from "host down", so it raises; for these, empty already means "not known
here", and "that MAC holds no IPv6" is an ordinary finding.

- A host that is down, times out, or loses every packet returns
  `reached=False`. It does **not** raise.
- An unresolvable name, missing permission, or nonsensical argument raises
  `IPScoutResolutionError`, `IPScoutPermissionError`, `IPScoutUnsupportedError`
  or `ValueError`. The many-host calls are the exception for a bad NAME: `ping_many` puts it
  on that target's `.error`, and `grab_banners` and `read_snmp_system` report it as an
  `UNREACHABLE` result, so one typo cannot cost the other results. A nonsensical argument still
  raises before anything is sent.
- A sweep that cannot cover the ground it was asked about raises
  `IPScoutSweepTooWideError` or `IPScoutSweepIncompleteError`. Catch
  `IPScoutSweepError` for either; both are also `ValueError`.

That split is the point: a permissions problem and a dead host need different
responses, so they arrive through different channels.

`is_reachable` is the deliberate exception. It never raises and always falls
back to TCP, which is what makes it a one-line shortcut. It is not
`ping(host).reached`.

## A MAC address does not survive a router hop

The frame sent toward `8.8.8.8` carries the **next-hop router's** address; the
remote host's own never appears in any packet arriving here. No privilege
level changes that. So there are two functions, and the scope is part of the
answer:

```python
ipscout.lookup_mac("8.8.8.8")
# MacLookup(mac='...', scope=MacScope.NEXT_HOP, via_ip='192.0.2.1')
ipscout.get_mac_address("8.8.8.8")  # None: refuses to pass off the gateway's
```

There is also no protocol that asks "who has this MAC" - RARP is dead. So
`find_ip_by_mac(mac, scan=True)` sweeps and then reads the cache. It returns a
**list**: one hardware address legitimately holds several addresses, commonly
an IPv4 and an IPv6 link-local on the same NIC. Each address is listed once.

`network=` and `scope=` apply only with `scan=True`, and are refused without it
rather than ignored - without a sweep there is only the cache to search.

## One MAC can carry several interfaces, and one address several machines

Both directions of that mapping are many-to-one, and code that assumes either
is one-to-one fails silently rather than loudly.

**One hardware address, several interfaces.** A MANA NIC presents the synthetic
adapter and its VF under the same address, so a MAC-to-one-interface map drops
whichever it sees second and an index comparison ends up comparing against a
list. Nothing here keeps such a map: `local_interfaces()` is keyed by interface
name and every record carries its own `mac`, so both appear and you decide per
interface by its own address. The neighbour cache holds an entry per interface
for the same reason, which is why `find_ip_by_mac` lists each address once
instead of once per entry.

**One address, several machines.** An address is only unique per link: a
link-local address names a different machine on each interface, and a
multi-homed host can hold the same address on two of them. So `lookup_mac`
answers from the entry learned on the interface the frame would actually leave
by, and the `MacLookup` it returns carries that interface - the answer says
which link it is about rather than leaving you to guess.

### Writing a link-local address: name the interface, by index

A `fe80::` address needs the zone that RFC 4007 writes after a `%`, and
**every call takes it**: `ping`, `is_reachable`, `scan_ports`, `traceroute`,
`lookup_mac`, `query_route`. Without one there is no link to send on, so it is
refused by name rather than reported as an unreachable host.

```python
interface = next(i for i in ipscout.local_interfaces() if i.name == "eth0")
ipscout.ping(f"fe80::200:5eff:fe00:5310%{interface.index}")
```

Use `interface.index`, not `interface.name`. The index is the one spelling
that works on every platform: **Windows reports a friendly name here**
(`Ethernet 4`) that neither `getaddrinfo` nor `if_nametoindex` recognises, both
of which speak a different namespace (`ethernet_32775`). An interface name as a
zone fails resolution outright there - measured on a real Windows host. The
names in `neighbours()` and `query_route()` come from that second namespace and
do work as zones, but only the index is portable.

**Join the zone yourself only when you started from an interface.** What a
lookup hands back already carries it: a cache entry offers `scoped`, and
`find_ip_by_mac` returns that form, so an answer goes straight back in.

```python
entry = ipscout.neighbours()[0]
entry.ip  # 'fe80::200:5eff:fe00:53af'  - no link, so no probe accepts it
entry.scoped  # 'fe80::200:5eff:fe00:53af%eth0'
ipscout.ping(entry.scoped)

ipscout.ping(ipscout.find_ip_by_mac("00:00:5e:00:53:af", family=ipscout.AddressFamily.IPV4)[0])
```

Do not add a zone to one of those - `f"{found}%{interface.index}"` builds
`fe80::1%eth0%2`, which is refused. `scoped` joins the interface only where it
means something, an IPv6 link-local address, and is the plain address for
everything else, so an IPv4 answer is unchanged.

## Finding a machine that has not got an address yet

Every other call needs the target already up and answering: the neighbour cache
only knows hosts that have sent traffic, and a sweep needs a host that already
holds an address. A machine that has just been started has neither, and it
DHCPs about a second after the start command. `observe_dhcp` watches that
exchange.

Two rules that are easy to get wrong, and both cost real debugging:

**Start watching before you start the machine.** A one-shot `observe_dhcp(...)`
begins capturing when it is called, which is already too late if you issued the
start command first. Use the session:

```python
with ipscout.observe_dhcp_session(mac, interface="br0", timeout=150) as watch:
    start_the_machine()  # the handshake happens ~1s into this
    addresses = watch.result()  # blocks until the exchange goes quiet
```

**The address it settled on is the LAST element, not the first.** A pool that
hands out an address the guest declines offers the working one afterwards, so
the list is chronological, not ranked. Taking `[0]` is how a perfectly
reachable machine gets reported as never having booted. Either check each one,
or let `observe_dhcp_first_reachable(mac, interface="br0")` do it - it returns
as soon as a candidate answers, so a SUCCESSFUL lookup skips the settle
wait entirely. Finding nothing still costs the whole `timeout`, because
giving up earlier would declare a machine absent while its window was open.

`result()` returns once 12 seconds pass with no new address, or when `timeout`
runs out. That makes 12 seconds a floor on every call; if that is too slow,
iterate `session.offers()` rather than shortening `timeout`, which truncates
the second offer and re-creates the bug above.

All three platforms, and every one needs elevation: root or `CAP_NET_RAW` on
Linux, root on macOS, Administrator on Windows. Ask `dhcp_capture_available()`
first.

**They do not all promise the same thing, and the difference decides whether
this works for you.** On Linux and macOS the capture binds to a bridge and sees
the traffic the bridge forwards, including frames addressed to a guest - which
is the VM case this exists for. On Windows it uses `SIO_RCVALL`, which sees
what reaches *this host's* interface; on a Hyper-V virtual switch that excludes
other guests unless the port is set to mirror. So Windows is right for DHCP on
this host's own segment, and the POSIX pair for watching a guest boot.

**The macOS device path has not been run on real hardware** (ipscout 1.6.0, checked
2026-08-28 - `ipscout --version`; treat it as still true unless a later release says
otherwise). No CI runner may
open a BPF device, so its ioctl encoding and record splitting are pinned by
tests while the syscalls themselves are untested. Linux is the one to trust for
anything that matters; treat macOS as new until you have exercised it. On macOS
name a bridge or physical interface, not `lo0` - loopback is not Ethernet-framed
and is refused by name rather than silently returning nothing.

## What needs privilege, and what it does about it

The operations in this table need privilege, apart from the exceptions a row names;
everything else in this skill runs unprivileged. Each of these raises `IPScoutPermissionError` naming the exact remedy rather than
degrading:

| Operation                                     | Needs                                                                                                                                                                                                                                       |
|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `scan_ports(..., method=ScanMethod.SYN)`      | root / `CAP_NET_RAW`. Unavailable on Windows at any privilege level: raw TCP sends have been blocked since XP SP2                                                                                                                           |
| `lookup_mac(ip, active=True)`                 | root / `CAP_NET_RAW` on Linux and macOS. Windows IPv4 needs none (`SendARP`); Windows IPv6 needs Administrator                                                                                                                              |
| Traceroute on macOS                           | a raw socket, so root. Unprivileged macOS does not surface Time Exceeded at all                                                                                                                                                             |
| `observe_dhcp(...)` and its session           | root / `CAP_NET_RAW` on Linux, root on macOS (`/dev/bpf`), Administrator on Windows (`SIO_RCVALL`, no driver)                                                                                                                               |
| `set_neighbour(...)`, `remove_neighbour(...)` | root / `CAP_NET_ADMIN` on Linux, root on macOS (routing socket, untested on real hardware), Administrator on Windows. `remove_neighbour` without `interface=` reads the cache first and answers `False` unprivileged when nothing is listed |

The rules these follow, worth relying on:

- **They never silently degrade.** `active=True` without the rights raises; it does not hand
  back a stale cache entry dressed up as a fresh one. A SYN scan does not quietly become a
  connect scan. To get an answer either way, ask for the fallback out loud:
  `lookup_mac(ip, active=True, fallback_to_cache=True)` reads the cache only when this host
  cannot ask: no privilege (`IPScoutPermissionError`), or an interface that cannot carry the
  request (no hardware address, as on loopback), no route, or a send that failed (all
  `IPScoutUnsupportedError`). Every `MacLookup` says in `method` which one answered:
  `MacMethod.ACTIVE` (asked through the active path; on Windows IPv4 that is `SendARP`,
  which answers from Windows' own ARP table when it holds the address and sends a request
  only when it does not) or `MacMethod.CACHE`. An active ask nobody answered stays `ACTIVE`
  with `mac=None` and is never replaced by a cache entry: no reply before the timeout (on
  Windows, `ERROR_BAD_NET_NAME`, the only status read as no reply) is that miss, while any
  other error the OS reports while sending or reading is the failed send above. A host name
  (`ValueError`) and a zone naming no interface at all (`IPScoutResolutionError`, a typo
  such as `%eht0`; an index is accepted, and on Windows both the friendly adapter name
  `local_interfaces()` reports and the `if_nametoindex` name) raise whatever
  `fallback_to_cache` says, and `fallback_to_cache=True` without `active=True` is a
  `ValueError`. `get_mac_address` takes the same flag but returns only the address, and its
  `None` then cannot tell an active miss from a cache miss, so use `lookup_mac` when the
  method matters. CLI: `ipscout mac IP --active --fallback-to-cache`. Never wrap
  `active=True` in `except IPScoutError` and retry passively yourself: that also swallows
  the typo'd zone, and the cache record you get back cannot tell an active ask that was
  refused from one never tried.
- **Writing the neighbour cache has no unprivileged route.** `set_neighbour` maps an IPv4
  address to one device's MAC (the ARP trick embedded devices are first addressed with), returns
  the entry read back from the cache (a `Neighbour`; state `PERMANENT` on Linux and Windows,
  `OTHER` on macOS), and replaces an existing
  one; IPv6 raises `IPScoutUnsupportedError`. `interface=` is optional: left out, it picks the one
  interface whose subnet holds the address and raises `IPScoutUnsupportedError` when none or
  several do, so an address outside every local subnet needs `interface=` named. The entry
  outlives the process, so call `set_neighbour` BEFORE the `try` and
  `remove_neighbour` it in the `finally`: a refused write then leaves nothing to remove.
  `remove_neighbour` with `interface=` always asks the kernel: unprivileged it raises
  `IPScoutPermissionError` even when nothing is there, privileged it answers `False` when there
  was no entry. It deletes rather than restores, so a replaced entry is gone: borrow an address
  that has no entry, checked first with `get_mac_address(ip, active=True)` (`None` = nothing
  answers). With the fallback, use `lookup_mac` and read `method` first: a `CACHE` answer
  with no MAC only says this host has not talked to that address, not that it is free, so do
  not borrow on it: get the privilege for an active ask, or pick an address you know. A
  neighbour entry is not a route - traffic to an address outside every local subnet
  still goes to the gateway and never uses it - so borrow an address inside a local subnet; ipscout
  adds no routes. `interface=` takes the index as digits (portable) or a name - unlike a zone,
  where Windows resolves only the index: on Windows either
  the friendly name `local_interfaces()` reports or the one `neighbours()` reports; remove with the
  same interface you set on, in any of those spellings (each resolves to its index).
- **For the READ operations, the unprivileged route to the same answer is named in the
  message** (a write has none, as above).
  Usually `arp_scan()`, which sweeps and then reads the cache, needing nothing.
  `observe_dhcp` is the one exception, and its message says so plainly: there
  is no unprivileged way to watch another machine's traffic. It points at
  `subnet_info()`, which needs nothing but describes only this host, or at
  running the observer on the host that owns the bridge.

## Do not reach for these instead

| Instead of                             | Why it fails the no-admin requirement                                                                                                                                                                                                                                 |
|----------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `icmplib` with `privileged=False`      | Unprivileged on Linux, but **not on Windows**. Its `sockets.py` reads `self._privileged = privileged or PLATFORM_WINDOWS`, then opens `SOCK_RAW` - Windows forces raw sockets and needs Administrator whatever you pass. Check the source before believing otherwise. |
| `scapy` `arping()` / `sr1()`           | Raw sockets: root, or npcap-with-admin on Windows.                                                                                                                                                                                                                    |
| `subprocess` around `ping` / `tracert` | A process per probe, and output that shifts with locale and distro.                                                                                                                                                                                                   |
| `python-nmap`                          | The useful scan modes want raw-socket privilege, and it shells out to `nmap`.                                                                                                                                                                                         |
| `netifaces`                            | Long unmaintained and needs a C build; `local_interfaces()` and `subnet_info()` cover it with no build step.                                                                                                                                                          |

## For machine consumers

`--json` emits `{"ok": ..., "command": ..., "data": ..., "skipped": [...]}`; a
failure is `{"ok": false, ..., "error": {"type": ..., "message": ...}}` rather
than a traceback. `--json-bare` drops the envelope for `jq`, and reports a
failure as the bare `{"type": ..., "message": ...}` so the pipeline still gets
JSON. `skipped` names any network a sweep could not cover, which is how a
partial answer is told from a complete one; the same note goes to stderr, never
to the stream you parse. Exit codes are `0` reached, `1` not reached, `2` error
- a bad name, a missing capability, or a malformed command line - independent of
output format. `remove-neighbour` exits `1` when there was no entry to remove, and `banners`
when no host greeted, `snmp-system` when no host ANSWERED.

## What it will not do, and why

- **Async is executor-backed on Windows.** Genuinely async on Linux and macOS,
  where a sweep of thousands shares one socket on one thread. `IcmpSendEcho`
  is a blocking C call with no asyncio integration.
- **A connect scan cannot tell CLOSED from FILTERED on Windows.** Measured on
  a runner: a closed port there goes quiet rather than refusing, so it reports
  `FILTERED`. On Linux and macOS a refusal is reported as `CLOSED`. A SYN scan
  draws the line everywhere it can run, which is not Windows.
- **ipscout never sends DHCP traffic.** `subnet_info()` reads the lease the
  OS's own client already stored, and `observe_dhcp` only listens - it never
  requests an address or answers anybody. The DHCP fields on `subnet_info()`
  may be unset on macOS and Windows; the addressing fields work everywhere.
- **`observe_dhcp` puts the interface in promiscuous mode.** It has to: on a
  bridge a reply is forwarded to the guest's own port and never reaches this
  host otherwise, and a Linux client does not set the broadcast flag that
  would make it visible. Pass `promiscuous=False` to decline, and expect to
  see only broadcast replies if you do.
- **`path_mtu` may return `None`.** That is an answer, not a failure: an MTU
  sizes packets, so a guessed one is a silent black hole.
- **`wake_on_lan` returns nothing.** Nothing acknowledges a magic packet, so a
  successful send means only that it left this host. Poll `is_reachable` to
  find out whether the target woke.

## When ICMP is unavailable

Some hardened hosts and CI runners disable the ping socket. You get an
`IPScoutPermissionError` whose message names the fix. Check first rather than
provoking it:

```python
if not ipscout.icmp_available():
    reachable = ipscout.is_reachable(host)  # falls back to TCP
```

Or `ping(host, allow_tcp_fallback=True)`. The fallback is always opt-in and the
result records `method=ProbeMethod.TCP`, because a TCP handshake time is not an
ICMP round trip and a filtered port is not a dead host.

## Common mistakes

- Taking `observe_dhcp(...)[0]` as the machine's address. It is the first
  address OFFERED, which is frequently the one the guest declined; the one
  it kept is last. Check them, or use `observe_dhcp_first_reachable`.
- Treating `is_reachable` as `ping(...).reached`. The first never raises and
  tries TCP; the second raises on a bad name and reports ICMP only.
- Reading `scan_ports` as a boolean map. It returns each port mapped to a `PortState`: `OPEN`
  means the handshake completed, `CLOSED` means something refused, `FILTERED` means nothing
  answered, and conflating the last two hides the firewall you were looking for.
- Calling `ping_many`, `scan_ports`, `grab_banners` or `read_snmp_system` from inside a running
  event loop. They raise `RuntimeError` rather than deadlocking - await `aping_many`,
  `ascan_ports`, `agrab_banners` or `aread_snmp_system` there.
- Finding open ports with `scan_ports` and then connecting again to read a banner. That is two
  sessions, and a device that refuses a reconnect right after one is missed; `grab_banners`
  reads on the connection it opens.
- Reading `time_avg_ms` without checking `reached`. Nothing received gives the
  `-1.0` sentinel, not `0.0`, and averaging that across a sweep is nonsense.
- Taking `find_ip_by_mac(...)[0]` without naming a family, then connecting to it. One MAC
  commonly holds an IPv4 AND an IPv6 link-local, and the list is in the order the cache
  learned them, not by family - so the first entry is decided by that order. Pass
  `family=AddressFamily.IPV4` when the answer is going to be connected to.
- Reading an empty `find_ip_by_mac(..., scan=True)` as "that host is gone"
  without checking coverage. A sweep with no network given covers the subnets
  this host is attached to that fit inside one sweep's 4096-address budget
  (counted across all of them, spent in the order the host reports them) and
  skips the rest, so a container bridge on a `/16` goes uncovered. A search that matched
  nothing over partial ground raises `IPScoutSweepIncompleteError` rather than
  answering; a search that found something can still be short an address held
  on the skipped network. Ask `sweep_scope()` when it matters, and name a
  narrower CIDR to cover a bridge.
