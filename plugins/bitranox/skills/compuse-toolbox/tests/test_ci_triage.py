"""Tests for ci_triage.py - strip ANSI + isolate a step + surface error/warning lines. ASCII only.

Exit contract under test: 0 = clean, 1 = errors found (or the command under triage failed),
2 = the tool could not do its job (bad argument, unreadable source, gh failed, step not found).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import ci_triage as T

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "ci_triage.py"

STEPS_LOG = "##[group]Run A\naaa\n##[group]Run B\nbbb\nerror here\n##[group]Run C\nccc\n"


def _cli(*args: str, stdin: bytes | None = None, env_extra: dict[str, str] | None = None,
         ) -> subprocess.CompletedProcess[bytes]:
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin if stdin is not None else b"",
                          capture_output=True, env=env, timeout=60)


def _write(tmp_path: Path, text: str, name: str = "x.log") -> str:
    p = tmp_path / name
    p.write_bytes(text.encode("utf-8"))
    return str(p)


def test_strip_ansi():
    assert T.strip_ansi("\x1b[31merror\x1b[0m: boom") == "error: boom"


def test_error_lines_default_keywords():
    log = "Compiling foo\nerror[E0308]: mismatched types\n  --> src/x.rs:3\nwarning: unused var\nok\n"
    got = [l for _, l in T.error_lines(log)]
    assert any("error[E0308]" in l for l in got)
    assert any("warning: unused" in l for l in got)
    assert "Compiling foo" not in got and "ok" not in got


def test_error_lines_custom_keywords():
    got = [l for _, l in T.error_lines("all green\nFAILED test_x\n", keywords=["FAILED"])]
    assert got == ["FAILED test_x"]


def test_isolate_step():
    block = T.isolate_step(STEPS_LOG, "Run B")
    assert "bbb" in block and "error here" in block
    assert "aaa" not in block and "ccc" not in block


class TestDefaultKeywordsAreWordBound:
    """A green log must not exit 1 because a keyword sits inside a hash, a crate name or a zero count."""

    @pytest.mark.parametrize("line", [
        "test result: ok. 12 passed; 0 failed; 0 ignored",
        "HEAD is now at 3f2e808a1c chore",
        "Checking out 9ae808bc4d1e",
        "Downloaded failure v0.1.8",
        "12 passed, 0 errors, 0 warnings",
        "stderr redirected",
    ])
    def test_green_lines_are_not_hits(self, line):
        assert T.error_lines(line + "\n") == []

    @pytest.mark.parametrize("line", [
        "error[E0308]: mismatched types",
        "ERROR: boom",
        "1 failed, 0 errors",
        "FAILED tests/test_x.py::test_y",
        "TypeError: bad operand",
        "DeprecationWarning: old",
        "thread 'main' panicked at src/main.rs:3",
        "Traceback (most recent call last):",
        "fatal: not a git repository",
        "E0425 unresolved name",
        "3 errors generated.",
    ])
    def test_real_failure_lines_are_hits(self, line):
        assert len(T.error_lines(line + "\n")) == 1


def test_lines_split_only_on_newlines_so_numbers_match_grep():
    """A form feed or U+2028 inside a line must not shift every later line number."""
    log = "a\x0cb\nc\u2028d\nerror: here\n"
    assert T.error_lines(log) == [(3, "error: here")]


class TestStepIsolationInMain:
    def test_line_numbers_under_step_count_from_the_log_not_the_block(self, tmp_path, capsys):
        rc = T.main(["--file", _write(tmp_path, STEPS_LOG), "--step", "Run B"])
        out = capsys.readouterr().out
        assert rc == 1
        assert "5: error here" in out

    def test_a_step_that_is_not_found_is_an_error_not_the_whole_log(self, tmp_path, capsys):
        rc = T.main(["--file", _write(tmp_path, STEPS_LOG), "--step", "Run Tset"])
        cap = capsys.readouterr()
        assert rc == 2
        assert "error here" not in cap.out
        assert "Run Tset" in cap.err

    def test_a_found_step_without_errors_is_clean(self, tmp_path, capsys):
        assert T.main(["--file", _write(tmp_path, STEPS_LOG), "--step", "Run C"]) == 0

    def test_gh_log_layout_prefix_is_understood(self, tmp_path, capsys):
        """`gh run view --log` prefixes every line with job TAB step TAB timestamp."""
        ts = "2026-09-25T10:20:40.1234567Z"
        log = "".join(f"build\t{step}\t{ts} {body}\n" for step, body in [
            ("Run A", "##[group]Run A"), ("Run A", "error in A"),
            ("Run B", "##[group]Run B"), ("Run B", "bbb"),
            ("Run C", "##[group]Run C"), ("Run C", "ccc"),
        ])
        rc = T.main(["--file", _write(tmp_path, log), "--step", "Run B"])
        cap = capsys.readouterr()
        assert rc == 0, cap.out
        assert "error in A" not in cap.out

    def test_gh_prefix_step_name_is_not_itself_a_keyword_hit(self, tmp_path, capsys):
        """A step NAMED 'Check for errors' must not flag every line of that step."""
        ts = "2026-09-25T10:20:40Z"
        log = f"lint\tCheck for errors\t{ts} ##[group]Run ruff\nlint\tCheck for errors\t{ts} all good\n"
        assert T.main(["--file", _write(tmp_path, log)]) == 0


class TestSources:
    def test_empty_file_argument_is_refused_not_read_from_stdin(self):
        r = _cli("--file", "", stdin=b"")
        assert r.returncode == 2

    @pytest.mark.parametrize("flag", ["--cmd", "--gh"])
    def test_empty_cmd_or_gh_is_refused(self, flag):
        assert _cli(flag, "", stdin=b"").returncode == 2

    def test_missing_file_is_exit_2_not_a_traceback(self, tmp_path):
        r = _cli("--file", str(tmp_path / "nope.log"))
        assert r.returncode == 2
        assert b"Traceback" not in r.stderr

    def test_invalid_keyword_regex_is_exit_2(self, tmp_path):
        r = _cli("--file", _write(tmp_path, "x\n"), "--keywords", "error[")
        assert r.returncode == 2
        assert b"Traceback" not in r.stderr

    def test_utf16_bom_log_is_decoded(self, tmp_path):
        p = tmp_path / "ps.log"
        p.write_bytes(b"\xff\xfe" + "ok\nerror: boom\n".encode("utf-16-le"))
        r = _cli("--file", str(p))
        assert r.returncode == 1
        assert b"2: error: boom" in r.stdout

    def test_utf8_bom_does_not_hide_a_first_line_header(self, tmp_path):
        p = tmp_path / "bom.log"
        p.write_bytes(b"\xef\xbb\xbf" + STEPS_LOG.encode("utf-8"))
        r = _cli("--file", str(p), "--step", "Run A")
        assert r.returncode == 0, r.stdout

    def test_stdin_is_decoded_as_utf8_whatever_the_locale(self):
        data = "error: \u274c test_x\n".encode("utf-8")  # contains byte 0x9d, undefined in cp1252
        r = _cli(stdin=data, env_extra={"PYTHONIOENCODING": "cp1252"})
        assert r.returncode == 1
        assert b"Traceback" not in r.stderr

    def test_non_cp1252_hit_does_not_crash_a_cp1252_stdout(self, tmp_path):
        r = _cli("--file", _write(tmp_path, "error: \u2717 boom\n"), env_extra={"PYTHONIOENCODING": "cp1252"})
        assert r.returncode == 1
        assert b"Traceback" not in r.stderr
        assert b"boom" in r.stdout


class TestCommandExitStatus:
    def _script(self, tmp_path: Path, body: str) -> str:
        p = tmp_path / "child.py"
        p.write_text(body, encoding="utf-8")
        return f"{sys.executable} {p}"

    def test_failing_command_without_keywords_is_not_clean(self, tmp_path):
        r = _cli("--cmd", self._script(tmp_path, "import sys\nprint('nothing to see')\nsys.exit(3)\n"))
        assert r.returncode == 1
        assert b"exited 3" in r.stdout + r.stderr
        assert b"nothing to see" in r.stdout + r.stderr

    def test_succeeding_command_with_a_hit_is_exit_1(self, tmp_path):
        assert _cli("--cmd", self._script(tmp_path, "print('error: x')\n")).returncode == 1

    def test_succeeding_clean_command_is_exit_0(self, tmp_path):
        assert _cli("--cmd", self._script(tmp_path, "print('all good')\n")).returncode == 0

    def test_command_not_found_is_exit_2(self):
        r = _cli("--cmd", "no_such_cmd_xyz_ci_triage")
        assert r.returncode == 2
        assert b"Traceback" not in r.stderr

    def test_whitespace_only_command_is_exit_2(self):
        assert _cli("--cmd", " ").returncode == 2


class TestGhSource:
    def test_gh_failure_is_exit_2_and_shows_gh_output(self, capsys):
        def fake_gh(argv):
            return "To get started with GitHub CLI, please run:  gh auth login\n", 4

        rc = T.main(["--gh", "123"], run=fake_gh)
        cap = capsys.readouterr()
        assert rc == 2
        assert "gh auth login" in cap.err

    def test_gh_success_is_triaged(self, capsys):
        calls = []

        def fake_gh(argv):
            calls.append(argv)
            return "build\tRun A\t2026-09-25T10:20:40Z error: boom\n", 0

        assert T.main(["--gh", "123", "--repo", "o/r"], run=fake_gh) == 1
        assert calls[0][-2:] == ["--repo", "o/r"]
        assert "error: boom" in capsys.readouterr().out


class TestKeywordCoverage:
    """Real failure shapes the default keywords must hit, with the green lines they must not."""

    @pytest.mark.parametrize("line", [
        # An exception class whose name has capitals right before "Error"/"Warning".
        "OSError: [Errno 2] No such file or directory: 'x'",
        "IOError: disk full",
        "EOFError: EOF when reading a line",
        "ssl.SSLError: [SSL] certificate verify",
        "HTTPError: HTTP 404: Not Found",
        "requests.exceptions.HTTPError: 500 Server",
        "URLError: <urlopen>",
        # failure / failures / failing (maven, junit, mocha).
        "[INFO] BUILD FAILURE",
        "There were 2 failures:",
        "Failures:",
        "  1 failing",
        # A count after the word, non-zero.
        "Tests run: 5, Failures: 1, Errors: 0, Skipped: 0",
        "Errors: 2",
        "Tests run: 5, Failures: 0, Errors: 0, Warnings: 3",
        # Rust double panic.
        "thread 'main' panicked while panicking. aborting.",
    ])
    def test_failure_line_is_a_hit(self, line):
        assert len(T.error_lines(line + "\n")) == 1, line

    @pytest.mark.parametrize("line", [
        # Zero counts in both orders are a green summary.
        "Errors: 0",
        "Warnings: 0",
        "Tests run: 5, Failures: 0, Errors: 0, Skipped: 0",
        "0 failures",
        "  0 failing",
        "  12 passing",
        "[INFO] BUILD SUCCESS",
        # A keyword glued into an identifier or a path is not a hit.
        "src/error_handler.py:3 ok",
        "import ErrorBoundary from './x'",
        "collected tests/test_failing_cases.py",
        # A crate named after a keyword is not a failure.
        "Downloaded failure v0.1.8",
        "   Compiling error-chain v0.12.4",
        "    Checking failure_derive v0.1.8",
        "  Downloaded warnings v0.2.1",
    ])
    def test_green_line_is_not_a_hit(self, line):
        assert T.error_lines(line + "\n") == [], line


def _gh_log(rows: list[tuple[str, str, str]]) -> str:
    """A `gh run view --log` shaped log: job TAB step TAB timestamp SPACE line."""
    ts = "2026-09-25T10:20:40.1234567Z"
    return "".join(f"{job}\t{step}\t{ts} {body}\n" for job, step, body in rows)


class TestStepByGhStepName:
    """`--gh --step NAME` names the step as gh lists it (the 2nd column), not the ##[group] text."""

    ROWS = [
        ("build", "Set up job", "Current runner version: '2.330.0'"),
        ("build", "Select PyPI auth method", "##[group]Run if [ -n \"$T\" ]; then"),
        ("build", "Select PyPI auth method", "##[endgroup]"),
        ("build", "Select PyPI auth method", "error: token missing"),
        ("build", "Run tests", "##[group]Run make test"),
        ("build", "Run tests", "all good"),
    ]

    def test_step_found_by_gh_step_column(self, tmp_path, capsys):
        rc = T.main(["--file", _write(tmp_path, _gh_log(self.ROWS)), "--step", "Select PyPI auth method"])
        out = capsys.readouterr().out
        assert rc == 1, out
        assert out.startswith("4: build\tSelect PyPI auth method\t"), out

    def test_step_by_column_excludes_other_steps(self, tmp_path, capsys):
        rc = T.main(["--file", _write(tmp_path, _gh_log(self.ROWS)), "--step", "Run tests"])
        assert rc == 0, capsys.readouterr().out

    def test_header_text_still_works_on_a_gh_log(self, tmp_path, capsys):
        rc = T.main(["--file", _write(tmp_path, _gh_log(self.ROWS)), "--step", "Run if"])
        assert rc == 1, capsys.readouterr().out

    def test_absent_step_name_is_still_exit_2(self, tmp_path, capsys):
        rc = T.main(["--file", _write(tmp_path, _gh_log(self.ROWS)), "--step", "Deploy"])
        assert rc == 2
        assert "Deploy" in capsys.readouterr().err

    def test_unknown_step_column_falls_back_to_header_text(self, tmp_path, capsys):
        """gh writes UNKNOWN STEP when it cannot map a line; the ##[group] header must still work."""
        rows = [
            ("build", "UNKNOWN STEP", "##[group]Run make lint"),
            ("build", "UNKNOWN STEP", "warning: lint"),
            ("build", "UNKNOWN STEP", "##[group]Run make test"),
            ("build", "UNKNOWN STEP", "all good"),
        ]
        path = _write(tmp_path, _gh_log(rows))
        assert T.main(["--file", path, "--step", "Run make test"]) == 0
        assert T.main(["--file", path, "--step", "Run make lint"]) == 1
        assert "2: build\tUNKNOWN STEP\t" in capsys.readouterr().out

    def test_step_in_every_matrix_job_is_triaged_not_only_the_first(self, tmp_path, capsys):
        rows = [
            ("Tests (3.12, ubuntu)", "Run tests", "##[group]Run make test"),
            ("Tests (3.12, ubuntu)", "Run tests", "all good"),
            ("Tests (3.12, ubuntu)", "Upload", "##[group]Run upload"),
            ("Tests (3.12, ubuntu)", "Upload", "warning: upload flaky"),
            ("Tests (3.13, windows)", "Run tests", "##[group]Run make test"),
            ("Tests (3.13, windows)", "Run tests", "FAILED tests/test_x.py::test_y"),
        ]
        rc = T.main(["--file", _write(tmp_path, _gh_log(rows)), "--step", "Run tests"])
        out = capsys.readouterr().out
        assert rc == 1, out
        assert "6: " in out and "warning: upload flaky" not in out, out

    def test_header_step_in_every_block_is_triaged_not_only_the_first(self, tmp_path, capsys):
        log = "##[group]Run make test\nok\n##[group]Run lint\nwarning: lint\n##[group]Run make test\nerror: boom\n"
        rc = T.main(["--file", _write(tmp_path, log), "--step", "Run make test"])
        out = capsys.readouterr().out
        assert rc == 1, out
        assert "6: error: boom" in out and "warning: lint" not in out, out
