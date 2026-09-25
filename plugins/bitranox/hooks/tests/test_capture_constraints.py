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


# ---- an imperative is not a claim ------------------------------------------------------------


def _negative(hook):
    return any("negative claim" in a for a in cc.advise(hook, ""))


def test_an_imperative_do_not_work_is_not_a_negative_claim():
    assert not _negative("When on a shared checkout, do not work on main directly.")
    assert not _negative("When a task needs root, don't work as root; use sudo per command.")
    assert not _negative("Do not work around a failing gate.")


def test_control_a_subject_before_do_not_work_is_still_a_claim():
    assert _negative("When using foo, know --bar and --baz do not work together.")
    assert _negative("When using foo, know the flags don't work on Windows.")
    assert _negative("When using foo, know it does not work.")


# ---- contractions and the curly apostrophe read like their spelled-out forms -----------------


def test_contracted_negative_claims_are_flagged():
    assert _negative("When using foo, know --bar isn't supported.")
    assert _negative("When using foo, know the old API can't be used.")
    assert _negative("When using foo, know it doesn%st work." % chr(0x2019))


def test_a_contracted_unresolved_failure_is_flagged():
    out = cc.advise("When X happens, check Y.", "We didn't find a working fix yet.")
    assert any("unresolved" in a for a in out), out


def test_control_spelled_out_forms_still_flag():
    assert _negative("When using foo, know --bar is not supported.")
    assert _negative("When using foo, know the old API cannot be used.")


def test_control_a_contraction_that_is_not_a_negative_claim_is_quiet():
    assert not _negative("When releasing, don't skip the gate; run make test first.")
    assert cc.advise("When X, run Y.", "It didn't take long.") == []
