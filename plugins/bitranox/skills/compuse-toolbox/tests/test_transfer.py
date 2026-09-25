"""Is it stalled, or is my instrument lying? The jig must never answer from one signal."""
from __future__ import annotations

import functools
import http.server
import os
import shlex
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import transfer as pc  # noqa: E402


def S(name, before, after):
    return pc.Signal(name=name, before=before, after=after)


class TestDecide:
    def test_the_case_that_caused_this_tool(self):
        """curl: file size flat (stale NTFS dir entry) while CPU climbs 158s.

        Reading the flat one alone said STALLED and nearly killed a healthy 5.4 GB
        download. A signal that IS moving outranks one that is not: something is
        happening, so the flat instrument is the thing in doubt.
        """
        code, msg = pc.decide([S("file:size", 0, 0), S("pid:cpu_s", 12.0, 158.2)])
        assert code == 0, msg
        assert "ADVANCING" in msg
        # and it must NAME the untrustworthy instrument, not silently ignore it
        assert "file:size" in msg
        assert "suspect" in msg.lower()

    def test_all_signals_flat_is_a_stall(self):
        code, msg = pc.decide([S("file:size", 100, 100), S("pid:cpu_s", 9.0, 9.0)])
        assert code == 1, msg
        assert "STALLED" in msg

    def test_one_flat_signal_alone_is_UNKNOWN_never_stalled(self):
        """The whole point: one instrument cannot prove a stall, only suggest one."""
        code, msg = pc.decide([S("file:size", 100, 100)])
        assert code == 2, msg
        assert "UNKNOWN" in msg
        assert "one" in msg.lower()

    def test_one_advancing_signal_alone_is_enough_to_say_advancing(self):
        # asymmetric on purpose: proving motion needs one witness, proving absence needs more
        code, msg = pc.decide([S("pid:cpu_s", 1.0, 2.0)])
        assert code == 0, msg
        assert "ADVANCING" in msg

    def test_unusable_signals_are_not_counted_as_flat(self):
        """A signal that could not be read is missing evidence, not evidence of a stall."""
        code, msg = pc.decide([S("file:size", None, None), S("pid:cpu_s", 5.0, 5.0)])
        assert code == 2, msg
        assert "UNKNOWN" in msg

    def test_no_usable_signal_at_all(self):
        code, msg = pc.decide([S("file:size", None, None)])
        assert code == 2, msg
        assert "UNKNOWN" in msg

    def test_a_going_backwards_signal_still_counts_as_motion(self):
        # a log being rotated / a counter reset is movement, and certainly not a stall
        code, msg = pc.decide([S("file:size", 900, 100), S("pid:cpu_s", 3.0, 3.0)])
        assert code == 0, msg
        assert "ADVANCING" in msg


class TestSignal:
    def test_delta_and_usable(self):
        assert S("x", 1, 4).delta == 3
        assert S("x", 1, 4).usable is True
        assert S("x", None, 4).usable is False
        assert S("x", 1, None).usable is False

    def test_delta_of_an_unusable_signal_is_none(self):
        assert S("x", None, 4).delta is None


class TestParseRate:
    """Bits vs bytes is the trap: `curl --limit-rate 8M` is 8 MiB/s = ~67 Mbit/s.

    Asking for "8 Mbit" and typing 8M caps you 8x too high, and nothing errors - the
    download just saturates the link you were trying to protect.
    """

    def test_bit_units_are_converted_to_bytes(self):
        assert pc.parse_rate("8Mbit") == 1_000_000        # 8e6 bits / 8
        assert pc.parse_rate("8mbit") == 1_000_000        # case-insensitive
        assert pc.parse_rate("800kbit") == 100_000
        assert pc.parse_rate("1Gbit") == 125_000_000

    def test_byte_units_follow_curl_and_are_binary(self):
        assert pc.parse_rate("1M") == 1024 * 1024
        assert pc.parse_rate("1K") == 1024
        assert pc.parse_rate("2MB") == 2 * 1024 * 1024

    def test_a_bare_number_is_bytes_per_second(self):
        assert pc.parse_rate("1000000") == 1_000_000

    def test_8M_is_not_8_megabit(self):
        # the whole reason this function exists
        assert pc.parse_rate("8M") != pc.parse_rate("8Mbit")
        assert pc.parse_rate("8M") == 8 * 1024 * 1024

    def test_garbage_raises_rather_than_guessing(self):
        import pytest
        for bad in ["", "fast", "8Mb/s", "-1"]:
            with pytest.raises(ValueError):
                pc.parse_rate(bad)


