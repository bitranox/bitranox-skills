"""Tests for fleet_ssh.py - one option set, one resolved key, no interactive prompt. ASCII only."""
import sys
import io
import os
import subprocess

import pytest

import fleet_ssh as F


def plan(argv, home="/home/nobody", default_user="localuser", config_user=lambda host: None):
    """parse_args + plan, which is where the wiring lives (and where the scp-user bug lived).

    config_user is injected and answers None by default, so no test shells out to `ssh -G` and no
    test depends on the ssh_config of the machine it runs on.
    """
    built, host, known_hosts = F.plan(F.parse_args(argv), home=home, default_user=default_user,
                                      config_user=config_user)
    return " ".join(built), host, known_hosts


# ---- trap 1: scp carries the user in the path -------------------------------------------------

def test_user_flag_reaches_an_scp_destination_not_only_the_key():
    """The bug this jig exists to prevent: --user picked the key, scp logged in as someone else.

    Both halves were right on their own - key resolution read the user, argv building copied the
    paths through - so only a test that goes through the WIRING can catch it.
    """
    line, _host, _kh = plan(["--scp", "--user", "root", "--key", "/k", "./f", "hst:/tmp/f"])
    assert line.endswith("./f root@hst:/tmp/f")


def test_user_flag_reaches_a_remote_scp_source_too():
    line, _host, _kh = plan(["--scp", "--user", "root", "--key", "/k", "hst:/tmp/f", "./f"])
    assert line.endswith("root@hst:/tmp/f ./f")


def test_a_user_named_in_the_path_wins_over_the_flag():
    line, _host, _kh = plan(["--scp", "--user", "someone", "--key", "/k", "./f", "root@hst:/tmp/f"])
    assert line.endswith("./f root@hst:/tmp/f")


def test_a_local_to_local_copy_gains_no_user():
    line, host, _kh = plan(["--scp", "--key", "/k", "/local/a", "/local/b"])
    assert line.endswith("/local/a /local/b")
    assert host is None, "a local copy has no host to heal"


def test_the_resolved_key_is_a_native_path(tmp_path):
    r"""The candidates are templates spelling their separator "/", so a Windows home produced
    "C:\Users\me/.ssh/key". Both ssh and Path accept that, so nothing failed - but it is the
    string the tool RETURNS and prints into the command line, so a caller holding the same key
    as a native path compares two spellings of one file and concludes they differ."""
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    key = home / ".ssh" / "root@anyhost_nopass.key"
    key.write_text("k", encoding="utf-8")
    resolved = F.resolve_key("root", home=str(home))
    assert resolved == os.path.join(str(home), ".ssh", "root@anyhost_nopass.key")
    assert resolved == str(key)


def test_the_key_and_the_login_are_the_same_identity(tmp_path):
    """Resolving one user's key and logging in as another is the failure this pairs against."""
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    key = home / ".ssh" / "root@anyhost_nopass.key"
    key.write_text("k")
    line, _host, _kh = plan(["--scp", "--user", "root", "./f", "hst:/tmp/f"], home=str(home))
    assert f"-i {key}" in line and "root@hst:/tmp/f" in line


def test_with_scp_user_only_touches_a_remote_side_naming_no_user():
    assert F.with_scp_user("hst:/p", "root") == "root@hst:/p"
    assert F.with_scp_user("root@hst:/p", "other") == "root@hst:/p"
    assert F.with_scp_user("/local/f", "root") == "/local/f"
    assert F.with_scp_user("/mnt/c:/weird", "root") == "/mnt/c:/weird"    # a path, not a host


def test_scp_host_finds_the_remote_side():
    assert F.scp_host("./f", "hst:/p") == "hst"
    assert F.scp_host("root@hst:/p", "./f") == "hst"
    assert F.scp_host("/a", "/b") is None
    assert F.scp_host("/a", "/mnt/c:/weird") is None


# ---- an unstated user must not override ssh_config ---------------------------------------------

def test_an_unstated_user_is_never_written_into_the_argv():
    """`user@host` on the command line OVERRIDES a `User` directive in ssh_config.

    So filling in the local account when nobody asked would silently log a host whose config says
    `User root` in as the wrong user - a regression against plain ssh, which the wrapper must not
    introduce.
    """
    line, _host, _kh = plan(["--key", "/k", "h", "uptime"])
    assert line.endswith(" h uptime")
    assert "localuser@h" not in line


def test_an_unstated_user_is_not_written_into_an_scp_path_either():
    line, _host, _kh = plan(["--scp", "--key", "/k", "./f", "hst:/p"])
    assert line.endswith("./f hst:/p")
    assert "localuser@" not in line


