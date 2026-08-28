"""A gate runner must report the REAL exit status, never the status of a pipe element."""

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

import gate

# The suite used to reach for `true`, `false`, `env` and `touch` as throwaway gate commands.
# None of them exists on Windows - they came from Git-for-Windows' usr/bin, which is on the
# CI runner's PATH but not on a plain Windows install, so those tests passed on CI while
# failing on a real user's machine: the environment, not the subject, decided the verdict.
# These stand-ins run the interpreter already running the suite, so they exist everywhere.
OK_ARGV = [sys.executable, "-c", ""]
FAIL_ARGV = [sys.executable, "-c", "raise SystemExit(1)"]

def quoted(*argv):
    """One command string that gate's splitter parses back to exactly `argv`, on either platform.

    NOT shlex.quote on Windows. It single-quotes, and a Windows command line has no such thing:
    CommandLineToArgvW reads a single quote as an ordinary character, so the path would arrive
    with quotes glued on and split at its spaces anyway. list2cmdline is that parser's inverse,
    which is exactly what this needs to be.
    """
    if os.name == "nt":
        return subprocess.list2cmdline(list(argv))
    return " ".join(shlex.quote(a) for a in argv)


# ...and the same two as ONE shell-quoted string, for the --gate route.
OK = quoted(sys.executable, "-c", "")
FAIL = quoted(sys.executable, "-c", "raise SystemExit(1)")


def write_exit_zero_script(path_without_suffix):
    """Create a directly-executable do-nothing script, named with a SPACE, and return its path.

    A `#!/bin/sh` file is not executable on Windows (WinError 193: not a valid Win32
    application), but the subject under test - that a lone `--` positional is never re-split -
    matters MOST there, since a path with a space in it is the norm on Windows rather than the
    exception. So the script's form follows the platform while the test's subject does not.
    """
    if os.name == "nt":
        script = path_without_suffix.with_suffix(".cmd")
        script.write_text("@exit /b 0\r\n", encoding="utf-8")
        return script
    script = path_without_suffix.with_suffix(".sh")
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def test_a_failing_gate_is_failed_even_when_its_output_looks_successful(tmp_path):
    """The whole point. `cargo test | grep "test result"` exits with grep's status, so a red
    gate whose log still contains a green-looking line reads as success and the `&&` fires.
    """
    log = tmp_path / "g.log"
    rep = gate.run_gates(
        [("fake", [sys.executable, "-c", "print('test result: ok. 5 passed'); raise SystemExit(1)"])],
        log,
        summary=r"test result",
    )
    assert rep.ok is False
    assert rep.results[0].returncode == 1
    assert "test result: ok. 5 passed" in rep.results[0].summary_lines[0]


def test_a_passing_gate_is_ok_and_its_summary_line_is_extracted(tmp_path):
    log = tmp_path / "g.log"
    rep = gate.run_gates(
        [("ok", [sys.executable, "-c", "print('test result: ok. 3 passed')"])],
        log,
        summary=r"test result",
    )
    assert rep.ok is True
    assert rep.results[0].returncode == 0
    assert rep.results[0].summary_lines == ["test result: ok. 3 passed"]


def test_every_gate_runs_and_one_red_fails_the_whole_report(tmp_path):
    log = tmp_path / "g.log"
    rep = gate.run_gates(
        [
            ("first", [sys.executable, "-c", "print('a')"]),
            ("second", [sys.executable, "-c", "raise SystemExit(3)"]),
        ],
        log,
    )
    assert rep.ok is False
    assert [r.returncode for r in rep.results] == [0, 3]


def test_the_log_keeps_every_gates_output_for_later_reading(tmp_path):
    log = tmp_path / "g.log"
    gate.run_gates([("one", [sys.executable, "-c", "print('HELLO-FROM-GATE')"])], log)
    assert "HELLO-FROM-GATE" in log.read_text(encoding="utf-8")


def test_a_missing_executable_is_a_failure_not_a_crash(tmp_path):
    log = tmp_path / "g.log"
    rep = gate.run_gates([("nope", ["definitely-not-a-real-binary-xyz"])], log)
    assert rep.ok is False
    assert rep.results[0].returncode != 0