class TestReadersDegradeInsteadOfThrowing:
    def test_missing_file_reads_none(self, tmp_path):
        assert pc.read_file_size(tmp_path / "nope") is None

    def test_existing_file_reads_its_size(self, tmp_path):
        f = tmp_path / "f"
        f.write_bytes(b"12345")
        assert pc.read_file_size(f) == 5

    def test_missing_pid_reads_none(self):
        # pid 0 is never a readable /proc entry for a user process
        assert pc.read_pid_cpu_seconds(0) is None

    def test_own_pid_reads_a_number_on_linux_and_degrades_elsewhere(self):
        """read_pid_cpu_seconds parses /proc, which only Linux has. The contract this class is
        named for is that it DEGRADES rather than throwing, so assert the degradation on the
        platforms without /proc instead of skipping and covering nothing there."""
        import os
        import sys
        v = pc.read_pid_cpu_seconds(os.getpid())
        if sys.platform.startswith("linux"):
            assert v is not None and v >= 0.0
        else:
            assert v is None


class TestBuildPushArgs:
    """Push a big file to another host, rate-capped and resumable.

    The unit trap is the reason this lives in code. rsync's --bwlimit takes KiB/s when
    given no suffix, so "8 Mbit" is 976, NOT 8 and NOT 8000. Computing that by hand is
    exactly how a cap silently ends up 8x or 1024x wrong.
    """

    def test_bwlimit_is_kib_per_second_not_bytes(self):
        argv = pc.build_push_args("/src/big.tar.zst", "root@host:/dst/", pc.parse_rate("8Mbit"))
        assert "--bwlimit=976" in argv, argv

    def test_no_rate_means_no_bwlimit_flag(self):
        argv = pc.build_push_args("/src/f", "root@host:/dst/", None)
        assert not any(a.startswith("--bwlimit") for a in argv), argv

    def test_resumable_and_in_place(self):
        """--partial keeps a killed transfer's bytes; --inplace makes the resume append
        to the same file rather than restarting into a temp copy."""
        argv = pc.build_push_args("/src/f", "root@host:/dst/", None)
        assert "--partial" in argv and "--inplace" in argv, argv

    def test_src_and_dest_are_last_and_in_order(self):
        argv = pc.build_push_args("/src/f", "root@host:/dst/", None)
        assert argv[-2:] == ["/src/f", "root@host:/dst/"], argv

    def test_ssh_options_are_passed_through_as_one_e_argument(self):
        argv = pc.build_push_args("/s", "h:/d", None, ssh="ssh -i /k -o BatchMode=yes")
        i = argv.index("-e")
        assert argv[i + 1] == "ssh -i /k -o BatchMode=yes", argv

    def test_a_rate_below_one_kib_still_caps_rather_than_becoming_unlimited(self):
        """--bwlimit=0 means UNLIMITED in rsync, so a tiny rate must floor at 1, never 0."""
        argv = pc.build_push_args("/s", "h:/d", 100)  # 100 B/s -> 0.098 KiB/s
        assert "--bwlimit=1" in argv, argv


# ---- helpers for the real-process tests below ---------------------------------------

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "transfer.py"


def _join(argv):
    """A command string the script's own splitter reads back as `argv` on this platform."""
    return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)


def _py(code):
    return _join([sys.executable, "-c", code])


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)


class TestParseRateRefusesZero:
    @pytest.mark.parametrize("bad", ["7bit", "0Mbit", "0.5", "0"])
    def test_a_rate_that_truncates_to_zero_is_refused(self, bad):
        """0 B/s is no cap at all: curl and rsync would run unlimited while asked to cap."""
        with pytest.raises(ValueError):
            pc.parse_rate(bad)

    def test_control_eight_bytes_per_second_still_caps(self):
        assert pc.parse_rate("8000bit") == 1000

    def test_cli_rejects_a_zero_rate_with_exit_2(self, tmp_path):
        p = _run("fetch", "http://127.0.0.1:9/x.iso", "-o", str(tmp_path / "x"), "--rate", "7bit")
        assert p.returncode == 2
        assert "rate" in p.stderr
        assert "Traceback" not in p.stderr


