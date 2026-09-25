"""Bounded paragraph rewrap: only the anchored paragraph may change."""
import re
import textwrap

import pytest

import mdwrap

DOC = """\
# Title

  First paragraph that is quite long and should be left completely alone by any rewrap that was
  anchored somewhere else entirely in this document.

  NEXT STEP: a sized frequency run scored BOTH ways, because it owes two answers. Per BOOT, sized to COUNT collapses - the per-boot rate is still unmeasured.

  | a | b |
  |---|---|
  | 1 | 2 |

  Trailing paragraph, also to be left alone.
"""


def test_rewraps_only_the_anchored_paragraph():
    r = mdwrap.rewrap(DOC, anchor="NEXT STEP", width=98)
    assert r.ok
    before, after = DOC.split("\n"), r.text.split("\n")
    # every line outside the reported range is byte-identical
    lo, hi = r.start_line, r.end_line
    assert before[: lo - 1] == after[: lo - 1]
    assert before[hi:] == after[hi + r.line_delta :]
    assert all(len(l) <= 98 for l in after[lo - 1 : hi + r.line_delta])


def test_refuses_an_ambiguous_anchor():
    r = mdwrap.rewrap(DOC, anchor="paragraph", width=98)
    assert not r.ok and "ambiguous" in r.reason


def test_refuses_a_missing_anchor():
    r = mdwrap.rewrap(DOC, anchor="no such text", width=98)
    assert not r.ok and "not found" in r.reason


def test_refuses_a_table_paragraph():
    r = mdwrap.rewrap(DOC, anchor="| a | b |", width=98)
    assert not r.ok and "table" in r.reason


def test_never_emits_a_stray_list_marker():
    # A wrap point falling before " - " would turn a continuation into a bullet.
    src = "  Per MEASUREMENT across a long window " + "x" * 12 + " - a boot-counting design cannot separate them.\n"
    # Precondition: plain textwrap really does start a line with the dash here, so this test
    # fails if the repair is removed rather than passing on an input that never needed it.
    naive = textwrap.wrap(src.strip(), width=52, initial_indent="  ", subsequent_indent="  ",
                          break_long_words=False, break_on_hyphens=False)
    assert any(l.lstrip().startswith("- ") for l in naive), naive
    r = mdwrap.rewrap(src, anchor="Per MEASUREMENT", width=52)
    assert r.ok
    assert not any(l.lstrip().startswith(("- ", "* ", "+ ")) for l in r.text.split("\n")), r.text


def test_preserves_the_paragraph_indent():
    r = mdwrap.rewrap(DOC, anchor="NEXT STEP", width=98)
    body = [l for l in r.text.split("\n") if l.strip().startswith(("NEXT STEP", "to COUNT", "COUNT"))]
    assert body and all(l.startswith("  ") and not l.startswith("   ") for l in body)


def test_reports_the_blast_radius():
    r = mdwrap.rewrap(DOC, anchor="NEXT STEP", width=98)
    assert r.start_line == r.end_line == 6      # the one-line source paragraph
    assert r.line_delta == 1                    # becomes two lines


REAL_PREFIX = """\
  NEXT STEP: DESIGNED, not yet run - the full design, with both readings pre-registered, is
  `docs/plans/2026-08-31-leg3-sized-frequency-run-design.md` (40 boots x 4 repeats on the deployed
  68476c9b6, 14.7h, 160 measurements). In summary: a sized frequency run scored BOTH ways, because
  it owes two answers. Per BOOT, sized to COUNT collapses - the per-boot rate is still unmeasured
  and four 3-boot samples could not establish it. Per MEASUREMENT across a long continuous window
  - a boot-counting design ALONE cannot separate a per-boot draw from a slow host state whose
  period exceeds the window (the RIVAL paragraph above). Plus per-boot capture of tap I/O thread
  placement and softirq CPU distribution. NOT another warm/cold arm, NOT another journal
  correlation, NOT iperf3 server pinning.
"""


