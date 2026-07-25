"""Tests for ci_triage.py - strip ANSI + isolate a step + surface error/warning lines. ASCII only."""
import ci_triage as T


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
    log = "##[group]Run A\naaa\n##[group]Run B\nbbb\nerror here\n##[group]Run C\nccc\n"
    block = T.isolate_step(log, "Run B")
    assert "bbb" in block and "error here" in block
    assert "aaa" not in block and "ccc" not in block
