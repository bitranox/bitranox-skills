"""Tests for pfsense.py - drive a pfSense box without hand-rolling PHP over SSH. ASCII only.

The load-bearing properties, each one a fault that has actually shipped:

  * stdout and stderr are never merged, so the ssh client's post-quantum banner cannot end up
    inside parsed data;
  * a mutation is a dry run until --apply, and snapshots before it acts;
  * selection is by MAC or name and refuses on ambiguity, never by a position that shifts;
  * `doctor` reports the faults that raise no error of their own, and stays quiet on a healthy
    config - a check that fires on everything is as useless as one that fires on nothing.

Addresses are RFC 5737 documentation ranges throughout.
"""
import datetime
import os
import pathlib
import json
import shutil
import subprocess
import sys

import pytest

import pfsense as P

TARGET = P.Target(host="192.0.2.1", user="admin", ssh="ssh -i /key")

# What the ssh CLIENT prints on stderr when the server has no post-quantum key exchange. Real
# capture. 380 hand-rolled payloads merged this into stdout with 2>&1 and then filtered it back out.
BANNER = (
    '** WARNING: connection is not using a post-quantum key exchange algorithm.\n'
    '** This session may be vulnerable to "store now, decrypt later" attacks.\n'
    '** The server may need to be upgraded. See https://openssh.com/pq.html\n'
)

# Real `arp -an` output from a pfSense 2.8 box, with one permanent entry and one incomplete.
ARP_TEXT = """? (192.0.2.1) at 00:11:22:33:44:01 on igb1 expires in 1200 seconds [ethernet]
? (192.0.2.30) at 00:11:22:33:44:30 on igb1 permanent [ethernet]
? (192.0.2.31) at 00:11:22:33:44:31 on igb1 expires in 800 seconds [ethernet]
? (192.0.2.99) at (incomplete) on igb1 expired [ethernet]
"""

CONFIG_XML = """<?xml version="1.0"?>
<pfsense>
  <dhcpd>
    <lan>
      <staticmap>
        <mac>00:11:22:33:44:30</mac><ipaddr>192.0.2.30</ipaddr><hostname>speaker</hostname>
        <arp_table_static_entry></arp_table_static_entry>
      </staticmap>
      <staticmap>
        <mac>00:11:22:33:44:31</mac><ipaddr>192.0.2.31</ipaddr><hostname>nas</hostname>
      </staticmap>
    </lan>
  </dhcpd>
  <unbound>
    <enable></enable>
    <hosts><host>nas</host><domain>example.com</domain><ip>192.0.2.31</ip></hosts>
    <hosts><host></host><domain>bare.example.com</domain><ip>192.0.2.40</ip></hosts>
  </unbound>
</pfsense>
"""


class FakeRun:
    """Stands in for the one process seam, recording every call so a test can assert what ran."""

    def __init__(self, responses=()):
        self.calls = []
        self.responses = list(responses)

    def __call__(self, argv, *, stdin_text=None, timeout=30):
        self.calls.append({"argv": argv, "remote": argv[-1], "stdin": stdin_text})
        for needle, response in self.responses:
            if needle in argv[-1] or (stdin_text and needle in stdin_text):
                return response
        return (0, "", "")

    def php_bodies(self):
        """Just the PHP scripts that were sent, in order."""
        return [c["stdin"] for c in self.calls if c["stdin"]]


def res(ip, mac, *, static_arp=False, interface="lan", hostname="", descr=""):
    """A Reservation with the fields a test does not care about left empty."""
    return P.Reservation(interface=interface, mac=mac, ip=ip, hostname=hostname, descr=descr,
                         static_arp=static_arp)


# ---- the streams stay apart ---------------------------------------------------------------------
def test_stderr_banner_never_reaches_the_parsed_data():
    """The whole point: the banner is on stderr, so a parser that keeps them apart never sees it."""
    fake = FakeRun([('config_get_path("dhcpd"', (0, RESERVATIONS_JSON, BANNER))])
    assert P.run_php(TARGET, P.php_list_reservations(), parse=P.Reservation.list_from_json, run=fake) == [
        res("192.0.2.30", "00:11:22:33:44:30", static_arp=True, hostname="speaker"),
        res("192.0.2.31", "00:11:22:33:44:31", hostname="nas")]


def test_a_banner_merged_into_stdout_would_break_the_parse():
    """The control, so the test above cannot pass vacuously.

    This is exactly what `ssh ... 2>&1` produces. If it did NOT fail here, the assertion above
    would prove nothing about where the banner went.
    """
    fake = FakeRun([('config_get_path("dhcpd"', (0, BANNER + "[]", ""))])
    with pytest.raises(P.PfsenseError):
        P.run_php(TARGET, P.php_list_reservations(), parse=P.Reservation.list_from_json, run=fake)


def test_php_source_travels_on_stdin_not_in_the_command():
    """No quoting layer can mangle what it never parses: the remote command is the bare word php."""
    fake = FakeRun([("config_get_path", (0, "[]", ""))])
    P.run_php(TARGET, P.php_list_reservations(), parse=P.Reservation.list_from_json, run=fake)
    assert fake.calls[0]["remote"] == "php"
    assert 'require_once("config.inc")' in fake.calls[0]["stdin"]


def test_php_that_returns_nothing_is_an_error_not_an_empty_result():
    fake = FakeRun([("config_get_path", (0, "", BANNER))])
    with pytest.raises(P.PfsenseError):
        P.run_php(TARGET, P.php_list_reservations(), parse=P.Reservation.list_from_json, run=fake)


# ---- a reply is checked where it enters ---------------------------------------------------------
# A reply of another shape used to reach the readers: a missing key or a list where text belongs
# crashed with a traceback, the string "yes" where a flag belongs read as true, and a pool with no
# end was skipped by the audit without a word. It is now refused at run_php, naming the box.
_ONE_RES = '"interface":"lan","mac":"00:11:22:33:44:30","hostname":"x","descr":""'


@pytest.mark.parametrize("reply", [
    "[{" + _ONE_RES + ',"ip":"192.0.2.30"}]',                                   # no static_arp
    "[{" + _ONE_RES + ',"ip":["192.0.2.30"],"static_arp":false}]',              # a list for text
    "[{" + _ONE_RES + ',"ip":"192.0.2.30","static_arp":"yes"}]',                # text for a flag
    '{"interface":"lan"}',                                                      # not a list at all
])
def test_a_reservation_reply_of_another_shape_is_refused_naming_the_box(reply, capsys):
    fake = FakeRun([('config_get_path("dhcpd"', (0, reply, BANNER))])
    assert P.main(["--host", "192.0.2.1", "dhcp", "list"], run=fake) == 2
    assert "php on 192.0.2.1 returned an unexpected reply: " in capsys.readouterr().err


@pytest.mark.parametrize("reply", [
    '[{"host":"nas","domain":"example.com","ip":"192.0.2.31"}]',                # no descr
    '[{"host":null,"domain":"example.com","ip":"192.0.2.31","descr":""}]',      # null for text
])
def test_an_override_reply_of_another_shape_is_refused_naming_the_box(reply, capsys):
    fake = FakeRun([('config_get_path("unbound/hosts"', (0, reply, ""))])
    assert P.main(["--host", "192.0.2.1", "--json", "dns", "list"], run=fake) == 2
    out = capsys.readouterr()
    assert json.loads(out.out)["ok"] is False
    assert "php on 192.0.2.1 returned an unexpected reply: a host override has no text field" in out.err


@pytest.mark.parametrize("reply", [
    '{"version":"2.8.0","dhcp_backend":"isc","resolver":"unbound","packages":[]}',  # no interfaces
    '{"version":"2.8.0","dhcp_backend":"isc","resolver":"unbound","packages":[],'
    '"interfaces":[{"name":"lan","descr":"","ipaddr":"192.0.2.1","subnet":"24"}]}',  # no if
    '{"version":"2.8.0","dhcp_backend":"isc","resolver":"unbound","interfaces":[],'
    '"packages":[{"name":"snort","version":4}]}',                                      # a number for text
])
def test_an_info_reply_of_another_shape_is_refused_naming_the_box(reply, capsys):
    fake = FakeRun([('"dhcp_backend"', (0, reply, ""))])
    assert P.main(["--host", "192.0.2.1", "info"], run=fake) == 2
    assert "php on 192.0.2.1 returned an unexpected reply: " in capsys.readouterr().err


def test_a_pool_reply_of_another_shape_is_refused_before_the_audit(capsys):
    fake = FakeRun([('$pools = array()', (0, '[{"interface":"lan","from":"192.0.2.100"}]', "")),
                    ('config_get_path("dhcpd"', (0, RESERVATIONS_JSON, "")),
                    ('config_get_path("unbound/hosts"', (0, "[]", ""))])
    assert P.main(["--host", "192.0.2.1", "doctor"], run=fake) == 2
    assert "a DHCP pool has no text field 'to'" in capsys.readouterr().err


# Each write's reply is checked too, and its refusal says the change may already be written: the
# reply only arrives after write_config() ran. Before, a missing unbound_follows read as false and
# skipped the unbound check, "changed": "yes" counted as 3 cleared reservations, and an echoed
# override without its address was printed as added.
_WRITE_REPLIES = [
    (["dhcp", "rm", "--mac", "00:11:22:33:44:30"], "$removed",
     '{"removed":[{"interface":"lan","ip":"192.0.2.30"}]}', "has no true/false field 'unbound_follows'"),
    (["dhcp", "rm-static-arp", "--mac", "00:11:22:33:44:30"], "$changed",
     '{"changed":"yes"}', "its changed list is not a JSON array"),
    (["dhcp", "rename", "--mac", "00:11:22:33:44:31", "--hostname", "storage"], "$renamed",
     '{"renamed":[{"interface":"lan"}],"unbound_follows":false}', "its renamed list has no text field 'ip'"),
    (["dhcp", "add", "--mac", "00:11:22:33:44:50", "--ip", "192.0.2.50", "--hostname", "printer"], "$added",
     '{"added":{"interface":"lan","mac":"00:11:22:33:44:50","ip":"192.0.2.50"},"unbound_follows":false}',
     "the added reservation has no text field 'hostname'"),
    (["dns", "add", "--name", "x.example.com", "--ip", "192.0.2.9"], "$hosts[] =",
     '{"added":{"host":"x","domain":"example.com"}}', "the added override has no text field 'ip'"),
    (["dns", "rm", "--name", "nas.example.com"], "$kept = array(); $removed = array();",
     '{"removed":[{"interface":"lan","ip":"192.0.2.31"}]}', "has no text field 'host'"),
]


@pytest.mark.parametrize(("argv", "marker", "reply", "why"), _WRITE_REPLIES)
def test_a_write_reply_of_another_shape_is_refused_saying_the_change_may_be_written(
        argv, marker, reply, why, tmp_path, capsys):
    fake = FakeRun([(marker, (0, reply, "")), *_unbound_up(),
                    ('"dhcp_backend"', (0, INFO_JSON, "")),
                    ('config_get_path("unbound/hosts"', (0, BARE_OVERRIDES, "")),
                    ('config_get_path("dhcpd"', (0, RESERVATIONS_JSON, "")),
                    ("cat /conf/config.xml", (0, CONFIG_XML, ""))])
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path), *argv], run=fake)
    err = capsys.readouterr().err
    assert rc == 2
    assert "php on 192.0.2.1 returned an unexpected reply: " in err and why in err
    assert "the change may already be written to config.xml" in err


def test_a_read_reply_of_another_shape_does_not_claim_a_write():
    fake = FakeRun([('config_get_path("dhcpd"', (0, '{"interface":"lan"}', ""))])
    with pytest.raises(P.PfsenseError) as caught:
        P.run_php(TARGET, P.php_list_reservations(), parse=P.Reservation.list_from_json, run=fake)
    assert "config.xml" not in str(caught.value)


# ---- ssh argv -----------------------------------------------------------------------------------
def test_batchmode_is_forced_so_a_rejected_key_cannot_prompt():
    """With only -i, ssh falls back to a password prompt and hangs an unattended run."""
    argv = P.build_ssh_argv(TARGET, "arp -an")
    assert "BatchMode=yes" in argv
    assert argv[-2:] == ["admin@192.0.2.1", "arp -an"]


def test_a_caller_supplied_batchmode_is_not_duplicated():
    argv = P.build_ssh_argv(P.Target(host="192.0.2.1", ssh="ssh -o BatchMode=yes"), "true")
    assert argv.count("BatchMode=yes") == 1


def test_the_ssh_prefix_is_split_as_a_command_line_not_one_argument():
    argv = P.build_ssh_argv(P.Target(host="192.0.2.1", ssh="ssh -i /a key/id -F /cfg"), "true")
    assert "-i" in argv and "/a key/id" not in " ".join(argv[:2])


# ---- pure parsers -------------------------------------------------------------------------------
def test_parse_table_strips_the_indent_pfctl_adds():
    assert P.parse_table("   192.0.2.5\n   192.0.2.6\n\n") == {"192.0.2.5", "192.0.2.6"}


def test_blocked_among_keeps_the_caller_order():
    table = "  192.0.2.6\n  192.0.2.5\n"
    assert P.blocked_among(table, ["192.0.2.5", "192.0.2.9", "192.0.2.6"]) == ["192.0.2.5", "192.0.2.6"]


def test_parse_alerts_survives_a_comma_inside_the_quoted_message():
    """str.split shifts every later field on this line and reads the wrong IP as the destination."""
    line = '01/02-03:04:05,1,2071408,1,"ET INFO Observed DNS Query, suspicious",TCP,192.0.2.7,443,198.51.100.9,80\n'
    alerts = P.parse_alerts(line)
    assert len(alerts) == 1
    assert alerts[0].sid == "2071408"
    assert alerts[0].src == "192.0.2.7"
    assert alerts[0].dst == "198.51.100.9"


def test_parse_alerts_filters_by_ip():
    line = '01/02-03:04:05,1,999,1,"msg",TCP,192.0.2.7,443,198.51.100.9,80\n'
    assert P.parse_alerts(line, ip="198.51.100.9")
    assert P.parse_alerts(line, ip="203.0.113.1") == []


