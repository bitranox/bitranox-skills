"""Is it stalled, or is my instrument lying? The jig must never answer from one signal."""
from __future__ import annotations

import sys
from pathlib import Path

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

    def test_own_pid_reads_a_number(self):
        import os
        v = pc.read_pid_cpu_seconds(os.getpid())
        assert v is not None and v >= 0.0


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
