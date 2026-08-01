"""Tests for shell_text.py. ASCII only.

This module exists so the command-scanning guards agree about what counts as DATA. The cases below
are the corpus that proved the two former copies behaviourally identical before they were merged;
keeping them here is what stops the next edit from splitting the behaviour again.
"""
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