# A real pfSense 2.8.1 Snort alert line (addresses replaced): a preprocessor alert, generator 125.
# Its SID 9 names a different rule under generator 1, so the generator has to travel with the SID.
ALERT_GID_125 = ('11/16/26-01:54:17.521185 ,125,9,1,"(ftp_telnet) Evasive (incomplete) TELNET CMD on '
                 'FTP Command Channel",TCP,192.0.2.146,3535,198.51.100.105,443,65159,'
                 'Potentially Bad Traffic,2,alert,Allow\n')


def test_parse_alerts_reads_the_generator_id():
    alerts = P.parse_alerts(ALERT_GID_125)
    assert [(a.gid, a.sid) for a in alerts] == [("125", "9")]
    assert (alerts[0].src, alerts[0].dst) == ("192.0.2.146", "198.51.100.105")


def test_parse_sid_spec_reads_gid_colon_sid_and_assumes_gid_1_for_a_bare_sid():
    assert P.parse_sid_spec("125:9") == P.SignatureId(gid=125, sid=9, gid_assumed=False)
    assert P.parse_sid_spec("2071408") == P.SignatureId(gid=1, sid=2071408, gid_assumed=True)
    assert P.parse_sid_spec(" 1:2071408 ") == P.SignatureId(gid=1, sid=2071408, gid_assumed=False)


@pytest.mark.parametrize("text", ["", "125:", ":9", "125:9:1", "abc", "9;reboot", "-1", "1.5",
                                  "125 9", chr(0x0662)])
def test_parse_sid_spec_refuses_anything_but_digits_or_gid_colon_sid(text):
    with pytest.raises(ValueError):
        P.parse_sid_spec(text)


def test_instance_dir_comes_from_the_running_process_not_a_glob():
    """A stale snort_<uuid>_<oldif> dir sorts FIRST, so a glob inspects a file nothing writes."""
    ps = "root 123 snort -R 12345 -c /usr/local/etc/snort/snort_9999_igb0/snort.conf -i igb0\n"
    assert P.instance_dir_from_ps(ps) == "/usr/local/etc/snort/snort_9999_igb0"


def test_instance_dir_is_none_when_snort_is_not_running():
    assert P.instance_dir_from_ps("root 1 /sbin/init\n") is None


def test_normalize_target_takes_the_host_out_of_a_url():
    assert P.normalize_target("https://example.com/a/b?c=1") == "example.com"
    assert P.normalize_target("example.com/path") == "example.com"
    assert P.normalize_target(" 192.0.2.5 ") == "192.0.2.5"


def test_resolve_ips_passes_an_address_through_without_dns():
    assert P.resolve_ips("192.0.2.5") == ["192.0.2.5"]


def test_normalize_mac_accepts_the_common_separators():
    assert P.normalize_mac("00-11-22-33-44-55") == "00:11:22:33:44:55"
    assert P.normalize_mac("0011.2233.4455") == "00:11:22:33:44:55"
    assert P.normalize_mac("00:11:22:33:44:AA") == "00:11:22:33:44:aa"


def test_normalize_mac_refuses_something_that_is_not_one():
    with pytest.raises(P.PfsenseError):
        P.normalize_mac("192.0.2.5")


def test_parse_arp_marks_the_permanent_entry():
    entries = P.parse_arp(ARP_TEXT)
    assert [e["ip"] for e in entries] == ["192.0.2.1", "192.0.2.30", "192.0.2.31", "192.0.2.99"]
    assert [e["permanent"] for e in entries] == [False, True, False, False]


def test_parse_arp_keeps_an_incomplete_entry_with_no_mac():
    incomplete = [e for e in P.parse_arp(ARP_TEXT) if e["ip"] == "192.0.2.99"][0]
    assert incomplete["mac"] == ""


def test_an_override_fqdn_handles_an_override_with_no_host_part():
    assert P.Override(host="", domain="example.com", ip="", descr="").fqdn == "example.com"
    assert P.Override(host="nas", domain="example.com", ip="", descr="").fqdn == "nas.example.com"


# ---- selection refuses to guess -----------------------------------------------------------------
def test_select_one_finds_the_single_match():
    items = [res("192.0.2.5", "aa:aa:aa:aa:aa:aa"), res("192.0.2.6", "bb:bb:bb:bb:bb:bb")]
    assert P.select_reservation(items, "BB:BB:BB:BB:BB:BB").mac == "bb:bb:bb:bb:bb:bb"


def test_select_one_refuses_when_nothing_matches():
    with pytest.raises(P.PfsenseError, match="no reservation with mac=bb:bb:bb:bb:bb:bb$"):
        P.select_reservation([res("192.0.2.5", "aa:aa:aa:aa:aa:aa")], "bb:bb:bb:bb:bb:bb")


def test_select_one_refuses_an_ambiguous_match_rather_than_taking_the_first():
    """Taking the first is how a second command from the same listing hits the wrong row."""
    items = [res("192.0.2.5", "aa:aa:aa:aa:aa:aa"), res("192.0.2.6", "aa:aa:aa:aa:aa:aa")]
    with pytest.raises(P.PfsenseError, match="2 reservation entries share mac=aa:aa:aa:aa:aa:aa; refusing to guess"):
        P.select_reservation(items, "aa:aa:aa:aa:aa:aa")


# ---- generated PHP is escaped at the sink -------------------------------------------------------
def test_php_str_escapes_a_quote_that_would_otherwise_end_the_literal():
    assert P.php_str("it's") == r"'it\'s'"


def test_php_str_escapes_a_backslash():
    assert P.php_str("a\\b") == r"'a\\b'"


NASTY_DESCR = "Bob's box'; system('rm -rf /'); //"


def _php_single_quoted_value(literal: str) -> str:
    """Decode a PHP single-quoted literal the way PHP does: only \\\\ and \\' are escapes.

    Raises if an unescaped quote closes the literal early, which is exactly what an injection is.
    """
    assert literal.startswith("'") and literal.endswith("'")
    body, out, i = literal[1:-1], [], 0
    while i < len(body):
        if body[i] == "\\" and i + 1 < len(body) and body[i + 1] in ("\\", "'"):
            out.append(body[i + 1])
            i += 2
            continue
        assert body[i] != "'", "an unescaped quote ends the literal early"
        out.append(body[i])
        i += 1
    return "".join(out)


def test_a_description_with_a_quote_survives_as_data_rather_than_becoming_code():
    assert _php_single_quoted_value(P.php_str(NASTY_DESCR)) == NASTY_DESCR


def test_the_naive_interpolation_this_replaces_really_would_break_out():
    """The control: without escaping, the literal closes early and the rest is parsed as PHP."""
    with pytest.raises(AssertionError, match="ends the literal early"):
        _php_single_quoted_value("'" + NASTY_DESCR + "'")


def test_a_hostile_description_reaches_the_generated_php_only_as_a_quoted_literal():
    body = P.php_add_override("nas", "example.com", "192.0.2.31", NASTY_DESCR)
    assert P.php_str(NASTY_DESCR) in body


# ---- XML is parsed defensively ------------------------------------------------------------------
def test_parse_xml_refuses_a_document_type_declaration():
    """A config.xml has no DOCTYPE, so refusing one closes entity expansion without a dependency."""
    with pytest.raises(P.PfsenseError, match="DOCTYPE"):
        P.parse_xml('<?xml version="1.0"?><!DOCTYPE p [<!ENTITY a "x">]><pfsense/>')


def test_parse_xml_accepts_a_real_config():
    assert P.parse_xml(CONFIG_XML).tag == "pfsense"


def test_reservations_are_read_out_of_a_snapshot_with_the_static_arp_flag():
    assert P.reservations_from_config_xml(CONFIG_XML) == [
        res("192.0.2.30", "00:11:22:33:44:30", static_arp=True, hostname="speaker"),
        res("192.0.2.31", "00:11:22:33:44:31", hostname="nas")]


def test_overrides_are_read_from_unbound_hosts_not_hostoverride():
    """The GUI says Host Overrides; the element is `hosts`. The wrong path returns [] silently."""
    overrides = P.overrides_from_config_xml(CONFIG_XML)
    assert [o.fqdn for o in overrides] == ["nas.example.com", "bare.example.com"]


# ---- doctor -------------------------------------------------------------------------------------
def test_doctor_warns_about_an_armed_static_arp_entry():
    findings = P.doctor_findings(reservations=P.reservations_from_config_xml(CONFIG_XML), overrides=[])
    armed = [f for f in findings if f.check == "static_arp_armed"]
    assert len(armed) == 1 and armed[0].severity == "warn" and "192.0.2.30" in armed[0].subject


def test_doctor_stays_quiet_on_a_config_with_nothing_wrong():
    """A check that fires on a healthy config is as useless as one that never fires."""
    clean = [res("192.0.2.31", "00:11:22:33:44:31")]
    assert [f for f in P.doctor_findings(reservations=clean, overrides=[]) if f.severity == "warn"] == []


def test_a_finding_with_a_misspelled_severity_is_refused():
    """`doctor` exits 1 only on a `warn`: a misspelled one would be filed as informational."""
    with pytest.raises(ValueError):
        P.Finding(check="static_arp_armed", severity="wran", subject="s", detail="d")


def test_a_finding_severity_keeps_its_wire_string():
    finding = P.Finding(check="c", severity="warn", subject="s", detail="d")
    assert finding.severity is P.Severity.WARN
    assert json.dumps(P.asdict(finding)) == (
        '{"check": "c", "severity": "warn", "subject": "s", "detail": "d"}')


def test_one_address_shared_by_several_macs_is_context_not_a_warning():
    """Measured: warning on this alone fired 5 times on a config that was entirely correct.

    A wired and a wireless interface sharing one reserved address is the intended setup.
    """
    shared = [res("192.0.2.31", "00:11:22:33:44:31"), res("192.0.2.31", "00:11:22:33:44:32")]
    findings = P.doctor_findings(reservations=shared, overrides=[])
    assert [f.check for f in findings] == ["shared_ip_multi_mac"]
    assert findings[0].severity == "info"


def test_static_arp_on_a_shared_address_names_the_lethal_combination():
    shared = [res("192.0.2.31", "00:11:22:33:44:31", static_arp=True), res("192.0.2.31", "00:11:22:33:44:32")]
    armed = [f for f in P.doctor_findings(reservations=shared, overrides=[]) if f.check == "static_arp_armed"]
    assert "2 MACs" in armed[0].detail


def test_doctor_reports_an_address_held_by_hardware_the_reservation_does_not_name():
    """The stale-reservation-versus-live-device collision, which shows up as flaky wifi."""
    reservations = [res("192.0.2.30", "aa:aa:aa:aa:aa:aa", descr="old AP")]
    findings = P.doctor_findings(reservations=reservations, overrides=[], arp=P.parse_arp(ARP_TEXT))
    mismatch = [f for f in findings if f.check == "reservation_mac_mismatch"]
    assert len(mismatch) == 1 and "00:11:22:33:44:30" in mismatch[0].subject


def test_an_idle_device_is_never_reported_as_gone():
    """ARP is a cache that expires after minutes of silence, so absence is not evidence.

    Measured: a version that concluded from absence called 22 healthy hosts possibly-gone on a
    network with nothing wrong with it. The DHCP lease file cannot rescue it either, because ISC
    dhcpd writes no lease for a fixed-address reservation.
    """
    reservations = [res("192.0.2.77", "aa:aa:aa:aa:aa:aa", descr="idle")]
    assert P.doctor_findings(reservations=reservations, overrides=[], arp=P.parse_arp(ARP_TEXT)) == []


def test_one_reserved_mac_answering_for_a_shared_address_is_not_a_mismatch():
    """A device with several reserved MACs answers from exactly one of them at a time.

    Measured: treating the others as mismatches produced 5 false warnings against a live config.
    """
    shared = [res("192.0.2.30", "00:11:22:33:44:30"), res("192.0.2.30", "00:11:22:33:44:99")]
    findings = P.doctor_findings(reservations=shared, overrides=[], arp=P.parse_arp(ARP_TEXT))
    assert [f.check for f in findings] == ["shared_ip_multi_mac"]


def test_an_override_pointing_at_a_static_host_is_not_a_finding():
    """A statically configured server has no reservation; that is normal, not a fault."""
    overrides = [P.Override(host="srv", domain="example.com", ip="192.0.2.200", descr="")]
    assert P.doctor_findings(reservations=[], overrides=overrides) == []
    assert P.doctor_findings(reservations=[], overrides=overrides, arp=P.parse_arp(ARP_TEXT)) == []


# Real captures, with the site-specific values replaced. HIJACKED is what tailscaled writes with
# Accept DNS on; HEALTHY is what a correct pfSense box looks like - its own resolver first, then
# the configured upstreams as fallbacks.
RESOLV_HIJACKED = """# resolv.conf(5) file generated by tailscale
# For more info, see https://tailscale.com/s/resolvconf-overwrite
# DO NOT EDIT THIS FILE BY HAND -- CHANGES WILL BE OVERWRITTEN

nameserver 100.100.100.100
search tailnet-example.ts.net internal.example
"""

RESOLV_HEALTHY = """nameserver 127.0.0.1
nameserver ::1
nameserver 192.0.2.53
nameserver 198.51.100.53
search internal.example
"""


def test_doctor_warns_when_magicdns_has_taken_over_the_resolver():
    findings = P.doctor_findings(reservations=[], overrides=[], arp=[], resolv_conf=RESOLV_HIJACKED)
    assert [f.check for f in findings] == ["magicdns_in_resolv_conf"]


def test_upstream_fallbacks_after_loopback_are_not_a_fault():
    """The regression that matters: a correct box lists upstream resolvers after its own.

    Measured: requiring every entry to be loopback flagged a firewall that had just been FIXED,
    naming its perfectly normal fallbacks as the evidence of a hijack. The check had only ever
    been run against the broken box, never against a healthy one.
    """
    assert P.doctor_findings(reservations=[], overrides=[], arp=[], resolv_conf=RESOLV_HEALTHY) == []


def test_ipv6_loopback_counts_as_the_box_resolving_through_itself():
    assert P.doctor_findings(reservations=[], overrides=[], arp=[],
                             resolv_conf="nameserver ::1\nnameserver 192.0.2.53\n") == []


