"""A Windows-written log must read back as text, whatever encoding the writer used."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import winlog

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "winlog.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


class TestDecode:
    def test_plain_utf8_is_unchanged(self):
        assert winlog.decode_windows_text(b"hello\nworld\n") == "hello\nworld\n"

    def test_utf8_bom_is_stripped(self):
        out = winlog.decode_windows_text("hello\n".encode("utf-8-sig"))
        assert out == "hello\n"
        assert not out.startswith("\ufeff")

    def test_utf16le_with_bom(self):
        assert winlog.decode_windows_text("DONE-OK\n".encode("utf-16")) == "DONE-OK\n"

    def test_utf16be_with_bom(self):
        assert winlog.decode_windows_text("\ufeffDONE-OK\n".encode("utf-16-be")) == "DONE-OK\n"

    def test_utf16le_without_bom(self):
        """Tee-Object/Out-File append UTF-16 with no BOM - nothing announces the encoding."""
        assert winlog.decode_windows_text("DONE-OK\n".encode("utf-16-le")) == "DONE-OK\n"

    def test_the_case_that_caused_this_tool(self):
        """ASCII header written by Set-Content, then UTF-16 appended by Tee-Object.

        The real file. Read naively it comes back as "D O N E - O K", so a match on the
        completion marker silently fails and a wait loop times out on a SUCCESSFUL run.
        """
        raw = b"=== KB install ===\n" + "11:50:39  DONE-OK\n".encode("utf-16-le")
        out = winlog.decode_windows_text(raw)
        assert "DONE-OK" in out
        assert "=== KB install ===" in out
        # the header must survive too, not be sacrificed to decode the tail
        assert out.startswith("=== KB install ===")

    def test_control_the_naive_read_really_does_miss_it(self):
        """Prove the test above could fail: the obvious decode does NOT find the marker.

        Without this the mixed-file test might be passing for some unrelated reason.
        """
        raw = b"=== KB install ===\n" + "11:50:39  DONE-OK\n".encode("utf-16-le")
        naive = raw.decode("utf-8", errors="replace")
        assert "DONE-OK" not in naive          # the bug, reproduced
        assert "D\x00O\x00N\x00E" in naive     # and this is what it looks like instead

    def test_cp1252_fallback_keeps_umlauts(self):
        """A legacy Windows tool writes ANSI; decoding as utf-8 would mangle or drop it."""
        out = winlog.decode_windows_text("NT-AUTORITÄT\\SYSTEM\n".encode("cp1252"))
        assert "NT-AUTORITÄT\\SYSTEM" in out

    def test_crlf_is_normalized(self):
        assert winlog.decode_windows_text(b"a\r\nb\r\n") == "a\nb\n"

    def test_empty_file(self):
        assert winlog.decode_windows_text(b"") == ""

    def test_a_wide_chunk_does_not_swallow_the_next_line(self):
        raw = "one\ntwo\nthree\n".encode("utf-16-le")
        assert winlog.decode_windows_text(raw).splitlines() == ["one", "two", "three"]


class TestDescribe:
    """The operator needs to LEARN the file is mixed, else they fix it in the reader forever."""

    def test_names_a_mixed_file(self):
        raw = b"header\n" + "tail\n".encode("utf-16-le")
        assert "mixed" in winlog.describe_encoding(raw).lower()

    def test_names_plain_utf8(self):
        assert "utf-8" in winlog.describe_encoding(b"hello\n").lower()

    def test_names_utf16(self):
        assert "utf-16" in winlog.describe_encoding("hi\n".encode("utf-16-le")).lower()


class TestCli:
    def test_read_prints_decoded_text(self, tmp_path):
        f = tmp_path / "install.log"
        f.write_bytes(b"=== start ===\n" + "DONE-OK\n".encode("utf-16-le"))
        p = run("read", str(f))
        assert p.returncode == 0, p.stderr
        assert "DONE-OK" in p.stdout

    def test_grep_matches_across_the_encoding_seam(self, tmp_path):
        f = tmp_path / "install.log"
        f.write_bytes(b"=== start ===\n" + "11:50:39  DONE-OK\n".encode("utf-16-le"))
        p = run("read", str(f), "--grep", "DONE-OK")
        assert p.returncode == 0, p.stderr
        assert "DONE-OK" in p.stdout

    def test_grep_no_match_exits_1(self, tmp_path):
        f = tmp_path / "install.log"
        f.write_bytes("nothing here\n".encode("utf-16-le"))
        p = run("read", str(f), "--grep", "DONE-OK")
        assert p.returncode == 1
        assert p.stdout.strip() == ""

    def test_missing_file_exits_2_and_says_so_on_stderr(self, tmp_path):
        p = run("read", str(tmp_path / "nope.log"))
        assert p.returncode == 2
        assert "nope.log" in p.stderr

    def test_tail_limits_the_output(self, tmp_path):
        f = tmp_path / "a.log"
        f.write_bytes("\n".join(f"line{i}" for i in range(50)).encode("utf-16-le"))
        p = run("read", str(f), "--tail", "3")
        assert p.returncode == 0, p.stderr
        assert len(p.stdout.strip().splitlines()) == 3
        assert "line49" in p.stdout

    def test_json_envelope(self, tmp_path):
        f = tmp_path / "a.log"
        f.write_bytes(b"head\n" + "DONE-OK\n".encode("utf-16-le"))
        p = run("read", str(f), "--json")
        assert p.returncode == 0, p.stderr
        doc = json.loads(p.stdout)
        assert doc["ok"] is True
        assert "mixed" in doc["data"]["encoding"].lower()
        assert any("DONE-OK" in line for line in doc["data"]["lines"])

    def test_json_still_emitted_on_failure(self, tmp_path):
        p = run("read", str(tmp_path / "gone.log"), "--json")
        assert p.returncode == 2
        doc = json.loads(p.stdout)
        assert doc["ok"] is False
        assert doc["error"]

    def test_warnings_go_to_stderr_not_into_the_parsed_stream(self, tmp_path):
        f = tmp_path / "a.log"
        f.write_bytes(b"head\n" + "tail\n".encode("utf-16-le"))
        p = run("read", str(f), "--json")
        json.loads(p.stdout)          # stdout must be pure JSON
        assert "mixed" in p.stderr.lower()   # the advisory belongs on stderr


class TestWideSegmentation:
    """UTF-16 lines must be found by their aligned terminator, not by a NUL share or a bare 0x0A."""

    def test_non_latin_utf16_line_is_wide_not_mixed(self, tmp_path):
        """Cyrillic code units carry no NUL, so a per-line NUL share judged this line narrow."""
        f = tmp_path / "ru.log"
        f.write_bytes("11:50:39 Ошибка установки\n".encode("utf-16-le"))
        p = run("read", str(f), "--grep", "Ошибка", "--json")
        assert p.returncode == 0, p.stdout + p.stderr
        doc = json.loads(p.stdout)
        assert doc["data"]["encoding"] == "utf-16-le (no BOM)"
        assert doc["data"]["lines"] == ["11:50:39 Ошибка установки"]

    def test_pure_non_latin_line_without_any_ascii(self):
        raw = "Ошибка\nустановки\n".encode("utf-16-le")
        assert winlog.decode_windows_text(raw) == "Ошибка\nустановки\n"
        assert winlog.describe_encoding(raw) == "utf-16-le (no BOM)"

    def test_control_cyrillic_with_ascii_already_worked(self, tmp_path):
        f = tmp_path / "rumix.log"
        f.write_bytes("11:50:39 step one two three Ошибка\n".encode("utf-16-le"))
        p = run("read", str(f), "--grep", "Ошибка")
        assert p.returncode == 0, p.stderr

    def test_a_character_with_a_0a_low_byte_does_not_cut_the_line(self, tmp_path):
        """U+4E0A is the bytes 0A 4E in UTF-16LE: splitting on the bare byte lost the marker."""
        f = tmp_path / "cn.log"
        f.write_bytes("step \u4e0a DONE-OK\n".encode("utf-16-le"))
        p = run("read", str(f), "--grep", "DONE-OK", "--json")
        assert p.returncode == 0, p.stdout + p.stderr
        assert json.loads(p.stdout)["data"]["lines"] == ["step \u4e0a DONE-OK"]

    def test_a_0a_low_byte_character_at_line_start(self):
        raw = "\u4e0a DONE-OK\n\u4e0a\u4e0a\n".encode("utf-16-le")
        assert winlog.decode_windows_text(raw) == "\u4e0a DONE-OK\n\u4e0a\u4e0a\n"

    def test_control_a_character_without_a_0a_byte(self, tmp_path):
        f = tmp_path / "cn_ctl.log"
        f.write_bytes("step \u4e0b DONE-OK\n".encode("utf-16-le"))
        p = run("read", str(f), "--grep", "DONE-OK")
        assert p.returncode == 0, p.stderr

    @pytest.mark.parametrize("nl", ["\n", "\r\n"])
    def test_narrow_after_wide_keeps_no_orphan_nul(self, tmp_path, nl):
        """A Tee-Object write followed by an Add-Content append: the wide LF's NUL is not text."""
        f = tmp_path / "wn.log"
        f.write_bytes(f"first{nl}".encode("utf-16-le") + f"DONE-OK{nl}".encode("ascii"))
        p = run("read", str(f), "--grep", "^DONE-OK", "--json")
        assert p.returncode == 0, p.stdout + p.stderr
        assert json.loads(p.stdout)["data"]["lines"] == ["DONE-OK"]

    def test_control_the_documented_order_narrow_then_wide(self, tmp_path):
        f = tmp_path / "nw.log"
        f.write_bytes(b"first\n" + "DONE-OK\n".encode("utf-16-le"))
        p = run("read", str(f), "--grep", "^DONE-OK")
        assert p.returncode == 0, p.stderr

    @pytest.mark.parametrize("head", [b"ab\n", b"abc\n", b"ab\ncdef\n", b"a\nbb\nccc\n", b"\n"])
    def test_narrow_lines_before_a_wide_segment_stay_narrow(self, head):
        """Whatever the narrow line lengths, the transition must not be read as one wide line."""
        raw = head + "x\n\u4e0a\nDONE-OK\n".encode("utf-16-le")
        assert winlog.decode_windows_text(raw) == head.decode() + "x\n\u4e0a\nDONE-OK\n"

    @pytest.mark.parametrize("head", [b"ab\n", b"head one\nab\n", b"\n", b"abcd\n"])
    @pytest.mark.parametrize("first", ["\u4e00", "\u0100", "\u4e00\u4e00"])
    def test_a_wide_segment_opening_with_a_00_low_byte_stays_separate(self, head, first):
        """U+xx00 is 00 xx in UTF-16LE, so the narrow LF plus that NUL reads as a wide LF.

        Taken as one wide line, every later code unit is misaligned and the marker is mojibake.
        """
        raw = head + f"{first} DONE-OK\r\n".encode("utf-16-le")
        assert winlog.decode_windows_text(raw) == head.decode() + f"{first} DONE-OK\n"
        if head.strip():  # a blank narrow line is no evidence of a narrow writer
            assert winlog.describe_encoding(raw).startswith("MIXED")

    def test_a_long_nul_free_wide_line_after_the_00_opener(self):
        """Misaligned by one byte, `4E 61 62 .. 0A` looks like a clean narrow line - but its LF is
        followed by a NUL again, so it is no evidence for the wide reading."""
        wide = "\u4e00" + "\u6261" * 20 + " DONE-OK\n"
        raw = b"ab\n" + "\u4e00\u6261\u6261\n".encode("utf-16-le") + wide.encode("utf-16-le")
        assert winlog.decode_windows_text(raw) == "ab\n\u4e00\u6261\u6261\n" + wide

    @pytest.mark.parametrize("first", ["\u6261", "\u4e00\u6261", "\u0414"])
    def test_control_a_wide_line_whose_next_line_opens_with_a_00_low_byte(self, first):
        """The same bytes (xx xx 0A 00 00 4E) are also a real wide file; alignment decides."""
        raw = f"{first}\n\u4e00 DONE-OK\r\n".encode("utf-16-le")
        assert winlog.decode_windows_text(raw) == f"{first}\n\u4e00 DONE-OK\n"
        assert winlog.describe_encoding(raw) == "utf-16-le (no BOM)"

    def test_control_a_narrow_line_then_zeroed_padding_is_still_padding(self):
        raw = b"ab\n" + b"\x00" * 8
        assert winlog.decode_windows_text(raw) == "ab\n"

    @pytest.mark.parametrize("line", [b"abc\x00def\n", b"abc\x00de\n", b"ab\x00d\n"])
    def test_a_stray_nul_does_not_flip_a_narrow_line(self, line):
        raw = line + b"next line\nDONE-OK\n"
        out = winlog.decode_windows_text(raw)
        assert out.endswith("next line\nDONE-OK\n")
        assert out.startswith(line.decode().split("\x00")[0])

    def test_mostly_cjk_line_with_one_ascii_space_before_a_0a_character(self):
        raw = "\u6f22\u6f22\u6f22\u6f22 \u4e0a DONE-OK\n".encode("utf-16-le")
        assert winlog.decode_windows_text(raw) == "\u6f22\u6f22\u6f22\u6f22 \u4e0a DONE-OK\n"

    def test_many_ambiguous_0a_00_lines_are_not_quadratic(self):
        """Each `ab\\n\\x00` asks the alignment question; answering it by scanning to EOF made
        8,000 lines take 2.7 s, which puts 50,000 at roughly 100 s."""
        raw = b"ab\n\x00" * 50_000
        assert winlog.decode_windows_text(raw).count("\n") == 50_000

    def test_a_long_narrow_file_is_not_quadratic(self):
        raw = b"line of narrow text\n" * 50_000 + "tail\n".encode("utf-16-le")
        out = winlog.decode_windows_text(raw)
        assert out.endswith("line of narrow text\ntail\n")


