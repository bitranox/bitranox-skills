"""A fake pfSense firewall behind pfsense.py's one process seam (`run`), plus a scenario matrix.

`FakeFirewall` answers every command the CLI sends over ssh the way a real box does: each PHP
body is recognised EXACTLY (it is rebuilt with the module's own builder and compared byte for
byte), executed against an in-memory config with the semantics of the PHP it carries, and
answered with the JSON that PHP would echo. A command it does not know raises `UnknownCommand`
rather than answering something plausible, so a change in what the CLI sends cannot pass
unnoticed. No real firewall is ever involved.

`run_matrix` drives every cmd_* through `main()` against a fresh fake per scenario and records
the exit code, stdout, stderr, every command sent and the config left behind. Two module versions
that produce the same records behave the same on every scenario: that is the before/after
harness the typed-record conversion of run_php's results is held to.
"""
import contextlib
import hashlib
import io
import ipaddress
import json
import random
import re
import shlex
import shutil
import sys
import types
import xml.etree.ElementTree as ET
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

PRELUDE = '<?php\nrequire_once("config.inc");\nrequire_once("util.inc");\n'
RESTART = "pfSsh.php playback svc restart unbound"
SNORT_INSTANCE = "/usr/local/etc/snort/snort_12345_igb1"
_LITERAL_RX = re.compile(r"'((?:[^'\\]|\\.)*)'")
_HOST_RX = re.compile(r"^host (\S+) 127\.0\.0\.1$")
_TEST_F_RX = re.compile(r"^test -f (\S+)$")
_PFCTL_SHOW_RX = re.compile(r"^pfctl -t (\S+) -T show$")
_PFCTL_DEL_RX = re.compile(r"^pfctl -t (\S+) -T delete (\S+)$")


class UnknownCommand(AssertionError):
    """The CLI sent something this fake does not model."""


def php_json(obj: object) -> str:
    """What PHP's json_encode echoes: compact, `/` escaped, non-ASCII as \\uXXXX."""
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=True).replace("/", "\\/")


def php_lower(text: str) -> str:
    """PHP 8 strtolower: ASCII letters only, whatever the locale."""
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in text)


def _literals(body: str) -> list[str]:
    """Every PHP single-quoted literal in a body, unescaped (the inverse of pfsense.php_str)."""
    return [re.sub(r"\\(.)", r"\1", raw) for raw in _LITERAL_RX.findall(body)]


@dataclass
class FirewallState:
    """The parts of a pfSense config and runtime the CLI reads or writes.

    Plain dicts on purpose: they model PHP arrays, keys may be missing exactly as in a real
    config.xml, and the PHP's `?? ""` fallbacks are applied when the fake answers.
    """

    version: str = "2.8.0-RELEASE"
    dhcp_backend: str = "isc"
    unbound: bool = True
    dnsmasq: bool = False
    regdhcpstatic: bool = False
    interfaces: list = field(default_factory=list)      # {name, if, descr, ipaddr, subnet}
    packages: list = field(default_factory=list)        # {name, version}
    dhcpd: dict = field(default_factory=dict)           # if -> {enable, range, pool, staticmap}
    hosts: list = field(default_factory=list)           # {host, domain, ip, descr}
    arp_text: str = ""
    resolv_conf: str = "nameserver 127.0.0.1\n"
    locks: list = field(default_factory=list)
    tables: dict = field(default_factory=dict)          # name -> [address]
    rules: str = "pass in quick on lo0 all\nblock drop in log all\n"
    snort_running: bool = True
    supp: str = ""
    passlist: str = ""
    alerts: str = ""
    clock: str = "2026-11-20T10:00:00"
    unbound_answers: bool = True
    restart_rc: int = 0
    writes: int = 0

    def to_json(self) -> dict:
        return {k: deepcopy(v) for k, v in self.__dict__.items()}