def test_doctor_warns_when_the_box_does_not_ask_itself_first():
    findings = P.doctor_findings(reservations=[], overrides=[], arp=[],
                                 resolv_conf="nameserver 192.0.2.53\nnameserver 127.0.0.1\n")
    assert [f.check for f in findings] == ["resolver_not_first"]


def test_doctor_reports_an_upgrade_lock_and_names_its_path():
    findings = P.doctor_findings(reservations=[], overrides=[], arp=[],
                                 upgrade_locks=["/tmp/pfSense-upgrade.lock"])
    assert [f.check for f in findings] == ["upgrade_lock_present"]
    assert findings[0].subject == "/tmp/pfSense-upgrade.lock"


def test_doctor_reports_no_lock_finding_when_no_lock_was_found():
    assert P.doctor_findings(reservations=[], overrides=[], arp=[], upgrade_locks=[]) == []


def test_the_upgrade_lock_finding_sends_the_reader_to_dns_before_the_lock():
    """The lock is usually held by a pfSense-upgrade hung on a repository the box cannot resolve.

    Advising removal on its own is the dirty patch: the next metadata run hangs again and the
    message comes back.
    """
    [finding] = P.doctor_findings(reservations=[], overrides=[], arp=[],
                                  upgrade_locks=["/var/run/pfSense-upgrade.lock"])
    assert "fix the box's dns first" in finding.detail.lower()
    assert "the lock is stale and the file can be removed" not in finding.detail


def test_the_magicdns_finding_does_not_advise_forwarding_to_quad_100():
    """quad-100 does not answer on FreeBSD/pfSense, so a forward to it SERVFAILs there."""
    [finding] = P.doctor_findings(reservations=[], overrides=[], arp=[],
                                  resolv_conf=RESOLV_HIJACKED)
    assert "domain override" not in finding.detail
    assert "forward the tailnet's domain to MagicDNS" not in finding.detail
    assert "Linux tailnet node" in finding.detail
    assert "--accept-dns=false" in finding.detail


# ---- mutations are dry runs until --apply -------------------------------------------------------
RESERVATIONS_JSON = json.dumps([
    {"interface": "lan", "mac": "00:11:22:33:44:30", "ip": "192.0.2.30", "hostname": "speaker",
     "descr": "", "static_arp": True},
    {"interface": "lan", "mac": "00:11:22:33:44:31", "ip": "192.0.2.31", "hostname": "nas",
     "descr": "", "static_arp": False},
])


def _fake_for_mutation():
    # Order matters: the mutation payloads ALSO read config_get_path("dhcpd"), so the specific
    # markers have to be matched before the listing one or every write answers with the listing.
    return FakeRun([
        ("$removed", (0, '{"removed":[{"interface":"lan","ip":"192.0.2.30"}],"unbound_follows":false}', "")),
        ("$changed", (0, '{"changed":[{"interface":"lan","ip":"192.0.2.30"}]}', "")),
        ('config_get_path("dhcpd"', (0, RESERVATIONS_JSON, BANNER)),
        ("cat /conf/config.xml", (0, CONFIG_XML, BANNER)),
    ])


def test_a_mutation_without_apply_sends_no_write():
    fake = _fake_for_mutation()
    rc = P.main(["--host", "192.0.2.1", "dhcp", "rm", "--mac", "00:11:22:33:44:30"], run=fake)
    assert rc == 0
    assert not any("write_config" in body for body in fake.php_bodies())


def test_a_mutation_without_apply_takes_no_snapshot_either():
    fake = _fake_for_mutation()
    P.main(["--host", "192.0.2.1", "dhcp", "rm", "--mac", "00:11:22:33:44:30"], run=fake)
    assert not any("config.xml" in call["remote"] for call in fake.calls)


def test_apply_snapshots_before_it_writes(tmp_path):
    """The snapshot is the only reason the change was safe to make, so it has to come first."""
    fake = _fake_for_mutation()
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path),
                 "dhcp", "rm", "--mac", "00:11:22:33:44:30"], run=fake)
    assert rc == 0
    order = [c["remote"] if not c["stdin"] else "php" for c in fake.calls]
    snapshot_at = order.index("cat /conf/config.xml")
    write_at = next(i for i, c in enumerate(fake.calls) if c["stdin"] and "write_config" in c["stdin"])
    assert snapshot_at < write_at
    assert list(tmp_path.glob("config-192.0.2.1-*.xml"))


def test_an_unknown_mac_is_refused_before_anything_is_written():
    fake = _fake_for_mutation()
    rc = P.main(["--host", "192.0.2.1", "--apply", "dhcp", "rm", "--mac", "aa:bb:cc:dd:ee:ff"], run=fake)
    assert rc == 2
    assert not any("write_config" in body for body in fake.php_bodies())


def test_clearing_static_arp_on_a_reservation_that_has_none_does_nothing():
    fake = _fake_for_mutation()
    rc = P.main(["--host", "192.0.2.1", "--apply", "dhcp", "rm-static-arp", "--mac", "00:11:22:33:44:31"], run=fake)
    assert rc == 0
    assert not any("write_config" in body for body in fake.php_bodies())


# W-D9: a single-target removal whose MATCH succeeded but whose change removed nothing is a failed
# action, exit 2 - never exit 1, which is a well-formed "no" (a finding, a partial outcome).
def _fake_that_removes_nothing():
    return FakeRun([
        ("$removed", (0, '{"removed":[],"unbound_follows":false}', "")),
        ("$changed", (0, '{"changed":[]}', "")),
        ('config_get_path("unbound/hosts"', (0, BARE_OVERRIDES, BANNER)),
        ('config_get_path("dhcpd"', (0, RESERVATIONS_JSON, BANNER)),
        ("cat /conf/config.xml", (0, CONFIG_XML, BANNER)),
    ])


@pytest.mark.parametrize("argv", [
    ["dhcp", "rm", "--mac", "00:11:22:33:44:30"],
    ["dhcp", "rm-static-arp", "--mac", "00:11:22:33:44:30"],
    ["dns", "rm", "--name", "nas.example.com"],
])
def test_a_matched_removal_that_removed_nothing_is_exit_2_with_ok_false(argv, tmp_path, capsys):
    rc = P.main(["--host", "192.0.2.1", "--json", "--apply", "--snapshot-dir", str(tmp_path / "s"),
                 *argv], run=_fake_that_removes_nothing())
    out = capsys.readouterr()
    assert rc == 2
    assert json.loads(out.out)["ok"] is False
    assert "nothing" in out.err


@pytest.mark.parametrize("argv", [
    ["dhcp", "rm", "--mac", "00:11:22:33:44:30"],
    ["dhcp", "rm-static-arp", "--mac", "00:11:22:33:44:30"],
    ["dns", "rm", "--name", "nas.example.com"],
])
def test_control_a_removal_that_removed_its_entry_is_exit_0(argv, tmp_path):
    fake = _fake_for_mutation()
    # The dns removal echoes overrides, not reservations, so it gets its own reply ahead of $removed.
    fake.responses[:0] = [("$kept = array(); $removed = array();",
                           (0, '{"removed":[{"host":"nas","domain":"example.com","ip":"192.0.2.31"}]}', ""))]
    fake.responses += [*_unbound_up(), ('config_get_path("unbound/hosts"', (0, BARE_OVERRIDES, BANNER))]
    assert P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path / "s"), *argv],
                  run=fake) == 0


# ---- snapshot -----------------------------------------------------------------------------------
def test_snapshot_writes_a_timestamped_file(tmp_path):
    fake = FakeRun([("cat /conf/config.xml", (0, CONFIG_XML, BANNER))])
    path = P.do_snapshot(TARGET, tmp_path, run=fake)
    assert path.parent == tmp_path and path.read_text(encoding="utf-8") == CONFIG_XML


@pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX-only")
def test_a_snapshot_is_readable_by_its_owner_only_whatever_the_umask(tmp_path):
    # The file holds password hashes and private keys. In an existing folder others can read (a
    # shared site folder keeps its mode), a umask-default 0644 file would hand them out.
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    old = os.umask(0o022)
    try:
        path = P.do_snapshot(TARGET, shared, run=FakeRun([("cat /conf/config.xml",
                                                           (0, CONFIG_XML, BANNER))]))
    finally:
        os.umask(old)
    assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX-only")