# A crash or power cut leaves a log ending in zeroed clusters. Those NUL bytes are not text in
# either encoding, and read as UTF-16 they turned the narrow lines before them into CJK.
NARROW_LOGS = [
    b"abc\nstep 2\nDONE-OK\n",
    b"DONE-OK!\n",
    b"abc\nDONE-OK",
    b"abc\nDONE-OK\r\n",
    b"Starting install\nDONE-OK\n",
    b"OK",
]
PADDING = [1, 2, 3, 16, 4096]


class TestTrailingNulPadding:
    @pytest.mark.parametrize("pad", PADDING)
    @pytest.mark.parametrize("text", NARROW_LOGS)
    def test_a_padded_narrow_log_reads_as_its_text(self, text, pad):
        out = winlog.decode_windows_text(text + b"\x00" * pad)
        assert out == text.decode().replace("\r\n", "\n")

    @pytest.mark.parametrize("text", NARROW_LOGS)
    def test_control_the_same_log_unpadded(self, text):
        assert winlog.decode_windows_text(text) == text.decode().replace("\r\n", "\n")

    @pytest.mark.parametrize("pad", PADDING)
    @pytest.mark.parametrize("text", ["Ошибка\nDONE-OK\n", "DONE-OK\n", "DONE", "上 DONE-OK\n",
                                      "11:50:39 Ошибка установки\n"])
    def test_a_padded_wide_log_keeps_its_last_character(self, text, pad):
        """The first NUL of the run can be the high byte of the last UTF-16 code unit."""
        assert winlog.decode_windows_text(text.encode("utf-16-le") + b"\x00" * pad) == text

    @pytest.mark.parametrize("pad", PADDING)
    def test_a_wide_last_line_whose_bytes_look_narrow_after_other_wide_lines(self, pad):
        """U+6F22 U+5B57 is the bytes 22 6F 57 5B - printable ASCII - so only the UTF-16 lines
        before it say the tail's first NUL is the high byte of the last LF."""
        text = "x\n漢字\n"
        assert winlog.decode_windows_text(text.encode("utf-16-le") + b"\x00" * pad) == text

    @pytest.mark.parametrize("pad", PADDING)
    def test_a_padded_mixed_log(self, pad):
        raw = b"=== KB install ===\n" + "11:50:39  DONE-OK\n".encode("utf-16-le") + b"\x00" * pad
        assert winlog.decode_windows_text(raw) == "=== KB install ===\n11:50:39  DONE-OK\n"

    @pytest.mark.parametrize("pad", PADDING)
    @pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
    def test_a_padded_bom_file(self, encoding, pad):
        text = "DONE-OK 一\n一"
        raw = "\ufeff".encode(encoding) + text.encode(encoding) + b"\x00" * pad
        assert winlog.decode_windows_text(raw) == text

    def test_padding_is_named_and_does_not_make_a_narrow_file_mixed(self):
        described = winlog.describe_encoding(b"abc\nstep 2\nDONE-OK\n" + b"\x00" * 512)
        assert described.startswith("utf-8")
        assert "512 trailing NUL" in described

    def test_control_an_unpadded_file_names_no_padding(self):
        assert "NUL" not in winlog.describe_encoding(b"abc\nDONE-OK\n")

    def test_a_file_of_only_nul_bytes(self):
        assert winlog.decode_windows_text(b"\x00" * 64) == ""

    def test_cli_finds_the_marker_in_a_padded_log(self, tmp_path):
        f = tmp_path / "install.log"
        f.write_bytes(b"abc\nstep 2\nDONE-OK\n" + b"\x00" * 4096)
        p = run("read", str(f), "--grep", "^DONE-OK$", "--json")
        assert p.returncode == 0, p.stdout + p.stderr
        assert json.loads(p.stdout)["data"]["lines"] == ["DONE-OK"]
        assert "mixed" not in p.stderr.lower()


