"""One fence rule for every hook module that has to know what is code.

tell_chars, memory_engine and harness_checks each needed to know which lines of a Markdown file
sit in a fenced code block, and each once carried its own scanner. They disagreed on indentation:
one accepted a fence at any depth, so an indented example fence nested in a block closed it early
and the rest of the block read as prose; the others accepted only 0-3 spaces, so a fence inside a
list item was missed and its code read as prose. The CASES below are the shapes that split them,
and every caller must give the answer CommonMark gives.

Four skill scripts keep a scanner of their own because they ship standalone and cannot import
hooks/. They cannot share the code, so they share this table instead: each is loaded from its own
path and held to the hooks rule, so a fix to one copy cannot leave the others behind unnoticed.
"""
import importlib.util
import sys
from pathlib import Path

import harness_checks as HC
import memory_engine as ME
import pytest
import tell_chars as TC

_SKILLS = Path(__file__).resolve().parents[2] / "skills"

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


# ---- the standalone skill-script scanners ------------------------------------------------------

def _load(rel):
    """Import a skill script from its own path under a private name. It is registered in
    sys.modules before it runs, because a string-annotated dataclass resolves through it, and its
    directory is on sys.path only while it loads, for the siblings it imports (mdwrap's
    _cli_envelope) - left there, it would shadow same-named modules for the rest of the run."""
    path = _SKILLS / rel
    name = "fence_parity_" + path.stem
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(path.parent))
    return module


MDWRAP = _load("compuse-toolbox/scripts/mdwrap.py")
TABLES = _load("docs-md-table-formatting/reformat_tables.py")
VARIANCE = _load("meta-consolidate-claude-md/scripts/claudemd_variance.py")
ADOPT = _load("meta-adopting-external-skills/adopt_skill.py")

# A column-0 line cannot sit inside a list item's fence (it ends the item), and the hooks rule
# does not model a container ending, so the heading probes skip the list-item cases.
_COLUMN_ZERO_CASES = [c for c in CASES if "list item" not in c[0]]


@pytest.mark.parametrize("name,text,code", CASES, ids=[c[0] for c in CASES])
def test_reformat_tables_classifies_lines_as_the_hooks_rule_does(name, text, code):
    lines = TC.split_lines(text)
    got = [cls.kind for cls in TABLES.classify_lines(lines)]
    want = {TC.FENCE: TABLES.FENCE, TC.CODE: TABLES.LITERAL, TC.TEXT: TABLES.TEXT}
    assert got == [want[kind] for kind in TC.line_kinds(lines)]


@pytest.mark.parametrize("name,text,code", CASES, ids=[c[0] for c in CASES])
def test_mdwrap_finds_the_lines_inside_a_fence_as_the_hooks_rule_does(name, text, code):
    # mdwrap reports the lines strictly INSIDE a block, fence lines excluded.
    lines = TC.split_lines(text)
    inside = {i for i, kind in enumerate(TC.line_kinds(lines)) if kind == TC.CODE}
    assert MDWRAP._fenced_lines(lines) == inside


def _probe_positions(text):
    """Each way to insert a column-0 `## probe` line into `text`, with whether the hooks rule
    reads that probe as code."""
    lines = TC.split_lines(text)
    for at in range(len(lines) + 1):
        probed = lines[:at] + ["## probe"] + lines[at:]
        yield probed, at, TC.code_line_flags(probed)[at]


@pytest.mark.parametrize("name,text,code", _COLUMN_ZERO_CASES,
                         ids=[c[0] for c in _COLUMN_ZERO_CASES])
def test_claudemd_variance_skips_a_heading_in_a_fence_as_the_hooks_rule_does(name, text, code):
    for probed, at, in_code in _probe_positions(text):
        assert (at in VARIANCE._heading_lines(probed)) is not in_code, (at, probed)


@pytest.mark.parametrize("name,text,code", _COLUMN_ZERO_CASES,
                         ids=[c[0] for c in _COLUMN_ZERO_CASES])
def test_adopt_skill_skips_a_heading_in_a_fence_as_the_hooks_rule_does(name, text, code):
    for probed, at, in_code in _probe_positions(text):
        h1 = [line.replace("## ", "# ", 1) if i == at else line for i, line in enumerate(probed)]
        # _h1_index answers the FIRST visible `# ` line, so only a probe in code may be skipped.
        assert (ADOPT._h1_index(h1, 0) == at) is not in_code, (at, h1)


def test_the_heading_probes_reach_both_answers():
    # A probe table where every insertion lands outside code would pass any scanner.
    answers = {in_code for _n, text, _c in _COLUMN_ZERO_CASES
               for _p, _at, in_code in _probe_positions(text)}
    assert answers == {True, False}
