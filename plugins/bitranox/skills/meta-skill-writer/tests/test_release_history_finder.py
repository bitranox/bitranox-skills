"""The version-history finder in SKILL.md ("Describe the latest release only") against planted lines.

The pattern is read out of SKILL.md itself, so the test checks the text a reader copies rather than
a second copy that could drift from it. The finder runs it through `grep -iE`; the test compiles it
with Python's `re` (IGNORECASE), whose syntax agrees with ERE for every construct the pattern uses,
and cross-checks with the real `grep -iE` where one is on PATH.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_MD = Path(__file__).resolve().parent.parent / "SKILL.md"
GREP = shutil.which("grep")

# Each line is a version-history marker the finder must list as a candidate.
HISTORY = [
    "From 3.0.0 the client retries on its own.",
    "Starting with v2.4 the cache is per project.",
    "**Layered paths (7.2.0 and later)** - the user layer moved.",
    "- **`serialize_by_alias=True`** (pydantic 2.11 and later).",
    "Profiles (5.7.0 or later) select a config.d subtree.",
    "Every release v2.0 and newer reads the file.",
    "Strict mode, 2.3 onwards, refuses unknown keys.",
    "The flag was previously required.",
    "It no longer prints a banner.",
]

# Text the finder must stay quiet on: no version number, or a floor in an install line.
NOT_HISTORY = [
    "uvx --from 'pkg>=0.3.2' pkg --help",
    "Sooner or later every cache goes stale.",
    "Pick option 3 and later ones in the menu.",
    "The newer and later releases share one config.",
]


def finder_pattern() -> str:
    """The single `P='...'` assignment in SKILL.md's finder block."""
    found = re.findall(r"^P='(.*)'$", SKILL_MD.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(found) == 1, found
    return found[0]


def joined(text: str) -> str:
    """The finder's second pass: every run of whitespace joined to one space (tr -s)."""
    return re.sub(r"\s+", " ", text)


@pytest.mark.parametrize("line", HISTORY)
def test_the_finder_lists_a_history_line(line: str) -> None:
    assert re.search(finder_pattern(), line, re.IGNORECASE), line


@pytest.mark.parametrize("line", NOT_HISTORY)
def test_the_finder_skips_a_line_with_no_version_history(line: str) -> None:
    assert not re.search(finder_pattern(), line, re.IGNORECASE), line


def test_the_whole_text_pass_finds_a_trailing_marker_broken_across_a_line_end() -> None:
    text = "**Layered paths (7.2.0\nand later)** - the user layer moved.\n"
    pattern = finder_pattern()
    assert not any(re.search(pattern, line, re.IGNORECASE) for line in text.splitlines())
    assert re.search(pattern, joined(text), re.IGNORECASE)


@pytest.mark.skipif(GREP is None, reason="grep is not on PATH")
def test_grep_agrees_with_re_on_every_planted_line(tmp_path: Path) -> None:
    lines = HISTORY + NOT_HISTORY
    sample = tmp_path / "sample.md"
    sample.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = subprocess.run([GREP, "-iE", finder_pattern(), str(sample)], capture_output=True,
                         encoding="utf-8", check=False)
    assert out.returncode in (0, 1), out.stderr
    assert out.stdout.splitlines() == HISTORY
