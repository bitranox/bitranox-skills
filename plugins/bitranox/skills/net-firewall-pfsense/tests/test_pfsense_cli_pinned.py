"""Every verb's output, pinned byte for byte against a fake firewall.

The digests in pfsense_cli_digests.json were recorded from the CLI as it stood before run_php's
results became typed records. Each one covers a scenario's exit code, stdout, stderr, every
command sent to the box and the config the fake is left holding, for every verb in human and
--json form over seven firewall states (one with mixed case and padding everywhere, three seeded
random ones with adversarial strings).
A change to what any verb prints or sends fails here naming the scenario.

When an output is changed ON PURPOSE, do not re-pin the whole file to today's output: a
re-recorded pin asserts that today equals today. Re-record only the scenarios the change is about,
and say which in the commit.
"""
import json
from pathlib import Path, PureWindowsPath

import fake_firewall as F
import pfsense as P
import pytest

DIGESTS = Path(__file__).with_name("pfsense_cli_digests.json")
SCRIPT = Path(P.__file__)


def _pinned() -> dict[str, str]:
    return json.loads(DIGESTS.read_text(encoding="utf-8"))["digests"]


def _mismatches(module, root: Path, states=None) -> list[tuple[str, F.Outcome]]:
    pinned = _pinned()
    seen = dict(F.run_matrix(module, root, states))
    if states is None:
        assert seen.keys() == pinned.keys(), "the scenario matrix and the pinned digests disagree"
    return [(key, outcome) for key, outcome in seen.items() if outcome.digest()[:16] != pinned[key]]


def test_every_verb_still_prints_and_sends_what_was_pinned(tmp_path):
    bad = _mismatches(P, tmp_path)
    if bad:
        key, outcome = bad[0]
        pytest.fail(f"{len(bad)} scenario(s) changed, first {key}: rc={outcome.rc!r}\n"
                    f"stdout:\n{outcome.stdout}\nstderr:\n{outcome.stderr}")


def test_the_matrix_drives_every_cmd_function_in_both_output_forms():
    parser = P.build_parser()
    driven = {parser.parse_args(["--host", "192.0.2.1", *argv]).verb.func.__name__
              for argv in F.scenario_argvs(F.rich_state(), "/opt/config.xml").values()}
    assert driven == {name for name in dir(P) if name.startswith("cmd_")}
    assert {key.rsplit("/", 1)[1] for key in _pinned()} == {"human", "json"}


@pytest.mark.parametrize(("anchor", "planted"), [
    # human output only
    ('f"  ({len(reservations)} reservations)"', 'f"  ({len(reservations)} reservation)"'),
    # --json output only: the envelope every verb shares
    ('"skipped": list(self.skipped)}', '"skipped": list(self.skipped), "extra": 1}'),
    # --json output only: records built on this side rather than decoded from a PHP reply
    ('"permanent": self.permanent}', '"permanent": not self.permanent}'),
    ('out["passlist_entries"] = self.passlist.passlist_entries', 'out["passlist_entries"] = 0'),
])
def test_a_planted_change_to_either_output_form_is_caught(anchor, planted, tmp_path):
    source = SCRIPT.read_text(encoding="utf-8")
    assert source.count(anchor) == 1, "the plant's anchor moved; pick a new one"
    module = F.load_module(SCRIPT, "pfsense_planted", source.replace(anchor, planted))
    assert _mismatches(module, tmp_path, {"rich": F.rich_state})


def test_the_fake_refuses_a_php_body_it_does_not_model():
    fake = F.FakeFirewall(F.rich_state(), P)
    with pytest.raises(F.UnknownCommand):
        fake(["ssh", "admin@192.0.2.1", "php"], stdin_text=F.PRELUDE + "echo 1;")
    with pytest.raises(F.UnknownCommand):
        fake(["ssh", "admin@192.0.2.1", "rm -rf /conf"])


def test_the_fake_rejects_a_mutation_body_its_builder_would_not_produce():
    body = P.php_rm_reservation("00:11:22:33:44:30").replace("count($removed) == 1", "true")
    fake = F.FakeFirewall(F.rich_state(), P)
    with pytest.raises(F.UnknownCommand, match="builder does not produce"):
        fake(["ssh", "admin@192.0.2.1", "php"], stdin_text=F.PRELUDE + body)


def test_the_fake_answers_like_the_php_it_was_sent():
    """The double is only worth its digests if its replies match the PHP's semantics."""
    state = F.rich_state()
    fake = F.FakeFirewall(state, P)

    def php(body):
        return json.loads(fake(["ssh", "admin@192.0.2.1", "php"], stdin_text=F.PRELUDE + body)[1])

    assert php(P.php_rename_reservation("00:11:22:33:44:30", "x")) == {
        "renamed": [{"interface": "lan", "ip": "192.0.2.30"}], "unbound_follows": True}
    assert php(P.php_add_reservation("lan", "00:11:22:33:44:31", "192.0.2.77", "h", "d")) == {
        "added": None, "error": "a reservation for that MAC already exists"}
    assert php(P.php_add_reservation("opt9", "00:11:22:33:44:77", "192.0.2.77", "h", "d"))["error"] == \
        "interface opt9 has no DHCP server"
    assert php(P.php_rm_override("", "bare.example.com")) == {
        "removed": [{"host": "", "domain": "bare.example.com", "ip": "192.0.2.40"}]}
    assert php(P.php_rm_static_arp("00:11:22:33:44:31")) == {"changed": []}
    assert [p["interface"] for p in php(P.php_list_pools())] == ["lan", "lan", "opt1"]
    assert state.writes == 2


def test_a_windows_scratch_path_normalises_in_plain_and_json_spelling():
    root = PureWindowsPath(r"C:\t\case")
    stamp = "config-192.0.2.1-20261120100000.xml"
    plain = F._normalise(rf"saved C:\t\case\snaps\{stamp}", root)
    escaped = F._normalise(json.dumps({"path": rf"C:\t\case\snaps\{stamp}"}), root)
    assert plain == "saved <SNAPS>/config-192.0.2.1-<STAMP>.xml"
    assert escaped == '{"path": "<SNAPS>/config-192.0.2.1-<STAMP>.xml"}'
