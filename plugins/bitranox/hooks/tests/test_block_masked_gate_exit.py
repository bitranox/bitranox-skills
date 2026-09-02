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


# --- inert regions: text that MENTIONS the footgun is not committing it -------------------
#
# Third false fire of this guard on the day it shipped, each on prose rather than a command.
# The escaped case is the one that actually happened, reproduced here from the real command:
# an echo label describing the rule, written after a `| sed`, was read as a status check.


def test_escaped_dollar_question_is_prose_not_a_status_read():
    """`\\$?` is passed through literally by bash, so it can never be reading a status."""
    command = 'grep -c "x" f.py | sed \'s/^/n: /\'\necho "=== does it do the \\$?-after-pipe detection? ==="'
    assert B.reads_masked_status(command) is False


def test_a_comment_mentioning_the_footgun_does_not_fire():
    assert B.reads_masked_status("grep x f | head -3\n# never read $? after a pipe") is False


def test_single_quoted_prose_does_not_fire():
    """No expansion happens inside single quotes, so the text is inert."""
    assert B.reads_masked_status("grep x f | head -3\necho 'mentions $? literally'") is False


def test_double_quoted_status_read_still_fires():
    """The counterpart the narrowing must NOT cost: `$?` expands inside double quotes.

    This is the whole point of the guard, and it is why double-quoted prose is knowingly left
    as a false positive - to the shell the two are identical, so no scanner can separate them.
    """
    assert B.reads_masked_status('tool verify | tail -5; echo "rc=$?"') is True


def test_blanking_preserves_the_command_shape():
    """Structure outside the inert regions must survive, or the pipeline split changes meaning."""
    import shell_text

    blanked = shell_text.blank_unexpanded_text("a | tail -2; b && c || d # note")
    assert "|" in blanked and ";" in blanked and "&&" in blanked and "||" in blanked
    assert "note" not in blanked


def _rc(monkeypatch, command):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": command}})))
    return B.main()


def test_a_heredoc_body_is_not_a_masked_gate(monkeypatch):
    """main()'s BLOCKING path split the RAW command while the advisory path masked data first, so
    a doc that WRITES an example of the footgun was blocked as being one. Measured live: this exact
    shape blocked a real command while this guard was under investigation."""
    body = ["C = [", "  'never write: pytest -q " + chr(124) + " tail -3',",
            "  'grep -rn x . " + chr(124) + " head -20 && git commit -m y',", "]"]
    cmd = "cat > claims.py <<'PYEOF'\n" + "\n".join(body) + "\nPYEOF\npython3 claims.py"
    assert _rc(monkeypatch, cmd) == 0


def test_a_gate_named_inside_a_quoted_argument_is_not_a_gate(monkeypatch):
    """`grep -rn "npm test"` runs grep, not npm. The gate name was matched anywhere in the
    statement rather than in command position."""
    assert _rc(monkeypatch, 'grep -rn "npm test" . ' + chr(124) + ' head -20 && git commit -m x') == 0


def test_a_real_masked_gate_is_still_blocked(monkeypatch):
    """The direction where it must NOT apply, including one standing after a heredoc."""
    assert _rc(monkeypatch, "pytest -q " + chr(124) + " tail -3 && echo OK") == 2
    assert _rc(monkeypatch, "cat > n.md <<'EOF'\nprose\nEOF\npytest -q "
               + chr(124) + " tail -3 && echo OK") == 2


# ---------------------------------------------------------------------------
# Blocks: a BACKGROUNDED gate that does not go through the jig
# ---------------------------------------------------------------------------


def run_main_bg(monkeypatch, command, background):
    """Drive main() with run_in_background set, as the Bash tool_input carries it."""
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": command, "run_in_background": background}}
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    return B.main()


@pytest.mark.parametrize(
    ("label", "command"),
    [
        ("make test with the safe redirect", 'make test > log 2>&1; echo "RC=$?" >> log; tail log'),
        ("make push", "make push ARGS='fix: x'"),
        ("ci_wait", "uv run ci_wait.py --sha deadbeef"),
        ("gh run watch", "gh run watch 123"),
        ("pytest", "pytest tests/ -q > out.log"),
    ],
)
def test_a_backgrounded_gate_without_the_jig_is_blocked(monkeypatch, capsys, label, command):
    """The completion notice reports the compound's last command, and that is what gets believed.

    The safe-redirect case is deliberately in this list. It is the form the memory entry
    recommends, and it is the exact command that produced the 2026-09-02 miss: written
    correctly, then misreported from the notice before the log was ever opened. Backgrounding
    is what makes the notice the thing you read, so the redirect does not rescue it.
    """
    assert run_main_bg(monkeypatch, command, True) == 2
    assert "BLOCKED: a backgrounded gate" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("label", "command", "background"),
    [
        ("the jig itself", "uv run scripts/gate.py --gate 'make test' --then 'git push'", True),
        ("foreground gate", 'make test > log 2>&1; echo "RC=$?" >> log', False),
        ("field absent entirely", "make test", None),
        ("backgrounded non-gate", "rsync -a src/ dst/ > sync.log 2>&1", True),
    ],
)
def test_what_the_background_block_must_never_refuse(monkeypatch, label, command, background):
    """The allow-cases, which matter more than the block-cases for a hook that denies.

    `field absent entirely` pins the degradation direction: this guard reads a field that is
    doc-verified rather than probed here, so if a harness stops sending it the guard must go
    quiet, never start refusing every gate anyone runs.
    """
    assert run_main_bg(monkeypatch, command, background) == 0
