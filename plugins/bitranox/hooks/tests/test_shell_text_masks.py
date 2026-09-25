"""The data-region masks and the heredoc opener, read the way each shell reads them. ASCII only.

Three shapes made a mask or the opener disagree with the shell, and each one hides a later
command from a guard or blocks a command that is fine:

- `mask_data_regions` read `\\` as an escape under every tool, but under PowerShell a backslash
  is a path separator, so `cd C:\\; git commit` masked the `;` and the second statement vanished;
- `blank_unexpanded_text` saw a blank after an escaped pair and opened a comment at `a\\ #b`,
  which bash reads as one word, blanking the rest of the line;
- a `<<` inside arithmetic (`(( x << y ))`, `$((1 << n))`) read as a heredoc opener, so every
  later line up to one spelling the "delimiter" was dropped as a body.

Every case is paired with a control for the direction the fix must NOT change.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import block_git_semicolon_chain
import block_masked_gate_exit
import block_sed_structured_files
import git_path_not_here_nudge
import git_wrong_repo_nudge
import jig_repetition_nudge
import shell_prefix_selfref_guard
import shell_text as S
import tooling_detour_nudge

HOOKS = Path(__file__).resolve().parent.parent
_B = "\\"


def _guard(name, command, tmp_path, tool_name="Bash"):
    event = {"tool_name": tool_name, "tool_input": {"command": command},
             "cwd": str(tmp_path), "session_id": "mask-test"}
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path)}
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run([sys.executable, str(HOOKS / (name + ".py"))],
                            input=json.dumps(event), capture_output=True, text=True,
                            encoding="utf-8", errors="replace", cwd=str(tmp_path), env=env,
                            timeout=60)
    return result.returncode


# ---- mask_data_regions follows the tool's escape character -----------------------------------

_PS_CD = "cd C:" + _B + "; git commit -m x"


def test_a_powershell_backslash_is_a_path_separator_not_an_escape():
    masked = S.mask_data_regions(_PS_CD, tool_name="PowerShell")
    assert masked == _PS_CD                       # nothing to mask: the `;` stays a separator


def test_a_quoted_powershell_path_ending_in_a_backslash_closes_its_quote():
    command = 'dir "C:' + _B + 'temp' + _B + '"; git commit -m x'
    assert S.mask_data_regions(command, tool_name="PowerShell").endswith('; git commit -m x')


def test_a_powershell_backtick_escapes():
    command = "echo a`; git commit"
    masked = S.mask_data_regions(command, tool_name="PowerShell")
    assert masked == "echo aQQ git commit"


def test_control_bash_still_escapes_with_a_backslash():
    assert S.mask_data_regions(_PS_CD) == "cd C:QQ git commit -m x"
    assert S.mask_data_regions(_PS_CD, tool_name="Bash") == "cd C:QQ git commit -m x"
    command = 'echo "a' + _B + '"b"; git push'
    assert S.mask_data_regions(command).endswith("; git push")


def test_control_bash_backticks_are_still_a_substitution():
    assert S.mask_data_regions("echo `date`; git push") == "echo QQQQQQ; git push"


def test_the_mask_preserves_length_under_every_tool():
    for tool in ("Bash", "PowerShell", None):
        for command in (_PS_CD, "echo a`; b", 'x "C:' + _B + '"; y', "a `b` c"):
            assert len(S.mask_data_regions(command, tool_name=tool)) == len(command)


def test_the_powershell_guards_split_a_backslash_path_statement(tmp_path):
    sed = "cd C:" + _B + "; sed -i s/a/b/ config.json"
    assert _guard("block-sed-structured-files", sed, tmp_path, "PowerShell") == 2
    # Control: under Bash `\;` is an escaped semicolon, so no second statement runs sed.
    assert _guard("block-sed-structured-files", sed, tmp_path, "Bash") == 0


def test_every_powershell_mask_caller_passes_the_tool_through():
    """A private default of "Bash" anywhere down the chain restores the miss, so each caller is
    asked the PowerShell question directly."""
    ps = "cd C:" + _B + "; sed -i s/a/b/ config.json"
    assert block_sed_structured_files.assess(ps, "PowerShell")[0] == "block"
    masked, spans = git_path_not_here_nudge._statements(ps, "PowerShell")
    assert len(spans) == 2
    masked, spans = git_wrong_repo_nudge._statements(ps, "PowerShell")
    assert len(spans) == 2
    assert len(shell_prefix_selfref_guard._statements(ps, "PowerShell")) == 2
    target = 'echo "C:' + _B + '" > out.py'
    assert tooling_detour_nudge._redirect_targets(target, "PowerShell") == ["out.py"]
    assert tooling_detour_nudge._redirect_targets(target, "Bash") == []
    piped = 'dir "C:' + _B + '" | make test | tail'
    assert block_masked_gate_exit.masks_a_gate(piped, "PowerShell") is True
    assert block_masked_gate_exit.masks_a_gate(piped, "Bash") is False
    chain = "echo C:" + _B + "; git commit -m x ; git push"
    assert block_git_semicolon_chain.chained_state_changes(chain, "PowerShell") == ["commit", "push"]
    assert block_git_semicolon_chain.chained_state_changes(chain, "Bash") is None


def test_a_hash_after_a_continuation_is_mid_word_in_the_mask_too():
    assert S.mask_data_regions("echo a" + _B + "\n#b; git push").endswith("#b; git push")
    assert S.mask_data_regions("echo a " + _B + "\n#b; git push").strip() == "echo a"


# ---- blank_unexpanded_text: an escaped blank does not end the word -----------------------------

def test_a_hash_after_an_escaped_space_is_not_a_comment():
    command = "echo a" + _B + ' #b; git commit -m "$(date)"'
    assert S.blank_unexpanded_text(command).endswith('; git commit -m "$(date)"')


def test_control_a_hash_after_a_real_space_is_a_comment():
    command = 'echo a #b; git commit -m "$(date)"'
    assert S.blank_unexpanded_text(command).strip() == "echo a"


def test_a_hash_after_a_continuation_follows_the_character_before_the_backslash():
    """`\\<newline>` is deleted before words are split: after `a \\<nl>` the `#` starts a word,
    after `a\\<nl>` it is mid-word."""
    assert "#b" not in S.blank_unexpanded_text("echo a " + _B + "\n#b")
    assert S.blank_unexpanded_text("echo a" + _B + "\n#b").endswith("#b")


def test_an_escaped_hash_no_longer_disarms_the_text_arg_guard(tmp_path):
    command = "echo a" + _B + ' #b; git commit -m "$(date)"'
    assert _guard("shell-prefix-selfref-guard", command, tmp_path) == 2
    assert _guard("shell-prefix-selfref-guard", 'echo a #b; git commit -m "$(date)"',
                  tmp_path) == 0


# ---- a shift inside arithmetic opens no heredoc ------------------------------------------------

@pytest.mark.parametrize("line", [
    "(( z = x << y ))",
    "echo $((x << y))",
    "for (( i = 0; i < 4; i = i << n )); do :; done",
    "(( (a + b) << c ))",
])
def test_an_arithmetic_shift_is_not_a_heredoc_opener(line):
    assert S.find_heredoc_opener(line) is None


@pytest.mark.parametrize("line,delimiter", [
    ("cat <<EOF", "EOF"),
    ("cat << 'EOF' > f.txt", "EOF"),
    ("(( n = 1 )); cat <<EOF", "EOF"),
    ('echo "<<X" && cat <<EOF', "EOF"),        # a quoted mention before the real opener
    ("x=$((1 << n)); cat > run.sh <<'EOS'", "EOS"),
])
def test_control_a_real_opener_is_still_found(line, delimiter):
    opener = S.find_heredoc_opener(line)
    assert opener is not None and opener.group(2) == delimiter


def test_an_arithmetic_shift_keeps_every_later_line():
    command = "(( z = x << y ))\ngit push origin main\ny"
    assert S.strip_heredoc_bodies(command) == command
    assert S.is_gated_command(command) is True


def test_control_a_real_heredoc_after_arithmetic_is_still_stripped():
    command = "(( n = 1 << 2 ))\ncat <<EOF\ngit push origin main\nEOF"
    assert "git push" not in S.strip_heredoc_bodies(command)


def test_a_heredoc_mentioned_inside_a_multi_line_string_opens_nothing():
    """Found by the corpus replay: read line by line, `\\"cat <<EOF\\"` on the second line of a
    `python3 -c "..."` string looked unquoted, and every later line became a body."""
    command = ('python3 -c "\nprint(' + "'a <<X', " + _B + '"b <<EOF' + _B + '")\n"\n'
               "git push origin main")
    assert S.strip_heredoc_bodies(command) == command
    assert S.is_gated_command(command) is True


def test_an_apostrophe_in_a_body_does_not_hide_the_next_heredoc():
    command = "cat <<'A'\ndon't\nA\ncat <<B\ngit push origin main\nB\necho done"
    assert S.strip_heredoc_bodies(command) == "cat <<'A'\ncat <<B\necho done"
    assert [body for _at, _op, body in S.iter_heredocs(command)] == [(1, 2), (4, 5)]


def test_a_quoted_mention_before_a_real_heredoc_no_longer_leaves_the_body_in():
    command = 'echo "<<X" && cat <<EOF\ngit push origin main\nEOF'
    assert "git push" not in S.strip_heredoc_bodies(command)


@pytest.mark.parametrize("hook,command", [
    ("block-sed-structured-files", "(( z = x << y ))\nsed -i s/a/b/ config.json"),
    ("git-footgun-guard", "(( z = x << y ))\ngit rev-parse --short A B"),
])
def test_an_arithmetic_shift_no_longer_hides_the_next_line_from_a_guard(hook, command, tmp_path):
    assert _guard(hook, command, tmp_path) == 2


def test_an_arithmetic_shift_no_longer_reads_as_a_bare_heredoc_to_the_selfref_guard(tmp_path):
    command = '(( z = x << y ))\necho "$(date)"\ny'
    assert _guard("shell-prefix-selfref-guard", command, tmp_path) == 0
    assert _guard("shell-prefix-selfref-guard", 'cat <<EOF\n$(date)\nEOF', tmp_path) == 2


def test_the_jig_nudge_finds_the_script_heredoc_after_an_arithmetic_shift():
    command = "x=$((1 << n)); cat > run.sh <<'EOS'\necho hi\nEOS"
    assert jig_repetition_nudge.heredoc_writes(command) == [("run.sh", "echo hi")]
