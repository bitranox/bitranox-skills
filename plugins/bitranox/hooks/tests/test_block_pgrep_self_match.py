"""Tests for block-pgrep-self-match.py (PreToolUse(Bash|PowerShell) bracket-trick guard).

Contract: reads a PreToolUse event JSON on stdin. Exit 2 (with stderr) blocks when a
pgrep/pkill call carrying -f/--full either has a plain-literal pattern, or has a
bracket-trick pattern [X]rest whose de-bracketed literal Xrest appears contiguously
elsewhere in the same command. Every other path exits 0.

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
    # A heredoc body is stdin data that runs nothing, so no pgrep/pkill call is made from it.
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



# --- finding 4 from the 2026-08-28 script-wave audit of this hook -------------------------------

def test_an_empty_dash_f_pattern_is_blocked(monkeypatch, capsys):
    """The empty pattern matches EVERY command line, so it is the worst self-match there is: it
    matches the shell running it, and with pkill it kills that shell along with everything else the
    user owns. It was the one pattern the loop explicitly skipped."""
    assert run_main(monkeypatch, 'pkill -f ""') == 2
    err = capsys.readouterr().err
    assert "EVERY process" in err


def test_plain_f_patterns_reports_the_empty_pattern():
    assert B.plain_f_patterns('pkill -f ""') == [""]
    assert B.plain_f_patterns("pkill -f ''") == [""]


def test_a_dash_f_with_no_pattern_at_all_is_not_blocked(monkeypatch):
    """The direction the fix must NOT reach. `-f` with nothing after it is a malformed command,
    not a footgun, and the guard has no pattern to reason about - skipping an UNPARSEABLE call is
    right, which is why the old empty-skip looked correct."""
    assert run_main(monkeypatch, "pgrep -f") == 0


def test_the_bracket_form_still_passes(monkeypatch):
    """The case this guard was built to allow, kept beside the widening."""
    assert run_main(monkeypatch, 'pgrep -f "[n]ginx"') == 0


# --- rank 10 readjudication, 2026-09-26 ----------------------------------------------------------

def run_bash(monkeypatch, command):
    """Drive main() with the event shape production sends, tool_name included."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    return B.main()


def test_a_substitution_inside_a_commit_message_still_blocks(monkeypatch):
    """`$(...)` inside a double-quoted message RUNS, so the pgrep in it is a real call. Rewriting
    every `-m "<text>"` to `-m X` erased it before anything looked."""
    assert run_bash(monkeypatch, 'git commit -m "$(pgrep -f nginx | wc -l) still up"') == 2
    assert run_bash(monkeypatch, 'git commit -m "`pgrep -f nginx | wc -l` still up"') == 2


def test_a_plain_commit_message_mentioning_the_footgun_still_passes(monkeypatch):
    """The direction the fix must not reach: message TEXT is stored, never run. The `git -C <dir>`
    spelling is the reason the message rewrite is narrowed rather than dropped - the shared sink
    stripper stops at the `-C` value and does not see that statement as a commit."""
    assert run_bash(monkeypatch, 'git commit -m "pgrep -f nginx is a footgun"') == 0
    assert run_bash(monkeypatch, 'git -C /repo commit -m "pkill -f nginx is a footgun"') == 0


def test_a_heredoc_body_line_starting_with_the_tag_does_not_end_the_body(monkeypatch):
    """bash ends a heredoc only at a line that IS the delimiter. `EOF is ...` is body text, so the
    `pkill -f` line after it is still data."""
    cmd = ("cat > NOTES.md <<'EOF'\nWhy not to use it:\nEOF is only a terminator at column 0\n"
           "pkill -f nginx  <- never do this\nEOF")
    assert run_bash(monkeypatch, cmd) == 0


def test_a_real_call_after_a_heredoc_still_blocks(monkeypatch):
    assert run_bash(monkeypatch, "cat > NOTES.md <<'EOF'\nhello\nEOF\npkill -f nginx") == 2


