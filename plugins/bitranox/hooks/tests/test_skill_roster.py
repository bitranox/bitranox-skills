"""Tests for skill_roster.py: the skill router's option list is the session's INSTALLED skills.

The router used to glob only this plugin's own skills/ dir, so a skill from another plugin, a
project skill or a Claude Code built-in could never be offered - 4 of the 6 skills no replay arm
ever proposed were of that kind. The session's real listing is in its transcript as a
`skill_listing` attachment, but on the FIRST prompt it is usually not written yet (50 of 51
sessions measured), so the roster falls back to a per-project cache, then to the shipped glob.
"""
import json
import os

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
    """A transcript file; a str record is written verbatim, so a test can plant a broken line."""
    p = tmp_path / name
    p.write_text("\n".join(r if isinstance(r, str) else json.dumps(r) for r in records) + "\n",
                 encoding="utf-8")
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


# ---- a budget-trimmed listing line --------------------------------------------------------------
# When the listing would exceed its budget the harness drops descriptions and leaves the line as a
# bare `- <name>`. The fixture below is synthetic but has the real shape: described entries, one
# running over several lines, and trimmed ones, both bare and plugin-prefixed, interleaved.

TRIMMED_LISTING = "\n".join([
    "- bitranox:files-edit-xml: Use when editing XML.",
    "- ralph-loop:cancel-ralph",
    "- claude-api: Reference for the Claude API.",
    "TRIGGER - read BEFORE opening.",
    "- update-config",
    "- code-review:code-review",
    "- code-review: Review the current diff.",
    "- loop",
])
TRIMMED_NAMES = ["bitranox:files-edit-xml", "ralph-loop:cancel-ralph", "claude-api",
                 "update-config", "code-review:code-review", "code-review", "loop"]


def _glued(roster, names):
    """Descriptions carrying another listed skill's line - the corruption a bare line caused."""
    return {k: v for k, v in roster.items() if any(" - %s" % n in v for n in names)}


def test_a_bare_name_line_opens_its_own_entry_instead_of_joining_the_previous_one():
    got = SR.parse_listing("- alpha: text\n- ghost\n- beta: b", ["alpha", "ghost", "beta"])
    assert got["alpha"] == "text" and got["beta"] == "b"
    assert "ghost" in got


def test_a_bare_name_line_with_trailing_whitespace_still_opens():
    got = SR.parse_listing("- alpha: text\n- ghost  \n- beta: b", ["alpha", "ghost", "beta"])
    assert got["alpha"] == "text" and got["ghost"] == "ghost"


def test_a_trimmed_listing_parses_with_no_description_glued_onto_another():
    got = SR.parse_listing(TRIMMED_LISTING, TRIMMED_NAMES)
    assert _glued(got, TRIMMED_NAMES) == {}
    assert got["files-edit-xml"] == "Use when editing XML."
    assert got["claude-api"] == "Reference for the Claude API. TRIGGER - read BEFORE opening."
    assert got["code-review"] == "Review the current diff."
    assert list(got) == ["files-edit-xml", "ralph-loop:cancel-ralph", "claude-api",
                         "update-config", "code-review:code-review", "code-review", "loop"]


def test_a_name_that_prefixes_a_longer_listed_name_does_not_open_on_its_line():
    # "- code-review:code-review" must not open `code-review` with ":code-review" as its text.
    got = SR.parse_listing("- code-review:code-review\n- code-review: Review the diff.",
                           ["code-review:code-review", "code-review"])
    assert got["code-review"] == "Review the diff."
    assert got["code-review:code-review"] == "code-review:code-review"


def test_a_trimmed_skill_with_no_file_anywhere_is_offered_under_its_name_alone():
    # A Claude Code built-in has no SKILL.md on disk: the name is the only text there is.
    got = SR.parse_listing("- alpha: text\n- update-config", ["alpha", "update-config"])
    assert got["update-config"] == "update-config"


def test_a_listed_name_with_no_line_at_all_is_still_offered():
    assert SR.parse_listing("- alpha: text", ["alpha", "ghost"]) == {"alpha": "text",
                                                                      "ghost": "ghost"}


def test_a_bare_repeat_does_not_overwrite_a_described_line():
    got = SR.parse_listing("- alpha: text\n- beta: b\n- alpha", ["alpha", "beta"])
    assert got["alpha"] == "text"