def test_a_snapshot_replacing_a_same_second_file_tightens_its_mode(tmp_path, monkeypatch):
    fixed = datetime.datetime(2026, 1, 2, 3, 4, 5)

    class Clock(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    monkeypatch.setattr(P, "datetime", Clock)  # the clock: the one external edge here
    stale = tmp_path / f"config-{TARGET.host}-20260102030405.xml"
    stale.write_text("old", encoding="utf-8")
    stale.chmod(0o644)
    path = P.do_snapshot(TARGET, tmp_path, run=FakeRun([("cat /conf/config.xml",
                                                         (0, CONFIG_XML, BANNER))]))
    assert path == stale and path.read_text(encoding="utf-8") == CONFIG_XML
    assert path.stat().st_mode & 0o777 == 0o600


def test_snapshot_refuses_to_save_something_that_is_not_a_config(tmp_path):
    """A snapshot nobody can restore from is worse than no snapshot, so a bad read must not be kept."""
    fake = FakeRun([("cat /conf/config.xml", (0, "ssh: connect to host: Connection timed out\n", ""))])
    with pytest.raises(P.PfsenseError):
        P.do_snapshot(TARGET, tmp_path, run=fake)
    assert list(tmp_path.iterdir()) == []


def test_snapshot_refuses_xml_that_is_not_a_pfsense_config(tmp_path):
    fake = FakeRun([("cat /conf/config.xml", (0, "<html><body>login</body></html>", ""))])
    with pytest.raises(P.PfsenseError, match="not <pfsense>"):
        P.do_snapshot(TARGET, tmp_path, run=fake)


def test_snapshot_refuses_when_the_read_failed(tmp_path):
    fake = FakeRun([("cat /conf/config.xml", (255, "", "Permission denied (publickey)."))])
    with pytest.raises(P.PfsenseError):
        P.do_snapshot(TARGET, tmp_path, run=fake)


# ---- read-only verbs ----------------------------------------------------------------------------
def test_table_test_says_yes_with_exit_zero_and_no_with_exit_one():
    fake = FakeRun([("-T show", (0, "  192.0.2.5\n  192.0.2.6\n", BANNER))])
    assert P.main(["--host", "192.0.2.1", "table", "test", "snort2c", "192.0.2.5"], run=fake) == 0
    assert P.main(["--host", "192.0.2.1", "table", "test", "snort2c", "203.0.113.9"], run=fake) == 1


def test_snort_check_exits_one_when_the_address_is_blocked():
    fake = FakeRun([("-T show", (0, "  192.0.2.5\n", BANNER))])
    assert P.main(["--host", "192.0.2.1", "snort", "check", "192.0.2.5"], run=fake) == 1
    assert P.main(["--host", "192.0.2.1", "snort", "check", "203.0.113.9"], run=fake) == 0


def test_snort_check_reports_an_unreadable_table_rather_than_calling_it_clear():
    """No Snort installed must not read as "nothing is blocked"."""
    fake = FakeRun([("-T show", (1, "", "pfctl: Table does not exist.\n"))])
    assert P.main(["--host", "192.0.2.1", "snort", "check", "192.0.2.5"], run=fake) == 2


def test_fix_steps_names_all_three_parts():
    steps = P.fix_steps(sig=P.parse_sid_spec("2071408"), cidr="198.51.100.0/22")
    assert "2071408" in steps and "198.51.100.0/22" in steps
    assert "suppress" in steps.lower() and "pass list" in steps.lower() and "unblock" in steps


def test_snort_fixsteps_suppresses_the_generator_that_fired(capsys):
    """gen_id 1, sig_id 9 is a different rule: following the old output verbatim shipped a no-op."""
    assert P.main(["snort", "fixsteps", "--sid", "125:9"], run=FakeRun()) == 0
    out = capsys.readouterr().out
    assert "'suppress gen_id 125, sig_id 9'" in out
    assert "gen_id 1," not in out
    assert "snort verify --sid 125:9" in out
    assert "assumed" not in out


def test_snort_fixsteps_with_a_bare_sid_says_gen_id_1_is_assumed(capsys):
    assert P.main(["--json", "snort", "fixsteps", "--sid", "2071408"], run=FakeRun()) == 0
    result = json.loads(capsys.readouterr().out)
    assert "'suppress gen_id 1, sig_id 2071408'" in result["data"]["steps"]
    assert "gen_id 1 is assumed" in result["data"]["steps"]
    assert (result["data"]["gid"], result["data"]["sid"], result["data"]["gid_assumed"]) == (1, 2071408, True)


def test_snort_fixsteps_with_a_cidr_offers_a_suppression_scoped_to_that_range(capsys):
    """The all-sources line silences the rule for every address; a scoped pair names both sides."""
    assert P.main(["snort", "fixsteps", "--sid", "125:9", "--cidr", "198.51.100.0/22"], run=FakeRun()) == 0
    out = capsys.readouterr().out
    assert "suppress gen_id 125, sig_id 9, track by_src, ip 198.51.100.0/22" in out
    assert "suppress gen_id 125, sig_id 9, track by_dst, ip 198.51.100.0/22" in out
    assert "EVERY address" in out


def test_snort_fixsteps_without_a_cidr_offers_no_scoped_line(capsys):
    assert P.main(["snort", "fixsteps", "--sid", "125:9"], run=FakeRun()) == 0
    out = capsys.readouterr().out
    assert "track by_" not in out
    assert "EVERY address" in out and "--cidr" in out


def test_snort_fixsteps_prints_no_scoped_line_for_a_cidr_that_is_not_a_range(capsys):
    assert P.main(["snort", "fixsteps", "--sid", "125:9", "--cidr", "not-a-range"], run=FakeRun()) == 0
    out = capsys.readouterr().out
    assert "track by_" not in out and "not an address range" in out


def test_snort_fixsteps_refuses_a_malformed_sid_without_printing_a_suppress_line(capsys):
    assert P.main(["snort", "fixsteps", "--sid", "125:"], run=FakeRun()) == 2
    captured = capsys.readouterr()
    assert "suppress" not in captured.out and "GID:SID" in captured.err


# ---- errors are typed, and reported without a traceback -----------------------------------------
def test_no_target_is_an_error_not_a_default_host():
    """There is deliberately no default firewall: the wrong box is one careless run away."""
    assert P.main(["dhcp", "list"], run=FakeRun()) == 2


def test_json_mode_still_emits_json_on_failure(capsys):
    P.main(["--json", "dhcp", "list"], run=FakeRun())
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and "error" in payload["data"]


def test_a_named_target_that_does_not_exist_names_the_file(tmp_path):
    with pytest.raises(P.PfsenseError, match="no target file"):
        P.load_named_target("home", path=tmp_path / "absent.ini")


def test_a_named_target_is_read_from_the_users_own_file(tmp_path):
    ini = tmp_path / "pfsense.ini"
    ini.write_text("[home]\nhost = 192.0.2.1\nuser = admin\nssh = ssh -i /key\n", encoding="utf-8")
    target = P.load_named_target("home", path=ini)
    assert (target.host, target.user, target.ssh) == ("192.0.2.1", "admin", "ssh -i /key")


def test_a_section_without_a_host_is_refused(tmp_path):
    ini = tmp_path / "pfsense.ini"
    ini.write_text("[home]\nuser = admin\n", encoding="utf-8")
    with pytest.raises(P.PfsenseError, match="no host"):
        P.load_named_target("home", path=ini)


# ---- snapshot destination: a live config.xml must not land in the cwd or a checkout ------------

def _git_says(answer, code=0):
    """A stand-in for `_run`, which returns the TUPLE (rc, stdout, stderr).

    An earlier version of this helper returned an object with .returncode/.stdout. Every test
    passed and the real guard was inert, because the real call raised and the fail-open swallowed
    it. A double whose SHAPE differs from the seam tests nothing.
    """
    def fake(argv, *, timeout=None, stdin_text=None):
        assert argv[0] == "git", "the probe must shell out to git, got %r" % (argv[0],)
        return code, answer, ""
    return fake


def test_the_git_double_matches_the_real_run_signature():
    """Guards the trap above: if _run's contract moves, this fails instead of the guard going quiet."""
    import inspect
    real = inspect.signature(P._run).parameters
    assert set(real) >= {"argv", "timeout"}
    rc, out, err = _git_says("true")(["git", "rev-parse"], timeout=10)
    assert (rc, out, err) == (0, "true", "")


def test_default_snapshot_dir_is_not_the_cwd(monkeypatch, tmp_path):
    """The whole point: a snapshot carries password hashes and private keys."""
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    d = P.default_snapshot_dir()
    assert d == tmp_path / "bitranox" / "pfsense"
    assert d.resolve() != pathlib.Path.cwd().resolve()


def test_default_snapshot_dir_falls_back_to_local_state(monkeypatch, tmp_path):
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", staticmethod(lambda: tmp_path))
    assert P.default_snapshot_dir() == tmp_path / ".local" / "state" / "bitranox" / "pfsense"


def test_prepare_refuses_a_git_work_tree(tmp_path):
    target = tmp_path / "repo" / "scripts"
    target.mkdir(parents=True)
    with pytest.raises(P.PfsenseError) as exc:
        P.prepare_snapshot_dir(target, run=_git_says("true"))
    assert "git work tree" in str(exc.value)
    assert "--allow-repo-snapshot" in str(exc.value)


def test_prepare_allows_a_git_work_tree_when_overridden(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    assert P.prepare_snapshot_dir(target, allow_repo=True, run=_git_says("true")) == target


def test_prepare_allows_a_plain_directory(tmp_path):
    """The known negative: the refusal must not fire where it should not."""
    target = tmp_path / "state"
    target.mkdir()
    assert P.prepare_snapshot_dir(target, run=_git_says("false")) == target


def test_prepare_creates_the_directory_when_missing(tmp_path):
    target = tmp_path / "state" / "pfsense"
    P.prepare_snapshot_dir(target, run=_git_says("false"))
    assert target.is_dir()


def test_prepare_makes_the_directory_private_on_posix(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX modes only")
    target = tmp_path / "state"
    P.prepare_snapshot_dir(target, run=_git_says("false"))
    assert oct(target.stat().st_mode & 0o777) == "0o700"


def test_inside_git_worktree_is_false_when_git_cannot_answer(tmp_path):
    """Fail-open: this is the second layer, behind a default that is already outside a checkout."""
    def boom(*_a, **_k):
        raise OSError("no git")
    assert P.inside_git_worktree(tmp_path, run=boom) is False
    assert P.inside_git_worktree(tmp_path, run=_git_says("", 128)) is False


# ---- the git guard must see a directory that does not exist yet ---------------------------------
needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="needs a real git to answer")


class GitPassingFake(FakeRun):
    """The ssh seam is faked; git calls go to the REAL process seam.

    The work-tree guard shells out to git through the same `run` the ssh verbs use. A fake that
    answered git too would decide the guard's verdict itself, so it could never show the guard
    failing on a real repository.
    """

    def __call__(self, argv, *, stdin_text=None, timeout=30):
        if argv[0] == "git":
            return P._run(argv, stdin_text=stdin_text, timeout=timeout)
        return super().__call__(argv, stdin_text=stdin_text, timeout=timeout)


def _git_repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    return path


@needs_git
def test_prepare_refuses_a_not_yet_existing_dir_inside_a_git_work_tree(tmp_path):
    """The guard used to run only on an existing dir, so a NEW dir inside a repo slipped through."""
    repo = _git_repo(tmp_path / "repo")
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(repo / "snaps" / "deeper")
    assert not (repo / "snaps").exists(), "a refused snapshot dir must not be created"


@needs_git
def test_prepare_still_allows_a_new_dir_outside_any_work_tree(tmp_path):
    """The control: the ancestor walk must not turn every new directory into a refusal."""
    target = tmp_path / "plain" / "snaps"
    assert P.prepare_snapshot_dir(target) == target
    assert target.is_dir()


@needs_git
def test_apply_with_a_new_snapshot_dir_inside_a_repo_writes_nothing_there(tmp_path):
    """End to end: a live config.xml must never land in a checkout because its dir was new."""
    repo = _git_repo(tmp_path / "repo")
    fake = GitPassingFake(_fake_for_mutation().responses)
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(repo / "snaps2"),
                 "dhcp", "rm", "--mac", "00:11:22:33:44:30"], run=fake)
    assert rc == 2
    assert not (repo / "snaps2").exists()
    assert not any("write_config" in body for body in fake.php_bodies())


# ---- a folder the repository ignores is not a folder it can publish ----------------------------
def _ignoring_repo(tmp_path):
    """A repo whose .gitignore ignores `configs/`, the usual home of a site's dated backups."""
    repo = _git_repo(tmp_path / "repo")
    (repo / ".gitignore").write_text("configs/\n", encoding="utf-8")
    return repo


@needs_git
def test_prepare_accepts_an_existing_directory_the_repo_ignores(tmp_path):
    """Measured: a machine repo's gitignored configs/ was refused on every change until
    --allow-repo-snapshot, though git would never stage a file written there."""
    repo = _ignoring_repo(tmp_path)
    (repo / "configs").mkdir()
    assert P.prepare_snapshot_dir(repo / "configs") == repo / "configs"


@needs_git
def test_prepare_accepts_a_new_directory_below_an_ignored_one(tmp_path):
    repo = _ignoring_repo(tmp_path)
    target = repo / "configs" / "fw1"
    assert P.prepare_snapshot_dir(target) == target
    assert target.is_dir()


@needs_git
def test_prepare_refuses_an_unignored_directory_inside_the_repo(tmp_path):
    """The control: an ignore rule elsewhere must not open the rest of the checkout."""
    repo = _ignoring_repo(tmp_path)
    (repo / "notes").mkdir()
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(repo / "notes")


@needs_git
def test_prepare_refuses_an_ignored_directory_that_holds_a_tracked_file(tmp_path):
    """git calls a NEW file in configs/ ignored even when configs/ holds a force-added tracked
    file, so the ignore answer alone would let a snapshot sit beside committed content."""
    repo = _ignoring_repo(tmp_path)
    (repo / "configs").mkdir()
    (repo / "configs" / "keep.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-f", "configs/keep.txt"],
                   check=True, capture_output=True)
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(repo / "configs")


@needs_git
def test_prepare_refuses_an_ignored_directory_with_a_tracked_file_deeper_down(tmp_path):
    repo = _ignoring_repo(tmp_path)
    (repo / "configs" / "old").mkdir(parents=True)
    (repo / "configs" / "old" / "keep.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-f", "configs/old/keep.txt"],
                   check=True, capture_output=True)
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(repo / "configs")


def _repo_with_ignore(tmp_path, rules):
    repo = _git_repo(tmp_path / "repo")
    (repo / ".gitignore").write_text(rules, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", ".gitignore"], check=True, capture_output=True)
    return repo


def _stages(repo, path):
    """Whether `git add -A` would stage `path`: the question every acceptance must answer no to."""
    out = subprocess.run(["git", "-C", str(repo), "add", "-A", "--dry-run"], check=True,
                         capture_output=True, text=True).stdout
    return path.relative_to(repo).as_posix() in out


@needs_git
@pytest.mark.parametrize("negation", ["!configs/*.xml", "!configs/config-*"])
def test_prepare_refuses_a_folder_whose_negation_re_includes_the_snapshot(tmp_path, negation):
    """Measured: `configs/*` plus a negation made git call the FOLDER ignored while `git add -A`
    staged the snapshot written into it, password hashes and keys included."""
    repo = _repo_with_ignore(tmp_path, f"configs/*\n{negation}\n")
    (repo / "configs").mkdir()
    (repo / "configs" / "config-x.xml").write_text("<pfsense/>", encoding="utf-8")
    assert _stages(repo, repo / "configs" / "config-x.xml"), "the fixture must show the leak"
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(repo / "configs")


@needs_git
def test_prepare_still_accepts_a_negation_for_another_file_only(tmp_path):
    """The control: `configs/*` with `!configs/.gitkeep` keeps every snapshot ignored."""
    repo = _repo_with_ignore(tmp_path, "configs/*\n!configs/.gitkeep\n")
    (repo / "configs").mkdir()
    assert P.prepare_snapshot_dir(repo / "configs") == repo / "configs"


@needs_git
def test_prepare_refuses_a_folder_ignored_only_by_a_per_user_excludes_file(tmp_path, monkeypatch):
    """Another user of the same checkout lacks this file, so for them the snapshot is committable."""
    repo = _git_repo(tmp_path / "repo")
    global_excludes = tmp_path / "my-excludes"
    global_excludes.write_text("configs/\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))  # git's own config file
    (tmp_path / "gitconfig").write_text(f"[core]\n\texcludesFile = {global_excludes}\n",
                                        encoding="utf-8")
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(repo / "configs")


@needs_git
def test_prepare_accepts_a_folder_the_clone_excludes_in_info_exclude(tmp_path):
    repo = _git_repo(tmp_path / "repo")
    with open(repo / ".git" / "info" / "exclude", "a", encoding="utf-8") as handle:
        handle.write("configs/\n")
    assert P.prepare_snapshot_dir(repo / "configs") == repo / "configs"


@needs_git
def test_prepare_accepts_an_untracked_gitignore_in_the_checkout(tmp_path):
    """An untracked .gitignore sits in the shared working tree, so every user of the checkout
    has it; `git add -A` stages the .gitignore and still skips the folder."""
    repo = _git_repo(tmp_path / "repo")
    (repo / ".gitignore").write_text("configs/\n", encoding="utf-8")
    assert P.prepare_snapshot_dir(repo / "configs") == repo / "configs"


@needs_git
@pytest.mark.skipif(os.name != "posix", reason="symlinks need privileges on Windows")
def test_prepare_judges_a_dotdot_path_where_the_file_lands(tmp_path):
    """`notes/../configs` with notes a symlink lands in sub/configs, which nothing ignores."""
    repo = _repo_with_ignore(tmp_path, "/configs/\n")
    (repo / "sub" / "deeper").mkdir(parents=True)
    (repo / "notes").symlink_to(repo / "sub" / "deeper")
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(repo / "notes" / ".." / "configs")


@needs_git
def test_prepare_accepts_an_ignored_folder_with_a_non_ascii_name(tmp_path):
    """git quotes a non-ASCII path in its answer unless told not to, which read as not ignored."""
    name = "B" + chr(0x00FC) + "ro"
    repo = _repo_with_ignore(tmp_path, name + "/\n")
    assert P.prepare_snapshot_dir(repo / name) == repo / name


@needs_git
def test_the_repo_checks_ignore_an_inherited_git_dir(tmp_path, monkeypatch):
    """A GIT_DIR from a hook would answer from another repository's index and excludes."""
    repo = _git_repo(tmp_path / "repo")
    with open(repo / ".git" / "info" / "exclude", "a", encoding="utf-8") as handle:
        handle.write("configs/\n")  # a rule only THIS repository's git dir holds
    other = _git_repo(tmp_path / "other")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))  # the environment a hook can hand down
    assert P.prepare_snapshot_dir(repo / "configs") == repo / "configs"


def test_prepare_refuses_when_the_ignore_question_cannot_be_answered(tmp_path):
    """The exemption fails closed: inside a work tree, a git that errors on check-ignore refuses."""
    target = tmp_path / "repo"
    target.mkdir()

    def git(argv, *, stdin_text=None, timeout=30):
        if "rev-parse" in argv:
            return 0, "true\n", ""
        raise OSError("git vanished")
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(target, run=git)


def test_prepare_refuses_a_check_ignore_that_names_no_path(tmp_path):
    """Only git echoing the directory back counts as ignored, never a bare exit 0."""
    target = tmp_path / "repo"
    target.mkdir()

    def git(argv, *, stdin_text=None, timeout=30):
        return (0, "true\n", "") if "rev-parse" in argv else (0, "", "")
    with pytest.raises(P.PfsenseError, match="git work tree"):
        P.prepare_snapshot_dir(target, run=git)


