"""A hostile `session_id` must not steer a hook's state file out of the audit dir.

`session_id` arrives on hook stdin and a dozen hooks build a filesystem path from it. A path built
by concatenation is confined by nothing: measured on the live tree before the fix,
`../../../tmp/pwned` left the audit dir entirely and an absolute id replaced the base dir outright.

Severity is BOUNDED and the tests say so rather than overstating it: `session_id` is minted by
Claude Code, not by the model, so this is defense in depth at a trust boundary rather than a live
hole. What makes it worth one shared helper is the breadth - every site below builds its own path.

Every session-keyed state path in the plugin is listed here on purpose. Wiring the helper into one
hook fixes only that hook, and a test that exercises the helper alone goes green against a plugin
that is still entirely unconfined; the table is what makes a half-applied fix fail.

All content is ASCII.
"""

import os
from pathlib import Path

import pytest

import context_watcher
import decision_review_nudge
import jig_repetition_nudge
import recall_memory
import recovery_retry_gate
import retry_with_a_flag_nudge
import self_improve_signals as sig
import skill_router
import toolbox_nudge


# Each entry is (site, builder). A builder takes a session id and returns the state path for it.
BUILDERS = [
    ("self_improve_signals.touched_file", sig.touched_file),
    ("self_improve_signals.subagent_learnings_file", sig.subagent_learnings_file),
    ("context-watcher._asked_flag", context_watcher._asked_flag),
    ("decision-review-nudge.asked_flag", decision_review_nudge.asked_flag),
    ("jig-repetition-nudge._state_path", jig_repetition_nudge._state_path),
    ("recovery-retry-gate._state_path", recovery_retry_gate._state_path),
    ("retry-with-a-flag-nudge._state_path", retry_with_a_flag_nudge._state_path),
    ("toolbox-nudge._nudge_flag", lambda s: toolbox_nudge._nudge_flag(s)),
    # These two already carried a private copy of the sanitiser before the shared helper existed,
    # so they are the KNOWN NEGATIVE of this table: they must pass both before and after the
    # convergence. A table in which every row fails cannot show that the rows differ.
    ("skill-router._state_file", lambda s: skill_router._state_file(os.getcwd(), s)),
    ("recall-memory._state_file", lambda s: recall_memory._state_file(os.getcwd(), s)),
]

HOSTILE_IDS = [
    "../../../tmp/pwned",        # relative traversal - measured to escape before the fix
    "/tmp/absolute-pwned",       # absolute - a join with this DISCARDS the base dir
    "sub/dir/plain",             # no dots at all: a plain separator still leaves the dir
    "..\\..\\pwned",             # live on Windows only; on POSIX a backslash is a filename char
    "with\x00nul",               # NUL: legal in a str, raises ValueError at the filesystem call
]


@pytest.fixture
def audit_dir(tmp_path, monkeypatch):
    """An isolated HOME, so a leaking write lands in tmp_path and the real store is untouched."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return sig._audit_dir()


@pytest.mark.parametrize("site,builder", BUILDERS, ids=[s for s, _ in BUILDERS])
@pytest.mark.parametrize("hostile", HOSTILE_IDS, ids=[repr(h) for h in HOSTILE_IDS])
def test_a_hostile_session_id_cannot_leave_the_audit_dir(site, builder, hostile, audit_dir):
    built = builder(hostile)
    assert built.parent == audit_dir, (
        "%s built %s, which is not a direct child of %s" % (site, built, audit_dir))
    # The parent check alone can be satisfied by a path that resolves elsewhere through a link or a
    # surviving `..`, so confirm containment on the resolved form too.
    assert built.resolve().is_relative_to(audit_dir.resolve()), (
        "%s built %s, which resolves outside %s" % (site, built, audit_dir))


def test_the_writers_create_nothing_outside_the_audit_dir(audit_dir, tmp_path):
    """The path builders are only half of it: each writer mkdirs its parent, so an unconfined id
    CREATES a directory outside the audit dir rather than merely naming one."""
    hostile = "../../../escaped/pwned"
    sig.record_touched_path(hostile, "/some/edited/file.py")
    sig.buffer_subagent_learning(hostile, {"kind": "probe", "text": "x"})
    toolbox_nudge._already_nudged(hostile, "grep_all")

    strays = [p for p in tmp_path.rglob("*")
              if p.is_file() and not p.is_relative_to(audit_dir)]
    assert strays == [], "writes escaped the audit dir: %s" % [str(p) for p in strays]
    # Non-vacuity: writers that silently did nothing would also leave no stray. All three must have
    # landed, under the flattened name, INSIDE the dir.
    landed = sorted(p.suffix for p in audit_dir.iterdir() if p.is_file())
    assert landed == [".subagent-learnings", ".toolbox-nudged", ".touched"], landed


def test_a_real_session_id_keeps_its_historical_filename(audit_dir):
    """Compatibility pin. Real ids are UUIDs, so the confinement must be a no-op on them - a
    sanitiser that rewrote them would orphan every state file already on disk, silently."""
    real = "928b23b2-af26-48b5-83b6-5059381c23e2"
    assert sig.touched_file(real).name == real + ".touched"
    assert sig.subagent_learnings_file(real).name == real + ".subagent-learnings"
    assert jig_repetition_nudge._state_path(real).name == real + ".jig-ledger.json"
    assert recovery_retry_gate._state_path(real).name == real + ".recovery-gate.json"
    assert retry_with_a_flag_nudge._state_path(real).name == real + ".retry-flag.json"
    assert toolbox_nudge._nudge_flag(real).name == real + ".toolbox-nudged"
    assert context_watcher._asked_flag(real).name == real + ".handover-asked"
    assert decision_review_nudge.asked_flag(real).name == real + ".decisions-asked"


def test_two_ids_sharing_the_first_64_chars_get_different_state_files(audit_dir):
    """The cap truncates, and truncation aliases: without a disambiguator two distinct sessions
    land on ONE file and the second silently reads the first one's state.

    Unreachable with real ids, which are 36-char UUIDs. It is pinned because the cap was inherited
    by copying it from two hooks that had always had one, into six sites that never did - so for
    those six this was a behaviour change nobody chose.
    """
    a = "s" * 64 + "-alpha"
    b = "s" * 64 + "-beta"
    assert sig.session_key(a) != sig.session_key(b)
    assert sig.touched_file(a) != sig.touched_file(b)
    # Still bounded: the point is to disambiguate WITHIN the cap, not to abandon it.
    for oversized in (a, b):
        assert len(sig.session_key(oversized)) <= 64


def test_a_queue_key_that_is_not_a_real_key_is_refused(audit_dir):
    """`contrib_file` accepts the pseudo-path `queue_key:<hash>` and slices the key straight into a
    filename. The key is `proj_key` output - exactly 16 hex chars - so anything else is a typo or an
    attempt to steer the path, and a REJECT is right here where a flatten is not: an operator who
    mistyped a key wants to be told, not silently pointed at a different queue.

    Ground truth for the shape: every *.contrib.jsonl on this machine is 16 hex chars.
    """
    good = sig.contrib_file(sig.QUEUE_KEY_PREFIX + "b76cc15ac35f308a")
    assert good.parent == audit_dir
    assert good.name == "b76cc15ac35f308a.contrib.jsonl"

    for bad in ("../../../tmp/pwned", "/tmp/absolute", "probe", "b76cc15ac35f308", "B76CC15AC35F308A"):
        with pytest.raises(ValueError):
            sig.contrib_file(sig.QUEUE_KEY_PREFIX + bad)