def test_a_continuation_line_that_reads_like_a_listed_name_does_not_open_early():
    # "- beta" here is prose INSIDE alpha's own multi-line description (more text follows on the
    # next line), not a real trimmed entry for beta - the real beta entry is the line after that.
    # Entries appear in `names` order in every real listing, so a bare candidate line only opens
    # when nothing follows it or what follows is itself a real entry line.
    content = "- alpha: Use with:\n- beta\nand more alpha text\n- beta: real beta"
    got = SR.parse_listing(content, ["alpha", "beta"])
    assert got["alpha"] == "Use with: - beta and more alpha text"
    assert got["beta"] == "real beta"


# ---- where a trimmed skill's description comes from ---------------------------------------------

def _skill_md(path, description):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nname: x\ndescription: %s\n---\n\n# body\n" % description,
                    encoding="utf-8")


def _install_plugin(home, plugin, root):
    f = home / ".claude" / "plugins" / "installed_plugins.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": 2, "plugins": {}}
    if f.exists():
        data = json.loads(f.read_text(encoding="utf-8"))
    data["plugins"]["%s@some-market" % plugin] = [{"scope": "user", "installPath": str(root)}]
    f.write_text(json.dumps(data), encoding="utf-8")


def test_a_trimmed_skill_of_this_plugin_takes_its_shipped_description():
    shipped = SR.classifier.load_skill_descriptions()
    got = SR.parse_listing("- bitranox:files-edit-xml", ["bitranox:files-edit-xml"])
    assert got["files-edit-xml"] == shipped["files-edit-xml"]


def test_a_trimmed_skill_of_another_plugin_takes_its_installed_skill_md(home, tmp_path):
    root = tmp_path / "cache" / "typesafe" / "0.5.7"
    _skill_md(root / "skills" / "typesafe-ai" / "SKILL.md", "Build AI software with TypeSafe.")
    _install_plugin(home, "typesafe", root)
    got = SR.parse_listing("- typesafe:typesafe-ai", ["typesafe:typesafe-ai"])
    assert got["typesafe:typesafe-ai"] == "Build AI software with TypeSafe."


def test_a_trimmed_plugin_command_takes_its_command_file_description(home, tmp_path):
    root = tmp_path / "cache" / "ralph-loop" / "1.0.0"
    cmd = root / "commands" / "cancel-ralph.md"
    cmd.parent.mkdir(parents=True)
    cmd.write_text('---\ndescription: "Cancel active Ralph Loop"\nallowed-tools: []\n---\n',
                   encoding="utf-8")
    _install_plugin(home, "ralph-loop", root)
    got = SR.parse_listing("- ralph-loop:cancel-ralph", ["ralph-loop:cancel-ralph"])
    assert got["ralph-loop:cancel-ralph"] == "Cancel active Ralph Loop"


def test_a_trimmed_project_skill_is_found_from_the_cwd_and_its_ancestors(tmp_path):
    proj = tmp_path / "proj"
    _skill_md(proj / ".claude" / "skills" / "provmm-build" / "SKILL.md", "Build provmm.")
    sub = proj / "src" / "deep"
    sub.mkdir(parents=True)
    got = SR.parse_listing("- provmm-build", ["provmm-build"], cwd=str(sub))
    assert got["provmm-build"] == "Build provmm."
    # Without the cwd the same line has nothing to resolve against: the name alone.
    assert SR.parse_listing("- provmm-build", ["provmm-build"])["provmm-build"] == "provmm-build"


def test_a_trimmed_user_command_without_front_matter_takes_its_first_line(home):
    cmd = home / ".claude" / "commands" / "tfbpr.md"
    cmd.parent.mkdir(parents=True)
    cmd.write_text("Test, Fix, Bump, Push, Release - full release pipeline.\n\nExecute.\n",
                   encoding="utf-8")
    got = SR.parse_listing("- tfbpr", ["tfbpr"])
    assert got["tfbpr"] == "Test, Fix, Bump, Push, Release - full release pipeline."


def test_a_trimmed_user_skill_is_found_under_home(home):
    _skill_md(home / ".claude" / "skills" / "toolbox" / "SKILL.md", "Check the toolbox first.")
    got = SR.parse_listing("- toolbox", ["toolbox"])
    assert got["toolbox"] == "Check the toolbox first."


def test_a_multi_line_front_matter_description_is_read_whole(home):
    md = home / ".claude" / "skills" / "folded" / "SKILL.md"
    md.parent.mkdir(parents=True)
    md.write_text("\ufeff---\nname: folded\ndescription: >-\n  Use when one thing\n  or another.\n"
                  "other: x\n---\n", encoding="utf-8")
    assert SR.parse_listing("- folded", ["folded"])["folded"] == "Use when one thing or another."