class FakeFirewall:
    """Stands in for pfsense._run. `module` is the pfsense module whose builders it recognises."""

    def __init__(self, state: FirewallState, module) -> None:
        self.state = state
        self.module = module
        self.calls: list[dict] = []

    # ---- the seam ----
    def __call__(self, argv, *, stdin_text=None, timeout=30):
        self.calls.append({"argv": list(argv), "stdin": stdin_text})
        if argv and Path(argv[0]).name in ("git", "git.exe"):
            return 128, "", "fatal: not a git repository (or any of the parent directories): .git\n"
        command = argv[-1]
        if command == "php":
            return 0, self._php(stdin_text or ""), ""
        return self._shell(command)

    # ---- php ----
    def _php(self, script: str) -> str:
        if not script.startswith(PRELUDE):
            raise UnknownCommand(f"php script without the prelude: {script[:80]!r}")
        body = script[len(PRELUDE):]
        m = self.module
        reads = {m.php_info(): self._info, m.php_list_reservations(): self._reservations,
                 m.php_list_pools(): self._pools, m.php_list_overrides(): self._overrides}
        if body in reads:
            return php_json(reads[body]())
        lits = _literals(body)
        reason = next((lit for lit in lits if lit.startswith("pfsense.py: ")), "")
        candidates = [
            ("pfsense.py: remove DHCP reservation", lambda: (m.php_rm_reservation(lits[0]), self._rm_res, (lits[0],))),
            ("pfsense.py: clear static ARP", lambda: (m.php_rm_static_arp(lits[0]), self._rm_arp, (lits[0],))),
            ("pfsense.py: add DHCP reservation", lambda: (
                m.php_add_reservation(lits[0], lits[1], lits[2], lits[5], lits[6]), self._add_res,
                (lits[0], lits[1], lits[2], lits[5], lits[6]))),
            ("pfsense.py: rename DHCP reservation", lambda: (
                m.php_rename_reservation(lits[0], lits[1]), self._rename, (lits[0], lits[1]))),
            ("pfsense.py: add host override", lambda: (
                m.php_add_override(lits[0], lits[1], lits[4], lits[5]), self._add_ovr,
                (lits[0], lits[1], lits[4], lits[5]))),
            ("pfsense.py: remove host override", lambda: (
                m.php_rm_override(lits[0], lits[1]), self._rm_ovr, (lits[0], lits[1]))),
        ]
        for prefix, build in candidates:
            if reason.startswith(prefix):
                expected, handler, params = build()
                if expected != body:
                    raise UnknownCommand(f"a {prefix!r} body that its builder does not produce")
                return php_json(handler(*params))
        raise UnknownCommand(f"unrecognised php body: {body[:120]!r}")

    def _info(self) -> dict:
        s = self.state
        resolver = "unbound" if s.unbound else ("dnsmasq" if s.dnsmasq else "none")
        return {
            "version": s.version.strip(), "dhcp_backend": s.dhcp_backend, "resolver": resolver,
            "interfaces": [{"name": i["name"], "if": i.get("if", ""), "descr": i.get("descr", ""),
                            "ipaddr": i.get("ipaddr", ""), "subnet": i.get("subnet", "")}
                           for i in s.interfaces],
            "packages": [{"name": p.get("name", ""), "version": p.get("version", "")} for p in s.packages],
        }

    def _reservations(self) -> list:
        return [{"interface": iface, "mac": php_lower(sm.get("mac", "")), "ip": sm.get("ipaddr", ""),
                 "hostname": sm.get("hostname", ""), "descr": sm.get("descr", ""),
                 "static_arp": bool(sm.get("arp"))}
                for iface, conf in self.state.dhcpd.items() for sm in conf.get("staticmap", [])]

    def _pools(self) -> list:
        out = []
        for iface, conf in self.state.dhcpd.items():
            if not conf.get("enable"):
                continue
            for rng in [conf.get("range") or {}, *(p or {} for p in conf.get("pool", []))]:
                low, high = rng.get("from", ""), rng.get("to", "")
                if low != "" and high != "":
                    out.append({"interface": iface, "from": low, "to": high})
        return out

    def _overrides(self) -> list:
        return [{"host": h.get("host", ""), "domain": h.get("domain", ""), "ip": h.get("ip", ""),
                 "descr": h.get("descr", "")} for h in self.state.hosts]

    def _unbound_follows(self) -> bool:
        return self.state.unbound and self.state.regdhcpstatic

    def _write(self) -> None:
        self.state.writes += 1

    def _rm_res(self, target: str) -> dict:
        removed, plan = [], {}
        for iface, conf in self.state.dhcpd.items():
            maps = conf.get("staticmap", [])
            kept = [sm for sm in maps if php_lower(sm.get("mac", "")) != target]
            removed += [{"interface": iface, "ip": sm.get("ipaddr", "")}
                        for sm in maps if php_lower(sm.get("mac", "")) == target]
            if len(kept) != len(maps):
                plan[iface] = kept
        follows = False
        if len(removed) == 1:
            for iface, kept in plan.items():
                self.state.dhcpd[iface]["staticmap"] = kept
            self._write()
            follows = self._unbound_follows()
        else:
            removed = []
        return {"removed": removed, "unbound_follows": follows}

    def _rm_arp(self, target: str) -> dict:
        changed = []
        for iface, conf in self.state.dhcpd.items():
            for sm in conf.get("staticmap", []):
                if php_lower(sm.get("mac", "")) == target and sm.get("arp"):
                    sm["arp"] = False
                    changed.append({"interface": iface, "ip": sm.get("ipaddr", "")})
        if changed:
            self._write()
        return {"changed": changed}

    def _add_res(self, iface: str, mac: str, ip: str, hostname: str, descr: str) -> dict:
        if iface not in self.state.dhcpd:
            return {"added": None, "error": "interface " + iface + " has no DHCP server"}
        for conf in self.state.dhcpd.values():
            for sm in conf.get("staticmap", []):
                if php_lower(sm.get("mac", "")) == mac:
                    return {"added": None, "error": "a reservation for that MAC already exists"}
                if sm.get("ipaddr", "") == ip:
                    return {"added": None, "error": "that address is already reserved"}
        self.state.dhcpd[iface].setdefault("staticmap", []).append(
            {"mac": mac, "ipaddr": ip, "hostname": hostname, "descr": descr})
        self._write()
        return {"added": {"interface": iface, "mac": mac, "ip": ip, "hostname": hostname},
                "unbound_follows": self._unbound_follows()}

    def _rename(self, mac: str, hostname: str) -> dict:
        renamed, touched = [], []
        for iface, conf in self.state.dhcpd.items():
            for sm in conf.get("staticmap", []):
                if php_lower(sm.get("mac", "")) == mac:
                    renamed.append({"interface": iface, "ip": sm.get("ipaddr", "")})
                    touched.append(sm)
        follows = False
        if len(renamed) == 1:
            touched[0]["hostname"] = hostname
            self._write()
            follows = self._unbound_follows()
        else:
            renamed = []
        return {"renamed": renamed, "unbound_follows": follows}

    def _add_ovr(self, host: str, domain: str, ip: str, descr: str) -> dict:
        for h in self.state.hosts:
            if php_lower(h.get("host", "")) == host and php_lower(h.get("domain", "")) == domain:
                return {"added": None, "error": "an override for that name already exists"}
        self.state.hosts.append({"host": host, "domain": domain, "ip": ip, "descr": descr})
        self._write()
        return {"added": {"host": host, "domain": domain, "ip": ip}}

    def _rm_ovr(self, host: str, domain: str) -> dict:
        kept, removed = [], []
        for h in self.state.hosts:
            if php_lower(h.get("host", "")) == host and php_lower(h.get("domain", "")) == domain:
                removed.append({"host": h.get("host", ""), "domain": h.get("domain", ""), "ip": h.get("ip", "")})
            else:
                kept.append(h)
        if removed:
            self.state.hosts = kept
            self._write()
        return {"removed": removed}

    # ---- everything that is not php ----
    def _shell(self, command: str):
        s = self.state
        fixed = {
            "cat /conf/config.xml": lambda: (0, render_config_xml(s), ""),
            "cat /etc/resolv.conf": lambda: (0, s.resolv_conf, ""),
            "arp -an": lambda: (0, s.arp_text, ""),
            RESTART: lambda: (s.restart_rc, "", "unbound failed to start\n" if s.restart_rc else ""),
            "pfctl -sT": lambda: (0, "".join(f"{name}\n" for name in s.tables), ""),
            "pfctl -sr": lambda: (0, s.rules, ""),
            "pfctl -sn": lambda: (0, "nat on igb0 inet from 192.0.2.0/24 to any -> (igb0) round-robin\n", ""),
            "pfctl -vvsr": lambda: (0, "@0 " + s.rules.replace("\n", "\n  [ Evaluations: 1 ]\n@1 ", 1), ""),
            "ps auxww": lambda: (0, self._ps(), ""),
            f"cat {SNORT_INSTANCE}/supp* 2>/dev/null": lambda: (0, s.supp, ""),
            f"cat {SNORT_INSTANCE}/*Whitelist* 2>/dev/null": lambda: (0, s.passlist, ""),
        }
        if command in fixed:
            return fixed[command]()
        if command.startswith("date '+PFSENSE_CLOCK"):
            return 0, f"PFSENSE_CLOCK {s.clock}\n{s.alerts}", ""
        for rx, handler in ((_HOST_RX, self._host), (_TEST_F_RX, self._test_f),
                            (_PFCTL_SHOW_RX, self._table_show), (_PFCTL_DEL_RX, self._table_del)):
            match = rx.match(command)
            if match:
                return handler(*(shlex.split(g)[0] for g in match.groups()))
        raise UnknownCommand(f"unknown remote command: {command!r}")

    def _ps(self) -> str:
        base = "root  1 0.0 0.1 1 1 - Ss 10:00 0:00.01 /sbin/init\n"
        if not self.state.snort_running:
            return base
        return base + (f"root 4242 1.0 9.0 1 1 - Ss 10:00 1:00.00 /usr/local/bin/snort -R 12345 -D -q "
                       f"-l /var/log/snort/snort_igb1 -c {SNORT_INSTANCE}/snort.conf -i igb1\n")

    def _host(self, name: str):
        if not self.state.unbound_answers:
            return 1, ";; connection timed out; no servers could be reached\n", ""
        wanted = php_lower(name.rstrip("."))
        answers = ["127.0.0.1"] if wanted == "localhost" else []
        for h in self.state.hosts:
            host, domain = h.get("host", "").strip(), h.get("domain", "").strip()
            fqdn = f"{host}.{domain}" if host else domain
            if php_lower(fqdn) == wanted and h.get("ip"):
                answers.append(h["ip"])
        if not answers:
            return 1, f"Host {name} not found: 3(NXDOMAIN)\n", ""
        lines = []
        for ip in answers:
            try:
                kind = "IPv6 address" if ipaddress.ip_address(ip).version == 6 else "address"
            except ValueError:
                kind = "address"
            lines.append(f"{name} has {kind} {ip}")
        return 0, "Using domain server:\nName: 127.0.0.1\n\n" + "\n".join(lines) + "\n", ""

    def _test_f(self, path: str):
        return (0 if path in self.state.locks else 1), "", ""

    def _table_show(self, table: str):
        if table not in self.state.tables:
            return 1, "", "pfctl: Table does not exist.\n"
        return 0, "".join(f"   {ip}\n" for ip in self.state.tables[table]), ""

    def _table_del(self, table: str, ip: str):
        entries = self.state.tables.get(table, [])
        if ip in entries:
            entries.remove(ip)
            return 0, "", "1/1 addresses deleted.\n"
        return 0, "", "0/1 addresses deleted.\n"


