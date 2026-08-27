# /// script
# requires-python = ">=3.10"
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

Mutating verbs are dry-run until `--apply`. The four that edit config.xml (`dhcp rm`,
`dhcp rm-static-arp`, `dns add`, `dns rm`) snapshot it first. `table del` and `snort unblock`
change LIVE pf state, which a config.xml snapshot neither captures nor restores, so they take
none - re-add the entry to undo them:

    pfsense.py --fw home dns add --name nas.example.com --ip 192.0.2.10 --apply
    pfsense.py --fw home dhcp rm --mac 00:11:22:33:44:55 --apply

Audit a box, or a snapshot file with no network at all:

    pfsense.py --fw home doctor
    pfsense.py doctor --config configs/config-20260809.xml

Add `--json` for a machine-readable envelope (emitted on failure too).
Exit codes: 0 = yes/clean, 1 = well-formed no/findings, 2 = error.
"""
from __future__ import annotations

import argparse
import configparser
import csv
import io
import ipaddress
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

SNORT_TABLE = "snort2c"
MAGICDNS = "100.100.100.100"          # Tailscale's fixed MagicDNS address, the same on every tailnet
CONFIG_FILE = Path(os.environ.get("PFSENSE_JIG_CONFIG", "~/.config/bitranox/pfsense.ini")).expanduser()
UPGRADE_LOCK = "/var/run/pfSense-upgrade.lock"

# `snort -c <path>/snort.conf -i <if>`: the conf path is the only reliable pointer to the
# instance dir, because a previous interface assignment leaves a same-uuid dir behind.
_SNORT_CONF_RX = re.compile(r"\bsnort\b[^\n]*?-c\s+(\S+snort\.conf)")

# Field positions in a snort CSV alert line.
_A_TS, _A_SID, _A_MSG, _A_SRC, _A_DST = 0, 2, 4, 6, 8
_A_MIN_FIELDS = 10

# `? (192.0.2.10) at 00:11:22:33:44:55 on igb1 expires in 1200 seconds [ethernet]`
_ARP_RX = re.compile(r"\((?P<ip>[0-9.]+)\)\s+at\s+(?P<mac>[0-9a-fA-F:]+|\(incomplete\))\s+on\s+(?P<iface>\S+)(?P<rest>.*)")


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
    if re.search(r"<!DOCTYPE|<!ENTITY", text, re.I):
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
class Alert:
    """One parsed snort alert line."""

    timestamp: str
    sid: str
    message: str
    src: str
    dst: str


@dataclass(frozen=True)
class Finding:
    """One `doctor` result. `warn` means act on it; `info` is context."""

    check: str
    severity: str
    subject: str
    detail: str


# ---- target resolution --------------------------------------------------------------------------
def load_named_target(name: str, *, path: Path = CONFIG_FILE) -> Target:
    """Resolve `--fw <name>` from the user's own ini file.

    Named targets live in the USER's config, never in this repo: the tool ships publicly and must
    carry no host names. An ini file rather than toml so this works on 3.10, where tomllib is absent.
    """
    if not path.exists():
        raise PfsenseError(f"no target file at {path}; use --host, or create a [{name}] section there")
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    if name not in parser:
        known = ", ".join(s for s in parser.sections()) or "none"
        raise PfsenseError(f"no [{name}] section in {path} (defined: {known})")
    section = parser[name]
    host = section.get("host", "").strip()
    if not host:
        raise PfsenseError(f"[{name}] in {path} has no host=")
    return Target(
        host=host,
        user=section.get("user", "admin").strip(),
        ssh=section.get("ssh", "ssh").strip(),
        timeout=section.getint("timeout", 30),
    )


def build_ssh_argv(target: Target, command: str) -> list[str]:
    """The argv for one remote command.

    BatchMode is forced on when the caller did not set it: with only `-i <key>`, ssh falls back to
    a password PROMPT when the key is rejected, which hangs an unattended run instead of failing.
    """
    argv = shlex.split(target.ssh)
    if not any("BatchMode" in part for part in argv):
        argv += ["-o", "BatchMode=yes"]
    argv += [f"{target.user}@{target.host}", command]
    return argv


# ---- the one process seam -----------------------------------------------------------------------
def _run(argv: list[str], *, stdin_text: str | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """Execute argv and return (rc, stdout, stderr), never merged.

    This is the single seam the tests inject past. capture_output keeps the streams apart on
    purpose: everything the ssh client says about host keys and key exchange is stderr, and merging
    it into stdout is what corrupts parsed output.
    """
    proc = subprocess.run(argv, input=stdin_text, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def run_remote(target: Target, command: str, *, run=_run, stdin_text: str | None = None,
               timeout: int | None = None) -> tuple[int, str, str]:
    """One remote command. Returns (rc, stdout, stderr) with the streams still separate."""
    return run(build_ssh_argv(target, command), stdin_text=stdin_text, timeout=timeout or target.timeout)


def run_php(target: Target, php_body: str, *, run=_run, timeout: int | None = None) -> object:
    """Run PHP against the live config API and decode the JSON it echoes.

    The source goes over STDIN, so no part of it is ever parsed by the local shell, the remote
    shell, or php's own -r argument handling. That is what removes the quoting layer that mangles
    a hand-rolled `php -r "..."` into plausible-but-wrong output.
    """
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
    """The IPs in a `pfctl -t <table> -T show` dump (it indents every entry)."""
    return {line.strip() for line in text.splitlines() if line.strip()}


def blocked_among(table_text: str, ips: list[str]) -> list[str]:
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
        if len(row) < _A_MIN_FIELDS or not row[_A_SID].strip().isdigit():
            continue
        alert = Alert(
            timestamp=row[_A_TS].strip(),
            sid=row[_A_SID].strip(),
            message=row[_A_MSG].strip(),
            src=row[_A_SRC].strip(),
            dst=row[_A_DST].strip(),
        )
        if ip is None or ip in (alert.src, alert.dst):
            alerts.append(alert)
    return alerts


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
    return sorted({info[4][0] for info in infos})


def normalize_mac(mac: str) -> str:
    """Lowercase colon-separated form, so `00-11-22-33-44-55` and `00:11:22:33:44:55` match."""
    cleaned = re.sub(r"[^0-9a-fA-F]", "", mac).lower()
    if len(cleaned) != 12:
        raise PfsenseError(f"not a MAC address: {mac}")
    return ":".join(cleaned[i:i + 2] for i in range(0, 12, 2))


def parse_arp(text: str) -> list[dict]:
    """Parse `arp -an`, marking permanent entries.

    A permanent entry is the fingerprint of a DHCP reservation with static ARP ticked, which is
    the fault that answers for a device on an interface that is down.
    """
    entries = []
    for line in text.splitlines():
        match = _ARP_RX.search(line)
        if not match:
            continue
        mac = match.group("mac")
        entries.append({
            "ip": match.group("ip"),
            "mac": "" if mac.startswith("(") else normalize_mac(mac),
            "interface": match.group("iface"),
            "permanent": "permanent" in match.group("rest"),
        })
    return entries


def select_one(items: list[dict], key: str, value: str, *, what: str) -> dict:
    """The single item whose `key` equals `value`; refuse on no match AND on ambiguity.

    Selection is by stable text, never by position: an index taken from a listing shifts the moment
    anything before it is removed, so a second command from the same listing hits the wrong row and
    still exits 0.
    """
    hits = [item for item in items if str(item.get(key, "")).lower() == value.lower()]
    if not hits:
        raise PfsenseError(f"no {what} with {key}={value}")
    if len(hits) > 1:
        raise PfsenseError(f"{len(hits)} {what} entries share {key}={value}; refusing to guess which")
    return hits[0]


def _is_loopback(address: str) -> str | bool:
    """Whether a nameserver entry points back at this host, in either address family."""
    return address.startswith("127.") or address in ("::1", "0:0:0:0:0:0:0:1")


def override_name(entry: dict) -> str:
    """The fully qualified name of a host override, tolerating an empty host part."""
    host, domain = (entry.get("host") or "").strip(), (entry.get("domain") or "").strip()
    return f"{host}.{domain}" if host else domain


# ---- offline config parsing ---------------------------------------------------------------------
def reservations_from_config_xml(text: str) -> list[dict]:
    """DHCP reservations read straight out of a config.xml snapshot.

    Offline parsing exists so `doctor` can audit a saved snapshot with no network, and so its
    checks can be proven able to FAIL against a config known to contain the fault.
    """
    root = parse_xml(text)
    out = []
    for dhcpd in root.findall("dhcpd"):
        for iface in dhcpd:
            for entry in iface.findall("staticmap"):
                out.append({
                    "interface": iface.tag,
                    "mac": (entry.findtext("mac") or "").strip().lower(),
                    "ip": (entry.findtext("ipaddr") or "").strip(),
                    "hostname": (entry.findtext("hostname") or "").strip(),
                    "descr": (entry.findtext("descr") or "").strip(),
                    "static_arp": entry.find("arp_table_static_entry") is not None,
                })
    return out


def overrides_from_config_xml(text: str) -> list[dict]:
    """DNS host overrides from a snapshot. The element is `hosts`, not `hostoverride`."""
    root = parse_xml(text)
    unbound = root.find("unbound")
    if unbound is None:
        return []
    return [{
        "host": (entry.findtext("host") or "").strip(),
        "domain": (entry.findtext("domain") or "").strip(),
        "ip": (entry.findtext("ip") or "").strip(),
        "descr": (entry.findtext("descr") or "").strip(),
    } for entry in unbound.findall("hosts")]


# ---- doctor: pure checks over plain data --------------------------------------------------------
def doctor_findings(*, reservations: list[dict], overrides: list[dict],
                    arp: list[dict] | None = None, resolv_conf: str | None = None,
                    upgrade_lock: bool | None = None) -> list[Finding]:
    """Every audit check, as pure logic over plain data.

    Each one is a fault that raises no error of its own and so goes unnoticed: they were all found
    the expensive way, by chasing a symptom that pointed somewhere else entirely.
    """
    findings: list[Finding] = []

    # One address reserved for several MACs is the NORMAL way to give a wired/wireless device a
    # single identity, so it is context, not a fault. It matters only because it is the precondition
    # for the static-ARP fault below: reporting it as a problem on its own cries wolf on a healthy
    # config (measured: 5 warnings on a config with nothing wrong with it).
    by_ip: dict[str, list[dict]] = {}
    for res in reservations:
        if res.get("ip"):
            by_ip.setdefault(res["ip"], []).append(res)

    for res in reservations:
        if res.get("static_arp"):
            shared = len(by_ip.get(res.get("ip", ""), []))
            extra = (f" This address is reserved for {shared} MACs, which is exactly the case that "
                     f"breaks: the firewall pins one of them permanently." if shared > 1 else "")
            findings.append(Finding(
                check="static_arp_armed", severity="warn",
                subject=f"{res.get('ip','?')} {res.get('mac','?')} {res.get('hostname') or res.get('descr') or ''}".strip(),
                detail="ARP Table Static Entry is ticked. On a device with more than one interface "
                       "the firewall answers for whichever one is down: reachable inside its subnet, "
                       "dead beyond it, and nothing logs an error." + extra,
            ))

    for ip, group in sorted(by_ip.items()):
        if len(group) > 1:
            findings.append(Finding(
                check="shared_ip_multi_mac", severity="info", subject=ip,
                detail="reserved for " + str(len(group)) + " MACs (" +
                       ", ".join(r.get("mac", "?") for r in group) +
                       "). Normal for a device with wired and wireless interfaces; only a problem "
                       "if static ARP is also ticked.",
            ))

    # ARP is used for POSITIVE evidence only: it is a cache that expires after minutes of silence,
    # so absence means "not seen lately", never "gone". An earlier version drew conclusions from
    # absence and reported 22 healthy hosts as possibly-gone on a network with nothing wrong with
    # it, which is the kind of noise that trains people to stop reading the output. The DHCP lease
    # file cannot rescue that check either: ISC dhcpd writes no lease for a fixed-address
    # reservation, so a reserved device leaves no trace there whether it is present or not.
    if arp is not None:
        macs_for_ip: dict[str, set[str]] = {}
        for res in reservations:
            if res.get("ip"):
                macs_for_ip.setdefault(res["ip"], set()).add(res.get("mac", ""))
        for entry in arp:
            reserved_macs = macs_for_ip.get(entry["ip"])
            if entry.get("mac") and reserved_macs and entry["mac"] not in reserved_macs:
                findings.append(Finding(
                    check="reservation_mac_mismatch", severity="warn",
                    subject=f"{entry['ip']} reserved for {', '.join(sorted(reserved_macs))}, held by {entry['mac']}",
                    detail="the address is in use by hardware no reservation for it names. If the "
                           "reserved device reappears, DHCP hands it an address something else "
                           "already holds, which shows up as an intermittent outage that is hard "
                           "to trace. Usually it means the reservation outlived the device.",
                ))

    # A healthy pfSense resolv.conf lists the box's own resolver FIRST and then the configured
    # upstream servers as fallbacks, so "every entry is loopback" is the wrong test - it flags a
    # correct box. The fault has two distinct signatures, checked separately.
    if resolv_conf is not None:
        servers = re.findall(r"^\s*nameserver\s+(\S+)", resolv_conf, re.M)
        if MAGICDNS in servers:
            findings.append(Finding(
                check="magicdns_in_resolv_conf", severity="warn", subject=MAGICDNS,
                detail="Tailscale's 'Accept DNS' has rewritten /etc/resolv.conf to MagicDNS. When "
                       "the tailnet has no global nameservers the box then resolves no public name "
                       "at all, so pkg and system upgrades fail while LAN clients stay fine because "
                       "they query the resolver directly - which is why this hides for months. Turn "
                       "Accept DNS off, and forward the tailnet's domain to MagicDNS with an unbound "
                       "domain override instead: that keeps tailnet names resolving without handing "
                       "over the system resolver.",
            ))
        elif servers and not _is_loopback(servers[0]):
            findings.append(Finding(
                check="resolver_not_first", severity="warn", subject=servers[0],
                detail="the first nameserver is not this firewall's own resolver, so the box does "
                       "not answer its own queries from unbound. Upstream servers listed AFTER "
                       "loopback are normal fallbacks and are not a fault.",
            ))

    if upgrade_lock:
        findings.append(Finding(
            check="upgrade_lock_present", severity="warn", subject=UPGRADE_LOCK,
            detail="a pfSense-upgrade lock is present, so every package operation reports "
                   "'Another instance of pfSense-upgrade is running'. If no upgrade is actually "
                   "running, the lock is stale and the file can be removed.",
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
}} else {{
    $removed = array();
}}
echo json_encode(array("removed" => $removed));
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
def envelope(*, command: str, data: object, ok: bool, skipped: list[str] | None = None) -> dict:
    """The machine-readable result envelope."""
    return {"ok": ok, "command": command, "data": data, "skipped": skipped or []}


def _emit(result: dict, as_json: bool, human: str) -> None:
    """Data to stdout. Diagnostics never travel this path; they go to stderr."""
    print(json.dumps(result, indent=2) if as_json else human)


def _target_from_args(args) -> Target:
    if getattr(args, "fw", None):
        return load_named_target(args.fw)
    if not getattr(args, "host", None):
        raise PfsenseError("no target: pass --host, or --fw <name> with a section in " + str(CONFIG_FILE))
    return Target(host=args.host, user=args.user, ssh=args.ssh, timeout=args.timeout)


def _guard_mutation(args, target: Target, what: str) -> str | None:
    """Snapshot before an --apply, and describe the intent when it is a dry run.

    Returns the snapshot path, or None for a dry run. A mutation whose snapshot failed does not
    proceed: the point of the snapshot is to make the change reversible, so a missing one removes
    the only reason it was safe to go ahead.
    """
    if not args.apply:
        return None
    path = do_snapshot(target, Path(args.snapshot_dir or default_snapshot_dir()),
                       run=args.run, allow_repo=getattr(args, "allow_repo_snapshot", False))
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


def inside_git_worktree(directory: Path, *, run=_run) -> bool:
    """True when `directory` sits inside a git work tree. False when git cannot answer.

    Fail-open by design: this is the SECOND layer, behind a default that already points outside any
    checkout. A machine with no git must still be able to take a snapshot.
    """
    import shutil  # noqa: PLC0415 - only needed on this path, and only to probe for git
    if not shutil.which("git"):
        return False
    try:
        rc, out, _err = run(["git", "-C", str(directory), "rev-parse", "--is-inside-work-tree"],
                            timeout=10)
    except Exception:
        return False
    return rc == 0 and (out or "").strip() == "true"


def prepare_snapshot_dir(directory: Path, *, allow_repo: bool = False, run=_run) -> Path:
    """Create `directory` private to the user, refusing a git work tree unless told otherwise."""
    directory = Path(directory).expanduser()
    if not allow_repo and directory.exists() and inside_git_worktree(directory, run=run):
        raise PfsenseError(
            f"{directory} is inside a git work tree, and a snapshot is a live config.xml with "
            f"password hashes and private keys in it. Pass --snapshot-dir to send it somewhere "
            f"private (default {default_snapshot_dir()}), or --allow-repo-snapshot to override."
        )
    directory.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        os.chmod(directory, 0o700)
    return directory


def do_snapshot(target: Target, directory: Path, *, run=_run, allow_repo: bool = False) -> Path:
    """Fetch /conf/config.xml and write it under a timestamped name.

    The content is validated before it is written: an ssh failure or a truncated read must not be
    saved as a snapshot, because a snapshot nobody can restore from is worse than none at all.
    """
    # Resolve the destination BEFORE fetching: a refusal should cost nothing, and there is no
    # reason to pull 180 KB of credentials over the wire only to decline to write it.
    directory = prepare_snapshot_dir(directory, allow_repo=allow_repo, run=run)
    rc, out, err = run_remote(target, "cat /conf/config.xml", run=run, timeout=max(target.timeout, 60))
    if rc != 0:
        raise PfsenseError(f"could not read /conf/config.xml from {target.host}: {err.strip()[:200]}")
    root = parse_xml(out)
    if root.tag != "pfsense":
        raise PfsenseError(f"root element is <{root.tag}>, not <pfsense>; refusing to save it")
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    path = directory / f"config-{target.host}-{stamp}.xml"
    path.write_text(out, encoding="utf-8")
    return path


# ---- commands -----------------------------------------------------------------------------------
def cmd_info(args) -> int:
    target = _target_from_args(args)
    data = run_php(target, php_info(), run=args.run)
    lines = [
        f"  version:      {data['version']}",
        f"  dhcp backend: {data['dhcp_backend']}",
        f"  resolver:     {data['resolver']}",
        "  interfaces:",
    ]
    for iface in data["interfaces"]:
        lines.append(f"    {iface['name']:<8} {iface['if']:<12} {iface['ipaddr']}/{iface['subnet']}  {iface['descr']}")
    pkgs = ", ".join(p["name"] for p in data["packages"]) or "none"
    lines.append(f"  packages:     {pkgs}")
    _emit(envelope(command="info", data=data, ok=True), args.json, "\n".join(lines))
    return 0


def cmd_snapshot(args) -> int:
    target = _target_from_args(args)
    path = do_snapshot(target, Path(args.dir or default_snapshot_dir()), run=args.run)
    _emit(envelope(command="snapshot", data={"path": str(path), "bytes": path.stat().st_size}, ok=True),
          args.json, f"  saved {path} ({path.stat().st_size} bytes)")
    return 0


def cmd_dhcp_list(args) -> int:
    target = _target_from_args(args)
    reservations = run_php(target, php_list_reservations(), run=args.run)
    lines = [f"  {r['ip']:<16} {r['mac']:<18} {'STATIC-ARP' if r['static_arp'] else '          '}  "
             f"{r['hostname'] or r['descr']}" for r in reservations]
    lines.append(f"  ({len(reservations)} reservations)")
    _emit(envelope(command="dhcp list", data=reservations, ok=True), args.json, "\n".join(lines))
    return 0


def cmd_dhcp_rm(args) -> int:
    target = _target_from_args(args)
    mac = normalize_mac(args.mac)
    reservations = run_php(target, php_list_reservations(), run=args.run)
    entry = select_one(reservations, "mac", mac, what="reservation")
    if not args.apply:
        _emit(envelope(command="dhcp rm", data={"would_remove": entry}, ok=True, skipped=["--apply not given"]),
              args.json, f"  DRY RUN: would remove {entry['ip']} {entry['mac']} "
                         f"({entry['hostname'] or entry['descr']}).  Re-run with --apply.")
        return 0
    _guard_mutation(args, target, f"removing the reservation for {mac}")
    result = run_php(target, php_rm_reservation(mac), run=args.run)
    removed = result.get("removed") or []
    _emit(envelope(command="dhcp rm", data=result, ok=bool(removed)), args.json,
          f"  removed {len(removed)} reservation(s) for {mac}")
    return 0 if removed else 1


def cmd_dhcp_rm_static_arp(args) -> int:
    target = _target_from_args(args)
    mac = normalize_mac(args.mac)
    reservations = run_php(target, php_list_reservations(), run=args.run)
    entry = select_one(reservations, "mac", mac, what="reservation")
    if not entry["static_arp"]:
        _emit(envelope(command="dhcp rm-static-arp", data={"entry": entry}, ok=True,
                       skipped=["static ARP was not set"]),
              args.json, f"  {entry['ip']} {mac} does not have static ARP set; nothing to do.")
        return 0
    if not args.apply:
        _emit(envelope(command="dhcp rm-static-arp", data={"would_clear": entry}, ok=True,
                       skipped=["--apply not given"]),
              args.json, f"  DRY RUN: would clear static ARP on {entry['ip']} {mac}.  Re-run with --apply.")
        return 0
    _guard_mutation(args, target, f"clearing static ARP for {mac}")
    result = run_php(target, php_rm_static_arp(mac), run=args.run)
    changed = result.get("changed") or []
    _emit(envelope(command="dhcp rm-static-arp", data=result, ok=bool(changed)), args.json,
          f"  cleared static ARP on {len(changed)} reservation(s) for {mac}")
    return 0 if changed else 1


def cmd_dns_list(args) -> int:
    target = _target_from_args(args)
    overrides = run_php(target, php_list_overrides(), run=args.run)
    lines = [f"  {override_name(o):<44} -> {o['ip']}" for o in overrides]
    lines.append(f"  ({len(overrides)} host overrides)")
    _emit(envelope(command="dns list", data=overrides, ok=True), args.json, "\n".join(lines))
    return 0


def _split_name(name: str) -> tuple[str, str]:
    """Split a fully qualified name into the host and domain parts pfSense stores separately."""
    parts = name.strip().strip(".").split(".", 1)
    if len(parts) != 2 or not parts[1]:
        raise PfsenseError(f"{name} is not a fully qualified name (needs a host and a domain part)")
    return parts[0].lower(), parts[1].lower()


def cmd_dns_add(args) -> int:
    target = _target_from_args(args)
    host, domain = _split_name(args.name)
    ipaddress.ip_address(args.ip)
    if not args.apply:
        _emit(envelope(command="dns add", data={"would_add": {"host": host, "domain": domain, "ip": args.ip}},
                       ok=True, skipped=["--apply not given"]),
              args.json, f"  DRY RUN: would add {host}.{domain} -> {args.ip}.  Re-run with --apply.")
        return 0
    _guard_mutation(args, target, f"adding {host}.{domain}")
    result = run_php(target, php_add_override(host, domain, args.ip, args.descr), run=args.run)
    if result.get("error"):
        raise PfsenseError(str(result["error"]))
    _emit(envelope(command="dns add", data=result, ok=True), args.json, f"  added {host}.{domain} -> {args.ip}")
    return 0


def cmd_dns_rm(args) -> int:
    target = _target_from_args(args)
    host, domain = _split_name(args.name)
    overrides = run_php(target, php_list_overrides(), run=args.run)
    named = [dict(o, fqdn=override_name(o)) for o in overrides]
    entry = select_one(named, "fqdn", f"{host}.{domain}", what="host override")
    if not args.apply:
        _emit(envelope(command="dns rm", data={"would_remove": entry}, ok=True, skipped=["--apply not given"]),
              args.json, f"  DRY RUN: would remove {entry['fqdn']} -> {entry['ip']}.  Re-run with --apply.")
        return 0
    _guard_mutation(args, target, f"removing {host}.{domain}")
    result = run_php(target, php_rm_override(host, domain), run=args.run)
    removed = result.get("removed") or []
    _emit(envelope(command="dns rm", data=result, ok=bool(removed)), args.json,
          f"  removed {len(removed)} override(s) for {host}.{domain}")
    return 0 if removed else 1


def cmd_arp(args) -> int:
    target = _target_from_args(args)
    rc, out, err = run_remote(target, "arp -an", run=args.run)
    if rc != 0:
        raise PfsenseError(f"could not read the ARP table on {target.host}: {err.strip()[:200]}")
    entries = parse_arp(out)
    if args.permanent:
        entries = [e for e in entries if e["permanent"]]
    lines = [f"  {e['ip']:<16} {e['mac'] or '(incomplete)':<18} {e['interface']:<8} "
             f"{'PERMANENT' if e['permanent'] else ''}" for e in entries]
    lines.append(f"  ({len(entries)} entries)")
    _emit(envelope(command="arp", data=entries, ok=True), args.json, "\n".join(lines))
    return 0


def cmd_table(args) -> int:
    target = _target_from_args(args)
    if args.action == "list":
        rc, out, err = run_remote(target, "pfctl -sT", run=args.run)
        if rc != 0:
            raise PfsenseError(f"could not list pf tables: {err.strip()[:200]}")
        names = [line.strip() for line in out.splitlines() if line.strip()]
        _emit(envelope(command="table list", data=names, ok=True), args.json,
              "\n".join(f"  {n}" for n in names) + f"\n  ({len(names)} tables)")
        return 0

    if args.action == "show":
        rc, out, err = run_remote(target, f"pfctl -t {shlex.quote(args.table)} -T show", run=args.run)
        if rc != 0:
            raise PfsenseError(f"could not read table {args.table}: {err.strip()[:200]}")
        ips = sorted(parse_table(out))
        _emit(envelope(command="table show", data=ips, ok=True), args.json,
              "\n".join(f"  {ip}" for ip in ips) + f"\n  ({len(ips)} entries in {args.table})")
        return 0

    if args.action == "test":
        rc, out, err = run_remote(target, f"pfctl -t {shlex.quote(args.table)} -T show", run=args.run)
        if rc != 0:
            raise PfsenseError(f"could not read table {args.table}: {err.strip()[:200]}")
        present = blocked_among(out, args.ips)
        data = {"table": args.table, "present": present,
                "absent": [ip for ip in args.ips if ip not in present]}
        _emit(envelope(command="table test", data=data, ok=bool(present)), args.json,
              "\n".join(f"  {'IN ' if ip in present else 'not'}  {ip}  ({args.table})" for ip in args.ips))
        return 0 if present else 1

    # del
    if not args.apply:
        _emit(envelope(command="table del", data={"would_delete": args.ips, "table": args.table},
                       ok=True, skipped=["--apply not given"]),
              args.json, f"  DRY RUN: would delete {', '.join(args.ips)} from {args.table}.  Re-run with --apply.")
        return 0
    for ip in args.ips:
        run_remote(target, f"pfctl -t {shlex.quote(args.table)} -T delete {shlex.quote(ip)}", run=args.run)
    rc, out, err = run_remote(target, f"pfctl -t {shlex.quote(args.table)} -T show", run=args.run)
    if rc != 0:
        raise PfsenseError(f"could not re-read table {args.table} to confirm: {err.strip()[:200]}")
    still = blocked_among(out, args.ips)
    _emit(envelope(command="table del", data={"requested": args.ips, "still_present": still}, ok=not still),
          args.json, f"  deleted {len(args.ips) - len(still)} of {len(args.ips)} from {args.table}" +
                     (f"\n  STILL PRESENT: {', '.join(still)}" if still else ""))
    return 1 if still else 0


def cmd_rules(args) -> int:
    target = _target_from_args(args)
    command = "pfctl -vvsr" if args.counters else ("pfctl -sn" if args.nat else "pfctl -sr")
    rc, out, err = run_remote(target, command, run=args.run, timeout=max(target.timeout, 60))
    if rc != 0:
        raise PfsenseError(f"could not read the ruleset: {err.strip()[:200]}")
    rules = [line.rstrip() for line in out.splitlines() if line.strip()]
    _emit(envelope(command="rules", data=rules, ok=True), args.json, "\n".join(rules))
    return 0


def cmd_snort_check(args) -> int:
    target = _target_from_args(args)
    resolved: dict[str, list[str]] = {}
    for name in args.targets:
        try:
            resolved[name] = resolve_ips(name)
        except OSError as exc:
            raise PfsenseError(f"cannot resolve {name}: {exc}") from exc
    every_ip = [ip for ips in resolved.values() for ip in ips]

    rc, table, err = run_remote(target, f"pfctl -t {SNORT_TABLE} -T show", run=args.run)
    if rc != 0:
        raise PfsenseError(f"could not read the {SNORT_TABLE} table on {target.host} "
                           f"(is Snort installed?): {err.strip()[:200]}")

    blocked = blocked_among(table, every_ip)
    data = {"resolved": resolved, "blocked": blocked,
            "clear": [ip for ip in every_ip if ip not in blocked]}
    lines = []
    for name, ips in resolved.items():
        for ip in ips:
            lines.append(f"  {'BLOCKED' if ip in blocked else 'clear  '}  {ip}  ({name})")
    if blocked:
        lines.append("")
        lines.append(f"Next: pfsense.py snort why {blocked[0]}   then snort fixsteps --sid <SID>")
    _emit(envelope(command="snort check", data=data, ok=not blocked), args.json, "\n".join(lines))
    return 1 if blocked else 0


def cmd_snort_why(args) -> int:
    target = _target_from_args(args)
    # The alert files ROTATE, so read the whole set: a block laid down yesterday is not in the
    # current file. Read once for every IP rather than per IP - these logs are large.
    rc, out, err = run_remote(target, "cat /var/log/snort/*/alert /var/log/snort/*/alert.* 2>/dev/null",
                              run=args.run, timeout=max(target.timeout, 60))
    if rc != 0 and not out:
        raise PfsenseError(f"could not read the snort alert logs on {target.host}: {err.strip()[:200]}")
    found = {ip: [asdict(a) for a in parse_alerts(out, ip=ip)] for ip in args.ips}

    lines = []
    for ip, alerts in found.items():
        if not alerts:
            lines.append(f"  {ip}: no alert names this IP (the block may come from a reputation feed)")
            continue
        sids = sorted({a["sid"] for a in alerts})
        lines.append(f"  {ip}: {len(alerts)} alert(s), SID(s) {', '.join(sids)}")
        lines.append(f"      latest: {alerts[-1]['timestamp']}  {alerts[-1]['message']}")
    any_found = any(found.values())
    _emit(envelope(command="snort why", data=found, ok=any_found), args.json, "\n".join(lines))
    return 0 if any_found else 1


def cmd_snort_unblock(args) -> int:
    target = _target_from_args(args)
    if not args.apply:
        _emit(envelope(command="snort unblock", data={"would_delete": args.ips}, ok=True,
                       skipped=["--apply not given"]),
              args.json, f"  DRY RUN: would delete {', '.join(args.ips)} from {SNORT_TABLE}.  Re-run with --apply.")
        return 0
    for ip in args.ips:
        run_remote(target, f"pfctl -t {SNORT_TABLE} -T delete {shlex.quote(ip)}", run=args.run)
    rc, table, err = run_remote(target, f"pfctl -t {SNORT_TABLE} -T show", run=args.run)
    if rc != 0:
        raise PfsenseError(f"could not re-read the table to confirm: {err.strip()[:200]}")
    still = blocked_among(table, args.ips)
    data = {"requested": args.ips, "still_blocked": still}
    human = "  cleared: " + ", ".join(ip for ip in args.ips if ip not in still)
    if still:
        human += f"\n  STILL BLOCKED: {', '.join(still)}"
    human += ("\n\nThis is temporary. Clearing the table does NOT stop the rule re-adding the "
              "address on the next packet: suppress the SID too, with snort fixsteps --sid <SID>.")
    _emit(envelope(command="snort unblock", data=data, ok=not still), args.json, human)
    return 1 if still else 0


def cmd_snort_verify(args) -> int:
    target = _target_from_args(args)
    rc, ps_out, _ = run_remote(target, "ps auxww", run=args.run)
    instance = instance_dir_from_ps(ps_out) if rc == 0 else None
    if not instance:
        raise PfsenseError(f"snort does not appear to be running on {target.host}")

    checks: dict[str, object] = {"instance_dir": instance}
    # The SUPPRESSION file carries the SID.
    _, supp, _ = run_remote(target, f"cat {instance}/supp* 2>/dev/null", run=args.run)
    checks["sid_suppressed"] = bool(re.search(rf"sig_id\s+{re.escape(args.sid)}\b", supp))

    if args.cidr:
        # The GENERATED PASS LIST only. Never grep the suppression file for this: its comments
        # name the same addresses, so the match would be vacuous and always "pass".
        _, passlist, _ = run_remote(target, f"cat {instance}/*Whitelist* 2>/dev/null", run=args.run)
        entries = {line.strip() for line in passlist.splitlines() if line.strip()}
        checks["cidr_passlisted"] = args.cidr in entries
        checks["passlist_entries"] = len(entries)

    ok = bool(checks["sid_suppressed"]) and (not args.cidr or bool(checks.get("cidr_passlisted")))
    human = "\n".join(
        [f"  live instance: {instance}",
         f"  sid {args.sid} suppressed: {'yes' if checks['sid_suppressed'] else 'NO'}"]
        + ([f"  {args.cidr} in pass list: {'yes' if checks.get('cidr_passlisted') else 'NO'}"] if args.cidr else [])
    )
    _emit(envelope(command="snort verify", data=checks, ok=ok), args.json, human)
    return 0 if ok else 1


def fix_steps(*, sid: str, cidr: str | None = None) -> str:
    """The durable three-part fix, spelled out for a human to apply and review.

    Deliberately NOT automated: it edits the firewall's config.xml, which is a reviewed change.
    What this does is make sure none of the three parts is forgotten, because doing only the
    obvious one (clearing the table) is the dirty patch that lets it recur within hours.
    """
    range_line = cidr or "<the destination range, e.g. 198.51.100.0/22>"
    return "\n".join([
        "Durable fix (all three parts, or it recurs):",
        "",
        f"  1. Suppress the rule: add 'suppress gen_id 1, sig_id {sid}' to the WAN suppression",
        "     list (Services > Snort > Pass Lists / Suppress, or config.xml).",
        "",
        f"  2. Pass-list the range: add {range_line} as a LITERAL <item> in the Snort pass list",
        "     entry's <address>. Do NOT add it to a firewall ALIAS: an alias entry there is a",
        "     NO-OP, because snort_build_list expands it via filter_generate_nested_alias, which",
        "     returns empty unless $aliastable was built by a filter run in the same PHP process,",
        "     and then writes the literal alias NAME into the generated list.",
        "",
        "  3. Clear what is already blocked - suppressing does not flush the table:",
        f"     pfsense.py snort unblock <ip> ... --apply",
        "",
        "Then resync Snort so the files are regenerated, and verify with:",
        f"  pfsense.py snort verify --sid {sid}" + (f" --cidr {cidr}" if cidr else ""),
    ])


def cmd_snort_fixsteps(args) -> int:
    steps = fix_steps(sid=args.sid, cidr=args.cidr)
    _emit(envelope(command="snort fixsteps", data={"sid": args.sid, "cidr": args.cidr, "steps": steps}, ok=True),
          args.json, steps)
    return 0


def cmd_doctor(args) -> int:
    if args.config:
        text = Path(args.config).read_text(encoding="utf-8")
        findings = doctor_findings(reservations=reservations_from_config_xml(text),
                                   overrides=overrides_from_config_xml(text))
        source = args.config
    else:
        target = _target_from_args(args)
        reservations = run_php(target, php_list_reservations(), run=args.run)
        overrides = run_php(target, php_list_overrides(), run=args.run)
        _, arp_out, _ = run_remote(target, "arp -an", run=args.run)
        _, resolv, _ = run_remote(target, "cat /etc/resolv.conf", run=args.run)
        rc_lock, _, _ = run_remote(target, f"test -f {UPGRADE_LOCK}", run=args.run)
        findings = doctor_findings(reservations=reservations, overrides=overrides,
                                   arp=parse_arp(arp_out), resolv_conf=resolv,
                                   upgrade_lock=(rc_lock == 0))
        source = target.host

    warns = [f for f in findings if f.severity == "warn"]
    lines = [f"  {source}:"]
    for finding in findings:
        lines.append(f"  [{finding.severity.upper():<4}] {finding.check}: {finding.subject}")
        lines.append(f"         {finding.detail}")
    lines.append(f"  ({len(warns)} to act on, {len(findings) - len(warns)} informational)")
    _emit(envelope(command="doctor", data=[asdict(f) for f in findings], ok=not warns),
          args.json, "\n".join(lines))
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
                        help="permit writing a snapshot inside a git work tree")
    return common


def build_parser() -> argparse.ArgumentParser:
    mut = _mutation_flags()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", help="firewall host or address (no default: name the box you mean)")
    ap.add_argument("--fw", help=f"named target from {CONFIG_FILE}")
    ap.add_argument("--user", default="admin", help="ssh user (default admin)")
    ap.add_argument("--ssh", default="ssh", help='ssh command, e.g. "ssh -i /key -o BatchMode=yes"')
    ap.add_argument("--timeout", type=int, default=30, help="per-command ssh timeout in seconds")
    ap.add_argument("--json", action="store_true", help="emit the machine-readable envelope")
    ap.add_argument("--apply", action="store_true", help="actually make the change (default is a dry run)")
    ap.add_argument("--snapshot-dir", default=None,
                    help=f"where a pre-change snapshot is written "
                         f"(default {default_snapshot_dir()}, mode 0700)")
    ap.add_argument("--allow-repo-snapshot", action="store_true",
                    help="permit writing a snapshot inside a git work tree (refused by default)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="version, DHCP backend, resolver, interfaces, packages").set_defaults(func=cmd_info)

    p = sub.add_parser("snapshot", help="save /conf/config.xml under a timestamped name")
    p.add_argument("--dir", default=None,
                   help="destination directory (default: a private per-user "
                        "state dir, never the current directory)")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("arp", help="the ARP table, flagging permanent entries")
    p.add_argument("--permanent", action="store_true", help="only the permanent entries")
    p.set_defaults(func=cmd_arp)

    p = sub.add_parser("rules", help="the live pf ruleset")
    p.add_argument("--counters", action="store_true", help="include per-rule counters (pfctl -vvsr)")
    p.add_argument("--nat", action="store_true", help="show NAT rules instead (pfctl -sn)")
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("doctor", help="audit for the faults that raise no error of their own")
    p.add_argument("--config", help="audit a saved config.xml offline instead of a live box")
    p.set_defaults(func=cmd_doctor)

    dhcp = sub.add_parser("dhcp", help="DHCP reservations").add_subparsers(dest="action", required=True)
    dhcp.add_parser("list", help="every reservation, with the static-ARP flag").set_defaults(func=cmd_dhcp_list)
    p = dhcp.add_parser("rm", parents=[mut], help="delete one reservation, selected by MAC")
    p.add_argument("--mac", required=True)
    p.set_defaults(func=cmd_dhcp_rm)
    p = dhcp.add_parser("rm-static-arp", parents=[mut], help="clear ARP Table Static Entry, keeping the reservation")
    p.add_argument("--mac", required=True)
    p.set_defaults(func=cmd_dhcp_rm_static_arp)

    dns = sub.add_parser("dns", help="unbound host overrides").add_subparsers(dest="action", required=True)
    dns.add_parser("list", help="every host override").set_defaults(func=cmd_dns_list)
    p = dns.add_parser("add", parents=[mut], help="add one host override")
    p.add_argument("--name", required=True, help="fully qualified, e.g. nas.example.com")
    p.add_argument("--ip", required=True)
    p.add_argument("--descr", default="added by pfsense.py")
    p.set_defaults(func=cmd_dns_add)
    p = dns.add_parser("rm", parents=[mut], help="remove one host override, selected by name")
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_dns_rm)

    table = sub.add_parser("table", parents=[mut], help="pf tables: snort2c, ISP aliases, anything else")
    table.add_argument("action", choices=["list", "show", "test", "del"])
    table.add_argument("table", nargs="?", help="table name (not needed for list)")
    table.add_argument("ips", nargs="*", help="addresses, for test and del")
    table.set_defaults(func=cmd_table)

    snort = sub.add_parser("snort", help="Snort snort2c blocks").add_subparsers(dest="action", required=True)
    p = snort.add_parser("check", help="is a host/URL/IP blocked in snort2c?")
    p.add_argument("targets", nargs="+")
    p.set_defaults(func=cmd_snort_check)
    p = snort.add_parser("why", help="which SID blocked this IP (reads the rotated alert logs)")
    p.add_argument("ips", nargs="+")
    p.set_defaults(func=cmd_snort_why)
    p = snort.add_parser("unblock", parents=[mut], help="delete IPs from snort2c (temporary; suppress the SID too)")
    p.add_argument("ips", nargs="+")
    p.set_defaults(func=cmd_snort_unblock)
    p = snort.add_parser("verify", help="is the SID suppressed and the CIDR pass-listed, in the LIVE instance?")
    p.add_argument("--sid", required=True)
    p.add_argument("--cidr")
    p.set_defaults(func=cmd_snort_verify)
    p = snort.add_parser("fixsteps", help="print the durable three-part fix")
    p.add_argument("--sid", required=True)
    p.add_argument("--cidr")
    p.set_defaults(func=cmd_snort_fixsteps)

    return ap


def main(argv=None, *, run=_run) -> int:
    args = build_parser().parse_args(argv)
    args.run = run
    command = " ".join(part for part in [args.cmd, getattr(args, "action", None)] if part)
    try:
        return args.func(args)
    except (PfsenseError, ValueError) as exc:
        if args.json:
            print(json.dumps(envelope(command=command, data={"error": str(exc)}, ok=False), indent=2))
        print(f"pfsense: {exc}", file=sys.stderr)
        return 2
    except (OSError, subprocess.TimeoutExpired) as exc:
        if args.json:
            print(json.dumps(envelope(command=command, data={"error": str(exc)}, ok=False), indent=2))
        print(f"pfsense: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
