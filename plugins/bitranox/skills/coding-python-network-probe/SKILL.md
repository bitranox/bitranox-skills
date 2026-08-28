---
name: coding-python-network-probe
description: Use when Python code needs to ping a host, sweep hosts for reachability, measure round-trip time or packet loss, run a traceroute, scan ports, find a MAC address or the host holding one, read the neighbour/ARP cache, look up the default gateway or a route, inspect local interfaces and subnets, reach an IPv6 link-local (fe80::) address that needs its interface zone, send a wake-on-LAN packet, find the path MTU, or watch a DHCP handshake to learn the address of a machine that has just been started and does not have one yet - especially when it must run as an ordinary user with no root, sudo, Administrator or CAP_NET_RAW, and must not shell out to ping, tracert, arp, ip, ifconfig or netstat. Also use when reaching for icmplib, scapy, python-nmap, netifaces, or subprocess around a system network command, or for tcpdump/tshark to watch a VM or container boot and find its address.
---

# Network probing from Python, unprivileged on the default paths

## Overview

Use `ipscout`. It does ICMP echo, traceroute, port scanning, neighbour and
route lookup, interface and subnet enumeration entirely in-process: no
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

| Task                              | Call                                                                 |
|-----------------------------------|----------------------------------------------------------------------|
| Ping one host                     | `ping("1.1.1.1", 4)`                                                 |
| Sweep many, concurrently          | `ping_many(hosts, concurrency=64)`                                   |
| Is it up, by any means            | `is_reachable(host)`                                                 |
| Path to a host                    | `traceroute(host)`                                                   |
| Scan ports                        | `scan_ports(host, "22,80,8000-8100")`                                |
| MAC of an address                 | `lookup_mac(ip)`, `get_mac_address(ip)`                              |
| Which host holds a MAC            | `find_ip_by_mac(mac, scan=True, family=AddressFamily.IPV4)`          |
| Neighbour / ARP cache             | `neighbours()`, `arp_scan(network)`; both take `family=`             |
| What a sweep will cover           | `sweep_scope()` -> `SweepScope(limit, networks, skipped, complete)`  |
| Sweep exactly that plan           | `arp_scan(scope=scope)`, `find_ip_by_mac(mac, scan=True, scope=...)` |
| Default route, any route          | `default_gateway()`, `query_route(ip)`                               |
| Interfaces and subnets            | `local_interfaces()`, `subnet_info()`, `local_networks()`            |
| Wake a sleeping host              | `wake_on_lan(mac)`                                                   |
| Address of a machine just started | `observe_dhcp(mac, interface="br0")` -> every offer, in order        |
| ... startable before you start it | `with observe_dhcp_session(mac, interface="br0") as s:`              |
| ... and just the one that answers | `observe_dhcp_first_reachable(mac, interface="br0")`                 |
| Largest unfragmented packet       | `path_mtu(host)`                                                     |
| What can this host do             | `icmp_available()`, `dhcp_capture_available()`                       |
| Package metadata                  | `print_info()`                                                       |
| Name to address, and back         | `resolve(name)`, `reverse_dns(ip)`                                   |
| Compare two hardware addresses    | `normalise_mac(written)`                                             |
| Parse a port specification        | `parse_ports("22,80,8000-8100")`                                     |
| Trace over your own transport     | `trace_path(transport, ...)`, `atrace_path(...)`                     |
| async equivalents                 | `aping`, `aping_many`, `ais_reachable`, `atraceroute`, `ascan_ports` |

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

Nineteen subcommands, one per capability above:

```
ping          ping-many     reachable     traceroute    scan-ports
mac           find-ip       arp-scan      neighbours    gateway
subnet        interfaces    resolve       reverse-dns   mtu
wake          observe-dhcp  capabilities  info
```

```bash
ipscout ping 1.1.1.1 -c 4
ipscout scan-ports 192.168.1.10 --ports 22,80,443,8000-8100
ipscout mac 8.8.8.8                       # the gateway's, labelled next_hop
ipscout find-ip 00:00:5e:00:53:af --scan -4   # -4/-6 on find-ip, arp-scan, neighbours too
ipscout arp-scan --network 192.168.1.0/24
ipscout observe-dhcp 02:00:5e:10:00:00 --interface br0   # needs root
ipscout capabilities                      # what this host can actually do
ipscout --json subnet                     # every command takes --json
```

`ipscout <command> --help` is the authoritative flag list for each. `capabilities` is worth
knowing about: it reports what this host can do - ICMP per family, traceroute - so a caller can
find out without provoking an error.

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
  or `ValueError`.
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
# MacLookup(mac='...', scope=MacScope.NEXT_HOP, via_ip='192.168.1.1')
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

Everything above is unprivileged. These are not, and each raises
`IPScoutPermissionError` naming the exact remedy rather than degrading:

| Operation                                | Needs                                                                                                             |
|------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `scan_ports(..., method=ScanMethod.SYN)` | root / `CAP_NET_RAW`. Unavailable on Windows at any privilege level: raw TCP sends have been blocked since XP SP2 |
| `lookup_mac(ip, active=True)`            | root / `CAP_NET_RAW` on Linux and macOS. Windows IPv4 needs none (`SendARP`); Windows IPv6 needs Administrator    |
| Traceroute on macOS                      | a raw socket, so root. Unprivileged macOS does not surface Time Exceeded at all                                   |
| `observe_dhcp(...)` and its session      | root / `CAP_NET_RAW` on Linux, root on macOS (`/dev/bpf`), Administrator on Windows (`SIO_RCVALL`, no driver)     |

Two rules these follow, worth relying on:

- **They never silently degrade.** `active=True` without the rights raises; it
  does not hand back a stale cache entry dressed up as a fresh one. A SYN scan
  does not quietly become a connect scan.
- **The unprivileged route to the same answer is named in the message.**
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
output format.

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
- Reading `scan_ports` as a boolean map. It returns `PortState`: `CLOSED` means
  something refused, `FILTERED` means nothing answered, and conflating them
  hides the firewall you were looking for.
- Calling `ping_many` or `scan_ports` from inside a running event loop. They
  raise rather than deadlocking - `await aping_many(...)` there.
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
