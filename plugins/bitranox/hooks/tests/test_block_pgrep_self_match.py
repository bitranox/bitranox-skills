"""Tests for block-pgrep-self-match.py (PreToolUse(Bash) bracket-trick guard).

Contract: reads a PreToolUse event JSON on stdin. Exit 2 (with stderr) blocks only
when a pgrep/pkill bracket-trick pattern [X]rest has its de-bracketed literal Xrest
appearing contiguously elsewhere in the same command. Every other path exits 0.

All content is ASCII.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import block_pgrep_self_match as B

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "block-pgrep-self-match.py"
SHIM = HOOKS_DIR / "run-python.sh"


def run_main(monkeypatch, command):
    payload = json.dumps({"tool_input": {"command": command}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    return B.main()


def test_no_pgrep_pkill_passes(monkeypatch):
    assert run_main(monkeypatch, "ls -la /tmp && echo done") == 0


def test_bracket_trick_clean_passes(monkeypatch):
    # The literal 'nginx' appears ONLY via the bracket form -> trick intact -> allow.
    assert run_main(monkeypatch, 'pgrep -f "[n]ginx"') == 0


def test_bracket_trick_defeated_by_echo_blocks(monkeypatch, capsys):
    cmd = 'pgrep -f "[n]ginx"; echo "=== nginx running? ==="'
    assert run_main(monkeypatch, cmd) == 2
    err = capsys.readouterr().err
    assert "BLOCKED" in err
    assert "[n]ginx -> nginx" in err


def test_plain_f_literal_blocks(monkeypatch, capsys):
    # This case used to be ALLOWED, on the recorded belief that catching it would
    # mean "blocking every pkill -f". That premise was wrong, and it is why the
    # error kept recurring: a plain `-f` literal ALWAYS self-matches, because -f
    # matches /proc/*/cmdline and this shell's own cmdline holds the literal.
    assert run_main(monkeypatch, "pgrep -f nginx") == 2
    assert "PLAIN" in capsys.readouterr().err


def test_plain_f_literal_over_ssh_blocks(monkeypatch):
    # The real hit that forced the hardening: killed the REMOTE shell (exit 255).
    assert run_main(monkeypatch, "ssh host 'pkill -f \"iperf3 -s\" 2>/dev/null'") == 2


def test_plain_f_literal_bundled_flags_blocks(monkeypatch):
    assert run_main(monkeypatch, 'pkill -af "vnc.*py"') == 2


def test_f_pattern_from_variable_passes(monkeypatch):
    # argv holds the UNEXPANDED "$NAME", so the expanded value is never in this
    # shell's own cmdline and cannot self-match.
    assert run_main(monkeypatch, 'pkill -f "$NAME"') == 0


def test_pkill_without_dash_f_passes(monkeypatch):
    # Without -f, pkill/pgrep match comm (the program name), not the full cmdline,
    # so a shell named bash/sh cannot match a program-name pattern.
    assert run_main(monkeypatch, "pkill -x iperf3") == 0
    assert run_main(monkeypatch, "pgrep iperf3") == 0


def test_explicit_self_exclusion_passes(monkeypatch):
    assert run_main(monkeypatch, 'pgrep -f "[n]ginx" | grep -vw "$$"') == 0


def test_git_commit_heredoc_body_not_blocked(monkeypatch):
    # The real false positive: a commit message (heredoc body) that DISCUSSES the pattern.
    # A heredoc body is stdin data, never the shell's argv, so it cannot self-match.
    cmd = "git commit -q -F - <<'MSG'\nnudge: pkill/pgrep -f -> procsig, ip neigh -> guestip\nMSG"
    assert run_main(monkeypatch, cmd) == 0


def test_git_commit_dash_m_message_not_blocked(monkeypatch):
    # git commit runs git, not pkill - the -m message text cannot self-match a pgrep/pkill call.
    assert run_main(monkeypatch, 'git commit -m "block pkill -f self-match footgun"') == 0


def test_real_pkill_after_commit_message_still_blocks(monkeypatch):
    # stripping the message must NOT hide a real pkill elsewhere in the command.
    assert run_main(monkeypatch, 'git commit -m "wip"; pkill -f nginx') == 2


def test_real_pkill_with_unrelated_heredoc_still_blocks(monkeypatch):
    cmd = "pkill -f nginx; cat <<'EOF'\nhello world\nEOF"
    assert run_main(monkeypatch, cmd) == 2


def test_empty_command_passes(monkeypatch):
    assert run_main(monkeypatch, "") == 0


def test_missing_tool_input_passes(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({})))
    assert B.main() == 0


def test_malformed_stdin_passes(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert B.main() == 0


@pytest.mark.skipif(sys.platform == "win32",
                    reason='bare "bash" on a Windows runner resolves to the WSL stub in System32, not Git Bash; this drives the bash shim directly')
def test_subprocess_block_via_shim():
    cmd = 'pkill -f "[m]yproc"; echo "myproc gone"'
    res = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": cmd}}),
        capture_output=True,
        text=True,
    )
    assert res.returncode == 2
    assert "BLOCKED" in res.stderr


# --- A trigger must be a whole shell TOKEN, not a substring. ----------------------------------
# Both halves fired together on a real command in this repo: a `for` loop naming the hook files
# matched "pgrep" inside the FILENAME block-pgrep-self-match, then matched "-f" inside the WORD
# detector-footguns and read the following word as its pattern. Neither text runs anything.

def test_a_program_name_inside_a_hyphenated_filename_is_not_an_invocation():
    assert B.plain_f_patterns("ls block-pgrep-self-match.py -f x") == []
    assert B.plain_f_patterns("cat pkill-notes.md -f x") == []


def test_a_real_invocation_is_still_found_however_it_is_spelled():
    """The direction where it must NOT apply: tightening the boundary must not lose a real call,
    including one given by absolute path, after a pipe, or inside an ssh argument."""
    assert B.plain_f_patterns("pgrep -f myserver") == ["myserver"]
    assert B.plain_f_patterns("/usr/bin/pgrep -f myserver") == ["myserver"]
    assert B.plain_f_patterns("ls | pkill -f myserver") == ["myserver"]
    assert B.plain_f_patterns("""ssh host 'pkill -f "iperf3 -s"'""") == ["iperf3 -s"]


def test_a_dash_f_inside_a_word_is_not_the_f_flag():
    """`-f` has to be its own token. Inside `detector-footguns` it is not, and reading the next
    word as the pattern invents an invocation out of two unrelated filenames. This is the exact
    command that fired: a shell loop naming the hook source files."""
    assert B.plain_f_patterns("for h in pgrep-self-match nudge-detector-footguns reformat-md-tables") == []


def test_the_f_flag_is_still_found_bundled_and_in_its_long_form():
    """The long form is a REAL self-matcher and is matched today, so the token-boundary fix must
    keep it. Requiring the flag to start at a token boundary is not the same as requiring a single
    leading dash - measured before the fix: `pkill --full x` already returned ["x"], and a naive
    `(?<![\\w-])-` guard would have silently dropped it."""
    assert B.plain_f_patterns("pgrep -af myserver") == ["myserver"]
    assert B.plain_f_patterns("pkill --full myserver") == ["myserver"]
    assert B.plain_f_patterns("pgrep --full myserver") == ["myserver"]


def test_a_bracket_pattern_belonging_to_another_command_is_not_a_leak():
    """`grep "[s]shd"` is grep's own search pattern. bracket_leaks scanned the whole command with
    no regard for whether a real -f invocation existed, so an unrelated bracket trick elsewhere on
    the line was reported as a pgrep self-match leak."""
    assert B.bracket_leaks('p' + 'grep -x sshd; grep "[s]shd" /var/log/auth.log') == []


def test_a_real_bracket_leak_is_still_reported():
    """The direction where it must NOT apply: the leak shape this guard exists for."""
    leaks = B.bracket_leaks('p' + 'grep -f "[n]ginx"; echo "=== nginx running? ==="')
    assert leaks


# ---- a mention is not an instance ---------------------------------------------------------------

def test_an_echo_of_the_footgun_does_not_block(monkeypatch):
    assert run_main(monkeypatch, "echo 'never run pkill -f \"iperf3 -s\"'") == 0


def test_a_real_invocation_after_an_echo_of_one_still_blocks(monkeypatch):
    assert run_main(monkeypatch, "echo 'do not' && ssh host 'pkill -f \"iperf3 -s\"'") == 2