def test_a_gate_wrapped_in_env_is_not_named_env(tmp_path):
    """Found in use: `--gate "env -u VIRTUAL_ENV uv run pytest"` reported as [PASS] env.

    argv[0] is a wrapper (env/uv/xargs/timeout) far more often than it is the thing under
    test, so a report keyed on it says nothing about which gate ran.
    """
    name, argv = gate.gate_spec("env -u VIRTUAL_ENV uv run --extra dev pytest -q")
    assert name != "env"
    assert "pytest" in name


def test_an_explicit_name_wins(tmp_path):
    """The documented, working form: a single-word label before '='."""
    name, argv = gate.gate_spec("unit=cargo test -p net_tap --lib")
    assert name == "unit"
    assert argv[0] == "cargo"


def test_a_plain_command_keeps_a_readable_name(tmp_path):
    name, argv = gate.gate_spec("cargo test -p net_tap --lib")
    assert name.startswith("cargo test")
    assert argv[:2] == ["cargo", "test"]


def test_a_multiword_head_before_equals_is_never_treated_as_a_label(tmp_path):
    """Found in use (2026-07-28): `env -u VIRTUAL_ENV BMK_PYTHON_CMD=/path/.venv/bin/python
    make test` carries a genuine env-assignment ('BMK_PYTHON_CMD=...') inside an env-wrapped
    command. Partitioning on that first '=' gives head "env -u VIRTUAL_ENV BMK_PYTHON_CMD" -
    non-empty, no leading '-', no '/', so the old guard accepted it as the LABEL and left
    "/path/.venv/bin/python make test" as the gate. The interpreter then tried to open a file
    literally named "make" and died - reported as a genuine-looking FAIL for what was really a
    parsing mistake, exactly the misattribution this tool exists to prevent.

    A real label is one word ("unit", "lint"); a multi-word head is the START of a command,
    never a name, so the whole spec must be kept and run verbatim as argv.
    """
    spec = "env -u VIRTUAL_ENV BMK_PYTHON_CMD=/path/to/.venv/bin/python make test"
    name, argv = gate.gate_spec(spec)
    assert argv == ["env", "-u", "VIRTUAL_ENV", "BMK_PYTHON_CMD=/path/to/.venv/bin/python", "make", "test"]
    assert name != "env -u VIRTUAL_ENV BMK_PYTHON_CMD"


@pytest.mark.skipif(
    os.name == "nt",
    reason="the SUBJECT is a real POSIX `env` binary applying VAR=value itself with no shell; "
           "Windows has no such program, so there is nothing to run the assignment through. "
           "The portable half of this - that gate_spec never carves a label out of a command "
           "carrying its own '=' - is asserted on argv shape by "
           "test_a_multiword_head_before_equals_is_never_treated_as_a_label, which runs "
           "everywhere.",
)
def test_an_env_wrapped_assignment_actually_runs_and_sees_its_value(tmp_path):
    """End-to-end proof, not just argv shape: run the mis-split-prone form through a real
    `env` binary (no shell) and confirm the assignment reaches the child process untouched -
    i.e. gate_spec never carved a label out of the command, and no shell was needed for `env`
    to apply MARKER itself.
    """
    log = tmp_path / "g.log"
    spec = (
        f'env MARKER=hello {sys.executable} -c '
        '"import os, sys; sys.exit(0 if os.environ.get(\'MARKER\') == \'hello\' else 1)"'
    )
    name, argv = gate.gate_spec(spec)
    rep = gate.run_gates([(name, argv)], log)
    assert rep.ok is True, log.read_text(encoding="utf-8")


def test_a_gate_string_naming_the_real_interpreter_actually_runs_it(tmp_path):
    r"""The realistic Windows case, and the one that was broken: an interpreter path holds
    backslashes and usually a space (C:\Program Files\...). gate_spec shlex-split it in POSIX
    mode, where a backslash is an ESCAPE, so the path came apart into 'C:Program' +
    'FilesPythonpython.exe', the gate ran a binary that does not exist and reported rc=127 -
    a FALSE RED for a command that passes, which is the misattribution this tool exists to
    prevent. Portable on purpose: on POSIX it is a plain regression guard.
    """
    log = tmp_path / "g.log"
    name, argv = gate.gate_spec(OK)
    assert argv[0] == sys.executable, "the interpreter path did not survive splitting"
    rep = gate.run_gates([(name, argv)], log)
    assert rep.ok is True, log.read_text(encoding="utf-8")