def render_config_xml(state: FirewallState) -> str:
    """The config.xml the state stands for, as `cat /conf/config.xml` would print it."""
    root = ET.Element("pfsense")
    ET.SubElement(root, "version").text = "24.0"
    dhcpd = ET.SubElement(root, "dhcpd")
    for iface, conf in state.dhcpd.items():
        node = ET.SubElement(dhcpd, iface)
        if conf.get("enable"):
            ET.SubElement(node, "enable")
        for tag, rng in [("range", conf.get("range")), *(("pool", p) for p in conf.get("pool", []))]:
            if rng is None:
                continue
            holder = ET.SubElement(node, tag)
            target = holder if tag == "range" else ET.SubElement(holder, "range")
            for key in ("from", "to"):
                if key in rng:
                    ET.SubElement(target, key).text = rng[key]
        for sm in conf.get("staticmap", []):
            entry = ET.SubElement(node, "staticmap")
            for key in ("mac", "ipaddr", "hostname", "descr"):
                if key in sm:
                    ET.SubElement(entry, key).text = sm[key]
            if sm.get("arp"):
                ET.SubElement(entry, "arp_table_static_entry")
    unbound = ET.SubElement(root, "unbound")
    if state.unbound:
        ET.SubElement(unbound, "enable")
    if state.regdhcpstatic:
        ET.SubElement(unbound, "regdhcpstatic")
    for h in state.hosts:
        entry = ET.SubElement(unbound, "hosts")
        for key in ("host", "domain", "ip", "descr"):
            if key in h:
                ET.SubElement(entry, key).text = h[key]
    # No newline anywhere: a snapshot is written in text mode, and a Windows CRLF would change
    # the byte count the snapshot verb prints.
    return '<?xml version="1.0"?>' + ET.tostring(root, encoding="unicode")


