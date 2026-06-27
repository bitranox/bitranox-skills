"""Tests for adopt_skill.py (the adopting-external-skills mechanical helper).

Behaviour is exercised against synthetic trees in tmp_path. No real network or git is used:
the end-to-end tests run on local-path sources and monkeypatch subprocess to prove the helper
never issues a commit/push/PR/clone.

All content is ASCII.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import adopt_skill as AS

# --------------------------------------------------------------------------
# License fixtures
# --------------------------------------------------------------------------

MIT = ("MIT License\n\nCopyright (c) 2024 Test Author\n\n"
       "Permission is hereby granted, free of charge, to any person obtaining a copy "
       "of this software and associated documentation files...\n")
APACHE = ("Apache License\nVersion 2.0, January 2004\n\nCopyright 2024 Test Author\n"
          "Licensed under the Apache License, Version 2.0...\n")
ISC = ("ISC License\n\nCopyright (c) 2024 Test Author\n\n"
       "Permission to use, copy, modify, and/or distribute this software for any purpose...\n")
BSD3 = ("Copyright (c) 2024 Test Author\n\n"
        "Redistribution and use in source and binary forms, with or without modification...\n"
        "3. Neither the name of the copyright holder nor the names of its contributors...\n")
BSD2 = ("Copyright (c) 2024 Test Author\n\n"
        "Redistribution and use in source and binary forms, with or without modification...\n")
GPL = ("GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n\nCopyright (c) 2024 Test Author\n")
AGPL = ("GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3\n")


# --------------------------------------------------------------------------
# classify_license_text
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    (MIT, "MIT"), (APACHE, "Apache-2.0"), (ISC, "ISC"),
    (BSD3, "BSD-3-Clause"), (BSD2, "BSD-2-Clause"),
    (GPL, "REJECT"), (AGPL, "REJECT"),
    ("", None), ("some random text", None),
])
def test_classify_license_text(text, expected):
    assert AS.classify_license_text(text) == expected


def test_gpl_with_mit_phrase_still_rejected():
    mixed = GPL + "\npermission is hereby granted, free of charge\n"
    assert AS.classify_license_text(mixed) == "REJECT"


@pytest.mark.parametrize("sid,expected", [
    ("MIT", "MIT"), ("Apache-2.0", "Apache-2.0"), ("ISC", "ISC"),
    ("BSD", "BSD-3-Clause"), ("GPL-3.0", "REJECT"), ("AGPL-3.0", "REJECT"),
    ("Unlicense", None), ("", None),
])
def test_classify_license_id(sid, expected):
    assert AS.classify_license_id(sid) == expected


# --------------------------------------------------------------------------
# find_license (searches the whole tree, beyond a skill subdir)
# --------------------------------------------------------------------------

def _tree(tmp_path, files):
    for rel, content in files.items():
        fp = tmp_path / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
    return tmp_path


def test_find_license_accepts_mit_with_copyright(tmp_path):
    _tree(tmp_path, {"LICENSE": MIT})
    lic = AS.find_license(tmp_path)
    assert lic["status"] == "accept"
    assert lic["id"] == "MIT"
    assert lic["copyright"] == "Copyright (c) 2024 Test Author"


def test_find_license_rejects_gpl(tmp_path):
    _tree(tmp_path, {"LICENSE": GPL})
    assert AS.find_license(tmp_path)["status"] == "reject"


def test_find_license_absent_when_none(tmp_path):
    _tree(tmp_path, {"README.md": "no license here\n"})
    assert AS.find_license(tmp_path)["status"] == "absent"


def test_find_license_from_manifest_field(tmp_path):
    _tree(tmp_path, {"package.json": '{"name": "x", "license": "MIT"}\n'})
    lic = AS.find_license(tmp_path)
    assert lic["status"] == "accept" and lic["id"] == "MIT"


def test_find_license_searches_repo_root_not_just_subdir(tmp_path):
    # License at repo root; the skill lives in a subdir with no LICENSE of its own.
    _tree(tmp_path, {"LICENSE": MIT, "skills/foo/SKILL.md": "# Foo\n"})
    assert AS.find_license(tmp_path)["status"] == "accept"


def test_apache_captures_notice(tmp_path):
    _tree(tmp_path, {"LICENSE": APACHE, "NOTICE": "Product X\nCopyright 2024 Test Author\n"})
    lic = AS.find_license(tmp_path)
    assert lic["id"] == "Apache-2.0"
    assert "Product X" in lic["notice"]


# --------------------------------------------------------------------------
# name + cross-ref helpers
# --------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Git Worktrees", "git-worktrees"), ("my_cool_skill", "my-cool-skill"),
    ("Already-Fine", "already-fine"), ("--weird__name--", "weird-name"),
])
def test_normalize_name(raw, expected):
    assert AS.normalize_name(raw) == expected


def test_derive_name_from_url_and_path():
    assert AS.derive_name("https://github.com/x/cool-skill.git", "") == "cool-skill"
    assert AS.derive_name("/some/dir/my-skill", "") == "my-skill"
    assert AS.derive_name("/some/dir/SKILL.md", "") == "SKILL"
    assert AS.derive_name("https://x/y", "pkg/inner") == "inner"


def test_rewrite_cross_refs():
    text = "Use oldname here. See superpowers:git-worktrees and obra:thing."
    out, n = AS.rewrite_cross_refs(text, "oldname", "newname")
    assert "newname here" in out
    assert "bitranox:git-worktrees" in out
    assert "bitranox:thing" in out
    assert n == 3


def test_rewrite_cross_refs_noop_when_same_name():
    text = "no references to rewrite"
    out, n = AS.rewrite_cross_refs(text, "x", "x")
    assert out == text and n == 0


def test_is_url():
    assert AS.is_url("https://github.com/x/y")
    assert AS.is_url("git@github.com:x/y.git")
    assert not AS.is_url("/local/path")
    assert not AS.is_url("./rel/path")


# --------------------------------------------------------------------------
# scaffolding + attribution
# --------------------------------------------------------------------------

def test_ships_scripts_and_scaffold(tmp_path):
    skill = _tree(tmp_path, {"SKILL.md": "# S\n", "helper.py": "x = 1\n"})
    script = AS.ships_scripts(skill)
    assert script and script.name == "helper.py"
    stub = AS.scaffold_tests(skill, script)
    assert stub.exists()
    assert (skill / "tests" / "conftest.py").exists()
    assert "import helper" in stub.read_text(encoding="utf-8")


def test_scaffold_skipped_when_tests_present(tmp_path):
    skill = _tree(tmp_path, {"SKILL.md": "# S\n", "helper.py": "x = 1\n",
                             "tests/test_helper.py": "def test_x():\n    assert True\n"})
    assert AS.scaffold_tests(skill, skill / "helper.py") is None


def test_ships_scripts_ignores_tests_dir(tmp_path):
    skill = _tree(tmp_path, {"SKILL.md": "# S\n", "tests/test_x.py": "def test():\n    pass\n"})
    assert AS.ships_scripts(skill) is None


def test_add_credit_line_after_h1_idempotent(tmp_path):
    md = tmp_path / "SKILL.md"
    md.write_text("# Title\n\nbody text\n", encoding="utf-8")
    assert AS.add_credit_line(md, "upstream x (MIT)", "MIT") is True
    text = md.read_text(encoding="utf-8")
    assert "> Adapted from upstream x (MIT) (MIT)." in text
    lines = text.splitlines()
    assert lines[0] == "# Title"  # credit goes right after H1
    # second call does not duplicate
    assert AS.add_credit_line(md, "upstream x (MIT)", "MIT") is False
    assert text.count("> Adapted from") == 1


def test_append_notice_format_and_idempotent(tmp_path):
    notices = tmp_path / "THIRD_PARTY_NOTICES.md"
    notices.write_text("# Third-Party Notices\n", encoding="utf-8")
    assert AS.append_notice(notices, "foo", "Foo upstream", "https://x/foo", "MIT",
                            "Copyright (c) 2024 Test Author", MIT, "") is True
    text = notices.read_text(encoding="utf-8")
    assert "### foo" in text
    assert "Copyright (c) 2024 Test Author" in text
    assert "MIT license text:" in text
    # idempotent
    assert AS.append_notice(notices, "foo", "Foo upstream", "https://x/foo", "MIT",
                            "Copyright (c) 2024 Test Author", MIT, "") is False
    assert notices.read_text(encoding="utf-8").count("### foo") == 1


# --------------------------------------------------------------------------
# End-to-end + negative controls (no network, no commit/push/PR)
# --------------------------------------------------------------------------

def _fake_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "plugins/bitranox/.claude-plugin").mkdir(parents=True)
    (repo / "plugins/bitranox/.claude-plugin/plugin.json").write_text(
        '{"name": "bitranox", "version": "1.0.0"}', encoding="utf-8")
    skills = repo / "plugins/bitranox/skills"
    skills.mkdir(parents=True)
    (repo / "plugins/bitranox/THIRD_PARTY_NOTICES.md").write_text(
        "# Third-Party Notices\n", encoding="utf-8")
    return repo, skills


def _fake_source(tmp_path, license_text=MIT, with_script=True):
    src = tmp_path / "upstream-skill"
    src.mkdir()
    (src / "SKILL.md").write_text("# Upstream Skill\n\nUse upstream-skill. See superpowers:x.\n",
                                  encoding="utf-8")
    (src / "LICENSE").write_text(license_text, encoding="utf-8")
    if with_script:
        (src / "run.py").write_text("VALUE = 1\n", encoding="utf-8")
    return src


@pytest.fixture
def record_subprocess(monkeypatch):
    calls = []

    def fake_run(cmd, *a, **k):
        calls.append(list(cmd))

        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""
        return R()

    monkeypatch.setattr(AS.subprocess, "run", fake_run)
    return calls


def test_adopt_mit_happy_path(tmp_path, record_subprocess, capsys):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path)
    AS.main([str(src), "--dest", str(skills)])

    dest = skills / "upstream-skill"
    assert dest.is_dir()
    skill_md = (dest / "SKILL.md").read_text(encoding="utf-8")
    assert "> Adapted from upstream-skill (upstream) (MIT)." in skill_md
    assert "bitranox:x" in skill_md  # superpowers: rewritten
    assert (dest / "tests" / "conftest.py").exists()
    assert (dest / "tests" / "test_run.py").exists()
    notices = (repo / "plugins/bitranox/THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "### upstream-skill" in notices
    out = capsys.readouterr().out
    assert "LICENSE GATE: ACCEPTED (MIT" in out


def test_adopt_never_commits_or_pushes(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path)
    AS.main([str(src), "--dest", str(skills)])
    flat = " ".join(" ".join(c) for c in record_subprocess)
    for forbidden in ("commit", "push", "pr", "clone", "uninstall"):
        assert forbidden not in flat, f"helper issued a forbidden subprocess: {forbidden}"


def test_adopt_gpl_blocks_and_scaffolds_nothing(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path, license_text=GPL)
    with pytest.raises(SystemExit) as exc:
        AS.main([str(src), "--dest", str(skills)])
    assert "REJECTED" in str(exc.value)
    assert not (skills / "upstream-skill").exists()


def test_adopt_no_license_blocks_and_asks(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path, license_text="no license here\n")
    # Remove the LICENSE file entirely so nothing is detected.
    (src / "LICENSE").unlink()
    with pytest.raises(SystemExit) as exc:
        AS.main([str(src), "--dest", str(skills)])
    msg = str(exc.value)
    assert "NO LICENSE FOUND" in msg and "do NOT assume MIT" in msg
    assert not (skills / "upstream-skill").exists()


def test_adopt_local_path_does_no_clone(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path)
    AS.main([str(src), "--dest", str(skills)])
    # The only subprocess that may run is the read-only gate; none is a clone.
    assert all("clone" not in " ".join(c) for c in record_subprocess)


# --------------------------------------------------------------------------
# Category-prefix validation (skill-taxonomy.json)
# --------------------------------------------------------------------------


def _write_taxonomy(repo):
    (repo / "plugins/bitranox/skill-taxonomy.json").write_text(
        json.dumps({"categories": {"coding": {"subs": ["python"]}}, "legacy": []}), encoding="utf-8")


def test_adopt_rejects_uncategorized_name(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    _write_taxonomy(repo)
    src = _fake_source(tmp_path)
    with pytest.raises(SystemExit) as exc:
        AS.main([str(src), "--name", "foobar", "--dest", str(skills)])
    assert "category prefix" in str(exc.value)
    assert not (skills / "foobar").exists()


def test_adopt_accepts_categorized_name(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    _write_taxonomy(repo)
    src = _fake_source(tmp_path)
    AS.main([str(src), "--name", "coding-foobar", "--dest", str(skills)])
    assert (skills / "coding-foobar").is_dir()


def test_adopt_no_taxonomy_skips_validation(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)  # no skill-taxonomy.json
    src = _fake_source(tmp_path)
    AS.main([str(src), "--name", "foobar", "--dest", str(skills)])
    assert (skills / "foobar").is_dir()  # validation skipped, adoption proceeds


# --------------------------------------------------------------------------
# Static guard: the source carries no plugin-removal / settings operations
# --------------------------------------------------------------------------

def test_source_has_no_forbidden_operations():
    src = Path(AS.__file__).read_text(encoding="utf-8")
    for token in ("uninstall", "settings.json", "~/.claude", "pr create", "git push"):
        assert token not in src, f"adopt_skill.py must not reference {token!r}"
