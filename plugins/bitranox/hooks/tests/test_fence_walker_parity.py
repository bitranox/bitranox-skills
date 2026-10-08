"""One fence rule for every hook module that has to know what is code.

tell_chars, memory_engine and harness_checks each needed to know which lines of a Markdown file
sit in a fenced code block, and each once carried its own scanner. They disagreed on indentation:
one accepted a fence at any depth, so an indented example fence nested in a block closed it early
and the rest of the block read as prose; the others accepted only 0-3 spaces, so a fence inside a
list item was missed and its code read as prose. The CASES below are the shapes that split them,
and every caller must give the answer CommonMark gives.
"""
import harness_checks as HC
import memory_engine as ME
import pytest
import tell_chars as TC

# (name, markdown, 1-based numbers of the lines that are code: fence lines and their content)
CASES = [
    ("plain backtick fence", "a\n```\nb\n```\nc\n", {2, 3, 4}),
    ("tilde fence", "~~~\nb\n~~~\nc\n", {1, 2, 3}),
    ("unclosed fence runs to the end", "a\n```\nb\nc\n", {2, 3, 4}),
    ("a closer may be longer", "```\nb\n`````\nc\n", {1, 2, 3}),
    ("a shorter run does not close", "````\n```\nb\n````\nc\n", {1, 2, 3, 4}),
    ("the other character does not close", "```\n~~~\nb\n```\nc\n", {1, 2, 3, 4}),
    ("a closer must be bare", "```\n```python\nb\n```\nc\n", {1, 2, 3, 4}),
    ("an inline span at line start is no opener", "```x``` y\nz\n", set()),
    ("a backtick in a tilde info string is allowed", "~~~`odd`\nb\n~~~\nc\n", {1, 2, 3}),
    ("an opener indented up to three spaces", "   ```\nb\n   ```\nc\n", {1, 2, 3}),
    # A list item's content starts after its marker, so a fence there is indented relative to it.
    ("a fence inside a list item", "1. step\n\n    ```bash\n    run\n    ```\nafter\n",
     {3, 4, 5}),
    ("a fence inside a deeper list item", "  2. step:\n     ```bash\n     run\n     ```\nafter\n",
     {2, 3, 4}),
    # Four columns beyond its block, a fence-looking line is content of the block it sits in.
    ("an indented example fence does not close the outer block",
     "```\nexample:\n    ```bash\n    x\n    ```\nstill code\n```\nprose\n", {1, 2, 3, 4, 5, 6, 7}),
    # At top level, four spaces after a paragraph's blank line make indented code, not a fence.
    ("four spaces at top level is indented code, not a fence",
     "para\n\n    ```\nprose after\n", set()),
]


def _tc(text):
    return {n for n, (_line, code) in enumerate(TC.lines_with_code_state(text), 1) if code}


def _hc(text):
    return {i + 1 for i in HC._fenced_lines(TC.split_lines(text))}


def _me(text):
    masked = ME.mask_code_regions(text)
    return {n for n, (raw, out) in enumerate(zip(TC.split_lines(text), TC.split_lines(masked)), 1)
            if raw.strip() and not out.strip()}


@pytest.mark.parametrize("name,text,code", CASES, ids=[c[0] for c in CASES])
def test_the_shared_rule_marks_the_commonmark_code_lines(name, text, code):
    assert {i + 1 for i, f in enumerate(TC.code_line_flags(TC.split_lines(text))) if f} == code


@pytest.mark.parametrize("name,text,code", CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize("caller", [_tc, _hc, _me], ids=["tell_chars", "harness_checks",
                                                         "memory_engine"])
def test_every_caller_gives_the_same_answer(caller, name, text, code):
    # memory_engine's view only shows NON-BLANK lines it blanked, so compare on those.
    nonblank = {n for n, line in enumerate(TC.split_lines(text), 1) if line.strip()}
    assert caller(text) & nonblank == code & nonblank


def test_code_line_flags_accepts_lines_with_their_endings():
    lines = TC.split_lines("```\r\nb\r\n```\r\nc\r\n", keepends=True)
    assert TC.code_line_flags(lines) == [True, True, True, False]


def test_memory_engine_keeps_offsets_and_line_breaks_when_masking():
    text = "a\r\n```\r\n[[x]]\r\n```\r\nb\n"
    masked = ME.mask_code_regions(text)
    assert len(masked) == len(text)
    assert [i for i, c in enumerate(masked) if c == "\n"] == [i for i, c in enumerate(text)
                                                              if c == "\n"]
    assert "[[x]]" not in masked and masked.endswith("b\n")