# ---- states -------------------------------------------------------------------------------------
_BASE_INTERFACES = [
    {"name": "wan", "if": "igb0", "descr": "WAN", "ipaddr": "dhcp", "subnet": ""},
    {"name": "lan", "if": "igb1", "descr": "LAN", "ipaddr": "192.0.2.1", "subnet": "24"},
    {"name": "opt1", "if": "igb2", "descr": "IOT", "ipaddr": "198.51.100.1", "subnet": "24"},
    {"name": "opt2", "if": "igb3", "descr": "GUEST", "ipaddr": "203.0.113.1", "subnet": "24"},
]

_ALERTS = ('11/20-09:58:01.123456 ,1,2000,3,"ET POLICY something, with a comma",TCP,192.0.2.30,'
           '51515,198.51.100.77,443,0,Unknown,0\n'
           '11/19-23:00:00.000001 ,125,9,1,"(ftp_telnet) bad command",TCP,192.0.2.31,2121,'
           '198.51.100.77,21,0,Unknown,0\n')


def rich_state() -> FirewallState:
    """A box with something of everything: a static-ARP entry on a shared address, a reservation
    inside its pool, a bare-host override, a MagicDNS resolv.conf and an upgrade lock."""
    return FirewallState(
        regdhcpstatic=True,
        interfaces=deepcopy(_BASE_INTERFACES),
        packages=[{"name": "snort", "version": "4.1.6"}, {"name": "Tailscale", "version": "0.1.4"}],
        dhcpd={
            "lan": {"enable": True, "range": {"from": "192.0.2.100", "to": "192.0.2.199"},
                    "pool": [{"from": "192.0.2.220", "to": "192.0.2.229"}],
                    "staticmap": [
                        {"mac": "00:11:22:33:44:30", "ipaddr": "192.0.2.30", "hostname": "speaker",
                         "descr": "", "arp": True},
                        {"mac": "00:11:22:33:44:31", "ipaddr": "192.0.2.31", "hostname": "nas", "descr": "NAS"},
                        {"mac": "00:11:22:33:44:32", "ipaddr": "192.0.2.30", "hostname": "",
                         "descr": "speaker wifi"},
                        {"mac": "00:11:22:33:44:33", "ipaddr": "192.0.2.150", "hostname": "inpool", "descr": ""},
                    ]},
            "opt1": {"enable": True, "range": {"from": "198.51.100.100", "to": "198.51.100.199"},
                     "staticmap": [{"mac": "00:11:22:33:55:01", "ipaddr": "198.51.100.10",
                                    "hostname": "cam", "descr": "Bob's cam", "arp": True}]},
            "opt2": {"range": {"from": "203.0.113.100", "to": "203.0.113.199"}, "staticmap": []},
        },
        hosts=[
            {"host": "nas", "domain": "example.com", "ip": "192.0.2.31", "descr": ""},
            {"host": "", "domain": "bare.example.com", "ip": "192.0.2.40", "descr": "bare"},
            {"host": "v6", "domain": "example.com", "ip": "2001:db8::31", "descr": ""},
        ],
        arp_text=("? (192.0.2.1) at 00:11:22:33:44:01 on igb1 permanent [ethernet]\n"
                  "? (192.0.2.30) at 00:11:22:33:44:30 on igb1 permanent [ethernet]\n"
                  "? (192.0.2.31) at 00:11:22:33:44:99 on igb1 expires in 800 seconds [ethernet]\n"
                  "? (192.0.2.99) at (incomplete) on igb1 expired [ethernet]\n"),
        resolv_conf="nameserver 100.100.100.100\nsearch tail.example.ts.net\n",
        locks=["/tmp/pfSense-upgrade.lock"],
        tables={"snort2c": ["198.51.100.77", "203.0.113.9"], "virusprot": []},
        supp="# comment naming 198.51.100.0/24\nsuppress gen_id 1, sig_id 2000, track by_dst, ip 198.51.100.0/24\n",
        passlist="192.0.2.0/24\n198.51.100.0/24\n",
        alerts=_ALERTS,
    )