def test_the_key_is_resolved_for_whoever_ssh_says_it_will_be(tmp_path):
    """Leaving the login to ssh_config must not leave the KEY behind: resolving it for the local
    account while ssh connects as root is the same identity mismatch one step along."""
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh" / "root@anyhost_nopass.key").write_text("k")
    line, _host, _kh = plan(["h", "uptime"], home=str(home), config_user=lambda host: "root")
    assert "root@anyhost_nopass.key" in line, "the key follows the config's user"
    assert "root@h" not in line, "but the login is still left to the config"


def test_the_local_user_is_the_fallback_when_ssh_config_names_nobody(tmp_path):
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh" / "localuser@anyhost_nopass.key").write_text("k")
    line, _host, _kh = plan(["h", "uptime"], home=str(home))
    assert "localuser@anyhost_nopass.key" in line
    assert "localuser@h" not in line


def test_ssh_config_user_reads_ssh_dash_G():
    calls = []

    def fake_run(argv, **kw):
        calls.append(list(argv))
        return _FakeProc(0, stdout="hostname h.example\nuser root\nport 22\n")

    assert F.ssh_config_user("h", run=fake_run) == "root"
    assert calls == [["ssh", "-G", "h"]], "asks ssh, and does not connect"


def test_ssh_config_user_is_none_when_ssh_cannot_answer():
    def failing(argv, **kw):
        return _FakeProc(255)

    def missing(argv, **kw):
        raise OSError("ssh not found")

    assert F.ssh_config_user("h", run=failing) is None
    assert F.ssh_config_user("h", run=missing) is None


# ---- trap 2: -i alone still prompts ------------------------------------------------------------

def test_batchmode_is_always_on_in_both_modes():
    """With only -i, a rejected key falls back to a password prompt and hangs an unattended run."""
    for argv in (["--key", "/k", "h", "uptime"], ["--scp", "--key", "/k", "./f", "hst:/p"]):
        assert "BatchMode=yes" in plan(argv)[0]


def test_identities_only_is_set_when_a_key_is_given_and_not_otherwise():
    assert "IdentitiesOnly=yes" in plan(["--key", "/k", "h"])[0]
    assert "IdentitiesOnly=yes" not in plan(["h"], default_user=None)[0]


# ---- trap 3: a key can exist and be unreadable --------------------------------------------------

@pytest.mark.skipif(sys.platform == "win32",
                    reason='Windows has no POSIX mode bits: chmod(0o000) leaves the file readable, so an unreadable candidate cannot be created')
def test_resolve_key_skips_an_existing_but_unreadable_candidate(tmp_path):
    """An unreadable key yields `Permission denied` with EMPTY stdout, and the cause then surfaces
    far downstream as "the command returned nothing"."""
    unreadable = tmp_path / "shared" / "srvuser@anyhost_nopass.key"
    unreadable.parent.mkdir()
    unreadable.write_text("k")
    unreadable.chmod(0o000)
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    readable = home / ".ssh" / "srvuser@anyhost_nopass.key"
    readable.write_text("k")

    candidates = (str(unreadable), "{home}/.ssh/{user}@anyhost_nopass.key")
    assert unreadable.is_file(), "skipped for being unreadable, not for being absent"
    assert F.resolve_key("srvuser", candidates, home=str(home)) == str(readable)


def test_no_readable_key_means_no_i_flag_and_ssh_decides(tmp_path):
    line, _host, _kh = plan(["h", "uptime"], home=str(tmp_path))
    assert " -i " not in f" {line} "


def test_key_candidates_come_from_the_environment(monkeypatch):
    monkeypatch.setenv("FLEET_SSH_KEY_CANDIDATES", os.pathsep.join(["/a/{user}.key", "/b/k"]))
    assert F.key_candidates() == ("/a/{user}.key", "/b/k")
    monkeypatch.delenv("FLEET_SSH_KEY_CANDIDATES")
    assert F.key_candidates() == F.DEFAULT_KEY_CANDIDATES


# ---- host-key policy ----------------------------------------------------------------------------

def test_strict_checking_is_the_default_and_no_known_hosts_is_overridden():
    """Shipped default must be ssh's own trust model, not one that accepts a changed key."""
    line, _host, known_hosts = plan(["--key", "/k", "h", "uptime"])
    assert "StrictHostKeyChecking=no" not in line
    assert "UserKnownHostsFile" not in line
    assert known_hosts is None


