"""Tests for recovery-retry-gate - the PreToolUse gate on re-running an act that had to be undone.

Every fixture here is SYNTHETIC and uses RFC-reserved names (example.com, 192.0.2.0/24). No content
from a real transcript is stored in this repo.

The subprocess tests hand HOME to the CHILD environment. A monkeypatch.setenv never reaches a
subprocess, and a suite that forgets this writes into the real audit dir, passes once on a clean
machine and then fails against its own leftover state.
"""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))

HOOK = HOOKS / "recovery-retry-gate.py"
spec = importlib.util.spec_from_file_location("recovery_retry_gate", HOOK)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


# --------------------------------------------------------------- destructive acts

@pytest.mark.parametrize(
    ("command", "op"),
    [
        ("robocopy C:\\empty C:\\Windows.old /MIR /MT:32", "mirror"),
        ("rm -rf /srv/build", "rmtree"),
        ("Remove-Item C:\\stale -Recurse -Force", "rmtree"),
        ("takeown /f C:\\Windows.old /r", "chattr"),
        ("mkfs.ext4 /dev/sdb1", "wipefs"),
        ("reg delete HKLM\\SOFTWARE\\Vendor /f", "regdel"),
        ("zfs destroy tank/scratch", "destroy"),
        ("apt-get purge nginx", "pkgrm"),
        ("git clean -fd", "gitwipe"),
    ],
)
def test_destructive_acts_are_named(command, op):
    assert op in gate.destructive_ops(command)


@pytest.mark.parametrize(
    "command",
    [
        "qm stop 4242",                       # lifecycle, not destruction
        "qm start 4242",
        "qm snapshot 4242 presnap",           # TAKING a snapshot protects state
        "systemctl restart nginx",
        "robocopy C:\\src C:\\dst /E",        # a copy without /MIR deletes nothing
        "cp -a build/app /usr/local/bin/app",  # a deploy overwrites one file, it is not a wipe
        "chown -R appuser /home/appuser",      # your own tree
        "ls -la /var/log",
    ],
)
def test_lifecycle_and_deploy_are_not_destructive(command):
    assert gate.destructive_ops(command) == set()


def test_a_comment_warning_about_a_destructive_act_is_not_one():
    """The reference session's only spurious detection came from exactly this line, in a read-only
    diagnostic script; a body-scanning guard must strip prose regions."""
    script = (
        "cat > junctions.ps1 <<'EOS'\n"
        "# robocopy /MIR follows junctions unless /XJ is passed, so any such link is a path out\n"
        "Get-ChildItem C:\\Windows.old -Attributes ReparsePoint\n"
        "EOS"
    )
    assert gate.destructive_ops(script) == set()


def test_a_destructive_act_inside_a_heredoc_body_still_counts():
    """Control for the strip above: the destruction lives in the script, not the shell line."""
    script = (
        "cat > purge.ps1 <<'EOS'\n"
        "robocopy C:\\empty C:\\Windows.old /MIR\n"
        "EOS"
    )
    assert "mirror" in gate.destructive_ops(script)


# --------------------------------------------------------------- undo detection

@pytest.mark.parametrize(
    "command",
    [
        "ssh root@node.example.com 'qm rollback 4242 presnap'",
        "pct rollback 105 before",
        "zfs rollback tank/data@yesterday",
        "virsh snapshot-revert web1 clean",
    ],
)
def test_machine_undos_are_recognised(command):
    assert gate.recovery_class("Bash", {"command": command}) != ""


@pytest.mark.parametrize(
    "command",
    [
        "git stash push -q app.py && pytest -q; git stash pop -q",   # the RED-proof idiom
        "git checkout -- app.py",
        "git restore app.py",
        "git reset --hard HEAD~1",
        "git revert abc1234",
        "cp -a scratch/app.orig src/app.py",
        "qm snapshot 4242 presnap",
    ],
)
def test_repo_level_and_snapshot_taking_are_not_undos(command):
    """Repo undos are the mutate-test-restore proof, not damage; every one admitted in the corpus
    turned out to be a RED/GREEN loop. Taking a snapshot is not an undo at all."""
    assert gate.recovery_class("Bash", {"command": command}) == ""