def clean_state() -> FirewallState:
    """A healthy box: nothing for doctor to warn about, unbound not following DHCP names."""
    return FirewallState(
        interfaces=deepcopy(_BASE_INTERFACES[:2]),
        dhcpd={"lan": {"enable": True, "range": {"from": "192.0.2.100", "to": "192.0.2.199"},
                       "staticmap": [{"mac": "AA:BB:CC:00:00:01", "ipaddr": "192.0.2.10",
                                      "hostname": "printer", "descr": "office"}]}},
        hosts=[{"host": "printer", "domain": "example.com", "ip": "192.0.2.10", "descr": ""}],
        resolv_conf="nameserver 127.0.0.1\nnameserver 9.9.9.9\n",
        tables={"snort2c": []},
        snort_running=False,
    )


def empty_state() -> FirewallState:
    """No reservations, no overrides, no DHCP server, a dead resolver: every list is empty."""
    return FirewallState(unbound=False, dnsmasq=True, interfaces=[{"name": "lan"}],
                         resolv_conf="", tables={}, unbound_answers=False, restart_rc=1,
                         snort_running=False)


def mixed_state() -> FirewallState:
    """Case and padding everywhere a reader might normalise one and not the other: an uppercase
    MAC, a padded host and domain, a padded subnet, a mixed-case override selected first."""
    return FirewallState(
        regdhcpstatic=True,
        version=" 2.7.2-RELEASE \n",
        interfaces=[{"name": "lan", "if": "em0", "descr": " Lan ", "ipaddr": "192.0.2.1", "subnet": "24"},
                    {"name": "opt1", "if": "em1", "descr": "Pad", "ipaddr": "198.51.100.1", "subnet": " 24 "}],
        packages=[{"name": " Padded ", "version": " 1 "}],
        dhcpd={"lan": {"enable": True, "range": {"from": " 192.0.2.100", "to": "192.0.2.199 "},
                       "staticmap": [{"mac": "aa:bb:cc:dd:ee:02", "ipaddr": " 192.0.2.11 ",
                                      "hostname": "", "descr": "Only Descr"},
                                     {"mac": "AA:BB:CC:DD:EE:01", "ipaddr": "192.0.2.10",
                                      "hostname": " Spaced ", "descr": " d ", "arp": True}]}},
        hosts=[{"host": "Mixed", "domain": "Example.COM", "ip": "192.0.2.10", "descr": " D "},
               {"host": " pad ", "domain": " example.com ", "ip": " 192.0.2.11", "descr": ""},
               {"host": "", "domain": "Bare.Example.Org", "ip": "2001:DB8::10", "descr": ""}],
        arp_text="? (192.0.2.10) at aa:bb:cc:dd:ee:01 on em0 permanent [ethernet]\n",
        resolv_conf="  nameserver 127.0.0.1\nnameserver 100.100.100.100\n",
        tables={"snort2c": [" 198.51.100.77"]},
    )


