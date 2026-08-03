"""A Windows-written log must read back as text, whatever encoding the writer used."""
from __future__ import annotations

import json
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
        assert not out.startswith("﻿")

    def test_utf16le_with_bom(self):
        assert winlog.decode_windows_text("DONE-OK\n".encode("utf-16")) == "DONE-OK\n"

    def test_utf16be_with_bom(self):
        assert winlog.decode_windows_text("﻿DONE-OK\n".encode("utf-16-be")) == "DONE-OK\n"

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


class TestReadFile:
    def test_reads_and_decodes(self, tmp_path):
        f = tmp_path / "x.log"
        f.write_bytes("hi\n".encode("utf-16-le"))
        assert winlog.read_windows_log(f) == "hi\n"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(OSError):
            winlog.read_windows_log(tmp_path / "missing.log")
