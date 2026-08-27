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
import os
import pathlib
import json

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


# ---- the streams stay apart ---------------------------------------------------------------------
def test_stderr_banner_never_reaches_the_parsed_data():
    """The whole point: the banner is on stderr, so a parser that keeps them apart never sees it."""
    fake = FakeRun([('config_get_path("dhcpd"', (0, '[{"mac":"00:11:22:33:44:30","ip":"192.0.2.30"}]', BANNER))])
    assert P.run_php(TARGET, P.php_list_reservations(), run=fake) == [{"mac": "00:11:22:33:44:30", "ip": "192.0.2.30"}]


def test_a_banner_merged_into_stdout_would_break_the_parse():
    """The control, so the test above cannot pass vacuously.

    This is exactly what `ssh ... 2>&1` produces. If it did NOT fail here, the assertion above
    would prove nothing about where the banner went.
    """
    fake = FakeRun([('config_get_path("dhcpd"', (0, BANNER + "[]", ""))])
    with pytest.raises(P.PfsenseError):
        P.run_php(TARGET, P.php_list_reservations(), run=fake)


def test_php_source_travels_on_stdin_not_in_the_command():
    """No quoting layer can mangle what it never parses: the remote command is the bare word php."""
    fake = FakeRun([("config_get_path", (0, "[]", ""))])
    P.run_php(TARGET, P.php_list_reservations(), run=fake)
    assert fake.calls[0]["remote"] == "php"
    assert 'require_once("config.inc")' in fake.calls[0]["stdin"]


def test_php_that_returns_nothing_is_an_error_not_an_empty_result():
    fake = FakeRun([("config_get_path", (0, "", BANNER))])
    with pytest.raises(P.PfsenseError):
        P.run_php(TARGET, P.php_list_reservations(), run=fake)


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


def test_override_name_handles_an_override_with_no_host_part():
    assert P.override_name({"host": "", "domain": "example.com"}) == "example.com"
    assert P.override_name({"host": "nas", "domain": "example.com"}) == "nas.example.com"


# ---- selection refuses to guess -----------------------------------------------------------------
def test_select_one_finds_the_single_match():
    items = [{"mac": "aa:aa:aa:aa:aa:aa"}, {"mac": "bb:bb:bb:bb:bb:bb"}]
    assert P.select_one(items, "mac", "BB:BB:BB:BB:BB:BB", what="reservation")["mac"] == "bb:bb:bb:bb:bb:bb"


def test_select_one_refuses_when_nothing_matches():
    with pytest.raises(P.PfsenseError, match="no reservation"):
        P.select_one([{"mac": "aa:aa:aa:aa:aa:aa"}], "mac", "bb:bb:bb:bb:bb:bb", what="reservation")


def test_select_one_refuses_an_ambiguous_match_rather_than_taking_the_first():
    """Taking the first is how a second command from the same listing hits the wrong row."""
    items = [{"mac": "aa:aa:aa:aa:aa:aa", "ip": "192.0.2.5"}, {"mac": "aa:aa:aa:aa:aa:aa", "ip": "192.0.2.6"}]
    with pytest.raises(P.PfsenseError, match="refusing to guess"):
        P.select_one(items, "mac", "aa:aa:aa:aa:aa:aa", what="reservation")


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
    reservations = P.reservations_from_config_xml(CONFIG_XML)
    assert [r["ip"] for r in reservations] == ["192.0.2.30", "192.0.2.31"]
    assert [r["static_arp"] for r in reservations] == [True, False]


def test_overrides_are_read_from_unbound_hosts_not_hostoverride():
    """The GUI says Host Overrides; the element is `hosts`. The wrong path returns [] silently."""
    overrides = P.overrides_from_config_xml(CONFIG_XML)
    assert [P.override_name(o) for o in overrides] == ["nas.example.com", "bare.example.com"]


# ---- doctor -------------------------------------------------------------------------------------
def test_doctor_warns_about_an_armed_static_arp_entry():
    findings = P.doctor_findings(reservations=P.reservations_from_config_xml(CONFIG_XML), overrides=[])
    armed = [f for f in findings if f.check == "static_arp_armed"]
    assert len(armed) == 1 and armed[0].severity == "warn" and "192.0.2.30" in armed[0].subject


def test_doctor_stays_quiet_on_a_config_with_nothing_wrong():
    """A check that fires on a healthy config is as useless as one that never fires."""
    clean = [{"ip": "192.0.2.31", "mac": "00:11:22:33:44:31", "static_arp": False}]
    assert [f for f in P.doctor_findings(reservations=clean, overrides=[]) if f.severity == "warn"] == []


