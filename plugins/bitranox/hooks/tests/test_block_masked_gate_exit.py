"""Tests for block-masked-gate-exit.py (PreToolUse(Bash|PowerShell) masked-gate-status guard).

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
import os
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


@pytest.mark.parametrize("command", [
    'echo "x | head ; rc=$?"',
    'echo "a | tail -3"; echo "rc=$?"',
    'printf "%s\\n" "one | head -1 ; two $?"',
])
def test_a_separator_or_pipe_inside_double_quotes_is_not_structure(command):
    """The status read is found where `$?` expands (double quotes kept), but STRUCTURE must come
    from the masked text: split on the expansion view, `echo "x | head ; rc=$?"` - one echo - read
    as a pipe into head followed by a status read."""
    assert B.reads_masked_status('tool verify | head ; echo "rc=$?"') is True     # control
    assert B.reads_masked_status(command) is False


def test_a_quoted_separator_before_the_pipe_does_not_shift_the_adjacency():
    assert B.reads_masked_status('echo "a;b" | tail -3; echo "rc=$?"') is True


# The corpus replay of the structure fix (100,216 real commands) changed 9 verdicts. Five were
# false positives removed - a pipe inside a `$(...)` that only builds an argument, whose `$?` then
# reads the OUTER command. The other four pinned these two rules.

@pytest.mark.parametrize("command", [
    'o=$(tool --x 2>&1 </dev/null | head -c 4000)\nrc=$?',
    'out=$(E --p x config 2>&1 >/dev/null | grep -iE "error" | head -1)\nrc=$?',
])
def test_an_assignment_from_a_piped_substitution_hands_on_the_filters_status(command):
    """An assignment-only statement exits with its substitution's status, which is the inner
    pipeline's LAST element - the filter. Two such loops in the corpus read `rc=$?` exactly so."""
    assert B.reads_masked_status(command) is True


@pytest.mark.parametrize("command", [
    'tool --sha a$(git rev-parse x | cut -c9-) > log 2>&1; echo "RC=$?"',
    'out=$(app $(env | grep -o X | sed s/^/-u/) 2>err); rc=$?',
])
def test_a_pipe_that_only_builds_an_argument_does_not_set_the_status(command):
    assert B.reads_masked_status(command) is False


def test_a_status_read_inside_a_later_substitution_reads_that_substitutions_command():
    """`$(tool ...; echo $?)` reports tool's status, not the pipe's before it - the corpus shape
    `... | tail -1; echo "exit=$(lsdsk ... >/dev/null 2>&1; echo $?)"`."""
    assert B.reads_masked_status('x | tail -1; echo "exit=$(tool >/dev/null 2>&1; echo $?)"') is False
    # A read that runs FIRST in its substitution still sees the pipe's status.
    assert B.reads_masked_status('x | tail -1; echo "exit=$(echo $?)"') is True


def test_a_filter_written_as_a_subshell_element_still_masks_the_gate(monkeypatch):
    """`gate | (tail -3)` runs tail in a subshell, and the subshell's status is still tail's."""
    assert B.masks_a_gate("pytest -q | tail -3") is True                          # control
    assert B.masks_a_gate("pytest -q | (tail -3)") is True
    assert run_main(monkeypatch, "pytest -q | ( tail -3 ) && git commit -m x") == 2


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
        ("gh run watch without --exit-status", "gh run watch 123"),
        ("a pipe into tee", "pytest tests/ -q | tee out.log"),
        ("an echo after &&", "make test && echo done"),
        ("a newline, then tail", "make test > log 2>&1\ntail log"),
        ("or-true", "make test || true"),
        ("a trailing ampersand", "make test > log 2>&1 &"),
        ("a second gate after the first", "make test; make lint"),
        ("ci_wait then a status echo", 'uv run ci_wait.py --sha deadbeef; echo "RC=$?"'),
    ],
)
def test_a_backgrounded_gate_without_the_jig_is_blocked(monkeypatch, capsys, label, command):
    """The completion notice reports the compound's last command, and that is what gets believed.

    The safe-redirect case is deliberately in this list. It is the form the memory entry
    recommends, and it is the exact command that produced the 2026-09-02 miss: written
    correctly, then misreported from the notice before the log was ever opened. Backgrounding
    is what makes the notice the thing you read, so the redirect does not rescue it. `gh run
    watch` is here with nothing after it because it exits 0 whatever the run concluded unless
    it is given --exit-status, so its own status is not a verdict either.
    """
    assert run_main_bg(monkeypatch, command, True) == 2
    assert "BLOCKED: a backgrounded gate" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("label", "command", "background"),
    [
        ("the jig itself", 'python3 scripts/gate.py --gate "make test" --then "git push"', True),
        # Wrongly launched, but still the jig: this guard is about the notice, not the launcher.
        ("the jig under uv run", "uv run scripts/gate.py --gate 'make test' --then 'git push'",
         True),
        ("foreground gate", 'make test > log 2>&1; echo "RC=$?" >> log', False),
        ("field absent entirely", "make test", None),
        ("backgrounded non-gate", "rsync -a src/ dst/ > sync.log 2>&1", True),
        # Nothing runs after the gate, so the task's exit code IS the gate's.
        ("make push alone", "make push ARGS='fix: x'", True),
        ("ci_wait alone, sha from a substitution",
         'python3 /p/skills/compuse-toolbox/scripts/ci_wait.py --sha "$(git rev-parse --verify HEAD)"',
         True),
        ("ci_wait after a cd", "cd /some/dir && uv run /p/scripts/ci_wait.py --sha deadbeef", True),
        ("gh run watch with --exit-status", "gh run watch 123 --exit-status", True),
        ("a lone redirected gate", "pytest tests/ -q > out.log 2>&1", True),
        ("a gate continued over two lines", "pytest tests/ \\\n  -q > out.log 2>&1", True),
        ("a trailing comment", "make test > log 2>&1  # the unit suite; slow", True),
        ("a trailing newline", "make test > log 2>&1\n", True),
    ],
)
def test_what_the_background_block_must_never_refuse(monkeypatch, label, command, background):
    """The allow-cases, which matter more than the block-cases for a hook that denies.

    `field absent entirely` pins the degradation direction: this guard reads a field that is
    doc-verified rather than probed here, so if a harness stops sending it the guard must go
    quiet, never start refusing every gate anyone runs.
    """
    assert run_main_bg(monkeypatch, command, background) == 0


