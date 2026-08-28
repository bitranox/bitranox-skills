"""Tests for shell_text.py. ASCII only.

This module exists so the command-scanning guards agree about what counts as DATA. The cases below
are the corpus that proved the two former copies behaviourally identical before they were merged;
keeping them here is what stops the next edit from splitting the behaviour again.
"""
import subprocess
import pytest
import shell_text as S


# ---- the point of the module: a body is data, not a command ------------------------------------

def test_body_is_dropped_and_surrounding_commands_are_kept():
    out = S.strip_heredoc_bodies("cat <<EOF\nbody line\nEOF\necho after")
    assert "body line" not in out
    assert "cat <<EOF" in out and "echo after" in out


def test_the_opener_line_is_kept_because_it_is_a_real_command():
    """`cat <<EOF > file.txt` still redirects and `cmd <<EOF | grep x` still pipes."""
    assert "> file.txt" in S.strip_heredoc_bodies("cat <<EOF > file.txt\nbody\nEOF")
    assert "| grep x" in S.strip_heredoc_bodies("cmd <<EOF | grep x\nbody\nEOF")


def test_terminator_line_itself_is_dropped():
    assert S.strip_heredoc_bodies("cat <<EOF\nb\nEOF").strip() == "cat <<EOF"


# ---- opener forms bash accepts -----------------------------------------------------------------

def test_quoted_and_dash_and_spaced_openers():
    for opener in ("<<EOF", "<<'EOF'", '<<"EOF"', "<<-EOF", "<< EOF"):
        text = "cat %s\nSECRETBODY\nEOF\necho after" % opener
        out = S.strip_heredoc_bodies(text)
        assert "SECRETBODY" not in out, opener
        assert "echo after" in out, opener


def test_dash_form_allows_an_indented_terminator():
    out = S.strip_heredoc_bodies("cat <<-EOF\n\tindented\n\tEOF\necho after")
    assert "indented" not in out and "echo after" in out


def test_underscore_delimiters_are_recognised():
    out = S.strip_heredoc_bodies("cat <<_MARK_\nbody\n_MARK_\necho after")
    assert "body" not in out and "echo after" in out


def test_a_delimiter_may_not_start_with_a_digit():
    """`<<9X` is not a valid delimiter, so nothing is stripped and the text stays a command."""
    text = "cat <<9INVALID\nbody\n9INVALID"
    assert S.strip_heredoc_bodies(text) == text


# ---- multiple and unterminated -----------------------------------------------------------------

def test_two_heredocs_in_one_command():
    out = S.strip_heredoc_bodies("cat <<A\nfirst\nA\ncat <<B\nsecond\nB\ndone")
    assert "first" not in out and "second" not in out
    assert "done" in out


def test_the_same_delimiter_reused_does_not_swallow_the_second_command():
    out = S.strip_heredoc_bodies("cat <<E\na\nE\ncat <<E\nb\nE\necho after")
    assert "a" not in out.split("\n")[1:] and "echo after" in out


def test_an_unterminated_heredoc_consumes_the_rest():
    """The safe direction: the shell would treat those lines as data too."""
    out = S.strip_heredoc_bodies("cat <<EOF\nbody\nmore body")
    assert out.strip() == "cat <<EOF"


def test_a_lowercase_terminator_does_not_close_an_uppercase_delimiter():
    out = S.strip_heredoc_bodies("cat <<EOF\nbody\neof")
    assert "body" not in out and "eof" not in out


# ---- inputs that must pass through untouched ---------------------------------------------------

def test_commands_without_a_heredoc_are_unchanged():
    for text in ("", "echo hello", "git status\ngit log", "multi\nline\nno heredoc", "\n\n\n"):
        assert S.strip_heredoc_bodies(text) == text, text


def test_a_quoted_mention_is_not_an_opener():
    """A guard documenting the syntax must not be mangled by the stripper itself."""
    text = "echo '<<NOTAHEREDOC'"
    assert S.strip_heredoc_bodies(text) == text


# ---- the guards must share ONE implementation --------------------------------------------------