def test_a_bracket_pattern_without_dash_f_is_not_a_leak(monkeypatch):
    """Without -f, pgrep matches comm (the program name), so an echo label naming the process cannot
    make it match the shell. This is the form the remedy text itself recommends."""
    assert run_bash(monkeypatch, 'pgrep -x "[s]shd"; echo "sshd up?"') == 0
    assert run_bash(monkeypatch, 'pgrep "[s]shd"; echo "sshd up?"') == 0


def test_a_bracket_leak_with_dash_f_or_full_still_blocks(monkeypatch):
    assert run_bash(monkeypatch, 'pgrep -f "[s]shd"; echo "=== sshd running? ==="') == 2
    assert run_bash(monkeypatch, 'pgrep --full "[s]shd"; echo "=== sshd running? ==="') == 2


def test_a_commented_out_call_is_not_an_invocation(monkeypatch):
    """A `#` comment is never executed, so a pkill named in one is not a call."""
    assert run_bash(monkeypatch, "# pkill -f nginx  <- never do this\nsystemctl stop nginx") == 0


def test_a_real_call_with_a_trailing_comment_still_blocks(monkeypatch):
    assert run_bash(monkeypatch, "pkill -f nginx  # stop it") == 2


def test_a_comment_still_counts_as_a_bracket_leak(monkeypatch):
    """The comment is blanked only where CALLS are read. It is still part of the shell's own
    command line, so its literal still defeats the bracket trick."""
    assert run_bash(monkeypatch, 'pgrep -f "[n]ginx"  # is nginx up') == 2


def test_a_grep_pattern_naming_the_footgun_is_still_blocked(monkeypatch):
    """Pinned choice: a quoted argument to grep still reads as a call. Whether an argument is inert
    is decided by ONE allowlist in shell_text (strip_data_sink_statements), and grep is not on it;
    a second, hook-local list would drift from it. The false positive is visible and has a cheap
    way round, which the second assertion pins: bracketing the grep pattern."""
    assert run_bash(monkeypatch, 'grep -rn "pkill -f nginx" hooks/') == 2
    assert run_bash(monkeypatch, 'grep -rn "[p]kill -f nginx" hooks/') == 0


def test_a_pidfile_option_is_not_the_f_flag(monkeypatch):
    """--pidfile and --logpidfile read PIDs from a file and match no command line, which is the
    kind of signal the remedy text recommends. Any long option containing an `f` was read as -f."""
    assert run_bash(monkeypatch, "pkill --pidfile /run/nginx.pid") == 0
    assert run_bash(monkeypatch, "pgrep --logpidfile /run/x.log -F /run/nginx.pid") == 0


def test_the_full_long_form_and_bundled_short_form_still_block(monkeypatch):
    assert run_bash(monkeypatch, "pkill --full nginx") == 2
    assert run_bash(monkeypatch, "pkill -af nginx") == 2


def test_a_heredoc_body_counts_as_a_bracket_leak(monkeypatch):
    """A heredoc body is part of the command string the shell was started with, so it IS in the
    shell's own /proc/<pid>/cmdline and its literal defeats the bracket trick exactly as an echo
    label does. Measured on this host: `pgrep -f "[M]ARKER"` followed by a heredoc whose body holds
    MARKER printed the shell's own PID; without the body it printed nothing."""
    cmd = "pgrep -f \"[n]ginx\"; cat <<'EOF' > notes.txt\nnginx config\nEOF"
    assert run_bash(monkeypatch, cmd) == 2


def test_a_commit_message_counts_as_a_bracket_leak(monkeypatch):
    assert run_bash(monkeypatch, 'pgrep -f "[n]ginx"; git commit -m "nginx restart"') == 2


def test_a_heredoc_without_the_literal_leaves_the_bracket_trick_intact(monkeypatch):
    cmd = "pgrep -f \"[n]ginx\"; cat <<'EOF' > notes.txt\nhello\nEOF"
    assert run_bash(monkeypatch, cmd) == 0
