"""Tests for unchained-gate-in-doc.py: refuse an edit that adds a bash block losing a gate's status."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import unchained_gate_in_doc as G

HOOK = Path(__file__).resolve().parent.parent / "unchained-gate-in-doc.py"
F = "```"


def _block(body, info="bash"):
    return "# Doc\n\n" + F + info + "\n" + body + "\n" + F + "\n"


# The motivating defect, verbatim in shape: a check appended after the gate made a red clippy exit 0.
MASKED = _block("cd /x\n"
                "CARGO_TARGET_DIR=/t cargo clippy --workspace -- -D warnings\n"
                'test -z "$(git status --porcelain -- Cargo.lock)" || { echo REFUSE; exit 1; }')
FIXED = _block("cd /x\n"
               "CARGO_TARGET_DIR=/t cargo clippy --workspace -- -D warnings \\\n"
               '  || { echo "REFUSE: clippy failed"; exit 1; }\n'
               'test -z "$(git status --porcelain -- Cargo.lock)" || { echo REFUSE; exit 1; }')


def test_the_motivating_block_is_a_finding_and_names_both_lines():
    [(line, gate, next_line, nxt)] = G.findings(MASKED)
    assert (line, next_line) == (5, 6)
    assert "cargo clippy" in gate and nxt.startswith("test -z")


def test_the_fixed_block_has_no_finding():
    assert G.findings(FIXED) == []


@pytest.mark.parametrize("body", [
    "cargo test -p a",                                            # the gate is the block's last status
    "cargo test -p a > out.txt 2>&1\necho $?",                    # status read explicitly
    "cargo test -p a > out.txt 2>&1\nrc=$?",
    "make test 2>&1 | tee log\nTEST_EXIT=${PIPESTATUS[0]}",       # status kept past a pipe
    "cargo test -p a || exit 1\ngit push",                        # its own refusal
    "cargo test -p a && echo ok || { echo bad; exit 1; }\ngit push",
    "cargo test -p a &\ngit status",                              # backgrounded
    "if cargo test -p a; then echo ok; fi\ngit push",              # a condition
    "while ! make test; do sleep 1; done\ngit push",
    "set -euo pipefail\nmake test\ngit push",                     # errexit stops the block
    "cargo test -p a  # unchained-ok: listing only\ngit push",    # opt-out on the line
    "# unchained-ok: alternatives, run one\ncargo test -p a\ncargo test -p b",
    "cat > f <<'EOF'\ncargo test\necho hi\nEOF\nrm f",            # gate text inside a heredoc body
    "grep -rn pytest docs/\ngit push",                            # pytest is an argument, not the program
    "echo 'cargo test; git push'\nls",                            # gate text inside quotes
])
def test_shapes_that_keep_or_read_the_status_are_left_alone(body):
    assert G.findings(_block(body)) == []


@pytest.mark.parametrize("body", [
    "make test\nmake push",                                       # the gate lost to a state change
    "make test && echo green\ngit push",                          # an &&-only tail still masks
    "cargo build --release -p x; strip target/release/x",         # `;` severs it like a newline
    "pytest -q\n# then publish\ngit push",                        # a comment line does not consume it
])
def test_shapes_that_lose_the_status_are_findings(body):
    assert len(G.findings(_block(body))) == 1


@pytest.mark.parametrize("info", ["text", "python", "", "console", "powershell"])
def test_only_shell_blocks_are_read(info):
    assert G.findings(_block("make test\nmake push", info=info)) == []


def test_only_added_findings_count_so_a_legacy_block_never_blocks_an_unrelated_edit():
    legacy = _block("make test\nmake push")
    assert G.added_findings(legacy, legacy + "\nNew prose.\n") == []
    assert len(G.added_findings(legacy, legacy + "\n" + MASKED)) == 1
    assert G.added_findings(MASKED, FIXED) == []


def _event(tool, path, **tool_input):
    return {"tool_name": tool, "tool_input": {"file_path": str(path), **tool_input}}


def test_edit_is_judged_against_the_file_it_lands_in(tmp_path):
    # The new follow-up line is outside any gate the old_string names: only reading the file
    # shows that the edit severed the gate above it.
    doc = tmp_path / "skills" / "x" / "SKILL.md"
    doc.parent.mkdir(parents=True)
    doc.write_text(_block("cd /x\nmake test"), encoding="utf-8")
    reason = G.decide(_event("Edit", doc, old_string="make test", new_string="make test\nmake push"))
    assert reason and "line 5" in reason and "make push" in reason and "unchained-ok" in reason


def test_edit_that_fixes_a_block_passes(tmp_path):
    doc = tmp_path / "CLAUDE.md"
    doc.write_text(MASKED, encoding="utf-8")
    old = "CARGO_TARGET_DIR=/t cargo clippy --workspace -- -D warnings\n"
    new = old.rstrip("\n") + ' || { echo "REFUSE: clippy failed"; exit 1; }\n'
    assert G.decide(_event("Edit", doc, old_string=old, new_string=new)) is None


def test_write_multiedit_and_unreadable_file_fallback(tmp_path):
    doc = tmp_path / "claude.md"                                  # case-insensitive name
    assert G.decide(_event("Write", doc, content=MASKED))
    missing = tmp_path / "gone" / "SKILL.md"
    edits = [{"old_string": "intro", "new_string": "intro\n" + MASKED}]
    assert G.decide(_event("MultiEdit", missing, edits=edits))    # falls back to the edit's own strings


@pytest.mark.parametrize("tool,name", [("Edit", "README.md"), ("Write", "notes.md"),
                                       ("Bash", "SKILL.md"), ("NotebookEdit", "SKILL.md")])
def test_other_files_and_tools_are_ignored(tmp_path, tool, name):
    assert G.decide(_event(tool, tmp_path / name, content=MASKED, new_string=MASKED,
                           old_string="")) is None


def _run(stdin):
    return subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", timeout=60)


def test_the_script_blocks_with_exit_2_and_explains_on_stderr(tmp_path):
    done = _run(json.dumps(_event("Write", tmp_path / "SKILL.md", content=MASKED)))
    assert done.returncode == 2
    assert "UNCHAINED GATE" in done.stderr and "cargo clippy" in done.stderr


def test_the_script_fails_open_on_garbage_and_allows_a_clean_doc(tmp_path):
    assert _run("not json").returncode == 0
    assert _run(json.dumps(_event("Write", tmp_path / "SKILL.md", content=FIXED))).returncode == 0
