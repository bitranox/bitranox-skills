"""Advisories for the two fact classes that poison a curated store."""
import pathlib
import sys

import pytest

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


def test_a_comma_inside_the_subject_does_not_make_an_imperative():
    """A comma is not a clause start: the flags are the subject of this claim, and reading any
    comma as a boundary lost the advisory that every other negative claim gets."""
    assert _negative("--foo and --bar, when combined, do not work on Windows")
    assert _negative("Hooks registered for Stop, and SessionEnd too, do not work under the SDK")
    assert _negative("When the lock is held, retries do not work")


def test_control_one_leading_condition_clause_keeps_the_imperative():
    assert not _negative("If the tree is dirty, do not work on the release branch.")
    assert not _negative("Before release, when on main, do not work there.")
    assert not _negative("Run the gate first. Do not work around it.")


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


# ---- version history in a hook -----------------------------------------------------------------
# "fixed in bmk 3.13.0" is a true sentence and a stale lesson a few releases later; no dream pass
# looked for it, so 122 such facts sat in one store. The advisory names it at write time.

VERSION_ADVICE = "ties its lesson to a version"


@pytest.mark.parametrize("hook", [
    "When make test dies in bmk's own deps, the tool env was rebuilt (fixed in bmk 3.13.0).",
    "When reading provenance, know Config.with_overrides names the override from lib 5.7.0.",
    "When releasing, know since plugin 7.22.10 the gate reads the index.",
    "When bmk lints, it skipped nested checkouts before 3.13.2.",
])
def test_a_hook_with_version_history_gets_the_advisory(hook):
    assert any(VERSION_ADVICE in a for a in cc.advise(hook, ""))


@pytest.mark.parametrize("hook", [
    "When releasing, run make test.",
    "When pinning, require pydantic>=2.13 in pyproject.",
    "When a host answers on 10.0.0.12, it is the gateway.",
    "When on Python 3.10, tomllib is missing.",
    # An interpreter boundary stays true while the supported range spans it (measured: 2 of the
    # 21 hooks the first version of this pattern flagged on the real store).
    "When probing with Path.is_file(), wrap it: before Python 3.14 it re-raises EACCES.",
    "When deciding absolute paths, from Python 3.13 on Windows isabs rejects /work/x.",
])
def test_a_hook_without_version_history_gets_none(hook):
    assert not any(VERSION_ADVICE in a for a in cc.advise(hook, ""))