def test_a_search_for_the_word_rollback_is_not_a_rollback():
    assert gate.recovery_class("Bash", {"command": "grep -c 'qm rollback' session.jsonl"}) == ""


def test_a_rollback_named_in_a_heredoc_body_is_not_a_rollback():
    command = "python3 - <<'PY'\nfor m in re.finditer(r'qm rollback', text): print(m)\nPY"
    assert gate.recovery_class("Bash", {"command": command}) == ""


def test_non_bash_tools_are_never_an_undo():
    assert gate.recovery_class("Write", {"file_path": "/x/qm rollback.txt"}) == ""


# --------------------------------------------------------------- subjects

def test_a_guest_id_and_an_ip_are_both_subjects():
    command = "ssh root@hv.example.com 'qm status 4242' && ssh admin@192.0.2.10 'hostname'"
    found = gate.mentions("Bash", {"command": command})
    assert {"vm:4242", "host:192.0.2.10", "host:hv.example.com"} <= found


def test_the_ssh_key_path_is_not_a_host():
    command = "ssh -i /root/.ssh/root@shared_nopass.key admin@node.example.com 'uptime'"
    found = gate.mentions("Bash", {"command": command})
    assert "host:node.example.com" in found
    assert not any(m.startswith("host:shared") for m in found)


def test_a_public_key_comment_is_not_a_host():
    """`ssh-ed25519 AAAA... root@buildhost` names a KEY, not a machine. Installing fleet keys made
    every such command mention one phantom host, and that phantom carried a false firing."""
    command = "echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExample root@buildhost' >> auth_keys"
    assert "host:buildhost" not in gate.mentions("Bash", {"command": command})


def test_an_author_email_is_not_a_host():
    """`git -c user.email="dev@example.com" commit` made the mail provider a subject in the corpus.
    A login target only occurs inside a remote-shell command."""
    command = 'git -c user.email="dev@example.com" commit -F msg.txt'
    assert gate.mentions("Bash", {"command": command}) == set()


def test_a_leading_cd_does_not_become_the_subject():
    command = "cd /tmp/scratch && ssh admin@192.0.2.10 'hostname'"
    assert "host:192.0.2.10" in gate.mentions("Bash", {"command": command})


def test_write_and_edit_subjects_are_the_file():
    assert gate.mentions("Write", {"file_path": "/srv/deploy.py"}) == {"f:deploy.py"}
    assert gate.mentions("Edit", {"file_path": "/srv/deploy.py"}) == {"f:deploy.py"}


def test_the_acting_text_of_each_tool():
    assert gate.acting_text("Bash", {"command": "rm -rf /x"}) == "rm -rf /x"
    assert gate.acting_text("Write", {"content": "rm -rf /x"}) == "rm -rf /x"
    assert gate.acting_text("Edit", {"new_string": "rm -rf /x"}) == "rm -rf /x"
    assert gate.acting_text("Read", {"file_path": "/x"}) == ""


# --------------------------------------------------------------- arming

def _window(*records):
    """[(mentions, ops)] as _absorb keeps them."""
    return [(sorted(m), sorted(o)) for m, o in records]


def test_an_undo_after_a_destructive_act_arms_on_that_subject():
    window = _window(({"vm:4242", "host:192.0.2.10"}, {"mirror"}))
    ids, ops = gate.arm_recovery(window, {"vm:4242"}, {}, position=50)
    assert ids == {"vm:4242", "host:192.0.2.10"}
    assert ops == {"mirror"}


def test_a_reset_to_baseline_arms_nothing():
    """The rollback-before-each-redeploy loop: nothing destructive precedes the undo, so there is
    no damage to repeat. 79 of the 99 machine undos in the corpus are this shape."""
    window = _window(({"vm:4242"}, set()), ({"f:deploy.sh"}, set()))
    ids, ops = gate.arm_recovery(window, {"vm:4242"}, {}, position=50)
    assert (ids, ops) == (set(), set())