def test_trusting_a_reimaged_fleet_is_opt_in_and_uses_a_separate_known_hosts():
    line, _host, known_hosts = plan(["--trust-changing-host-keys", "--key", "/k", "h", "uptime"])
    # accept-new, never `no`: a NEW host is recorded, a CHANGED or revoked key is refused before
    # anything runs, which is what makes the single retry after a drop safe.
    assert "StrictHostKeyChecking=accept-new" in line
    assert "StrictHostKeyChecking=no" not in line
    # separator-agnostic: the path is native now, so spelling one separator asserts the host's
    # OS rather than where the fleet known_hosts file goes
    assert known_hosts.replace(os.sep, "/").endswith("/.ssh/known_hosts_fleet")
    assert f"UserKnownHostsFile={known_hosts}" in line


def test_dev_null_known_hosts_is_refused():
    """/dev/null records every key "permanently" into the bit bucket: every connect is a first
    connect, so the "Permanently added" warning repeats forever and pollutes merged output."""
    with pytest.raises(F.UsageError):
        F.build_options(key=None, timeout=10, trust_changing_host_keys=True,
                        known_hosts="/dev/null")


def test_forward_stderr_drops_only_the_known_hosts_noise():
    out = io.StringIO()
    F.forward_stderr("Warning: Permanently added 'h' (ED25519) to the list of known hosts.\n"
                     "real error: something broke\n", stream=out)
    assert "Permanently added" not in out.getvalue()
    assert "real error: something broke" in out.getvalue()


def test_the_mismatch_is_ssh_s_offending_line_for_our_own_known_hosts_file():
    assert F.offends_known_hosts(_real_changed("/kh"), "/kh")
    assert not F.offends_known_hosts(_real_changed("/root/.ssh/known_hosts"), "/kh")
    assert not F.offends_known_hosts("Host key verification failed.\n", "/kh")
    assert not F.offends_known_hosts("Permission denied (publickey).\n", "/kh")


def test_the_offending_path_is_compared_as_a_path():
    home = os.path.expanduser("~")
    assert F.offends_known_hosts(_real_changed(os.path.join(home, "kh")), "~/kh")
    assert F.offends_known_hosts(_real_changed("/a/b/kh"), "/a/./b/kh")


# ---- healing: accept-new refuses a changed key, so ONE retry after the drop runs the command once

class _FakeProc:
    def __init__(self, returncode=0, stderr="", stdout="", log=""):
        self.returncode, self.stderr, self.stdout = returncode, stderr, stdout
        self.log = log
        """What ssh writes about ITSELF: to the `-E` file when one is given, else to stderr."""


class _Runner:
    """A fake process runner recording every argv it was handed.

    It plays ssh's split honestly: with `-E FILE` in the argv, a result's `log` goes to that file
    and its `stderr` (the REMOTE command's) to the captured stream; without `-E` both are stderr.
    `on_keygen` stands in for ssh-keygen's effect on the known-hosts file.
    """

    def __init__(self, *results, on_keygen=None):
        self.results, self.calls, self.on_keygen = list(results), [], on_keygen

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        if argv[0] == "ssh-keygen":
            if self.on_keygen is not None:
                self.on_keygen()
            return _FakeProc()
        proc = self.results.pop(0) if self.results else _FakeProc()
        if "-E" in argv:
            with open(argv[argv.index("-E") + 1], "a", encoding="utf-8") as fh:
                fh.write(proc.log)
            return _FakeProc(proc.returncode, proc.stderr)
        return _FakeProc(proc.returncode, proc.log + proc.stderr)


def _real_changed(known_hosts: str, host: str = "h") -> str:
    """What OpenSSH 10.2 prints for a changed key under StrictHostKeyChecking=accept-new, captured
    from a real run against a known-hosts file holding a wrong key: the banner, the offending
    entry in the file it read, the removal advice, and the refusal. The command does NOT run."""
    frame = "@" * 59 + "\n"
    return (frame + "@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @\n" + frame +
            "IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!\n"
            "Someone could be eavesdropping on you right now (man-in-the-middle attack)!\n"
            "It is also possible that a host key has just been changed.\n"
            "The fingerprint for the ED25519 key sent by the remote host is\n"
            "SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.\n"
            "Please contact your system administrator.\n"
            f"Add correct host key in {known_hosts} to get rid of this message.\n"
            f"Offending ED25519 key in {known_hosts}:1\n"
            "  remove with:\n"
            f"  ssh-keygen -f '{known_hosts}' -R '{host}'\n"
            f"Host key for {host} has changed and you have requested strict checking.\n"
            "Host key verification failed.\n")