@pytest.mark.parametrize("text, want", [
    # With no `description:` the harness describes a skill or command by its first paragraph.
    ("Test, Fix, Bump - full pipeline.\n\nExecute the steps.\n",
     "Test, Fix, Bump - full pipeline."),
    ("# Title\n\nFirst paragraph\nwraps here.\n\nSecond.\n", "First paragraph wraps here."),
    ("---\nname: x\n---\n\n# Heading\nBody line.\n", "Body line."),
    ("---\nname: x\n---\n", ""),
    # Front matter that never closes reads as the shared reader splits it, as the gate does.
    ("---\nname: x\ndescription: unclosed\n", "unclosed"),
    ("", ""),
    ("---\ndescription: 'quoted'\n---\nBody.\n", "quoted"),
    ("---\ndescription: plain start\n  continued here\nname: x\n---\n",
     "plain start continued here"),
    ("---\ndescription: |\n  literal\n  block\n---\n", "literal block"),
])
def test_the_skill_file_description_reader(tmp_path, text, want):
    md = tmp_path / "SKILL.md"
    md.write_text(text, encoding="utf-8")
    assert SR._file_description(md) == want  # noqa: SLF001 - the reader is the unit


def test_a_skill_file_reads_through_the_shared_front_matter_reader(tmp_path):
    # One reader for every consumer: whatever skill_frontmatter reads, the roster offers,
    # decoded from its quotes or block header.
    md = tmp_path / "SKILL.md"
    md.write_text("---\nname: x\ndescription: >-\n  Use when folded\n  # not a comment here\n"
                  "---\n", encoding="utf-8")
    raw = SR.skill_frontmatter.description(md)
    assert SR._file_description(md) == SR.skill_frontmatter.scalar_text(raw)  # noqa: SLF001
    assert SR._file_description(md) == "Use when folded # not a comment here"  # noqa: SLF001


def test_a_missing_or_undecodable_skill_file_never_raises(tmp_path):
    md = tmp_path / "SKILL.md"
    md.write_bytes(b"---\ndescription: \xff\xfe bad\n---\n")
    assert SR._file_description(md) == "\ufffd\ufffd bad"  # noqa: SLF001
    assert SR._file_description(tmp_path / "missing.md") == ""  # noqa: SLF001


def test_malformed_installed_plugin_entries_are_skipped(home, tmp_path):
    root = tmp_path / "cache" / "typesafe"
    _skill_md(root / "skills" / "typesafe-ai" / "SKILL.md", "Build AI software.")
    f = home / ".claude" / "plugins" / "installed_plugins.json"
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"plugins": {"typesafe@m": ["junk", {"installPath": 3},
                                                        {"installPath": str(root)}],
                                         "other@m": "not a list"}}), encoding="utf-8")
    got = SR.parse_listing("- typesafe:typesafe-ai", ["typesafe:typesafe-ai"])
    assert got["typesafe:typesafe-ai"] == "Build AI software."


def test_a_broken_installed_plugins_file_degrades_to_the_name(home):
    f = home / ".claude" / "plugins" / "installed_plugins.json"
    f.parent.mkdir(parents=True)
    f.write_text("{not json", encoding="utf-8")
    got = SR.parse_listing("- typesafe:typesafe-ai", ["typesafe:typesafe-ai"])
    assert got["typesafe:typesafe-ai"] == "typesafe:typesafe-ai"


def test_a_described_line_never_consults_the_skill_file(home):
    # The listing's own text is what the session saw; a file is only the fallback.
    _skill_md(home / ".claude" / "skills" / "toolbox" / "SKILL.md", "file text")
    assert SR.parse_listing("- toolbox: listed text", ["toolbox"]) == {"toolbox": "listed text"}


# ---- a bare name and this plugin's name for the same skill --------------------------------------

def test_a_local_skill_sharing_a_bare_name_with_this_plugins_keeps_both():
    got = SR.parse_listing("- bitranox:meta-self-improve: shipped\n- meta-self-improve: local",
                           ["bitranox:meta-self-improve", "meta-self-improve"])
    assert got == {"bitranox:meta-self-improve": "shipped", "meta-self-improve": "local"}


def test_with_no_collision_this_plugins_skills_stay_keyed_bare():
    got = SR.parse_listing("- bitranox:meta-self-improve: shipped\n- other: local",
                           ["bitranox:meta-self-improve", "other"])
    assert got == {"meta-self-improve": "shipped", "other": "local"}


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


def test_a_truncated_listing_line_is_skipped_and_the_next_one_read(tmp_path):
    good = _listing(BASE)
    cut = json.dumps(good)[:120]
    assert '"skill_listing"' in cut  # it passes the substring filter and must fail the decode
    t = _transcript(tmp_path, [cut, good])
    assert set(SR.listing_from_transcript(t)) == {"files-edit-xml", "typesafe:typesafe-ai",
                                                  "update-config"}


