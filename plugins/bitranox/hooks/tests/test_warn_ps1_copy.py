"""Tests for warn-ps1-copy.py - a local .ps1 copied to a remote host unchecked. ASCII only.

The recorded miss: a hand-written .ps1 was copied with scp and run with -File, and its parse error
only surfaced on the remote host. The nudge names pwshpy first and a local [ScriptBlock]::Create
syntax check second. It is a NUDGE: every path exits 0.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import warn_ps1_copy as W

HOOK = Path(__file__).resolve().parent.parent / "warn-ps1-copy.py"


def _n(cmd, tool_name="Bash"):
    return W.notice(cmd, tool_name)


# --- fires: scp to a remote destination -----------------------------------------------------------

def test_scp_of_a_local_ps1_to_a_remote_host_fires():
    ctx = _n("scp /tmp/check.ps1 admin@winhost:C:/temp/")
    assert ctx
    assert "bitranox:coding-python-pwshpy" in ctx
    assert "[ScriptBlock]::Create" in ctx


def test_scp_options_with_values_are_skipped_not_read_as_operands():
    assert _n("scp -i /opt/keys/id.key -P 2222 -o BatchMode=yes /tmp/a.ps1 winhost:/c/temp/a.ps1")
    assert _n("scp -oBatchMode=yes -q /tmp/a.ps1 winhost:")
    assert _n("scp -rp -F /opt/cfg /tmp/a.ps1 winhost:/tmp/")


def test_one_ps1_among_several_sources_fires():
    assert _n("scp /tmp/a.txt /tmp/b.ps1 /tmp/c.json winhost:/tmp/")


def test_a_quoted_path_with_a_space_fires():
    assert _n('scp -P 22 "/tmp/my script.ps1" winhost:/tmp/')


def test_the_extension_is_matched_case_insensitively():
    assert _n("scp /tmp/SETUP.PS1 winhost:/tmp/")


def test_a_copy_inside_a_chained_command_fires():
    assert _n("cd /tmp && scp job.ps1 admin@winhost:C:/temp/ && "
              "ssh admin@winhost powershell -File C:/temp/job.ps1")


def test_a_copy_behind_a_launcher_fires():
    assert _n("timeout 60 scp /tmp/x.ps1 winhost:/tmp/")
    assert _n("sshpass -f /opt/pw scp /tmp/x.ps1 winhost:/tmp/")


def test_an_scp_url_and_a_bracketed_ipv6_destination_fire():
    assert _n("scp /tmp/x.ps1 scp://winhost:22/tmp/")
    assert _n("scp /tmp/x.ps1 [2001:db8::1]:/tmp/")


def test_a_copy_split_over_line_continuations_fires():
    """Measured in the replay: the scp, its .ps1 and its destination on three lines."""
    cmd = "scp -o BatchMode=yes -i /opt/k \\\n  /tmp/run.ps1 \\\n  'admin@winhost:C:/temp/run.ps1' 2>&1 | tail -10"
    assert "\\\n" in cmd
    assert _n(cmd)
    assert W.notice(cmd)                                  # the default tool reading is Bash


def test_an_end_of_options_marker_is_honoured():
    assert _n("scp -- /tmp/x.ps1 winhost:/tmp/")


def test_a_redirection_after_the_copy_is_not_read_as_its_destination():
    assert _n("scp /tmp/x.ps1 winhost:/tmp/ 2>&1")
    assert _n("scp /tmp/x.ps1 winhost:/tmp/ > /tmp/scp.log")


# --- fires: rsync to a remote destination ---------------------------------------------------------

def test_rsync_of_a_local_ps1_fires_past_its_value_options():
    assert _n('rsync -av -e "ssh -i /opt/k" ./x.ps1 user@winhost:/tmp/')
    assert _n('rsync -av --rsh "ssh -p 22" ./x.ps1 winhost:/tmp/')
    assert _n("rsync -av --rsh=ssh ./x.ps1 winhost::module/")


def test_rsync_excluding_ps1_files_is_quiet():
    """The `*.ps1` here is an option VALUE, not a source."""
    assert _n("rsync -av --exclude '*.ps1' ./dir winhost:/tmp/") is None
    assert _n("rsync -av --exclude=*.ps1 ./dir winhost:/tmp/") is None


# --- fires: the script reaches ssh on stdin -------------------------------------------------------

def test_a_ps1_redirected_into_ssh_fires():
    assert _n("ssh winhost 'cat > /tmp/x.ps1' < /tmp/x.ps1")
    assert _n('ssh winhost "powershell -Command -" </tmp/x.ps1')


def test_a_ps1_piped_into_ssh_fires():
    assert _n("cat /tmp/x.ps1 | ssh winhost 'cat > x.ps1'")


def test_a_non_ps1_on_ssh_stdin_is_quiet():
    assert _n("ssh winhost 'cat > /tmp/x' < /tmp/x.txt") is None
    assert _n("cat /tmp/x.txt | ssh winhost 'cat > x'") is None


def test_a_ps1_piped_into_something_other_than_ssh_is_quiet():
    assert _n("cat /tmp/x.ps1 | grep -n Param") is None


def test_a_logical_or_is_not_a_pipe():
    assert _n("cat /tmp/x.ps1 || ssh winhost hostname") is None


# --- quiet: not a local-to-remote copy -------------------------------------------------------------

def test_a_copy_from_a_remote_host_to_local_is_quiet():
    assert _n("scp winhost:/tmp/x.ps1 /tmp/") is None
    assert _n("rsync -av winhost:/tmp/x.ps1 ./") is None


def test_a_remote_to_remote_copy_has_no_local_script_and_is_quiet():
    assert _n("scp hostone:/tmp/a.ps1 hosttwo:/tmp/") is None


def test_a_local_copy_is_quiet():
    assert _n("cp /tmp/x.ps1 /opt/scripts/") is None
    assert _n("scp /tmp/x.ps1 /opt/scripts/x.ps1") is None


def test_a_single_letter_drive_is_local_not_a_host():
    assert _n("scp /tmp/x.ps1 C:/temp/") is None


def test_a_non_ps1_copy_is_quiet():
    assert _n("scp /tmp/x.py winhost:/tmp/") is None


def test_running_a_remote_ps1_without_copying_it_is_quiet():
    assert _n("ssh winhost powershell -File C:/temp/x.ps1") is None


@pytest.mark.parametrize("cmd", [
    'echo "scp /tmp/x.ps1 winhost:/tmp/"',
    "ls /tmp/*.ps1",
    "git add tools/x.ps1",
    "grep -n Param /tmp/x.ps1",
    "cat > /tmp/notes.txt <<'EOF'\nscp /tmp/x.ps1 winhost:/tmp/\nEOF",
])
def test_a_ps1_merely_mentioned_is_quiet(cmd):
    assert _n(cmd) is None


def test_a_copy_already_syntax_checked_in_the_same_command_is_quiet():
    check = ('pwsh -NoProfile -Command "$null = [ScriptBlock]::Create((Get-Content -Raw '
             '/tmp/x.ps1))"')
    assert _n(check + " && scp /tmp/x.ps1 winhost:/tmp/") is None


def test_empty_and_non_string_commands_are_quiet():
    assert _n("") is None
    assert _n(None) is None


# --- the PowerShell tool reads its own command line -----------------------------------------------

def test_the_powershell_tool_arm_fires_on_a_windows_path():
    assert _n(r"scp C:\temp\x.ps1 admin@winhost:C:/temp/", "PowerShell")
    assert _n(r"scp.exe -i C:\keys\id.key .\x.ps1 winhost:/tmp/", "PowerShell")


def test_the_powershell_tool_arm_pipes_get_content_into_ssh():
    assert _n(r"Get-Content C:\temp\x.ps1 | ssh winhost 'cat > x.ps1'", "PowerShell")


# --- main(): the hook protocol --------------------------------------------------------------------

def _run_hook(event):
    proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event),
                          capture_output=True, check=False, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def test_main_emits_additional_context_and_exits_zero():
    rc, out, err = _run_hook({"tool_name": "Bash",
                              "tool_input": {"command": "scp /tmp/x.ps1 winhost:/tmp/"}})
    assert rc == 0 and err == ""
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert "pwshpy" in payload["additionalContext"]
    assert "permissionDecision" not in payload         # a nudge, never a block


def test_main_is_silent_for_a_quiet_command_and_a_non_shell_tool():
    assert _run_hook({"tool_name": "Bash", "tool_input": {"command": "ls"}}) == (0, "", "")
    assert _run_hook({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x.ps1"}}) == (0, "", "")


def test_main_survives_malformed_input():
    proc = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, check=False,
                          text=True, encoding="utf-8")
    assert (proc.returncode, proc.stdout) == (0, "")