def test_repairs_a_paragraph_a_previous_bad_wrap_left_with_a_leading_dash():
    """The real 2026-08-31 case: a continuation line starting '- ' is damage to REPAIR, not a list.

    Regression: `_refusal` used to scan every line, so it refused this paragraph outright. The
    refusal made an 'and no stray bullet remains' check pass on EMPTY output.
    """
    r = mdwrap.rewrap(REAL_PREFIX, anchor="NEXT STEP", width=98)
    assert r.ok, f"refused the paragraph it exists to repair: {r.reason}"
    out = r.text.split("\n")
    assert not any(l.lstrip().startswith("- ") for l in out), out
    # non-vacuous: it really did produce wrapped prose, not nothing
    assert len([l for l in out if l.strip()]) >= 8
    assert "a boot-counting design ALONE" in r.text


def test_a_real_list_is_still_refused():
    """The first line decides. A genuine bullet block must still be refused."""
    r = mdwrap.rewrap("  - a real bullet item with quite a lot of trailing words here\n", anchor="real bullet", width=40)
    assert not r.ok and "list" in r.reason


def test_reports_lines_that_exceed_the_width():
    """Pulling a dash token up can push the previous line over the width; say so."""
    r = mdwrap.rewrap(REAL_PREFIX, anchor="NEXT STEP", width=98)
    assert r.ok
    over = [l for l in r.text.split("\n") if len(l) > 98]
    assert over, "fixture no longer produces an over-width line; pick another"
    assert len(r.notes) == len(over)
    for n in r.notes:
        assert n.startswith("line ") and " chars" in n, n
        # the line number must be a bare integer, not a mangled f-string fragment
        assert n.split()[1].rstrip(":").isdigit(), n


# ==== rank-10 skill-script audit: line endings, block structure, the CLI contract ===============

import io
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(mdwrap.__file__).resolve()
PARA = "Title\n\nANCHOR one two three four five six seven\n\nTail\n"


def _main(tmp_path, content, *args, name="doc.md"):
    p = tmp_path / name
    p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return p, mdwrap.main(["--file", str(p), *args])


# --- line endings are the file's own, on every platform -------------------------------------------

def test_apply_keeps_a_crlf_file_crlf_everywhere(tmp_path, capsys):
    p, rc = _main(tmp_path, PARA.replace("\n", "\r\n"), "--anchor", "ANCHOR", "--width", "20",
                  "--apply")
    data = p.read_bytes()
    assert rc == 0
    assert data.count(b"\n") == data.count(b"\r\n"), data
    assert data.startswith(b"Title\r\n\r\nANCHOR one two three\r\n") and data.endswith(b"Tail\r\n")


def test_apply_keeps_an_lf_file_lf(tmp_path, capsys):
    p, rc = _main(tmp_path, PARA, "--anchor", "ANCHOR", "--width", "20", "--apply")
    assert rc == 0 and b"\r" not in p.read_bytes()


def test_apply_writes_no_crlf_where_the_platform_would_translate(tmp_path, capsys, monkeypatch):
    """Windows text mode turns every written \\n into \\r\\n. Simulated with the pure-Python io
    implementation and a CRLF os.linesep - the platform edge, not this module's code."""
    import _pyio
    monkeypatch.setattr(os, "linesep", "\r\n")
    monkeypatch.setattr(io, "open", _pyio.open)
    monkeypatch.setattr("builtins.open", _pyio.open)
    monkeypatch.setattr(os, "fdopen", lambda fd, *a, **k: _pyio.open(fd, *a, **k))
    p, rc = _main(tmp_path, PARA, "--anchor", "ANCHOR", "--width", "20", "--apply")
    monkeypatch.undo()
    assert rc == 0 and b"\r" not in p.read_bytes()


def test_a_bom_is_kept_and_does_not_hide_a_heading(tmp_path, capsys):
    p, rc = _main(tmp_path, b"\xef\xbb\xbf# Title\nANCHOR one two three four five six\n",
                  "--anchor", "ANCHOR", "--width", "20", "--apply")
    assert rc == 0
    assert p.read_bytes().startswith(b"\xef\xbb\xbf# Title\nANCHOR one two three\n")


