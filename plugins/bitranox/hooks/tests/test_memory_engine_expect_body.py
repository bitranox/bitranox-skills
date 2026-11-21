"""upsert_entry's `expect_body`: a write derived from a body read before the call refuses when
that body changed in between, instead of overwriting the change.

The change here comes from a real second process, the way a concurrent writer reaches the store.
All content ASCII.
"""

import subprocess
import sys
from pathlib import Path

import memory_engine as E
import pytest
import uuid_store as us

HOOKS = str(Path(E.__file__).resolve().parent)
HOOK = "When a write is derived from a body read earlier, refuse it once the body changed."


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("BITRANOX_MEMORY_WRITES", raising=False)
    return h


def _level(tmp_path):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    return str(root)


def _amend_in_another_process(level, slug, prose):
    script = (f"import sys\nsys.path.insert(0, {HOOKS!r})\nimport memory_engine as E\n"
              f"E.upsert_entry({level!r}, '', '', body={prose!r}, slug={slug!r}, must_exist=True)\n")
    done = subprocess.run([sys.executable, "-c", script], capture_output=True, encoding="utf-8",
                          timeout=120, check=False)
    assert done.returncode == 0, done.stderr


def test_a_body_changed_since_the_read_refuses_and_writes_nothing(tmp_path):
    level = _level(tmp_path)
    slug = E.add_or_update_entry(level, "Derived", HOOK, body="FIRST PROSE")
    body = us.body_path(level, slug)
    read = E.read_store_text(body)
    _amend_in_another_process(level, slug, "AMENDED PROSE")
    after_amend = (body.read_text(encoding="utf-8"),
                   Path(level, "CLAUDE.local.md").read_text(encoding="utf-8"))
    with pytest.raises(E.BodyChanged) as exc:
        E.upsert_entry(level, "", "", body="DERIVED FROM FIRST", slug=slug, must_exist=True,
                       expect_body=read)
    assert exc.value.slug == slug
    assert (body.read_text(encoding="utf-8"),
            Path(level, "CLAUDE.local.md").read_text(encoding="utf-8")) == after_amend


def test_an_unchanged_body_is_written(tmp_path):
    level = _level(tmp_path)
    slug = E.add_or_update_entry(level, "Derived", HOOK, body="FIRST PROSE")
    body = us.body_path(level, slug)
    read = E.read_store_text(body)
    assert E.upsert_entry(level, "", "", body="DERIVED FROM FIRST", slug=slug, must_exist=True,
                          expect_body=read) == (slug, False)
    text = body.read_text(encoding="utf-8")
    assert "DERIVED FROM FIRST" in text and "FIRST PROSE" not in text
