# /// script
# requires-python = ">=3.14"
# ///
"""Drive a pfSense firewall from the command line instead of hand-rolling PHP over SSH.

Why this exists: pfSense has no usable CLI for its own configuration, so every change becomes a
throwaway `ssh fw 'php -r "..."'` that fights four quoting layers. Doing that repeatedly re-derives
the same four traps, each of which has silently produced a wrong answer:

  * `ssh ... 2>&1 | grep -v ...` is self-inflicted damage. The ssh client's post-quantum warning
    ("connection is not using a post-quantum key exchange algorithm") goes to STDERR and never
    touches a parser that keeps the streams apart. Merging them first and filtering afterwards is
    how that banner ends up spliced into parsed data. This tool never merges.
  * The DNS host overrides are at config path `unbound/hosts`, NOT `unbound/hostoverride`. The GUI
    label says "Host Overrides", so the wrong path is the natural guess - and it returns an empty
    list rather than an error, which reads as "there are none".
  * An empty XML tag means ENABLED. `<enable></enable>` comes back as "", so
    `if (config_get_path("unbound/enable"))` is FALSE for a running resolver. Test against null.
  * A DHCP reservation with "ARP Table Static Entry" ticked installs one permanent ARP entry for
    that address. On a device with more than one interface the firewall then answers for whichever
    interface is down: everything inside the subnet still works, everything beyond it fails, and
    nothing logs an error. `doctor` looks for exactly this.

Access is supplied by the caller, never discovered here - this ships publicly, so it carries no
key policy and no host names:

    pfsense.py --host 192.0.2.1 --user admin --ssh "ssh -i /path/key" info
    pfsense.py --fw home dhcp list                  # named target from ~/.config/bitranox/pfsense.ini

Mutating verbs are dry-run until `--apply`. The six that edit config.xml (`dhcp add`,
`dhcp rename`, `dhcp rm`, `dhcp rm-static-arp`, `dns add`, `dns rm`) snapshot it first. `table del` and `snort unblock`
change LIVE pf state, which a config.xml snapshot neither captures nor restores, so they take
none - re-add the entry to undo them:

    pfsense.py --fw home dns add --name nas.example.com --ip 192.0.2.10 --apply
    pfsense.py --fw home dhcp rm --mac 00:11:22:33:44:55 --apply
    pfsense.py --fw home dhcp add --mac 00:11:22:33:44:56 --ip 192.0.2.56 --hostname printer --apply
    pfsense.py --fw home dhcp rename --mac 00:11:22:33:44:56 --hostname office-printer --apply

Audit a box, or a snapshot file with no network at all:

    pfsense.py --fw home doctor
    pfsense.py doctor --config configs/config-20260809.xml

Add `--json` for a machine-readable envelope {ok, command, data, skipped}, emitted on failure
too; `ok` means the command ran without error, so it is true on exit 0 and exit 1.
Exit codes: 0 = yes/clean, 1 = well-formed no/findings, 2 = error.
A removal that removed nothing is a failed action, exit 2: `dhcp rm`, `dhcp rm-static-arp` or
`dns rm` whose entry matched but whose write changed nothing, and a `table del` or
`snort unblock` that leaves every requested address present (one address asked for included).
Only some of several addresses left present is a partial outcome, exit 1, naming them.
`dns add` and `dns rm` with --apply restart unbound after the write and resolve a name through
127.0.0.1; when it does not answer they exit 2 saying the change was written. `dhcp add`,
`dhcp rename` and `dhcp rm` with --apply do the same (reconfigure, restart, resolve `localhost.`)
when the resolver registers DHCP static mappings, so a reservation's hostname follows the change.
"""

import argparse
import configparser
import csv
import io
import ipaddress
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol, cast
from urllib.parse import urlparse

_DTD_RE = re.compile(r"<!DOCTYPE|<!ENTITY", re.IGNORECASE)
_DIGITS_RE = re.compile(r"[0-9]+")
_NON_HEX_RE = re.compile(r"[^0-9a-fA-F]")
_NAMESERVER_RE = re.compile(r"^[^\S\n]*nameserver\s+(\S+)", re.MULTILINE)
_TRACK_RE = re.compile(r"\btrack\s+([^,\s]+)")
_TRACK_IP_RE = re.compile(r"\bip\s+(\[[^\]]*\]|[^,\s]+)")

SNORT_TABLE = "snort2c"
MAGICDNS = "100.100.100.100"          # Tailscale's fixed MagicDNS address, the same on every tailnet
# Both paths are tested and the one found is named: the lock has been observed at /tmp on a real
# box, there is no pfSense source here to say which path the current release uses, and testing
# only one reports "no lock" while the GUI shows "Another instance".
UPGRADE_LOCKS = ("/var/run/pfSense-upgrade.lock", "/tmp/pfSense-upgrade.lock")

# The pfSense way to restart unbound: a playback script exits normally, while interactive pfSsh.php
# fed on stdin does not exit on EOF and hangs. SKILL.md tells the reader to run this exact command,
# and a test holds the two together.
UNBOUND_RESTART = "pfSsh.php playback svc restart unbound"

# `host <name> 127.0.0.1` prints one line per record: "<name> has address <ip>" or
# "<name> has IPv6 address <ip>". Only those lines count as an answer; the "Name: 127.0.0.1"
# header it prints for an explicit server would otherwise read as one.
_HOST_ANSWER_RX = re.compile(r"\bhas (?:IPv6 )?address (\S+)")

# `snort -c <path>/snort.conf -i <if>`: the conf path is the only reliable pointer to the
# instance dir, because a previous interface assignment leaves a same-uuid dir behind.
_SNORT_CONF_RX = re.compile(r"\bsnort\b[^\n]*?-c\s+(\S+snort\.conf)")

# Field positions in a snort CSV alert line: timestamp, GID, SID, rev, message, proto, src, sport,
# dst, dport, ... The GID is read because a SID alone names a rule only under generator 1: a
# preprocessor alert (GID 125, SID 9) and the text rule 1:9 are different rules.
_A_TS, _A_GID, _A_SID, _A_MSG, _A_SRC, _A_DST = 0, 1, 2, 4, 6, 8
_A_MIN_FIELDS = 10

# `--sid` takes `GID:SID` or a bare SID. ASCII digits only: str.isdigit() and int() also accept
# other scripts' digits, which would then be printed into a suppress line Snort cannot parse.
_SID_SPEC_RX = re.compile(r"(?:([0-9]+):)?([0-9]+)")

# `? (192.0.2.10) at 00:11:22:33:44:55 on igb1 expires in 1200 seconds [ethernet]`
_ARP_RX = re.compile(r"\((?P<ip>[0-9.]+)\)\s+at\s+(?P<mac>[0-9a-fA-F:]+|\(incomplete\))\s+on\s+(?P<iface>\S+)(?P<rest>.*)")

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
Network = ipaddress.IPv4Network | ipaddress.IPv6Network


class PfsenseError(Exception):
    """A typed failure, so callers get a message rather than a traceback."""


def parse_xml(text: str) -> ET.Element:
    """Parse a config.xml, refusing a document type declaration first.

    defusedxml would be the usual answer, but a skill script may import nothing outside the stdlib.
    ElementTree on 3.10+ already declines to fetch external entities; what it does NOT stop is an
    internal DTD defining nested entities (the billion-laughs expansion). A config.xml has no
    legitimate DOCTYPE, so refusing one closes that without a dependency and without weakening the
    parse of anything real.
    """
    if _DTD_RE.search(text):
        raise PfsenseError("the document declares a DOCTYPE or ENTITY; a pfSense config.xml has "
                           "neither, so this is refused rather than expanded")
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise PfsenseError(f"not parseable as XML: {exc}") from exc


def php_str(value: str) -> str:
    """Quote a Python value as a PHP single-quoted string literal.

    Interpolating a value straight into generated PHP is the same mistake as string-building SQL:
    a quote or a backslash in a description ends the literal and the rest is parsed as code. PHP
    single-quoted strings give exactly two escapes to handle, which is why they are used here.
    """
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


@dataclass(frozen=True)
class Target:
    """Where to connect and how. The ssh prefix is the caller's, exactly like transfer.py."""

    host: str
    user: str = "admin"
    ssh: str = "ssh"
    timeout: int = 30


@dataclass(frozen=True)
class SignatureId:
    """A Snort rule identity: generator id plus signature id, as `--sid` was given.

    `gid_assumed` records that the caller gave a bare SID and generator 1 was filled in, so the
    output can say so instead of presenting a guess as the alert's own generator.
    """

    gid: int
    sid: int
    gid_assumed: bool = False

    @property
    def label(self) -> str:
        return f"{self.gid}:{self.sid}"


@dataclass(frozen=True)
class Alert:
    """One parsed snort alert line.

    `gid` and `sid` keep the digit strings of the log line, which is what `snort why --json`
    has always emitted; `signature` is the typed form the code compares and prints.
    """

    timestamp: str
    gid: str
    sid: str
    message: str
    src: str
    dst: str

    @property
    def signature(self) -> SignatureId:
        # parse_alerts admits a line only when both fields are ASCII digits, so int() holds.
        return SignatureId(gid=int(self.gid), sid=int(self.sid))


class Severity(StrEnum):
    """A `doctor` finding's weight. `warn` means act on it (doctor exits 1); `info` is context."""

    WARN = "warn"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    """One `doctor` result. `warn` means act on it; `info` is context."""

    check: str
    severity: Severity
    subject: str
    detail: str

    def __post_init__(self) -> None:
        # The exit code counts only WARN, so a misspelled severity would be filed as context and
        # doctor would exit 0 over it; parsing refuses it where the finding is built.
        object.__setattr__(self, "severity", Severity(self.severity))


# ---- typed replies from the box -----------------------------------------------------------------
# run_php decodes the JSON a PHP body echoes; the records below are what the rest of this module
# reads. Each reply is checked where it enters (every key present, every value of its type), so no
# reader meets a missing key or a list where text belongs, and a reader cannot misspell a key and
# silently read a default. `to_json` rebuilds the object the PHP echoed, keys in the same order,
# because that object is what --json prints.
def _preview(value: object) -> str:
    return json.dumps(value)[:200]


