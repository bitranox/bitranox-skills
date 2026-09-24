"""Tests for skill_roster.py: the skill router's option list is the session's INSTALLED skills.

The router used to glob only this plugin's own skills/ dir, so a skill from another plugin, a
project skill or a Claude Code built-in could never be offered - 4 of the 6 skills no replay arm
ever proposed were of that kind. The session's real listing is in its transcript as a
`skill_listing` attachment, but on the FIRST prompt it is usually not written yet (50 of 51
sessions measured), so the roster falls back to a per-project cache, then to the shipped glob.
"""
import json

import pytest

import skill_roster as SR


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _listing(names_descs, initial=True):
    content = "\n".join("- %s: %s" % (n, d) for n, d in names_descs)
    return {"type": "attachment", "attachment": {
        "type": "skill_listing", "content": content, "names": [n for n, _d in names_descs],
        "skillCount": len(names_descs), "isInitial": initial}}


def _transcript(tmp_path, records, name="t.jsonl"):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(p)


def _prompt(text):
    return {"type": "user", "origin": {"kind": "human"}, "message": {"content": text}}


BASE = [("bitranox:files-edit-xml", "Use when editing XML."),
        ("typesafe:typesafe-ai", "Build AI-powered software with TypeSafe."),
        ("update-config", "Use this skill to configure the Claude Code harness.")]


# ---- parsing one listing ----------------------------------------------------------------------

def test_parse_keys_this_plugin_bare_and_every_other_skill_by_its_full_name():
    rec = _listing(BASE)["attachment"]
    got = SR.parse_listing(rec["content"], rec["names"])
    assert got == {"files-edit-xml": "Use when editing XML.",
                   "typesafe:typesafe-ai": "Build AI-powered software with TypeSafe.",
                   "update-config": "Use this skill to configure the Claude Code harness."}


def test_parse_keeps_a_description_that_runs_over_several_lines():
    content = ("- claude-api: Reference for the Claude API.\nTRIGGER - read BEFORE opening.\n"
               "SKIP only when another provider.\n- loop: Run a prompt on an interval.")
    got = SR.parse_listing(content, ["claude-api", "loop"])
    assert got["claude-api"] == ("Reference for the Claude API. TRIGGER - read BEFORE opening. "
                                 "SKIP only when another provider.")
    assert got["loop"] == "Run a prompt on an interval."


def test_parse_does_not_split_on_a_dash_line_that_names_no_listed_skill():
    # A description line may itself start with "- "; only a listed NAME opens a new entry.
    content = "- alpha: first line\n- not a skill: still alpha\n- beta: second"
    got = SR.parse_listing(content, ["alpha", "beta"])
    assert got == {"alpha": "first line - not a skill: still alpha", "beta": "second"}


def test_parse_drops_a_listed_name_with_no_description():
    assert SR.parse_listing("- alpha: text", ["alpha", "ghost"]) == {"alpha": "text"}


# ---- reading the transcript -------------------------------------------------------------------

def test_no_listing_in_the_transcript_reads_as_none(tmp_path):
    assert SR.listing_from_transcript(_transcript(tmp_path, [_prompt("hi")])) is None
    assert SR.listing_from_transcript(str(tmp_path / "missing.jsonl")) is None
    assert SR.listing_from_transcript("") is None


def test_the_latest_full_listing_wins(tmp_path):
    t = _transcript(tmp_path, [_listing(BASE), _prompt("x"),
                               _listing([("bitranox:compuse-git", "Use when running git.")])])
    assert SR.listing_from_transcript(t) == {"compuse-git": "Use when running git."}


def test_a_delta_after_the_full_listing_adds_its_skills(tmp_path):
    t = _transcript(tmp_path, [_listing(BASE), _listing([("docx", "Word files.")], initial=False)])
    got = SR.listing_from_transcript(t)
    assert set(got) == {"files-edit-xml", "typesafe:typesafe-ai", "update-config", "docx"}


def test_a_delta_before_a_later_full_listing_is_superseded(tmp_path):
    t = _transcript(tmp_path, [_listing(BASE), _listing([("docx", "Word files.")], initial=False),
                               _listing(BASE)])
    assert "docx" not in SR.listing_from_transcript(t)


def test_a_delta_with_no_full_listing_before_it_is_not_a_roster(tmp_path):
    # One added skill is not the installed set; offering it alone would hide every other skill.
    t = _transcript(tmp_path, [_listing([("docx", "Word files.")], initial=False)])
    assert SR.listing_from_transcript(t) is None


def test_a_prompt_that_merely_mentions_skill_listing_is_not_a_listing(tmp_path):
    t = _transcript(tmp_path, [_prompt('read the "skill_listing" attachment'),
                               "not json {", _listing(BASE)])
    assert set(SR.listing_from_transcript(t)) == {"files-edit-xml", "typesafe:typesafe-ai",
                                                  "update-config"}


# ---- the roster the router uses ---------------------------------------------------------------

def test_a_transcript_listing_is_used_and_cached_for_its_project(tmp_path):
    t = _transcript(tmp_path, [_listing(BASE)])
    skills, source = SR.installed_skills(t, "/p/a")
    assert source == SR.SOURCE_TRANSCRIPT and "typesafe:typesafe-ai" in skills
    # The next session's FIRST prompt has no listing on disk yet: the cache answers.
    empty = _transcript(tmp_path, [_prompt("first prompt")], name="new.jsonl")
    again, source = SR.installed_skills(empty, "/p/a")
    assert source == SR.SOURCE_CACHE and again == skills


def test_the_cache_is_per_project_so_project_skills_do_not_leak(tmp_path):
    SR.installed_skills(_transcript(tmp_path, [_listing(BASE + [("provmm-build", "p")])]), "/p/a")
    skills, source = SR.installed_skills("", "/p/b")
    assert source == SR.SOURCE_SHIPPED and "provmm-build" not in skills


def test_with_no_listing_and_no_cache_the_shipped_skills_answer():
    skills, source = SR.installed_skills("", "/p/none")
    assert source == SR.SOURCE_SHIPPED
    assert "files-edit-xml" in skills and len(skills) >= 20


def test_a_corrupt_cache_falls_back_to_the_shipped_skills(tmp_path):
    SR.installed_skills(_transcript(tmp_path, [_listing(BASE)]), "/p/a")
    SR._cache_file("/p/a").write_text("{not json", encoding="utf-8")  # noqa: SLF001 - the seam
    assert SR.installed_skills("", "/p/a")[1] == SR.SOURCE_SHIPPED
