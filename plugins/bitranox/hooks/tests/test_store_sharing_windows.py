"""Store reads and renames wait out a file another handle holds for a moment (Windows only).

On Windows an open or rename that meets a file at the instant another session's write replaces
it is refused with a PermissionError. Each test here holds the file with a second handle opened
with no sharing at all for 0.3 s, the way a replace or a scanner holds it, and checks the store
waits that out rather than failing the verb or skipping the file.
"""

import sys
import threading
from pathlib import Path
from typing import Self

import memory_engine as E
import pytest
import uuid_store as us

if sys.platform == "win32":
    import _winapi

pytestmark = pytest.mark.skipif(sys.platform != "win32",
                                reason="only Windows refuses an open by share mode")

_LEGACY_UUID = "11111111-0000-5000-8000-000000000000"


_FILE_SHARE_READ = 1


class _HeldExclusive:
    """The file at `path` opened sharing only `share`, closed `seconds` later from a second
    thread: with no sharing every other open or rename of it is refused meanwhile, with
    _FILE_SHARE_READ only a rename (or a write) is."""

    def __init__(self, path: Path, seconds: float, share: int = 0) -> None:
        self.handle = _winapi.CreateFile(str(path), _winapi.GENERIC_READ, share, 0,
                                         _winapi.OPEN_EXISTING, 0, 0)
        self.timer = threading.Timer(seconds, _winapi.CloseHandle, args=(self.handle,))

    def __enter__(self) -> Self:
        self.timer.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.timer.join()


def _tree(root: Path, *levels: str) -> list[str]:
    """A tree at `root` (CLAUDE.md and the central store there) with a CLAUDE.md at each level."""
    root.mkdir(parents=True)
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    out = []
    for rel in levels:
        d = root / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        out.append(str(d))
    return out


def _line(level: str, slug: str) -> us.Pointer | None:
    text = (Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8")
    return next((p for p in us.parse_pointer_index(text)[1] if p.slug == slug), None)


def test_a_store_read_waits_out_a_file_another_handle_holds(tmp_path):
    """read_store_text, the reader of every level file and body, returns the text of a held file
    instead of raising TreeWalkError("unreadable")."""
    path = tmp_path / "CLAUDE.local.md"
    path.write_text("held\n", encoding="utf-8")
    with _HeldExclusive(path, 0.3):
        assert us.read_store_text(path) == "held\n"


def test_an_add_never_takes_over_a_slug_while_its_owning_level_is_held(tmp_path):
    """The owner walk skips a level it cannot read, so a refused open of the owning level read as
    "nobody owns this slug" and the add created the fact a second time."""
    root = tmp_path / "tree"
    here, owner = _tree(root, "proj/here", "proj/owner")
    us.add_pointer(owner, "fact", "Owned", "When racing, the owner's line.")
    with _HeldExclusive(Path(owner) / "CLAUDE.local.md", 0.3), \
            pytest.raises(E.SlugOwnedElsewhere):
        E.upsert_entry(here, "T1", "When racing 1, keep it.", body="prose 1", slug="fact")
    assert not (Path(here) / "CLAUDE.local.md").exists() or _line(here, "fact") is None
    assert not us.body_path(str(root), "fact").exists()


def test_a_legacy_body_held_for_a_moment_is_still_archived_by_the_update_that_flips_it(tmp_path):
    """The first update of a legacy entry moves its old sharded body to `.archive/`. A refused
    rename fell into the best-effort `pass`, so the legacy file stayed behind for good beside the
    new slug-named body. The holder shares reading, the way a scanner does, so the update's read of
    the body goes through and only the rename meets the refusal."""
    root = tmp_path / "tree"
    (proj,) = _tree(root, "proj")
    legacy = us.legacy_body_path(str(root), _LEGACY_UUID)
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("OLD\n", encoding="utf-8")
    (Path(proj) / "CLAUDE.local.md").write_text(
        f"{us.LEGACY_INDEX_BEGIN}\n# Memory index\n"
        f"- [Old](uuid:{_LEGACY_UUID}) - When old, keep it. <!-- bx:slug=old-fact -->\n"
        f"{us.LEGACY_INDEX_END}\n", encoding="utf-8")
    with _HeldExclusive(legacy, 0.3, share=_FILE_SHARE_READ):
        E.upsert_entry(proj, "Old", "When old, keep it newly.", body="NEW", slug="old-fact")
    assert not legacy.exists()
    assert us.body_path(str(root), "old-fact").is_file()