# --- block structure: fences, headings, lists, markers, hard breaks -------------------------------

def test_prose_inside_a_fenced_block_is_refused():
    doc = "```sh\nset -e\n\nstep_one ANCHOR\nstep_two\nstep_three\n\ndone\n```\n"
    r = mdwrap.rewrap(doc, anchor="ANCHOR", width=80)
    assert not r.ok and "fence" in r.reason


def test_a_paragraph_after_a_closed_fence_is_still_rewrapped():
    doc = "```\ncode\n```\n\nANCHOR one two three four five six seven\n"
    r = mdwrap.rewrap(doc, anchor="ANCHOR", width=20)
    assert r.ok and r.text.startswith("```\ncode\n```\n\nANCHOR one two three\n")


def test_a_heading_directly_above_is_not_merged():
    doc = "## Setup notes\nANCHOR prose that is long enough to wrap\n"
    r = mdwrap.rewrap(doc, anchor="ANCHOR", width=20)
    assert r.ok
    assert r.text.split("\n")[0] == "## Setup notes"
    assert r.start_line == 2


def test_a_heading_directly_below_is_not_merged():
    doc = "ANCHOR prose that is long enough to wrap\n## Next\n"
    r = mdwrap.rewrap(doc, anchor="ANCHOR", width=20)
    assert r.ok and "## Next" in r.text.split("\n")


def test_an_anchor_on_a_heading_is_refused():
    r = mdwrap.rewrap("## ANCHOR heading\nbody text\n", anchor="ANCHOR", width=10)
    assert not r.ok and "heading" in r.reason


def test_a_setext_heading_is_refused():
    r = mdwrap.rewrap("ANCHOR title words here\n===\n", anchor="ANCHOR", width=10)
    assert not r.ok and "heading" in r.reason


def test_a_list_under_a_lead_in_line_is_refused():
    r = mdwrap.rewrap("Steps to run ANCHOR:\n- build the image\n- push the image\n",
                      anchor="ANCHOR", width=80)
    assert not r.ok and "list" in r.reason


def test_a_single_item_list_under_a_colon_lead_in_is_refused():
    r = mdwrap.rewrap("Steps to run ANCHOR:\n- build the image\n", anchor="ANCHOR", width=80)
    assert not r.ok and "list" in r.reason


@pytest.mark.parametrize("marker", ["#", ">", "##"])
def test_a_wrap_never_starts_a_line_with_a_heading_or_quote_marker(marker):
    src = f"ANCHOR prefix text with a {marker} sign and the {marker} sign goes here now\n"
    for width in range(12, 60):
        r = mdwrap.rewrap(src, anchor="ANCHOR", width=width)
        assert r.ok
        for line in r.text.split("\n")[1:]:
            s = line.lstrip()
            assert not s.startswith(">"), (width, r.text)
            assert not (s.split(" ", 1)[0] and set(s.split(" ", 1)[0]) == {"#"}), (width, r.text)


def test_a_repaired_line_is_checked_again():
    for width in range(10, 40):
        r = mdwrap.rewrap("ANCHOR aaaa bbbb - - cccc dddd\n", anchor="ANCHOR", width=width)
        assert r.ok
        assert not any(l.lstrip().startswith("- ") or l.strip() == "-"
                       for l in r.text.split("\n")[1:]), (width, r.text)


@pytest.mark.parametrize("doc", [
    "Intro.\n\n> quoted ANCHOR paragraph long enough to wrap\n> second quoted line here\n\nEnd.\n",
    "> quoted first line\nlazy ANCHOR continuation that is long enough to wrap\n",
    "Prose ANCHOR above a quote that is long enough to wrap\n> a quote with no blank line\n",
    "  > indented quoted ANCHOR paragraph long enough to wrap\n  > and its second line\n",
])
def test_a_blockquote_paragraph_is_refused(doc):
    # Joining the lines kept the first '> ' and turned every later one into literal text inside
    # the quote ("here. > second"), which changes what the document says.
    r = mdwrap.rewrap(doc, anchor="ANCHOR", width=20)
    assert not r.ok and "blockquote" in r.reason, r.text


