"""The offset-preserving heredoc blank and its commands_only twin. ASCII only.

`strip_heredoc_bodies` DELETES body lines, so an offset found on its output points somewhere else
in the raw command. A guard that finds a verb on the stripped text and then slices the RAW command
at that offset reads the wrong characters, silently. `blank_heredoc_bodies` blanks the same lines
to spaces instead, so every offset found on it is an offset into the raw command, and
`commands_only_aligned` is the same guarantee for the stripped-and-masked reading.

The invariants are asserted over one list of tricky commands, so a new shape added to the list is
checked by every property at once.
"""
import re

import pytest

import shell_text as S

_B = "\\"

# Each shape named in the contract, plus the ones that have broken a heredoc reader before.
TRICKY = [
    "",
    "git push",
    "cat <<EOF > notes.md\nbody with 'apostrophe\nEOF\ngit push",
    "cat <<EOF > notes.md\r\nbody line\r\nEOF\r\ngit push\r\n",                    # CRLF
    "cat <<-EOF > f\n\tindented body; git push\n\tEOF\ngit commit -m x",          # <<- tab strip
    "cat <<A > a; cat <<B > b\nfirst body\nA\nsecond body\nB\ngit push",           # two on one line
    "cat <<ONE > one\nbody one\nONE\ncat <<TWO > two\nbody two\nTWO\ngit push",   # two in sequence
    "git status\ncat <<EOF > f\nlast body with no terminator",                     # unterminated
    "git status\ncat <<EOF > f\nbody\nEOF",                                        # terminator last, no newline
    "cat <<EOF",                                                                   # opener on the last line
    "cat <<'EOF' > f\n$(not run) `nor this` \"quote\nEOF\ngit push",               # quoted delimiter
    'cat <<"END-X" > f\nbody\nEND-X\ngit push',                                     # double-quoted word
    "cat <<" + _B + "EOF > f\nbody\nEOF\ngit push",                                # backslash-quoted
    'git commit -m "$(cat <<\'EOF\'\nsubject (with parens\n\nbody\nEOF\n)" && git push',
    "echo 'a << b' && git push",                                                   # << in single quotes
    'echo "docs: explain <<EOF heredocs" && git push',                             # << in double quotes
    "echo $(( 1 << 2 ))\ngit push",                                                # arithmetic shift
    "(( z = x << y ))\ngit push\ny",                                               # bare arithmetic
    "git status # see <<EOF later\ngit push\nEOF",                                 # << in a comment
    "cat <<< 'here string'\ngit push",                                             # here-string
    "python3 - <<'PY'\nimport re\nprint('git push')\nPY\ngit -C /repo commit -F msg",
]

# Inputs where no heredoc opens: the blank must return them unchanged.
NOT_A_HEREDOC = [
    "",
    "git push",
    "echo 'a << b' && git push",
    'echo "docs: explain <<EOF heredocs" && git push',
    "echo $(( 1 << 2 ))\ngit push",
    "(( z = x << y ))\ngit push\ny",
    "git status # see <<EOF later\ngit push\nEOF",
    "cat <<< 'here string'\ngit push",
    "cat <<EOF",
]

# Patterns confined to one line, the shape a guard uses to find a verb or an operator.
PATTERNS = [
    re.compile(r"\bgit[^\S\n]+(?:-C[^\S\n]+\S+[^\S\n]+)?\w+"),
    re.compile(r"<<-?[^\S\n]*\S+"),
    re.compile(r"&&|\|\||[;|&]"),
    re.compile(r"\S+"),
]


def _body_lines(command):
    """Indices, in command.split('\\n'), of every line strip_heredoc_bodies drops."""
    lines = command.split("\n")
    dropped = set()
    for _at, _opener, (start, end) in S.iter_heredocs(command):
        dropped.update(range(start, min(end + 1, len(lines))))
    return dropped


def _kept_line_starts(command):
    """(stripped offset, raw offset) of every kept line, in order."""
    dropped = _body_lines(command)
    pairs, raw, stripped = [], 0, 0
    for index, line in enumerate(command.split("\n")):
        if index not in dropped:
            pairs.append((stripped, raw))
            stripped += len(line) + 1
        raw += len(line) + 1
    return pairs