def _kh(tmp_path, body="h ssh-ed25519 AAAA\n"):
    kh = tmp_path / "kh"
    kh.write_text(body, encoding="utf-8")
    return kh


def _emptying(kh):
    return lambda: kh.write_text("", encoding="utf-8")


def _heal(runner, *, heal=True, host="h", known_hosts="/kh", argv=("ssh", "h", "uptime")):
    return F.run_with_host_key_healing(list(argv), host=host, known_hosts=str(known_hosts),
                                       heal=heal, run=runner)


def _programs(runner):
    return [c[0] for c in runner.calls]


def test_a_clean_run_is_executed_exactly_once():
    r = _Runner(_FakeProc(0))
    assert _heal(r) == 0
    assert _programs(r) == ["ssh"]


@pytest.mark.parametrize("retry_status", [0, 7])
def test_a_changed_key_is_dropped_and_the_refused_command_runs_once(tmp_path, retry_status):
    """Under accept-new ssh REFUSES a changed key before running anything (measured on OpenSSH
    10.2: exit 255, the command never ran), so after the stale entry is dropped one retry is the
    command's FIRST run. The retry's status is the command's own."""
    kh = _kh(tmp_path)
    r = _Runner(_FakeProc(255, log=_real_changed(str(kh))), _FakeProc(retry_status),
                on_keygen=_emptying(kh))
    assert _heal(r, known_hosts=kh) == retry_status
    assert _programs(r) == ["ssh", "ssh-keygen", "ssh"]
    assert r.calls[1] == ["ssh-keygen", "-R", "h", "-f", str(kh)]


def test_an_inner_banner_on_the_remote_stderr_never_triggers_the_retry(tmp_path, capsys):
    """The reimage case: the remote command itself runs ssh or rsync to a peer whose key changed.
    That inner ssh's banner - offending path, removal advice, refusal, exit 255 and all - reaches
    us as the REMOTE command's stderr, and it can even name a file with our path, since the fleet
    runs the same tooling. Only ssh's OWN messages, which `-E` sends to a file of ours, count."""
    kh = _kh(tmp_path)
    inner = _real_changed(str(kh), host="peer")       # the SAME path, to rule the path test out
    r = _Runner(_FakeProc(255, stderr=inner), on_keygen=_emptying(kh))
    assert _heal(r, known_hosts=kh, argv=("ssh", "h", "rsync -a /data peer:/data")) == 255
    assert _programs(r) == ["ssh"], "the outer key is fine: no drop, and the command ran ONCE"
    assert kh.read_text(encoding="utf-8"), "our known-hosts file is untouched"
    assert "Host key verification failed." in capsys.readouterr().err, "remote stderr survives"


def test_ssh_s_own_messages_go_to_a_log_of_ours_only_when_healing():
    r = _Runner(_FakeProc(0))
    _heal(r)
    assert r.calls[0][:2] == ["ssh", "-E"]
    plain = _Runner(_FakeProc(0))
    _heal(plain, heal=False)
    assert "-E" not in plain.calls[0]


def test_ssh_s_own_log_is_forwarded_minus_the_known_hosts_noise(capsys):
    r = _Runner(_FakeProc(0, log="Warning: Permanently added 'h' (ED25519) to the list of known "
                                 "hosts.\nsome ssh notice\n", stderr="remote says hi\n"))
    assert _heal(r) == 0
    err = capsys.readouterr().err
    assert "some ssh notice" in err and "remote says hi" in err
    assert "Permanently added" not in err


def test_a_changed_host_key_is_not_healed_when_trust_was_not_asked_for(tmp_path):
    """Strict mode must report the mismatch, not quietly accept the new key."""
    kh = _kh(tmp_path)
    r = _Runner(_FakeProc(255, log=_real_changed(str(kh))), on_keygen=_emptying(kh))
    assert _heal(r, heal=False, known_hosts=kh) == 255
    assert _programs(r) == ["ssh"]


def test_an_ordinary_failure_is_never_retried():
    """A remote command fails for a thousand reasons; re-running a MUTATING one applies it twice."""
    r = _Runner(_FakeProc(1, stderr="rm: cannot remove 'x': No such file\n"))
    assert _heal(r, argv=("ssh", "h", "rm x")) == 1
    assert _programs(r) == ["ssh"]