def _object(value: object, what: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PfsenseError(f"{what} is not a JSON object: {_preview(value)}")
    # json.loads gives every object str keys, and each field is then checked by its own reader.
    return cast("dict[str, object]", value)


def _array(value: object, what: str) -> list[object]:
    if not isinstance(value, list):
        raise PfsenseError(f"{what} is not a JSON array: {_preview(value)}")
    return cast("list[object]", value)


def _text(obj: dict[str, object], key: str, what: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str):
        raise PfsenseError(f"{what} has no text field {key!r}: {_preview(obj)}")
    return value


def _flag(obj: dict[str, object], key: str, what: str) -> bool:
    value = obj.get(key)
    if not isinstance(value, bool):
        raise PfsenseError(f"{what} has no true/false field {key!r}: {_preview(obj)}")
    return value


@dataclass(frozen=True)
class Reservation:
    """One DHCP static mapping: what `dhcp list` prints and every reservation check reads."""

    interface: str
    mac: str
    ip: str
    hostname: str
    descr: str
    static_arp: bool

    @classmethod
    def from_json(cls, value: object) -> Reservation:
        what = "a DHCP reservation"
        obj = _object(value, what)
        return cls(interface=_text(obj, "interface", what), mac=_text(obj, "mac", what),
                   ip=_text(obj, "ip", what), hostname=_text(obj, "hostname", what),
                   descr=_text(obj, "descr", what), static_arp=_flag(obj, "static_arp", what))

    @classmethod
    def list_from_json(cls, value: object) -> list[Reservation]:
        return [cls.from_json(item) for item in _array(value, "the DHCP reservation list")]

    def to_json(self) -> dict[str, object]:
        return {"interface": self.interface, "mac": self.mac, "ip": self.ip,
                "hostname": self.hostname, "descr": self.descr, "static_arp": self.static_arp}


@dataclass(frozen=True)
class Pool:
    """One dynamic DHCP range of an enabled server, `first` to `last` inclusive."""

    interface: str
    first: str
    last: str

    @classmethod
    def from_json(cls, value: object) -> Pool:
        what = "a DHCP pool"
        obj = _object(value, what)
        return cls(interface=_text(obj, "interface", what), first=_text(obj, "from", what),
                   last=_text(obj, "to", what))

    @classmethod
    def list_from_json(cls, value: object) -> list[Pool]:
        return [cls.from_json(item) for item in _array(value, "the DHCP pool list")]


@dataclass(frozen=True)
class Override:
    """One unbound host override, as `dns list` prints it."""

    host: str
    domain: str
    ip: str
    descr: str

    @property
    def fqdn(self) -> str:
        """The fully qualified name, tolerating an empty host part (the whole name in `domain`)."""
        host, domain = self.host.strip(), self.domain.strip()
        return f"{host}.{domain}" if host else domain

    @classmethod
    def from_json(cls, value: object) -> Override:
        what = "a host override"
        obj = _object(value, what)
        return cls(host=_text(obj, "host", what), domain=_text(obj, "domain", what),
                   ip=_text(obj, "ip", what), descr=_text(obj, "descr", what))

    @classmethod
    def list_from_json(cls, value: object) -> list[Override]:
        return [cls.from_json(item) for item in _array(value, "the host override list")]

    def to_json(self, *, with_fqdn: bool = False) -> dict[str, object]:
        """The object the PHP echoed; `with_fqdn` appends the name `dns rm` selected it by."""
        out: dict[str, object] = {"host": self.host, "domain": self.domain, "ip": self.ip,
                                  "descr": self.descr}
        if with_fqdn:
            out["fqdn"] = self.fqdn
        return out


@dataclass(frozen=True)
class Interface:
    """One assigned interface: pfSense name (lan, opt1), device (`if` on the wire), static address."""

    name: str
    device: str
    descr: str
    ipaddr: str
    subnet: str

    @classmethod
    def from_json(cls, value: object) -> Interface:
        what = "an interface"
        obj = _object(value, what)
        return cls(name=_text(obj, "name", what), device=_text(obj, "if", what),
                   descr=_text(obj, "descr", what), ipaddr=_text(obj, "ipaddr", what),
                   subnet=_text(obj, "subnet", what))

    def to_json(self) -> dict[str, object]:
        return {"name": self.name, "if": self.device, "descr": self.descr, "ipaddr": self.ipaddr,
                "subnet": self.subnet}


@dataclass(frozen=True)
class Package:
    """One installed pfSense package."""

    name: str
    version: str

    @classmethod
    def from_json(cls, value: object) -> Package:
        what = "a package"
        obj = _object(value, what)
        return cls(name=_text(obj, "name", what), version=_text(obj, "version", what))

    def to_json(self) -> dict[str, object]:
        return {"name": self.name, "version": self.version}


@dataclass(frozen=True)
class FirewallInfo:
    """The `info` reply: version, DHCP backend, resolver, interfaces and packages."""

    version: str
    dhcp_backend: str
    resolver: str
    interfaces: tuple[Interface, ...]
    packages: tuple[Package, ...]

    @classmethod
    def from_json(cls, value: object) -> FirewallInfo:
        what = "the firewall info"
        obj = _object(value, what)
        interfaces = _array(obj.get("interfaces"), "the firewall info's interface list")
        packages = _array(obj.get("packages"), "the firewall info's package list")
        return cls(version=_text(obj, "version", what), dhcp_backend=_text(obj, "dhcp_backend", what),
                   resolver=_text(obj, "resolver", what),
                   interfaces=tuple(Interface.from_json(item) for item in interfaces),
                   packages=tuple(Package.from_json(item) for item in packages))

    def to_json(self) -> dict[str, object]:
        return {"version": self.version, "dhcp_backend": self.dhcp_backend, "resolver": self.resolver,
                "interfaces": [i.to_json() for i in self.interfaces],
                "packages": [p.to_json() for p in self.packages]}


# ---- typed results of the PHP writes ------------------------------------------------------------
# One record per write, each holding exactly the keys its PHP echoes. `unbound` is the restart-and-
# resolve check this side adds after the write; it is appended to the --json object last, as the
# key the PHP never sends.
def _optional_text(obj: dict[str, object], key: str, what: str) -> str | None:
    if key not in obj:
        return None
    return _text(obj, key, what)


@dataclass(frozen=True)
class UnboundCheck:
    """unbound was restarted and resolved `resolved` to `ip` through 127.0.0.1."""

    restarted: bool
    resolved: str
    ip: str

    def to_json(self) -> dict[str, object]:
        return {"restarted": self.restarted, "resolved": self.resolved, "ip": self.ip}


def _with_unbound(out: dict[str, object], unbound: UnboundCheck | None) -> dict[str, object]:
    if unbound is not None:
        out["unbound"] = unbound.to_json()
    return out


@dataclass(frozen=True)
class TouchedReservation:
    """A reservation a write removed, renamed or cleared static ARP on: where it was, and its address."""

    interface: str
    ip: str

    @classmethod
    def list_from_json(cls, value: object, what: str) -> tuple[TouchedReservation, ...]:
        items: list[TouchedReservation] = []
        for item in _array(value, what):
            obj = _object(item, f"an entry of {what}")
            items.append(cls(interface=_text(obj, "interface", what), ip=_text(obj, "ip", what)))
        return tuple(items)

    def to_json(self) -> dict[str, object]:
        return {"interface": self.interface, "ip": self.ip}


@dataclass(frozen=True)
class ReservationRemoved:
    """The `dhcp rm` write: what it removed (empty unless exactly one entry matched)."""

    removed: tuple[TouchedReservation, ...]
    unbound_follows: bool
    unbound: UnboundCheck | None = None

    @classmethod
    def from_json(cls, value: object) -> ReservationRemoved:
        what = "the reservation removal"
        obj = _object(value, what)
        return cls(removed=TouchedReservation.list_from_json(obj.get("removed"), "its removed list"),
                   unbound_follows=_flag(obj, "unbound_follows", what))

    def to_json(self) -> dict[str, object]:
        return _with_unbound({"removed": [r.to_json() for r in self.removed],
                              "unbound_follows": self.unbound_follows}, self.unbound)


@dataclass(frozen=True)
class ReservationRenamed:
    """The `dhcp rename` write: what it renamed (empty unless exactly one entry matched)."""

    renamed: tuple[TouchedReservation, ...]
    unbound_follows: bool
    unbound: UnboundCheck | None = None

    @classmethod
    def from_json(cls, value: object) -> ReservationRenamed:
        what = "the reservation rename"
        obj = _object(value, what)
        return cls(renamed=TouchedReservation.list_from_json(obj.get("renamed"), "its renamed list"),
                   unbound_follows=_flag(obj, "unbound_follows", what))

    def to_json(self) -> dict[str, object]:
        return _with_unbound({"renamed": [r.to_json() for r in self.renamed],
                              "unbound_follows": self.unbound_follows}, self.unbound)


@dataclass(frozen=True)
class StaticArpCleared:
    """The `dhcp rm-static-arp` write: the reservations whose static-ARP flag it cleared."""

    changed: tuple[TouchedReservation, ...]

    @classmethod
    def from_json(cls, value: object) -> StaticArpCleared:
        obj = _object(value, "the static ARP change")
        return cls(changed=TouchedReservation.list_from_json(obj.get("changed"), "its changed list"))

    def to_json(self) -> dict[str, object]:
        return {"changed": [r.to_json() for r in self.changed]}


@dataclass(frozen=True)
class NewReservation:
    """A reservation `dhcp add` writes, or would write on a dry run."""

    interface: str
    mac: str
    ip: str
    hostname: str

    @classmethod
    def from_json(cls, value: object) -> NewReservation:
        what = "the added reservation"
        obj = _object(value, what)
        return cls(interface=_text(obj, "interface", what), mac=_text(obj, "mac", what),
                   ip=_text(obj, "ip", what), hostname=_text(obj, "hostname", what))

    def to_json(self) -> dict[str, object]:
        return {"interface": self.interface, "mac": self.mac, "ip": self.ip, "hostname": self.hostname}


@dataclass(frozen=True)
class ReservationAdded:
    """The `dhcp add` write: the reservation added, or (added None) the refusal the PHP gave."""

    added: NewReservation | None
    error: str | None
    unbound_follows: bool
    unbound: UnboundCheck | None = None

    @classmethod
    def from_json(cls, value: object) -> ReservationAdded:
        what = "the reservation add"
        obj = _object(value, what)
        if obj.get("added") is None:
            return cls(added=None, error=_text(obj, "error", what), unbound_follows=False)
        return cls(added=NewReservation.from_json(obj["added"]), error=None,
                   unbound_follows=_flag(obj, "unbound_follows", what))

    def to_json(self) -> dict[str, object]:
        if self.added is None:
            return _with_unbound({"added": None, "error": self.error}, self.unbound)
        return _with_unbound({"added": self.added.to_json(), "unbound_follows": self.unbound_follows},
                             self.unbound)


@dataclass(frozen=True)
class NameAndAddress:
    """A host override as the `dns add` and `dns rm` writes echo it: no description."""

    host: str
    domain: str
    ip: str

    @classmethod
    def from_json(cls, value: object, what: str) -> NameAndAddress:
        obj = _object(value, what)
        return cls(host=_text(obj, "host", what), domain=_text(obj, "domain", what),
                   ip=_text(obj, "ip", what))

    def to_json(self) -> dict[str, object]:
        return {"host": self.host, "domain": self.domain, "ip": self.ip}


@dataclass(frozen=True)
class OverrideAdded:
    """The `dns add` write: the override added, or (added None) the refusal the PHP gave."""

    added: NameAndAddress | None
    error: str | None
    unbound: UnboundCheck | None = None

    @classmethod
    def from_json(cls, value: object) -> OverrideAdded:
        what = "the override add"
        obj = _object(value, what)
        if obj.get("added") is None:
            return cls(added=None, error=_text(obj, "error", what))
        return cls(added=NameAndAddress.from_json(obj["added"], "the added override"),
                   error=_optional_text(obj, "error", what))

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {"added": None if self.added is None else self.added.to_json()}
        if self.error is not None:
            out["error"] = self.error
        return _with_unbound(out, self.unbound)


@dataclass(frozen=True)
class OverrideRemoved:
    """The `dns rm` write: the overrides it removed."""

    removed: tuple[NameAndAddress, ...]
    unbound: UnboundCheck | None = None

    @classmethod
    def from_json(cls, value: object) -> OverrideRemoved:
        obj = _object(value, "the override removal")
        what = "its removed list"
        return cls(removed=tuple(NameAndAddress.from_json(item, f"an entry of {what}")
                                 for item in _array(obj.get("removed"), what)))

    def to_json(self) -> dict[str, object]:
        return _with_unbound({"removed": [r.to_json() for r in self.removed]}, self.unbound)


# ---- typed results built on this side -----------------------------------------------------------
# What a verb reads from shell output (arp, pfctl, the snort files) and answers with. Code reads
# these through attributes, so a misspelled key is a type error instead of a silent default, and
# `to_json` rebuilds the object --json has always printed, keys in the same order.
@dataclass(frozen=True)
class ArpEntry:
    """One `arp -an` line. `mac` is empty for an incomplete entry; `permanent` marks a static one."""

    ip: str
    mac: str
    interface: str
    permanent: bool

    def to_json(self) -> dict[str, object]:
        return {"ip": self.ip, "mac": self.mac, "interface": self.interface, "permanent": self.permanent}


@dataclass(frozen=True)
class SnapshotSaved:
    """The `snapshot` answer: where config.xml was saved, and its size."""

    path: str
    size: int

    def to_json(self) -> dict[str, object]:
        return {"path": self.path, "bytes": self.size}


@dataclass(frozen=True)
class TableCheck:
    """The `table test` answer: which of the asked addresses the table holds."""

    table: str
    present: tuple[str, ...]
    absent: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {"table": self.table, "present": list(self.present), "absent": list(self.absent)}


@dataclass(frozen=True)
class TableDeletion:
    """The `table del --apply` answer: what was asked for, and what a re-read still found."""

    requested: tuple[str, ...]
    still_present: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {"requested": list(self.requested), "still_present": list(self.still_present)}


@dataclass(frozen=True)
class BlockCheck:
    """The `snort check` answer: each target's addresses, and which of them snort2c holds.

    `resolved` keeps the targets in the order given, each named once.
    """

    resolved: tuple[tuple[str, tuple[str, ...]], ...]
    blocked: tuple[str, ...]
    clear: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {"resolved": {name: list(ips) for name, ips in self.resolved},
                "blocked": list(self.blocked), "clear": list(self.clear)}


@dataclass(frozen=True)
class Unblocked:
    """The `snort unblock --apply` answer: what was asked for, and what a re-read still found."""

    requested: tuple[str, ...]
    still_blocked: tuple[str, ...]

    def to_json(self) -> dict[str, object]:
        return {"requested": list(self.requested), "still_blocked": list(self.still_blocked)}


@dataclass(frozen=True)
class FixSteps:
    """The `snort fixsteps` answer: the rule it is for, the range, and the steps text."""

    sig: SignatureId
    cidr: str | None
    steps: str

    def to_json(self) -> dict[str, object]:
        return {"gid": self.sig.gid, "sid": self.sig.sid, "gid_assumed": self.sig.gid_assumed,
                "cidr": self.cidr, "steps": self.steps}


# ---- target resolution --------------------------------------------------------------------------
def config_file() -> Path:
    """The named-target ini, read from the environment when asked rather than at import."""
    return Path(os.environ.get("PFSENSE_JIG_CONFIG", "~/.config/bitranox/pfsense.ini")).expanduser()


def load_named_target(name: str, *, path: Path | None = None) -> Target:
    """Resolve `--fw <name>` from the user's own ini file.

    Named targets live in the USER's config, never in this repo: the tool ships publicly and must
    carry no host names. An ini file rather than toml so this works on 3.10, where tomllib is absent.

    A value is read in whichever `%` dialect it is written in. An ssh prefix legitimately carries
    raw `%` tokens (ControlPath=~/.ssh/cm-%r@%h:%p), which ConfigParser's default interpolation
    rejects with a traceback, so such a value is taken as written. A value that IS valid under
    that interpolation - every `%` doubled as `%%` or a `%(key)s` reference - is read through it,
    because it was written for it: taken raw, `%%r` reached ssh as a literal percent and the
    ControlPath silently named a different socket.
    """
    path = path or config_file()
    if not path.exists():
        raise PfsenseError(f"no target file at {path}; use --host, or create a [{name}] section there")
    parser = configparser.ConfigParser()
    try:
        parser.read(path, encoding="utf-8-sig")
    except configparser.Error as exc:
        raise PfsenseError(f"cannot parse {path}: {exc}") from exc
    if name not in parser:
        known = ", ".join(s for s in parser.sections()) or "none"
        raise PfsenseError(f"no [{name}] section in {path} (defined: {known})")
    section = parser[name]
    host = _ini_value(section, "host", "").strip()
    if not host:
        raise PfsenseError(f"[{name}] in {path} has no host=")
    timeout = _ini_value(section, "timeout", "30").strip()
    try:
        timeout_seconds = int(timeout)
    except ValueError as exc:
        raise PfsenseError(f"[{name}] in {path} has timeout={timeout!r}, not a whole number") from exc
    return Target(
        host=host,
        user=_ini_value(section, "user", "admin").strip(),
        ssh=_ini_value(section, "ssh", "ssh").strip(),
        timeout=timeout_seconds,
    )


def _ini_value(section: configparser.SectionProxy, key: str, default: str) -> str:
    """One ini value, interpolated when it is valid interpolation syntax and raw otherwise."""
    if key not in section:
        return default
    try:
        return section.get(key, fallback=default)
    except configparser.InterpolationError:
        return section.get(key, raw=True, fallback=default)


def _split_windows(text: str) -> list[str]:
    """Split a command line the way the Microsoft C runtime (CommandLineToArgvW) does.

    A backslash is literal unless a run of them ends in a double quote: 2n backslashes then a quote
    give n backslashes and toggle quoting, 2n+1 give n backslashes and a literal quote. There is no
    single-quoting. Pure Python rather than ctypes so the same rules are testable on every OS.
    """
    args: list[str] = []
    current: list[str] = []
    in_quotes = in_arg = False
    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\":
            run_end = i
            while run_end < len(text) and text[run_end] == "\\":
                run_end += 1
            count = run_end - i
            if run_end < len(text) and text[run_end] == '"':
                current.append("\\" * (count // 2))
                if count % 2:
                    current.append('"')
                    run_end += 1
            else:
                current.append("\\" * count)
            in_arg, i = True, run_end
            continue
        if char == '"':
            in_quotes, in_arg = not in_quotes, True
        elif char in " \t" and not in_quotes:
            if in_arg:
                args.append("".join(current))
                current, in_arg = [], False
        else:
            current.append(char)
            in_arg = True
        i += 1
    if in_arg:
        args.append("".join(current))
    return args


def split_command(text: str, *, windows: bool = os.name == "nt") -> list[str]:
    """Split a caller-supplied command prefix by the rules of the platform it runs on.

    POSIX shlex reads a backslash as an escape, so on Windows it eats the separators out of a key
    path (`-i C:\\Users\\me\\.ssh\\id` becomes `-i C:Usersme.sshid`) and the login fails as an auth
    error far from the cause.
    """
    return _split_windows(text) if windows else shlex.split(text)


def build_ssh_argv(target: Target, command: str) -> list[str]:
    """The argv for one remote command.

    BatchMode is forced on when the caller did not set it: with only `-i <key>`, ssh falls back to
    a password PROMPT when the key is rejected, which hangs an unattended run instead of failing.
    """
    argv = split_command(target.ssh)
    if not any("BatchMode" in part for part in argv):
        argv += ["-o", "BatchMode=yes"]
    argv += [f"{target.user}@{target.host}", command]
    return argv


# ---- the one process seam -----------------------------------------------------------------------
class Runner(Protocol):
    """The shape of the process seam: `_run`, or a test double standing in for it."""

    def __call__(self, argv: list[str], *, stdin_text: str | None = ...,
                 timeout: int = ...) -> tuple[int, str, str]: ...


def _run(argv: list[str], *, stdin_text: str | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """Execute argv and return (rc, stdout, stderr), never merged.

    This is the single seam the tests inject past. capture_output keeps the streams apart on
    purpose: everything the ssh client says about host keys and key exchange is stderr, and merging
    it into stdout is what corrupts parsed output.
    """
    proc = subprocess.run(argv, input=stdin_text, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, check=False,
                          env=_child_env(argv))
    return proc.returncode, proc.stdout, proc.stderr


def _child_env(argv: list[str]) -> dict[str, str] | None:
    """The environment for a child: a git child loses every GIT_* variable.

    A GIT_DIR or GIT_INDEX_FILE inherited from a hook or a linked-worktree push would make the
    repository checks answer from another repository's index and excludes. Other children keep the
    caller's environment untouched (None).
    """
    if not argv or Path(argv[0]).name not in ("git", "git.exe"):
        return None
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def run_remote(target: Target, command: str, *, run: Runner = _run, stdin_text: str | None = None,
               timeout: int | None = None) -> tuple[int, str, str]:
    """One remote command. Returns (rc, stdout, stderr) with the streams still separate."""
    return run(build_ssh_argv(target, command), stdin_text=stdin_text, timeout=timeout or target.timeout)


def run_php[T](target: Target, php_body: str, *, parse: Callable[[object], T], run: Runner = _run,
                timeout: int | None = None) -> T:
    """Run PHP against the live config API and return its JSON reply as `parse` reads it.

    The source goes over STDIN, so no part of it is ever parsed by the local shell, the remote
    shell, or php's own -r argument handling. That is what removes the quoting layer that mangles
    a hand-rolled `php -r "..."` into plausible-but-wrong output.

    `parse` is required so that no call site can take the decoded JSON untyped: each one names the
    record its PHP body answers with (Reservation.list_from_json, ReservationRemoved.from_json,
    ...), and a reply of any other shape is refused here, naming the box. The reply of a write
    arrives after write_config() may already have run, so that refusal says so: a reader who
    retries a change that did land would otherwise make it twice.
    """
    decoded = _run_php_json(target, php_body, run=run, timeout=timeout)
    try:
        return parse(decoded)
    except PfsenseError as exc:
        landed = ("; the change may already be written to config.xml, so check it before running "
                  "this again" if "write_config(" in php_body else "")
        raise PfsenseError(f"php on {target.host} returned an unexpected reply: {exc}{landed}") from None


def _run_php_json(target: Target, php_body: str, *, run: Runner, timeout: int | None) -> object:
    script = '<?php\nrequire_once("config.inc");\nrequire_once("util.inc");\n' + php_body
    rc, out, err = run_remote(target, "php", run=run, stdin_text=script, timeout=timeout)
    if rc != 0:
        raise PfsenseError(f"php on {target.host} exited {rc}: {(err or out).strip()[:400]}")
    text = out.strip()
    if not text:
        raise PfsenseError(f"php on {target.host} returned nothing (stderr: {err.strip()[:200]})")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise PfsenseError(f"php on {target.host} did not return JSON: {text[:300]}") from exc


# ---- pure parsers -------------------------------------------------------------------------------
def parse_table(text: str) -> set[str]:
    """The IPs in a `pfctl -t <table> -T show` dump (it indents every entry).

    Split on newline only: str.splitlines also breaks on form feed and U+2028, which would turn
    one garbled line into a phantom entry. Every remote listing here is split the same way.
    """
    return {line.strip() for line in text.split("\n") if line.strip()}


def blocked_among(table_text: str, ips: Sequence[str]) -> list[str]:
    """Which of `ips` the table currently contains, in the order given."""
    present = parse_table(table_text)
    return [ip for ip in ips if ip in present]


def parse_alerts(text: str, ip: str | None = None) -> list[Alert]:
    """Parse snort CSV alert lines, optionally keeping only those touching `ip`.

    Uses the csv module rather than str.split: the message field is quoted and contains commas,
    so splitting shifts every later field and silently reads the wrong IP.
    """
    alerts: list[Alert] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < _A_MIN_FIELDS or not _is_ascii_number(row[_A_GID]) or not _is_ascii_number(row[_A_SID]):
            continue
        alert = Alert(
            timestamp=row[_A_TS].strip(),
            gid=row[_A_GID].strip(),
            sid=row[_A_SID].strip(),
            message=row[_A_MSG].strip(),
            src=row[_A_SRC].strip(),
            dst=row[_A_DST].strip(),
        )
        if ip is None or ip in (alert.src, alert.dst):
            alerts.append(alert)
    return alerts


def _is_ascii_number(field: str) -> bool:
    return _DIGITS_RE.fullmatch(field.strip()) is not None


def parse_sid_spec(text: str) -> SignatureId:
    """`GID:SID` or a bare SID, as `--sid` takes it. A bare SID means generator 1.

    Generator 1 is Snort's own default for a SID given alone (the text rules), and it is what a
    bare `--sid` always meant here, so a bare SID keeps working - but the result says the
    generator was assumed, because for a preprocessor alert it is the wrong rule.

    Raises:
        ValueError: anything but ASCII digits, optionally `digits:` in front.
    """
    match = _SID_SPEC_RX.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"--sid must be GID:SID (e.g. 125:9) or a bare SID, not {text!r}")
    gid, sid = match.groups()
    if gid is None:
        return SignatureId(gid=1, sid=int(sid), gid_assumed=True)
    return SignatureId(gid=int(gid), sid=int(sid))


_ALERT_STAMP_RX = re.compile(
    r"^(\d{2})/(\d{2})(?:/(\d{2}))?-(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?$"
)


def alert_moment(timestamp: str, *, now: datetime) -> datetime | None:
    """When a snort alert stamp happened, or None when it is not a snort stamp.

    Snort writes `MM/DD-HH:MM:SS.ffffff`, with no year unless it runs with `-y`
    (`MM/DD/YY-...`). A year it wrote is read. A missing one is inferred the way syslog readers
    do: the most recent year that does not put the stamp after `now`, because an alert cannot
    come from the future. Compared as text, a December alert outranked every January alert
    written after it.
    """
    match = _ALERT_STAMP_RX.match(timestamp.strip())
    if match is None:
        return None
    month, day, year, hour, minute, second, fraction = match.groups()
    parts = (int(month), int(day), int(hour), int(minute), int(second),
             int((fraction or "0").ljust(6, "0")))
    try:
        if year is not None:
            return datetime(2000 + int(year), *parts)
        moment = _in_year(now.year, parts)
        if moment is not None and moment <= now:
            return moment
        return _in_year(now.year - 1, parts)
    except ValueError:
        return None  # 13/40, or a 02/29 in a year without one


def _in_year(year: int, parts: tuple[int, int, int, int, int, int]) -> datetime | None:
    try:
        return datetime(year, *parts)
    except ValueError:
        return None  # 02/29 in a non-leap year: the other candidate year decides


def latest_alert(alerts: list[Alert], *, now: datetime) -> Alert:
    """The most recent alert. A stamp that cannot be read ranks below every readable one."""
    def key(alert: Alert) -> tuple[int, datetime]:
        moment = alert_moment(alert.timestamp, now=now)
        return (0, datetime.min) if moment is None else (1, moment)

    return max(alerts, key=key)


def instance_dir_from_ps(ps_text: str) -> str | None:
    """The LIVE Snort instance dir, taken from the running process argv.

    Never glob for it: a stale snort_<uuid>_<oldif> dir from a previous interface assignment sits
    beside the live one and sorts FIRST, so a glob inspects a file nothing has written for a year
    and reports a correct change as missing.
    """
    match = _SNORT_CONF_RX.search(ps_text)
    return os.path.dirname(match.group(1)) if match else None


def normalize_target(target: str) -> str:
    """A bare host from a URL, a host, or an IP."""
    text = target.strip()
    if "://" in text:
        return urlparse(text).hostname or text
    return text.split("/", 1)[0]


def resolve_ips(target: str) -> list[str]:
    """Every IPv4 a target resolves to, or the target itself when it already is an IP."""
    host = normalize_target(target)
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return [host]
    infos = socket.getaddrinfo(host, None, socket.AF_INET)
    # An AF_INET sockaddr is (address, port): the address is always text, never the int the
    # IPv6 tuple's later fields are typed as.
    return sorted({str(info[4][0]) for info in infos})


def normalize_mac(mac: str) -> str:
    """Lowercase colon-separated form, so `00-11-22-33-44-55` and `00:11:22:33:44:55` match."""
    cleaned = _NON_HEX_RE.sub("", mac).lower()
    if len(cleaned) != 12:
        raise PfsenseError(f"not a MAC address: {mac}")
    return ":".join(cleaned[i:i + 2] for i in range(0, 12, 2))


def parse_arp(text: str) -> list[ArpEntry]:
    """Parse `arp -an`, marking permanent entries.

    A permanent entry is the fingerprint of a DHCP reservation with static ARP ticked, which is
    the fault that answers for a device on an interface that is down.
    """
    entries: list[ArpEntry] = []
    for line in text.split("\n"):
        match = _ARP_RX.search(line)
        if not match:
            continue
        mac = match.group("mac")
        entries.append(ArpEntry(
            ip=match.group("ip"),
            mac="" if mac.startswith("(") else normalize_mac(mac),
            interface=match.group("iface"),
            permanent="permanent" in match.group("rest"),
        ))
    return entries


def select_one[T](items: Sequence[T], value: str, *, key: Callable[[T], str], field: str,
                  what: str) -> T:
    """The single item whose `key` equals `value`, ignoring case; refuse on no match AND on
    ambiguity. `field` names the key in the refusal.

    Selection is by stable text, never by position: an index taken from a listing shifts the moment
    anything before it is removed, so a second command from the same listing hits the wrong row and
    still exits 0.
    """
    hits = [item for item in items if key(item).lower() == value.lower()]
    if not hits:
        raise PfsenseError(f"no {what} with {field}={value}")
    if len(hits) > 1:
        raise PfsenseError(f"{len(hits)} {what} entries share {field}={value}; refusing to guess which")
    return hits[0]


def select_reservation(reservations: Sequence[Reservation], mac: str) -> Reservation:
    """The one reservation for `mac` (normalised), refusing none and several."""
    return select_one(reservations, mac, key=lambda r: r.mac, field="mac", what="reservation")


def _is_loopback(address: str) -> str | bool:
    """Whether a nameserver entry points back at this host, in either address family."""
    return address.startswith("127.") or address in ("::1", "0:0:0:0:0:0:0:1")


# ---- offline config parsing ---------------------------------------------------------------------
def reservations_from_config_xml(text: str) -> list[Reservation]:
    """DHCP reservations read straight out of a config.xml snapshot.

    Offline parsing exists so `doctor` can audit a saved snapshot with no network, and so its
    checks can be proven able to FAIL against a config known to contain the fault.
    """
    root = parse_xml(text)
    out: list[Reservation] = []
    for dhcpd in root.findall("dhcpd"):
        for iface in dhcpd:
            for entry in iface.findall("staticmap"):
                out.append(Reservation(
                    interface=iface.tag,
                    mac=(entry.findtext("mac") or "").strip().lower(),
                    ip=(entry.findtext("ipaddr") or "").strip(),
                    hostname=(entry.findtext("hostname") or "").strip(),
                    descr=(entry.findtext("descr") or "").strip(),
                    static_arp=entry.find("arp_table_static_entry") is not None,
                ))
    return out


def pools_from_config_xml(text: str) -> list[Pool]:
    """The dynamic ranges of every ENABLED DHCP server in a snapshot: the main range plus each
    additional pool, as {interface, from, to}.

    A server without `<enable>` hands out nothing, so its range is no pool, and reporting a
    reservation inside it would be noise. Additional pools sit at `dhcpd/<if>/pool[]/range` with
    the same `from`/`to` shape as the main range.
    """
    root = parse_xml(text)
    out: list[Pool] = []
    for dhcpd in root.findall("dhcpd"):
        for iface in dhcpd:
            if iface.find("enable") is None:
                continue
            ranges = [iface.find("range"), *(pool.find("range") for pool in iface.findall("pool"))]
            for rng in ranges:
                if rng is None:
                    continue
                low, high = (rng.findtext("from") or "").strip(), (rng.findtext("to") or "").strip()
                if low and high:
                    out.append(Pool(interface=iface.tag, first=low, last=high))
    return out


# ---- doctor: pure checks over plain data --------------------------------------------------------
def _pool_holding(address: IPAddress, interface: str, pools: Sequence[Pool]) -> Pool | None:
    """The first pool on `interface` whose inclusive first-last range holds `address`."""
    for pool in pools:
        if pool.interface != interface:
            continue
        try:
            low, high = ipaddress.ip_address(pool.first), ipaddress.ip_address(pool.last)
        except ValueError:
            continue
        if _within(address, low, high):
            return pool
    return None


def _within(address: IPAddress, low: IPAddress, high: IPAddress) -> bool:
    """`low <= address <= high`, and False unless all three are one address family.

    Comparing addresses of two families raises TypeError, so a pool written with an IPv4 start and
    an IPv6 end crashed doctor for every reservation of the start's family; it holds nothing.
    """
    if (isinstance(address, ipaddress.IPv4Address) and isinstance(low, ipaddress.IPv4Address)
            and isinstance(high, ipaddress.IPv4Address)):
        return low <= address <= high
    if (isinstance(address, ipaddress.IPv6Address) and isinstance(low, ipaddress.IPv6Address)
            and isinstance(high, ipaddress.IPv6Address)):
        return low <= address <= high
    return False


def _reservations_in_pools(reservations: Sequence[Reservation], pools: Sequence[Pool]) -> list[Finding]:
    """A reservation whose address lies in its own interface's dynamic pool.

    A pool widened after the reservation was made produces one, as can a reservation written by a
    script that bypasses the GUI's checks. A pool on another interface is never a conflict: each
    DHCP server leases only its own range.
    """
    findings: list[Finding] = []
    for res in reservations:
        try:
            address = ipaddress.ip_address(res.ip)
        except ValueError:
            continue
        pool = _pool_holding(address, res.interface, pools)
        if pool is None:
            continue
        name = res.hostname or res.descr or "(no hostname)"
        findings.append(Finding(
            check="static_map_in_dynamic_pool", severity=Severity.WARN,
            subject=f"{res.ip} {res.mac} {name} on {res.interface}, "
                    f"inside the pool {pool.first}-{pool.last}",
            detail="ISC dhcpd, pfSense's default DHCP backend, does not keep a reserved address out "
                   "of its dynamic pool: it can lease this address to another client, and its "
                   "pre-lease ping check misses a host that does not answer ping (Windows by "
                   "default), so two machines end up on one address. The only trace is dhcpd "
                   "logging 'Dynamic and static leases present' for it. Move the reservation "
                   "outside the pool, or shrink the pool so it no longer covers the address.",
        ))
    return findings


def doctor_findings(*, reservations: Sequence[Reservation],
                    arp: Sequence[ArpEntry] | None = None, resolv_conf: str | None = None,
                    upgrade_locks: list[str] | None = None,
                    pools: Sequence[Pool] | None = None) -> list[Finding]:
    """Every audit check, as pure logic over plain data.

    Each one is a fault that raises no error of its own and so goes unnoticed: they were all found
    the expensive way, by chasing a symptom that pointed somewhere else entirely.

    Host overrides are not an input: an override naming an address no reservation holds is a
    statically configured server, which is normal, so no check reads them and doctor does not
    fetch them.
    """
    findings: list[Finding] = []

    # One address reserved for several MACs is the NORMAL way to give a wired/wireless device a
    # single identity, so it is context, not a fault. It matters only because it is the precondition
    # for the static-ARP fault below: reporting it as a problem on its own cries wolf on a healthy
    # config (measured: 5 warnings on a config with nothing wrong with it).
    by_ip: dict[str, list[Reservation]] = {}
    for res in reservations:
        if res.ip:
            by_ip.setdefault(res.ip, []).append(res)

    for res in reservations:
        if res.static_arp:
            shared = len(by_ip.get(res.ip, []))
            extra = (f" This address is reserved for {shared} MACs, which is exactly the case that "
                     f"breaks: the firewall pins one of them permanently." if shared > 1 else "")
            findings.append(Finding(
                check="static_arp_armed", severity=Severity.WARN,
                subject=f"{res.ip} {res.mac} {res.hostname or res.descr or ''}".strip(),
                detail="ARP Table Static Entry is ticked. On a device with more than one interface "
                       "the firewall answers for whichever one is down: reachable inside its subnet, "
                       "dead beyond it, and nothing logs an error." + extra,
            ))

    for ip, group in sorted(by_ip.items()):
        if len(group) > 1:
            findings.append(Finding(
                check="shared_ip_multi_mac", severity=Severity.INFO, subject=ip,
                detail="reserved for " + str(len(group)) + " MACs (" +
                       ", ".join(r.mac for r in group) +
                       "). Normal for a device with wired and wireless interfaces; only a problem "
                       "if static ARP is also ticked.",
            ))

    findings.extend(_reservations_in_pools(reservations, pools or []))

    # ARP is used for POSITIVE evidence only: it is a cache that expires after minutes of silence,
    # so absence means "not seen lately", never "gone". An earlier version drew conclusions from
    # absence and reported 22 healthy hosts as possibly-gone on a network with nothing wrong with
    # it, which is the kind of noise that trains people to stop reading the output. The DHCP lease
    # file cannot rescue that check either: ISC dhcpd writes no lease for a fixed-address
    # reservation, so a reserved device leaves no trace there whether it is present or not.
    if arp is not None:
        macs_for_ip: dict[str, set[str]] = {}
        for res in reservations:
            if res.ip:
                macs_for_ip.setdefault(res.ip, set()).add(res.mac)
        for entry in arp:
            reserved_macs = macs_for_ip.get(entry.ip)
            if entry.mac and reserved_macs and entry.mac not in reserved_macs:
                findings.append(Finding(
                    check="reservation_mac_mismatch", severity=Severity.WARN,
                    subject=f"{entry.ip} reserved for {', '.join(sorted(reserved_macs))}, held by {entry.mac}",
                    detail="the address is in use by hardware no reservation for it names. If the "
                           "reserved device reappears, DHCP hands it an address something else "
                           "already holds, which shows up as an intermittent outage that is hard "
                           "to trace. Usually it means the reservation outlived the device.",
                ))

    # A healthy pfSense resolv.conf lists the box's own resolver FIRST and then the configured
    # upstream servers as fallbacks, so "every entry is loopback" is the wrong test - it flags a
    # correct box. The fault has two distinct signatures, checked separately.
    if resolv_conf is not None:
        servers = _NAMESERVER_RE.findall(resolv_conf)
        if MAGICDNS in servers:
            findings.append(Finding(
                check="magicdns_in_resolv_conf", severity=Severity.WARN, subject=MAGICDNS,
                detail="Tailscale's 'Accept DNS' has rewritten /etc/resolv.conf to MagicDNS. When "
                       "the tailnet has no global nameservers the box then resolves no public name "
                       "at all, so pkg and system upgrades fail while LAN clients stay fine because "
                       "they query the resolver directly - which is why this hides for months. Turn "
                       "Accept DNS off in the package config AND with `tailscale set "
                       "--accept-dns=false`. Do not forward the tailnet's domain to "
                       "100.100.100.100 instead: quad-100 is reported not to answer on "
                       "FreeBSD/pfSense, so that forward SERVFAILs. To resolve tailnet names, "
                       "forward the tailnet's domain to a resolver on a Linux tailnet node, where "
                       "quad-100 does answer (see bitranox:net-tailscale).",
            ))
        elif servers and not _is_loopback(servers[0]):
            findings.append(Finding(
                check="resolver_not_first", severity=Severity.WARN, subject=servers[0],
                detail="the first nameserver is not this firewall's own resolver, so the box does "
                       "not answer its own queries from unbound. Upstream servers listed AFTER "
                       "loopback are normal fallbacks and are not a fault.",
            ))

    if upgrade_locks:
        findings.append(Finding(
            check="upgrade_lock_present", severity=Severity.WARN, subject=", ".join(upgrade_locks),
            detail="a pfSense-upgrade lock is present, so every package operation reports "
                   "'Another instance of pfSense-upgrade is running'. Usually a background "
                   "pfSense-upgrade is hung on a repository the box cannot resolve: fix the box's "
                   "DNS first (see the resolv.conf findings). Remove the lock only once public "
                   "names resolve on the box and no pfSense-upgrade process is running.",
        ))

    return findings


# ---- PHP payload builders (pure; each returns the body run after the config.inc prelude) ---------
def php_info() -> str:
    """Read version, DHCP backend, resolver, interfaces and packages in one round trip."""
    return """
$resolver = "none";
if (config_get_path("unbound/enable") !== null) { $resolver = "unbound"; }
elseif (config_get_path("dnsmasq/enable") !== null) { $resolver = "dnsmasq"; }
$ifaces = array();
foreach (config_get_path("interfaces", array()) as $name => $conf) {
    $ifaces[] = array("name" => $name, "if" => $conf["if"] ?? "", "descr" => $conf["descr"] ?? "",
                      "ipaddr" => $conf["ipaddr"] ?? "", "subnet" => $conf["subnet"] ?? "");
}
$pkgs = array();
foreach (config_get_path("installedpackages/package", array()) as $p) {
    $pkgs[] = array("name" => $p["name"] ?? "", "version" => $p["version"] ?? "");
}
echo json_encode(array(
    "version" => trim(@file_get_contents("/etc/version")),
    "dhcp_backend" => config_get_path("dhcpbackend", "isc"),
    "resolver" => $resolver,
    "interfaces" => $ifaces,
    "packages" => $pkgs,
));
"""


def php_list_reservations() -> str:
    """Every DHCP reservation, with the static-ARP flag as a real boolean."""
    return """
$out = array();
foreach (config_get_path("dhcpd", array()) as $if => $conf) {
    foreach (($conf["staticmap"] ?? array()) as $m) {
        $out[] = array(
            "interface" => $if,
            "mac" => strtolower($m["mac"] ?? ""),
            "ip" => $m["ipaddr"] ?? "",
            "hostname" => $m["hostname"] ?? "",
            "descr" => $m["descr"] ?? "",
            "static_arp" => array_key_exists("arp_table_static_entry", $m),
        );
    }
}
echo json_encode($out);
"""


def php_list_pools() -> str:
    """The dynamic ranges of every enabled DHCP server, main range and additional pools alike.

    `enable` is tested by key: `<enable></enable>` reads back as "", so a truthiness test would
    skip every server that is on.
    """
    return """
$pools = array();
foreach (config_get_path("dhcpd", array()) as $if => $conf) {
    if (!is_array($conf) || !array_key_exists("enable", $conf)) { continue; }
    $ranges = array($conf["range"] ?? array());
    foreach (($conf["pool"] ?? array()) as $p) { $ranges[] = $p["range"] ?? array(); }
    foreach ($ranges as $r) {
        $from = $r["from"] ?? ""; $to = $r["to"] ?? "";
        if ($from !== "" && $to !== "") { $pools[] = array("interface" => $if, "from" => $from, "to" => $to); }
    }
}
echo json_encode($pools);
"""


def _php_unbound_follows_static_maps() -> str:
    """Rewrite unbound's static-mapping names when the resolver registers DHCP static mappings.

    With `unbound/regdhcpstatic` on, unbound answers each reservation's hostname from
    host_entries.conf, which only services_unbound_configure() rewrites: a reservation removed or
    added without it keeps answering with the old address. The flag is echoed so the caller can
    restart unbound and check it answers, since the reconfigure has been seen to leave it stopped.
    Both settings are empty tags when on, so they are tested against null.
    """
    return """
$unbound_follows = config_get_path("unbound/enable") !== null && config_get_path("unbound/regdhcpstatic") !== null;
if ($unbound_follows) {
    services_unbound_configure();
}
"""


def _php_reconfigure_dhcp() -> str:
    """Reload whichever DHCP daemon this box actually runs.

    2.8 can be switched from ISC dhcpd to Kea, which is a different service function. function_exists
    keeps this correct on both rather than assuming the backend that happens to be in front of us.
    """
    return """
if (config_get_path("dhcpbackend", "isc") == "kea" && function_exists("services_kea_configure")) {
    services_kea_configure();
} else {
    services_dhcpd_configure();
}
"""


def php_rm_reservation(mac: str) -> str:
    """Delete the reservation for one MAC by rebuilding the list without it.

    Rebuilding rather than unsetting an index: a positional delete shifts every later entry, so a
    second delete taken from the same listing removes the wrong row. The write happens only when
    exactly one entry matched, so an ambiguous MAC changes nothing.
    """
    target = php_str(mac)
    reason = php_str(f"pfsense.py: remove DHCP reservation for {mac}")
    return f"""
$target = {target};
$removed = array();
$plan = array();
$unbound_follows = false;
foreach (config_get_path("dhcpd", array()) as $if => $conf) {{
    $kept = array();
    foreach (($conf["staticmap"] ?? array()) as $m) {{
        if (strtolower($m["mac"] ?? "") === $target) {{ $removed[] = array("interface" => $if, "ip" => $m["ipaddr"] ?? ""); }}
        else {{ $kept[] = $m; }}
    }}
    if (count($kept) != count($conf["staticmap"] ?? array())) {{ $plan[$if] = $kept; }}
}}
if (count($removed) == 1) {{
    foreach ($plan as $if => $kept) {{ config_set_path("dhcpd/{{$if}}/staticmap", $kept); }}
    write_config({reason});
    {_php_reconfigure_dhcp()}
    {_php_unbound_follows_static_maps()}
}} else {{
    $removed = array();
}}
echo json_encode(array("removed" => $removed, "unbound_follows" => $unbound_follows));
"""


def php_rm_static_arp(mac: str) -> str:
    """Clear the static-ARP flag on one reservation, leaving the reservation itself alone."""
    target = php_str(mac)
    reason = php_str(f"pfsense.py: clear static ARP for {mac}")
    return f"""
$target = {target};
$changed = array();
foreach (config_get_path("dhcpd", array()) as $if => $conf) {{
    $maps = $conf["staticmap"] ?? array();
    $touched = false;
    foreach ($maps as $i => $m) {{
        if (strtolower($m["mac"] ?? "") === $target && array_key_exists("arp_table_static_entry", $m)) {{
            unset($maps[$i]["arp_table_static_entry"]);
            $changed[] = array("interface" => $if, "ip" => $m["ipaddr"] ?? "");
            $touched = true;
        }}
    }}
    if ($touched) {{ config_set_path("dhcpd/{{$if}}/staticmap", array_values($maps)); }}
}}
if (count($changed) > 0) {{
    write_config({reason});
    {_php_reconfigure_dhcp()}
}}
echo json_encode(array("changed" => $changed));
"""


def php_add_reservation(interface: str, mac: str, ip: str, hostname: str, descr: str) -> str:
    """Append one DHCP reservation to an interface's DHCP server.

    Refuses, writing nothing, when that interface has no DHCP server or when the MAC or the
    address is already reserved anywhere: a second reservation for either is a conflict the
    daemon resolves silently in favour of whichever entry it reads first.
    """
    i, m, a, h, d = (php_str(v) for v in (interface, mac, ip, hostname, descr))
    reason = php_str(f"pfsense.py: add DHCP reservation {ip} for {mac}")
    return f"""
$added = null;
$if = {i};
if (config_get_path("dhcpd/{{$if}}") === null) {{
    echo json_encode(array("added" => null, "error" => "interface " . $if . " has no DHCP server"));
    exit;
}}
foreach (config_get_path("dhcpd", array()) as $other => $conf) {{
    foreach (($conf["staticmap"] ?? array()) as $sm) {{
        if (strtolower($sm["mac"] ?? "") === {m}) {{
            echo json_encode(array("added" => null, "error" => "a reservation for that MAC already exists"));
            exit;
        }}
        if (($sm["ipaddr"] ?? "") === {a}) {{
            echo json_encode(array("added" => null, "error" => "that address is already reserved"));
            exit;
        }}
    }}
}}
$maps = config_get_path("dhcpd/{{$if}}/staticmap", array());
$maps[] = array("mac" => {m}, "cid" => "", "ipaddr" => {a}, "hostname" => {h}, "descr" => {d});
config_set_path("dhcpd/{{$if}}/staticmap", $maps);
write_config({reason});
{_php_reconfigure_dhcp()}
{_php_unbound_follows_static_maps()}
$added = array("interface" => $if, "mac" => {m}, "ip" => {a}, "hostname" => {h});
echo json_encode(array("added" => $added, "unbound_follows" => $unbound_follows));
"""


def php_rename_reservation(mac: str, hostname: str) -> str:
    """Set the hostname of the one reservation for a MAC; write only when exactly one matched."""
    m, h = php_str(mac), php_str(hostname)
    reason = php_str(f"pfsense.py: rename DHCP reservation for {mac} to {hostname}")
    return f"""
$renamed = array();
$plan = array();
$unbound_follows = false;
foreach (config_get_path("dhcpd", array()) as $if => $conf) {{
    $maps = $conf["staticmap"] ?? array();
    $touched = false;
    foreach ($maps as $n => $sm) {{
        if (strtolower($sm["mac"] ?? "") === {m}) {{
            $maps[$n]["hostname"] = {h};
            $renamed[] = array("interface" => $if, "ip" => $sm["ipaddr"] ?? "");
            $touched = true;
        }}
    }}
    if ($touched) {{ $plan[$if] = $maps; }}
}}
if (count($renamed) == 1) {{
    foreach ($plan as $if => $maps) {{ config_set_path("dhcpd/{{$if}}/staticmap", $maps); }}
    write_config({reason});
    {_php_reconfigure_dhcp()}
    {_php_unbound_follows_static_maps()}
}} else {{
    $renamed = array();
}}
echo json_encode(array("renamed" => $renamed, "unbound_follows" => $unbound_follows));
"""


def php_list_overrides() -> str:
    """Host overrides. The path is unbound/hosts; unbound/hostoverride silently returns nothing."""
    return """
$out = array();
foreach (config_get_path("unbound/hosts", array()) as $h) {
    $out[] = array("host" => $h["host"] ?? "", "domain" => $h["domain"] ?? "",
                   "ip" => $h["ip"] ?? "", "descr" => $h["descr"] ?? "");
}
echo json_encode($out);
"""


def php_add_override(host: str, domain: str, ip: str, descr: str) -> str:
    """Append one host override, refusing a duplicate name rather than shadowing it."""
    h, d, i, s = php_str(host), php_str(domain), php_str(ip), php_str(descr)
    reason = php_str(f"pfsense.py: add host override {host}.{domain}")
    return f"""
$hosts = config_get_path("unbound/hosts", array());
foreach ($hosts as $h) {{
    if (strtolower($h["host"] ?? "") === {h} && strtolower($h["domain"] ?? "") === {d}) {{
        echo json_encode(array("added" => null, "error" => "an override for that name already exists"));
        exit;
    }}
}}
$hosts[] = array("host" => {h}, "domain" => {d}, "ip" => {i}, "descr" => {s}, "aliases" => "");
config_set_path("unbound/hosts", $hosts);
write_config({reason});
services_unbound_configure();
echo json_encode(array("added" => array("host" => {h}, "domain" => {d}, "ip" => {i})));
"""


def php_rm_override(host: str, domain: str) -> str:
    """Remove one host override by name, rebuilding the list rather than deleting by index."""
    h, d = php_str(host), php_str(domain)
    reason = php_str(f"pfsense.py: remove host override {host}.{domain}")
    return f"""
$hosts = config_get_path("unbound/hosts", array());
$kept = array(); $removed = array();
foreach ($hosts as $h) {{
    if (strtolower($h["host"] ?? "") === {h} && strtolower($h["domain"] ?? "") === {d}) {{
        $removed[] = array("host" => $h["host"] ?? "", "domain" => $h["domain"] ?? "", "ip" => $h["ip"] ?? "");
    }} else {{ $kept[] = $h; }}
}}
if (count($removed) > 0) {{
    config_set_path("unbound/hosts", $kept);
    write_config({reason});
    services_unbound_configure();
}}
echo json_encode(array("removed" => $removed));
"""


# ---- output -------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Envelope:
    """The machine-readable result envelope. `ok` means "ran without error": true for every
    answer a command gives (exit 0 or 1), false only on exit 2. The yes/no is the exit code's.

    `data` is already JSON-ready (a record's `to_json()`, a list, a string): the envelope does not
    know the verbs' records, it only frames them.
    """

    command: str
    data: object
    ok: bool
    skipped: Sequence[str] = ()

    def __post_init__(self) -> None:
        # Held as a tuple so a caller's list mutated afterwards cannot change what is printed.
        object.__setattr__(self, "skipped", tuple(self.skipped))

    def to_json(self) -> dict[str, object]:
        return {"ok": self.ok, "command": self.command, "data": self.data, "skipped": list(self.skipped)}


def _emit(result: Envelope, as_json: bool, human: str) -> None:
    """Data to stdout. Diagnostics never travel this path; they go to stderr."""
    print(json.dumps(result.to_json(), indent=2) if as_json else human)


# ---- the parsed command line --------------------------------------------------------------------
@dataclass(frozen=True)
class ParsedArgs:
    """Typed reads of what argparse parsed: the one place its untyped Namespace is touched.

    Each verb's options are read from here once, at the edge, into a frozen record, so no command
    function reads an attribute argparse may or may not have set. A value of the wrong type means
    the parser and its reader disagree, a defect in this file, so it raises TypeError rather than a
    PfsenseError a caller would read as an answer about the firewall.
    """

    namespace: argparse.Namespace

    def _value(self, name: str) -> object:
        value: object = getattr(self.namespace, name, None)
        return value

    def _refuse(self, name: str, wanted: str, value: object, *, item: bool = False) -> TypeError:
        subject = f"an item of the parsed option {name}" if item else f"the parsed option {name}"
        return TypeError(f"{subject} is {type(value).__name__}, not {wanted}")

    def text(self, name: str) -> str:
        value = self._value(name)
        if not isinstance(value, str):
            raise self._refuse(name, "str", value)
        return value

    def optional_text(self, name: str) -> str | None:
        value = self._value(name)
        if value is not None and not isinstance(value, str):
            raise self._refuse(name, "str or None", value)
        return value

    def flag(self, name: str) -> bool:
        value = self._value(name)
        if not isinstance(value, bool):
            raise self._refuse(name, "bool", value)
        return value

    def number(self, name: str) -> int:
        value = self._value(name)
        if not isinstance(value, int) or isinstance(value, bool):
            raise self._refuse(name, "int", value)
        return value

    def texts(self, name: str) -> tuple[str, ...]:
        """A list option (nargs or action="append"); an append option never given is None: ()."""
        value = self._value(name)
        if value is None:
            return ()
        if not isinstance(value, list):
            raise self._refuse(name, "list", value)
        items = tuple(cast(list[object], value))
        texts = tuple(item for item in items if isinstance(item, str))
        if len(texts) != len(items):
            bad = next(item for item in items if not isinstance(item, str))
            raise self._refuse(name, "str", bad, item=True)
        return texts

    def command(self) -> str:
        """The verb as the envelope names it: `info`, `dhcp add`, `table del`."""
        return " ".join(part for part in [self.text("cmd"), self.optional_text("action")] if part)

    def handler(self) -> Handler:
        value = self._value("verb")
        if not isinstance(value, Handler):
            raise self._refuse("verb", "Handler", value)
        return value


@dataclass(frozen=True)
class CommonOptions:
    """The options every verb accepts before its subcommand, and the process seam it runs through.

    The mutation flags are here, not on the mutating verbs' records, because the top-level parser
    accepts them for every verb (`--apply dns add ...`) and `snapshot` reads the snapshot ones too.
    `run` is not an option: main() injects it, and every remote read of every verb goes through it.
    """

    host: str | None
    fw: str | None
    user: str
    ssh: str
    timeout: int
    json: bool
    apply: bool
    snapshot_dir: str | None
    allow_repo_snapshot: bool
    run: Runner

    @classmethod
    def read(cls, parsed: ParsedArgs, run: Runner) -> CommonOptions:
        return cls(host=parsed.optional_text("host"), fw=parsed.optional_text("fw"),
                   user=parsed.text("user"), ssh=parsed.text("ssh"), timeout=parsed.number("timeout"),
                   json=parsed.flag("json"), apply=parsed.flag("apply"),
                   snapshot_dir=parsed.optional_text("snapshot_dir"),
                   allow_repo_snapshot=parsed.flag("allow_repo_snapshot"), run=run)


@dataclass(frozen=True)
class NoArgs:
    """A verb with no options of its own (`info`, `dhcp list`, `dns list`)."""

    @classmethod
    def read(cls, parsed: ParsedArgs) -> NoArgs:
        del parsed
        return cls()


@dataclass(frozen=True)
class SnapshotArgs:
    dir: str | None

    @classmethod
    def read(cls, parsed: ParsedArgs) -> SnapshotArgs:
        return cls(dir=parsed.optional_text("dir"))


@dataclass(frozen=True)
class ArpArgs:
    permanent: bool

    @classmethod
    def read(cls, parsed: ParsedArgs) -> ArpArgs:
        return cls(permanent=parsed.flag("permanent"))


@dataclass(frozen=True)
class RulesArgs:
    counters: bool
    nat: bool

    @classmethod
    def read(cls, parsed: ParsedArgs) -> RulesArgs:
        return cls(counters=parsed.flag("counters"), nat=parsed.flag("nat"))


@dataclass(frozen=True)
class DoctorArgs:
    config: str | None

    @classmethod
    def read(cls, parsed: ParsedArgs) -> DoctorArgs:
        return cls(config=parsed.optional_text("config"))


@dataclass(frozen=True)
class DhcpAddArgs:
    mac: str
    ip: str
    hostname: str
    interface: str | None
    descr: str

    @classmethod
    def read(cls, parsed: ParsedArgs) -> DhcpAddArgs:
        return cls(mac=parsed.text("mac"), ip=parsed.text("ip"), hostname=parsed.text("hostname"),
                   interface=parsed.optional_text("interface"), descr=parsed.text("descr"))


@dataclass(frozen=True)
class DhcpRenameArgs:
    mac: str
    hostname: str

    @classmethod
    def read(cls, parsed: ParsedArgs) -> DhcpRenameArgs:
        return cls(mac=parsed.text("mac"), hostname=parsed.text("hostname"))


@dataclass(frozen=True)
class MacArgs:
    """A verb that selects one reservation by MAC (`dhcp rm`, `dhcp rm-static-arp`)."""

    mac: str

    @classmethod
    def read(cls, parsed: ParsedArgs) -> MacArgs:
        return cls(mac=parsed.text("mac"))


@dataclass(frozen=True)
class DnsAddArgs:
    name: str
    ip: str
    descr: str

    @classmethod
    def read(cls, parsed: ParsedArgs) -> DnsAddArgs:
        return cls(name=parsed.text("name"), ip=parsed.text("ip"), descr=parsed.text("descr"))


@dataclass(frozen=True)
class DnsRmArgs:
    name: str

    @classmethod
    def read(cls, parsed: ParsedArgs) -> DnsRmArgs:
        return cls(name=parsed.text("name"))


@dataclass(frozen=True)
class TableArgs:
    """`table <action> [table] [ips...]`; which operands an action needs is checked by the verb."""

    action: str
    table: str | None
    ips: tuple[str, ...]

    @classmethod
    def read(cls, parsed: ParsedArgs) -> TableArgs:
        return cls(action=parsed.text("action"), table=parsed.optional_text("table"),
                   ips=parsed.texts("ips"))


@dataclass(frozen=True)
class SnortCheckArgs:
    targets: tuple[str, ...]

    @classmethod
    def read(cls, parsed: ParsedArgs) -> SnortCheckArgs:
        return cls(targets=parsed.texts("targets"))


@dataclass(frozen=True)
class IpsArgs:
    """A verb over a list of addresses (`snort why`, `snort unblock`)."""

    ips: tuple[str, ...]

    @classmethod
    def read(cls, parsed: ParsedArgs) -> IpsArgs:
        return cls(ips=parsed.texts("ips"))


@dataclass(frozen=True)
class SnortVerifyArgs:
    sid: str
    cidr: str | None
    ip: tuple[str, ...]

    @classmethod
    def read(cls, parsed: ParsedArgs) -> SnortVerifyArgs:
        return cls(sid=parsed.text("sid"), cidr=parsed.optional_text("cidr"), ip=parsed.texts("ip"))


@dataclass(frozen=True)
class SnortFixstepsArgs:
    sid: str
    cidr: str | None

    @classmethod
    def read(cls, parsed: ParsedArgs) -> SnortFixstepsArgs:
        return cls(sid=parsed.text("sid"), cidr=parsed.optional_text("cidr"))


class Handler(ABC):
    """What a subcommand's parser carries as its `verb` default: how to run it."""

    @abstractmethod
    def invoke(self, parsed: ParsedArgs, common: CommonOptions) -> int:
        """Read the verb's own options from `parsed` and run it."""


@dataclass(frozen=True)
class Verb[A](Handler):
    """One subcommand: the reader of its options, and the command function that takes them.

    Binding the two in one record is what lets the type checker see that every command function
    receives the record its reader builds.
    """

    read: Callable[[ParsedArgs], A]
    func: Callable[[CommonOptions, A], int]

    def invoke(self, parsed: ParsedArgs, common: CommonOptions) -> int:
        return self.func(common, self.read(parsed))


def _target_from_options(common: CommonOptions) -> Target:
    if common.fw:
        return load_named_target(common.fw)
    if not common.host:
        raise PfsenseError("no target: pass --host, or --fw <name> with a section in " + str(config_file()))
    return Target(host=common.host, user=common.user, ssh=common.ssh, timeout=common.timeout)


def _guard_mutation(common: CommonOptions, target: Target, what: str) -> str | None:
    """Snapshot before an --apply, and describe the intent when it is a dry run.

    Returns the snapshot path, or None for a dry run. A mutation whose snapshot failed does not
    proceed: the point of the snapshot is to make the change reversible, so a missing one removes
    the only reason it was safe to go ahead.
    """
    if not common.apply:
        return None
    path = do_snapshot(target, Path(common.snapshot_dir or default_snapshot_dir()),
                       run=common.run, allow_repo=common.allow_repo_snapshot)
    print(f"pfsense: snapshot before {what}: {path}", file=sys.stderr)
    return str(path)


def default_snapshot_dir() -> Path:
    """Where a config snapshot goes when the caller does not name a directory.

    NOT the current directory. A snapshot is a whole config.xml carrying password hashes, private
    keys and certificates; defaulting to the cwd drops that wherever the operator happened to be
    standing, and one such file reached a public repository's index that way. An XDG state dir is
    private to the user and is not somewhere anybody runs `git add .`.
    """
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "bitranox" / "pfsense"


def inside_git_worktree(directory: Path, *, run: Runner = _run) -> bool:
    """True when `directory` sits inside a git work tree. False when git cannot answer.

    Fail-open by design: this is the SECOND layer, behind a default that already points outside any
    checkout. A machine with no git must still be able to take a snapshot.
    """
    if not shutil.which("git"):
        return False
    try:
        rc, out, _err = run(["git", "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
                            timeout=10)
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return rc == 0 and (out or "").strip() == "true"


def nearest_existing(directory: Path) -> Path:
    """`directory` itself, or its closest ancestor that exists."""
    probe = directory.absolute()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


SNAPSHOT_PROBE_NAME = "config-snapshot.xml"


def ignored_by_git(directory: Path, *, filename: str = SNAPSHOT_PROBE_NAME, run: Runner = _run) -> bool:
    """True only when git would never stage `directory/filename`, for anyone using this checkout.

    A site's dated backups often live in a gitignored folder of its own machine repo. Four things
    must all hold, because each one alone let a snapshot become committable:

    - the FILE is ignored, not just the folder: with `configs/*` plus `!configs/*.xml` git calls
      `configs/` ignored while the negation re-includes every snapshot in it;
    - the folder is ignored too, and nothing is tracked beneath it (`ls-files`): a force-added
      file makes the folder a tracked place even while a new file there reads as ignored;
    - every matching rule comes from a .gitignore in the checkout or the clone's info/exclude, never
      a per-user core.excludesFile, which another user of the same checkout does not have;
    - the path is resolved first, so `notes/../configs` through a symlink is judged where the
      file will land, not by its spelling.

    core.quotePath=false keeps a non-ASCII path unquoted in git's answer. Fail-closed, unlike
    inside_git_worktree: this is an exemption from a refusal, so any doubt keeps the refusal.
    """
    directory = Path(directory).expanduser().resolve()
    probe = nearest_existing(directory)
    asked_dir = directory.as_posix().rstrip("/") + "/"
    asked_file = (directory / filename).as_posix()
    try:
        top = _git_toplevel(probe, run=run)
        if top is None:
            return False
        rc, out, _err = run(["git", "-c", "core.quotePath=false", "-C", str(probe), "check-ignore",
                             "--stdin", "-z", "-v"], stdin_text=f"{asked_dir}\0{asked_file}\0",
                            timeout=10)
        if rc != 0:
            return False
        sources = _ignore_sources(out or "")
        if set(sources) != {asked_dir, asked_file}:
            return False
        if not all(_trusted_ignore_source(src, top, run=run) for src in sources.values()):
            return False
        rc, tracked, _err = run(["git", "-c", "core.quotePath=false", "-C", str(top), "ls-files",
                                 "-z", "--", asked_dir], timeout=10)
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return rc == 0 and not (tracked or "").strip("\0")


def _git_toplevel(probe: Path, *, run: Runner = _run) -> Path | None:
    rc, out, _err = run(["git", "-C", str(probe), "rev-parse", "--show-toplevel"], timeout=10)
    text = (out or "").strip()
    return Path(text).resolve() if rc == 0 and text else None


def _ignore_sources(out: str) -> dict[str, str]:
    """Map each path check-ignore -v -z named to the source of the rule that IGNORES it.

    Records are four NUL-ended fields: source, line, pattern, path. A path whose deciding pattern
    starts with `!` matched a negation, which RE-INCLUDES it, so it is left out of the map.
    """
    fields = out.split("\0")
    sources: dict[str, str] = {}
    for i in range(0, len(fields) - 3, 4):
        source, _line, pattern, path = fields[i:i + 4]
        if source and not pattern.startswith("!"):
            sources[path] = source
    return sources


def _trusted_ignore_source(source: str, top: Path, *, run: Runner = _run) -> bool:
    """A .gitignore inside the checkout, or this clone's info/exclude; nothing per-user.

    Both live in the checkout every user of it shares (a tracked or untracked .gitignore alike).
    A per-user core.excludesFile does not: git names it by a path outside the work tree. The
    source is resolved against the top (joining keeps an absolute source as it is) and must land
    inside it, so no drive-dependent absoluteness test decides it.
    """
    resolved = (top / source).resolve()
    rc, out, _err = run(["git", "-C", str(top), "rev-parse", "--git-path", "info/exclude"],
                        timeout=10)
    if rc == 0 and out.strip() and resolved == (top / out.strip()).resolve():
        return True
    return resolved.name == ".gitignore" and resolved.is_relative_to(top)


def prepare_snapshot_dir(directory: Path, *, allow_repo: bool = False,
                         filename: str = SNAPSHOT_PROBE_NAME, run: Runner = _run) -> Path:
    """Create `directory` private to the user, refusing a git work tree unless told otherwise.

    A directory the work tree ignores, with nothing tracked beneath it, is not refused (see
    ignored_by_git). The work-tree probe runs on the nearest EXISTING ancestor: git cannot answer
    for a directory that is not there yet, so probing only an existing one let a new dir inside a
    checkout through.
    Only a directory this call creates is made 0700; an existing one keeps its mode (it may be
    shared or served), with a warning when others can read it.
    """
    directory = Path(directory).expanduser()
    if (not allow_repo and inside_git_worktree(nearest_existing(directory), run=run)
            and not ignored_by_git(directory, filename=filename, run=run)):
        raise PfsenseError(
            f"{directory} is inside a git work tree and not ignored by it, and a snapshot is a "
            f"live config.xml with password hashes and private keys in it. Pass --snapshot-dir to "
            f"send it somewhere private (default {default_snapshot_dir()}) or to a folder the "
            f"repository ignores, or --allow-repo-snapshot to override."
        )
    created = not directory.exists()
    directory.mkdir(parents=True, exist_ok=True)
    if os.name != "posix":
        return directory
    if created:
        os.chmod(directory, 0o700)
    elif directory.stat().st_mode & 0o077:
        print(f"pfsense: warning: {directory} is readable by others; a snapshot holds password "
              f"hashes and private keys", file=sys.stderr)
    return directory


def do_snapshot(target: Target, directory: Path, *, run: Runner = _run, allow_repo: bool = False) -> Path:
    """Fetch /conf/config.xml and write it under a timestamped name.

    The content is validated before it is written: an ssh failure or a truncated read must not be
    saved as a snapshot, because a snapshot nobody can restore from is worse than none at all.
    """
    # Resolve the destination BEFORE fetching: a refusal should cost nothing, and there is no
    # reason to pull 180 KB of credentials over the wire only to decline to write it.
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name = f"config-{target.host}-{stamp}.xml"
    directory = prepare_snapshot_dir(directory, allow_repo=allow_repo, filename=name, run=run)
    rc, out, err = run_remote(target, "cat /conf/config.xml", run=run, timeout=max(target.timeout, 60))
    if rc != 0:
        raise PfsenseError(f"could not read /conf/config.xml from {target.host}: {err.strip()[:200]}")
    root = parse_xml(out)
    if root.tag != "pfsense":
        raise PfsenseError(f"root element is <{root.tag}>, not <pfsense>; refusing to save it")
    path = directory / name
    _write_private(path, out)
    return path


def _write_private(path: Path, text: str) -> None:
    """Write `text` to `path` readable by its owner only, whatever the umask.

    A snapshot holds password hashes and private keys, and an existing snapshot folder keeps its
    own mode (it may be shared), so the FILE must be private even where the folder is not. The
    mode is set at creation (0600) and again with fchmod, because O_CREAT ignores the mode for a
    file that already exists: a second snapshot in the same second replaces the first.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        if os.name == "posix":
            os.fchmod(handle.fileno(), 0o600)
        handle.write(text)


# ---- commands -----------------------------------------------------------------------------------
def cmd_info(common: CommonOptions, args: NoArgs) -> int:
    target = _target_from_options(common)
    info = run_php(target, php_info(), parse=FirewallInfo.from_json, run=common.run)
    lines = [
        f"  version:      {info.version}",
        f"  dhcp backend: {info.dhcp_backend}",
        f"  resolver:     {info.resolver}",
        "  interfaces:",
    ]
    for iface in info.interfaces:
        lines.append(f"    {iface.name:<8} {iface.device:<12} {iface.ipaddr}/{iface.subnet}  {iface.descr}")
    pkgs = ", ".join(p.name for p in info.packages) or "none"
    lines.append(f"  packages:     {pkgs}")
    _emit(Envelope(command="info", data=info.to_json(), ok=True), common.json, "\n".join(lines))
    return 0


def cmd_snapshot(common: CommonOptions, args: SnapshotArgs) -> int:
    target = _target_from_options(common)
    directory = args.dir or common.snapshot_dir or default_snapshot_dir()
    path = do_snapshot(target, Path(directory), run=common.run, allow_repo=common.allow_repo_snapshot)
    saved = SnapshotSaved(path=str(path), size=path.stat().st_size)
    _emit(Envelope(command="snapshot", data=saved.to_json(), ok=True),
          common.json, f"  saved {saved.path} ({saved.size} bytes)")
    return 0


def cmd_dhcp_list(common: CommonOptions, args: NoArgs) -> int:
    target = _target_from_options(common)
    reservations = run_php(target, php_list_reservations(), parse=Reservation.list_from_json, run=common.run)
    lines = [f"  {r.ip:<16} {r.mac:<18} {'STATIC-ARP' if r.static_arp else '          '}  "
             f"{r.hostname or r.descr}" for r in reservations]
    lines.append(f"  ({len(reservations)} reservations)")
    _emit(Envelope(command="dhcp list", data=[r.to_json() for r in reservations], ok=True), common.json,
          "\n".join(lines))
    return 0


_HOSTNAME_RX = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def valid_hostname(name: str) -> str:
    """The name a reservation's hostname field takes: one DNS label (letters, digits, inner
    hyphens, at most 63 characters). A dot, an underscore or a leading hyphen is refused here
    rather than by the GUI's validator, which this tool bypasses."""
    if not _HOSTNAME_RX.match(name):
        raise PfsenseError(f"{name!r} is not a valid reservation hostname (one label: letters, "
                           "digits and inner hyphens, at most 63 characters)")
    return name


def interface_for_ip(interfaces: Sequence[Interface], ip: str) -> str:
    """The interface whose static subnet holds `ip`, or a refusal when none or several do."""
    address = ipaddress.ip_address(ip)
    hits: list[str] = []
    for iface in interfaces:
        try:
            network = ipaddress.ip_interface(f"{iface.ipaddr}/{iface.subnet}").network
        except ValueError:
            continue                     # dhcp, track6, none: no static subnet to hold anything
        if address in network:
            hits.append(iface.name)
    if len(hits) != 1:
        found = "no interface" if not hits else f"{len(hits)} interfaces ({', '.join(hits)})"
        raise PfsenseError(f"{found} has a static subnet holding {ip}; pass --interface")
    return hits[0]


def cmd_dhcp_add(common: CommonOptions, args: DhcpAddArgs) -> int:
    target = _target_from_options(common)
    mac = normalize_mac(args.mac)
    ipaddress.ip_address(args.ip)
    hostname = valid_hostname(args.hostname)
    reservations = run_php(target, php_list_reservations(), parse=Reservation.list_from_json, run=common.run)
    taken = [r for r in reservations if r.mac == mac or r.ip == args.ip]
    if taken:
        raise PfsenseError(f"already reserved: {taken[0].ip} {taken[0].mac} "
                           f"({taken[0].hostname or taken[0].descr}) - rename or rm it instead")
    interfaces = run_php(target, php_info(), parse=FirewallInfo.from_json, run=common.run).interfaces
    if args.interface:
        # A named interface must still hold the address: the GUI checks this, and this tool
        # bypasses the GUI, so a reservation outside the subnet would be stored and never served.
        interfaces = tuple(i for i in interfaces if i.name == args.interface)
    interface = interface_for_ip(interfaces, args.ip)
    entry = NewReservation(interface=interface, mac=mac, ip=args.ip, hostname=hostname)
    if not common.apply:
        _emit(Envelope(command="dhcp add", data={"would_add": entry.to_json()}, ok=True,
                       skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would reserve {args.ip} for {mac} ({hostname}) on {interface}.  "
                         "Re-run with --apply.")
        return 0
    _guard_mutation(common, target, f"adding the reservation {args.ip} for {mac}")
    result = run_php(target, php_add_reservation(interface, mac, args.ip, hostname, args.descr),
                     parse=ReservationAdded.from_json, run=common.run)
    if result.added is None:
        raise PfsenseError(result.error or "the reservation was not added")
    result, note = _restart_unbound_after_dhcp(target, result, run=common.run,
                                               change=f"the reservation {args.ip} for {mac}")
    _emit(Envelope(command="dhcp add", data=result.to_json(), ok=True), common.json,
          f"  reserved {args.ip} for {mac} ({hostname}) on {interface}{note}")
    return 0


def _restart_unbound_after_dhcp[R: (ReservationAdded, ReservationRenamed, ReservationRemoved)](
        target: Target, result: R, *, run: Runner, change: str) -> tuple[R, str]:
    """Restart unbound and check it answers when the DHCP write also reconfigured it.

    The PHP side reconfigured unbound only when it registers DHCP static mappings, and says so in
    `unbound_follows`. The check resolves `localhost.`, unbound's own built-in local zone: the
    reservation's name depends on a domain this tool does not read, so the check proves unbound
    answers, not that it answers that name. Returns the result with the check recorded, and the
    human-output suffix.
    """
    if not result.unbound_follows:
        return result, ""
    check = restart_and_verify_unbound(target, name="localhost.", ip="127.0.0.1", run=run, change=change)
    return (replace(result, unbound=check),
            "; unbound reconfigured and restarted for the static-mapping name, and answers")


def cmd_dhcp_rename(common: CommonOptions, args: DhcpRenameArgs) -> int:
    target = _target_from_options(common)
    mac = normalize_mac(args.mac)
    hostname = valid_hostname(args.hostname)
    reservations = run_php(target, php_list_reservations(), parse=Reservation.list_from_json, run=common.run)
    entry = select_reservation(reservations, mac)
    if not common.apply:
        _emit(Envelope(command="dhcp rename", data={"would_rename": entry.to_json(), "to": hostname}, ok=True,
                       skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would rename {entry.ip} {mac} from "
                         f"{entry.hostname or '(no hostname)'} to {hostname}.  Re-run with --apply.")
        return 0
    _guard_mutation(common, target, f"renaming the reservation for {mac}")
    result = run_php(target, php_rename_reservation(mac, hostname), parse=ReservationRenamed.from_json,
                     run=common.run)
    if len(result.renamed) != 1:
        raise PfsenseError(f"the reservation for {mac} was not renamed (it changed since it was listed)")
    result, note = _restart_unbound_after_dhcp(target, result, run=common.run,
                                               change=f"the rename of the reservation for {mac} to {hostname}")
    _emit(Envelope(command="dhcp rename", data=result.to_json(), ok=True), common.json,
          f"  renamed {entry.ip} {mac} to {hostname}{note}")
    return 0


def cmd_dhcp_rm(common: CommonOptions, args: MacArgs) -> int:
    target = _target_from_options(common)
    mac = normalize_mac(args.mac)
    reservations = run_php(target, php_list_reservations(), parse=Reservation.list_from_json, run=common.run)
    entry = select_reservation(reservations, mac)
    if not common.apply:
        _emit(Envelope(command="dhcp rm", data={"would_remove": entry.to_json()}, ok=True,
                       skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would remove {entry.ip} {entry.mac} "
                         f"({entry.hostname or entry.descr}).  Re-run with --apply.")
        return 0
    _guard_mutation(common, target, f"removing the reservation for {mac}")
    result = run_php(target, php_rm_reservation(mac), parse=ReservationRemoved.from_json, run=common.run)
    removed = result.removed
    _require_effect(removed, f"the reservation for {mac} matched, but removing it removed nothing "
                             "(it changed since it was listed); config.xml was not written")
    result, note = _restart_unbound_after_dhcp(target, result, run=common.run,
                                               change=f"the removal of the reservation for {mac}")
    _emit(Envelope(command="dhcp rm", data=result.to_json(), ok=True), common.json,
          f"  removed {len(removed)} reservation(s) for {mac}{note}")
    return 0


def _require_effect(effect: Sequence[object], failure: str) -> None:
    """Refuse a single-target change that matched and then changed nothing.

    The listing found exactly one entry, so the caller asked for one thing and it did not happen.
    That is a failed action (exit 2), not a well-formed "no": exit 1 is reserved for an answer
    such as a finding or a PARTIAL outcome, and reporting this as one hides that nothing changed.
    """
    if not effect:
        raise PfsenseError(failure)


def _removal_exit(requested: Sequence[str], still: Sequence[str], *, where: str) -> int:
    """0 when every address is gone, 1 when SOME of several remain, 2 (raised) when none went.

    Some-of-several is a partial outcome, an answer the caller reads as "these are left". Every
    requested address still present - one address asked for included - means the action did
    nothing, which is a failure rather than an answer.
    """
    if not still:
        return 0
    if set(still) >= set(requested):
        raise PfsenseError(f"nothing was removed: {', '.join(still)} still present in {where}")
    return 1


def cmd_dhcp_rm_static_arp(common: CommonOptions, args: MacArgs) -> int:
    target = _target_from_options(common)
    mac = normalize_mac(args.mac)
    reservations = run_php(target, php_list_reservations(), parse=Reservation.list_from_json, run=common.run)
    entry = select_reservation(reservations, mac)
    if not entry.static_arp:
        _emit(Envelope(command="dhcp rm-static-arp", data={"entry": entry.to_json()}, ok=True,
                       skipped=["static ARP was not set"]),
              common.json, f"  {entry.ip} {mac} does not have static ARP set; nothing to do.")
        return 0
    if not common.apply:
        _emit(Envelope(command="dhcp rm-static-arp", data={"would_clear": entry.to_json()}, ok=True,
                       skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would clear static ARP on {entry.ip} {mac}.  Re-run with --apply.")
        return 0
    _guard_mutation(common, target, f"clearing static ARP for {mac}")
    result = run_php(target, php_rm_static_arp(mac), parse=StaticArpCleared.from_json, run=common.run)
    changed = result.changed
    _require_effect(changed, f"static ARP is set on the reservation for {mac}, but clearing it "
                             "changed nothing (it changed since it was listed); config.xml was not written")
    _emit(Envelope(command="dhcp rm-static-arp", data=result.to_json(), ok=True), common.json,
          f"  cleared static ARP on {len(changed)} reservation(s) for {mac}")
    return 0


def cmd_dns_list(common: CommonOptions, args: NoArgs) -> int:
    target = _target_from_options(common)
    overrides = run_php(target, php_list_overrides(), parse=Override.list_from_json, run=common.run)
    lines = [f"  {o.fqdn:<44} -> {o.ip}" for o in overrides]
    lines.append(f"  ({len(overrides)} host overrides)")
    _emit(Envelope(command="dns list", data=[o.to_json() for o in overrides], ok=True), common.json,
          "\n".join(lines))
    return 0


def _split_name(name: str) -> tuple[str, str]:
    """Split a fully qualified name into the host and domain parts pfSense stores separately."""
    parts = name.strip().strip(".").split(".", 1)
    if len(parts) != 2 or not parts[1]:
        raise PfsenseError(f"{name} is not a fully qualified name (needs a host and a domain part)")
    return parts[0].lower(), parts[1].lower()


def cmd_dns_add(common: CommonOptions, args: DnsAddArgs) -> int:
    target = _target_from_options(common)
    host, domain = _split_name(args.name)
    ipaddress.ip_address(args.ip)
    if not common.apply:
        _emit(Envelope(command="dns add", data={"would_add": {"host": host, "domain": domain, "ip": args.ip}},
                       ok=True, skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would add {host}.{domain} -> {args.ip}.  Re-run with --apply.")
        return 0
    # The PHP duplicate check compares host and domain separately, so it cannot see an override
    # stored with an EMPTY host whose domain is this whole name. Compare full names here, with the
    # same rule the listing uses, before anything is snapshotted or written.
    existing = run_php(target, php_list_overrides(), parse=Override.list_from_json, run=common.run)
    if any(o.fqdn.lower() == f"{host}.{domain}" for o in existing):
        raise PfsenseError(f"an override for {host}.{domain} already exists")
    _guard_mutation(common, target, f"adding {host}.{domain}")
    result = run_php(target, php_add_override(host, domain, args.ip, args.descr),
                     parse=OverrideAdded.from_json, run=common.run)
    if result.error:
        raise PfsenseError(result.error)
    result = replace(result, unbound=restart_and_verify_unbound(
        target, name=f"{host}.{domain}", ip=args.ip, run=common.run,
        change=f"the override {host}.{domain} -> {args.ip}"))
    _emit(Envelope(command="dns add", data=result.to_json(), ok=True), common.json,
          f"  added {host}.{domain} -> {args.ip}; unbound restarted and answers it")
    return 0


def unbound_probe_command(name: str) -> str:
    """The lookup that proves unbound answers: the same form SKILL.md gives the reader."""
    return f"host {shlex.quote(name)} 127.0.0.1"


def answered_addresses(host_output: str) -> set[IPAddress]:
    """The addresses a `host` run printed as answers, normalised so 2001:DB8::1 equals 2001:db8::1."""
    found: set[IPAddress] = set()
    for token in _HOST_ANSWER_RX.findall(host_output):
        try:
            found.add(ipaddress.ip_address(token))
        except ValueError:
            continue
    return found


def restart_and_verify_unbound(target: Target, *, name: str, ip: str, run: Runner, change: str) -> UnboundCheck:
    """Restart unbound and resolve `name` through 127.0.0.1, expecting `ip` among the answers.

    services_unbound_configure() has been observed to leave unbound stopped, with
    unbound-checkconf clean and every lookup timing out, so a write that ends at the reconfigure
    can report success over a dead resolver. Raises with a message that says the change IS in
    config.xml, so the reader repairs the resolver instead of retrying the edit.
    """
    def down(detail: str) -> PfsenseError:
        return PfsenseError(
            f"{change} was written to config.xml, but unbound is not answering: {detail}. "
            f"On the firewall run `{UNBOUND_RESTART}`, then `{unbound_probe_command(name)}`; "
            "reach it by IP, since its own name does not resolve while unbound is down")

    try:
        rc, out, err = run_remote(target, UNBOUND_RESTART, run=run)
        if rc != 0:
            raise down(f"the restart exited {rc}: {(err or out).strip()[:200]}")
        rc, out, err = run_remote(target, unbound_probe_command(name), run=run)
    except subprocess.TimeoutExpired as exc:
        raise down(f"no reply within {exc.timeout}s") from exc
    if ipaddress.ip_address(ip) not in answered_addresses(out):
        reply = " ".join((out or err).split())[:200] or "no output"
        raise down(f"{name} did not resolve to {ip} through 127.0.0.1 (exit {rc}: {reply})")
    return UnboundCheck(restarted=True, resolved=name, ip=ip)


def _probe_after_removal(overrides: Sequence[Override], removed_fqdn: str) -> tuple[str, str]:
    """A name unbound must still answer locally after `removed_fqdn` is gone, and its address.

    An override that remains has a known answer that needs no upstream server, so a dead link to
    the internet cannot fail the check. With none left, `localhost.` is unbound's own built-in
    local zone; the trailing dot keeps a search domain from being tried first.
    """
    for entry in overrides:
        if entry.fqdn.lower() != removed_fqdn.lower() and entry.ip:
            return entry.fqdn, entry.ip
    return "localhost.", "127.0.0.1"


def cmd_dns_rm(common: CommonOptions, args: DnsRmArgs) -> int:
    target = _target_from_options(common)
    host, domain = _split_name(args.name)
    overrides = run_php(target, php_list_overrides(), parse=Override.list_from_json, run=common.run)
    entry = select_one(overrides, f"{host}.{domain}", key=lambda o: o.fqdn, field="fqdn",
                       what="host override")
    if not common.apply:
        _emit(Envelope(command="dns rm", data={"would_remove": entry.to_json(with_fqdn=True)}, ok=True,
                       skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would remove {entry.fqdn} -> {entry.ip}.  Re-run with --apply.")
        return 0
    _guard_mutation(common, target, f"removing {host}.{domain}")
    # Target the fields as STORED, not a re-split of the name: an override with an empty host keeps
    # the whole name in its domain, and host 'bare' + domain 'example.com' would match nothing.
    stored_host = entry.host.lower()
    stored_domain = entry.domain.lower()
    result = run_php(target, php_rm_override(stored_host, stored_domain), parse=OverrideRemoved.from_json,
                     run=common.run)
    removed = result.removed
    _require_effect(removed, f"the override {host}.{domain} matched, but removing it removed nothing "
                             "(it changed since it was listed); config.xml was not written")
    probe_name, probe_ip = _probe_after_removal(overrides, entry.fqdn)
    result = replace(result, unbound=restart_and_verify_unbound(
        target, name=probe_name, ip=probe_ip, run=common.run,
        change=f"the removal of the override {entry.fqdn}"))
    _emit(Envelope(command="dns rm", data=result.to_json(), ok=True), common.json,
          f"  removed {len(removed)} override(s) for {host}.{domain}; "
          f"unbound restarted and answers {probe_name}")
    return 0


def cmd_arp(common: CommonOptions, args: ArpArgs) -> int:
    target = _target_from_options(common)
    rc, out, err = run_remote(target, "arp -an", run=common.run)
    if rc != 0:
        raise PfsenseError(f"could not read the ARP table on {target.host}: {err.strip()[:200]}")
    entries = parse_arp(out)
    if args.permanent:
        entries = [e for e in entries if e.permanent]
    lines = [f"  {e.ip:<16} {e.mac or '(incomplete)':<18} {e.interface:<8} "
             f"{'PERMANENT' if e.permanent else ''}" for e in entries]
    lines.append(f"  ({len(entries)} entries)")
    _emit(Envelope(command="arp", data=[e.to_json() for e in entries], ok=True), common.json,
          "\n".join(lines))
    return 0


def _require_table_operands(args: TableArgs) -> str:
    """The table name as given, refusing a missing table or address as a usage error.

    An empty shell variable in a script otherwise reaches pfctl as `-t ''` and comes back as a
    verdict ("not in", "deleted 0 of 0") with exit 0 or 1, indistinguishable from a real answer.
    `list` names no table, so it gets "".
    """
    table = args.table or ""
    if args.action == "list":
        return table
    if not table.strip():
        raise PfsenseError(f"table {args.action} needs a table name")
    if args.action in ("test", "del") and not [ip for ip in args.ips if ip.strip()]:
        raise PfsenseError(f"table {args.action} needs at least one address")
    return table


def cmd_table(common: CommonOptions, args: TableArgs) -> int:
    table = _require_table_operands(args)
    target = _target_from_options(common)
    if args.action == "list":
        rc, out, err = run_remote(target, "pfctl -sT", run=common.run)
        if rc != 0:
            raise PfsenseError(f"could not list pf tables: {err.strip()[:200]}")
        names = [line.strip() for line in out.split("\n") if line.strip()]
        _emit(Envelope(command="table list", data=names, ok=True), common.json,
              "\n".join(f"  {n}" for n in names) + f"\n  ({len(names)} tables)")
        return 0

    if args.action == "show":
        rc, out, err = run_remote(target, f"pfctl -t {shlex.quote(table)} -T show", run=common.run)
        if rc != 0:
            raise PfsenseError(f"could not read table {table}: {err.strip()[:200]}")
        ips = sorted(parse_table(out))
        _emit(Envelope(command="table show", data=ips, ok=True), common.json,
              "\n".join(f"  {ip}" for ip in ips) + f"\n  ({len(ips)} entries in {table})")
        return 0

    if args.action == "test":
        rc, out, err = run_remote(target, f"pfctl -t {shlex.quote(table)} -T show", run=common.run)
        if rc != 0:
            raise PfsenseError(f"could not read table {table}: {err.strip()[:200]}")
        present = blocked_among(out, args.ips)
        check = TableCheck(table=table, present=tuple(present),
                           absent=tuple(ip for ip in args.ips if ip not in present))
        _emit(Envelope(command="table test", data=check.to_json(), ok=True), common.json,
              "\n".join(f"  {'IN ' if ip in present else 'not'}  {ip}  ({table})" for ip in args.ips))
        return 0 if present else 1

    # del
    if not common.apply:
        _emit(Envelope(command="table del", data={"would_delete": args.ips, "table": table},
                       ok=True, skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would delete {', '.join(args.ips)} from {table}.  Re-run with --apply.")
        return 0
    for ip in args.ips:
        run_remote(target, f"pfctl -t {shlex.quote(table)} -T delete {shlex.quote(ip)}", run=common.run)
    rc, out, err = run_remote(target, f"pfctl -t {shlex.quote(table)} -T show", run=common.run)
    if rc != 0:
        raise PfsenseError(f"could not re-read table {table} to confirm: {err.strip()[:200]}")
    still = blocked_among(out, args.ips)
    code = _removal_exit(args.ips, still, where=f"table {table}")
    deletion = TableDeletion(requested=tuple(args.ips), still_present=tuple(still))
    _emit(Envelope(command="table del", data=deletion.to_json(), ok=True),
          common.json, f"  deleted {len(args.ips) - len(still)} of {len(args.ips)} from {table}" +
                     (f"\n  STILL PRESENT: {', '.join(still)}" if still else ""))
    return code


def cmd_rules(common: CommonOptions, args: RulesArgs) -> int:
    target = _target_from_options(common)
    command = "pfctl -vvsr" if args.counters else ("pfctl -sn" if args.nat else "pfctl -sr")
    rc, out, err = run_remote(target, command, run=common.run, timeout=max(target.timeout, 60))
    if rc != 0:
        raise PfsenseError(f"could not read the ruleset: {err.strip()[:200]}")
    rules = [line.rstrip() for line in out.split("\n") if line.strip()]
    _emit(Envelope(command="rules", data=rules, ok=True), common.json, "\n".join(rules))
    return 0


def cmd_snort_check(common: CommonOptions, args: SnortCheckArgs) -> int:
    target = _target_from_options(common)
    resolved: dict[str, list[str]] = {}
    for name in args.targets:
        try:
            resolved[name] = resolve_ips(name)
        except OSError as exc:
            raise PfsenseError(f"cannot resolve {name}: {exc}") from exc
    every_ip = [ip for ips in resolved.values() for ip in ips]

    rc, table, err = run_remote(target, f"pfctl -t {SNORT_TABLE} -T show", run=common.run)
    if rc != 0:
        raise PfsenseError(f"could not read the {SNORT_TABLE} table on {target.host} "
                           f"(is Snort installed?): {err.strip()[:200]}")

    blocked = blocked_among(table, every_ip)
    check = BlockCheck(resolved=tuple((name, tuple(ips)) for name, ips in resolved.items()),
                       blocked=tuple(blocked), clear=tuple(ip for ip in every_ip if ip not in blocked))
    lines: list[str] = []
    for name, ips in resolved.items():
        for ip in ips:
            lines.append(f"  {'BLOCKED' if ip in blocked else 'clear  '}  {ip}  ({name})")
    if blocked:
        lines.append("")
        lines.append(f"Next: pfsense.py snort why {blocked[0]}   then snort fixsteps --sid <GID:SID>")
    _emit(Envelope(command="snort check", data=check.to_json(), ok=True), common.json, "\n".join(lines))
    return 1 if blocked else 0


CLOCK_MARKER = "PFSENSE_CLOCK"
_CLOCK_RX = re.compile(rf"^{CLOCK_MARKER} (\d{{4}}-\d{{2}}-\d{{2}}T\d{{2}}:\d{{2}}:\d{{2}})\s*$", re.MULTILINE)


def split_firewall_clock(out: str) -> tuple[datetime | None, str]:
    """(the firewall's local time from the clock line, the output without that line).

    Snort stamps are the firewall's local time with no year, so the year is inferred against
    the FIREWALL's clock: this machine's clock differs by its time zone and skew, and an alert a
    few minutes old there could read as 'in the future' here and be pushed a year back."""
    match = _CLOCK_RX.search(out)
    if match is None:
        return None, out
    try:
        moment = datetime.fromisoformat(match.group(1))
    except ValueError:
        moment = None
    return moment, out[:match.start()] + out[match.end():]


def cmd_snort_why(common: CommonOptions, args: IpsArgs) -> int:
    target = _target_from_options(common)
    # The alert files ROTATE, so read the whole set: a block laid down yesterday is not in the
    # current file. Read once for every IP rather than per IP - these logs are large. The clock
    # is read in the same command, so it is the time the logs were read at.
    rc, out, err = run_remote(target, f"date '+{CLOCK_MARKER} %Y-%m-%dT%H:%M:%S'; "
                                      "cat /var/log/snort/*/alert /var/log/snort/*/alert.* 2>/dev/null",
                              run=common.run, timeout=max(target.timeout, 60))
    firewall_now, out = split_firewall_clock(out)
    if rc != 0 and not out.strip():
        raise PfsenseError(f"could not read the snort alert logs on {target.host}: {err.strip()[:200]}")
    found = {ip: parse_alerts(out, ip=ip) for ip in args.ips}
    skipped: list[str] = []
    now = firewall_now
    if now is None:
        now = datetime.now()
        skipped.append("the firewall clock could not be read; a missing stamp year was inferred "
                       "from the local clock")

    lines: list[str] = []
    for ip, alerts in found.items():
        if not alerts:
            lines.append(f"  {ip}: no alert names this IP (the block may come from a reputation feed)")
            continue
        # GID:SID, never the SID alone: the suppression has to name the generator that fired.
        signatures = sorted({a.signature for a in alerts}, key=lambda s: (s.gid, s.sid))
        # The glob reads the current file BEFORE the rotated ones, so file order is not time
        # order: pick by the stamp, with the year the stamp leaves out inferred from today.
        latest = latest_alert(alerts, now=now)
        lines.append(f"  {ip}: {len(alerts)} alert(s), GID:SID {', '.join(s.label for s in signatures)}")
        lines.append(f"      latest: {latest.timestamp}  {latest.message}  (GID:SID {latest.signature.label})")
        lines.append(f"      next:   pfsense.py snort fixsteps --sid {latest.signature.label}")
    for note in skipped:
        print(f"pfsense: note: {note}", file=sys.stderr)
    any_found = any(found.values())
    data = {ip: [asdict(a) for a in alerts] for ip, alerts in found.items()}
    _emit(Envelope(command="snort why", data=data, ok=True, skipped=skipped), common.json,
          "\n".join(lines))
    return 0 if any_found else 1


def cmd_snort_unblock(common: CommonOptions, args: IpsArgs) -> int:
    target = _target_from_options(common)
    if not common.apply:
        _emit(Envelope(command="snort unblock", data={"would_delete": args.ips}, ok=True,
                       skipped=["--apply not given"]),
              common.json, f"  DRY RUN: would delete {', '.join(args.ips)} from {SNORT_TABLE}.  Re-run with --apply.")
        return 0
    for ip in args.ips:
        run_remote(target, f"pfctl -t {SNORT_TABLE} -T delete {shlex.quote(ip)}", run=common.run)
    rc, table, err = run_remote(target, f"pfctl -t {SNORT_TABLE} -T show", run=common.run)
    if rc != 0:
        raise PfsenseError(f"could not re-read the table to confirm: {err.strip()[:200]}")
    still = blocked_among(table, args.ips)
    code = _removal_exit(args.ips, still, where=SNORT_TABLE)
    unblocked = Unblocked(requested=tuple(args.ips), still_blocked=tuple(still))
    human = "  cleared: " + ", ".join(ip for ip in args.ips if ip not in still)
    if still:
        human += f"\n  STILL BLOCKED: {', '.join(still)}"
    human += ("\n\nThis is temporary. Clearing the table does NOT stop the rule re-adding the "
              "address on the next packet: suppress the rule too, with snort fixsteps --sid <GID:SID> "
              "(snort why prints it).")
    _emit(Envelope(command="snort unblock", data=unblocked.to_json(), ok=True), common.json, human)
    return code


_TRACKS = ("by_src", "by_dst")


@dataclass(frozen=True)
class SuppressScope:
    """Which addresses one live `suppress` statement for a rule applies to.

    `track` None with `understood` True is the plain form, which suppresses the rule for every
    address. A scoped form names the side of the alert (`by_src`, `by_dst`) and the addresses on
    that side (`networks`). `understood` False is a statement whose scope this tool does not
    evaluate (a variable, a negation, track without ip): it counts as covering nothing.
    """

    track: str | None
    ip: str | None
    networks: tuple[Network, ...] = ()
    understood: bool = True

    def covers(self, target: Network | None) -> bool:
        if not self.understood:
            return False
        if self.track is None:
            return True
        if target is None:
            return False
        return any(_subnet_of(target, net) for net in self.networks)

    def to_json(self) -> dict[str, object]:
        return {"track": self.track, "ip": self.ip, "understood": self.understood}

    @property
    def label(self) -> str:
        if self.track is None and self.understood:
            return "every address"
        return f"track {self.track}, ip {self.ip}"


def _subnet_of(inner: Network, outer: Network) -> bool:
    """`inner.subnet_of(outer)`, and False across address families, where subnet_of raises."""
    if isinstance(inner, ipaddress.IPv4Network) and isinstance(outer, ipaddress.IPv4Network):
        return inner.subnet_of(outer)
    if isinstance(inner, ipaddress.IPv6Network) and isinstance(outer, ipaddress.IPv6Network):
        return inner.subnet_of(outer)
    return False


def _scope_networks(ip_value: str) -> tuple[Network, ...] | None:
    """The networks a suppress `ip` value names, or None for a form not evaluated here.

    Snort's README.filters documents a single address and a CIDR block; a bracketed list of them
    is read member by member. A `$VARIABLE` or a `!` negation would need Snort's own variable
    table and list semantics, so it is not guessed at: None, and the statement covers nothing.
    """
    inner = ip_value[1:-1] if ip_value.startswith("[") and ip_value.endswith("]") else ip_value
    networks: list[Network] = []
    for member in (part.strip() for part in inner.split(",")):
        try:
            networks.append(ipaddress.ip_network(member, strict=False))
        except ValueError:
            return None
    return tuple(networks)


def _parse_scope(rest: str) -> SuppressScope:
    """The scope of one statement, from the text after its `sig_id <n>`."""
    track = _TRACK_RE.search(rest)
    ip = _TRACK_IP_RE.search(rest)
    if track is None and ip is None:
        return SuppressScope(track=None, ip=None)
    track_value = track.group(1) if track else None
    ip_value = ip.group(1) if ip else None
    # Snort requires track and ip together; one without the other, or a track it does not
    # define, is not a scope this tool can vouch for.
    networks = _scope_networks(ip_value) if ip_value is not None else None
    if track_value not in _TRACKS or networks is None:
        return SuppressScope(track=track_value, ip=ip_value, understood=False)
    return SuppressScope(track=track_value, ip=ip_value, networks=networks)


def suppress_scopes(supp_text: str, sig: SignatureId) -> list[SuppressScope]:
    """The scope of every live `suppress` statement that names this generator AND this signature.

    Anchored per line to a live statement: a commented-out line, or a SID named only in a trailing
    comment, suppresses nothing. The generator is part of the match because `gen_id 1, sig_id 9`
    leaves a GID 125 SID 9 alert firing, and reading it as the fix being in place is how a no-op
    suppression went unnoticed. Only the order pfSense writes (`gen_id` before `sig_id`) counts:
    whether Snort accepts the reverse was not checked, and a NO there is the safe misreading.
    The scope is returned rather than a yes/no because `track by_src, ip X` suppresses the rule
    only where X is the alert's source: counting it as a full suppression said yes while every
    other address stayed blocked.
    `sig_id 0` matches too: Snort's README.filters says it "applies to all sig_ids for the given
    gen_id", and reading it as some other signature said NO while Snort suppressed the alert.
    """
    live_rule = re.compile(rf"^[ \t]*suppress\b[^#\n]*\bgen_id\s+{sig.gid}\b[^#\n]*"
                           rf"\bsig_id\s+(?:{sig.sid}|0)\b(?P<rest>[^#\n]*)", re.MULTILINE)
    return [_parse_scope(match.group("rest")) for match in live_rule.finditer(supp_text)]


def _assumed_note(sig: SignatureId) -> str:
    if not sig.gid_assumed:
        return ""
    return " (gen_id 1 assumed for a bare --sid; pass the GID:SID that snort why prints)"


def _verify_targets(args: SnortVerifyArgs) -> list[tuple[str, Network | None]]:
    """The addresses the suppression must cover: each --ip, and the --cidr range.

    An --ip that is not an address is refused (ValueError, exit 2). An unparsable --cidr is kept
    with no network: it still goes to the pass-list check verbatim, and no scoped suppression can
    be shown to cover it.
    """
    targets: list[tuple[str, Network | None]] = []
    for ip in args.ip or []:
        address = ipaddress.ip_address(ip.strip())
        targets.append((str(address), ipaddress.ip_network(address)))
    if args.cidr:
        try:
            targets.append((args.cidr, ipaddress.ip_network(args.cidr.strip(), strict=False)))
        except ValueError:
            targets.append((args.cidr, None))
    return targets


def _scope_verdict(scopes: list[SuppressScope], targets: Sequence[tuple[str, Network | None]],
                   ) -> tuple[bool, dict[str, list[str]], list[str]]:
    """(suppressed for what was asked, which scopes cover each target, the human lines)."""
    if not scopes:
        return False, {}, []
    if any(s.understood and s.track is None for s in scopes):
        return True, {label: ["all"] for label, _ in targets}, []
    # A plain statement returned above, so every covering scope here names its side.
    coverage = {label: [s.track for s in scopes if s.covers(net) and s.track is not None]
                for label, net in targets}
    lines: list[str] = []
    for label, tracks in coverage.items():
        if tracks:
            sides = " and ".join(f"track {t}" for t in tracks)
            lines.append(f"    {label}: yes ({sides}: only alerts with it on that side)")
        else:
            lines.append(f"    {label}: NO - outside every scoped suppression of this rule")
    return bool(targets) and all(coverage.values()), coverage, lines


def _suppressed_line(sig: SignatureId, scopes: list[SuppressScope],
                     targets: Sequence[tuple[str, Network | None]], suppressed: bool) -> str:
    head = f"  GID:SID {sig.label} suppressed: "
    if not scopes:
        return head + "NO"
    if any(s.understood and s.track is None for s in scopes):
        return head + "yes, for every address"
    unread = [s.label + " (scope not understood)" for s in scopes if not s.understood]
    read = [s.label for s in scopes if s.understood]
    named = "; ".join(read + unread)
    if not targets:
        return (head + f"NO - only for {named}. Give --ip <blocked address> or --cidr to check "
                "whether that covers the address being blocked")
    return head + ("yes" if suppressed else "NO") + f", only for {named}"


@dataclass(frozen=True)
class PassListCheck:
    """Whether the `--cidr` range is a literal entry of the live instance's generated pass list."""

    cidr_passlisted: bool
    passlist_entries: int


@dataclass(frozen=True)
class SuppressionCheck:
    """The `snort verify` answer: the live instance, the rule, every live suppress statement for
    it with its scope, which statements cover each asked address, and (with --cidr) the pass list.

    `coverage` keeps the asked addresses in the order given, each named once; `["all"]` means a
    plain statement covers it. `passlist` is None when no --cidr was asked, and its keys are then
    absent from the JSON, as they always were.
    """

    instance_dir: str
    sig: SignatureId
    sid_suppressed: bool
    suppressions: tuple[SuppressScope, ...]
    coverage: tuple[tuple[str, tuple[str, ...]], ...]
    passlist: PassListCheck | None

    def to_json(self) -> dict[str, object]:
        out: dict[str, object] = {
            "instance_dir": self.instance_dir, "gid": self.sig.gid, "sid": self.sig.sid,
            "gid_assumed": self.sig.gid_assumed, "sid_suppressed": self.sid_suppressed,
            "suppressions": [s.to_json() for s in self.suppressions],
            "coverage": {label: list(tracks) for label, tracks in self.coverage}}
        if self.passlist is not None:
            out["cidr_passlisted"] = self.passlist.cidr_passlisted
            out["passlist_entries"] = self.passlist.passlist_entries
        return out


def _passlist_check(target: Target, instance: str, cidr: str, *, run: Runner) -> PassListCheck:
    """Whether `cidr` is a literal line of the GENERATED pass list.

    Never grep the suppression file for this: its comments name the same addresses, so the match
    would be vacuous and always "pass".
    """
    _, passlist, _ = run_remote(target, f"cat {instance}/*Whitelist* 2>/dev/null", run=run)
    entries = {line.strip() for line in passlist.split("\n") if line.strip()}
    return PassListCheck(cidr_passlisted=cidr in entries, passlist_entries=len(entries))


def cmd_snort_verify(common: CommonOptions, args: SnortVerifyArgs) -> int:
    sig = parse_sid_spec(args.sid)
    targets = _verify_targets(args)
    target = _target_from_options(common)
    rc, ps_out, _ = run_remote(target, "ps auxww", run=common.run)
    instance = instance_dir_from_ps(ps_out) if rc == 0 else None
    if not instance:
        raise PfsenseError(f"snort does not appear to be running on {target.host}")

    # The SUPPRESSION file carries the GID:SID and the scope of each statement.
    _, supp, _ = run_remote(target, f"cat {instance}/supp* 2>/dev/null", run=common.run)
    scopes = suppress_scopes(supp, sig)
    suppressed, coverage, coverage_lines = _scope_verdict(scopes, targets)
    passlist = _passlist_check(target, instance, args.cidr, run=common.run) if args.cidr else None
    check = SuppressionCheck(
        instance_dir=instance, sig=sig, sid_suppressed=suppressed, suppressions=tuple(scopes),
        coverage=tuple((label, tuple(tracks)) for label, tracks in coverage.items()), passlist=passlist)

    ok = suppressed and (passlist is None or passlist.cidr_passlisted)
    human = "\n".join(
        [f"  live instance: {instance}",
         _suppressed_line(sig, scopes, targets, suppressed) + _assumed_note(sig)]
        + coverage_lines
        + ([f"  {args.cidr} in pass list: {'yes' if passlist.cidr_passlisted else 'NO'}"]
           if passlist is not None else [])
    )
    _emit(Envelope(command="snort verify", data=check.to_json(), ok=True), common.json, human)
    return 0 if ok else 1


def _scoped_suppress_lines(sig: SignatureId, cidr: str | None) -> list[str]:
    """The narrower alternative to the all-addresses suppression, when a range was given.

    The plain line silences the rule for every address, which is the reviewer's call to make,
    so the scope is said out loud. A scoped pair names BOTH sides because the range can be the
    alert's source or its destination depending on the rule, and one side alone leaves the other
    direction blocking. The range goes into a suppress line only when it parses as a network.
    """
    if not cidr:
        return ["     That line suppresses the rule for EVERY address. Give --cidr <range> for a form",
                "     scoped to one range."]
    try:
        network = ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError:
        return ["     That line suppresses the rule for EVERY address. No scoped form is printed:",
                "     --cidr is not an address range."]
    base = f"suppress gen_id {sig.gid}, sig_id {sig.sid}"
    return ["     That line suppresses the rule for EVERY address. To suppress it only for traffic",
            f"     to or from {network}, add these two lines instead (the range can be either side",
            "     of the alert):",
            f"       {base}, track by_src, ip {network}",
            f"       {base}, track by_dst, ip {network}"]


def fix_steps(*, sig: SignatureId, cidr: str | None = None) -> str:
    """The durable three-part fix, spelled out for a human to apply and review.

    Deliberately NOT automated: it edits the firewall's config.xml, which is a reviewed change.
    What this does is make sure none of the three parts is forgotten, because doing only the
    obvious one (clearing the table) is the dirty patch that lets it recur within hours.
    """
    range_line = cidr or "<the destination range, e.g. 198.51.100.0/22>"
    assumed = ([f"     gen_id 1 is assumed: --sid {sig.sid} gave no generator. If snort why shows",
                f"     another GID for SID {sig.sid}, re-run with --sid <GID>:{sig.sid}; under any other",
                "     generator this line suppresses a different rule and the block recurs."]
               if sig.gid_assumed else [])
    return "\n".join([
        "Durable fix (all three parts, or it recurs):",
        "",
        f"  1. Suppress the rule: add 'suppress gen_id {sig.gid}, sig_id {sig.sid}' to the WAN suppression",
        "     list (Services > Snort > Pass Lists / Suppress, or config.xml).",
        *assumed,
        *_scoped_suppress_lines(sig, cidr),
        "",
        f"  2. Pass-list the range: add {range_line} as a LITERAL <item> in the Snort pass list",
        "     entry's <address>. Do NOT add it to a firewall ALIAS: an alias entry there is a",
        "     NO-OP, because snort_build_list expands it via filter_generate_nested_alias, which",
        "     returns empty unless $aliastable was built by a filter run in the same PHP process,",
        "     and then writes the literal alias NAME into the generated list.",
        "",
        "  3. Clear what is already blocked - suppressing does not flush the table:",
        "     pfsense.py snort unblock <ip> ... --apply",
        "",
        "Then resync Snort so the files are regenerated, and verify with:",
        f"  pfsense.py snort verify --sid {sig.label}" + (f" --cidr {cidr}" if cidr else ""),
    ])


def cmd_snort_fixsteps(common: CommonOptions, args: SnortFixstepsArgs) -> int:
    sig = parse_sid_spec(args.sid)
    steps = fix_steps(sig=sig, cidr=args.cidr)
    _emit(Envelope(command="snort fixsteps", data=FixSteps(sig=sig, cidr=args.cidr, steps=steps).to_json(),
                   ok=True), common.json, steps)
    return 0


def _read_or_raise(target: Target, command: str, *, run: Runner) -> str:
    """Stdout of a read the audit depends on, or a typed error.

    An empty read after an ssh drop is indistinguishable from a healthy empty answer, so an
    unchecked rc turns a dropped connection into a clean bill of health.
    """
    rc, out, err = run_remote(target, command, run=run)
    if rc != 0:
        raise PfsenseError(f"`{command}` failed on {target.host} (exit {rc}): {err.strip()[:200]}")
    return out


def _present_upgrade_locks(target: Target, *, run: Runner) -> list[str]:
    """The UPGRADE_LOCKS paths that exist on the box, or a typed error.

    One `test -f` per path, the same command shape for each: exit 0 is present, 1 is absent, and
    anything else (255 for a dropped ssh) is a failed read, never "no lock".
    """
    present: list[str] = []
    for path in UPGRADE_LOCKS:
        rc, _, err = run_remote(target, f"test -f {path}", run=run)
        if rc not in (0, 1):
            raise PfsenseError(f"could not test for {path} on {target.host} "
                               f"(exit {rc}): {err.strip()[:200]}")
        if rc == 0:
            present.append(path)
    return present


def cmd_doctor(common: CommonOptions, args: DoctorArgs) -> int:
    if args.config:
        text = Path(args.config).read_text(encoding="utf-8")
        findings = doctor_findings(reservations=reservations_from_config_xml(text),
                                   pools=pools_from_config_xml(text))
        source = args.config
    else:
        target = _target_from_options(common)
        reservations = run_php(target, php_list_reservations(), parse=Reservation.list_from_json, run=common.run)
        pools = run_php(target, php_list_pools(), parse=Pool.list_from_json, run=common.run)
        arp_out = _read_or_raise(target, "arp -an", run=common.run)
        resolv = _read_or_raise(target, "cat /etc/resolv.conf", run=common.run)
        findings = doctor_findings(reservations=reservations,
                                   arp=parse_arp(arp_out), resolv_conf=resolv,
                                   upgrade_locks=_present_upgrade_locks(target, run=common.run),
                                   pools=pools)
        source = target.host

    warns = [f for f in findings if f.severity == Severity.WARN]
    lines = [f"  {source}:"]
    for finding in findings:
        lines.append(f"  [{finding.severity.upper():<4}] {finding.check}: {finding.subject}")
        lines.append(f"         {finding.detail}")
    lines.append(f"  ({len(warns)} to act on, {len(findings) - len(warns)} informational)")
    _emit(Envelope(command="doctor", data=[asdict(f) for f in findings], ok=True),
          common.json, "\n".join(lines))
    return 1 if warns else 0


# ---- cli ----------------------------------------------------------------------------------------
def _mutation_flags() -> argparse.ArgumentParser:
    """The flags a mutating verb accepts AFTER its subcommand, as a reusable parent.

    They also exist on the top-level parser, so both `--apply dns add ...` and the documented
    `dns add ... --apply` work. `SUPPRESS` is what makes that safe: without it argparse would set
    the subparser's default over a value the top level already parsed, so `--apply` given first
    would be silently reset to False and a mutation the operator asked for would run as a dry run.
    """
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--apply", action="store_true", default=argparse.SUPPRESS,
                        help="actually make the change (default is a dry run)")
    common.add_argument("--snapshot-dir", default=argparse.SUPPRESS,
                        help="where a pre-change snapshot is written (default is a private "
                             "per-user state dir, never the current directory)")
    common.add_argument("--allow-repo-snapshot", action="store_true", default=argparse.SUPPRESS,
                        help="permit writing a snapshot inside a git work tree, in a folder "
                             "it does not ignore")
    return common


def build_parser() -> argparse.ArgumentParser:
    mut = _mutation_flags()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", help="firewall host or address (no default: name the box you mean)")
    ap.add_argument("--fw", help=f"named target from {config_file()}")
    ap.add_argument("--user", default="admin", help="ssh user (default admin)")
    ap.add_argument("--ssh", default="ssh", help='ssh command, e.g. "ssh -i /key -o BatchMode=yes"')
    ap.add_argument("--timeout", type=int, default=30, help="per-command ssh timeout in seconds")
    ap.add_argument("--json", action="store_true", help="emit the machine-readable envelope")
    ap.add_argument("--apply", action="store_true", help="actually make the change (default is a dry run)")
    ap.add_argument("--snapshot-dir", default=None,
                    help=f"where a pre-change snapshot is written "
                         f"(default {default_snapshot_dir()}, mode 0700)")
    ap.add_argument("--allow-repo-snapshot", action="store_true",
                    help="permit writing a snapshot inside a git work tree (refused by default unless the "
                         "repository ignores the folder)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("info", help="version, DHCP backend, resolver, interfaces, packages")
    p.set_defaults(verb=Verb(read=NoArgs.read, func=cmd_info))

    p = sub.add_parser("snapshot", help="save /conf/config.xml under a timestamped name")
    p.add_argument("--dir", default=None,
                   help="destination directory (default: a private per-user "
                        "state dir, never the current directory)")
    p.set_defaults(verb=Verb(read=SnapshotArgs.read, func=cmd_snapshot))

    p = sub.add_parser("arp", help="the ARP table, flagging permanent entries")
    p.add_argument("--permanent", action="store_true", help="only the permanent entries")
    p.set_defaults(verb=Verb(read=ArpArgs.read, func=cmd_arp))

    p = sub.add_parser("rules", help="the live pf ruleset")
    p.add_argument("--counters", action="store_true", help="include per-rule counters (pfctl -vvsr)")
    p.add_argument("--nat", action="store_true", help="show NAT rules instead (pfctl -sn)")
    p.set_defaults(verb=Verb(read=RulesArgs.read, func=cmd_rules))

    p = sub.add_parser("doctor", help="audit for the faults that raise no error of their own")
    p.add_argument("--config", help="audit a saved config.xml offline instead of a live box")
    p.set_defaults(verb=Verb(read=DoctorArgs.read, func=cmd_doctor))

    dhcp = sub.add_parser("dhcp", help="DHCP reservations").add_subparsers(dest="action", required=True)
    p = dhcp.add_parser("list", help="every reservation, with the static-ARP flag")
    p.set_defaults(verb=Verb(read=NoArgs.read, func=cmd_dhcp_list))
    p = dhcp.add_parser("add", parents=[mut], help="add one reservation (MAC -> address)")
    p.add_argument("--mac", required=True)
    p.add_argument("--ip", required=True)
    p.add_argument("--hostname", required=True, help="one label, e.g. printer")
    p.add_argument("--interface", help="pfSense interface name, e.g. lan or opt1 (default: the "
                                       "one whose static subnet holds --ip)")
    p.add_argument("--descr", default="added by pfsense.py")
    p.set_defaults(verb=Verb(read=DhcpAddArgs.read, func=cmd_dhcp_add))
    p = dhcp.add_parser("rename", parents=[mut], help="set the hostname of one reservation, selected by MAC")
    p.add_argument("--mac", required=True)
    p.add_argument("--hostname", required=True, help="one label, e.g. office-printer")
    p.set_defaults(verb=Verb(read=DhcpRenameArgs.read, func=cmd_dhcp_rename))
    p = dhcp.add_parser("rm", parents=[mut], help="delete one reservation, selected by MAC")
    p.add_argument("--mac", required=True)
    p.set_defaults(verb=Verb(read=MacArgs.read, func=cmd_dhcp_rm))
    p = dhcp.add_parser("rm-static-arp", parents=[mut], help="clear ARP Table Static Entry, keeping the reservation")
    p.add_argument("--mac", required=True)
    p.set_defaults(verb=Verb(read=MacArgs.read, func=cmd_dhcp_rm_static_arp))

    dns = sub.add_parser("dns", help="unbound host overrides").add_subparsers(dest="action", required=True)
    p = dns.add_parser("list", help="every host override")
    p.set_defaults(verb=Verb(read=NoArgs.read, func=cmd_dns_list))
    p = dns.add_parser("add", parents=[mut], help="add one host override")
    p.add_argument("--name", required=True, help="fully qualified, e.g. nas.example.com")
    p.add_argument("--ip", required=True)
    p.add_argument("--descr", default="added by pfsense.py")
    p.set_defaults(verb=Verb(read=DnsAddArgs.read, func=cmd_dns_add))
    p = dns.add_parser("rm", parents=[mut], help="remove one host override, selected by name")
    p.add_argument("--name", required=True)
    p.set_defaults(verb=Verb(read=DnsRmArgs.read, func=cmd_dns_rm))

    table = sub.add_parser("table", parents=[mut], help="pf tables: snort2c, ISP aliases, anything else")
    table.add_argument("action", choices=["list", "show", "test", "del"])
    table.add_argument("table", nargs="?", help="table name (not needed for list)")
    table.add_argument("ips", nargs="*", help="addresses, for test and del")
    table.set_defaults(verb=Verb(read=TableArgs.read, func=cmd_table))

    snort = sub.add_parser("snort", help="Snort snort2c blocks").add_subparsers(dest="action", required=True)
    p = snort.add_parser("check", help="is a host/URL/IP blocked in snort2c?")
    p.add_argument("targets", nargs="+")
    p.set_defaults(verb=Verb(read=SnortCheckArgs.read, func=cmd_snort_check))
    p = snort.add_parser("why", help="which GID:SID blocked this IP (reads the rotated alert logs)")
    p.add_argument("ips", nargs="+")
    p.set_defaults(verb=Verb(read=IpsArgs.read, func=cmd_snort_why))
    p = snort.add_parser("unblock", parents=[mut], help="delete IPs from snort2c (temporary; suppress the SID too)")
    p.add_argument("ips", nargs="+")
    p.set_defaults(verb=Verb(read=IpsArgs.read, func=cmd_snort_unblock))
    p = snort.add_parser("verify", help="is the SID suppressed and the CIDR pass-listed, in the LIVE instance?")
    p.add_argument("--sid", required=True, metavar="GID:SID",
                   help="the rule as snort why prints it; a bare SID means gen_id 1")
    p.add_argument("--cidr", help="the pass-listed range; a scoped suppression must cover it too")
    p.add_argument("--ip", action="append", metavar="ADDRESS",
                   help="a blocked address a scoped suppression must cover (repeatable)")
    p.set_defaults(verb=Verb(read=SnortVerifyArgs.read, func=cmd_snort_verify))
    p = snort.add_parser("fixsteps", help="print the durable three-part fix")
    p.add_argument("--sid", required=True, metavar="GID:SID",
                   help="the rule as snort why prints it; a bare SID means gen_id 1")
    p.add_argument("--cidr")
    p.set_defaults(verb=Verb(read=SnortFixstepsArgs.read, func=cmd_snort_fixsteps))

    return ap


def _tolerate_unencodable_output() -> None:
    """Replace, rather than crash on, a character the console cannot encode.

    A Windows pipe defaults to cp1252, so a hostname or a snort message outside it raised
    UnicodeEncodeError in the middle of the report, with exit 1 - which here means "findings".
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: Sequence[str] | None = None, *, run: Runner = _run) -> int:
    _tolerate_unencodable_output()
    parsed = ParsedArgs(build_parser().parse_args(argv))
    common = CommonOptions.read(parsed, run)
    command = parsed.command()
    handler = parsed.handler()
    try:
        return handler.invoke(parsed, common)
    except (PfsenseError, ValueError) as exc:
        if common.json:
            print(json.dumps(Envelope(command=command, data={"error": str(exc)}, ok=False).to_json(), indent=2))
        print(f"pfsense: {exc}", file=sys.stderr)
        return 2
    except (OSError, subprocess.TimeoutExpired) as exc:
        if common.json:
            print(json.dumps(Envelope(command=command, data={"error": str(exc)}, ok=False).to_json(), indent=2))
        print(f"pfsense: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
