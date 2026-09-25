"""Tests for the memory engine's data-safety boundaries: the paths by which a write could destroy a
fact body another tree owns, escape the central store, or report success for a change it never made.

Each defect pairs with a control for the nearest input that must keep today's verdict. Every tree is
a throwaway fixture under tmp_path with HOME pointed at a scratch dir. All content ASCII.
"""

import os
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(root, name):
    """A tree top (CLAUDE.md + store) with a nested `sub` level. Returns (top, sub) as str."""
    top = Path(root) / name
    sub = top / "sub"
    sub.mkdir(parents=True)
    (top / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (sub / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (top / us.STORE_DIRNAME).mkdir()
    return str(top), str(sub)


def _body(anchor, slug):
    return us.body_path(anchor, slug).read_text(encoding="utf-8")


def _slugs(level):
    local = sig.claude_local_md_path(level)
    if not local.is_file():
        return []
    return [p.slug for p in us.parse_pointer_index(local.read_text(encoding="utf-8"))[1]]


# ---- relocate must never overwrite a body the TARGET tree already owns --------------------------
# The body file is the tree-wide slug registry. A check scoped to the target LEVEL's pointers misses
# a slug owned at another level of the target tree, and misses a same-level duplicate whose hook
# matches but whose body differs - both overwrote the owner's body and exited 0.

def test_relocate_refuses_a_slug_the_target_tree_owns_at_another_level(tmp_path):
    top1, sub1 = _tree(tmp_path, "tree1")
    top2, sub2 = _tree(tmp_path, "tree2")
    E.add_or_update_entry(top2, "Shared name", "When T2, keep me", body="TREE2 ORIGINAL FACT")
    E.add_or_update_entry(sub1, "Shared name", "When T1, other", body="TREE1 FACT")
    rep = E.relocate_entry(sub1, sub2, "shared-name")
    assert rep["relocated"] is False and rep["refused"], rep
    assert "TREE2 ORIGINAL FACT" in _body(top2, "shared-name")      # the owner's body survives
    assert "shared-name" in _slugs(sub1)                             # nothing moved at the source
    assert "shared-name" not in _slugs(sub2)
    assert "TREE1 FACT" in _body(top1, "shared-name")


def test_relocate_refuses_a_same_level_duplicate_whose_body_differs(tmp_path):
    top1, sub1 = _tree(tmp_path, "tree1")
    top2, sub2 = _tree(tmp_path, "tree2")
    E.add_or_update_entry(sub2, "Same", "When same, do same", body="TREE2 BODY")
    E.add_or_update_entry(sub1, "Same", "When same, do same", body="TREE1 BODY")
    rep = E.relocate_entry(sub1, sub2, "same")
    assert rep["relocated"] is False and rep["refused"], rep
    assert "TREE2 BODY" in _body(top2, "same")
    assert "TREE1 BODY" in _body(top1, "same")


def test_relocate_refuses_to_overwrite_a_dangling_body_in_the_target_tree(tmp_path):
    top1, sub1 = _tree(tmp_path, "tree1")
    top2, sub2 = _tree(tmp_path, "tree2")
    us.put_body(top2, "lonely", "---\nname: lonely\n---\n\nDANGLING TREE2 BODY")
    E.add_or_update_entry(sub1, "Lonely", "When lonely, do x", body="TREE1 BODY")
    rep = E.relocate_entry(sub1, sub2, "lonely")
    assert rep["relocated"] is False and rep["refused"], rep
    assert "DANGLING TREE2 BODY" in _body(top2, "lonely")


def test_relocate_completes_when_the_target_already_holds_an_identical_body(tmp_path):
    # CONTROL: a crash between the copy and the source drop leaves the SAME body at the target;
    # re-running the relocate must finish the move, not refuse it.
    top1, sub1 = _tree(tmp_path, "tree1")
    top2, sub2 = _tree(tmp_path, "tree2")
    E.add_or_update_entry(sub1, "Resumed", "When resumed, finish", body="THE BODY")
    us.put_body(top2, "resumed", _body(top1, "resumed"))
    us.add_pointer(sub2, slug="resumed", title="Resumed", hook="When resumed, finish")
    rep = E.relocate_entry(sub1, sub2, "resumed")
    assert rep["relocated"] is True and rep["refused"] is None, rep
    assert "THE BODY" in _body(top2, "resumed")
    assert "resumed" not in _slugs(sub1)
    assert not us.body_path(top1, "resumed").exists()


def test_relocate_into_a_tree_without_the_slug_still_works(tmp_path):
    # CONTROL: the ordinary cross-tree relocate is unaffected.
    top1, sub1 = _tree(tmp_path, "tree1")
    top2, sub2 = _tree(tmp_path, "tree2")
    E.add_or_update_entry(sub1, "Mover", "When moving, move", body="MOVER BODY")
    rep = E.relocate_entry(sub1, sub2, "mover")
    assert rep["relocated"] is True, rep
    assert "MOVER BODY" in _body(top2, "mover") and "mover" in _slugs(sub2)


def test_cli_relocate_refusal_exits_one(tmp_path, capsys):
    top1, sub1 = _tree(tmp_path, "tree1")
    top2, sub2 = _tree(tmp_path, "tree2")
    E.add_or_update_entry(top2, "Shared name", "When T2, keep me", body="TREE2 ORIGINAL FACT")
    E.add_or_update_entry(sub1, "Shared name", "When T1, other", body="TREE1 FACT")
    rc = E.main(["relocate", "--from-level", sub1, "--to-level", sub2, "--slug", "shared-name"])
    assert rc == 1 and "refused" in capsys.readouterr().out


# ---- a caller-supplied slug is a FILENAME: it must not carry a path -----------------------------

@pytest.mark.parametrize("bad", ["../../CLAUDE", "../../../outside", "a/b", "a\\b", "..", ".hidden",
                                 "UPPER", "trailing.", "sp ace"])
def test_add_refuses_a_slug_that_is_not_a_plain_filename(tmp_path, bad):
    top, sub = _tree(tmp_path, "tree")
    before = (Path(top) / "CLAUDE.md").read_text(encoding="utf-8")
    with pytest.raises(E.InvalidSlug):
        E.add_or_update_entry(sub, "T", "When x, do y", body="clobbered", slug=bad)
    assert (Path(top) / "CLAUDE.md").read_text(encoding="utf-8") == before
    assert not (tmp_path / "outside.md").exists()
    assert _slugs(sub) == []


@pytest.mark.parametrize("good", ["plain-slug", "starlette-1.2-httpx2-testclient", "a", "x9-2"])
def test_add_accepts_the_slug_shapes_real_stores_carry(tmp_path, good):
    # CONTROL: slugify output, a collision suffix, and dotted version numbers all occur in real stores.
    top, sub = _tree(tmp_path, "tree")
    assert E.add_or_update_entry(sub, "T", "When x, do y", body="b", slug=good) == good
    assert us.body_path(top, good).is_file()


def test_cli_add_refuses_a_traversal_slug_with_exit_one(tmp_path, capsys):
    top, sub = _tree(tmp_path, "tree")
    rc = E.main(["add", "--proj", sub, "--title", "t", "--hook", "When x, do y",
                 "--body", "clobbered", "--slug", "../../CLAUDE"])
    assert rc == 1 and "refused" in capsys.readouterr().out
    assert (Path(top) / "CLAUDE.md").read_text(encoding="utf-8") == "x\n"


def _plant_pointer(level, slug):
    """A pointer line with a hostile target, as an older engine could have written it."""
    us.add_pointer(level, slug=slug, title="t", hook="When x, do y")


def test_amend_pinned_refuses_a_traversal_slug_even_when_a_pointer_names_it(tmp_path):
    top, sub = _tree(tmp_path, "tree")
    _plant_pointer(sub, "../../CLAUDE")
    with pytest.raises(E.InvalidSlug):
        E.amend_pinned_entry(sub, "../../CLAUDE", body="clobbered")
    assert (Path(top) / "CLAUDE.md").read_text(encoding="utf-8") == "x\n"


def test_rename_refuses_a_traversal_target_and_leaves_the_body_in_the_store(tmp_path):
    top, sub = _tree(tmp_path, "tree")
    E.add_or_update_entry(sub, "Keep", "When x, do y", body="KEEP BODY")
    rep = E.rename_entry(sub, "keep", "../../renamed-out")
    assert rep["renamed"] is False and "not a valid slug" in (rep["refused"] or ""), rep
    assert not (Path(top) / "renamed-out.md").exists()
    assert "KEEP BODY" in _body(top, "keep") and _slugs(sub) == ["keep"]


def test_rename_to_a_plain_slug_still_works(tmp_path):
    # CONTROL
    top, sub = _tree(tmp_path, "tree")
    E.add_or_update_entry(sub, "Keep", "When x, do y", body="KEEP BODY")
    rep = E.rename_entry(sub, "keep", "kept-v1.2")
    assert rep["renamed"] is True, rep
    assert "KEEP BODY" in _body(top, "kept-v1.2")


def test_relocate_refuses_a_traversal_slug_planted_in_a_pointer(tmp_path):
    top1, sub1 = _tree(tmp_path, "tree1")
    top2, sub2 = _tree(tmp_path, "tree2")
    (Path(top1) / "CLAUDE.md").write_text("tree1 top\n", encoding="utf-8")
    _plant_pointer(sub1, "../../CLAUDE")
    rep = E.relocate_entry(sub1, sub2, "../../CLAUDE")
    assert rep["relocated"] is False and "not a valid slug" in (rep["refused"] or ""), rep
    assert (Path(top2) / "CLAUDE.md").read_text(encoding="utf-8") == "x\n"


# ---- amend-pinned --type: a re-type with no body must re-type, and only a known kind -------------

def test_amend_pinned_type_alone_retypes_the_stored_body(tmp_path):
    top, sub = _tree(tmp_path, "tree")
    E.add_or_update_entry(sub, "Pinned rule", "When x, do y", body="prose", type_="project",
                          pin=True, slug="pinned-rule")
    E.amend_pinned_entry(sub, "pinned-rule", type_="feedback")
    text = _body(top, "pinned-rule")
    assert "type: feedback" in text and "type: project" not in text
    assert text.rstrip("\n").endswith("prose")                       # the prose is untouched
    assert [e.pin for e in E.read_store(sub)[1]] == [True]


def test_add_type_alone_on_update_retypes_the_stored_body(tmp_path):
    top, sub = _tree(tmp_path, "tree")
    E.add_or_update_entry(sub, "Rule", "When x, do y", body="prose", type_="project", slug="rule")
    E.add_or_update_entry(sub, "Rule", "When x, do y", type_="reference", slug="rule")
    assert "type: reference" in _body(top, "rule")


def test_amend_pinned_without_type_or_body_keeps_the_stored_type(tmp_path):
    # CONTROL: a hook-only amend leaves the kind alone.
    top, sub = _tree(tmp_path, "tree")
    E.add_or_update_entry(sub, "Pinned rule", "When x, do y", body="prose", type_="feedback",
                          pin=True, slug="pinned-rule")
    E.amend_pinned_entry(sub, "pinned-rule", hook="When x happens, do y.")
    assert "type: feedback" in _body(top, "pinned-rule")


def test_retype_of_an_unframed_body_frames_it_with_the_new_kind(tmp_path):
    top, sub = _tree(tmp_path, "tree")
    E.add_or_update_entry(sub, "Bare", "When x, do y", body="prose", slug="bare")
    us.put_body(top, "bare", "bare prose, no frontmatter")          # a hand-written legacy body
    E.add_or_update_entry(sub, "Bare", "When x, do y", type_="user", slug="bare")
    text = _body(top, "bare")
    assert text.startswith("---\nname: bare\n") and "type: user" in text
    assert "bare prose, no frontmatter" in text


def test_cli_amend_pinned_rejects_an_unknown_type(tmp_path, capsys):
    top, sub = _tree(tmp_path, "tree")
    E.add_or_update_entry(sub, "Pinned rule", "When x, do y", body="prose", pin=True,
                          slug="pinned-rule")
    with pytest.raises(SystemExit) as exc:
        E.main(["amend-pinned", "--proj", sub, "--slug", "pinned-rule", "--type", "bogus"])
    assert exc.value.code == 2
    assert "type: bogus" not in _body(top, "pinned-rule")


def test_api_rejects_an_unknown_type(tmp_path):
    top, sub = _tree(tmp_path, "tree")
    with pytest.raises(ValueError):
        E.add_or_update_entry(sub, "T", "When x, do y", body="b", type_="bogus")
    assert not us.body_path(top, "t").exists()


# ---- --proj is resolved before the excluded-altitude check --------------------------------------

def test_cli_add_accepts_a_relative_proj_and_writes_where_the_cwd_is(tmp_path, monkeypatch, capsys):
    top, sub = _tree(tmp_path, "tree")
    monkeypatch.chdir(sub)
    rc = E.main(["add", "--proj", ".", "--title", "Rel", "--hook", "When x, do y", "--body", "b"])
    assert rc == 0, capsys.readouterr()
    assert _slugs(sub) == ["rel"]
    assert us.body_path(top, "rel").is_file()                        # the TREE's store, not sub's
    assert not (Path(sub) / us.STORE_DIRNAME).exists()


def test_a_symlink_to_home_is_refused_like_home_itself(tmp_path, _isolated_home):
    link = tmp_path / "homelink"
    try:
        os.symlink(str(_isolated_home), str(link), target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable here")
    with pytest.raises(ValueError):
        E.add_or_update_entry(str(link), "T", "When x, do y", body="b")
    assert not (_isolated_home / "CLAUDE.local.md").exists()
    assert not (_isolated_home / us.STORE_DIRNAME).exists()


def test_home_itself_is_still_refused(_isolated_home):
    # CONTROL
    with pytest.raises(ValueError):
        E.add_or_update_entry(str(_isolated_home), "T", "When x, do y", body="b")
    assert not (_isolated_home / "CLAUDE.local.md").exists()


def test_an_absolute_proj_below_the_tree_is_still_accepted(tmp_path):
    # CONTROL
    top, sub = _tree(tmp_path, "tree")
    assert E.add_or_update_entry(sub, "Abs", "When x, do y", body="b") == "abs"


# ---- a wrapped --hook-file reaches the pointer line whole ---------------------------------------

def test_cli_add_hook_file_that_wraps_keeps_the_whole_hook(tmp_path, capsys):
    top, sub = _tree(tmp_path, "tree")
    hook_file = tmp_path / "hook.txt"
    hook_file.write_text("When a long hook wraps,\ndo the thing.\n", encoding="utf-8")
    rc = E.main(["add", "--proj", sub, "--title", "Wrapped", "--hook-file", str(hook_file),
                 "--body", "b"])
    assert rc == 0, capsys.readouterr()
    ptrs = us.parse_pointer_index(sig.claude_local_md_path(sub).read_text(encoding="utf-8"))[1]
    assert [(p.slug, p.hook) for p in ptrs] == [("wrapped", "When a long hook wraps, do the thing.")]
    assert "description: When a long hook wraps, do the thing." in _body(top, "wrapped")
    E.heal(sub)                                                      # a re-render keeps it whole
    ptrs = us.parse_pointer_index(sig.claude_local_md_path(sub).read_text(encoding="utf-8"))[1]
    assert ptrs[0].hook == "When a long hook wraps, do the thing."


def test_duplicate_slug_in_two_blocks_updates_the_copy_everyone_reads(tmp_path):
    top, sub = _tree(tmp_path, "tree")
    us.put_body(top, "feedback-x", "---\nname: feedback-x\n---\n\nbody")
    new_block = "%s\n%s%s" % (us.INDEX_BEGIN, us.render_pointer_index(
        "s", [us.Pointer(slug="feedback-x", title="X", hook="When old, do old")]), us.INDEX_END)
    legacy = ("%s\n- [X](uuid:1234) - When old, do old <!-- bx:slug=feedback-x -->\n%s"
              % (us.LEGACY_INDEX_BEGIN, us.LEGACY_INDEX_END))
    sig.claude_local_md_path(sub).write_text(new_block + "\n\n" + legacy + "\n", encoding="utf-8")
    E.add_or_update_entry(sub, "X", "When NEW, do NEW", slug="feedback-x")
    assert [(r.slug, r.hook) for r in us.resolve(sub)][0] == ("feedback-x", "When NEW, do NEW")
    text = sig.claude_local_md_path(sub).read_text(encoding="utf-8")
    assert text.count("feedback-x") == 1