@needs_git
def test_apply_writes_its_snapshot_into_an_ignored_site_folder(tmp_path):
    """End to end: the call that exited 2 now writes the backup and applies."""
    repo = _ignoring_repo(tmp_path)
    fake = GitPassingFake(_fake_for_mutation().responses)
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(repo / "configs"),
                 "dhcp", "rm", "--mac", "00:11:22:33:44:30"], run=fake)
    assert rc == 0
    assert list((repo / "configs").glob("config-192.0.2.1-*.xml"))


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes only")
def test_prepare_leaves_an_existing_directory_mode_alone(tmp_path, capsys):
    """Only a directory this call created is tightened; a shared one must keep its mode."""
    target = tmp_path / "shared"
    target.mkdir()
    os.chmod(target, 0o755)
    P.prepare_snapshot_dir(target, run=_git_says("false"))
    assert oct(target.stat().st_mode & 0o777) == "0o755"
    assert "readable by others" in capsys.readouterr().err


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes only")
def test_prepare_says_nothing_about_an_existing_private_directory(tmp_path, capsys):
    target = tmp_path / "private"
    target.mkdir()
    os.chmod(target, 0o700)
    P.prepare_snapshot_dir(target, run=_git_says("false"))
    assert capsys.readouterr().err == ""


# ---- the snapshot verb honours the flags its refusal names --------------------------------------
def test_snapshot_verb_writes_to_the_top_level_snapshot_dir(tmp_path):
    fake = FakeRun([("cat /conf/config.xml", (0, CONFIG_XML, BANNER))])
    dest = tmp_path / "chosen"
    assert P.main(["--host", "192.0.2.1", "--snapshot-dir", str(dest), "snapshot"], run=fake) == 0
    assert list(dest.glob("config-192.0.2.1-*.xml"))
    assert not (tmp_path / "xdg-state").exists(), "the default dir must not be used when one is named"


def test_snapshot_verb_dir_flag_wins_over_the_top_level_one(tmp_path):
    fake = FakeRun([("cat /conf/config.xml", (0, CONFIG_XML, BANNER))])
    assert P.main(["--host", "192.0.2.1", "--snapshot-dir", str(tmp_path / "top"),
                   "snapshot", "--dir", str(tmp_path / "verb")], run=fake) == 0
    assert list((tmp_path / "verb").glob("config-*.xml"))
    assert not (tmp_path / "top").exists()


def test_snapshot_verb_honours_allow_repo_snapshot(tmp_path):
    fake = FakeRun([("cat /conf/config.xml", (0, CONFIG_XML, BANNER)),
                    ("rev-parse", (0, "true", ""))])
    repo = tmp_path / "repo"
    repo.mkdir()
    refused = P.main(["--host", "192.0.2.1", "snapshot", "--dir", str(repo)], run=_ssh_and_git(fake))
    allowed = P.main(["--host", "192.0.2.1", "--allow-repo-snapshot", "snapshot", "--dir", str(repo)],
                     run=_ssh_and_git(fake))
    assert (refused, allowed) == (2, 0)
    assert len(list(repo.glob("config-*.xml"))) == 1


def _ssh_and_git(fake):
    """Answer git's work-tree probe with "inside" and everything else from `fake`."""
    def run(argv, *, stdin_text=None, timeout=30):
        if argv[0] == "git":
            return 0, "true\n", ""
        return fake(argv, stdin_text=stdin_text, timeout=timeout)
    return run


# ---- named targets ------------------------------------------------------------------------------
def test_a_percent_in_the_ini_ssh_line_is_taken_literally(tmp_path):
    """ssh's own ControlPath tokens use %; interpolation turned them into a traceback."""
    ini = tmp_path / "home" / "pfsense.ini"
    ini.parent.mkdir(parents=True)
    ini.write_text("[home]\nhost = 192.0.2.1\nssh = ssh -o ControlPath=~/.ssh/cm-%r@%h:%p\n",
                   encoding="utf-8")
    fake = FakeRun([('config_get_path("dhcpd"', (0, "[]", ""))])
    assert P.main(["--fw", "home", "--json", "dhcp", "list"], run=fake) == 0
    assert "ControlPath=~/.ssh/cm-%r@%h:%p" in fake.calls[0]["argv"]


def _named_ssh(tmp_path, ssh_line: str) -> str:
    ini = tmp_path / "pfsense.ini"
    ini.write_text(f"[home]\nhost = 192.0.2.1\nport = 2222\nssh = {ssh_line}\n", encoding="utf-8")
    return P.load_named_target("home", path=ini).ssh


def test_an_ini_that_escapes_its_percents_still_means_a_single_percent(tmp_path):
    """An ini written for ConfigParser's default interpolation doubles every % (`%%r`). Read raw,
    that reached ssh as `%%r`, which ssh reads as a literal percent: the ControlPath silently
    changed to a different socket instead of failing."""
    assert _named_ssh(tmp_path, "ssh -o ControlPath=~/.ssh/cm-%%r@%%h:%%p") == (
        "ssh -o ControlPath=~/.ssh/cm-%r@%h:%p"
    )


@pytest.mark.parametrize(
    "line",
    [
        "ssh -o ControlPath=~/.ssh/cm-%r@%h:%p",  # raw ssh tokens: the case interpolation broke
        "ssh -o ControlPath=~/.ssh/cm-%%r@%h:%p",  # mixed: not valid escaping, so taken as written
        "ssh -o ControlPath=%(missing)s",  # a reference to nothing: taken as written
    ],
)
def test_an_ini_value_that_is_not_valid_escaping_is_taken_literally(tmp_path, line):
    assert _named_ssh(tmp_path, line) == line


def test_an_ini_reference_to_another_key_still_resolves(tmp_path):
    """The escaped dialect also allowed `%(key)s`; an ini relying on it keeps working."""
    assert _named_ssh(tmp_path, "ssh -p %(port)s") == "ssh -p 2222"


def test_a_malformed_ini_is_a_typed_error_not_a_traceback(tmp_path, capsys):
    ini = tmp_path / "home" / "pfsense.ini"
    ini.parent.mkdir(parents=True)
    ini.write_text("host = 192.0.2.1\n", encoding="utf-8")
    assert P.main(["--fw", "home", "--json", "dhcp", "list"], run=FakeRun()) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_the_named_target_file_is_read_from_the_environment_at_call_time(tmp_path, monkeypatch):
    other = tmp_path / "other.ini"
    other.write_text("[box]\nhost = 192.0.2.7\n", encoding="utf-8")
    monkeypatch.setenv("PFSENSE_JIG_CONFIG", str(other))
    assert P.load_named_target("box").host == "192.0.2.7"


# ---- Windows command lines ----------------------------------------------------------------------
def test_a_windows_key_path_keeps_its_backslashes():
    argv = P.split_command(r"ssh -i C:\Users\me\.ssh\id_ed25519", windows=True)
    assert argv == ["ssh", "-i", r"C:\Users\me\.ssh\id_ed25519"]


def test_windows_splitting_honours_double_quotes_around_a_path_with_spaces():
    argv = P.split_command(r'"C:\Program Files\OpenSSH\ssh.exe" -i "C:\my keys\id" -p 22', windows=True)
    assert argv == [r"C:\Program Files\OpenSSH\ssh.exe", "-i", r"C:\my keys\id", "-p", "22"]


def test_windows_splitting_follows_the_backslash_before_quote_rules():
    """2n backslashes then a quote give n backslashes and a delimiter; 2n+1 give a literal quote."""
    assert P.split_command(r'a\\"b c"', windows=True) == ["a\\b c"]
    assert P.split_command(r'a\"b', windows=True) == ['a"b']


def test_posix_splitting_is_unchanged():
    assert P.split_command("ssh -i '/a key/id' -F /cfg", windows=False) == ["ssh", "-i", "/a key/id", "-F", "/cfg"]


# ---- dns ----------------------------------------------------------------------------------------
BARE_OVERRIDES = json.dumps([
    {"host": "", "domain": "bare.example.com", "ip": "192.0.2.40", "descr": ""},
    {"host": "nas", "domain": "example.com", "ip": "192.0.2.31", "descr": ""},
])


def _unbound_up():
    """A restart that works and an unbound that answers every name these tests write or keep."""
    return [
        ("pfSsh.php playback svc restart unbound", (0, "", "")),
        ("host new.example.com 127.0.0.1", (0, "new.example.com has address 192.0.2.41\n", "")),
        ("host nas.example.com 127.0.0.1", (0, "nas.example.com has address 192.0.2.31\n", "")),
        ("host bare.example.com 127.0.0.1", (0, "bare.example.com has address 192.0.2.40\n", "")),
    ]


def _dns_fake():
    return FakeRun([
        *_unbound_up(),
        ("$removed", (0, '{"removed":[{"host":"","domain":"bare.example.com","ip":"192.0.2.40"}]}', "")),
        ("$hosts[] =", (0, '{"added":{"host":"x","domain":"example.com","ip":"192.0.2.9"}}', "")),
        ('config_get_path("unbound/hosts"', (0, BARE_OVERRIDES, BANNER)),
        ("cat /conf/config.xml", (0, CONFIG_XML, BANNER)),
    ])


def _rm_body(fake):
    return next(b for b in fake.php_bodies() if "write_config" in b)


def test_dns_rm_of_an_override_with_no_host_part_targets_the_stored_fields(tmp_path):
    """Re-splitting bare.example.com gives host 'bare', which matches no stored entry on --apply."""
    fake = _dns_fake()
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path / "s"),
                 "dns", "rm", "--name", "bare.example.com"], run=fake)
    body = _rm_body(fake)
    assert rc == 0
    assert "=== ''" in body and "=== 'bare.example.com'" in body
    assert "=== 'bare'" not in body


def test_dns_rm_of_an_ordinary_override_still_targets_host_and_domain(tmp_path):
    fake = _dns_fake()
    P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path / "s"),
            "dns", "rm", "--name", "NAS.example.com"], run=fake)
    body = _rm_body(fake)
    assert "=== 'nas'" in body and "=== 'example.com'" in body


def test_dns_add_refuses_a_name_an_empty_host_override_already_answers(tmp_path):
    """bare.example.com exists with an empty host; adding host 'bare' would shadow it silently."""
    fake = _dns_fake()
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path / "s"),
                 "dns", "add", "--name", "bare.example.com", "--ip", "192.0.2.41"], run=fake)
    assert rc == 2
    assert not any("write_config" in body for body in fake.php_bodies())


def test_dns_add_of_a_new_name_is_sent(tmp_path):
    fake = _dns_fake()
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path / "s"),
                 "dns", "add", "--name", "new.example.com", "--ip", "192.0.2.41"], run=fake)
    assert rc == 0
    assert any("write_config" in body and "'new'" in body for body in fake.php_bodies())


def test_dns_add_without_apply_sends_nothing():
    fake = _dns_fake()
    assert P.main(["--host", "192.0.2.1", "dns", "add", "--name", "new.example.com",
                   "--ip", "192.0.2.41"], run=fake) == 0
    assert fake.calls == []


# ---- after services_unbound_configure(): restart unbound and check it answers -------------------
# A reconfigure has been observed to leave unbound stopped with every lookup timing out, so both
# writing verbs restart it the pfSense way and resolve a name through 127.0.0.1 before reporting
# success. The commands are the ones SKILL.md tells a reader to run, so the two cannot drift.
RESTART = "pfSsh.php playback svc restart unbound"


def _answer(name, ip):
    """What `host <name> 127.0.0.1` prints on a pfSense box when unbound answers."""
    header = "Using domain server:\nName: 127.0.0.1\nAddress: 127.0.0.1#53\nAliases: \n\n"
    return (0, f"{header}{name} has address {ip}\n", "")


TIMED_OUT = (1, ";; connection timed out; no servers could be reached\n", "")


def _unbound_fake(probe_name, probe_answer, restart=(0, "", ""), overrides=BARE_OVERRIDES):
    fake = _dns_fake()
    fake.responses = [
        (RESTART, restart),
        (f"host {probe_name} 127.0.0.1", probe_answer),
        *[(n, r) for n, r in fake.responses if n != 'config_get_path("unbound/hosts"'],
        ('config_get_path("unbound/hosts"', (0, overrides, BANNER)),
    ]
    return fake


def _remote_after_write(fake):
    write_at = next(i for i, c in enumerate(fake.calls) if c["stdin"] and "write_config" in c["stdin"])
    return [c["remote"] for c in fake.calls[write_at + 1:]]


