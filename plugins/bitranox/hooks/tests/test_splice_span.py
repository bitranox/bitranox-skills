"""Tests for splice_span.py, the one detector behind the toolbox-nudge span rule and the
block-index-splice guard. ASCII only."""

import pytest

import splice_span as S


SPLICE = (
    "from pathlib import Path\n"
    "p = Path('src/layout.py')\n"
    "s = p.read_text(encoding='utf-8')\n"
    "a = s.index('def natural_widths(')\n"
    "b = s.index('def render(')\n"
    "p.write_text(s[:a] + NEW + s[b:], encoding='utf-8')\n"
)


def heredoc(opener_prefix, body, delim="PY"):
    return "%s<<'%s'\n%s%s\n" % (opener_prefix, delim, body, delim)


# ---- the textual shape, shared with the nudge --------------------------------------------------
def test_the_shape_matches_the_splice():
    assert S.SPAN_SHAPE.search(SPLICE)


def test_the_shape_needs_a_write():
    assert not S.SPAN_SHAPE.search(SPLICE.replace("p.write_text(", "print("))


# ---- the code-level check ----------------------------------------------------------------------
def test_a_splice_written_back_is_a_span_splice():
    assert S.splices_between_found_anchors(SPLICE)


def test_a_splice_of_one_line_of_a_file_is_a_span_splice():
    program = ("lines = p.read_text().split('\\n')\nl = lines[i]\n"
               "a = l.index('| in flight:'); b = l.index('| FROM')\n"
               "lines[i] = l[:a] + new + l[b:]\np.write_text('\\n'.join(lines))\n")
    assert S.splices_between_found_anchors(program)


def test_a_splice_with_find_and_an_end_searched_from_the_start_still_counts():
    program = ("t = p.read_text()\ni = t.find('# BEGIN')\nj = t.find('# END', i)\n"
               "p.write_text(t[:i] + block + t[j:])\n")
    assert S.splices_between_found_anchors(program)


@pytest.mark.parametrize("program", [
    # the shape only inside a string literal: a document or test data ABOUT the trap
    "body = '''Never splice s[:a] + new + s[b:] after s.index(x) and s.index(y);\n"
    "p.write_text(it) is how it is written back.'''\nopen(out, 'w').write(body)\n",
    # the splice only inside an assert: a check of an edit made another way
    "a = dev.index('x'); b = dev.index('y')\nassert new == dev[:a] + ['z'] + dev[b:]\n"
    "p.write_text(text.replace(old, repl))\n",
    # an insert at ONE anchor (head and tail cut at the same offset) is anchor_edit insert's chore
    "t = p.read_text()\ni = t.index('marker')\nj = t.index('other')\n"
    "p.write_text(t[:i] + add + t[i:])\n",
    # two finds and a splice, but nothing written: printing a view
    "i = s.index('x')\nj = s.index('y')\nprint(s[:i] + '|' + s[j:])\n",
    # not Python at all (a shell-expanded heredoc that does not parse)
    "s = p.read_text(\na = s.index('x') b = s.index('y')\np.write_text(s[:a] + n + s[b:])\n",
])
def test_shapes_that_are_not_a_span_splice(program):
    assert not S.splices_between_found_anchors(program)


# ---- which heredocs are programs being RUN ------------------------------------------------------
@pytest.mark.parametrize("prefix", [
    "python3 - ",
    "python3 ",
    "cd /opt/repo && python3 - ",
    "python3 - \"$S\" /opt/x.md ",
    "uv run python - ",
    "uv run --with pyyaml python3 - ",
    "env -u VIRTUAL_ENV python3.14 -I - ",
    "/usr/bin/python3 - ",
    "FOO=1 python - ",
])
def test_a_heredoc_fed_to_a_python_interpreter_is_a_program(prefix):
    assert S.programs_run_by(heredoc(prefix, SPLICE)) == [SPLICE.rstrip("\n")]


@pytest.mark.parametrize("prefix", [
    "cat > /tmp/edit.py ",          # authoring a file: the Write tool's case, not refused
    "python3 /opt/tool.py ",        # the body is stdin DATA for a script
    "python3 -m json.tool ",        # stdin data for a module
    "python3 -c 'import sys' ",     # -c is the program, the body is its stdin
    "git commit -F - ",
    "tee /tmp/notes.md ",
])
def test_a_heredoc_not_run_as_python_is_not_a_program(prefix):
    assert S.programs_run_by(heredoc(prefix, SPLICE)) == []