def test_both_guards_use_this_exact_function():
    """Re-exported, not re-implemented: a second copy is how the behaviour split last time."""
    import git_footgun_guard as G
    import shell_prefix_selfref_guard as P
    assert G.strip_heredoc_bodies is S.strip_heredoc_bodies
    assert P.strip_heredoc_bodies is S.strip_heredoc_bodies


# --- mask_data_regions ----------------------------------------------------------------------------


def test_mask_consumes_the_quote_characters_too():
    """Keeping the quotes leaves `"$MAIN"` as two bare `"` tokens, which loses the subcommand."""
    masked = S.mask_data_regions('git -C "$MAIN" commit')
    assert masked.split() == ["git", "-C", "QQQQQQQ", "commit"]


def test_mask_preserves_length():
    for command in ['git commit -m "a; b"', "echo 'x' ; ls", "n=$((1+2))", "echo ${FOO}", "a `b` c"]:
        assert len(S.mask_data_regions(command)) == len(command)


def test_mask_hides_a_semicolon_inside_a_double_quoted_message():
    assert ";" not in S.mask_data_regions('git commit -m "wip; git push"')


def test_mask_hides_a_newline_inside_a_quoted_message():
    assert "\n" not in S.mask_data_regions("git commit -m 'line one\nline two'")


def test_mask_handles_nested_command_substitution():
    masked = S.mask_data_regions("x=$(echo $(date)) ; ls")
    assert masked.endswith(" ; ls")
    assert "(" not in masked and ")" not in masked


def test_mask_handles_arithmetic_expansion():
    masked = S.mask_data_regions("n=$((1+2)) ; ls")
    assert "(" not in masked and ")" not in masked


def test_mask_leaves_parameter_expansion_as_one_token():
    masked = S.mask_data_regions("echo ${FOO} ; ls")
    assert "{" not in masked and "}" not in masked


def test_mask_turns_a_backslash_newline_into_whitespace():
    """A line continuation must not become filler, or the tokens it joins fuse into one word."""
    assert S.mask_data_regions("git -c a=b \\\ncommit").split() == ["git", "-c", "a=b", "commit"]


def test_mask_blanks_comments():
    assert ";" not in S.mask_data_regions("git commit -m x  # ; git push")


def test_mask_survives_an_unterminated_quote():
    assert len(S.mask_data_regions('git commit -m "oops')) == len('git commit -m "oops')


def test_blank_unexpanded_text_still_leaves_double_quotes_alone():
    """The two functions answer different questions and must keep treating quotes differently."""
    assert "$?" in S.blank_unexpanded_text('echo "rc=$?"')
    assert "$?" not in S.mask_data_regions('echo "rc=$?"')


# --------------------------------------------------------------------------
# split_for_tool: a Bash|PowerShell matcher delivers command strings in two
# different languages, and the TOOL decides which, never the host OS.
# --------------------------------------------------------------------------

WIN_PATH = r"C:\Users\me\msg.txt"


def test_split_for_tool_keeps_a_windows_path_whole_for_powershell():
    """In PowerShell a backslash is a PATH SEPARATOR, so eating it destroys the argument.

    A guard that then resolves the token - opens it, stats it, runs it - gets nothing back and
    fails open, which is a guard approving exactly what it exists to block.
    """
    assert S.split_for_tool("git commit -F " + WIN_PATH, "PowerShell")[-1] == WIN_PATH


def test_split_for_tool_matches_bash_itself_for_the_bash_tool():
    """Not a bug on this arm, and the reason the split must be keyed rather than made uniform.

    Real bash gives `C:Usersmemsg.txt` for that same unquoted string - verified against bash - so
    shlex is not merely acceptable here, it is what the tool actually does. Applying the Windows
    rules to a Bash command would be a NEW defect on a Windows host.
    """
    assert S.split_for_tool("git commit -F " + WIN_PATH, "Bash")[-1] == "C:Usersmemsg.txt"