def _raw_offset(command, stripped_offset):
    """Map an offset on strip_heredoc_bodies(command) to the same character in the raw command."""
    best = (0, 0)
    for pair in _kept_line_starts(command):
        if pair[0] <= stripped_offset:
            best = pair
    return best[1] + (stripped_offset - best[0])


def _drop_body_lines(aligned, command):
    """`aligned` (same length as `command`) with the raw body lines cut out the way
    strip_heredoc_bodies cuts them: kept lines joined by the character after each one."""
    dropped = _body_lines(command)
    pieces, raw = [], 0
    lines = command.split("\n")
    for index, line in enumerate(lines):
        if index not in dropped:
            pieces.append((aligned[raw:raw + len(line)], aligned[raw + len(line):raw + len(line) + 1]))
        raw += len(line) + 1
    out = []
    for position, (text, separator) in enumerate(pieces):
        out.append(text)
        if position < len(pieces) - 1:
            out.append(separator)
    return "".join(out)


@pytest.mark.parametrize("command", TRICKY)
def test_blank_heredoc_bodies_preserves_length(command):
    assert len(S.blank_heredoc_bodies(command)) == len(command)


@pytest.mark.parametrize("command", TRICKY)
def test_blank_heredoc_bodies_keeps_every_newline_and_blanks_only_bodies(command):
    blanked = S.blank_heredoc_bodies(command)
    dropped = _body_lines(command)
    for index, (raw_line, out_line) in enumerate(zip(command.split("\n"), blanked.split("\n"))):
        if index in dropped:
            assert out_line == " " * len(raw_line)
        else:
            assert out_line == raw_line                   # byte-identical outside the bodies
    assert [i for i, c in enumerate(blanked) if c == "\n"] == [i for i, c in enumerate(command) if c == "\n"]


@pytest.mark.parametrize("command", TRICKY)
def test_removing_the_blanked_lines_gives_exactly_strip_heredoc_bodies(command):
    """Detection is identical: the lines blanked are exactly the lines stripped."""
    assert _drop_body_lines(S.blank_heredoc_bodies(command), command) == S.strip_heredoc_bodies(command)


@pytest.mark.parametrize("command", NOT_A_HEREDOC)
def test_a_double_angle_that_opens_no_heredoc_is_left_untouched(command):
    assert S.blank_heredoc_bodies(command) == command


def test_none_reads_as_empty():
    assert S.blank_heredoc_bodies(None) == ""
    assert S.commands_only_aligned(None) == ""


@pytest.mark.parametrize("command", TRICKY)
@pytest.mark.parametrize("pattern", PATTERNS, ids=lambda p: p.pattern)
def test_every_match_on_the_stripped_text_is_found_at_the_raw_offset_on_the_blanked_text(command, pattern):
    blanked = S.blank_heredoc_bodies(command)
    found = {(m.start(), m.group()) for m in pattern.finditer(blanked)}
    for match in pattern.finditer(S.strip_heredoc_bodies(command)):
        at = _raw_offset(command, match.start())
        assert (at, match.group()) in found
        assert command[at:at + len(match.group())] == match.group()


@pytest.mark.parametrize("command", TRICKY)
def test_the_blanked_text_has_the_same_tokens_as_the_stripped_text(command):
    """The converse: nothing is found on the blanked text that the stripped text lacks."""
    blanked = S.blank_heredoc_bodies(command)
    assert re.findall(r"\S+", blanked) == re.findall(r"\S+", S.strip_heredoc_bodies(command))
    for match in re.finditer(r"\S+", blanked):
        assert command[match.start():match.end()] == match.group()


def test_a_verb_after_a_body_slices_from_the_raw_command_where_the_stripped_offset_does_not():
    """The defect this exists for: an offset from the STRIPPED text is wrong on the raw one."""
    command = "cat <<EOF > f\nsome body text here\nEOF\ngit push origin"
    stripped_at = S.strip_heredoc_bodies(command).index("git push")
    assert command[stripped_at:stripped_at + 8] != "git push"
    blanked_at = S.blank_heredoc_bodies(command).index("git push")
    assert command[blanked_at:blanked_at + 8] == "git push"


