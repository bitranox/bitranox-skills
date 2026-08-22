"""Tests for fleet_ssh.py - one option set, one resolved key, no interactive prompt. ASCII only."""
import sys
import io
import os

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
    line, _host, _kh = plan(["--scp", "--user", "root", "--key", "/k", "./f", "h:/tmp/f"])
    assert line.endswith("./f root@h:/tmp/f")


def test_user_flag_reaches_a_remote_scp_source_too():
    line, _host, _kh = plan(["--scp", "--user", "root", "--key", "/k", "h:/tmp/f", "./f"])
    assert line.endswith("root@h:/tmp/f ./f")


def test_a_user_named_in_the_path_wins_over_the_flag():
    line, _host, _kh = plan(["--scp", "--user", "someone", "--key", "/k", "./f", "root@h:/tmp/f"])
    assert line.endswith("./f root@h:/tmp/f")


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
    line, _host, _kh = plan(["--scp", "--user", "root", "./f", "h:/tmp/f"], home=str(home))
    assert f"-i {key}" in line and "root@h:/tmp/f" in line


def test_with_scp_user_only_touches_a_remote_side_naming_no_user():
    assert F.with_scp_user("h:/p", "root") == "root@h:/p"
    assert F.with_scp_user("root@h:/p", "other") == "root@h:/p"
    assert F.with_scp_user("/local/f", "root") == "/local/f"
    assert F.with_scp_user("/mnt/c:/weird", "root") == "/mnt/c:/weird"    # a path, not a host


def test_scp_host_finds_the_remote_side():
    assert F.scp_host("./f", "h:/p") == "h"
    assert F.scp_host("root@h:/p", "./f") == "h"
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
    line, _host, _kh = plan(["--scp", "--key", "/k", "./f", "h:/p"])
    assert line.endswith("./f h:/p")
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
    for argv in (["--key", "/k", "h", "uptime"], ["--scp", "--key", "/k", "./f", "h:/p"]):
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
    assert "StrictHostKeyChecking=no" in line
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


def test_host_key_changed_matches_both_ssh_phrasings():
    assert F.HOST_KEY_CHANGED.search("WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!")
    assert F.HOST_KEY_CHANGED.search("Host key verification failed.")
    assert not F.HOST_KEY_CHANGED.search("Permission denied (publickey).")


# ---- the retry: this decides whether a remote command runs once or twice -------------------------

class _FakeProc:
    def __init__(self, returncode=0, stderr="", stdout=""):
        self.returncode, self.stderr, self.stdout = returncode, stderr, stdout


class _Runner:
    """A fake process runner recording every argv it was handed."""

    def __init__(self, *results):
        self.results, self.calls = list(results), []

    def __call__(self, argv, **kw):
        self.calls.append(list(argv))
        return self.results.pop(0) if self.results else _FakeProc()


_CHANGED = "@@@ REMOTE HOST IDENTIFICATION HAS CHANGED! @@@\n"


def _heal(runner, *, heal=True, host="h", known_hosts="/kh", argv=("ssh", "h", "uptime")):
    return F.run_with_host_key_healing(list(argv), host=host, known_hosts=known_hosts,
                                       heal=heal, run=runner)


def test_a_clean_run_is_executed_exactly_once():
    r = _Runner(_FakeProc(0, ""))
    assert _heal(r) == 0
    assert len(r.calls) == 1


def test_a_changed_host_key_drops_the_entry_and_retries_once():
    r = _Runner(_FakeProc(255, _CHANGED), _FakeProc(0, ""), _FakeProc(0, ""))
    assert _heal(r) == 0
    assert r.calls[1] == ["ssh-keygen", "-R", "h", "-f", "/kh"]
    assert r.calls[0] == r.calls[2] == ["ssh", "h", "uptime"]     # the command twice, no more


def test_a_changed_host_key_is_not_healed_when_trust_was_not_asked_for():
    """Strict mode must report the mismatch, not quietly accept the new key."""
    r = _Runner(_FakeProc(255, _CHANGED))
    assert _heal(r, heal=False) == 255
    assert len(r.calls) == 1


def test_an_ordinary_failure_is_never_retried():
    """A remote command fails for a thousand reasons; re-running a MUTATING one applies it twice."""
    r = _Runner(_FakeProc(1, "rm: cannot remove 'x': No such file\n"))
    assert _heal(r, argv=("ssh", "h", "rm x")) == 1
    assert len(r.calls) == 1


def test_a_zero_exit_is_never_retried_even_if_stderr_mentions_the_phrase():
    """Guards against keying on the message alone - the text can appear in a command's output."""
    r = _Runner(_FakeProc(0, "echo Host key verification failed\n"))
    assert _heal(r, argv=("ssh", "h", "cat log")) == 0
    assert len(r.calls) == 1


def test_no_host_means_no_retry():
    """A local-to-local scp has no host to heal; retrying would just repeat the copy."""
    r = _Runner(_FakeProc(255, _CHANGED))
    assert _heal(r, host=None, argv=("scp", "a", "b")) == 255
    assert len(r.calls) == 1


def test_the_retry_happens_at_most_once():
    r = _Runner(_FakeProc(255, _CHANGED), _FakeProc(0, ""), _FakeProc(255, _CHANGED))
    assert _heal(r) == 255
    assert len([c for c in r.calls if c[0] == "ssh"]) == 2


# ---- CLI surface --------------------------------------------------------------------------------

def test_dry_run_prints_the_argv_and_runs_nothing(capsys):
    r = _Runner()
    assert F.main(["--dry-run", "--key", "/k", "h", "uptime"], run=r) == 0
    assert r.calls == []
    assert capsys.readouterr().out.strip().startswith("ssh -i /k ")


def test_dry_run_json_is_machine_readable(capsys):
    import json
    assert F.main(["--dry-run", "--json", "--key", "/k", "h", "uptime"]) == 0
    assert json.loads(capsys.readouterr().out)["argv"][:1] == ["ssh"]


def test_a_usage_error_exits_2_without_connecting(capsys):
    r = _Runner()
    assert F.main(["--scp", "./only-one-path"], run=r) == 2
    assert r.calls == []
    assert "scp needs" in capsys.readouterr().err
