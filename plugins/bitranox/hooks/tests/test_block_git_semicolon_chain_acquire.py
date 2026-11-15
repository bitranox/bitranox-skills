"""Tests for block-git-semicolon-chain.py's third rule: an acquire, then a further step, across `;`.

The shape: a lease take that fails on a wrong option, `;`, then a deploy - the deploy runs without
the host lease it was meant to hold, and its own output reads like success. The same applies to a
lock (`flock -n 9`) and a registry login. Followers that only print, filter or report state stay
quiet, and so does every acquire whose failure path is already written.
"""

import io
import json
import sys

import pytest

import block_git_semicolon_chain as G

NL = "\n"


@pytest.mark.parametrize("command, expected", [
    ("scripts/e2e lease take --minutes 180 2>&1 | tail -3; uv run scripts/deploy.py",
     ("lease take", "uv")),
    ("tool lease take 90m 'note'" + NL + "./deploy.sh", ("lease take", "deploy.sh")),
    ("hostctl lock acquire build ; make install", ("lock acquire", "make")),
    ("flock -n 9 ; make install", ("flock", "make")),
    ("docker login registry.example.com ; docker push img", ("docker login", "docker")),
    ("gh auth login --with-token < t ; gh release create v1", ("gh auth login", "gh")),
    ("sudo tool lease take 1h ; ./deploy.sh", ("lease take", "deploy.sh")),
])
def test_an_acquire_reaching_a_further_step_across_a_semicolon_fires(command, expected):
    assert G.acquire_then_act(command) == expected


@pytest.mark.parametrize("command", [
    "tool lease take 1h && ./deploy.sh",                     # stops where the take failed
    "tool lease take 1h || exit 1 ; ./deploy.sh",            # the failure path is written
    "set -e ; tool lease take 1h ; ./deploy.sh",             # the shell aborts on failure
    "tool lease take --help ; ./deploy.sh",                  # a help call takes nothing
    "tool lease take 1h ; echo rc=$?",                       # only prints
    "tool lease take 1h ; tool lease status",                # only reports the lease
    "tool lease take 1h 2>&1 | tail -3",                     # nothing after it
    "echo 'lease take 1h' ; ./deploy.sh",                    # the words are quoted data
    "flock /tmp/build.lock make ; make test",                # flock RUNS the command it guards
    "./deploy.sh ; tool lease take 1h",                      # the acquire comes last
    "docker logout ; docker push img",                       # not a login
])
def test_shapes_that_already_stop_or_cannot_matter_stay_quiet(command):
    assert G.acquire_then_act(command) is None


def _run_main(command, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": command}})))
    rc = G.main()
    return rc, capsys.readouterr().err


def test_main_refuses_the_incident_and_names_the_fix(monkeypatch, capsys):
    rc, err = _run_main("tool lease take --minutes 180 ; uv run deploy.py", monkeypatch, capsys)
    assert rc == 2
    assert "lease take" in err and "`&&`" in err and "|| exit 1" in err


def test_main_passes_the_chained_form(monkeypatch, capsys):
    assert _run_main("tool lease take 180m && uv run deploy.py", monkeypatch, capsys) == (0, "")


def test_the_git_pair_rule_still_wins_when_both_apply(monkeypatch, capsys):
    rc, err = _run_main("tool lease take 1h ; git commit -m x ; git push", monkeypatch, capsys)
    assert rc == 2
    assert "`git commit` and `git push`" in err
