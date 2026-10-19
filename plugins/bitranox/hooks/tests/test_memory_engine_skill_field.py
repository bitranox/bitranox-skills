"""Tests for the optional `skill` field on a curated fact (`add --skill`, `metadata: skill:`).

A lesson learned while following a skill belongs in that skill; meta-self-improve step 2 routes it
there. When a fact is written as well, because the rule also binds work outside the skill, the
field records which skill it is tied to, so a later sweep can find the facts that belong in one.

It behaves like `type`: written into the body's frontmatter, kept on an update that does not name
it, replaced by one that does, and set in place by an update that passes no body. It is validated
before any write, because the value lands inside the frontmatter. All content ASCII.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us

BRIDGE = Path(__file__).resolve().parents[1] / "mod_bridge.py"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
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


def _body(proj, slug):
    return us.body_path(proj, slug).read_text(encoding="utf-8")


def _frontmatter(text):
    return text.split("\n---\n", 1)[0]


def test_add_writes_the_skill_into_the_frontmatter(proj):
    slug = E.add_or_update_entry(proj, "Quote shell text", "When passing text to a shell, use a file.",
                                 body="prose", type_="feedback", skill="bitranox:compuse-git",
                                 slug="quote-shell-text", scope_default="lvl")
    front = _frontmatter(_body(proj, slug))
    assert "\n  type: feedback" in front
    assert "\n  skill: bitranox:compuse-git" in front
    assert E._body_skill(_body(proj, slug)) == "bitranox:compuse-git"


def test_no_skill_writes_no_skill_line(proj):
    slug = E.add_or_update_entry(proj, "Plain", "When X, do Y.", body="prose", slug="plain-fact",
                                 scope_default="lvl")
    assert "skill:" not in _body(proj, slug)
    assert E._body_skill(_body(proj, slug)) == ""


def test_update_with_a_new_body_keeps_the_stored_skill(proj):
    # The same trap the type preservation closes: re-framing a new body from the arguments alone
    # would drop the field, and nothing reports a field that silently disappeared.
    slug = E.add_or_update_entry(proj, "R", "When X, do Y.", body="v1", skill="bitranox:devops-bmk",
                                 slug="keeps-skill", scope_default="lvl")
    E.add_or_update_entry(proj, "R", "When X, do Y.", body="v2", slug=slug)
    text = _body(proj, slug)
    assert E._body_skill(text) == "bitranox:devops-bmk" and "v2" in text


def test_an_explicit_skill_wins_on_update(proj):
    slug = E.add_or_update_entry(proj, "R", "When X, do Y.", body="v1", skill="bitranox:devops-bmk",
                                 slug="skill-wins", scope_default="lvl")
    E.add_or_update_entry(proj, "R", "When X, do Y.", body="v2", skill="bitranox:compuse-git",
                          slug=slug)
    text = _body(proj, slug)
    assert E._body_skill(text) == "bitranox:compuse-git"
    assert text.count("skill:") == 1


def test_a_skill_with_no_body_tags_the_stored_fact_in_place(proj):
    slug = E.add_or_update_entry(proj, "R", "When X, do Y.", body="the prose", type_="reference",
                                 slug="tag-in-place", scope_default="lvl")
    before = _body(proj, slug)
    E.add_or_update_entry(proj, "R", "When X, do Y.", skill="bitranox:infra-proxmox", slug=slug)
    after = _body(proj, slug)
    assert E._body_skill(after) == "bitranox:infra-proxmox"
    assert E._body_type(after) == "reference"                       # the kind is untouched
    assert after.split("\n---\n", 1)[1] == before.split("\n---\n", 1)[1]   # prose untouched


def test_a_skill_line_in_the_prose_does_not_answer_for_the_frontmatter(proj):
    slug = E.add_or_update_entry(proj, "R", "When X, do Y.", body="  skill: not-this-one\n",
                                 slug="prose-skill-line", scope_default="lvl")
    assert E._body_skill(_body(proj, slug)) == ""


@pytest.mark.parametrize("bad", ["two words", "bitranox:x\ninjected: 1", "UPPER", ":lead",
                                 "a" * 129, "bitranox:x:y"])
def test_an_invalid_skill_is_refused_before_any_write(proj, bad):
    with pytest.raises(E.InvalidSkill):
        E.add_or_update_entry(proj, "R", "When X, do Y.", body="b", skill=bad, slug="never-written",
                              scope_default="lvl")
    assert not us.body_path(proj, "never-written").exists()


def test_amend_pinned_keeps_the_stored_skill(proj):
    slug = E.add_or_update_entry(proj, "Iron", "When X happens, do Y.", body="prose", pin=True,
                                 skill="bitranox:compuse-git", slug="iron-keeps-skill",
                                 scope_default="lvl")
    E.amend_pinned_entry(proj, slug, body="amended")
    assert E._body_skill(_body(proj, slug)) == "bitranox:compuse-git"


def test_the_cli_add_takes_skill(proj, capsys):
    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", "When X, do Y.", "--body", "b",
                 "--slug", "cli-skill", "--skill", "bitranox:compuse-ssh"])
    assert rc == 0
    assert E._body_skill(_body(proj, "cli-skill")) == "bitranox:compuse-ssh"


def test_the_cli_refuses_an_invalid_skill_as_a_refusal(proj, capsys):
    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", "When X, do Y.", "--body", "b",
                 "--slug", "cli-bad-skill", "--skill", "two words"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "skill" in (captured.out + captured.err)
    assert not us.body_path(proj, "cli-bad-skill").exists()


def test_the_mod_bridge_passes_skill_through(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    level = tmp_path / "lvl"
    level.mkdir()
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
           "HOME": str(home), "USERPROFILE": str(home)}
    payload = {"tool": "memory_add", "input": {"title": "T", "hook": "When x, y.", "body": "b",
                                               "level": str(level), "type": "feedback",
                                               "skill": "bitranox:compuse-git"}}
    p = subprocess.run([sys.executable, str(BRIDGE)], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, cwd=str(tmp_path), env=env)
    out = json.loads(p.stdout.decode("ascii"))
    assert p.returncode == 0, out
    assert E._body_skill(_body(str(level), out["data"]["slug"])) == "bitranox:compuse-git"


@pytest.mark.parametrize("bad", [7, "two words"])
def test_the_mod_bridge_refuses_an_invalid_skill_by_kind(tmp_path, bad):
    # A refusal, not an internal error: the caller must learn the field was wrong, by name.
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    level = tmp_path / "lvl"
    level.mkdir()
    env = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
           "HOME": str(home), "USERPROFILE": str(home)}
    payload = {"tool": "memory_add", "input": {"title": "T", "hook": "When x, y.", "body": "b",
                                               "level": str(level), "type": "feedback",
                                               "skill": bad}}
    p = subprocess.run([sys.executable, str(BRIDGE)], input=json.dumps(payload).encode("utf-8"),
                       capture_output=True, cwd=str(tmp_path), env=env)
    out = json.loads(p.stdout.decode("ascii"))
    assert (p.returncode, out["error"]["kind"]) == (1, "InvalidSkill"), out