class TestTailAndPattern:
    def test_tail_zero_prints_nothing(self, tmp_path):
        f = tmp_path / "t.log"
        f.write_bytes(b"l1\nl2\nl3\n")
        p = run("read", str(f), "--tail", "0")
        assert p.returncode == 0, p.stderr
        assert p.stdout == ""

    def test_negative_tail_is_refused(self, tmp_path):
        f = tmp_path / "t.log"
        f.write_bytes(b"l1\nl2\nl3\n")
        p = run("read", str(f), "--tail", "-1")
        assert p.returncode == 2
        assert p.stdout == ""

    def test_control_tail_one(self, tmp_path):
        f = tmp_path / "t.log"
        f.write_bytes(b"l1\nl2\nl3\n")
        assert run("read", str(f), "--tail", "1").stdout == "l3\n"

    def test_invalid_grep_regex_exits_2_not_1(self, tmp_path):
        f = tmp_path / "a.log"
        f.write_bytes(b"x\n")
        p = run("read", str(f), "--grep", "(")
        assert p.returncode == 2
        assert "Traceback" not in p.stderr
        assert "--grep" in p.stderr

    def test_invalid_grep_regex_json_envelope(self, tmp_path):
        f = tmp_path / "a.log"
        f.write_bytes(b"x\n")
        p = run("read", str(f), "--grep", "(", "--json")
        assert p.returncode == 2
        doc = json.loads(p.stdout)
        assert doc["ok"] is False
        assert "--grep" in doc["error"]

    def test_form_feed_does_not_split_a_log_line(self, tmp_path):
        f = tmp_path / "ff.log"
        f.write_bytes("a\fb DONE-OK\nc\u2028d\n".encode())
        p = run("read", str(f), "--json")
        assert json.loads(p.stdout)["data"]["lines"] == ["a\fb DONE-OK", "c\u2028d"]