_NAMES = [" pad ", "", "nas", "Bob's box", "a\\b", 'quo"te', chr(0x00FC) + "mlaut", chr(0x65E5) + chr(0x672C), "x" * 63,
          "emoji\U0001F600", "UPPER", "tab\there", "</descr>", "100%"]


def random_state(seed: int) -> FirewallState:
    """A seeded random box, adversarial strings and duplicate MACs and addresses included."""
    rng = random.Random(seed)
    nets = {"lan": "192.0.2", "opt1": "198.51.100"}
    macs = [f"0{rng.randint(0, 9)}:aa:bb:cc:dd:{n:02x}" for n in range(6)]
    dhcpd = {}
    for iface, net in nets.items():
        maps = []
        for _ in range(rng.randint(0, 6)):
            sm = {"mac": rng.choice(macs).upper() if rng.random() < 0.2 else rng.choice(macs),
                  "ipaddr": f"{net}.{rng.randint(2, 254)}", "hostname": rng.choice(_NAMES),
                  "descr": rng.choice(_NAMES), "arp": rng.random() < 0.3}
            if rng.random() < 0.1:
                del sm["hostname"]
            maps.append(sm)
        low = rng.randint(50, 150)
        dhcpd[iface] = {"enable": rng.random() < 0.8,
                        "range": {"from": f"{net}.{low}", "to": f"{net}.{low + rng.randint(0, 80)}"},
                        "pool": [{"from": f"{net}.230", "to": f"{net}.240"}] if rng.random() < 0.3 else [],
                        "staticmap": maps}
    hosts = []
    for _ in range(rng.randint(0, 5)):
        host = rng.choice(["", "www", "Mixed", "db", chr(0x00FC) + "ml"])
        hosts.append({"host": host, "domain": rng.choice(["example.com", "Example.COM", "bare.example.org"]),
                      "ip": rng.choice(["192.0.2.5", "2001:db8::5", "198.51.100.7"]),
                      "descr": rng.choice(_NAMES)})
    reserved = [(sm["ipaddr"], sm["mac"]) for conf in dhcpd.values() for sm in conf["staticmap"]]
    arp_lines = []
    for ip, mac in reserved[:4]:
        shown = mac if rng.random() < 0.7 else rng.choice(macs)
        tail = "permanent [ethernet]" if rng.random() < 0.3 else "expires in 600 seconds [ethernet]"
        arp_lines.append(f"? ({ip}) at {shown.lower()} on igb1 {tail}")
    return FirewallState(
        regdhcpstatic=rng.random() < 0.5,
        interfaces=deepcopy(_BASE_INTERFACES[: rng.randint(2, 4)]),
        packages=[{"name": rng.choice(_NAMES), "version": "1.0"}] if rng.random() < 0.5 else [],
        dhcpd=dhcpd, hosts=hosts, arp_text="\n".join(arp_lines) + "\n",
        resolv_conf=rng.choice(["nameserver 127.0.0.1\n", "nameserver 8.8.8.8\nnameserver 127.0.0.1\n",
                                "nameserver ::1\n", "nameserver 100.100.100.100\n"]),
        locks=rng.sample(["/var/run/pfSense-upgrade.lock", "/tmp/pfSense-upgrade.lock"], rng.randint(0, 2)),
        tables={"snort2c": rng.sample(["198.51.100.77", "203.0.113.9", "192.0.2.200"], rng.randint(0, 3))},
        supp=rng.choice(["", "suppress gen_id 1, sig_id 2000\n"]), passlist="198.51.100.0/24\n",
        alerts=_ALERTS, unbound_answers=rng.random() < 0.8, restart_rc=0 if rng.random() < 0.9 else 1,
    )


