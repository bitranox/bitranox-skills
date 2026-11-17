"""The cmd.exe `if`-swallows-the-chain guard.

In cmd.exe `if <cond> a & b` parses as `if <cond> (a & b)`, so a "clean, then recreate" one-liner
sent over ssh to a Windows host runs nothing after the condition when the condition is false, and
exits 0 with no output. These tests pin the shapes it refuses, the forms it must pass, and that the
forms its own refusal offers pass it.
"""

import io
import json
import re
import sys
from pathlib import Path

import block_cmd_if_chain as guard
import pytest

HOOK = Path(guard.__file__)


def fires(command: str, tool_name: str = "Bash") -> bool:
    return guard.find_swallowing_if(command, tool_name) is not None


def run_main(command: str, tool_name: str = "Bash", monkeypatch=None):
    event = {"tool_name": tool_name, "tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    err = io.StringIO()
    monkeypatch.setattr(sys, "stderr", err)
    return guard.main(), err.getvalue()


# ------------------------------------------------------------- the real failing lines


def test_the_rmdir_then_mkdir_line_is_refused() -> None:
    assert fires(r'ssh -o BatchMode=yes admin@win "if exist C:\temp\x rmdir /s /q C:\temp\x & mkdir C:\temp\x"')


def test_the_tar_and_pytest_chain_is_refused() -> None:
    command = ('ssh win "cd /d C:\\temp && if exist tbx rmdir /s /q tbx & mkdir tbx && '
               'tar -xf tbx.tar -C tbx && cd tbx && python -m pytest -q"')
    assert guard.find_swallowing_if(command) == (
        "cd /d C:\\temp && if exist tbx rmdir /s /q tbx & mkdir tbx && "
        "tar -xf tbx.tar -C tbx && cd tbx && python -m pytest -q")


def test_an_errorlevel_chain_is_refused() -> None:
    assert fires('ssh win "build.cmd & if errorlevel 1 echo FAILED & type build.log"')


def test_an_or_chain_after_the_if_is_refused() -> None:
    assert fires('ssh win "if not exist out mkdir out || echo cannot create out"')


@pytest.mark.parametrize("remote", [
    'if defined TEMP echo %TEMP% & dir',
    'if /i "%OS%"=="Windows_NT" echo nt & ver',
    'if not "%X%"=="1" echo no & echo next',
    'if %X%==1 echo one && echo next',
    'if %N% GEQ 3 echo many & echo next',
    '@if exist x del x & echo done',
    'if cmdextversion 2 echo ok & echo next',
])
def test_each_cmd_condition_form_is_recognised(remote: str) -> None:
    assert fires('ssh win "' + remote.replace('"', '\\"') + '"')


def test_cmd_slash_c_with_its_own_quotes_is_unwrapped() -> None:
    assert fires('ssh win \'cmd /c "if exist x rmdir /s /q x & mkdir x"\'')
    assert fires('ssh win \'cmd.exe /s /c "if exist x rmdir /s /q x & mkdir x"\'')


def test_quotes_the_local_shell_removes_never_reach_the_inner_cmd() -> None:
    # The LOCAL shell strips these double quotes, so the remote line is
    # `cmd.exe /s /c if exist x rmdir /s /q x & mkdir x`, which the outer cmd.exe splits at `&`.
    assert not fires('ssh win cmd.exe /s /c "if exist x rmdir /s /q x & mkdir x"')


def test_launchers_and_ssh_value_flags_are_skipped() -> None:
    assert fires('timeout 120 ssh -p 2222 -i /opt/k -tt win "if exist x del x & echo gone"')
    assert fires('ssh -oBatchMode=yes -- win "if exist x del x & echo gone"')


def test_the_powershell_tool_reads_the_same_ssh_call() -> None:
    assert fires('ssh win "if exist x rmdir /s /q x & mkdir x"', tool_name="PowerShell")


def test_ssh_options_held_in_a_variable_do_not_hide_the_remote_if() -> None:
    # Replay misses: `$K` is one unexpanded word that the shell later splits into options.
    assert fires('K="-i /opt/k -o BatchMode=yes"; ssh $K admin@win "if exist t rmdir /s /q t & mkdir t"')
    assert fires('ssh "${O[@]}" $H "if not exist t mkdir t & where uv"')


def test_a_variable_host_before_the_remote_string_is_the_host() -> None:
    assert fires("ssh $H 'if exist t rmdir /s /q t & mkdir t'")


def test_ssh_called_through_a_variable_holding_it_is_judged() -> None:
    assert fires('SSH="ssh -i /opt/k admin@win"; $SSH \'cmd /c "if exist t rmdir /s /q t & mkdir t"\'')
    assert fires('S="ssh -o BatchMode=yes"; $S win "if exist t rmdir /s /q t & mkdir t"')


def test_a_variable_program_that_is_not_ssh_passes() -> None:
    assert not fires('RUN="bash -c"; $RUN "if exist t rmdir /s /q t & mkdir t"')
    assert not fires('$X "if exist t rmdir /s /q t & mkdir t"')


def test_a_later_statement_of_a_multi_statement_command_is_judged() -> None:
    assert fires('cd /tmp && scp a.tar win:C:/temp/ && ssh win "if exist t rmdir /s /q t & mkdir t"')


# ------------------------------------------------------------- the fixes, which must pass


def test_the_parenthesised_if_passes() -> None:
    assert not fires('ssh win "(if exist tbx rmdir /s /q tbx) & mkdir tbx && tar -xf tbx.tar -C tbx"')


def test_a_parenthesised_if_after_other_steps_passes() -> None:
    assert not fires('ssh win "cd /d C:\\temp && (if exist tbx rmdir /s /q tbx) & mkdir tbx"')


def test_one_call_per_step_passes() -> None:
    assert not fires('ssh win "if exist tbx rmdir /s /q tbx" && ssh win "mkdir tbx"')


def test_running_a_shipped_script_passes() -> None:
    assert not fires('scp prep.cmd win:C:/temp/ && ssh win "C:\\temp\\prep.cmd"')


def test_block_form_passes() -> None:
    assert not fires('ssh win "if exist tbx ( rmdir /s /q tbx & mkdir tbx )"')
    assert not fires('ssh win "if exist tbx (rmdir /s /q tbx) else (mkdir tbx)"')
    # What a `& c` after the block belongs to was not verified on a host, so it is not refused.
    assert not fires('ssh win "if exist tbx (rmdir /s /q tbx) & mkdir tbx"')


def test_a_chain_inside_a_later_group_is_not_the_parenthesised_ifs() -> None:
    assert not fires('ssh win "(if exist x del x) & (mkdir x & echo made)"')


def test_a_quoted_ampersand_in_the_ifs_body_is_not_a_chain() -> None:
    assert not fires('ssh win "if exist x echo \\"a & b\\""')


def test_a_local_ampersand_redirection_is_dropped() -> None:
    assert not fires('ssh win "if exist x del x" &>/tmp/log.txt')


def test_an_escaped_or_quoted_ampersand_is_not_a_chain() -> None:
    assert not fires('ssh win "if exist x echo a ^& b"')
    assert not fires('ssh win "if exist \\"C:\\a & b\\" del x"')


def test_an_if_with_nothing_after_it_passes() -> None:
    assert not fires('ssh win "if exist x del x"')


def test_the_refusals_offered_forms_pass_the_guard() -> None:
    offered = re.findall(r'ssh <host> "[^"]*"', guard.refusal("if exist X rmdir /s /q X & mkdir X"))
    assert len(offered) == 4, offered
    for form in offered:
        assert not fires(form.replace("<host>", "win")), form


# ------------------------------------------------------------- POSIX, local and data: must pass


def test_posix_if_over_ssh_passes() -> None:
    assert not fires("ssh linux 'if [ -e x ]; then rm -rf x; fi && mkdir x'")
    assert not fires("ssh linux 'if test -d x; then rm -rf x; fi; mkdir x && tar -xf a.tar -C x'")
    assert not fires('ssh linux "if [[ $A == b ]]; then echo y; fi && echo next"')
    assert not fires("ssh linux 'if ! grep -q x f; then echo no; fi && echo next'")


def test_a_posix_quoted_comparison_is_kept_silent_by_its_then() -> None:
    # `"$A" == "b"` has the shape of a cmd.exe comparison; only the `then` says it is POSIX.
    assert not fires("ssh linux 'if \"$A\" == \"b\" ; then echo y; fi && echo next'")


def test_a_posix_dollar_comparison_is_not_cmd() -> None:
    assert not fires("ssh linux 'if $A==b echo x & echo y'")


def test_an_ssh_to_a_linux_host_with_an_and_chain_passes() -> None:
    assert not fires("ssh -o BatchMode=yes root@host 'cd /opt/app && git pull && systemctl restart app'")


def test_a_remote_powershell_command_is_not_cmd() -> None:
    assert not fires("ssh win 'powershell -NoProfile -Command \"if (Test-Path x) { rm x }; mkdir x\"'")


def test_a_local_cmd_if_without_ssh_passes() -> None:
    assert not fires("if exist x rmdir /s /q x & mkdir x")
    assert not fires('cmd /c "if exist x rmdir /s /q x & mkdir x"')


def test_a_local_posix_if_passes() -> None:
    assert not fires("if [ -e x ]; then rm -rf x; fi && mkdir x")


def test_a_quoted_mention_is_data() -> None:
    assert not fires('echo "ssh win \\"if exist x rmdir x & mkdir x\\""')
    assert not fires("git commit -m 'block ssh win \"if exist x a & b\"'")
    assert not fires("grep -rn 'if exist x rmdir x & mkdir x' docs/")


def test_a_heredoc_body_mentioning_it_is_data() -> None:
    command = "cat > /tmp/notes.txt <<'EOF'\nssh win \"if exist x rmdir /s /q x & mkdir x\"\nEOF"
    assert not fires(command)


def test_a_local_redirection_after_the_remote_command_is_not_a_chain() -> None:
    # Replay false positive: the LOCAL shell consumes `2>&1 | tail`; it never reaches cmd.exe.
    assert not fires("ssh win 'del x.ps1 && if not exist x.ps1 echo gone' 2>&1 | tail -2")


def test_a_remote_redirection_is_not_a_chain() -> None:
    assert not fires('ssh win "if exist x dir x 2>&1"')
    assert not fires('ssh win "if exist x type x 1>&2"')


def test_an_unquoted_cmd_slash_c_belongs_to_the_outer_cmd() -> None:
    # Replay false positive: the OUTER cmd.exe splits `cmd /c if exist X rmdir X` from `mkdir X`,
    # so the mkdir runs whatever the condition says.
    assert not fires('ssh win "cmd /c if exist C:\\temp\\b rmdir /s /q C:\\temp\\b & mkdir C:\\temp\\b"')


def test_a_later_check_swallowed_by_an_earlier_if_is_refused() -> None:
    # Replay true positive: the final existence check runs only when the .ps1 existed.
    assert fires('ssh win "rmdir /s /q w & if exist w.ps1 del w.ps1 & '
                 'if exist w (echo STILL_THERE) else (echo GONE)"')


def test_ssh_with_no_remote_command_passes() -> None:
    assert not fires("ssh win")
    assert not fires("ssh -p 22")


# ------------------------------------------------------------- the hook as a process


def test_main_refuses_with_the_fix_and_the_footer(monkeypatch) -> None:
    rc, err = run_main('ssh win "if exist t rmdir /s /q t & mkdir t"', monkeypatch=monkeypatch)
    assert rc == 2
    assert "(if exist X rmdir /s /q X) & mkdir X" in err
    assert "Remote line: if exist t rmdir /s /q t & mkdir t" in err
    assert "one call per step" in err
    assert err.rstrip().endswith(guard.shell_text.WHOLE_CALL_REFUSED)


def test_main_passes_a_fixed_line(monkeypatch) -> None:
    rc, err = run_main('ssh win "(if exist t rmdir /s /q t) & mkdir t"', monkeypatch=monkeypatch)
    assert (rc, err) == (0, "")


def test_main_fails_open_on_unreadable_input(monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert guard.main() == 0
    monkeypatch.setattr(sys, "stdin", io.StringIO("[1, 2]"))
    assert guard.main() == 0


def test_an_unbalanced_quote_fails_open() -> None:
    assert not fires('ssh win "if exist x del x & echo')


def test_a_long_remote_line_is_shortened_in_the_refusal() -> None:
    line = "if exist x del x & echo " + "y" * 600
    assert len(guard.refusal(line)) < 1400


def test_registered_on_bash_and_powershell() -> None:
    hooks = json.loads((HOOK.parent / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    groups = [g for g in hooks["PreToolUse"]
              if any("block-cmd-if-chain.py" in h["command"] for h in g["hooks"])]
    assert [g["matcher"] for g in groups] == ["Bash|PowerShell"]
    command = next(h["command"] for h in groups[0]["hooks"] if "block-cmd-if-chain.py" in h["command"])
    assert "run-python.sh\" --hook " in command


def test_replay_decision_is_recorded() -> None:
    doc = guard.__doc__
    assert "Decisions:" in doc
    block = doc.split("Decisions:", 1)[1]
    for needle in ("guard_replay.py", "false positive", "Reopen if", "Rejected:"):
        assert needle in block, needle
    for name in re.findall(r"`(test_\w+)`", block):
        assert name in globals(), name