class TestDescribeLabels:
    def test_empty(self):
        assert winlog.describe_encoding(b"") == "empty"

    def test_utf16_bom(self):
        assert winlog.describe_encoding("x\n".encode("utf-16")) == "utf-16-le (BOM)"

    def test_utf8_bom(self):
        assert winlog.describe_encoding("x\n".encode("utf-8-sig")) == "utf-8 (BOM)"

    def test_cp1252(self):
        assert winlog.describe_encoding("AUTORITÄT\n".encode("cp1252")) == "cp1252/ansi"

    def test_plain_utf8(self):
        assert winlog.describe_encoding(b"hello\n") == "utf-8"


class TestConsoleEncoding:
    def test_cp1252_stdout_does_not_crash_on_a_replacement_char(self, tmp_path):
        f = tmp_path / "c.log"
        f.write_bytes(b"bad \x81 byte\n")
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        env.pop("PYTHONUTF8", None)
        p = subprocess.run([sys.executable, str(SCRIPT), "read", str(f), "--grep", "bad"],
                           capture_output=True, env=env, check=False)
        assert p.returncode == 0, p.stderr
        assert b"bad" in p.stdout


class TestReadFile:
    def test_reads_and_decodes(self, tmp_path):
        f = tmp_path / "x.log"
        f.write_bytes("hi\n".encode("utf-16-le"))
        assert winlog.read_windows_log(f) == "hi\n"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(OSError):
            winlog.read_windows_log(tmp_path / "missing.log")