def test_a_greater_than_sign_inside_prose_is_not_a_blockquote():
    r = mdwrap.rewrap("ANCHOR a > b holds for every pair of values in the set\n",
                      anchor="ANCHOR", width=20)
    assert r.ok and r.changed


# An oracle of its own, not mdwrap's predicates: CommonMark reads each of these, at the start of a
# line directly under paragraph text, as something other than a continuation of that paragraph -
# a setext underline, a thematic break, a code fence or an HTML block.
_SETEXT_OR_BREAK = re.compile(r"(?:=+|-+|(?:\*[ \t]*){3,}|(?:_[ \t]*){3,})$")


def _renders_as_a_new_block(line: str) -> bool:
    s = line.strip()
    return bool(_SETEXT_OR_BREAK.match(s)) or s.startswith(("```", "~~~", "<"))


@pytest.mark.parametrize("token", ["---", "===", "-", "=", "***", "___", "_ _ _", "```", "~~~",
                                   "<div>"])
@pytest.mark.parametrize("shape", ["ANCHOR aaaa bbbb cccc dddd {t}\n",
                                   "ANCHOR aaaa {t} bbbb cccc {t} dddd eeee ffff\n"])
def test_a_wrap_never_leaves_a_line_markdown_reads_as_a_new_block(token, shape):
    src = shape.format(t=token)
    for width in range(4, 60):
        r = mdwrap.rewrap(src, anchor="ANCHOR", width=width)
        if not r.ok:
            assert "block" in r.reason, (width, r.reason)
            continue
        lines = [l for l in r.text.split("\n") if l]
        assert not any(_renders_as_a_new_block(l) for l in lines[1:]), (width, r.text)


@pytest.mark.parametrize("token", ["---", "***", "_ _ _"])
def test_a_wrap_never_turns_the_first_line_into_a_thematic_break(token):
    # A first line reading only '---' after a blank line is a thematic break: the paragraph's
    # opening words become a horizontal rule.
    src = f"{token} ANCHOR aaaa bbbb cccc\n"
    for width in range(3, 30):
        r = mdwrap.rewrap(src, anchor="ANCHOR", width=width)
        if not r.ok:
            assert "block" in r.reason, (width, r.reason)
            continue
        first = r.text.split("\n")[0].strip()
        assert not _SETEXT_OR_BREAK.match(first) or first.startswith("="), (width, r.text)


def test_a_wrap_the_repair_cannot_make_safe_is_refused_not_written():
    # Width 2 leaves '--' then '-': pulling the '-' up joins them into '-- -', a thematic break.
    # With no token left to pull, the only safe answer is to write nothing.
    r = mdwrap.rewrap("-- - ANCHOR\n", anchor="ANCHOR", width=2)
    assert not r.ok and "new block" in r.reason and r.text == ""


def test_the_block_marker_guard_still_rewraps_plain_prose():
    # The control for the two tests above: prose with none of those tokens still wraps.
    r = mdwrap.rewrap("ANCHOR aaaa bbbb cccc dddd eeee ffff gggg\n", anchor="ANCHOR", width=12)
    assert r.ok and r.line_delta > 0


@pytest.mark.parametrize("brk", ["  ", "\\"])
def test_a_hard_line_break_is_refused(brk):
    r = mdwrap.rewrap(f"ANCHOR first line{brk}\nsecond line after a hard break\n",
                      anchor="ANCHOR", width=80)
    assert not r.ok and "hard line break" in r.reason


def test_trailing_spaces_on_the_last_line_are_not_a_hard_break():
    r = mdwrap.rewrap("ANCHOR first line\nsecond line  \n", anchor="ANCHOR", width=80)
    assert r.ok


# --- the CLI contract: 0 rewrapped, 1 refused, 2 error ---------------------------------------------