def test_an_ssh_failure_that_is_not_a_changed_key_is_never_retried():
    r = _Runner(_FakeProc(255, log="ssh: connect to host h port 22: Connection refused\n"))
    assert _heal(r) == 255
    assert _programs(r) == ["ssh"]


def test_no_host_means_no_retry(tmp_path):
    kh = _kh(tmp_path)
    r = _Runner(_FakeProc(255, log=_real_changed(str(kh))), on_keygen=_emptying(kh))
    assert _heal(r, host=None, known_hosts=kh, argv=("scp", "a", "b")) == 255
    assert _programs(r) == ["scp"]


def _real_revoked(host: str = "h") -> str:
    """What OpenSSH 10.2 prints for a host key marked @revoked in the known-hosts file. Under
    accept-new it is refused like a changed one, and it names no offending entry."""
    frame = "@" * 59 + "\n"
    return (frame + "@       WARNING: REVOKED HOST KEY DETECTED!               @\n" + frame +
            f"The ED25519 host key for {host} is marked as revoked.\n"
            "This could mean that a stolen key is being used to\n"
            "impersonate this host.\n"
            "Host key verification failed.\n")


def test_a_revoked_key_is_never_healed_and_never_retried(capsys):
    """Dropping the entry would delete the @revoked marker itself - healing a revocation into
    acceptance. ssh names no offending entry for it, so nothing is dropped."""
    r = _Runner(_FakeProc(255, log=_real_revoked()))
    assert _heal(r) == 255
    assert _programs(r) == ["ssh"]
    assert "REVOKED HOST KEY" in capsys.readouterr().err


def test_the_heal_drops_the_name_ssh_recorded_not_the_alias_it_was_given(tmp_path):
    """An ssh_config alias or a non-default port is recorded under the RESOLVED name
    (`[10.0.0.5]:2222`), so `ssh-keygen -R <alias>` removes nothing - measured against a real
    sshd - and the banner then repeats on every call. ssh prints the exact name to remove."""
    kh = _kh(tmp_path)
    r = _Runner(_FakeProc(255, log=_real_changed(str(kh), host="[10.0.0.5]:2222")), _FakeProc(0),
                on_keygen=_emptying(kh))
    assert _heal(r, host="fleetalias", known_hosts=kh,
                 argv=("ssh", "fleetalias", "uptime")) == 0
    assert r.calls[1] == ["ssh-keygen", "-R", "[10.0.0.5]:2222", "-f", str(kh)]


def test_without_ssh_s_removal_hint_the_host_given_is_dropped(tmp_path):
    kh = _kh(tmp_path)
    log = (f"Offending ED25519 key in {kh}:1\n"
           "@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @\n"
           "Host key verification failed.\n")
    r = _Runner(_FakeProc(255, log=log), _FakeProc(0), on_keygen=_emptying(kh))
    assert _heal(r, host="h", known_hosts=kh) == 0
    assert r.calls[1] == ["ssh-keygen", "-R", "h", "-f", str(kh)]


def test_a_drop_that_removed_nothing_is_reported_and_not_retried(tmp_path, capsys):
    """'dropped the stale entry' is a claim about the file; it is made only when the file
    actually changed. A retry against an unchanged file would fail the same way."""
    kh = _kh(tmp_path, "[10.0.0.5]:2222 ssh-ed25519 AAAA\n")
    r = _Runner(_FakeProc(255, log=_real_changed(str(kh), host="[10.0.0.5]:2222")))
    assert _heal(r, known_hosts=kh) == 255
    assert _programs(r) == ["ssh", "ssh-keygen"]
    err = capsys.readouterr().err
    assert "dropped the stale entry" not in err, err
    assert "removed nothing" in err, err


def test_a_drop_that_changed_the_file_is_reported_and_retried(tmp_path, capsys):
    kh = _kh(tmp_path)
    r = _Runner(_FakeProc(255, log=_real_changed(str(kh))), _FakeProc(0), on_keygen=_emptying(kh))
    assert _heal(r, known_hosts=kh) == 0
    err = capsys.readouterr().err
    assert "dropped the stale entry" in err and "retrying once" in err


def test_the_retry_happens_once_at_most(tmp_path):
    """A host whose key changes again between the two connects is reported, not chased."""
    kh = _kh(tmp_path)
    changed = _FakeProc(255, log=_real_changed(str(kh)))
    r = _Runner(changed, _FakeProc(255, log=_real_changed(str(kh))), on_keygen=_emptying(kh))
    assert _heal(r, known_hosts=kh) == 255
    assert _programs(r) == ["ssh", "ssh-keygen", "ssh"]