def test_a_marker_line_that_is_not_a_listing_attachment_is_skipped(tmp_path):
    # Both pass the substring filter: an attachment of another type naming the marker, and a
    # JSON line that is not an object at all.
    other = {"type": "attachment", "attachment": {"type": "hook_note", "text": "skill_listing"}}
    t = _transcript(tmp_path, [_listing(BASE), other, '["skill_listing"]'])
    assert set(SR.listing_from_transcript(t)) == {"files-edit-xml", "typesafe:typesafe-ai",
                                                  "update-config"}


def test_a_bare_name_arriving_in_a_delta_does_not_overwrite_this_plugins_skill(tmp_path):
    t = _transcript(tmp_path, [_listing([("bitranox:meta-self-improve", "shipped")]),
                               _listing([("meta-self-improve", "local")], initial=False)])
    assert SR.listing_from_transcript(t) == {"bitranox:meta-self-improve": "shipped",
                                             "meta-self-improve": "local"}


def test_a_trimmed_line_in_a_delta_resolves_like_one_in_the_full_listing(tmp_path, home):
    _skill_md(home / ".claude" / "skills" / "toolbox" / "SKILL.md", "Check the toolbox first.")
    delta = {"type": "attachment", "attachment": {
        "type": "skill_listing", "content": "- toolbox", "names": ["toolbox"],
        "isInitial": False}}
    t = _transcript(tmp_path, [_listing(BASE), delta])
    assert SR.listing_from_transcript(t)["toolbox"] == "Check the toolbox first."


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


def test_an_unchanged_listing_does_not_rewrite_the_cache(tmp_path):
    t = _transcript(tmp_path, [_listing(BASE)])
    SR.installed_skills(t, "/p/a")
    path = SR._cache_file("/p/a")  # noqa: SLF001 - the seam
    os.utime(path, ns=(10**9, 10**9))
    SR.installed_skills(t, "/p/a")
    assert path.stat().st_mtime_ns == 10**9
    # Control: a changed listing does rewrite it.
    SR.installed_skills(_transcript(tmp_path, [_listing(BASE[:2])], name="b.jsonl"), "/p/a")
    assert path.stat().st_mtime_ns != 10**9


def test_an_unwritable_cache_never_costs_the_roster(tmp_path, home):
    # The audit dir is a FILE, so the cache cannot be created; the transcript still answers.
    audit = home / ".claude" / "self-improve-audit"
    audit.write_text("in the way", encoding="utf-8")
    skills, source = SR.installed_skills(_transcript(tmp_path, [_listing(BASE)]), "/p/a")
    assert source == SR.SOURCE_TRANSCRIPT and "update-config" in skills


def test_a_failed_cache_write_leaves_no_temp_file_behind(tmp_path):
    # A directory where the cache file belongs makes the final rename fail. The temp file must
    # not stay behind, and its name must be private to the writer: a fixed `.tmp` name is shared
    # by every concurrent session of the project.
    path = SR._cache_file("/p/a")  # noqa: SLF001 - the seam
    path.mkdir(parents=True)
    SR.installed_skills(_transcript(tmp_path, [_listing(BASE)]), "/p/a")
    assert sorted(p.name for p in path.parent.iterdir()) == [path.name]


@pytest.mark.parametrize("data", [[], {}, {"x": 1}, "a string"])
def test_a_cache_of_the_wrong_shape_falls_back_to_the_shipped_skills(data):
    path = SR._cache_file("/p/shape")  # noqa: SLF001 - the seam
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    assert SR.installed_skills("", "/p/shape")[1] == SR.SOURCE_SHIPPED


def test_the_installed_roster_offers_trimmed_skills_resolved_from_the_project(tmp_path):
    proj = tmp_path / "proj"
    _skill_md(proj / ".claude" / "skills" / "provmm-build" / "SKILL.md", "Build provmm.")
    rec = {"type": "attachment", "attachment": {
        "type": "skill_listing",
        "content": "- bitranox:compuse-git: Use when running git.\n- provmm-build\n- loop",
        "names": ["bitranox:compuse-git", "provmm-build", "loop"], "isInitial": True}}
    skills, source = SR.installed_skills(_transcript(tmp_path, [rec]), str(proj))
    assert source == SR.SOURCE_TRANSCRIPT
    assert skills == {"compuse-git": "Use when running git.", "provmm-build": "Build provmm.",
                      "loop": "loop"}