def test_one_address_shared_by_several_macs_is_context_not_a_warning():
    """Measured: warning on this alone fired 5 times on a config that was entirely correct.

    A wired and a wireless interface sharing one reserved address is the intended setup.
    """
    shared = [{"ip": "192.0.2.31", "mac": "00:11:22:33:44:31", "static_arp": False},
              {"ip": "192.0.2.31", "mac": "00:11:22:33:44:32", "static_arp": False}]
    findings = P.doctor_findings(reservations=shared, overrides=[])
    assert [f.check for f in findings] == ["shared_ip_multi_mac"]
    assert findings[0].severity == "info"


def test_static_arp_on_a_shared_address_names_the_lethal_combination():
    shared = [{"ip": "192.0.2.31", "mac": "00:11:22:33:44:31", "static_arp": True},
              {"ip": "192.0.2.31", "mac": "00:11:22:33:44:32", "static_arp": False}]
    armed = [f for f in P.doctor_findings(reservations=shared, overrides=[]) if f.check == "static_arp_armed"]
    assert "2 MACs" in armed[0].detail


def test_doctor_reports_an_address_held_by_hardware_the_reservation_does_not_name():
    """The stale-reservation-versus-live-device collision, which shows up as flaky wifi."""
    reservations = [{"ip": "192.0.2.30", "mac": "aa:aa:aa:aa:aa:aa", "static_arp": False, "descr": "old AP"}]
    findings = P.doctor_findings(reservations=reservations, overrides=[], arp=P.parse_arp(ARP_TEXT))
    mismatch = [f for f in findings if f.check == "reservation_mac_mismatch"]
    assert len(mismatch) == 1 and "00:11:22:33:44:30" in mismatch[0].subject


def test_an_idle_device_is_never_reported_as_gone():
    """ARP is a cache that expires after minutes of silence, so absence is not evidence.

    Measured: a version that concluded from absence called 22 healthy hosts possibly-gone on a
    network with nothing wrong with it. The DHCP lease file cannot rescue it either, because ISC
    dhcpd writes no lease for a fixed-address reservation.
    """
    reservations = [{"ip": "192.0.2.77", "mac": "aa:aa:aa:aa:aa:aa", "static_arp": False, "descr": "idle"}]
    assert P.doctor_findings(reservations=reservations, overrides=[], arp=P.parse_arp(ARP_TEXT)) == []


def test_one_reserved_mac_answering_for_a_shared_address_is_not_a_mismatch():
    """A device with several reserved MACs answers from exactly one of them at a time.

    Measured: treating the others as mismatches produced 5 false warnings against a live config.
    """
    shared = [{"ip": "192.0.2.30", "mac": "00:11:22:33:44:30", "static_arp": False},
              {"ip": "192.0.2.30", "mac": "00:11:22:33:44:99", "static_arp": False}]
    findings = P.doctor_findings(reservations=shared, overrides=[], arp=P.parse_arp(ARP_TEXT))
    assert [f.check for f in findings] == ["shared_ip_multi_mac"]


def test_an_override_pointing_at_a_static_host_is_not_a_finding():
    """A statically configured server has no reservation; that is normal, not a fault."""
    overrides = [{"host": "srv", "domain": "example.com", "ip": "192.0.2.200"}]
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


def test_doctor_reports_a_stale_upgrade_lock():
    findings = P.doctor_findings(reservations=[], overrides=[], arp=[], upgrade_lock=True)
    assert [f.check for f in findings] == ["upgrade_lock_present"]


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
        ("$removed", (0, '{"removed":[{"interface":"lan","ip":"192.0.2.30"}]}', "")),
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


# ---- snapshot -----------------------------------------------------------------------------------
def test_snapshot_writes_a_timestamped_file(tmp_path):
    fake = FakeRun([("cat /conf/config.xml", (0, CONFIG_XML, BANNER))])
    path = P.do_snapshot(TARGET, tmp_path, run=fake)
    assert path.parent == tmp_path and path.read_text(encoding="utf-8") == CONFIG_XML


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


def test_arp_permanent_filters_to_the_entries_that_matter():
    fake = FakeRun([("arp -an", (0, ARP_TEXT, BANNER))])
    assert P.main(["--host", "192.0.2.1", "--json", "arp", "--permanent"], run=fake) == 0


def test_fix_steps_names_all_three_parts():
    steps = P.fix_steps(sid="2071408", cidr="198.51.100.0/22")
    assert "2071408" in steps and "198.51.100.0/22" in steps
    assert "suppress" in steps.lower() and "pass list" in steps.lower() and "unblock" in steps


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
