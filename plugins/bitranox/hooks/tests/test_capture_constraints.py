"""Advisories for the two fact classes that poison a curated store."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import capture_constraints as cc


def test_bare_negative_claim_is_flagged():
    out = cc.advise("When using the browser tool, know it does not work.", "")
    assert any("negative claim" in a for a in out), out


def test_negative_claim_with_a_version_is_not_flagged():
    out = cc.advise(
        "When using foo 1.2.3, know --bar does not work; fixed upstream in 1.3.0.",
        "",
    )
    assert out == [], out


def test_negative_claim_with_a_date_is_not_flagged():
    out = cc.advise(
        "When using the browser tool, know it does not work (measured 2026-08-15).",
        "",
    )
    assert out == [], out


def test_negative_claim_with_an_unrelated_date_elsewhere_is_still_flagged():
    # The date describes when the tool was RELEASED, not when the "broken"
    # claim was tested - it must not excuse a claim it has nothing to do with.
    out = cc.advise(
        "When using the browser tool released around 2026-08-01, know the "
        "search command is broken.",
        "",
    )
    assert any("negative claim" in a for a in out), out


def test_negative_claim_with_an_unrelated_version_elsewhere_is_still_flagged():
    # The version scopes the PLUGIN mentioned in the trigger clause, not the
    # export-button claim in the separate clause after the comma.
    out = cc.advise(
        "As of plugin 5.201.0, the old export button is broken.",
        "",
    )
    assert any("negative claim" in a for a in out), out


def test_unresolved_failure_written_as_procedure_is_flagged():
    body = "We tried A, then B, then C. None of them worked. Next session should retry."
    out = cc.advise("When X happens, do A then B then C.", body)
    assert any("unresolved" in a for a in out), out


def test_a_working_procedure_is_not_flagged():
    body = "Run `make test`, then `make push`. **Why:** the gate is a superset."
    out = cc.advise("When releasing, run make test then make push.", body)
    assert out == [], out


def test_advise_never_raises_on_empty_input():
    assert cc.advise("", "") == []