def test_a_file_is_never_the_subject_of_a_machine_undo():
    window = _window(({"f:purge.ps1", "vm:4242"}, {"rmtree"}))
    ids, _ = gate.arm_recovery(window, set(), {}, position=50)
    assert ids == {"vm:4242"}


def test_a_ubiquitous_identifier_is_scenery_not_a_subject():
    """The hypervisor host appears in a quarter of a fleet session's commands; keeping it would link
    every guest to every other one."""
    window = _window(({"host:hv.example.com", "vm:4242"}, {"mirror"}))
    seen = {"host:hv.example.com": 40, "vm:4242": 2}
    ids, _ = gate.arm_recovery(window, set(), seen, position=100)
    assert ids == {"vm:4242"}


def test_the_rarity_floor_protects_a_young_session():
    """At event 5, 10% is 0, and an integer threshold would reject every subject."""
    window = _window(({"vm:4242"}, {"mirror"}))
    ids, _ = gate.arm_recovery(window, set(), {"vm:4242": 2}, position=5)
    assert ids == {"vm:4242"}


# --------------------------------------------------------------- the firing rule

ARMED = [[10, ["vm:4242"], ["mirror", "rmtree"]]]


def test_same_subject_and_same_act_fires():
    hit = gate.matching_recovery(ARMED, {"vm:4242"}, {"mirror"}, position=30)
    assert hit == (10, ["vm:4242"], ["mirror"])


def test_same_subject_without_the_same_act_is_silent():
    """Booting, verifying and stopping the restored guest are the aftermath of the undo, not a
    retry of it. Ablating this clause takes the corpus from 5 firings to 43."""
    assert gate.matching_recovery(ARMED, {"vm:4242"}, set(), position=30) is None
    assert gate.matching_recovery(ARMED, {"vm:4242"}, {"pkgrm"}, position=30) is None


def test_same_act_on_a_different_subject_is_silent():
    assert gate.matching_recovery(ARMED, {"vm:9999"}, {"mirror"}, position=30) is None


def test_a_repeat_beyond_the_lookback_is_silent():
    far = gate.LOOKBACK_EVENTS + 11
    assert gate.matching_recovery(ARMED, {"vm:4242"}, {"mirror"}, position=far) is None


def test_the_newest_armed_undo_is_the_one_cited():
    armed = [[10, ["vm:4242"], ["mirror"]], [20, ["vm:4242"], ["mirror"]]]
    assert gate.matching_recovery(armed, {"vm:4242"}, {"mirror"}, position=30)[0] == 20


# --------------------------------------------------------------- the message

def test_the_message_carries_the_evidence_and_the_skill():
    message = gate.build_message(586, ["host:192.0.2.10"], ["mirror", "rmtree"], 36)
    assert "586" in message and "host:192.0.2.10" in message and "mirror" in message
    assert "bitranox:process-stop-repeating-failure" in message
    assert len(message) < 900, "this lands in every gated call; it has to stay small"


# --------------------------------------------------------------- transcript state

def test_split_pending_separates_the_call_being_gated():
    records = [("Bash", {"command": "ls"}), ("Bash", {"command": "rm -rf /x"})]
    history, pending = gate.split_pending(records, ("Bash", "rm -rf /x"))
    assert len(history) == 1 and pending == records[1]


def test_split_pending_keeps_everything_when_the_call_is_not_written_yet():
    records = [("Bash", {"command": "ls"})]
    history, pending = gate.split_pending(records, ("Bash", "rm -rf /x"))
    assert history == records and pending is None