def _apply(tmp_path, *argv):
    return ["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path / "s"), *argv]


def test_dns_add_restarts_unbound_and_resolves_the_added_name_after_the_write(tmp_path):
    fake = _unbound_fake("new.example.com", _answer("new.example.com", "192.0.2.41"))
    rc = P.main(_apply(tmp_path, "dns", "add", "--name", "new.example.com", "--ip", "192.0.2.41"), run=fake)
    assert rc == 0
    assert _remote_after_write(fake) == [RESTART, "host new.example.com 127.0.0.1"]


def test_dns_add_whose_name_gets_no_answer_after_the_restart_is_exit_2(tmp_path, capsys):
    fake = _unbound_fake("new.example.com", TIMED_OUT)
    rc = P.main(_apply(tmp_path, "--json", "dns", "add", "--name", "new.example.com", "--ip", "192.0.2.41"),
                run=fake)
    out = capsys.readouterr()
    assert rc == 2
    assert json.loads(out.out)["ok"] is False
    assert "was written" in out.err and "not answering" in out.err and RESTART in out.err


def test_dns_add_answered_with_another_address_is_exit_2(tmp_path, capsys):
    fake = _unbound_fake("new.example.com", _answer("new.example.com", "192.0.2.99"))
    rc = P.main(_apply(tmp_path, "dns", "add", "--name", "new.example.com", "--ip", "192.0.2.41"), run=fake)
    assert rc == 2
    assert "192.0.2.41" in capsys.readouterr().err


def test_a_failed_unbound_restart_is_exit_2_and_skips_the_lookup(tmp_path, capsys):
    fake = _unbound_fake("new.example.com", _answer("new.example.com", "192.0.2.41"),
                         restart=(1, "", "unbound failed to start\n"))
    rc = P.main(_apply(tmp_path, "dns", "add", "--name", "new.example.com", "--ip", "192.0.2.41"), run=fake)
    err = capsys.readouterr().err
    assert rc == 2
    assert "was written" in err and "unbound failed to start" in err
    assert _remote_after_write(fake) == [RESTART]


def test_a_lookup_that_hits_the_process_timeout_still_says_the_change_was_written(tmp_path, capsys):
    fake = _unbound_fake("new.example.com", (0, "", ""))
    plain = fake

    def run(argv, *, stdin_text=None, timeout=30):
        if argv[-1].startswith("host "):
            raise subprocess.TimeoutExpired(cmd="ssh", timeout=timeout)
        return plain(argv, stdin_text=stdin_text, timeout=timeout)

    rc = P.main(_apply(tmp_path, "dns", "add", "--name", "new.example.com", "--ip", "192.0.2.41"), run=run)
    assert rc == 2
    assert "was written" in capsys.readouterr().err


def test_dns_rm_restarts_unbound_and_resolves_an_override_that_remains(tmp_path):
    """bare.example.com goes; nas.example.com stays and has a known local answer."""
    fake = _unbound_fake("nas.example.com", _answer("nas.example.com", "192.0.2.31"))
    rc = P.main(_apply(tmp_path, "dns", "rm", "--name", "bare.example.com"), run=fake)
    assert rc == 0
    assert _remote_after_write(fake) == [RESTART, "host nas.example.com 127.0.0.1"]


def test_dns_rm_of_the_last_override_resolves_localhost(tmp_path):
    only = json.dumps([{"host": "", "domain": "bare.example.com", "ip": "192.0.2.40", "descr": ""}])
    fake = _unbound_fake("localhost.", _answer("localhost", "127.0.0.1"), overrides=only)
    rc = P.main(_apply(tmp_path, "dns", "rm", "--name", "bare.example.com"), run=fake)
    assert rc == 0
    assert _remote_after_write(fake) == [RESTART, "host localhost. 127.0.0.1"]


def test_dns_rm_whose_check_gets_no_answer_is_exit_2(tmp_path, capsys):
    fake = _unbound_fake("nas.example.com", TIMED_OUT)
    rc = P.main(_apply(tmp_path, "dns", "rm", "--name", "bare.example.com"), run=fake)
    err = capsys.readouterr().err
    assert rc == 2
    assert "was written" in err and "not answering" in err


def test_the_probe_name_is_quoted_for_the_remote_shell():
    assert P.unbound_probe_command("a.example.com;reboot") == "host 'a.example.com;reboot' 127.0.0.1"


def test_skill_md_tells_the_reader_the_same_commands_the_verbs_run():
    skill = (pathlib.Path(P.__file__).resolve().parent.parent / "SKILL.md").read_text(encoding="utf-8")
    assert P.UNBOUND_RESTART == RESTART
    assert f"`{P.UNBOUND_RESTART}`" in skill
    assert f"`{P.unbound_probe_command('NAME').replace('NAME', '<name>')}`" in skill


# ---- dhcp add / rename: the two edits that otherwise need the GUI ---------------------------------
INFO_JSON = json.dumps({
    "version": "2.8.0", "dhcp_backend": "isc", "resolver": "unbound", "packages": [],
    "interfaces": [
        {"name": "wan", "if": "igb0", "descr": "WAN", "ipaddr": "dhcp", "subnet": ""},
        {"name": "lan", "if": "igb1", "descr": "LAN", "ipaddr": "192.0.2.1", "subnet": "24"},
        {"name": "opt1", "if": "igb2", "descr": "IOT", "ipaddr": "198.51.100.1", "subnet": "24"},
    ],
})


def _dhcp_edit_fake():
    # The edit payloads also read config_get_path("dhcpd"), so their markers come first.
    return FakeRun([
        ("$added", (0, '{"added":{"interface":"lan","mac":"00:11:22:33:44:50","ip":"192.0.2.50",'
                       '"hostname":"printer"},"unbound_follows":false}', "")),
        ("$renamed", (0, '{"renamed":[{"interface":"lan","ip":"192.0.2.31"}],"unbound_follows":false}', "")),
        ('"dhcp_backend"', (0, INFO_JSON, BANNER)),
        ('config_get_path("dhcpd"', (0, RESERVATIONS_JSON, BANNER)),
        ("cat /conf/config.xml", (0, CONFIG_XML, BANNER)),
    ])


def _writes(fake):
    return [body for body in fake.php_bodies() if "write_config" in body]


def test_the_interface_for_an_address_is_the_one_whose_subnet_holds_it():
    interfaces = P.FirewallInfo.from_json(json.loads(INFO_JSON)).interfaces
    assert P.interface_for_ip(interfaces, "192.0.2.50") == "lan"
    assert P.interface_for_ip(interfaces, "198.51.100.9") == "opt1"
    with pytest.raises(P.PfsenseError, match="no interface"):
        P.interface_for_ip(interfaces, "203.0.113.5")


def test_dhcp_add_refuses_an_address_outside_the_named_interface(capsys):
    """--interface opt1 with a LAN address would be stored and never served."""
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "dhcp", "add", "--mac", "00:11:22:33:44:50",
                 "--ip", "192.0.2.50", "--hostname", "printer", "--interface", "opt1"], run=fake)
    assert rc == 2
    assert "192.0.2.50" in capsys.readouterr().err
    assert _writes(fake) == []


def test_dhcp_add_accepts_the_named_interface_that_holds_the_address():
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "dhcp", "add", "--mac", "00:11:22:33:44:50",
                 "--ip", "198.51.100.9", "--hostname", "sensor", "--interface", "opt1"], run=fake)
    assert rc == 0


def test_dhcp_add_without_apply_writes_nothing():
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "dhcp", "add", "--mac", "00:11:22:33:44:50",
                 "--ip", "192.0.2.50", "--hostname", "printer"], run=fake)
    assert rc == 0
    assert _writes(fake) == []


def test_dhcp_add_apply_snapshots_and_sends_the_reservation_on_the_inferred_interface(tmp_path):
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "--json", "--apply", "--snapshot-dir", str(tmp_path),
                 "dhcp", "add", "--mac", "00-11-22-33-44-50", "--ip", "192.0.2.50",
                 "--hostname", "printer"], run=fake)
    assert rc == 0
    (body,) = _writes(fake)
    assert "'lan'" in body and "'00:11:22:33:44:50'" in body and "'192.0.2.50'" in body
    assert "'printer'" in body
    assert list(tmp_path.glob("config-192.0.2.1-*.xml")), "no snapshot before the write"


@pytest.mark.parametrize("mac, ip", [("00:11:22:33:44:31", "192.0.2.50"),   # MAC taken
                                     ("00:11:22:33:44:50", "192.0.2.31")])  # address taken
def test_dhcp_add_refuses_a_duplicate_before_anything_is_written(tmp_path, mac, ip, capsys):
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path),
                 "dhcp", "add", "--mac", mac, "--ip", ip, "--hostname", "printer"], run=fake)
    assert rc == 2
    assert "already" in capsys.readouterr().err
    assert _writes(fake) == []
    assert not list(tmp_path.glob("*.xml")), "a refused add took a snapshot"


@pytest.mark.parametrize("hostname", ["has.dot", "-lead", "bad_char", "x" * 64])
def test_dhcp_add_refuses_a_hostname_pfsense_would_reject(hostname):
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "dhcp", "add", "--mac", "00:11:22:33:44:50",
                 "--ip", "192.0.2.50", f"--hostname={hostname}"], run=fake)
    assert rc == 2
    assert fake.calls == []


def test_dhcp_rename_dry_run_names_old_and_new(capsys):
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "dhcp", "rename", "--mac", "00:11:22:33:44:31",
                 "--hostname", "storage"], run=fake)
    assert rc == 0
    out = capsys.readouterr().out
    assert "nas" in out and "storage" in out
    assert _writes(fake) == []


def test_dhcp_rename_apply_sends_only_the_new_name(tmp_path):
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path),
                 "dhcp", "rename", "--mac", "00:11:22:33:44:31", "--hostname", "storage"], run=fake)
    assert rc == 0
    (body,) = _writes(fake)
    assert "'storage'" in body and "'00:11:22:33:44:31'" in body


def test_dhcp_rename_of_an_unknown_mac_is_refused():
    fake = _dhcp_edit_fake()
    rc = P.main(["--host", "192.0.2.1", "--apply", "dhcp", "rename", "--mac", "aa:bb:cc:dd:ee:ff",
                 "--hostname", "storage"], run=fake)
    assert rc == 2
    assert _writes(fake) == []


# ---- the envelope's ok means "ran without error", also on a well-formed no -----------------------
def test_a_doctor_with_findings_exits_1_with_ok_true(tmp_path, capsys):
    config = tmp_path / "config.xml"
    config.write_text(CONFIG_XML, encoding="utf-8", newline="")
    rc = P.main(["--json", "doctor", "--config", str(config)])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["ok"] is True and payload["data"]


# ---- table: missing operands are usage errors, not verdicts -------------------------------------
@pytest.mark.parametrize("argv", [
    ["table", "show"],
    ["table", "test"],
    ["table", "test", "snort2c"],
    ["table", "del"],
    ["table", "del", "snort2c"],
    ["table", "del", "snort2c", "--apply"],
])
def test_table_without_its_operands_is_exit_2_and_runs_nothing(argv):
    fake = FakeRun([("-T show", (0, "  192.0.2.5\n", ""))])
    assert P.main(["--host", "192.0.2.1", *argv], run=fake) == 2
    assert fake.calls == []


def test_table_del_apply_deletes_and_confirms():
    fake = FakeRun([("-T show", (0, "  192.0.2.6\n", ""))])
    rc = P.main(["--host", "192.0.2.1", "table", "del", "snort2c", "192.0.2.5", "--apply"], run=fake)
    assert rc == 0
    assert any("-T delete 192.0.2.5" in c["remote"] for c in fake.calls)


def test_table_del_of_one_address_that_survives_is_a_failed_action_exit_2(capsys):
    """W-D9: one address asked for and still present is not a partial outcome - nothing happened."""
    fake = FakeRun([("-T show", (0, "  192.0.2.5\n", ""))])
    rc = P.main(["--host", "192.0.2.1", "--json", "table", "del", "snort2c", "192.0.2.5", "--apply"], run=fake)
    out = capsys.readouterr()
    assert rc == 2
    assert json.loads(out.out)["ok"] is False and "192.0.2.5" in out.err


def test_table_del_of_several_where_some_survive_is_partial_exit_1(capsys):
    fake = FakeRun([("-T show", (0, "  192.0.2.5\n", ""))])
    rc = P.main(["--host", "192.0.2.1", "--json", "table", "del", "snort2c", "192.0.2.5", "192.0.2.6",
                 "--apply"], run=fake)
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["ok"] is True and payload["data"]["still_present"] == ["192.0.2.5"]


def test_table_del_of_several_where_all_survive_is_a_failed_action_exit_2():
    fake = FakeRun([("-T show", (0, "  192.0.2.5\n  192.0.2.6\n", ""))])
    assert P.main(["--host", "192.0.2.1", "table", "del", "snort2c", "192.0.2.5", "192.0.2.6",
                   "--apply"], run=fake) == 2


# ---- snort --------------------------------------------------------------------------------------
PS_SNORT = "root 1 snort -R 1 -c /usr/local/etc/snort/snort_1_igb0/snort.conf -i igb0\n"


def _verify(supp, *extra):
    fake = FakeRun([("ps auxww", (0, PS_SNORT, "")), ("/supp*", (0, supp, ""))])
    return P.main(["--host", "192.0.2.1", "snort", "verify", "--sid", "2071408", *extra], run=fake)


def test_snort_verify_counts_a_live_suppression():
    assert _verify("suppress gen_id 1, sig_id 2071408\n") == 0


def test_snort_verify_does_not_count_a_commented_out_suppression():
    assert _verify("#suppress gen_id 1, sig_id 2071408\n") == 1
    assert _verify("  # suppress gen_id 1, sig_id 2071408\n") == 1


def test_snort_verify_does_not_count_a_sid_named_only_in_a_trailing_comment():
    assert _verify("suppress gen_id 1, sig_id 999 # was sig_id 2071408\n") == 1


def test_snort_verify_without_the_sid_is_no():
    assert _verify("suppress gen_id 1, sig_id 999\n") == 1


def _verify_sid(sid, supp, *extra):
    fake = FakeRun([("ps auxww", (0, PS_SNORT, "")), ("/supp*", (0, supp, ""))])
    return P.main(["--host", "192.0.2.1", "snort", "verify", "--sid", sid, *extra], run=fake)


def test_snort_verify_does_not_count_the_same_sid_under_another_generator():
    """The no-op fix the old fixsteps printed must not then read as verified."""
    assert _verify_sid("125:9", "suppress gen_id 1, sig_id 9\n") == 1


def test_snort_verify_counts_the_suppression_of_the_generator_given():
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 9\n") == 0
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 9, track by_src, ip 192.0.2.146\n",
                       "--ip", "192.0.2.146") == 0


def test_snort_verify_counts_sig_id_0_as_every_signature_of_its_generator():
    """Snort's README.filters: sig_id 0 "applies to all sig_ids for the given gen_id"."""
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 0\n") == 0
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 0, track by_src, ip 192.0.2.146\n",
                       "--ip", "192.0.2.146") == 0


def test_snort_verify_does_not_count_sig_id_0_of_another_generator():
    assert _verify_sid("125:9", "suppress gen_id 1, sig_id 0\n") == 1


def test_snort_verify_does_not_read_a_sid_starting_with_0_as_the_wildcard():
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 09\n") == 1


# ---- snort verify: a scoped suppression covers only the addresses it lists -----------------------
# Snort's README.filters: `suppress gen_id G, sig_id S` suppresses the event completely, while
# `..., track by_src|by_dst, ip <ip>` suppresses it only where that side of the alert is <ip>
# (a single address or a CIDR block).
SCOPED_SRC = "suppress gen_id 125, sig_id 9, track by_src, ip 192.0.2.146\n"


def _verify_json(sid, supp, *extra, passlist=""):
    fake = FakeRun([("ps auxww", (0, PS_SNORT, "")), ("/supp*", (0, supp, "")),
                    ("*Whitelist*", (0, passlist, ""))])
    return P.main(["--host", "192.0.2.1", "--json", "snort", "verify", "--sid", sid, *extra], run=fake)