STATES = {"rich": rich_state, "clean": clean_state, "empty": empty_state, "mixed": mixed_state,
          **{f"random{seed}": (lambda seed=seed: random_state(seed)) for seed in (1, 2, 3)}}


# ---- scenarios ----------------------------------------------------------------------------------
def scenario_argvs(state: FirewallState, config_path: str) -> dict[str, list[str]]:
    """Every verb, read and write, dry run and --apply, against entities this state holds."""
    maps = [(iface, sm) for iface, conf in state.dhcpd.items() for sm in conf.get("staticmap", [])]
    first_mac = maps[0][1].get("mac", "00:00:00:00:00:00") if maps else "00:00:00:00:00:00"
    armed = next((sm["mac"] for _, sm in maps if sm.get("arp")), first_mac)
    unarmed = next((sm["mac"] for _, sm in maps if not sm.get("arp")), first_mac)
    names = [(f"{h['host']}.{h['domain']}" if h.get("host") else h.get("domain", "")) for h in state.hosts]
    first_name = names[0] if names else "nothing.example.com"
    bare = next((n for h, n in zip(state.hosts, names) if not h.get("host")), first_name)
    mut = ["--apply"]
    return {
        "info": ["info"],
        "dhcp-list": ["dhcp", "list"],
        "dns-list": ["dns", "list"],
        "doctor": ["doctor"],
        "doctor-config": ["doctor", "--config", config_path],
        "arp": ["arp"],
        "arp-permanent": ["arp", "--permanent"],
        "snapshot": ["snapshot"],
        "dhcp-add-dry": ["dhcp", "add", "--mac", "00:11:22:33:44:5A", "--ip", "192.0.2.50", "--hostname", "printer"],
        "dhcp-add-apply": [*mut, "dhcp", "add", "--mac", "00-11-22-33-44-AB", "--ip", "192.0.2.50",
                           "--hostname", "printer", "--descr", "Bob's \"new\" printer"],
        "dhcp-add-taken": [*mut, "dhcp", "add", "--mac", first_mac, "--ip", "192.0.2.51", "--hostname", "dup"],
        "dhcp-add-named-iface": [*mut, "dhcp", "add", "--mac", "00:11:22:33:44:52", "--ip", "198.51.100.52",
                                 "--hostname", "iot", "--interface", "opt1"],
        "dhcp-add-no-server": [*mut, "dhcp", "add", "--mac", "00:11:22:33:44:53", "--ip", "203.0.113.53",
                               "--hostname", "guest"],
        "dhcp-add-bad-name": ["dhcp", "add", "--mac", "00:11:22:33:44:54", "--ip", "192.0.2.54", "--hostname", "a_b"],
        "dhcp-rename-dry": ["dhcp", "rename", "--mac", first_mac, "--hostname", "renamed"],
        "dhcp-rename-apply": [*mut, "dhcp", "rename", "--mac", first_mac, "--hostname", "renamed"],
        "dhcp-rename-unknown": [*mut, "dhcp", "rename", "--mac", "de:ad:be:ef:00:00", "--hostname", "x"],
        "dhcp-rm-dry": ["dhcp", "rm", "--mac", first_mac],
        "dhcp-rm-apply": [*mut, "dhcp", "rm", "--mac", first_mac],
        "dhcp-rm-unknown": [*mut, "dhcp", "rm", "--mac", "de:ad:be:ef:00:00"],
        "dhcp-rm-static-arp-dry": ["dhcp", "rm-static-arp", "--mac", armed],
        "dhcp-rm-static-arp-apply": [*mut, "dhcp", "rm-static-arp", "--mac", armed],
        "dhcp-rm-static-arp-unset": [*mut, "dhcp", "rm-static-arp", "--mac", unarmed],
        "dns-add-dry": ["dns", "add", "--name", "New.Example.com", "--ip", "192.0.2.41"],
        "dns-add-apply": [*mut, "dns", "add", "--name", "new.example.com", "--ip", "192.0.2.41",
                          "--descr", "it's new"],
        "dns-add-v6": [*mut, "dns", "add", "--name", "six.example.com", "--ip", "2001:DB8::6"],
        "dns-add-existing": [*mut, "dns", "add", "--name", first_name, "--ip", "192.0.2.42"],
        "dns-add-not-fqdn": ["dns", "add", "--name", "single", "--ip", "192.0.2.42"],
        "dns-rm-dry": ["dns", "rm", "--name", first_name],
        "dns-rm-apply": [*mut, "dns", "rm", "--name", first_name],
        "dns-rm-bare": [*mut, "dns", "rm", "--name", bare],
        "dns-rm-unknown": [*mut, "dns", "rm", "--name", "nothing.example.net"],
        "table-list": ["table", "list"],
        "table-show": ["table", "show", "snort2c"],
        "table-test": ["table", "test", "snort2c", "198.51.100.77", "192.0.2.9"],
        "table-del": [*mut, "table", "del", "snort2c", "198.51.100.77"],
        "rules": ["rules"],
        "rules-nat": ["rules", "--nat"],
        "rules-counters": ["rules", "--counters"],
        "snort-check": ["snort", "check", "198.51.100.77", "192.0.2.9"],
        "snort-why": ["snort", "why", "198.51.100.77", "192.0.2.250"],
        "snort-unblock": [*mut, "snort", "unblock", "198.51.100.77"],
        "snort-verify": ["snort", "verify", "--sid", "1:2000", "--cidr", "198.51.100.0/24", "--ip", "198.51.100.77"],
        "snort-fixsteps": ["snort", "fixsteps", "--sid", "2000", "--cidr", "198.51.100.0/24"],
    }