@pytest.mark.skipif(os.name != "nt", reason="describes how a backslash is read ON Windows, "
                                            "where it is a path separator and not an escape")
def test_on_windows_a_backslash_is_a_path_separator_not_an_escape():
    r"""The unquoted form a Windows user actually types. Nobody doubles a backslash there, so
    escape processing must be off or every bare path silently loses its separators."""
    assert gate.split_command(r"C:\Tools\py.exe -c print(1)") == [r"C:\Tools\py.exe", "-c", "print(1)"]


@pytest.mark.skipif(os.name == "nt", reason="asserts the POSIX escape semantics callers rely "
                                            "on there, which Windows deliberately does not share")
def test_on_posix_a_backslash_still_escapes():
    """The Windows fix must not quietly change POSIX behaviour: a backslash-escaped space
    still joins one argument here."""
    assert gate.split_command(r"esc\ aped x") == ["esc aped", "x"]


def test_a_flag_looking_head_is_never_split_into_a_label(tmp_path):
    """Guard: a leading '-' before '=' is an option (`--flag=value`), never a label. A bare
    `name != "<head>"` passes for nearly any wrong return value too (e.g. an empty name with
    a mangled argv), so assert the actual argv stays the whole spec, unsplit."""
    name, argv = gate.gate_spec("--flag=value")
    assert name != "--flag"
    assert argv == ["--flag=value"]
    assert name == "--flag=value"


def test_a_path_looking_head_is_never_split_into_a_label(tmp_path):
    """Guard: a '/' before '=' means the head is a path, never a label."""
    name, argv = gate.gate_spec("path/to/bin=arg")
    assert name != "path/to/bin"
    assert argv == ["path/to/bin=arg"]
    assert name == "path/to/bin=arg"