def test_snort_verify_says_no_for_an_address_a_scoped_suppression_does_not_list(capsys):
    """The block on another source recurs, so verify must not say yes for it."""
    assert _verify_sid("125:9", SCOPED_SRC, "--ip", "192.0.2.7") == 1
    out = capsys.readouterr().out
    assert "192.0.2.7: NO" in out
    assert "track by_src, ip 192.0.2.146" in out


def test_snort_verify_without_an_address_does_not_call_a_scoped_suppression_complete(capsys):
    assert _verify_sid("125:9", SCOPED_SRC) == 1
    out = capsys.readouterr().out
    assert "only for track by_src, ip 192.0.2.146" in out and "--ip" in out


def test_snort_verify_names_the_direction_a_scoped_suppression_covers(capsys):
    assert _verify_sid("125:9", SCOPED_SRC, "--ip", "192.0.2.146") == 0
    assert "192.0.2.146: yes (track by_src" in capsys.readouterr().out


def test_snort_verify_an_unscoped_suppression_covers_every_address(capsys):
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 9\n", "--ip", "203.0.113.5") == 0
    assert "every address" in capsys.readouterr().out


def test_snort_verify_matches_an_address_against_a_cidr_scope():
    supp = "suppress gen_id 1, sig_id 2071408, track by_dst, ip 198.51.100.0/24\n"
    assert _verify_sid("1:2071408", supp, "--ip", "198.51.100.7") == 0
    assert _verify_sid("1:2071408", supp, "--ip", "198.51.101.7") == 1
    assert _verify_sid("1:2071408", supp, "--ip", "2001:db8::1") == 1


def test_snort_verify_matches_against_each_member_of_a_bracketed_list():
    supp = "suppress gen_id 1, sig_id 9, track by_src, ip [192.0.2.5, 198.51.100.0/24]\n"
    assert _verify_sid("1:9", supp, "--ip", "192.0.2.5") == 0
    assert _verify_sid("1:9", supp, "--ip", "198.51.100.200") == 0
    assert _verify_sid("1:9", supp, "--ip", "192.0.2.6") == 1


def test_snort_verify_checks_every_address_given():
    assert _verify_sid("125:9", SCOPED_SRC, "--ip", "192.0.2.146", "--ip", "192.0.2.7") == 1


@pytest.mark.parametrize("ip_value", ["$HOME_NET", "!192.0.2.146", "[192.0.2.146,!192.0.2.7]", "bogus"])
def test_snort_verify_does_not_count_a_scope_it_cannot_read(ip_value, capsys):
    """A variable or a negation is not evaluated here, so NO is the safe reading."""
    supp = f"suppress gen_id 125, sig_id 9, track by_src, ip {ip_value}\n"
    assert _verify_sid("125:9", supp, "--ip", "192.0.2.146") == 1
    assert "not understood" in capsys.readouterr().out


def test_snort_verify_does_not_count_track_without_ip_or_an_unknown_track():
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 9, track by_src\n", "--ip", "192.0.2.1") == 1
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 9, ip 192.0.2.1\n", "--ip", "192.0.2.1") == 1
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 9, track by_any, ip 192.0.2.1\n",
                       "--ip", "192.0.2.1") == 1


def test_snort_verify_an_unscoped_line_beside_a_scoped_one_covers_everything():
    supp = SCOPED_SRC + "suppress gen_id 125, sig_id 9\n"
    assert _verify_sid("125:9", supp, "--ip", "192.0.2.7") == 0


def test_snort_verify_checks_the_cidr_is_inside_a_scoped_suppression(capsys):
    supp = "suppress gen_id 1, sig_id 9, track by_dst, ip 198.51.100.0/22\n"
    assert _verify_json("1:9", supp, "--cidr", "198.51.100.0/24", passlist="198.51.100.0/24\n") == 0
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["suppressions"] == [{"track": "by_dst", "ip": "198.51.100.0/22", "understood": True}]
    assert data["coverage"] == {"198.51.100.0/24": ["by_dst"]}
    assert _verify_json("1:9", supp, "--cidr", "198.51.96.0/20", passlist="198.51.96.0/20\n") == 1


def test_snort_verify_refuses_an_ip_that_is_not_an_address():
    assert _verify_sid("125:9", SCOPED_SRC, "--ip", "192.0.2.300") == 2


def test_snort_verify_needs_both_ids_in_one_live_statement():
    """Two half-matching lines, or a SID only in a comment, suppress nothing for 125:9. A reversed
    statement reads NO: only the order pfSense writes is trusted."""
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 8\nsuppress gen_id 1, sig_id 9\n") == 1
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 8 # sig_id 9\n") == 1
    assert _verify_sid("125:9", "suppress sig_id 9, gen_id 125\n") == 1


def test_snort_verify_matches_whole_numbers_only():
    assert _verify_sid("1:9", "suppress gen_id 125, sig_id 9\n") == 1
    assert _verify_sid("125:9", "suppress gen_id 125, sig_id 99\n") == 1
    assert _verify_sid("12:9", "suppress gen_id 125, sig_id 9\n") == 1


def test_snort_verify_with_a_bare_sid_means_gen_id_1_and_says_so(capsys):
    assert _verify_sid("9", "suppress gen_id 125, sig_id 9\n") == 1
    out = capsys.readouterr().out
    assert "1:9" in out and "gen_id 1 assumed" in out


def test_snort_verify_refuses_a_malformed_sid():
    assert _verify_sid("9;x", "suppress gen_id 1, sig_id 9\n") == 2


