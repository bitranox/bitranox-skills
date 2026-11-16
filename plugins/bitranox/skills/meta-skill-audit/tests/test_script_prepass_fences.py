"""Tests for script_prepass.fenced_python_syntax: the Python examples inside shipped Markdown.

Every case has a positive AND a negative: a check that only fires is indistinguishable from one
that always fires. The fence cases follow CommonMark, because a scanner that miscounts fences
reads prose as code (false hits) or code as prose (silent misses). ASCII only."""

import script_prepass as P

FENCE = "`" * 3


def _md(tmp_path, body, name="SKILL.md"):
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return [(name, path)]


def _block(code, info="python", fence=FENCE, indent=""):
    lines = [indent + fence + info] + [indent + line if line else "" for line in code.split("\n")]
    return "\n".join(lines + [indent + fence]) + "\n"


def test_a_python_block_that_does_not_parse_is_reported_at_its_markdown_line(tmp_path):
    body = "# Title\n\nSome prose.\n\n" + _block("x = 1\ndef f(:\n    pass")
    hits = P.fenced_python_syntax(_md(tmp_path, body))
    assert [(rel, line) for rel, line, _msg in hits] == [("SKILL.md", 7)]
    assert "does not parse" in hits[0][2]


def test_a_python_block_that_parses_is_silent(tmp_path):
    assert P.fenced_python_syntax(_md(tmp_path, _block("def f():\n    return 1"))) == []


def test_the_py_info_string_counts_as_python(tmp_path):
    assert P.fenced_python_syntax(_md(tmp_path, _block("def f(:", info="py")))


def test_a_block_of_another_language_is_not_parsed(tmp_path):
    assert P.fenced_python_syntax(_md(tmp_path, _block("def f(:", info="bash"))) == []


def test_a_bare_fence_is_not_parsed(tmp_path):
    assert P.fenced_python_syntax(_md(tmp_path, _block("def f(:", info=""))) == []


def test_a_method_body_fragment_is_accepted(tmp_path):
    code = "    def close(self):\n        self._sock.close()"
    assert P.fenced_python_syntax(_md(tmp_path, _block(code))) == []


def test_a_doctest_block_is_accepted(tmp_path):
    code = ">>> x = [1, 2]\n>>> len(x)\n2\n>>> for i in x:\n...     print(i)\n1\n2"
    assert P.fenced_python_syntax(_md(tmp_path, _block(code))) == []


def test_a_doctest_example_that_does_not_parse_is_reported_at_its_line(tmp_path):
    code = ">>> x = 1\n>>> x\n1\n>>> def f(:\n...     pass"
    hits = P.fenced_python_syntax(_md(tmp_path, _block(code)))
    assert [line for _rel, line, _msg in hits] == [5]


def test_a_block_indented_under_a_list_item_is_parsed_after_stripping_the_opener_indent(tmp_path):
    good = "- item\n\n" + _block("try:\n    pass\nfinally:\n    pass", indent="  ")
    bad = "- item\n\n" + _block("x = 1\nexcept ValueError:\n    pass", indent="  ")
    assert P.fenced_python_syntax(_md(tmp_path, good)) == []
    assert P.fenced_python_syntax(_md(tmp_path, bad, name="b.md"))


def test_a_python_fence_inside_a_longer_outer_fence_is_content_not_a_block(tmp_path):
    body = "````markdown\n" + _block("def f(:") + "````\n"
    assert P.fenced_python_syntax(_md(tmp_path, body)) == []


def test_a_python_fence_inside_a_tilde_fence_is_content_not_a_block(tmp_path):
    body = "~~~text\n" + _block("def f(:") + "~~~\n"
    assert P.fenced_python_syntax(_md(tmp_path, body)) == []


def test_a_closer_shorter_than_the_opener_does_not_close_the_block(tmp_path):
    body = "````python\nx = 1\n" + FENCE + "\ny = 2\n````\n"
    hits = P.fenced_python_syntax(_md(tmp_path, body))
    assert [line for _rel, line, _msg in hits] == [3]


def test_a_backtick_info_string_holding_a_backtick_is_not_a_fence(tmp_path):
    body = FENCE + "python `x`\ndef f(:\n" + FENCE + "python\nx = 1\n" + FENCE + "\n"
    assert P.fenced_python_syntax(_md(tmp_path, body)) == []


def test_an_unclosed_block_runs_to_the_end_of_the_document(tmp_path):
    body = "# T\n\n" + FENCE + "python\nx = 1\ndef f(:\n"
    hits = P.fenced_python_syntax(_md(tmp_path, body))
    assert [line for _rel, line, _msg in hits] == [5]


def test_two_blocks_are_judged_separately(tmp_path):
    body = _block("x = 1") + "\nprose\n\n" + _block("def f(:")
    hits = P.fenced_python_syntax(_md(tmp_path, body))
    assert [line for _rel, line, _msg in hits] == [8]


def test_run_prepass_reports_a_broken_block_in_a_shipped_skill_markdown(tmp_path):
    room = tmp_path / "plugin"
    skill = room / "skills" / "a"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(_block("def f(:"), encoding="utf-8")
    (skill / "references" / "ok.md").write_text(_block("x = 1"), encoding="utf-8")
    (skill / ".skillwriter").mkdir()
    (skill / ".skillwriter" / "notes.md").write_text(_block("def g(:"), encoding="utf-8")
    facts, _leads, summary = P.run_prepass(room, [], run=lambda *_a, **_k: None)
    assert list(facts) == ["skills/a/SKILL.md"]
    assert any(line.startswith("fenced_python_syntax") and "1 hit" in line for line in summary)