def test_cli_dry_run_exits_0_and_writes_nothing(tmp_path, capsys):
    p, rc = _main(tmp_path, PARA, "--anchor", "ANCHOR", "--width", "20")
    assert rc == 0 and p.read_text(encoding="utf-8") == PARA
    assert capsys.readouterr().out.startswith("would rewrite lines 3-3")


def test_cli_refusal_exits_1(tmp_path, capsys):
    _, rc = _main(tmp_path, PARA, "--anchor", "missing words")
    assert rc == 1 and "refused: anchor not found" in capsys.readouterr().err


def test_cli_json_envelope(tmp_path, capsys):
    _, rc = _main(tmp_path, PARA, "--anchor", "ANCHOR", "--width", "20", "--json")
    env = json.loads(capsys.readouterr().out)
    assert rc == 0 and env["ok"] is True and env["command"] == "mdwrap"
    assert env["data"]["start_line"] == 3 and env["data"]["applied"] is False


def test_cli_empty_anchor_is_refused(tmp_path, capsys):
    _, rc = _main(tmp_path, PARA, "--anchor", "  ")
    assert rc == 1 and "empty anchor" in capsys.readouterr().err


def test_cli_missing_file_exits_2(tmp_path, capsys):
    assert mdwrap.main(["--file", str(tmp_path / "nope.md"), "--anchor", "x"]) == 2


def test_cli_non_utf8_file_exits_2(tmp_path, capsys):
    _, rc = _main(tmp_path, b"caf\xe9 ANCHOR\n", "--anchor", "ANCHOR")
    assert rc == 2 and "error" in capsys.readouterr().err


@pytest.mark.parametrize("width", ["0", "-5"])
def test_cli_width_below_one_is_a_usage_error(tmp_path, capsys, width):
    p = tmp_path / "doc.md"
    p.write_text(PARA, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        mdwrap.main(["--file", str(p), "--anchor", "ANCHOR", "--width", width])
    assert exc.value.code == 2


@pytest.mark.skipif(sys.platform == "win32" or getattr(os, "geteuid", lambda: 1)() == 0,
                    reason="needs POSIX mode bits and a non-root user to make a file read-only")
def test_cli_apply_to_a_read_only_file_exits_2_and_leaves_it(tmp_path, capsys):
    p = tmp_path / "ro.md"
    p.write_text(PARA, encoding="utf-8")
    p.chmod(0o444)
    try:
        rc = mdwrap.main(["--file", str(p), "--anchor", "ANCHOR", "--width", "20", "--apply"])
        assert rc == 2 and p.read_text(encoding="utf-8") == PARA
    finally:
        p.chmod(0o644)
    assert sorted(x.name for x in tmp_path.iterdir()) == ["ro.md"], "a temp file was left behind"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX mode bits")
def test_cli_apply_keeps_the_file_mode(tmp_path, capsys):
    p = tmp_path / "x.md"
    p.write_text(PARA, encoding="utf-8")
    p.chmod(0o640)
    assert mdwrap.main(["--file", str(p), "--anchor", "ANCHOR", "--width", "20", "--apply"]) == 0
    assert p.stat().st_mode & 0o777 == 0o640
    assert sorted(x.name for x in tmp_path.iterdir()) == ["x.md"]


def test_cli_unexpected_crash_exits_2_not_the_refusal_code(tmp_path, capsys, monkeypatch):
    class Broken:
        def write(self, _):
            raise RuntimeError("stream gone")

        def flush(self):
            pass

    p = tmp_path / "doc.md"
    p.write_text(PARA, encoding="utf-8")
    monkeypatch.setattr(sys, "stdout", Broken())
    assert mdwrap.main(["--file", str(p), "--anchor", "ANCHOR", "--width", "20"]) == 2
    assert "stream gone" in capsys.readouterr().err


def test_help_names_the_real_script_path():
    proc = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
    assert "tools/mdwrap.py" not in proc.stdout
    assert "scripts/mdwrap.py" in proc.stdout
