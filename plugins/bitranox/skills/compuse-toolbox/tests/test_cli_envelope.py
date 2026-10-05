"""Tests for _cli_envelope: the shared {ok, command, data, skipped} envelope and exit-code boundary."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import _cli_envelope as cli_envelope
import pytest
from _cli_envelope import (
    EXIT_ERROR,
    EXIT_NO,
    EXIT_YES,
    EnvelopeArgumentParser,
    emit,
    envelope,
    envelope_for_exit,
    guarded,
    render,
    run_guarded,
    wants_json,
)

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


class TestEnvelope:
    def test_keys_and_order(self):
        env = envelope(True, "tool", {"a": 1}, ["x"])
        assert list(env) == ["ok", "command", "data", "skipped"]
        assert env == {"ok": True, "command": "tool", "data": {"a": 1}, "skipped": ["x"]}

    def test_defaults_are_empty_data_and_skipped(self):
        assert envelope(False, "tool") == {"ok": False, "command": "tool", "data": {}, "skipped": []}

    def test_error_key_only_when_given(self):
        assert "error" not in envelope(True, "tool")
        assert envelope(False, "tool", error="boom")["error"] == "boom"

    def test_list_data_is_kept(self):
        assert envelope(True, "tool", [1, 2])["data"] == [1, 2]

    def test_skipped_tuple_becomes_list(self):
        assert envelope(True, "tool", skipped=("a", "b"))["skipped"] == ["a", "b"]


class TestEnvelopeForExit:
    @pytest.mark.parametrize("code,ok", [(EXIT_YES, True), (EXIT_NO, True), (EXIT_ERROR, False)])
    def test_ok_is_exit_not_two(self, code, ok):
        assert envelope_for_exit(code, "tool")["ok"] is ok

    def test_constants(self):
        assert (EXIT_YES, EXIT_NO, EXIT_ERROR) == (0, 1, 2)


class TestRenderAndEmit:
    def test_render_is_ascii_safe(self):
        text = render(envelope(True, "tool", {"p": "café →"}))
        assert text.isascii()
        assert json.loads(text)["data"]["p"] == "café →"

    def test_render_indent(self):
        assert render(envelope(True, "t"), indent=None).count("\n") == 0
        assert "\n" in render(envelope(True, "t"))

    def test_emit_prints_and_returns_code(self, capsys):
        assert emit(1, "tool", {"n": 0}, skipped=["s"]) == 1
        out = json.loads(capsys.readouterr().out)
        assert out == {"ok": True, "command": "tool", "data": {"n": 0}, "skipped": ["s"]}

    def test_emit_exit_two_is_not_ok_and_carries_error(self, capsys):
        assert emit(2, "tool", error="bad input") == 2
        out = json.loads(capsys.readouterr().out)
        assert out["ok"] is False and out["error"] == "bad input"

    def test_emit_to_named_stream(self, capsys):
        import io
        buf = io.StringIO()
        emit(0, "tool", file=buf)
        assert json.loads(buf.getvalue())["ok"] is True
        assert capsys.readouterr().out == ""


class TestWantsJson:
    def test_present(self):
        assert wants_json(["x", "--json"])

    def test_absent(self):
        assert not wants_json(["x", "--jsonl"])

    def test_after_double_dash_is_an_operand(self):
        assert not wants_json(["--", "--json"])

    def test_custom_flags(self):
        assert wants_json(["--json-bare"], flags=("--json", "--json-bare"))

    def test_equals_form(self):
        assert wants_json(["--json=1"])

    def test_none_reads_sys_argv(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "--json"])
        assert wants_json(None)


def _parser() -> EnvelopeArgumentParser:
    p = EnvelopeArgumentParser(prog="tool", envelope_command="tool")
    p.add_argument("--json", action="store_true")
    p.add_argument("--n", type=int)
    return p


class TestParser:
    def test_usage_error_with_json_prints_envelope(self, capsys):
        with pytest.raises(SystemExit) as exc:
            _parser().parse_args(["--json", "--n", "x"])
        assert exc.value.code == 2
        cap = capsys.readouterr()
        env = json.loads(cap.out)
        assert env["ok"] is False and env["command"] == "tool"
        assert "invalid int value" in env["error"]
        assert "usage:" in cap.err

    def test_usage_error_without_json_prints_no_envelope(self, capsys):
        with pytest.raises(SystemExit) as exc:
            _parser().parse_args(["--n", "x"])
        assert exc.value.code == 2
        cap = capsys.readouterr()
        assert cap.out == ""
        assert "invalid int value" in cap.err

    def test_unrecognized_argument(self, capsys):
        with pytest.raises(SystemExit):
            _parser().parse_args(["--json", "--bogus"])
        env = json.loads(capsys.readouterr().out)
        assert "unrecognized arguments" in env["error"]

    def test_success_parses_normally(self, capsys):
        args = _parser().parse_args(["--json", "--n", "3"])
        assert args.n == 3 and args.json
        assert capsys.readouterr().out == ""

    def test_help_prints_no_envelope(self, capsys):
        with pytest.raises(SystemExit) as exc:
            _parser().parse_args(["--json", "--help"])
        assert exc.value.code == 0
        assert not capsys.readouterr().out.lstrip().startswith("{")

    def test_command_defaults_to_prog(self, capsys):
        p = EnvelopeArgumentParser(prog="mytool")
        p.add_argument("--json", action="store_true")
        p.add_argument("pos")
        with pytest.raises(SystemExit):
            p.parse_args(["--json"])
        assert json.loads(capsys.readouterr().out)["command"] == "mytool"

    def test_subparser_error_sees_root_json_flag(self, capsys):
        p = EnvelopeArgumentParser(prog="tool", envelope_command="tool")
        p.add_argument("--json", action="store_true")
        subs = p.add_subparsers(dest="cmd", required=True)
        sub = subs.add_parser("run")
        sub.add_argument("--k", type=int)
        with pytest.raises(SystemExit) as exc:
            p.parse_args(["--json", "run", "--k", "z"])
        assert exc.value.code == 2
        env = json.loads(capsys.readouterr().out)
        assert env["ok"] is False and env["command"] == "tool"

    def test_subparser_error_sees_its_own_json_flag(self, capsys):
        p = EnvelopeArgumentParser(prog="tool", envelope_command="tool")
        subs = p.add_subparsers(dest="cmd", required=True)
        sub = subs.add_parser("run")
        sub.add_argument("--json", action="store_true")
        sub.add_argument("--k", type=int)
        with pytest.raises(SystemExit):
            p.parse_args(["run", "--json", "--k", "z"])
        assert json.loads(capsys.readouterr().out)["ok"] is False

    def test_missing_subcommand(self, capsys):
        p = EnvelopeArgumentParser(prog="tool", envelope_command="tool")
        p.add_argument("--json", action="store_true")
        subs = p.add_subparsers(dest="cmd", required=True)
        subs.add_parser("run")
        with pytest.raises(SystemExit) as exc:
            p.parse_args(["--json"])
        assert exc.value.code == 2
        assert json.loads(capsys.readouterr().out)["ok"] is False

    def test_envelope_printed_once_on_reparse(self, capsys):
        p = _parser()
        p.parse_args(["--n", "1"])
        with pytest.raises(SystemExit):
            p.parse_args(["--json", "--n", "q"])
        assert capsys.readouterr().out.count('"ok"') == 1


class TestGuarded:
    def test_passes_return_code_through(self):
        assert run_guarded(lambda argv: 1, ["--json"], command="t") == 1

    def test_crash_maps_to_two_with_envelope(self, capsys):
        def boom(argv):
            raise ValueError("bad thing")
        assert run_guarded(boom, ["--json"], command="t") == 2
        cap = capsys.readouterr()
        env = json.loads(cap.out)
        assert env["ok"] is False and env["command"] == "t"
        assert "ValueError" in env["error"] and "bad thing" in env["error"]
        assert "t: internal error: ValueError: bad thing" in cap.err
        assert "Traceback" not in cap.err

    def test_crash_names_the_raising_frame(self, capsys):
        def boom(argv):
            raise RuntimeError("x")
        run_guarded(boom, [], command="t")
        err = capsys.readouterr().err
        assert "test_cli_envelope.py" in err and "boom" in err

    def test_crash_without_json_prints_no_envelope(self, capsys):
        def boom(argv):
            raise OSError("disk")
        assert run_guarded(boom, [], command="t") == 2
        assert capsys.readouterr().out == ""

    def test_system_exit_passes_through(self):
        def bye(argv):
            raise SystemExit(1)
        with pytest.raises(SystemExit) as exc:
            run_guarded(bye, ["--json"], command="t")
        assert exc.value.code == 1

    def test_keyboard_interrupt_is_130(self, capsys):
        def stop(argv):
            raise KeyboardInterrupt
        assert run_guarded(stop, ["--json"], command="t") == 130
        assert capsys.readouterr().out == ""

    def test_decorator_form(self, capsys):
        @guarded("deco")
        def main(argv=None):
            raise KeyError("k")
        assert main(["--json"]) == 2
        assert json.loads(capsys.readouterr().out)["command"] == "deco"

    def test_decorator_keeps_name_and_return(self):
        @guarded("deco")
        def main(argv=None):
            return 0
        assert main([]) == 0 and main.__name__ == "main"

    def test_custom_json_flag(self, capsys):
        def boom(argv):
            raise ValueError("v")
        run_guarded(boom, ["--json-bare"], command="t", json_flags=("--json-bare",))
        assert json.loads(capsys.readouterr().out)["ok"] is False


class TestSiblingImport:
    """The real launch shape: a script next to _cli_envelope.py imports it by bare module name."""

    def test_script_in_scripts_dir_imports_helper(self, tmp_path):
        probe = tmp_path / "probe.py"
        probe.write_bytes(
            b"import sys\n"
            b"sys.path.insert(0, sys.argv[1])\n"
            b"from _cli_envelope import EnvelopeArgumentParser, guarded\n"
            b"@guarded('probe')\n"
            b"def main(argv=None):\n"
            b"    p = EnvelopeArgumentParser(prog='probe')\n"
            b"    p.add_argument('--json', action='store_true')\n"
            b"    p.add_argument('--n', type=int)\n"
            b"    p.parse_args(argv)\n"
            b"    raise ValueError('late')\n"
            b"sys.exit(main(sys.argv[2:]))\n"
        )
        bad = subprocess.run([sys.executable, str(probe), str(SCRIPTS), "--json", "--n", "x"],
                             capture_output=True, encoding="utf-8", errors="replace", check=False)
        assert bad.returncode == 2
        assert json.loads(bad.stdout)["ok"] is False
        crash = subprocess.run([sys.executable, str(probe), str(SCRIPTS), "--json"],
                               capture_output=True, encoding="utf-8", errors="replace", check=False)
        assert crash.returncode == 2
        assert "late" in json.loads(crash.stdout)["error"]


def test_module_exports():
    assert set(cli_envelope.__all__) >= {
        "EXIT_YES", "EXIT_NO", "EXIT_ERROR", "envelope", "envelope_for_exit", "render", "emit",
        "wants_json", "EnvelopeArgumentParser", "guarded", "run_guarded",
    }