class TestBuildFetchArgs:
    def test_fetch_fails_on_an_http_error_instead_of_saving_the_error_page(self):
        argv = pc.build_fetch_args("http://h/f.iso", "f.iso", None)
        assert "--fail" in argv, argv

    def test_rate_and_resume_and_quiet_meter(self):
        argv = pc.build_fetch_args("http://h/f.iso", "f.iso", 1000)
        assert argv[:3] == ["curl", "--limit-rate", "1000"], argv
        assert "--no-progress-meter" in argv and "-C" in argv, argv
        assert argv[-3:] == ["-o", "f.iso", "http://h/f.iso"], argv

    def test_no_rate_means_no_limit_flag(self):
        assert "--limit-rate" not in pc.build_fetch_args("http://h/f", "f", None)


class TestDefaultOutputName:
    @pytest.mark.parametrize(("url", "name"), [
        ("http://h/real.iso", "real.iso"),
        ("http://h/dl/real.iso?X-Amz-Signature=ab/cd", "real.iso"),
        ("http://h/a/b.iso#frag/x", "b.iso"),
    ])
    def test_name_comes_from_the_url_path_not_the_query(self, url, name):
        assert pc.default_output_name(url) == name

    @pytest.mark.parametrize("url", ["http://h/dl/", "http://h", "http://h/..", "http://h/."])
    def test_no_usable_name_is_refused(self, url):
        with pytest.raises(ValueError):
            pc.default_output_name(url)

    def test_cli_trailing_slash_exits_2_and_asks_for_o(self, tmp_path):
        p = _run("fetch", "http://127.0.0.1:9/dl/")
        assert p.returncode == 2
        assert "-o" in p.stderr


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def http_root(tmp_path):
    root = tmp_path / "srv"
    root.mkdir()
    (root / "real.iso").write_bytes(b"x" * 5000)
    handler = functools.partial(_Quiet, directory=str(root))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.skipif(shutil.which("curl") is None, reason="fetch drives curl")
class TestFetchEndToEnd:
    """A loopback server only: the real curl, the real script, no outside network."""

    def test_a_404_exits_1_and_leaves_no_error_page_behind(self, http_root, tmp_path):
        out = tmp_path / "missing.iso"
        p = _run("fetch", f"{http_root}/missing.iso", "-o", str(out))
        assert p.returncode == 1, p.stdout + p.stderr
        assert not out.exists() or b"<!DOCTYPE" not in out.read_bytes()

    def test_control_an_existing_file_downloads(self, http_root, tmp_path):
        out = tmp_path / "real.iso"
        p = _run("fetch", f"{http_root}/real.iso", "-o", str(out))
        assert p.returncode == 0, p.stdout + p.stderr
        assert out.stat().st_size == 5000


class TestReadCommandNumber:
    def test_reads_the_number_a_command_prints(self):
        assert pc.read_command_number(_py("print(42)")) == 42.0

    def test_a_failing_command_is_unreadable_not_a_number(self):
        """A sampler that exits non-zero printed an error, not a reading."""
        assert pc.read_command_number(_py("import sys; print(42); sys.exit(3)")) is None

    def test_digits_inside_an_identifier_are_not_the_reading(self):
        """The natural sampler `grep eth0 /proc/net/dev` prints 'eth0: 999 0' - eth0 is no 0."""
        assert pc.read_command_number(_py("print('eth0: 999 0')")) == 999.0

    @pytest.mark.parametrize(("text", "value"), [
        ("size=42", 42.0), ("-3.5 left", -3.5), ("v1.2.3 then 7", 7.0), ("12%", 12.0)])
    def test_number_boundaries(self, text, value):
        assert pc.read_command_number(_py(f"print({text!r})")) == value

    def test_no_number_at_all_is_unreadable(self):
        assert pc.read_command_number(_py("print('eth0 x1 42MB')")) is None

    def test_a_missing_program_is_unreadable(self):
        assert pc.read_command_number("no-such-program-xyz-123") is None


