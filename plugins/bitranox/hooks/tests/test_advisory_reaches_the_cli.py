"""The capture advisories must reach the CLI's OUTPUT, for BOTH hook input forms.

`test_capture_constraints.py` proves `advise()` classifies correctly, but it exercises the pure
function: deleting the two-line call site in `memory_engine.main` leaves that suite fully green, so
nothing in the suite asserts a running `add` ever PRINTS an advisory. This file closes that gap by
driving the real script as a subprocess and reading its stdout.

The `--hook-file` arm is the load-bearing one. `--hook` and `--hook-file` are alternative spellings
of the same argument, resolved once into a local by `_text_from_flag_or_file`; a call site that
reads `args.hook` instead of that local sees `None` whenever the caller chose the file form, and
`advise()` coerces `None` to `""`, so the advisory silently stops firing with no error and no failed
test. Asserting only the inline arm cannot detect that - hence one arm per form. All content ASCII.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

import uuid_store as us

HOOKS = Path(__file__).resolve().parent.parent
ENGINE = HOOKS / "memory_engine.py"

# Matches capture_constraints.NEGATIVE_RX ("is broken") and leads with a trigger, so the only
# advisory this fact earns is the negative-claim one.
NEGATIVE_HOOK = (
    "When the widget CLI serves a stale cache, know that its --refresh flag is broken, "
    "so clear the cache directory by hand instead."
)
# Deliberately free of UNRESOLVED_RX phrasing: this test asserts the hook-derived advisory, and a
# second advisory firing off the body would let the assertion pass for the wrong reason.
BODY = (
    "The widget CLI keeps a cache under its state directory. Clearing that directory by hand "
    "produces a fresh read on the next invocation."
)
ADVISORY_MARKER = "~ warning:"
ADVISORY_TEXT = "bare negative claim about a tool"


def _tree(tmp_path):
    """anchor -> proj, both CLAUDE.md-bearing rungs; the central store sits at the anchor."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return proj


def _run_add(proj, tmp_path, *hook_args):
    """Run the engine's `add` for real, against a HOME that is not the developer's."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    body_file = tmp_path / "body.txt"
    body_file.write_text(BODY, encoding="utf-8")
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    argv = [sys.executable, str(ENGINE), "add", "--proj", str(proj),
            "--title", "Widget cache refresh", "--body-file", str(body_file), *hook_args]
    return subprocess.run(argv, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


@pytest.mark.parametrize("form", ["inline-flag", "file-flag"])
def test_a_negative_claim_advisory_is_printed_by_the_running_cli(tmp_path, form):
    """`add` prints the negative-claim advisory whether the hook arrives inline or as a file."""
    proj = _tree(tmp_path)
    if form == "inline-flag":
        hook_args = ("--hook", NEGATIVE_HOOK)
    else:
        hook_file = tmp_path / "hook.txt"
        hook_file.write_text(NEGATIVE_HOOK, encoding="utf-8")
        hook_args = ("--hook-file", str(hook_file))

    p = _run_add(proj, tmp_path, *hook_args)

    assert p.returncode == 0, "add failed (rc=%s)\nstdout:\n%s\nstderr:\n%s" % (
        p.returncode, p.stdout, p.stderr)
    advisories = [ln for ln in p.stdout.splitlines() if ln.startswith(ADVISORY_MARKER)]
    assert any(ADVISORY_TEXT in ln for ln in advisories), (
        "the negative-claim advisory never reached stdout via %s\nstdout:\n%s" % (form, p.stdout))


@pytest.mark.parametrize("form", ["inline-flag", "file-flag"])
def test_a_clean_hook_earns_no_advisory_through_either_form(tmp_path, form):
    """The control: a hook with no negative claim prints no advisory, so the assertion above
    could have reported the other answer."""
    proj = _tree(tmp_path)
    clean = "When the widget CLI serves a stale cache, clear its state directory to force a re-read."
    if form == "inline-flag":
        hook_args = ("--hook", clean)
    else:
        hook_file = tmp_path / "hook.txt"
        hook_file.write_text(clean, encoding="utf-8")
        hook_args = ("--hook-file", str(hook_file))

    p = _run_add(proj, tmp_path, *hook_args)

    assert p.returncode == 0, p.stdout + p.stderr
    assert ADVISORY_TEXT not in p.stdout, p.stdout