def test_a_verb_written_inside_a_body_is_not_found():
    command = "cat <<'EOF' > runbook.md\ngit push --force\nEOF\necho done"
    assert "git push" not in S.blank_heredoc_bodies(command)
    assert "git push" not in S.commands_only_aligned(command)


def test_crlf_body_is_blanked_through_its_carriage_returns():
    command = "cat <<EOF\r\ngit push\r\nEOF\r\necho ok\r\n"
    assert S.blank_heredoc_bodies(command) == "cat <<EOF\r\n         \n    \necho ok\r\n"


def test_a_tab_stripped_terminator_is_blanked_too():
    command = "cat <<-EOF\n\tgit push\n\tEOF\necho ok"
    assert S.blank_heredoc_bodies(command) == "cat <<-EOF\n" + " " * 9 + "\n" + " " * 4 + "\necho ok"


@pytest.mark.parametrize("command", TRICKY)
@pytest.mark.parametrize("tool_name", ["Bash", "PowerShell", None])
def test_masking_the_blanked_text_stays_length_preserving(command, tool_name):
    blanked = S.blank_heredoc_bodies(command)
    assert len(S.mask_data_regions(blanked, tool_name=tool_name)) == len(command)


@pytest.mark.parametrize("command", TRICKY)
def test_mask_reads_a_blanked_body_as_whitespace(command):
    """mask_data_regions knows nothing of heredocs, so it cannot re-detect the opener; the blank
    body is plain spaces to it, and a quote or `(` that was in the body can no longer open a
    region. So every body position is still a space (or inside a region the OPENER line began)."""
    masked = S.mask_data_regions(S.blank_heredoc_bodies(command))
    dropped = _body_lines(command)
    raw = 0
    for index, line in enumerate(command.split("\n")):
        if index in dropped:
            assert set(masked[raw:raw + len(line)]) <= {" ", "Q"}
        raw += len(line) + 1


def test_an_apostrophe_in_a_body_no_longer_hides_the_next_statement_from_mask():
    command = "cat <<EOF > f\ndon't\nEOF\ngit push"
    assert "git push" not in S.mask_data_regions(command)              # the defect, raw
    assert "git push" in S.mask_data_regions(S.blank_heredoc_bodies(command))


@pytest.mark.parametrize("command", TRICKY)
@pytest.mark.parametrize("tool_name", ["Bash", "PowerShell"])
def test_commands_only_aligned_preserves_length(command, tool_name):
    assert len(S.commands_only_aligned(command, tool_name=tool_name)) == len(command)


@pytest.mark.parametrize("command", TRICKY)
@pytest.mark.parametrize("tool_name", ["Bash", "PowerShell"])
def test_commands_only_aligned_minus_the_body_lines_is_commands_only(command, tool_name):
    aligned = S.commands_only_aligned(command, tool_name=tool_name)
    assert _drop_body_lines(aligned, command) == S.commands_only(command, tool_name=tool_name)


@pytest.mark.parametrize("command", TRICKY)
def test_a_git_verb_found_on_commands_only_aligned_slices_from_the_raw_command(command):
    aligned = S.commands_only_aligned(command)
    for match in PATTERNS[0].finditer(aligned):
        assert command[match.start():match.end()] == match.group()


def test_commands_only_aligned_finds_the_real_push_and_not_the_quoted_one():
    command = ('git commit -m "$(cat <<\'EOF\'\nwhy: git push was (wrong\nEOF\n)" '
               "&& echo 'git push' && git push origin")
    aligned = S.commands_only_aligned(command)
    hits = [m.start() for m in re.finditer(r"\bgit push\b", aligned)]
    assert len(hits) == 1
    assert command[hits[0]:].startswith("git push origin")
    assert command.rfind("git push origin") == hits[0]


def test_commands_only_aligned_uses_the_tool_escape_rules():
    command = "cd C:" + _B + "; git push"
    assert "git push" in S.commands_only_aligned(command, tool_name="PowerShell")
    assert S.commands_only_aligned(command, tool_name="PowerShell") == S.commands_only(command, tool_name="PowerShell")
