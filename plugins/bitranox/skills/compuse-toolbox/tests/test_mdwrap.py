"""Bounded paragraph rewrap: only the anchored paragraph may change."""
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
    doc = "  Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu\n  - a dash clause - that must not start a line.\n"
    src = "  Per MEASUREMENT across a long continuous window " + "x" * 40 + " - a boot-counting design cannot separate them.\n"
    r = mdwrap.rewrap(src, anchor="Per MEASUREMENT", width=60)
    assert r.ok
    assert not any(l.lstrip().startswith(("- ", "* ", "+ ")) for l in r.text.split("\n")), r.text
    assert doc  # keep the counter-example visible


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