def test_ssh_keygen_missing_keeps_ssh_s_code_and_warns(tmp_path, capsys):
    kh = _kh(tmp_path)

    def runner(argv, **kw):
        if argv[0] == "ssh-keygen":
            raise FileNotFoundError(2, "No such file or directory", "ssh-keygen")
        with open(argv[argv.index("-E") + 1], "a", encoding="utf-8") as fh:
            fh.write(_real_changed(str(kh)))
        return _FakeProc(255)

    assert _heal(runner, known_hosts=kh) == 255
    assert "ssh-keygen" in capsys.readouterr().err


def test_scp_reads_its_own_stderr_since_it_runs_no_remote_command(tmp_path):
    """scp has no `-E`, and nothing but ssh and scp writes its stderr, so the banner there is
    ssh's own."""
    kh = _kh(tmp_path)
    r = _Runner(_FakeProc(255, log=_real_changed(str(kh))), _FakeProc(0), on_keygen=_emptying(kh))
    assert _heal(r, known_hosts=kh, argv=("scp", "./f", "h:/tmp/f")) == 0
    assert _programs(r) == ["scp", "ssh-keygen", "scp"]
    assert "-E" not in r.calls[0]


def test_a_missing_ssh_binary_is_exit_2_not_a_traceback(capsys):
    def runner(argv, **kw):
        raise FileNotFoundError(2, "No such file or directory", argv[0])

    assert _heal(runner) == 2
    assert "cannot run ssh" in capsys.readouterr().err


# ---- CLI surface --------------------------------------------------------------------------------

def test_dry_run_prints_the_argv_and_runs_nothing(capsys):
    r = _Runner()
    assert F.main(["--dry-run", "--key", "/k", "h", "uptime"], run=r) == 0
    assert r.calls == []
    assert capsys.readouterr().out.strip().startswith("ssh -i /k ")