def test_snort_verify_is_an_error_when_snort_is_not_running():
    fake = FakeRun([("ps auxww", (0, "root 1 /sbin/init\n", ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "verify", "--sid", "1"], run=fake) == 2


ALERT_OLD = '08/01-10:00:00.000000,1,2071408,1,"OLD alert",TCP,192.0.2.7,443,198.51.100.9,80\n'
ALERT_NEW = '08/02-10:00:00.000000,1,2071408,1,"NEW alert",TCP,192.0.2.7,443,198.51.100.9,80\n'


def test_snort_why_labels_the_newest_alert_latest_whatever_the_file_order(capsys):
    """The current file is read before the rotated ones, so the last line is the OLDEST."""
    fake = FakeRun([("/var/log/snort", (0, ALERT_NEW + ALERT_OLD, ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "why", "198.51.100.9"], run=fake) == 0
    assert "latest: 08/02-10:00:00.000000  NEW alert" in capsys.readouterr().out


def test_snort_why_reports_gid_colon_sid(capsys):
    """It printed 'SID(s) 9' for a generator-125 alert, and the 9 led to the wrong suppression."""
    fake = FakeRun([("/var/log/snort", (0, ALERT_GID_125 + ALERT_OLD, ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "why", "198.51.100.105"], run=fake) == 0
    out = capsys.readouterr().out
    assert "GID:SID 125:9" in out
    assert "fixsteps --sid 125:9" in out


def test_snort_why_lists_each_gid_sid_pair_in_numeric_order(capsys):
    lines = ALERT_GID_125 + ALERT_GID_125.replace(",125,9,", ",1,2071408,") + ALERT_GID_125.replace(",125,9,", ",1,9,")
    fake = FakeRun([("/var/log/snort", (0, lines, ""))])
    assert P.main(["--host", "192.0.2.1", "--json", "snort", "why", "198.51.100.105"], run=fake) == 0
    result = json.loads(capsys.readouterr().out)
    assert [(a["gid"], a["sid"]) for a in result["data"]["198.51.100.105"]] == [
        ("125", "9"), ("1", "2071408"), ("1", "9")]
    fake = FakeRun([("/var/log/snort", (0, lines, ""))])
    P.main(["--host", "192.0.2.1", "snort", "why", "198.51.100.105"], run=fake)
    assert "GID:SID 1:9, 1:2071408, 125:9" in capsys.readouterr().out


def _snort_line(moment: datetime.datetime, message: str) -> str:
    return (moment.strftime("%m/%d-%H:%M:%S.000000")
            + f',1,2071408,1,"{message}",TCP,192.0.2.7,443,198.51.100.9,80\n')


def test_snort_why_infers_the_year_from_the_firewall_clock_not_the_local_one(capsys):
    """The stamps are the FIREWALL's local time. With the firewall two hours ahead of this
    machine, an alert 30 minutes old there is 'in the future' here, so a local-clock inference
    put it a year back and labelled an older alert latest."""
    firewall_now = datetime.datetime.now().replace(microsecond=0) + datetime.timedelta(hours=2)
    recent = _snort_line(firewall_now - datetime.timedelta(minutes=30), "RECENT alert")
    older = _snort_line(firewall_now - datetime.timedelta(hours=3), "OLDER alert")
    clock = firewall_now.strftime(f"{P.CLOCK_MARKER} %Y-%m-%dT%H:%M:%S\n")
    fake = FakeRun([("/var/log/snort", (0, clock + older + recent, ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "why", "198.51.100.9"], run=fake) == 0
    assert "RECENT alert" in capsys.readouterr().out.split("latest:")[1]
    assert "date " in fake.calls[0]["remote"]


def test_snort_why_without_a_firewall_clock_says_it_used_the_local_one(capsys):
    """Control: no clock line, so the local clock decides - and the envelope says so."""
    fake = FakeRun([("/var/log/snort", (0, ALERT_NEW + ALERT_OLD, ""))])
    assert P.main(["--host", "192.0.2.1", "--json", "snort", "why", "198.51.100.9"], run=fake) == 0
    result = json.loads(capsys.readouterr().out)
    assert any("local clock" in s for s in result["skipped"])
    assert [a["message"] for a in result["data"]["198.51.100.9"]] == ["NEW alert", "OLD alert"]


def test_snort_why_with_the_firewall_clock_skips_nothing(capsys):
    clock = f"{P.CLOCK_MARKER} 2026-08-03T12:00:00\n"
    fake = FakeRun([("/var/log/snort", (0, clock + ALERT_NEW, ""))])
    assert P.main(["--host", "192.0.2.1", "--json", "snort", "why", "198.51.100.9"], run=fake) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["skipped"] == []
    assert len(result["data"]["198.51.100.9"]) == 1


def _alert(stamp: str, message: str) -> P.Alert:
    return P.Alert(timestamp=stamp, gid="1", sid="1", message=message, src="192.0.2.7", dst="198.51.100.9")


def test_latest_alert_crosses_a_year_boundary():
    """Snort's MM/DD stamp carries no year, so as TEXT a December alert outranks the January one
    written after it. Each stamp belongs to the most recent year that does not put it in the
    future."""
    alerts = [_alert("01/02-08:00:00.000000", "january"), _alert("12/31-23:00:00.000000", "december")]
    now = datetime.datetime(2027, 1, 3, 12, 0, 0)
    assert P.latest_alert(alerts, now=now).message == "january"


def test_latest_alert_within_one_year_is_plain_time_order():
    """Control: away from the boundary the later stamp is still the latest, and a December alert
    seen in December is this year's, not last year's."""
    alerts = [_alert("12/01-08:00:00.000000", "first"), _alert("12/02-08:00:00.000000", "second")]
    assert P.latest_alert(alerts, now=datetime.datetime(2026, 12, 5)).message == "second"


def test_latest_alert_honours_a_year_when_snort_logs_one():
    """`snort -y` writes MM/DD/YY: the year is then read, never inferred."""
    alerts = [_alert("12/31/25-23:00:00.000000", "old"), _alert("01/02/26-08:00:00.000000", "new")]
    assert P.latest_alert(alerts, now=datetime.datetime(2026, 6, 1)).message == "new"


def test_latest_alert_puts_an_unparseable_stamp_last():
    alerts = [_alert("garbage", "bad"), _alert("03/04-05:06:07.000000", "good")]
    assert P.latest_alert(alerts, now=datetime.datetime(2026, 6, 1)).message == "good"


def test_snort_why_with_no_alert_for_the_ip_is_no():
    fake = FakeRun([("/var/log/snort", (0, ALERT_OLD, ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "why", "203.0.113.1"], run=fake) == 1


def test_snort_unblock_dry_run_sends_nothing():
    fake = FakeRun()
    assert P.main(["--host", "192.0.2.1", "snort", "unblock", "192.0.2.5"], run=fake) == 0
    assert fake.calls == []


def test_snort_unblock_apply_confirms_by_rereading_the_table():
    cleared = FakeRun([("-T show", (0, "", ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "unblock", "192.0.2.5", "--apply"], run=cleared) == 0
    stuck = FakeRun([("-T show", (0, "  192.0.2.5\n", ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "unblock", "192.0.2.5", "--apply"], run=stuck) == 2


def test_snort_unblock_of_several_where_some_stay_blocked_is_partial_exit_1():
    stuck = FakeRun([("-T show", (0, "  192.0.2.5\n", ""))])
    assert P.main(["--host", "192.0.2.1", "snort", "unblock", "192.0.2.5", "192.0.2.6", "--apply"],
                  run=stuck) == 1


def test_snort_unblock_of_several_where_all_stay_blocked_is_exit_2(capsys):
    stuck = FakeRun([("-T show", (0, "  192.0.2.5\n  192.0.2.6\n", ""))])
    rc = P.main(["--host", "192.0.2.1", "--json", "snort", "unblock", "192.0.2.5", "192.0.2.6", "--apply"],
                run=stuck)
    assert rc == 2 and json.loads(capsys.readouterr().out)["ok"] is False


# ---- live doctor --------------------------------------------------------------------------------
def _doctor_fake(arp=(0, "", ""), resolv=(0, "nameserver 127.0.0.1\n", ""), lock=(1, "", "")):
    return FakeRun([
        ('config_get_path("dhcpd"', (0, "[]", "")),
        ('config_get_path("unbound/hosts"', (0, "[]", "")),
        ("arp -an", arp),
        ("cat /etc/resolv.conf", resolv),
        ("test -f", lock),
    ])


def test_live_doctor_on_a_healthy_box_is_clean():
    assert P.main(["--host", "192.0.2.1", "doctor"], run=_doctor_fake()) == 0


def test_live_doctor_reports_findings_from_the_live_reads():
    assert P.main(["--host", "192.0.2.1", "doctor"],
                  run=_doctor_fake(resolv=(0, "nameserver 100.100.100.100\n", ""))) == 1


@pytest.mark.parametrize("which", ["arp", "resolv", "lock"])
def test_live_doctor_is_an_error_when_a_read_fails_not_a_clean_bill(which):
    """An ssh drop after the PHP reads used to leave every later check empty, which reads as clean."""
    dropped = (255, "", "Connection closed by 192.0.2.1")
    assert P.main(["--host", "192.0.2.1", "doctor"], run=_doctor_fake(**{which: dropped})) == 2


def test_live_doctor_reads_a_present_lock_as_a_finding():
    assert P.main(["--host", "192.0.2.1", "doctor"], run=_doctor_fake(lock=(0, "", ""))) == 1


LOCK_PATHS = ("/tmp/pfSense-upgrade.lock", "/var/run/pfSense-upgrade.lock")


@pytest.mark.parametrize("present", LOCK_PATHS)
def test_live_doctor_finds_the_lock_at_either_path_and_names_it(present, capsys):
    """The lock has been observed at /tmp, and which of the two paths is current is unverified."""
    absent = next(p for p in LOCK_PATHS if p != present)
    fake = FakeRun([
        ('config_get_path("dhcpd"', (0, "[]", "")),
        ('config_get_path("unbound/hosts"', (0, "[]", "")),
        ("arp -an", (0, "", "")),
        ("cat /etc/resolv.conf", (0, "nameserver 127.0.0.1\n", "")),
        (f"test -f {present}", (0, "", "")),
        (f"test -f {absent}", (1, "", "")),
    ])
    assert P.main(["--host", "192.0.2.1", "--json", "doctor"], run=fake) == 1
    data = json.loads(capsys.readouterr().out)["data"]
    assert [(f["check"], f["subject"]) for f in data] == [("upgrade_lock_present", present)]


def test_live_doctor_tests_both_lock_paths():
    fake = _doctor_fake()
    assert P.main(["--host", "192.0.2.1", "doctor"], run=fake) == 0
    tested = [c["remote"] for c in fake.calls if c["remote"].startswith("test -f")]
    assert sorted(tested) == sorted(f"test -f {p}" for p in LOCK_PATHS)


# ---- arp --permanent really filters -------------------------------------------------------------
def test_arp_permanent_returns_only_the_permanent_entries(capsys):
    fake = FakeRun([("arp -an", (0, ARP_TEXT, BANNER))])
    assert P.main(["--host", "192.0.2.1", "--json", "arp", "--permanent"], run=fake) == 0
    data = json.loads(capsys.readouterr().out)["data"]
    assert [e["ip"] for e in data] == ["192.0.2.30"]


# ---- cross-platform text handling ---------------------------------------------------------------
SCRIPT = pathlib.Path(P.__file__)


def test_a_non_cp1252_character_on_a_cp1252_stdout_does_not_crash(tmp_path):
    """A Windows pipe is cp1252; an unencodable character used to raise mid-report with exit 1.

    The character rides in --cidr, which fixsteps echoes as given; --sid only accepts digits."""
    env = dict(os.environ, PYTHONIOENCODING="cp1252", XDG_STATE_HOME=str(tmp_path))
    env.pop("PYTHONUTF8", None)
    proc = subprocess.run([sys.executable, str(SCRIPT), "snort", "fixsteps", "--sid", "1",
                           "--cidr", chr(0x0141)],
                          capture_output=True, env=env, check=False)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert b"add ? as a LITERAL" in proc.stdout


def test_a_target_file_saved_with_a_bom_still_has_its_first_section(tmp_path):
    """Notepad writes a BOM; configparser then reads '\\ufeff[home]' as no section header."""
    ini = tmp_path / "pfsense.ini"
    ini.write_bytes(b"\xef\xbb\xbf[home]\r\nhost = 192.0.2.1\r\n")
    assert P.load_named_target("home", path=ini).host == "192.0.2.1"


def test_a_form_feed_inside_a_table_line_is_not_a_second_entry():
    assert "192.0.2.6" not in P.parse_table("  192.0.2.5\x0c192.0.2.6\n")
    assert P.parse_table("  192.0.2.5\n  192.0.2.6\n") == {"192.0.2.5", "192.0.2.6"}


# ---- process-level failures are exit 2 with an envelope -----------------------------------------
@pytest.mark.parametrize("exc", [OSError("ssh: not found"),
                                 subprocess.TimeoutExpired(cmd="ssh", timeout=30)])
def test_a_process_failure_is_exit_2_with_a_json_envelope(exc, capsys):
    def boom(*_a, **_k):
        raise exc
    assert P.main(["--host", "192.0.2.1", "--json", "arp"], run=boom) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


# ---- a reservation inside the dynamic pool ------------------------------------------------------
# ISC dhcpd does not keep a reserved address out of its own pool: it leases it to another client,
# its pre-lease ping check misses a host that does not answer ping, and the only trace is a
# "Dynamic and static leases present" line in its log.
POOL_CONFIG_XML = """<?xml version="1.0"?>
<pfsense>
  <dhcpd>
    <lan>
      <enable></enable>
      <range><from>192.0.2.100</from><to>192.0.2.199</to></range>
      <pool><range><from>192.0.2.220</from><to>192.0.2.229</to></range></pool>
      <staticmap><mac>00:11:22:33:44:20</mac><ipaddr>192.0.2.20</ipaddr><hostname>outside</hostname></staticmap>
      <staticmap><mac>00:11:22:33:44:51</mac><ipaddr>192.0.2.150</ipaddr><hostname>runner</hostname></staticmap>
      <staticmap><mac>00:11:22:33:44:52</mac><ipaddr>192.0.2.100</ipaddr><hostname>lowedge</hostname></staticmap>
      <staticmap><mac>00:11:22:33:44:53</mac><ipaddr>192.0.2.199</ipaddr><hostname>highedge</hostname></staticmap>
      <staticmap><mac>00:11:22:33:44:54</mac><ipaddr>192.0.2.225</ipaddr><hostname>extra</hostname></staticmap>
    </lan>
    <opt1>
      <range><from>198.51.100.100</from><to>198.51.100.199</to></range>
      <staticmap><mac>00:11:22:33:44:60</mac><ipaddr>198.51.100.150</ipaddr><hostname>off</hostname></staticmap>
    </opt1>
    <opt2>
      <enable></enable>
      <range><from>203.0.113.100</from><to>203.0.113.199</to></range>
    </opt2>
  </dhcpd>
</pfsense>
"""


def _pool_findings(text=POOL_CONFIG_XML):
    findings = P.doctor_findings(reservations=P.reservations_from_config_xml(text), overrides=[],
                                 pools=P.pools_from_config_xml(text))
    return [f for f in findings if f.check == "static_map_in_dynamic_pool"]


def _pool_findings_subjects():
    return [f.subject.split()[0] for f in _pool_findings()]


def test_pools_are_read_from_enabled_dhcp_servers_including_additional_pools():
    """opt1 has a range but no <enable>: its DHCP server is off, so its range leases nothing."""
    assert P.pools_from_config_xml(POOL_CONFIG_XML) == [
        P.Pool(interface="lan", first="192.0.2.100", last="192.0.2.199"),
        P.Pool(interface="lan", first="192.0.2.220", last="192.0.2.229"),
        P.Pool(interface="opt2", first="203.0.113.100", last="203.0.113.199"),
    ]


def test_doctor_warns_about_a_static_map_inside_its_interfaces_pool_and_names_all_four_parts():
    found = {f.subject.split()[0]: f for f in _pool_findings()}
    runner = found["192.0.2.150"]
    assert runner.severity == "warn"
    for part in ("00:11:22:33:44:51", "runner", "lan", "192.0.2.100-192.0.2.199"):
        assert part in runner.subject
    assert "Dynamic and static leases present" in runner.detail


def test_doctor_counts_both_ends_of_a_pool_and_an_additional_pool():
    """ISC ranges are inclusive, and an additional pool leases dynamically just like the main one."""
    assert sorted(_pool_findings_subjects()) == ["192.0.2.100", "192.0.2.150", "192.0.2.199", "192.0.2.225"]


def test_doctor_ignores_a_static_map_outside_the_pool_and_on_a_disabled_server():
    subjects = _pool_findings_subjects()
    assert "192.0.2.20" not in subjects        # outside the pool
    assert "198.51.100.150" not in subjects    # opt1 serves no DHCP at all


def test_a_pool_on_another_interface_does_not_claim_a_reservation():
    reservations = [res("203.0.113.150", "00:11:22:33:44:70", hostname="x")]
    pools = [P.Pool(interface="opt2", first="203.0.113.100", last="203.0.113.199")]
    assert P.doctor_findings(reservations=reservations, overrides=[], pools=pools) == []


def test_doctor_from_a_snapshot_reports_the_pool_overlap(tmp_path, capsys):
    config = tmp_path / "config.xml"
    config.write_text(POOL_CONFIG_XML, encoding="utf-8", newline="")
    assert P.main(["--json", "doctor", "--config", str(config)]) == 1
    data = json.loads(capsys.readouterr().out)["data"]
    assert "static_map_in_dynamic_pool" in {f["check"] for f in data}


def test_live_doctor_reads_the_pools_and_reports_the_overlap(capsys):
    reservations = json.dumps([{"interface": "lan", "mac": "00:11:22:33:44:51", "ip": "192.0.2.150",
                                "hostname": "runner", "descr": "", "static_arp": False}])
    pools = json.dumps([{"interface": "lan", "from": "192.0.2.100", "to": "192.0.2.199"}])
    fake = FakeRun([
        ("$pools", (0, pools, "")),
        ('config_get_path("dhcpd"', (0, reservations, "")),
        ('config_get_path("unbound/hosts"', (0, "[]", "")),
        ("arp -an", (0, "", "")),
        ("cat /etc/resolv.conf", (0, "nameserver 127.0.0.1\n", "")),
        ("test -f", (1, "", "")),
    ])
    assert P.main(["--host", "192.0.2.1", "--json", "doctor"], run=fake) == 1
    data = json.loads(capsys.readouterr().out)["data"]
    assert [f["check"] for f in data] == ["static_map_in_dynamic_pool"]


def test_the_pool_read_skips_a_disabled_dhcp_server_by_testing_the_key_not_its_value():
    """<enable></enable> reads back as "", so a truthiness test would skip every enabled server."""
    body = P.php_list_pools()
    assert 'array_key_exists("enable", $conf)' in body
    assert '["pool"]' in body and '["range"]' in body


# ---- dhcp add / rm keep the resolver's static-mapping names in step ------------------------------
# With "Register DHCP static mappings" (unbound/regdhcpstatic) on, unbound answers each
# reservation's hostname from host_entries.conf, which only services_unbound_configure() rewrites;
# a reconfigure has also been seen to leave unbound stopped, so the restart and liveness check follow.
@pytest.mark.parametrize("builder", [
    lambda: P.php_add_reservation("lan", "00:11:22:33:44:50", "192.0.2.50", "printer", ""),
    lambda: P.php_rm_reservation("00:11:22:33:44:30"),
    lambda: P.php_rename_reservation("00:11:22:33:44:31", "storage"),
])
def test_the_dhcp_write_reconfigures_unbound_only_when_it_registers_static_mappings(builder):
    body = builder()
    gate = ('config_get_path("unbound/enable") !== null && '
            'config_get_path("unbound/regdhcpstatic") !== null')
    assert gate in body
    assert body.index("write_config(") < body.index("services_unbound_configure();")
    assert '"unbound_follows"' in body


def _dhcp_unbound_fake(follows, *, probe=None):
    flag = "true" if follows else "false"
    return FakeRun([
        (RESTART, (0, "", "")),
        ("host localhost. 127.0.0.1", probe or _answer("localhost", "127.0.0.1")),
        ("$removed", (0, '{"removed":[{"interface":"lan","ip":"192.0.2.30"}],"unbound_follows":' + flag + "}", "")),
        ("$added", (0, '{"added":{"interface":"lan","mac":"00:11:22:33:44:50","ip":"192.0.2.50",'
                       '"hostname":"printer"},'
                       '"unbound_follows":' + flag + "}", "")),
        ("$renamed", (0, '{"renamed":[{"interface":"lan","ip":"192.0.2.31"}],"unbound_follows":' + flag + "}", "")),
        ('"dhcp_backend"', (0, INFO_JSON, BANNER)),
        ('config_get_path("dhcpd"', (0, RESERVATIONS_JSON, BANNER)),
        ("cat /conf/config.xml", (0, CONFIG_XML, BANNER)),
    ])


DHCP_WRITES = [
    ["dhcp", "add", "--mac", "00:11:22:33:44:50", "--ip", "192.0.2.50", "--hostname", "printer"],
    ["dhcp", "rm", "--mac", "00:11:22:33:44:30"],
    ["dhcp", "rename", "--mac", "00:11:22:33:44:31", "--hostname", "storage"],
]


@pytest.mark.parametrize("argv", DHCP_WRITES)
def test_a_dhcp_write_restarts_unbound_and_checks_it_answers_when_it_follows(argv, tmp_path, capsys):
    fake = _dhcp_unbound_fake(True)
    rc = P.main(["--host", "192.0.2.1", "--json", "--apply", "--snapshot-dir", str(tmp_path), *argv], run=fake)
    assert rc == 0
    remotes = [c["remote"] for c in fake.calls]
    assert RESTART in remotes and "host localhost. 127.0.0.1" in remotes
    assert json.loads(capsys.readouterr().out)["data"]["unbound"]["restarted"] is True


@pytest.mark.parametrize("argv", DHCP_WRITES)
def test_a_dhcp_write_leaves_unbound_alone_when_it_does_not_register_static_mappings(argv, tmp_path):
    fake = _dhcp_unbound_fake(False)
    assert P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path), *argv], run=fake) == 0
    assert RESTART not in [c["remote"] for c in fake.calls]


@pytest.mark.parametrize("argv", DHCP_WRITES)
def test_a_dhcp_write_over_a_dead_unbound_is_exit_2_saying_the_change_is_written(argv, tmp_path, capsys):
    fake = _dhcp_unbound_fake(True, probe=TIMED_OUT)
    rc = P.main(["--host", "192.0.2.1", "--apply", "--snapshot-dir", str(tmp_path), *argv], run=fake)
    assert rc == 2
    assert "written to config.xml" in capsys.readouterr().err