def test_split_for_tool_defaults_to_bash_for_an_unknown_tool():
    assert S.split_for_tool("git commit -F " + WIN_PATH)[-1] == "C:Usersmemsg.txt"


@pytest.mark.parametrize("command,expected", [
    (r'a "b c"', ["a", "b c"]),                        # quotes group
    (r'a "b\"c"', ["a", 'b"c']),                       # 2n+1 backslashes -> literal quote
    (r'a "b\\" c', ["a", "b\\", "c"]),                 # 2n backslashes -> n, quote still toggles
    (r'a C:\dir\file.txt', ["a", r"C:\dir\file.txt"]), # a run with no quote after it is literal
    ("", []),                                          # must not become the interpreter path
])
def test_split_for_tool_follows_the_documented_backslash_rules(command, expected):
    """The CRT rules are only surprising around quotes; a plain path must pass through untouched."""
    assert S.split_for_tool(command, "PowerShell") == expected


_B = chr(92)   # kept out of the literals below so this file needs no escaping puzzles


@pytest.mark.parametrize("argv", [
    ["git", "commit", "-F", "C:" + _B + "Users" + _B + "me" + _B + "msg.txt"],
    ["a", "C:" + _B + "dir" + _B + " "],          # a space inside a quoted path
    ["x", 'b"c'],                                  # an embedded quote
    ["p", "C:" + _B + "a b" + _B + "c.txt"],
    ["q", ""],                                     # an empty argument must survive
    ["tool", _B + _B + "server" + _B + "share" + _B + "f.txt"],   # UNC
    ["n", "trailing" + _B],                        # a run with nothing after it
])
def test_split_for_tool_inverts_list2cmdline(argv):
    """The property, rather than cases I happened to think of.

    `subprocess.list2cmdline` is the stdlib's own Windows command-line BUILDER, quoting to the
    same C-runtime rules this splitter reads. Requiring the two to be inverses covers the shapes
    a hand-written case list reliably misses - UNC prefixes, a trailing backslash run, an empty
    argument - and it fails if either side drifts.
    """
    assert S.split_for_tool(subprocess.list2cmdline(argv), "PowerShell") == argv


@pytest.mark.parametrize("token,tool,expected", [
    ("/usr/bin/sed", "Bash", "sed"),
    ("sed", "Bash", "sed"),
    ("C:" + _B + "tools" + _B + "sed.exe", "PowerShell", "sed"),
    ("C:" + _B + "tools" + _B + "sed", "PowerShell", "sed"),
    ("sed.exe", "PowerShell", "sed"),
    # The Bash arm must NOT learn Windows separators: bash would have eaten them, so a token
    # still carrying one is one long filename and calling it "sed" would invent a match.
    ("C:" + _B + "tools" + _B + "sed", "Bash", "C:" + _B + "tools" + _B + "sed"),
])
def test_basename_for_tool_uses_the_tool_s_separator_rules(token, tool, expected):
    """A guard asking "is this command sed?" must strip the path, and which characters separate a
    path is the TOOL's question. `.exe` goes on the PowerShell arm because a Windows program is
    spelled with it while every command allowlist in this plugin is spelled without."""
    assert S.basename_for_tool(token, tool) == expected


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_basename_for_tool_strips_exe_on_both_arms(tool):
    """Git Bash on Windows runs `sed.exe`, so the Bash arm needs this exactly as much.

    The earlier PowerShell-only stripping was justified by separator handling, which has nothing
    to do with it: `.exe` is about how a program is NAMED, and every command allowlist in this
    plugin is spelled without it. The asymmetry left `sed.exe -i config.json` unblocked under the
    tool that carries nearly all the traffic.
    """
    assert S.basename_for_tool("sed.exe", tool) == "sed"
    assert S.basename_for_tool("SED.EXE", tool) == "SED"


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_basename_for_tool_leaves_a_non_exe_suffix_alone(tool):
    """Only `.exe` goes. A dot in a program name is otherwise part of the name."""
    assert S.basename_for_tool("my.tool", tool) == "my.tool"
    assert S.basename_for_tool("sed.executable", tool) == "sed.executable"