class TestFollowUpAndArgParsing:
    """Both bugs here were hit in real use on 2026-07-27, one masking the other."""

    def test_a_compound_follow_up_runs_every_command(self, tmp_path):
        """`--then "git add X && git commit"` must run BOTH, not hand git a literal '&&'.

        shlex.split turns the operator into an argv element, so git received `&&` as a
        pathspec and the commit never ran while the tool reported the follow-up's status.
        A follow-up is the user's own command, so it is the one place a shell is correct -
        the tool's guarantee is that the GATE's status is never masked, not that the
        follow-up avoids a shell.
        """
        a, b = tmp_path / "a", tmp_path / "b"
        rc = gate.main([
            "--gate", OK, "--log", str(tmp_path / "g.log"),
            "--then", f"echo one > {a} && echo two > {b}",
        ])
        assert rc == 0
        # Redirection is pure shell: with no shell, echo prints the whole rest of the line
        # as text and neither file appears. `touch A && touch B` is NOT a valid probe here -
        # touch takes many operands, so it creates a file literally named "&&" and passes
        # while the bug is still present.
        assert a.exists() and b.exists(), "a compound follow-up must run every command"
        assert not (tmp_path / "&&").exists(), "the shell operator leaked through as an argument"

    def test_a_red_gate_still_blocks_a_compound_follow_up(self, tmp_path):
        a = tmp_path / "a"
        rc = gate.main([
            "--gate", FAIL, "--log", str(tmp_path / "g.log"),
            "--then", f"touch {a} && touch {a}-2",
        ])
        assert rc == 1
        assert not a.exists(), "a red gate must block the follow-up, compound or not"

    def test_a_bare_positional_gate_does_not_swallow_later_options(self, tmp_path):
        """argparse.REMAINDER ate `--then` and its value into one nonsense gate.

        It reported FAIL rc=127 naming the whole command line, which reads like a broken gate
        rather than the mis-parse it was. The quoted form must leave later options alone: the
        gate here is `false`, so the follow-up must be BLOCKED - which proves --then was
        parsed as an option rather than glued onto the gate.

        Do NOT write this probe as a gate that shells out to pytest: with the bug present it
        spawned a RECURSIVE pytest run and the suite hung instead of failing.
        """
        marker = tmp_path / "ran"
        rc = gate.main([FAIL, "--then", f"touch {marker}", "--log", str(tmp_path / "g.log")])
        assert rc == 1
        assert not marker.exists(), "--then was swallowed into the gate instead of parsed"

    def test_a_single_bare_positional_is_still_accepted_as_a_gate(self, tmp_path):
        rc = gate.main([OK, "--log", str(tmp_path / "g.log")])
        assert rc == 0

    def test_a_dashdash_positional_gate_is_named_by_its_command_not_by_argv0(self, tmp_path, capsys):
        """Review finding (2026-07-28): `-- <cmd ...>` named the gate `args.rest[0]`, so
        `-- env -u VIRTUAL_ENV make --version` reported `[FAIL] env (rc=2)` - the report names
        the wrapper, not the thing under test. gate_spec's docstring rejects naming by argv[0]
        for exactly this reason and the single-string route already obeys it; the two routes
        must derive the name the same way, or the module's own first Run: example lies."""
        argv = [*OK_ARGV, "a-trailing-token"]
        rc = gate.main(["--log", str(tmp_path / "g.log"), "--", *argv])
        assert rc == 0
        out = capsys.readouterr().out
        # The end-to-end half asserts only that main labels the gate through derived_name.
        # It deliberately does NOT assert "argv[0] is absent": derived_name truncates at
        # _NAME_WIDTH, and on a machine where the interpreter path happens to be that long the
        # truncated name IS argv[0], so such an assertion would turn on the length of a path
        # rather than on the rule. The rule itself is pinned deterministically below.
        assert f"[PASS] {gate.derived_name(argv)} (rc=" in out

    def test_the_derived_name_is_the_whole_command_never_argv0(self):
        """The rule the report line depends on, pinned where no path length can reach it:
        `-- env -u VIRTUAL_ENV make --version` reported "[FAIL] env (rc=2)", naming the wrapper
        instead of the thing under test."""
        assert gate.derived_name(["env", "-u", "VIRTUAL_ENV", "make"]) == "env -u VIRTUAL_ENV make"
        assert gate.derived_name(["env", "-u", "VIRTUAL_ENV", "make"]) != "env"

    def test_a_dashdash_positional_token_holding_a_space_is_not_re_split(self, tmp_path, capsys):
        """Review finding (2026-07-28, round 4): `-- <cmd ...>` positionals are already real argv
        tokens, but a LONE one was handed back to shlex.split, so a path with a space in it
        (`-- '/path/my gate.sh'`) came apart into '/path/my' + 'gate.sh' and ran as '/path' -
        `[FAIL] /path (rc=127)`, a FALSE RED for a script that exits 0. That is the
        misattribution this whole tool exists to prevent, produced by the tool itself."""
        script = write_exit_zero_script(tmp_path / "my gate")
        rc = gate.main(["--log", str(tmp_path / "g.log"), "--", str(script)])
        assert rc == 0, capsys.readouterr().out
        assert "[PASS]" in capsys.readouterr().out

    def test_a_dashdash_gates_verdict_does_not_change_when_an_argument_is_added(self, tmp_path, capsys):
        """The finding's sharpest form: the SAME script passed or failed depending on whether a
        second, unrelated token followed it, because one positional took the shlex route and two
        took the argv route. A verdict must never turn on an argument the gate ignores."""
        script = write_exit_zero_script(tmp_path / "my gate")
        alone = gate.main(["--log", str(tmp_path / "g.log"), "--", str(script)])
        capsys.readouterr()
        with_arg = gate.main(["--log", str(tmp_path / "g.log"), "--", str(script), "ignored-arg"])
        capsys.readouterr()
        assert alone == with_arg == 0

    def test_both_ways_of_writing_one_command_derive_the_same_name(self, tmp_path):
        """derived_name's docstring claims the two routes cannot label the same command two ways.
        The re-split made that false in the other direction too: pin it as an assertion."""
        spec = "/opt/bin/run gate --verbose"
        from_string, argv_from_string = gate.gate_spec(spec)
        from_tokens = gate.derived_name(argv_from_string)
        assert from_string == from_tokens

    def test_a_dashdash_positional_gate_can_still_be_named_explicitly(self, tmp_path, capsys):
        """The derived name is only the default; --name still wins for the positional route."""
        rc = gate.main(["--name", "unit tests", "--log", str(tmp_path / "g.log"),
                        "--", *OK_ARGV])
        assert rc == 0
        assert "[PASS] unit tests" in capsys.readouterr().out


