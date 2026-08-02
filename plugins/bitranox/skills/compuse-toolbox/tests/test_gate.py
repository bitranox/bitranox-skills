"""A gate runner must report the REAL exit status, never the status of a pipe element."""

import sys

import pytest

import gate


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
            "--gate", "true", "--log", str(tmp_path / "g.log"),
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
            "--gate", "false", "--log", str(tmp_path / "g.log"),
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
        rc = gate.main(["false", "--then", f"touch {marker}", "--log", str(tmp_path / "g.log")])
        assert rc == 1
        assert not marker.exists(), "--then was swallowed into the gate instead of parsed"

    def test_a_single_bare_positional_is_still_accepted_as_a_gate(self, tmp_path):
        rc = gate.main(["true", "--log", str(tmp_path / "g.log")])
        assert rc == 0

    def test_a_dashdash_positional_gate_is_named_by_its_command_not_by_argv0(self, tmp_path, capsys):
        """Review finding (2026-07-28): `-- <cmd ...>` named the gate `args.rest[0]`, so
        `-- env -u VIRTUAL_ENV make --version` reported `[FAIL] env (rc=2)` - the report names
        the wrapper, not the thing under test. gate_spec's docstring rejects naming by argv[0]
        for exactly this reason and the single-string route already obeys it; the two routes
        must derive the name the same way, or the module's own first Run: example lies."""
        rc = gate.main([
            "--log", str(tmp_path / "g.log"),
            "--", "env", "-u", "VIRTUAL_ENV", sys.executable, "-c", "print('ok')",
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "[PASS] env (rc=" not in out, "the gate was named after its wrapper"
        assert "[PASS] env -u VIRTUAL_ENV" in out

    def test_a_dashdash_positional_token_holding_a_space_is_not_re_split(self, tmp_path, capsys):
        """Review finding (2026-07-28, round 4): `-- <cmd ...>` positionals are already real argv
        tokens, but a LONE one was handed back to shlex.split, so a path with a space in it
        (`-- '/path/my gate.sh'`) came apart into '/path/my' + 'gate.sh' and ran as '/path' -
        `[FAIL] /path (rc=127)`, a FALSE RED for a script that exits 0. That is the
        misattribution this whole tool exists to prevent, produced by the tool itself."""
        script = tmp_path / "my gate.sh"
        script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        script.chmod(0o755)
        rc = gate.main(["--log", str(tmp_path / "g.log"), "--", str(script)])
        assert rc == 0, capsys.readouterr().out
        assert "[PASS]" in capsys.readouterr().out

    def test_a_dashdash_gates_verdict_does_not_change_when_an_argument_is_added(self, tmp_path, capsys):
        """The finding's sharpest form: the SAME script passed or failed depending on whether a
        second, unrelated token followed it, because one positional took the shlex route and two
        took the argv route. A verdict must never turn on an argument the gate ignores."""
        script = tmp_path / "my gate.sh"
        script.write_text('#!/bin/sh\nexit 0\n', encoding="utf-8")
        script.chmod(0o755)
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
                        "--", "env", "true"])
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
            "--gate", "true", "--name", "first gate",
            "--gate", "true", "--name", "second gate",
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
                "--gate", "true", "--name", "one", "--name", "two",
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
            "--gate", "true",
            "--gate", "false", "--name", "smoke",
            "--log", str(tmp_path / "g.log"),
        ])
        assert rc == 1                                     # the second gate is red
        out = capsys.readouterr().out
        assert "[FAIL] smoke" in out, "the name belongs to the gate it was written after"
        assert "[PASS] smoke" not in out, "the name landed on the wrong gate"
        assert "[PASS] true" in out, "the unnamed gate keeps its derived name"

    def test_fewer_names_than_gates_leaves_the_later_gates_with_their_derived_name(self, tmp_path, capsys):
        """A name is optional per gate; the gates after the last named one are not shifted or
        left blank, they simply keep the name derived from their command."""
        rc = gate.main([
            "--gate", "true", "--name", "first gate",
            "--gate", "true",
            "--log", str(tmp_path / "g.log"),
        ])
        assert rc == 0
        out = capsys.readouterr().out
        assert "[PASS] first gate" in out
        assert "[PASS] true" in out

    def test_a_name_written_before_any_gate_is_a_usage_error_with_an_accurate_message(self, tmp_path, capsys):
        """Written order is the whole rule, so a --name with no --gate in front of it has
        nothing to label. Say THAT, rather than counting names against gates (which would be a
        wrong description of this mistake)."""
        with pytest.raises(SystemExit) as exc:
            gate.main([
                "--name", "orphan", "--gate", "true",
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
        rc = gate.main(["--name", "unit tests", "--log", str(tmp_path / "g.log"), "--", "true"])
        assert rc == 0
        assert "[PASS] unit tests" in capsys.readouterr().out

    def test_a_single_quoted_positional_gate_can_be_labeled_by_a_name(self, tmp_path, capsys):
        rc = gate.main(["--name", "unit tests", "--log", str(tmp_path / "g.log"), "true"])
        assert rc == 0
        assert "[PASS] unit tests" in capsys.readouterr().out

    def test_two_names_for_one_positional_gate_is_still_a_usage_error(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            gate.main(["--name", "one", "--name", "two", "--log", str(tmp_path / "g.log"), "true"])
        assert exc.value.code == 2
        assert "more --name than --gate" in capsys.readouterr().err

    def test_a_name_before_a_gate_option_is_rejected_even_with_a_positional_gate(self, tmp_path, capsys):
        """The one shape that IS ambiguous: with both a --gate and a positional gate present, a
        leading --name could plausibly mean either, so it is refused rather than guessed."""
        with pytest.raises(SystemExit) as exc:
            gate.main(["--name", "which one", "--gate", "true",
                       "--log", str(tmp_path / "g.log"), "--", "true"])
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
            gate.main(["--gate", "true", "--name", "", "--log", str(tmp_path / "g.log")])
        assert exc.value.code == 2
        err = capsys.readouterr().err
        assert "empty" in err
        assert "more --name than --gate" not in err, "that would misdescribe the mistake"

    def test_an_empty_name_followed_by_a_real_one_reports_the_empty_name_not_a_count(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc:
            gate.main(["--gate", "true", "--name", "", "--name", "y", "--log", str(tmp_path / "g.log")])
        assert exc.value.code == 2
        assert "empty" in capsys.readouterr().err

    def test_a_whitespace_only_name_is_rejected_too(self, tmp_path, capsys):
        """A blank label prints as a nameless gate, which is the same unreadable report."""
        with pytest.raises(SystemExit) as exc:
            gate.main(["--gate", "true", "--name", "   ", "--log", str(tmp_path / "g.log")])
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
