"""Advisories for the two fact classes that poison a curated store."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import capture_constraints as cc


def test_bare_negative_claim_is_flagged():
    out = cc.advise("When using the browser tool, know it does not work.", "")
    assert any("negative claim" in a for a in out), out


def test_negative_claim_with_a_version_is_still_flagged():
    out = cc.advise(
        "When using foo 1.2.3, know --bar does not work; fixed upstream in 1.3.0.",
        "",
    )
    assert any("negative claim" in a for a in out), out


def test_negative_claim_with_a_date_is_still_flagged():
    out = cc.advise(
        "When using the browser tool, know it does not work (measured 2026-08-15).",
        "",
    )
    assert any("negative claim" in a for a in out), out


def test_negative_claim_with_an_unrelated_date_elsewhere_is_still_flagged():
    # A date in the trigger clause (when the tool was released) does not
    # suppress the warning on the negative claim later in the hook.
    out = cc.advise(
        "When using the browser tool released around 2026-08-01, know the "
        "search command is broken.",
        "",
    )
    assert any("negative claim" in a for a in out), out


def test_negative_claim_with_an_unrelated_version_elsewhere_is_still_flagged():
    # A version in the trigger clause (the plugin's own version) does not
    # suppress the warning on the negative claim later in the hook.
    out = cc.advise(
        "As of plugin 5.201.0, the old export button is broken.",
        "",
    )
    assert any("negative claim" in a for a in out), out


def test_unresolved_failure_in_body_is_flagged():
    body = "We tried A, then B, then C. None of them worked. Next session should retry."
    out = cc.advise("When X happens, do A then B then C.", body)
    assert any("unresolved" in a for a in out), out


def test_unresolved_failure_is_flagged_even_when_the_hook_is_not_a_procedure():
    # The trigger is the BODY alone - the hook here is a plain observation, not a
    # numbered/sequential how-to, and the advisory must still fire.
    body = "We tried A, then B, then C. None of them worked. Next session should retry."
    out = cc.advise("When investigating X, know that the usual suspects do not explain it.", body)
    assert any("unresolved" in a for a in out), out


def test_a_working_procedure_is_not_flagged():
    body = "Run `make test`, then `make push`. **Why:** the gate is a superset."
    out = cc.advise("When releasing, run make test then make push.", body)
    assert out == [], out


def test_advise_never_raises_on_empty_input():
    assert cc.advise("", "") == []
