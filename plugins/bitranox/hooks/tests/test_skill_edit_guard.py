"""Tests for skill-edit-guard.py: deny a SKILL.md edit (exit 2), allow else, env opt-out, fail-open."""

import json
import sys

import pytest

import skill_edit_guard as G


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    # isolate HOME so a REAL session receipt on the dev machine cannot flip deny tests to allow
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _ev(tool, path):
    return {"tool_name": tool, "tool_input": {"file_path": path}}


def test_deny_reason_on_skill_md_edit():
    reason = G.decide(_ev("Edit", "/repo/plugins/bitranox/skills/foo/SKILL.md"), {})
    assert reason and "meta-skill-writer" in reason


def test_deny_on_write_and_multiedit_and_relative_path():
    assert G.decide(_ev("Write", "/x/skills/bar/SKILL.md"), {})
    assert G.decide(_ev("MultiEdit", "skills/baz/SKILL.md"), {})              # relative path still matches


def test_allow_non_skill_files():
    assert G.decide(_ev("Edit", "/x/skills/foo/README.md"), {}) is None       # not SKILL.md
    assert G.decide(_ev("Edit", "/x/notskills/foo/SKILL.md"), {}) is None     # "skills" not a path seg
    assert G.decide(_ev("Edit", "/x/src/SKILL.md"), {}) is None               # no /skills/<name>/


def test_allow_non_edit_tools():
    assert G.decide(_ev("Bash", "/x/skills/foo/SKILL.md"), {}) is None
    assert G.decide({"tool_name": "Read", "tool_input": {"file_path": "/x/skills/foo/SKILL.md"}}, {}) is None


def test_env_bypass_allows_silently():
    assert G.decide(_ev("Edit", "/x/skills/foo/SKILL.md"), {"BITRANOX_SKILL_WRITER": "1"}) is None


def test_missing_tool_input_is_allowed():
    assert G.decide({"tool_name": "Edit"}, {}) is None


def test_main_blocks_with_exit_2_and_stderr(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_ev("Edit", "/x/skills/foo/SKILL.md"))))
    monkeypatch.delenv("BITRANOX_SKILL_WRITER", raising=False)
    assert G.main() == 2                              # non-zero blocks the tool call
    assert "SKILL-EDIT GUARD" in capsys.readouterr().err


def test_main_allows_when_env_set(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_ev("Edit", "/x/skills/foo/SKILL.md"))))
    monkeypatch.setenv("BITRANOX_SKILL_WRITER", "1")
    assert G.main() == 0
    assert capsys.readouterr().err == ""


def test_main_fail_open_on_bad_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert G.main() == 0                              # allow, never wedge
    assert capsys.readouterr().err == ""


# --- finding 5 from the 2026-08-28 script-wave audit of this hook -------------------------------

@pytest.mark.parametrize("path", [
    "/repo/plugins/bitranox/skills/demo/./SKILL.md",
    "/repo/plugins/bitranox/skills/demo/././SKILL.md",
    "/repo/plugins/bitranox/skills/./demo/SKILL.md",
    "/repo/plugins/bitranox/skills/demo/../demo/SKILL.md",
    "/repo/plugins/bitranox//skills/demo/SKILL.md",
])
def test_an_uncanonical_spelling_of_a_skill_md_still_denies(path):
    """The regex is tail-anchored, so an interior `/./` right before SKILL.md left it unmatched
    and the edit went through unguarded. `./` at the front and `..` earlier in the path happen to
    survive the tail anchor, which is why the first spellings anyone tries look safe."""
    assert G.decide({"tool_name": "Edit", "tool_input": {"file_path": path}}, {}) is not None


def test_the_canonical_path_still_denies():
    """Control: the case the guard was built for, beside the widening."""
    assert G.decide({"tool_name": "Edit",
                     "tool_input": {"file_path": "/repo/skills/demo/SKILL.md"}}, {}) is not None


@pytest.mark.parametrize("path", [
    "/repo/skills/demo/README.md",
    "/repo/skills/demo/scripts/SKILL.md.bak",
    "/repo/docs/SKILL.md",
    "/repo/skills/demo/nested/SKILL.md",
])
def test_a_path_that_is_not_a_skill_md_still_passes(path):
    """The direction the canonicalisation must NOT reach: normalising a path must not turn a
    non-SKILL.md into one. `skills/<name>/SKILL.md` is exactly one directory deep by design."""
    assert G.decide({"tool_name": "Edit", "tool_input": {"file_path": path}}, {}) is None


