"""Tests for block-masked-gate-exit.py (PreToolUse(Bash) masked-gate-status guard).

Contract: reads a PreToolUse event JSON on stdin. Exit 2 (with stderr) blocks ONLY when a
recognised gate runs inside a pipeline where it is not the last element (so a filter's status
becomes the pipeline's), AND a later statement claims success (an OK-ish echo) or commits/pushes.
Every other path exits 0, including each documented fix (pipefail, PIPESTATUS), a bare gate, a
gate that ends its pipeline, and a pipe with no success claim.

The allow-cases matter as much as the block-cases: this guard blocks a Bash call outright, so a
false positive wedges legitimate work for everyone who installs the marketplace. The module's
docstring promises "a pipeline whose status is handled correctly is never blocked" - these pin it.

All content is ASCII.
"""

import io
import json
import sys

import pytest

import block_masked_gate_exit as B


def run_main(monkeypatch, command):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    return B.main()


# ---------------------------------------------------------------------------
# Blocks: a gate's status is masked, and a later statement claims it passed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "command"),
    [
        ("fmt piped to head, then OK echo", 'cargo fmt -- --check 2>&1 | head -20 && echo "FMT-OK"'),
        ("clippy piped to grep, then commit", 'cargo clippy -- -D warnings 2>&1 | grep -E "^error" ; git add -A && git commit -m x'),
        ("pytest piped to tail, then commit", 'pytest -q | tail -3; git commit -m "wip"'),
        ("ruff piped to wc, then PASS echo", 'ruff check . | wc -l && echo "PASS"'),
        ("pyright piped to grep, then push", 'pyright | grep error; git push'),
        ("make test piped to tail, then clean echo", 'make test 2>&1 | tail -5 && echo "all clean"'),
    ],
)
def test_blocks_a_success_claim_on_a_masked_gate(monkeypatch, capsys, label, command):
    assert run_main(monkeypatch, command) == 2, label
    err = capsys.readouterr().err
    assert "BLOCKED" in err
    # The message must name the fixes, or it teaches nothing.
    assert "PIPESTATUS" in err and "pipefail" in err


# ---------------------------------------------------------------------------
# Allows: the documented fixes, and ordinary correct usage
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "command"),
    [
        ("set -o pipefail propagates the status", 'set -o pipefail; pytest -q | tail -3 && echo "OK"'),
        ("PIPESTATUS is checked", 'pytest -q | tail -3; test ${PIPESTATUS[0]} -eq 0 && echo "OK"'),
        ("gate runs bare, it sets the status", 'pytest -q && echo "OK"'),
        ("gate is the last pipeline element", 'echo hi | pytest -q --stdin && echo "OK"'),
        ("piped, but nothing claims success", "make test 2>&1 | tail -6"),
        ("no gate involved at all", 'ls | head -3 && git commit -m x'),
        ("gate piped, success claim comes BEFORE it", 'echo "OK so far" && pytest -q | tail -3'),
        ("commit first, then an unrelated piped gate", 'git commit -m x && pytest -q | tail -3'),
    ],
)
def test_allows_correct_or_unrelated_commands(monkeypatch, capsys, label, command):
    assert run_main(monkeypatch, command) == 0, label
    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# The pure predicate
# ---------------------------------------------------------------------------


def test_masks_a_gate_requires_a_pipe():
    assert B.masks_a_gate("pytest -q") is False


def test_masks_a_gate_false_when_gate_is_last():
    assert B.masks_a_gate("cat log | pytest -q") is False


def test_masks_a_gate_false_without_a_swallowing_filter():
    # A pipe into a non-filter still masks the status, but this guard deliberately
    # scopes itself to the head/grep/tail shape it can recognise with confidence.
    assert B.masks_a_gate("pytest -q | some-unknown-tool") is False


def test_masks_a_gate_true_for_the_real_shape():
    assert B.masks_a_gate("pytest -q 2>&1 | head -5") is True


# ---------------------------------------------------------------------------
# Fail-open: a broken guard must never wedge a turn
# ---------------------------------------------------------------------------


def test_bad_stdin_exits_clean(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
    assert B.main() == 0


def test_missing_command_exits_clean(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": "Bash", "tool_input": {}})))
    assert B.main() == 0


def test_non_bash_payload_exits_clean(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "x"}})))
    assert B.main() == 0


def test_block_message_is_ascii(monkeypatch, capsys):
    run_main(monkeypatch, 'pytest -q | tail -3; git commit -m x')
    capsys.readouterr().err.encode("ascii")  # raises if a non-ASCII char slipped in


# ---- the VERIFICATION shape: a pipe, then a read of $? -----------------------------------------
# The gate-then-action shape above did not cover measuring a command's OWN exit code. Measured
# 2026-08-09: `tool verify ... | tail -5; echo "rc=$?"` printed rc=0 while the tool had exited 1,
# so a working negative control read as broken - and a passing one would have been recorded as
# proof. The command need not be a recognised gate for this to mislead.

def test_reads_masked_status_catches_the_verification_shape():
    assert B.reads_masked_status('mytool verify --sid 9 | tail -5; echo "rc=$?"') is True
    assert B.reads_masked_status("uv run t.py check x | head -3; rc=$?") is True


def test_reads_masked_status_ignores_a_pipe_with_no_status_read():
    """The negative must be reachable, or every pipeline is blocked."""
    assert B.reads_masked_status("ls -l | tail -5") is False
    assert B.reads_masked_status("ls -l | tail -5; echo done") is False


def test_reads_masked_status_ignores_a_status_read_with_no_pipe():
    assert B.reads_masked_status('mytool verify; echo "rc=$?"') is False


# ---- false positives found by the guard firing on its author, 2026-08-09 -----------------------

def test_a_status_read_belonging_to_a_LATER_command_is_not_masked():
    """`$?` refers to the IMMEDIATELY preceding command. Once another command has run, the
    pipeline's status is gone and the read is about something else entirely - so only the
    statement directly after the pipe can be the mistake. Measured: this fired on a command that
    piped one check into `tail`, then ran a SECOND check redirected to a file (the correct form)
    and read its `$?`, which is exactly the shape the guard tells you to use."""
    correct = ('pwsh -File chk.ps1 good.ps1 2>&1 | tail -4; echo "=== control ==="; '
               'pwsh -File chk.ps1 bad.ps1 > out 2>&1; echo "rc=$?"')
    assert B.reads_masked_status(correct) is False


def test_a_heredoc_body_is_data_here_too():
    """Writing ABOUT the footgun is not committing it - the guard blocked its own documentation."""
    documenting = ("cat > note.md <<'EOF'\n"
                   "never write: mytool verify | tail -5; echo \"rc=$?\"\n"
                   "EOF")
    assert B.reads_masked_status(documenting) is False


def test_the_real_shape_still_fires_after_both_fixes():
    """The control: narrowing must not disarm the guard."""
    assert B.reads_masked_status('mytool verify --sid 9 | tail -5; echo "rc=$?"') is True
    assert B.reads_masked_status("uv run t.py check x | head -3; rc=$?") is True


def test_reads_masked_status_respects_the_documented_fixes():
    assert B.reads_masked_status('set -o pipefail; t | tail -1; echo "rc=$?"') is False
    assert B.reads_masked_status('t | tail -1; echo "${PIPESTATUS[0]}"') is False


def test_reads_masked_status_only_counts_a_read_AFTER_the_pipe():
    """`rc=$?` before the pipeline reads something else entirely - not this bug."""
    assert B.reads_masked_status('true; rc=$?; ls | tail -2') is False