# ---------------------------------------------------------------------------
# The remedy the block names must be one that works
# ---------------------------------------------------------------------------


def _suggested_jig_line(err):
    lines = [line.strip() for line in err.splitlines() if "gate.py" in line]
    assert lines, err
    return lines[0]


def test_the_background_block_launches_the_jig_the_way_the_jig_says(monkeypatch, capsys):
    """gate.py's own docstring: plain python3, NOT uv run - under uv run the gate inherits uv's
    isolated interpreter, so a `python3 -m pytest` gate reads RED. The block told a reader to
    run exactly that, as the one safe way out of the refusal it had just issued."""
    assert run_main_bg(monkeypatch, "pytest tests/ -q > out.log; tail out.log", True) == 2
    line = _suggested_jig_line(capsys.readouterr().err)
    assert not line.startswith("uv run"), line
    plain = "python" if os.name == "nt" else "python3"
    assert line.startswith(plain + " "), line


def test_the_background_block_and_the_nudge_name_the_same_launch(monkeypatch, capsys):
    """Two hooks name the jig; the pin keeps them from drifting apart again."""
    import toolbox_nudge as N  # noqa: PLC0415 - the sibling hook is the oracle for this test only

    assert run_main_bg(monkeypatch, "pytest tests/ -q > out.log; tail out.log", True) == 2
    line = _suggested_jig_line(capsys.readouterr().err)
    nudge_cmd, _note = N.launch_command(N._shipped_dir() / "gate.py")
    assert line.split()[0] == nudge_cmd.split()[0], (line, nudge_cmd)


def test_the_background_block_quotes_the_gate_the_way_every_platform_splits(monkeypatch, capsys):
    """gate.py: quote --gate with DOUBLE quotes - a Windows command line has no single-quoting, so
    `--gate '<cmd>'` arrives as broken argv there."""
    assert run_main_bg(monkeypatch, "pytest tests/ -q > out.log; tail out.log", True) == 2
    err = capsys.readouterr().err
    assert "--gate '" not in err and "--then '" not in err, err
    assert '--gate "' in err, err


def test_the_background_block_names_no_drive_relative_log_path(monkeypatch, capsys):
    """`/tmp/...` is DRIVE-RELATIVE on Windows (gate.py says so), and a fixed shared log name is
    the very hazard gate.py's fresh per-invocation default exists to remove."""
    assert run_main_bg(monkeypatch, "pytest tests/ -q > out.log; tail out.log", True) == 2
    err = capsys.readouterr().err
    assert "/tmp/" not in err, err
    assert "--log" not in _suggested_jig_line(err), err


@pytest.mark.parametrize("background", [True, False])
def test_the_jig_launched_under_uv_run_gets_an_advisory(monkeypatch, capsys, background):
    """gate.py declares LAUNCH_WITH = python3: under `uv run` a child `python3 -m pytest` gate
    resolves to uv's throwaway env and reads a false RED. Not a block - the result errs RED."""
    rc = run_main_bg(monkeypatch, 'uv run /p/scripts/gate.py --gate "make test"', background)
    assert rc == 0
    context = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "uv run" in context and "gate.py" in context


@pytest.mark.parametrize("command", [
    "uv run --with pytest python plugins/bitranox/hooks/repo-gate.py --ci > log 2>&1; tail log",
    "uv run --with pytest python -m pytest tests/test_gate.py > log 2>&1; tail log",
])
def test_a_file_merely_ending_in_gate_py_is_not_the_jig(monkeypatch, capsys, command):
    """`\\bgate\\.py` matched inside `repo-gate.py`, which both exempted a masked backgrounded
    gate as if it ran through the jig and drew the uv-run advisory for a different program."""
    assert run_main_bg(monkeypatch, command, True) == 2
    assert capsys.readouterr().out == ""