# --- rank 10 re-adjudication: case variants, NotebookEdit, the deny fall-through, backslashes ---

@pytest.mark.parametrize("path", [
    "/repo/Skills/foo/SKILL.md",
    "/repo/skills/foo/skill.md",
    "/repo/SKILLS/foo/Skill.Md",
])
def test_a_case_variant_of_a_skill_md_still_denies(path):
    """On macOS and Windows the filesystem ignores case, so these strings open the real SKILL.md.
    A case-sensitive match let every one of them through unguarded."""
    assert G.decide(_ev("Edit", path), {}) is not None


@pytest.mark.parametrize("path", [
    "/repo/Skills/foo/README.md",
    "/repo/notSkills/foo/skill.md",
    "/repo/Skills/foo/nested/skill.md",
])
def test_ignoring_case_does_not_widen_the_match_to_other_files(path):
    """Control: only the letter case is relaxed; the segment structure still decides."""
    assert G.decide(_ev("Edit", path), {}) is None


def _run_main(monkeypatch, capsys, event):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    monkeypatch.delenv("BITRANOX_SKILL_WRITER", raising=False)
    rc = G.main()
    return rc, capsys.readouterr().err


def test_notebookedit_names_its_target_in_notebook_path_and_is_denied(monkeypatch, capsys):
    """NotebookEdit sends `notebook_path`, not `file_path`. Reading only `file_path` made the
    registered NotebookEdit matcher unable to produce a decision at all."""
    rc, err = _run_main(monkeypatch, capsys, {
        "session_id": "S", "tool_name": "NotebookEdit",
        "tool_input": {"notebook_path": "/repo/skills/foo/SKILL.md", "new_source": "x"}})
    assert rc == 2
    assert "SKILL-EDIT GUARD" in err


def test_notebookedit_on_an_ordinary_notebook_is_allowed(monkeypatch, capsys):
    """Control: reading `notebook_path` must not turn every notebook edit into a denial."""
    rc, err = _run_main(monkeypatch, capsys, {
        "session_id": "S", "tool_name": "NotebookEdit",
        "tool_input": {"notebook_path": "/repo/notebooks/Quickstart.ipynb", "new_source": "x"}})
    assert (rc, err) == (0, "")


def test_edit_with_file_path_is_still_denied(monkeypatch, capsys):
    """Control: the `file_path` spelling keeps its answer beside the `notebook_path` fallback."""
    rc, _err = _run_main(monkeypatch, capsys, {
        "session_id": "S", "tool_name": "Edit",
        "tool_input": {"file_path": "/repo/skills/foo/SKILL.md"}})
    assert rc == 2


class _ReceiptStub:
    """Stands in for skill_receipt at the guard's call-time import, the one seam it has."""

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    def is_fresh(self, skill, session_id=None):
        self.calls += 1
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def test_a_receipt_store_that_raises_falls_through_to_deny(monkeypatch):
    """Fail CLOSED on the receipt: an error while asking the store is not a receipt. Allowing
    there would let any broken store disarm the guard."""
    stub = _ReceiptStub(OSError("receipt store unreadable"))
    monkeypatch.setitem(sys.modules, "skill_receipt", stub)
    assert G.decide({"session_id": "S", **_ev("Edit", "/repo/skills/foo/SKILL.md")}, {}) is not None
    assert stub.calls == 1, "the stub was never consulted, so this test proved nothing"


def test_a_fresh_receipt_from_the_same_seam_allows(monkeypatch):
    """Liveness pair for the test above: the same stub answering True must allow, which proves
    the stub really replaces the store rather than being bypassed."""
    stub = _ReceiptStub(True)
    monkeypatch.setitem(sys.modules, "skill_receipt", stub)
    assert G.decide({"session_id": "S", **_ev("Edit", "/repo/skills/foo/SKILL.md")}, {}) is None
    assert stub.calls == 1


@pytest.mark.parametrize("path", [
    r"C:\repo\skills\foo\SKILL.md",
    r"C:\repo\plugins\bitranox\skills\foo\.\SKILL.md",
    r"C:\repo\skills/foo\SKILL.md",
])
def test_a_windows_backslash_path_to_a_skill_md_denies(path):
    """Windows sends backslash separators even under Git Bash; the `/`-anchored regex never
    matches them unless they are normalised first."""
    assert G.decide(_ev("Edit", path), {}) is not None


def test_a_windows_backslash_path_to_another_file_is_allowed():
    """Control: normalising separators must not make a non-SKILL.md match."""
    assert G.decide(_ev("Edit", r"C:\repo\skills\foo\README.md"), {}) is None