def test_reading_the_tail_leaves_a_partial_line_for_the_next_call(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"a": 1}\n{"b": 2', encoding="utf-8")
    chunk, offset = gate._read_new_lines(str(transcript), 0)
    assert chunk == '{"a": 1}\n' and offset == 9
    transcript.write_text('{"a": 1}\n{"b": 2}\n', encoding="utf-8")
    chunk, offset = gate._read_new_lines(str(transcript), offset)
    assert chunk == '{"b": 2}\n'


def test_a_truncated_transcript_restarts_the_read(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"a": 1}\n', encoding="utf-8")
    chunk, offset = gate._read_new_lines(str(transcript), 10 ** 6)
    assert chunk == '{"a": 1}\n' and offset == 9


def test_sidechain_records_are_not_this_session_s_actions():
    """A subagent's calls are its own; folding them in makes one dispatch look like a burst."""
    main = json.dumps({"message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}})
    side = json.dumps({"isSidechain": True,
                       "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {}}]}})
    assert len(list(gate._tool_calls(main + "\n" + side + "\n"))) == 1


# --------------------------------------------------------------- end to end

def _line(tool, tool_input):
    return json.dumps({"message": {"content": [
        {"type": "tool_use", "name": tool, "input": tool_input}]}}) + "\n"


DESTROY = ("cd /tmp/w && cat > purge.ps1 <<'EOS'\n"
           "robocopy C:\\empty C:\\Windows.old /MIR /MT:32\n"
           "EOS\n"
           "run.sh purge.ps1 192.0.2.10 admin")
UNDO = ("ssh root@hv.example.com 'qm stop 4242; qm rollback 4242 presnap; qm status 4242'\n"
        "# 192.0.2.10 is guest 4242")
RETRY = ("cd /tmp/w && cat > purge2.ps1 <<'EOS'\n"
         "robocopy C:\\empty C:\\Windows.old /MIR /XJ\n"
         "EOS\n"
         "run.sh purge2.ps1 192.0.2.10 admin")


class Session:
    """A transcript that grows, plus the hook run against it as a real subprocess."""

    def __init__(self, tmp_path, name="sess"):
        self.home = tmp_path / "home"
        self.home.mkdir(parents=True, exist_ok=True)
        self.transcript = tmp_path / (name + ".jsonl")
        self.transcript.write_text("", encoding="utf-8")
        self.name = name

    def call(self, tool, tool_input, written=True):
        """Run the hook for one call, writing it to the transcript first as the harness does."""
        if written:
            with open(self.transcript, "a", encoding="utf-8") as handle:
                handle.write(_line(tool, tool_input))
        payload = {"tool_name": tool, "tool_input": tool_input, "session_id": self.name,
                   "transcript_path": str(self.transcript)}
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home))
        result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                                capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)
        assert result.returncode == 0, result.stderr
        if not result.stdout.strip():
            return ""
        return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]

    def bash(self, command, **kwargs):
        return self.call("Bash", {"command": command}, **kwargs)

    def filler(self, count):
        for i in range(count):
            self.bash("echo step %d" % i)


def test_state_is_isolated_to_the_given_home(tmp_path):
    """Guards the isolation itself: a monkeypatch cannot reach a subprocess."""
    session = Session(tmp_path)
    session.bash("echo hello")
    assert list(tmp_path.rglob("*.recovery-gate.json")), "state did not land under the test HOME"


def test_destroy_undo_retry_fires_on_the_retry(tmp_path):
    session = Session(tmp_path)
    assert session.bash(DESTROY) == ""
    assert session.bash(UNDO) == ""
    message = session.bash(RETRY)
    assert "STOP-CHECK" in message and "host:192.0.2.10" in message and "mirror" in message


def test_the_same_sequence_without_the_undo_is_silent(tmp_path):
    """The KNOWN NEGATIVE. Identical destructive work, identical retry, no rollback in between: if
    this fired, the gate would be detecting repetition rather than repetition of an UNDONE act."""
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash("ssh root@hv.example.com 'qm status 4242'")
    assert session.bash(RETRY) == ""


def test_a_reset_loop_never_fires(tmp_path):
    """Negative control: roll back to a clean snapshot, redeploy, measure, repeat. The redeploy
    carries no destructive op and nothing destructive precedes the rollback."""
    session = Session(tmp_path)
    for _ in range(4):
        assert session.bash("ssh root@hv.example.com 'qm rollback 4242 clean; qm start 4242'") == ""
        assert session.bash("scp build/app admin@192.0.2.10:/opt/app && run.sh bench.ps1 192.0.2.10") == ""


def test_verifying_the_restored_guest_is_silent(tmp_path):
    """The events right after an undo are the undo: boot it, check it, stop it."""
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    assert session.bash("ssh root@hv.example.com 'qm start 4242'") == ""
    assert session.bash("run.sh verify.ps1 192.0.2.10 admin") == ""
    assert session.bash("ssh admin@192.0.2.10 'dir C:\\Windows.old'") == ""


def test_a_repeat_on_another_machine_is_silent(tmp_path):
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    assert session.bash(RETRY.replace("192.0.2.10", "192.0.2.77")) == ""


def test_a_repeat_after_the_lookback_has_passed_is_silent(tmp_path):
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    session.filler(gate.LOOKBACK_EVENTS + 2)
    assert session.bash(RETRY) == ""


def test_one_message_per_undo_however_many_retries_follow(tmp_path):
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    assert session.bash(RETRY) != ""
    assert session.bash(RETRY) == ""
    assert session.bash(RETRY) == ""


def test_a_second_undo_earns_a_second_message(tmp_path):
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    assert session.bash(RETRY) != ""
    session.bash(UNDO)
    assert session.bash(RETRY) != ""


def test_the_session_cap_bounds_the_noise(tmp_path):
    session = Session(tmp_path)
    session.bash(DESTROY)
    fired = 0
    for _ in range(gate.FIRE_CAP + 3):
        session.bash(UNDO)
        if session.bash(RETRY):
            fired += 1
    assert fired == gate.FIRE_CAP


def test_the_undo_itself_never_fires(tmp_path):
    """An undo repeated after an undo is still an undo, not an attempt."""
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    assert session.bash(UNDO) == ""


def test_every_call_is_counted_once_even_when_already_in_the_transcript(tmp_path):
    """The gated call is usually ALREADY written when PreToolUse runs. Dropping it as 'the pending'
    without absorbing it afterwards made the running state count 64 of 766 events - the in-process
    replay could not see it because only the real subprocess advances the read offset."""
    session = Session(tmp_path)
    session.filler(5)
    state = json.loads(next(iter(session.home.rglob("*.recovery-gate.json"))).read_text())
    assert state["n"] == 5


def test_a_call_not_yet_in_the_transcript_is_still_judged(tmp_path):
    """The other order: some harness versions write the assistant message after the hook runs."""
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    assert session.bash(RETRY, written=False) != ""


def test_write_and_edit_of_a_destructive_script_are_gated(tmp_path):
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    message = session.call("Write", {"file_path": "/tmp/w/purge3.ps1",
                                     "content": "robocopy C:\\empty C:\\Windows.old /MIR\n"})
    assert message == "", "a file is not the subject of a machine undo"


def test_a_read_is_never_gated(tmp_path):
    session = Session(tmp_path)
    session.bash(DESTROY)
    session.bash(UNDO)
    assert session.call("Read", {"file_path": "/tmp/w/purge.ps1"}) == ""


def test_malformed_stdin_is_silent_and_harmless():
    result = subprocess.run([sys.executable, str(HOOK)], input="not json",
                            capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0 and result.stdout.strip() == ""


def test_a_missing_transcript_is_silent(tmp_path):
    payload = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /x"}, "session_id": "s",
               "transcript_path": str(tmp_path / "nope.jsonl")}
    env = dict(os.environ, HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                            capture_output=True, text=True, encoding="utf-8", timeout=60, env=env)
    assert result.returncode == 0 and result.stdout.strip() == ""


def test_corrupt_state_starts_over_rather_than_crashing(tmp_path):
    session = Session(tmp_path)
    session.bash("echo warm up")
    state = next(iter(session.home.rglob("*.recovery-gate.json")))
    state.write_text("{not json", encoding="utf-8")
    assert session.bash("echo again") == ""
    assert json.loads(state.read_text())["v"] == gate.STATE_VERSION
