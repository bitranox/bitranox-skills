"""Tests for pct-path-nudge.py - a hand-typed PATH inside `pct exec` that drops a standard dir.

`pct exec` hands the container a minimal PATH, so the fix is to set one - and the recurring miss is
setting a SHORTER one from memory. `/usr/local/bin:/usr/bin:/bin` runs uv and then fails on
runuser, postfix and postmap, which live in /usr/sbin. The nudge names what the typed value is
missing and gives the full line to copy.
"""
import json

import pytest

import pct_path_nudge as N

FULL = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def _n(cmd):
    return N.notice(cmd)


# --- fires on a short PATH inside pct exec -------------------------------------------------------

def test_env_path_without_usr_sbin_is_flagged():
    ctx = _n("pct exec 101 -- env PATH=/usr/local/bin:/usr/bin:/bin bash updrootvol.sh")
    assert ctx and "/usr/sbin" in ctx


def test_the_message_gives_the_full_path_to_copy():
    ctx = _n("pct exec 101 -- env PATH=/usr/local/bin:/usr/bin:/bin uv --version")
    assert FULL in ctx


def test_the_message_names_only_what_is_missing():
    ctx = _n("pct exec 101 -- env PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin uv run x.py")
    assert ctx and "missing: /usr/local/sbin" in ctx


def test_a_path_without_usr_local_bin_is_flagged():
    """The other direction of the same trap: uv lives in /usr/local/bin."""
    ctx = _n("pct exec 101 -- env PATH=/usr/sbin:/usr/bin:/sbin:/bin uv --version")
    assert ctx and "/usr/local/bin" in ctx


def test_an_export_inside_bash_c_is_flagged():
    assert _n("pct exec 101 -- bash -c 'export PATH=/usr/local/bin:/usr/bin:/bin; uv sync'")


def test_a_prefix_assignment_inside_bash_lc_is_flagged():
    assert _n('pct exec 101 -- bash -lc "PATH=/usr/local/bin:/usr/bin:/bin runuser -u x id"')


def test_a_quoted_value_is_flagged():
    assert _n("pct exec 101 -- env 'PATH=/usr/local/bin:/usr/bin:/bin' uv --version")


def test_pct_exec_inside_an_ssh_argument_is_flagged():
    """The usual shape from a dev box: the pct call travels inside ssh's quoted command."""
    cmd = "ssh -o BatchMode=yes root@node1 'pct exec 101 -- env PATH=/usr/local/bin:/usr/bin:/bin uv sync'"
    assert _n(cmd)


def test_pct_invoked_by_path_is_flagged():
    assert _n("/usr/sbin/pct exec 101 -- env PATH=/usr/bin:/bin uv sync")


def test_a_variable_vmid_is_flagged():
    assert _n('pct exec "$ct" -- env PATH=/usr/local/bin:/usr/bin:/bin uv sync')


def test_keep_env_before_the_separator_is_flagged():
    assert _n("pct exec 101 --keep-env 0 -- env PATH=/usr/bin:/bin uv sync")


# --- stays quiet otherwise -----------------------------------------------------------------------

def test_the_full_path_is_quiet():
    assert _n("pct exec 101 -- env PATH=%s bash updrootvol.sh" % FULL) is None


def test_the_full_path_in_another_order_is_quiet():
    """Order is not the defect; a dropped dir is."""
    assert _n("pct exec 101 -- env PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin uv") is None


def test_trailing_slashes_count_as_the_same_dir():
    val = "/usr/local/sbin/:/usr/local/bin/:/usr/sbin/:/usr/bin/:/sbin/:/bin/"
    assert _n("pct exec 101 -- env PATH=%s uv" % val) is None


def test_extending_the_inherited_path_is_quiet():
    """`$PATH` keeps the container's own dirs, so nothing standard is dropped."""
    assert _n("pct exec 101 -- bash -c 'PATH=/usr/local/bin:$PATH uv sync'") is None
    assert _n("pct exec 101 -- bash -c 'export PATH=/opt/x/bin:${PATH}; x'") is None


def test_pct_exec_without_any_path_is_quiet():
    """A bare pct exec of a /usr/bin tool is fine; only a hand-typed SHORT value is the trap."""
    assert _n("pct exec 101 -- systemctl is-active soundtouch") is None


def test_a_short_path_outside_pct_exec_is_quiet():
    assert _n("env PATH=/usr/bin:/bin make test") is None


def test_a_path_suffix_variable_is_not_path():
    assert _n("pct exec 101 -- env LD_LIBRARY_PATH=/opt/lib MYPATH=/x uv sync") is None


def test_a_word_ending_in_pct_is_not_the_command():
    assert _n("cmpct exec 101 -- env PATH=/usr/bin:/bin x") is None


# --- data regions: mentioning the pattern is not running it -------------------------------------

def test_a_sentence_about_the_trap_in_some_tool_argument_is_quiet():
    """No vmid and no `--`, so it is prose; measured as the one false hit over real transcripts."""
    cmd = 'tool.py add --what "a pct exec line with env PATH=/usr/local/bin:/usr/bin:/bin failed"'
    assert _n(cmd) is None


def test_an_echo_of_the_pattern_is_quiet():
    assert _n('echo "pct exec 101 -- env PATH=/usr/local/bin:/usr/bin:/bin uv"') is None


def test_a_commit_message_describing_the_pattern_is_quiet():
    cmd = 'git commit -m "warn on pct exec 101 -- env PATH=/usr/local/bin:/usr/bin:/bin"'
    assert _n(cmd) is None


def test_the_pattern_inside_a_heredoc_body_is_quiet():
    cmd = (
        "cat > notes.md <<'EOF'\n"
        "pct exec 101 -- env PATH=/usr/local/bin:/usr/bin:/bin uv sync\n"
        "EOF\n"
    )
    assert _n(cmd) is None


def test_a_real_call_after_an_echo_of_one_still_fires():
    cmd = 'echo "see notes"; pct exec 101 -- env PATH=/usr/bin:/bin uv sync'
    assert _n(cmd)


# --- the hook contract ---------------------------------------------------------------------------

def test_empty_and_garbage_never_raise():
    for cmd in (None, "", 42, [], "pct exec", "pct exec 101 -- env PATH="):
        N.notice(cmd)


def test_main_emits_additional_context_and_exits_zero(capsys):
    event = {"tool_name": "Bash",
             "tool_input": {"command": "pct exec 101 -- env PATH=/usr/bin:/bin uv sync"}}
    assert N.main(json.dumps(event)) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "/usr/sbin" in out["hookSpecificOutput"]["additionalContext"]
    assert "permissionDecision" not in out["hookSpecificOutput"]


def test_main_is_silent_for_a_clean_command(capsys):
    event = {"tool_name": "Bash", "tool_input": {"command": "pct exec 101 -- env PATH=%s uv" % FULL}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out == ""


def test_main_ignores_other_tools(capsys):
    event = {"tool_name": "Write",
             "tool_input": {"command": "pct exec 101 -- env PATH=/usr/bin:/bin uv sync"}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("raw", ["", "{", "null", "[]", '{"tool_name": "Bash"}',
                                 '{"tool_name": "Bash", "tool_input": "x"}'])
def test_main_never_wedges_on_malformed_input(raw, capsys):
    assert N.main(raw) == 0
    assert capsys.readouterr().out == ""