class TestCommandArgument:
    @pytest.mark.parametrize("cmd", ["ls -l dev.txt | awk '{print $5}'", "cat f && echo 1",
                                     "echo 1; echo 2", "stat f > out", "a || b"])
    def test_a_bare_shell_operator_is_refused_at_parse_time(self, cmd):
        """There is no shell, so `|` would reach the first program as an argument."""
        p = _run("check", "--file", __file__, "--cmd", cmd, "--interval", "0")
        assert p.returncode == 2
        assert "shell" in p.stderr
        assert "Traceback" not in p.stderr

    def test_an_operator_inside_one_quoted_remote_argument_is_fine(self):
        cmd = _join(["ssh", "host", "cat /proc/net/dev | grep eth0"])
        assert pc.command_argument(cmd) == cmd

    def test_help_does_not_promise_a_shell(self):
        help_text = " ".join(_run("check", "--help").stdout.split())  # immune to line wrapping
        assert "run with no shell" in help_text
        assert "shell command" not in help_text


@pytest.mark.skipif(os.name != "nt", reason="the Windows command-line splitter exists only there")
class TestWindowsSplit:
    def test_backslashes_in_an_unquoted_path_survive(self):
        assert pc.split_command(r"C:\Tools\count.exe --x") == [r"C:\Tools\count.exe", "--x"]

    def test_a_double_quoted_argument_groups(self):
        assert pc.split_command(r'ssh host "powershell -File C:\count.ps1"') == [
            "ssh", "host", r"powershell -File C:\count.ps1"]


class TestCheckEndToEnd:
    def test_a_moving_command_is_advancing(self, tmp_path):
        counter = tmp_path / "n"
        code = ("import pathlib; p = pathlib.Path(%r); n = int(p.read_text()) if p.exists() else 0;"
                " p.write_text(str(n + 1)); print(n)") % str(counter)
        p = _run("check", "--cmd", _py(code), "--interval", "0")
        assert p.returncode == 0, p.stdout + p.stderr
        assert "ADVANCING" in p.stdout

    def test_a_failing_sampler_is_named_unreadable_not_flat(self, tmp_path):
        f = tmp_path / "static.bin"
        f.write_bytes(b"x")
        p = _run("check", "--file", str(f), "--cmd", _py("import sys; print(1); sys.exit(2)"),
                 "--interval", "0")
        assert p.returncode == 2, p.stdout
        assert "UNKNOWN" in p.stdout
        assert "cmd0" in p.stdout

    def test_two_flat_signals_are_a_stall(self, tmp_path):
        f = tmp_path / "static.bin"
        f.write_bytes(b"x")
        p = _run("check", "--file", str(f), "--cmd", _py("print(5)"), "--interval", "0")
        assert p.returncode == 1, p.stdout
        assert "STALLED" in p.stdout


class TestUnknownNamesTheUnreadable:
    def test_one_flat_signal_plus_an_unreadable_pid_names_the_pid(self):
        code, msg = pc.decide([S("file:size", 5, 5), S("pid4992:cpu_s", None, None),
                               S("pid4992:io_bytes", None, None)])
        assert code == 2, msg
        assert "unreadable: pid4992:cpu_s, pid4992:io_bytes" in msg

    @pytest.mark.skipif(sys.platform.startswith("linux"), reason="Linux has /proc")
    def test_pid_off_linux_says_why_it_is_unreadable(self, tmp_path):
        f = tmp_path / "f"
        f.write_bytes(b"x")
        p = _run("check", "--file", str(f), "--pid", str(os.getpid()), "--interval", "0")
        assert "Linux" in p.stderr


class TestReadPidIo:
    def test_missing_pid_reads_none(self):
        assert pc.read_pid_io_bytes(0) is None

    @pytest.mark.skipif(not Path(f"/proc/{os.getpid()}/io").exists(), reason="needs /proc/<pid>/io")
    def test_own_pid_reads_a_total(self):
        v = pc.read_pid_io_bytes(os.getpid())
        assert v is not None and v >= 0


@pytest.mark.skipif(shutil.which("rsync") is None, reason="push drives rsync")
class TestPushEndToEnd:
    def test_local_push_copies_and_exits_0(self, tmp_path):
        src = tmp_path / "a.bin"
        src.write_bytes(b"y" * 100)
        dst = tmp_path / "out"
        dst.mkdir()
        p = _run("push", str(src), str(dst) + "/", "--rate", "8Mbit")
        assert p.returncode == 0, p.stderr
        assert (dst / "a.bin").read_bytes() == b"y" * 100
        assert "--bwlimit" not in p.stdout
        assert "# cap 1000000 B/s" in p.stderr
