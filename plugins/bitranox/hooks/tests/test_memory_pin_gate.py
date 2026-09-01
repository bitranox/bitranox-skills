"""`bx:pin` is a write-permission gate: an ordinary `add` must refuse to overwrite an
already-pinned fact, and the only deliberate way through is `amend-pinned`. The gate lives
entirely in `add_or_update_entry`'s update branch; the movers (`move`, `relocate`, `rename`)
carry `pin` through untouched and never refuse on it - this file's last test proves the gate
still holds AFTER a move, which is the point of the whole feature.
"""

from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    # the stores-generation marker + recall caches live under ~/.claude; keep tests hermetic.
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def _three_levels(tmp_path):
    """anchor -> mid -> proj, each a CLAUDE.md-bearing rung; central store at the anchor."""
    anchor = tmp_path / "tree"
    mid = anchor / "mid"
    proj = mid / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, mid, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(mid), str(proj)


def _pointer(level, slug):
    text = (Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8")
    _scope, pointers = us.parse_pointer_index(text)
    by_slug = {p.slug: p for p in pointers}
    return by_slug.get(slug)


def test_add_refuses_a_pinned_target_and_leaves_the_original_hook_on_disk(proj, capsys):
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)

    rc = E.main(["add", "--proj", proj, "--title", "Iron rule",
                "--hook", "When testing, do something ELSE.", "--body", "B2", "--slug", slug])
    out = capsys.readouterr().out

    assert rc == 1
    assert "! refused:" in out and slug in out and "amend-pinned" in out

    ptr = _pointer(proj, slug)
    assert ptr is not None and ptr.pin is True
    assert ptr.hook == "When testing, do the original thing."   # unchanged - refused BEFORE any write
    body = us.body_path(E._anchor(proj), slug).read_text(encoding="utf-8")
    assert "something ELSE" not in body


def test_pinned_refusal_attributes_the_escape_to_a_human_not_the_reader(proj, capsys):
    """The refusal message is the most proximate instruction an autonomous reader sees at the
    moment it is blocked - it must not read as a hand-off to run `amend-pinned` itself. Assert on
    the phrase carrying that meaning, not the whole sentence, so a later copy-edit does not break
    this test for a wording change that keeps the intent."""
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)

    rc = E.main(["add", "--proj", proj, "--title", "Iron rule",
                "--hook", "When testing, do something ELSE.", "--slug", slug])
    out = capsys.readouterr().out

    assert rc == 1
    assert "human review" in out
    assert "amend-pinned --slug %s" % slug in out   # a human at a keyboard still needs the verb


def test_add_still_succeeds_on_an_unpinned_target(proj, capsys):
    """Control: the gate discriminates on pin, it does not refuse every overwrite."""
    slug = E.add_or_update_entry(proj, "Ordinary fact", "When testing, do the original thing.",
                                 body="B")   # pin defaults False

    rc = E.main(["add", "--proj", proj, "--title", "Ordinary fact",
                "--hook", "When testing, do the UPDATED thing.", "--body", "B2", "--slug", slug])
    out = capsys.readouterr().out

    assert rc == 0 and "! refused:" not in out
    ptr = _pointer(proj, slug)
    assert ptr.hook == "When testing, do the UPDATED thing."


def test_amend_pinned_changes_the_hook_and_the_fact_stays_pinned(proj, capsys):
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)

    rc = E.main(["amend-pinned", "--proj", proj, "--slug", slug,
                "--hook", "When testing, do the AMENDED thing."])
    out = capsys.readouterr().out

    assert rc == 0, out
    ptr = _pointer(proj, slug)
    assert ptr.hook == "When testing, do the AMENDED thing."
    assert ptr.pin is True, "amend-pinned must not silently unpin the fact"


def test_source_flag_is_gone_from_both_verbs(proj, capsys):
    """Provenance was removed in 5.300.0 and `--source` went with it, on `add` and `amend-pinned`
    alike. Asserted as a REJECTION rather than a no-op: a flag that silently accepts and discards
    is the shape this change exists to remove, so 'gone' has to mean argparse refuses it."""
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)
    for argv in (["amend-pinned", "--proj", proj, "--slug", slug, "--source", "x"],
                 ["add", "--proj", proj, "--title", "T", "--hook", "When x, do y.",
                  "--body", "B", "--source", "x"]):
        with pytest.raises(SystemExit) as exc:      # argparse exits 2 on an unknown option
            E.main(argv)
        assert exc.value.code == 2, "%s must reject --source" % argv[0]
    assert _pointer(proj, slug).pin is True         # the fact is untouched by the refusal


def test_amend_pinned_reads_the_hook_from_a_file(tmp_path, proj, capsys):
    """A 500-char hook cannot be typed inline behind the shell guard, so `amend-pinned` takes the
    same `--hook-file` as `add`, resolved through the same helper."""
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)
    hf = tmp_path / "hook.txt"
    hf.write_text("When testing, read the AMENDED hook from a file.\n", encoding="utf-8")

    rc = E.main(["amend-pinned", "--proj", proj, "--slug", slug, "--hook-file", str(hf)])
    out = capsys.readouterr().out

    assert rc == 0, out
    ptr = _pointer(proj, slug)
    assert ptr.hook == "When testing, read the AMENDED hook from a file."
    assert ptr.pin is True


def test_amend_pinned_refuses_an_unreadable_hook_file_before_writing(tmp_path, proj, capsys):
    """The file form fails loud rather than silently amending with an empty hook."""
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)

    rc = E.main(["amend-pinned", "--proj", proj, "--slug", slug,
                "--hook-file", str(tmp_path / "absent.txt")])
    out = capsys.readouterr().out

    assert rc == 1
    assert "! refused:" in out
    assert _pointer(proj, slug).hook == "When testing, do the original thing."


def test_amend_pinned_with_neither_hook_form_is_not_an_error(proj, capsys):
    """Unlike `add`, the hook is optional here: a body-only amend keeps the stored hook and must
    not trip the 'pass --hook or --hook-file' refusal that `add` raises."""
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)
    body_file = Path(proj) / "newbody.txt"
    body_file.write_text("An amended body.\n", encoding="utf-8")

    rc = E.main(["amend-pinned", "--proj", proj, "--slug", slug, "--body-file", str(body_file)])
    out = capsys.readouterr().out

    assert rc == 0, out
    assert "! refused:" not in out
    assert _pointer(proj, slug).hook == "When testing, do the original thing."
    assert "An amended body." in us.body_path(E._anchor(proj), slug).read_text(encoding="utf-8")


def test_pinned_fact_survives_move_and_the_gate_still_refuses_at_the_destination(tmp_path, capsys):
    anchor, mid, proj = _three_levels(tmp_path)
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True, scope_default="proj")

    rep = E.move_entry(proj, mid, slug)
    assert rep["moved"] is True and rep["refused"] is None

    moved_ptr = _pointer(mid, slug)
    assert moved_ptr is not None and moved_ptr.pin is True   # pin threaded through the mover

    rc = E.main(["add", "--proj", mid, "--title", "Iron rule",
                "--hook", "When testing, do something ELSE.", "--slug", slug])
    out = capsys.readouterr().out

    assert rc == 1
    assert "! refused:" in out and slug in out
    ptr = _pointer(mid, slug)
    assert ptr.hook == "When testing, do the original thing."   # still unchanged after the move