def test_only_the_python_heredoc_of_several_is_returned():
    command = heredoc("cat > /tmp/n.md ", "notes\n", "EOF") + heredoc("python3 - ", SPLICE)
    assert S.programs_run_by(command) == [SPLICE.rstrip("\n")]


# ---- the guard's question ----------------------------------------------------------------------
def test_a_command_running_a_span_splice_is_found():
    assert S.runs_an_unchecked_splice(heredoc("python3 - ", SPLICE))


def test_the_same_splice_authored_into_a_file_is_not_a_run():
    assert not S.runs_an_unchecked_splice(heredoc("cat > /tmp/edit.py ", SPLICE))


def test_a_command_without_a_heredoc_is_not_a_run():
    assert not S.runs_an_unchecked_splice("python3 /tmp/edit.py")


def test_a_program_with_an_invalid_escape_judges_without_a_warning():
    # a heredoc body often carries `\``; the warning would print on the hook's stderr
    import warnings
    program = SPLICE + "note = 'run \\`make\\`'\n"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert S.splices_between_found_anchors(program)
    assert not [w for w in caught if issubclass(w.category, SyntaxWarning)]


# ---- the exemption: every anchor the program cuts at is asserted unique ------------------------
# User decision 2026-10-30: a program whose every find/index anchor is checked `count(...) == 1`
# is let through; a partly checked one is refused, and an anchor the matcher cannot pair with a
# count falls on the REFUSE side.

_CUT = ("s = p.read_text()\n"
        "a = s.index(START)\n"
        "b = s.index(END, a)\n"
        "p.write_text(s[:a] + new + s[b:])\n")


def _checked(*lines):
    return "".join(line + "\n" for line in lines) + _CUT


@pytest.mark.parametrize("program", [
    _checked("assert s.count(START) == 1", "assert s.count(END) == 1"),
    _checked("assert s.count(START) == 1 and s.count(END) == 1, 'ambiguous'"),
    _checked("assert 1 == s.count(START)", "assert s.count(END) == 1"),
    _checked("if s.count(START) != 1:", "    raise SystemExit('start')",
             "if s.count(END) != 1:", "    sys.exit('end')"),
    _checked("if not s.count(START) == 1 or s.count(END) != 1:", "    raise ValueError('x')"),
    # string-constant anchors paired with the same constant
    "s = p.read_text()\nassert s.count('# BEGIN') == 1 and s.count('# END') == 1\n"
    "a = s.index('# BEGIN'); b = s.index('# END')\np.write_text(s[:a] + new + s[b:])\n",
])
def test_a_fully_checked_splice_is_exempt(program):
    assert S.splices_between_found_anchors(program)
    assert S.every_anchor_checked(program)
    assert not S.runs_an_unchecked_splice(heredoc("python3 - ", program))


@pytest.mark.parametrize("program", [
    # the recorded recurrence was the END marker: checking only the start is not enough
    _checked("assert s.count(START) == 1"),
    _checked("assert s.count(END) == 1"),
    # the wrong comparison: present at least once is not unique
    _checked("assert s.count(START) >= 1", "assert s.count(END) >= 1"),
    _checked("assert s.count(START) == 1", "assert s.count(END) == 2"),
    # a positive branch is not a guard: the edit is not stopped when the count is wrong
    _checked("if s.count(START) == 1 and s.count(END) == 1:", "    print('ok')"),
    # a failing count that only prints goes on to cut anyway
    _checked("if s.count(START) != 1:", "    print('start')",
             "if s.count(END) != 1:", "    print('end')"),
    # an anchor the matcher cannot pair (built in place) falls on the refuse side
    "s = p.read_text()\nassert s.count(f'def {n}(') == 1 and s.count(END) == 1\n"
    "a = s.index(f'def {n}('); b = s.index(END)\np.write_text(s[:a] + new + s[b:])\n",
    # a count of a DIFFERENT anchor does not cover this one
    _checked("assert s.count(OTHER) == 1", "assert s.count(END) == 1"),
    # nothing checked at all
    SPLICE,
])
def test_a_splice_not_fully_checked_is_still_refused(program):
    assert S.splices_between_found_anchors(program)
    assert not S.every_anchor_checked(program)
    assert S.runs_an_unchecked_splice(heredoc("python3 - ", program))
