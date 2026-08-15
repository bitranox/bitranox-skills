"""An autonomous writer must not be able to overwrite a human-owned fact."""
import pathlib
import subprocess
import sys

HOOKS = pathlib.Path(__file__).resolve().parents[1]
ENGINE = HOOKS / "memory_engine.py"


def _add(proj, title, hook, body, *extra):
    body_file = proj / "_body.md"
    body_file.write_text(body, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(ENGINE), "add", "--proj", str(proj),
         "--type", "reference", "--title", title, "--hook", hook,
         "--body-file", str(body_file), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def _seed(tmp_path):
    """A minimal tree top: a dir with a CLAUDE.md is an anchor."""
    top = tmp_path / "tree"
    top.mkdir()
    (top / "CLAUDE.md").write_text("# top\n", encoding="utf-8")
    return top


BODY = "A fact.\n\n**Why:** test.\n\n**How to apply:** test.\n"


def test_owner_defaults_to_agent_and_is_not_rendered(tmp_path):
    top = _seed(tmp_path)
    r = _add(top, "Agent owned", "When testing, do the thing.", BODY)
    assert r.returncode == 0, r.stderr
    text = (top / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "bx:owner" not in text, text


def test_owner_human_is_recorded_on_the_pointer_line(tmp_path):
    top = _seed(tmp_path)
    r = _add(top, "Human owned", "When testing, do the thing.", BODY,
             "--owner", "human")
    assert r.returncode == 0, r.stderr
    text = (top / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "bx:owner=human" in text, text


def test_plain_add_refuses_to_overwrite_a_human_owned_fact(tmp_path):
    top = _seed(tmp_path)
    first = _add(top, "Human owned", "When testing, do the thing.", BODY,
                 "--owner", "human")
    assert first.returncode == 0, first.stderr
    slug = first.stdout.strip().splitlines()[0]

    second = _add(top, "Human owned", "When testing, do something ELSE.", BODY,
                  "--slug", slug)
    assert second.returncode == 1, second.stdout
    assert "refused" in (second.stdout + second.stderr).lower()

    text = (top / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "do the thing" in text, "the original hook must survive the refusal"
    assert "something ELSE" not in text


def test_amend_human_owned_is_the_only_way_through(tmp_path):
    top = _seed(tmp_path)
    first = _add(top, "Human owned", "When testing, do the thing.", BODY,
                 "--owner", "human")
    slug = first.stdout.strip().splitlines()[0]

    body_file = top / "_body2.md"
    body_file.write_text(BODY, encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(ENGINE), "amend-human-owned", "--proj", str(top),
         "--slug", slug, "--hook", "When testing, do the AMENDED thing.",
         "--body-file", str(body_file)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert r.returncode == 0, r.stderr
    text = (top / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "AMENDED" in text
    assert "bx:owner=human" in text, "ownership must survive an amend"