def test_dry_run_json_is_the_shared_envelope(capsys):
    import json
    assert F.main(["--dry-run", "--json", "--key", "/k", "h", "uptime"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True and payload["command"] == "fleet_ssh"
    assert payload["data"]["argv"][:1] == ["ssh"]


def test_a_usage_error_exits_2_without_connecting(capsys):
    r = _Runner()
    assert F.main(["--scp", "./only-one-path"], run=r) == 2
    assert r.calls == []
    assert "scp needs" in capsys.readouterr().err


def test_a_usage_error_under_json_prints_the_envelope(capsys):
    import json
    r = _Runner()
    assert F.main(["--json", "--dry-run", "--scp", "./only-one-path"], run=r) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and "scp needs" in payload["error"]


def test_a_json_flag_inside_the_remote_command_is_not_ours(capsys):
    """`fleet_ssh h tool --json` passes --json to the REMOTE tool; an envelope from us on its
    stdout would corrupt the stream the caller parses."""
    r = _Runner(_FakeProc(0))
    assert F.main(["--key", "/k", "h", "tool", "--json"], run=r) == 0
    assert r.calls[0][-1] == "tool --json"
    assert capsys.readouterr().out == ""


def test_a_crash_under_json_is_exit_2_with_an_envelope(monkeypatch, capsys):
    import json

    def boom(*_a, **_k):
        raise RuntimeError("planner broke")

    monkeypatch.setattr(F, "plan", boom)
    assert F.main(["--json", "--dry-run", "h", "uptime"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and "planner broke" in payload["error"]


def test_getuser_failing_is_exit_2(monkeypatch, capsys):
    import getpass

    def nobody():
        raise OSError("No username set in the environment")

    monkeypatch.setattr(getpass, "getuser", nobody)
    assert F.main(["--dry-run", "h", "uptime"]) == 2
    assert "local user" in capsys.readouterr().err


def test_an_uncreatable_known_hosts_directory_is_exit_2(tmp_path, capsys):
    """A FILE where the directory must go makes mkdir fail on every platform, unlike a mode bit."""
    blocker = tmp_path / "file"
    blocker.write_bytes(b"x")
    r = _Runner(_FakeProc(0))
    rc = F.main(["--key", "/k", "--trust-changing-host-keys", "--known-hosts",
                 str(blocker / "sub" / "kh"), "h", "uptime"], run=r)
    assert rc == 2 and r.calls == []
    assert "known-hosts" in capsys.readouterr().err


# ---- end to end through real processes, on a private PATH ---------------------------------------

def _stub_ssh_bin(tmp_path, exit_code):
    """A fake `ssh` and `ssh-keygen` on a private PATH, so no test can reach a real host.

    The fake ssh behaves as real ssh does under accept-new: while the known-hosts file holds the
    STALE key it writes the changed-key banner to its `-E` log and exits 255 WITHOUT running the
    command; otherwise it records that the remote command RAN and exits with its status. It also
    writes a byte that is not UTF-8 to stderr, which the capture must survive. The fake
    ssh-keygen drops the stale line, as `ssh-keygen -R` does."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    log = tmp_path / "calls.log"
    (bindir / "ssh").write_text(
        "#!/bin/sh\n"
        f"echo ssh >> '{log}'\n"
        "elog=/dev/stderr; prev=\n"
        "for a in \"$@\"; do\n"
        "  case $a in UserKnownHostsFile=*) kh=${a#UserKnownHostsFile=};; esac\n"
        "  [ \"$prev\" = -E ] && elog=$a\n"
        "  prev=$a\n"
        "done\n"
        "if grep -q STALE \"$kh\" 2>/dev/null; then\n"
        "  echo '@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @' >> \"$elog\"\n"
        "  echo \"Offending ED25519 key in $kh:1\" >> \"$elog\"\n"
        "  echo 'Host key verification failed.' >> \"$elog\"\n"
        "  exit 255\n"
        "fi\n"
        f"echo REMOTE-COMMAND-EXECUTED >> '{log}'\n"
        "printf 'bad byte \\377\\n' >&2\n"
        f"exit {exit_code}\n", encoding="utf-8")
    (bindir / "ssh-keygen").write_text(
        "#!/bin/sh\n"
        f"echo ssh-keygen >> '{log}'\n"
        "while [ $# -gt 0 ]; do [ \"$1\" = -f ] && kh=$2; shift; done\n"
        ": > \"$kh\"\n", encoding="utf-8")
    for stub in bindir.iterdir():
        stub.chmod(0o755)
    return bindir, log


@pytest.mark.skipif(sys.platform == "win32",
                    reason="the stub ssh is a #!/bin/sh script, which CreateProcess cannot launch by "
                           "bare name; the healing rule itself is covered by the injected-run tests")
@pytest.mark.parametrize("status", [0, 3])
def test_end_to_end_a_changed_key_heals_and_the_command_runs_once(tmp_path, status):
    bindir, log = _stub_ssh_bin(tmp_path, status)
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    (home / ".ssh" / "known_hosts_fleet").write_text("h ssh-ed25519 STALE\n", encoding="utf-8")
    env = {**os.environ, "PATH": str(bindir) + os.pathsep + os.environ.get("PATH", ""),
           "HOME": str(home), "USERPROFILE": str(home)}
    done = subprocess.run([sys.executable, F.__file__, "--key", "/k", "--trust-changing-host-keys",
                           "h", "apt-get -y upgrade"],
                          env=env, capture_output=True, timeout=60)
    assert b"Traceback" not in done.stderr, "an undecodable byte on ssh's stderr must not crash"
    assert done.returncode == status, done.stderr
    assert log.read_text(encoding="utf-8").split() == ["ssh", "ssh-keygen", "ssh",
                                                        "REMOTE-COMMAND-EXECUTED"]


# ---- scp argument shapes -----------------------------------------------------------------------

def test_scp_with_more_than_two_paths_is_refused_not_truncated(capsys):
    """`--scp f1 f2 host:/dir/` used to run `scp f1 f2`, a LOCAL copy overwriting f2."""
    r = _Runner()
    assert F.main(["--scp", "--key", "/k", "f1", "f2", "hst:/dir/"], run=r) == 2
    assert r.calls == []
    assert "exactly" in capsys.readouterr().err


def test_a_bracketed_ipv6_target_resolves_to_the_address():
    assert F.scp_host("./f", "[fe80::1]:/p") == "fe80::1"
    assert F.scp_host("./f", "root@[::1]:/p") == "::1"
    assert F.scp_user("./f", "root@[::1]:/p") == "root"
    assert F.with_scp_user("[::1]:/p", "root") == "root@[::1]:/p"
    assert F.scp_host("./f", "root@host:/p") == "host"


def test_a_windows_drive_path_is_local():
    for side in ("C:\\Users\\me\\f", "d:\\x"):
        assert not F.is_remote_side(side), side
        assert F.with_scp_user(side, "root") == side
    # The forward-slash spelling is a drive only where scp itself reads it as one.
    assert F.remote_prefix("C:/Users/me/f", windows=True) is None
    assert F.remote_prefix("h:/p", windows=False) == "h"
    line, host, _kh = plan(["--scp", "--user", "root", "--key", "/k", "C:\\Users\\me\\f",
                            "hst:/tmp/f"])
    assert line.endswith("C:\\Users\\me\\f root@hst:/tmp/f")
    assert host == "hst"


# ---- key readability is probed by opening, not by os.access -------------------------------------

@pytest.mark.skipif(sys.platform == "win32",
                    reason='Windows has no POSIX mode bits: chmod(0o000) leaves the file readable, so an unreadable candidate cannot be created')
def test_resolve_key_does_not_trust_os_access(tmp_path, monkeypatch):
    """On Windows os.access(R_OK) is True for any existing file whatever its ACL. Simulate that and
    the unreadable candidate must still be skipped, because the probe is a real open()."""
    unreadable = tmp_path / "shared" / "u@anyhost_nopass.key"
    unreadable.parent.mkdir()
    unreadable.write_text("k")
    unreadable.chmod(0o000)
    try:
        with open(unreadable, "rb"):
            pytest.skip("running with privileges that read a mode-000 file (root)")
    except OSError:
        pass
    readable = tmp_path / "ok.key"
    readable.write_text("k")
    monkeypatch.setattr(os, "access", lambda *a, **k: True)
    assert F.resolve_key("u", (str(unreadable), str(readable)), home=str(tmp_path)) == str(readable)


@pytest.mark.skipif(sys.platform == "win32",
                    reason='Windows has no POSIX mode bits: chmod(0o000) leaves the dir readable')
def test_a_candidate_inside_an_unreadable_directory_is_skipped_not_a_crash(tmp_path):
    """A root-only key DIRECTORY: Path.is_file raised PermissionError there before 3.12."""
    locked = tmp_path / "rootonly"
    locked.mkdir()
    (locked / "u.key").write_text("k")
    readable = tmp_path / "ok.key"
    readable.write_text("k")
    locked.chmod(0o000)
    try:
        if os.access(locked, os.R_OK | os.X_OK):
            pytest.skip("running with privileges that read a mode-000 dir (root)")
        found = F.resolve_key("u", (str(locked / "u.key"), str(readable)), home=str(tmp_path))
    finally:
        locked.chmod(0o755)
    assert found == str(readable)


# ---- main() wiring, not only plan() -------------------------------------------------------------

def _home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def test_main_passes_the_trust_flag_through_as_healing(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    fleet = home / ".ssh" / "known_hosts_fleet"
    fleet.parent.mkdir()
    fleet.write_text("h ssh-ed25519 AAAA\n", encoding="utf-8")
    r = _Runner(_FakeProc(255, log=_real_changed(str(fleet))), _FakeProc(0),
                on_keygen=_emptying(fleet))
    assert F.main(["--key", "/k", "--trust-changing-host-keys", "h", "uptime"], run=r) == 0
    assert r.calls[1] == ["ssh-keygen", "-R", "h", "-f", str(fleet)]
    assert _programs(r) == ["ssh", "ssh-keygen", "ssh"]


def test_main_creates_the_fleet_known_hosts_directory_before_ssh_runs(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    r = _Runner(_FakeProc(0))
    assert F.main(["--key", "/k", "--trust-changing-host-keys", "h", "uptime"], run=r) == 0
    assert (home / ".ssh").is_dir()


def test_main_without_the_trust_flag_never_heals(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    r = _Runner(_FakeProc(255, _real_changed(str(home / ".ssh" / "known_hosts"))
                          + "Host key verification failed.\n"))
    assert F.main(["--key", "/k", "h", "uptime"], run=r) == 255
    assert [c[0] for c in r.calls] == ["ssh"]


def test_main_passes_the_remote_exit_code_through(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)
    r = _Runner(_FakeProc(7))
    assert F.main(["--key", "/k", "h", "exit 7"], run=r) == 7


def test_main_with_no_host_is_a_usage_error(capsys):
    r = _Runner()
    assert F.main(["--key", "/k"], run=r) == 2
    assert r.calls == []
    assert "need a <host>" in capsys.readouterr().err


def test_dry_run_survives_a_cp1252_stdout():
    """A Windows pipe is cp1252; a path it cannot encode must not crash the print."""
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
    env.pop("PYTHONUTF8", None)
    done = subprocess.run([sys.executable, F.__file__, "--dry-run", "--key", "/k", "--scp",
                           "./arrow\u2192f", "hst:/tmp/"], env=env, capture_output=True, timeout=60)
    assert done.returncode == 0, done.stderr
    assert b"hst:/tmp/" in done.stdout