class TestExplicitNameOption:
    """Found in use (2026-07-28): the single-word-label rule in gate_spec (see
    test_a_multiword_head_before_equals_is_never_treated_as_a_label) is correct and must stay -
    a multi-word head before '=' is syntactically identical to an env-assignment command
    prefix, and defaulting to 'it is a command' is the safe direction. But that narrowing took
    away the only way to give a gate a label with spaces, with no replacement, and a spec that
    used to work (`unit tests=cargo test -p net_tap --lib`) now mis-splits into a broken argv
    and reports a FALSE RED - exactly the misattribution this tool exists to prevent, just
    moved to a different spec shape. --name is the replacement: it never touches the command
    string at all, so it cannot mis-split anything.
    """

    def test_name_option_gives_a_multiword_label_without_mangling_the_command(self, tmp_path, capsys):
        log = tmp_path / "g.log"
        rc = gate.main([
            "--gate", f'{sys.executable} -c "print(1)"',
            "--name", "unit tests",
            "--log", str(log),
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "unit tests" in out
        assert "[PASS] unit tests" in out

    def test_name_option_pairs_positionally_with_multiple_gates(self, tmp_path, capsys):
        log = tmp_path / "g.log"
        rc = gate.main([
            "--gate", OK, "--name", "first gate",
            "--gate", OK, "--name", "second gate",
            "--log", str(log),
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "[PASS] first gate" in out
        assert "[PASS] second gate" in out

    def test_more_names_than_gates_is_a_usage_error_not_a_silent_mismatch(self, tmp_path, capsys):
        """A stray extra --name would otherwise pair with nothing and hide a mismatch; fail
        loudly (a usage error) instead of mislabeling a gate.

        Asserting a bare SystemExit was not a regression test: it passed against the pre-fix
        code for the wrong reason (argparse rejecting an option it did not know, also exit 2),
        so it could not tell a working guard from a missing one. Pin the exit CODE (2, the
        argparse usage-error convention, distinct from 1 = a red gate) and the message.
        """
        with pytest.raises(SystemExit) as exc:
            gate.main([
                "--gate", OK, "--name", "one", "--name", "two",
                "--log", str(tmp_path / "g.log"),
            ])
        assert exc.value.code == 2
        assert "more --name than --gate" in capsys.readouterr().err

    def test_a_name_labels_the_gate_written_before_it_not_the_first_one(self, tmp_path, capsys):
        """Regression (2026-07-28, review round 2): argparse keeps --gate and --name in two
        INDEPENDENT lists, so the order they were written in is lost. Pairing them by list
        index made `--gate true --gate false --name smoke` label the FIRST gate 'smoke' - the
        label ends up on a gate the user never named, and on the gate with the opposite result.
        Mislabeling a result is precisely the failure mode this tool exists to prevent.
        """
        rc = gate.main([
            "--gate", OK,
            "--gate", FAIL, "--name", "smoke",
            "--log", str(tmp_path / "g.log"),
        ])
        assert rc == 1                                     # the second gate is red
        out = capsys.readouterr().out
        assert "[FAIL] smoke" in out, "the name belongs to the gate it was written after"
        assert "[PASS] smoke" not in out, "the name landed on the wrong gate"
        assert f"[PASS] {gate.gate_spec(OK)[0]}" in out, "the unnamed gate keeps its derived name"

    def test_fewer_names_than_gates_leaves_the_later_gates_with_their_derived_name(self, tmp_path, capsys):
        """A name is optional per gate; the gates after the last named one are not shifted or
        left blank, they simply keep the name derived from their command."""
        rc = gate.main([
            "--gate", OK, "--name", "first gate",
            "--gate", OK,
            "--log", str(tmp_path / "g.log"),
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "[PASS] first gate" in out
        assert f"[PASS] {gate.gate_spec(OK)[0]}" in out

    def test_a_name_written_before_any_gate_is_a_usage_error_with_an_accurate_message(self, tmp_path, capsys):
        """Written order is the whole rule, so a --name with no --gate in front of it has
        nothing to label. Say THAT, rather than counting names against gates (which would be a
        wrong description of this mistake)."""
        with pytest.raises(SystemExit) as exc:
            gate.main([
                "--name", "orphan", "--gate", OK,
                "--log", str(tmp_path / "g.log"),
            ])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "AFTER" in err
        assert "more --name than --gate" not in err, "that would misdescribe the mistake"

    def test_a_positional_gate_can_be_labeled_by_a_name(self, tmp_path, capsys):
        """Found in use (2026-07-28): `gate.py --name "unit tests" -- true` exited 2 claiming
        more names than gates, although a gate WAS given - the positional form was simply not
        counted. With exactly one gate and one name there is nothing to pair ambiguously, so
        the name applies."""
        rc = gate.main(["--name", "unit tests", "--log", str(tmp_path / "g.log"), "--", *OK_ARGV])
        assert rc == 0
        assert "[PASS] unit tests" in capsys.readouterr().out

    def test_a_single_quoted_positional_gate_can_be_labeled_by_a_name(self, tmp_path, capsys):
        rc = gate.main(["--name", "unit tests", "--log", str(tmp_path / "g.log"), OK])
        assert rc == 0
        assert "[PASS] unit tests" in capsys.readouterr().out

    def test_two_names_for_one_positional_gate_is_still_a_usage_error(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            gate.main(["--name", "one", "--name", "two", "--log", str(tmp_path / "g.log"), OK])
        assert exc.value.code == 2
        assert "more --name than --gate" in capsys.readouterr().err

    def test_a_name_before_a_gate_option_is_rejected_even_with_a_positional_gate(self, tmp_path, capsys):
        """The one shape that IS ambiguous: with both a --gate and a positional gate present, a
        leading --name could plausibly mean either, so it is refused rather than guessed."""
        with pytest.raises(SystemExit) as exc:
            gate.main(["--name", "which one", "--gate", OK,
                       "--log", str(tmp_path / "g.log"), "--", *OK_ARGV])
        assert exc.value.code == 2
        assert "AFTER" in capsys.readouterr().err

    def test_an_empty_name_is_rejected_instead_of_occupying_a_pairing_slot(self, tmp_path, capsys):
        """Review finding (2026-07-28): `--name ""` was stored as the gate's name, then dropped
        again at report time by `explicit or derived`, so it labeled nothing while still filling
        the gate's one pairing slot. A following --name then failed with 'more --name than
        --gate' although exactly one effective name had been given - a message describing a
        mistake the user did not make. An empty label can never be useful, so it is refused at
        the point it is written, with a message that says so."""
        with pytest.raises(SystemExit) as exc:
            gate.main(["--gate", OK, "--name", "", "--log", str(tmp_path / "g.log")])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "empty" in err
        assert "more --name than --gate" not in err, "that would misdescribe the mistake"

    def test_an_empty_name_followed_by_a_real_one_reports_the_empty_name_not_a_count(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            gate.main(["--gate", OK, "--name", "", "--name", "y", "--log", str(tmp_path / "g.log")])
        assert exc.value.code == 2
        assert "empty" in capsys.readouterr().err

    def test_a_whitespace_only_name_is_rejected_too(self, tmp_path, capsys):
        """A blank label prints as a nameless gate, which is the same unreadable report."""
        with pytest.raises(SystemExit) as exc:
            gate.main(["--gate", OK, "--name", "   ", "--log", str(tmp_path / "g.log")])
        assert exc.value.code == 2
        assert "empty" in capsys.readouterr().err

    def test_gate_help_states_that_an_empty_name_is_rejected(self, capsys):
        with pytest.raises(SystemExit):
            gate.main(["--help"])
        flat = " ".join(capsys.readouterr().out.split())
        assert "empty" in flat

    def test_gate_help_documents_the_name_equals_command_form_and_its_constraint(self, capsys):
        """Before this fix, --help never mentioned the label form at all - only the module
        docstring did, which a user running --help never sees."""
        with pytest.raises(SystemExit):
            gate.main(["--help"])
        out = capsys.readouterr().out
        assert "name=command" in out
        assert "--name" in out


def emit(text: str, code: int = 0):
    """A gate that prints `text` and exits `code` - a REAL subprocess, nothing stubbed.

    The count is read off a gate's own output, so the test has to produce that output the way a
    gate does. Handing the string straight to `observed_test_count` would skip the capture, the
    decoding and the stdout/stderr join that sit between a runner's line and the verdict, and
    those are where a count gets lost.
    """
    return [sys.executable, "-c", f"print({text!r}); raise SystemExit({code})"]


def log_path_in(report_text: str) -> str:
    """The path the report says it wrote to. That line is the ONLY pointer a reader is given."""
    for line in report_text.splitlines():
        if line.startswith("log: "):
            return line[len("log: "):].strip()
    raise AssertionError(f"no 'log:' line in report:\n{report_text}")


class TestThePerInvocationDefaultLog:
    """A fixed default log is SHARED, and gates APPEND to it.

    So two runs at once - parallel agents, two worktrees, one CI matrix - interleave into a
    single file, and whoever reads it back attributes the other run's lines to the run they just
    watched. Observed 2026-07-29: a PASS was read beside another worktree's log. Nothing in the
    report shows it, because the `log:` line names the same path either way. That is the same
    "a correct exit status still proves nothing" failure this tool exists to prevent, arriving
    through the log instead of through a pipe.
    """

    @pytest.fixture(autouse=True)
    def _default_log_into_tmp(self, tmp_path, monkeypatch):
        """Keep the suite from littering the real temp dir with a file per test.

        Patches tempfile's OWN `tempdir` global rather than anything in gate: mkstemp resolves
        the directory through `gettempdir()` at call time, so this steers the real code path
        instead of replacing it, and it is a seam that exists whichever version of gate.py is
        imported - a fixture that patched a name only the FIXED gate.py defines would make this
        class error in setup against the old one, which proves the symbol is absent and not that
        the behaviour is wrong.
        """
        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    def test_two_default_paths_taken_in_one_process_are_different_files(self):
        """A 'per-invocation' default that hands back the same name twice is the shared default
        again under a new name. mkstemp also CREATES each one, so these are not merely two
        strings that differ: neither run can be given a name the other already holds."""
        first, second = gate.default_log_path(), gate.default_log_path()
        assert first != second

    def test_two_runs_that_pass_no_log_option_report_two_different_paths(self, capsys):
        first_rc = gate.main(["--gate", OK])
        first = log_path_in(capsys.readouterr().out)
        second_rc = gate.main(["--gate", OK])
        second = log_path_in(capsys.readouterr().out)
        assert first_rc == 0 and second_rc == 0
        assert first != second

    def test_one_runs_log_does_not_hold_another_runs_output(self, capsys):
        """The defect itself rather than the path it hides behind.

        Asserted against the LOG FILE on purpose. `--summary` is extracted from the gate's own
        captured stdout and never reads the log, so a summary-based version of this test passes
        even against the shared default and would prove nothing - the first assertion below is
        the premise check that keeps this one honest.
        """
        gate.main(["--gate", quoted(*emit("MARKER-FROM-RUN-A"))])
        first_log = Path(log_path_in(capsys.readouterr().out))
        gate.main(["--gate", quoted(*emit("run B says nothing of interest"))])
        second_log = Path(log_path_in(capsys.readouterr().out))
        assert "MARKER-FROM-RUN-A" in first_log.read_text(encoding="utf-8"), \
            "premise: run A's output really did reach run A's log"
        assert "MARKER-FROM-RUN-A" not in second_log.read_text(encoding="utf-8"), \
            "run B's log holds run A's output, so a reader cannot tell whose result it is"


def test_an_explicit_log_option_still_pins_the_path(tmp_path, capsys):
    """Control: `--log` is how a caller reads the log afterwards, so it has to survive the
    change of default. Deliberately OUTSIDE TestThePerInvocationDefaultLog: a control belongs
    where no fixture of the thing under test can decide whether it runs."""
    wanted = tmp_path / "mine.log"
    rc = gate.main(["--gate", OK, "--log", str(wanted)])
    assert rc == 0
    assert log_path_in(capsys.readouterr().out) == str(wanted)
    assert wanted.exists()


def test_the_default_log_path_is_absolute():
    r"""'/tmp/gate.log' is DRIVE-RELATIVE on Windows, not absolute: Path reads it as
    \tmp\gate.log, so the log landed on whichever drive happened to be current and the
    'log: ...' line named a path the user could not open. Carried over from the fixed-path
    era - the default moved, and this property has to move with it."""
    assert Path(gate.default_log_path()).is_absolute()


class TestAZeroTestGateIsRefused:
    """A filter that matches NOTHING exits 0.

    `pytest -k <typo>` and `cargo test <prefix no test starts with>` each run zero tests and
    return success, so the status reports green about work that never happened - and a renamed
    or moved test quietly turns a gate into a no-op that keeps passing forever after.
    """

    def test_a_cargo_run_that_matched_no_test_is_refused_though_it_exited_zero(self, tmp_path):
        rep = gate.run_gates([("unit", emit("running 0 tests"))], tmp_path / "g.log")
        assert rep.results[0].returncode == 0, "the premise: the gate itself did succeed"
        assert rep.results[0].test_count == 0
        assert rep.ok is False

    def test_a_pytest_filter_that_deselected_everything_is_refused(self, tmp_path):
        """The number that must NOT be believed here is `collected`. On a total deselection it
        still reads 300, so anyone reading that alone calls the empty run a 300-test pass."""
        line = "collected 300 items / 300 deselected / 0 selected"
        rep = gate.run_gates([("unit", emit(line))], tmp_path / "g.log")
        assert rep.results[0].test_count == 0
        assert rep.ok is False

    def test_pytests_quiet_wording_for_an_empty_run_is_refused(self, tmp_path):
        """Under -q pytest prints no counts at all, only this sentence."""
        rep = gate.run_gates([("unit", emit("no tests ran in 0.01s"))], tmp_path / "g.log")
        assert rep.results[0].test_count == 0
        assert rep.ok is False

    def test_a_zero_test_gate_blocks_the_follow_up_and_exits_red(self, tmp_path):
        """End to end through main(): the `--then` is the thing that must not fire, since the
        whole tool exists so that a red state never gets pushed."""
        marker = tmp_path / "pushed"
        rc = gate.main(["--gate", quoted(*emit("running 0 tests")),
                        "--log", str(tmp_path / "g.log"), "--then", f"touch {marker}"])
        assert rc == 1
        assert not marker.exists(), "a gate that ran no tests let the follow-up fire"


class TestTheObservedCountIsReported:
    """A count nobody is shown cannot be sanity-checked, so it is printed for every recognised
    test run and not only for the zero that gets refused: a suite that HALVES is the next
    failure along, and the status stays green through all of it."""

    def test_the_count_appears_in_the_report_for_a_healthy_run(self, tmp_path):
        rep = gate.run_gates([("unit", emit("running 7 tests"))], tmp_path / "g.log")
        assert rep.results[0].test_count == 7
        assert rep.ok is True
        assert "7 tests" in gate.format_report(rep, tmp_path / "g.log")

    def test_a_refused_run_says_it_ran_zero_and_why(self, tmp_path):
        rep = gate.run_gates([("unit", emit("running 0 tests"))], tmp_path / "g.log")
        text = gate.format_report(rep, tmp_path / "g.log")
        assert "[FAIL]" in text
        assert "0 tests" in text

    def test_cargo_counts_sum_over_every_test_binary(self):
        """libtest prints one `running N tests` per BINARY. A workspace whose lib tests ran and
        whose integration binary matched nothing has still run tests, so these add up rather
        than the last line winning."""
        assert gate.observed_test_count("running 2 tests\nok\nrunning 3 tests\n") == 5

    def test_a_gate_that_is_not_a_test_runner_is_classified_as_having_no_count(self, tmp_path):
        """None and 0 are different answers: None is 'not a test run', judged on the exit status
        as before, while 0 is 'a test run that ran nothing'. Collapsing the two would fail every
        lint gate in every caller's pipeline."""
        rep = gate.run_gates([("lint", emit("All checks passed!"))], tmp_path / "g.log")
        assert rep.results[0].test_count is None


class TestNonTestGatesKeepPassing:
    """Controls for the over-reach this refusal could cause. Both pass BEFORE and after the
    change, which is what makes them controls rather than more of the same assertion."""

    def test_a_gate_that_is_not_a_test_runner_still_passes(self, tmp_path):
        rep = gate.run_gates([("lint", emit("All checks passed!"))], tmp_path / "g.log")
        assert rep.ok is True

    def test_a_linter_reporting_zero_errors_is_not_read_as_a_zero_test_run(self, tmp_path):
        """The false red a looser matcher would produce. `Found 0 errors.` is a linter
        SUCCEEDING, and a rule that counts any `0 <word>` as an empty test run turns every clean
        lint run into a gate failure."""
        rep = gate.run_gates([("lint", emit("Found 0 errors."))], tmp_path / "g.log")
        assert rep.ok is True