@dataclass(frozen=True)
class Outcome:
    rc: object
    stdout: str
    stderr: str
    calls: tuple
    state: str

    def digest(self) -> str:
        blob = json.dumps([self.rc, self.stdout, self.stderr, list(self.calls), self.state])
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _normalise(text: str, root: Path) -> str:
    """Scratch paths and snapshot timestamps differ per run and per OS; nothing else may.

    Each scratch path is replaced in its plain and its JSON-escaped spelling (a Windows path in a
    --json envelope doubles every backslash), and the separator after it is made `/`.
    """
    for path, token in ((root / "snaps", "<SNAPS>"), (root, "<CASE>"), (root.parent, "<MATRIX>")):
        for form in (str(path), json.dumps(str(path))[1:-1]):
            text = text.replace(form, token)
    text = re.sub(r"(<SNAPS>|<CASE>|<MATRIX>)(?:\\\\|\\|/)", r"\1/", text)
    return re.sub(r"-\d{14}\.xml", "-<STAMP>.xml", text)


def run_one(module, state: FirewallState, argv: list[str], root: Path, *, json_mode: bool) -> Outcome:
    """One CLI run against a fresh fake, with everything machine-dependent normalised away."""
    fake = FakeFirewall(state, module)
    full = ["--host", "192.0.2.1", "--user", "admin", "--ssh", "ssh -i /opt/key",
            "--snapshot-dir", str(root / "snaps"), *(["--json"] if json_mode else []), *argv]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            rc: object = module.main(full, run=fake)
        except SystemExit as exc:                # argparse usage errors
            rc = f"SystemExit {exc.code}"
        except UnknownCommand:
            raise
        except Exception as exc:                 # a crash is an outcome too, compared like the rest
            rc = f"{type(exc).__name__}: {exc}"
    # git calls are left out: whether they happen depends on git being installed, not on the CLI.
    calls = tuple(_normalise(json.dumps(c["argv"]), root) + (
        " <stdin sha256 " + hashlib.sha256(c["stdin"].encode()).hexdigest()[:16] + ">" if c["stdin"] else "")
        for c in fake.calls if Path(c["argv"][0]).name not in ("git", "git.exe"))
    return Outcome(rc=rc, stdout=_normalise(out.getvalue(), root),
                   stderr=_normalise(err.getvalue(), root), calls=calls,
                   state=json.dumps(fake.state.to_json(), sort_keys=True))


def run_matrix(module, root: Path, states: dict | None = None):
    """Yield (scenario id, Outcome) for every state x verb x output mode."""
    root.mkdir(parents=True, exist_ok=True)
    for state_name, factory in (states or STATES).items():
        config_path = root / f"{state_name}-config.xml"
        config_path.write_text(render_config_xml(factory()), encoding="utf-8")
        for verb, argv in scenario_argvs(factory(), str(config_path)).items():
            for json_mode in (False, True):
                case_root = root / "case"
                if case_root.exists():
                    shutil.rmtree(case_root)
                case_root.mkdir()
                outcome = run_one(module, factory(), argv, case_root, json_mode=json_mode)
                yield f"{state_name}/{verb}/{'json' if json_mode else 'human'}", outcome


def load_module(path: Path, name: str, source: str | None = None):
    """Import a pfsense.py from `path`, or from `source` text standing at that path."""
    text = source if source is not None else path.read_text(encoding="utf-8")
    module = types.ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(text, str(path), "exec"), module.__dict__)  # noqa: S102 - our own script under test
    return module