def test_the_jig_under_a_plain_interpreter_gets_no_advisory(monkeypatch, capsys):
    assert run_main_bg(monkeypatch, 'python3 /p/scripts/gate.py --gate "make test"', True) == 0
    assert capsys.readouterr().out == ""


def test_both_advisories_arrive_as_one_json_document(monkeypatch, capsys):
    """Claude Code reads ONE JSON document from a hook's stdout; two lines of JSON is neither."""
    command = 'foo | tail -3; echo "rc=$?"; uv run /p/scripts/gate.py --gate "make test"'
    assert run_main_bg(monkeypatch, command, False) == 0
    context = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "MASKED EXIT STATUS" in context and "uv run" in context


# ---------------------------------------------------------------------------
# Comments, `|&`, and the handled-status evidence (rank-10 re-adjudication)
# ---------------------------------------------------------------------------


def test_a_comment_line_after_a_piped_gate_is_not_a_consumer(monkeypatch):
    """A `#` comment is never executed, so `git commit` written in one commits nothing.

    The statement split read the comment line as a statement and CONSUMER matched its prose.
    """
    command = "ruff check . 2>&1 " + chr(124) + " tail -5\n# after this, never git commit on a red gate"
    assert _rc(monkeypatch, command) == 0


def test_a_comment_holding_a_separator_is_not_split_into_a_consumer(monkeypatch):
    command = "pytest -q " + chr(124) + " tail -3  # note; git commit when green"
    assert _rc(monkeypatch, command) == 0


def test_a_real_consumer_after_a_comment_still_blocks(monkeypatch):
    """The control: the comment is ignored, the real commit on the next line is not."""
    command = ("ruff check . 2>&1 " + chr(124) + " tail -5\n# after this, commit\n"
               "git commit -m x")
    assert _rc(monkeypatch, command) == 2


@pytest.mark.parametrize("claim", ['echo "PASS"', "echo 'PASS'", 'echo "CLIPPY-OK"'])
def test_a_quoted_success_claim_is_still_evidence(monkeypatch, claim):
    """Only comments are masked for CONSUMER: the claim IS a quoted string, in either quote."""
    assert _rc(monkeypatch, "cargo clippy 2>&1 " + chr(124) + " head -20 && " + claim) == 2


def test_a_pipe_ampersand_masks_a_gate_too(monkeypatch):
    """`|&` pipes stderr as well; the pipeline still exits with the filter's status."""
    command = 'cargo clippy -- -D warnings ' + chr(124) + '& head -20 && echo "CLIPPY-OK"'
    assert _rc(monkeypatch, command) == 2
    assert B.masks_a_gate("pytest -q " + chr(124) + "& tail -3") is True


def test_a_pipe_ampersand_into_the_gate_leaves_the_gate_last(monkeypatch):
    """The control: `|&` INTO the gate means the gate sets the status, as with a plain pipe."""
    assert B.masks_a_gate("echo hi " + chr(124) + "& pytest -q --stdin") is False


def test_the_status_advisory_sees_a_pipe_ampersand(monkeypatch, capsys):
    command = "mytool " + chr(124) + '& tail -5; echo "rc=$?"'
    assert B.reads_masked_status(command) is True
    assert run_main(monkeypatch, command) == 0
    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert "MASKED EXIT STATUS" in output["additionalContext"]


@pytest.mark.parametrize("prose", [
    'git commit -m "note: add pipefail later"',
    'git commit -m "note: check PIPESTATUS later"',
    "git commit -m x  # pipefail is on the todo list",
])
def test_the_word_pipefail_in_prose_is_not_the_fix(monkeypatch, prose):
    """HANDLED was searched on the raw command, so the word in a commit message disabled the block."""
    assert _rc(monkeypatch, "pytest -q " + chr(124) + " tail -3 && " + prose) == 2


@pytest.mark.parametrize("fix", [
    "set -o pipefail; pytest -q " + chr(124) + " tail -3 && git commit -m x",
    "set -euo pipefail\npytest -q " + chr(124) + " tail -3 && git commit -m x",
    "pytest -q " + chr(124) + ' tail -3; [ "${PIPESTATUS[0]}" -eq 0 ] && git commit -m x',
    "pytest -q " + chr(124) + " tail -3; test $PIPESTATUS -eq 0 && git commit -m x",
])
def test_the_real_pipe_status_fixes_still_allow(monkeypatch, fix):
    assert _rc(monkeypatch, fix) == 0


def test_the_status_advisory_ignores_pipefail_prose(monkeypatch):
    assert B.reads_masked_status('t ' + chr(124) + ' tail -1; echo "rc=$? (pipefail later)"') is True
    assert B.reads_masked_status('t ' + chr(124) + ' tail -1; echo "${PIPESTATUS[0]}"') is False


def test_advisory_json_names_the_pretooluse_event(monkeypatch, capsys):
    """Claude Code routes additionalContext by hookEventName; a wrong name drops the advisory."""
    assert run_main_bg(monkeypatch, 'uv run /p/scripts/gate.py --gate "make test"', False) == 0
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
