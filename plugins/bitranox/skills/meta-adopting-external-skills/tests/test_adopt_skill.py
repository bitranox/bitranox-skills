"""Tests for adopt_skill.py (the adopting-external-skills mechanical helper).

Behaviour is exercised against synthetic trees in tmp_path. No real network or git is used:
the end-to-end tests run on local-path sources and monkeypatch subprocess to prove the helper
never issues a commit/push/PR/clone.

All content is ASCII.
"""
import json
import os
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
    text = "See superpowers:oldname, superpowers:git-worktrees and obra:thing."
    out, n = AS.rewrite_cross_refs(text, "oldname", "newname")
    assert "bitranox:newname," in out
    assert "bitranox:git-worktrees" in out
    assert "bitranox:thing" in out
    assert n == 3


@pytest.mark.parametrize("text", [
    "Run `git commit` before you push.",
    "git is the tool this skill drives.",
    "Use `git-worktrees` for isolation.",
    "See superpowers:git-worktrees.",       # a different skill that merely starts with the name
    "Files live in .git/hooks/.",
])
def test_the_name_as_an_ordinary_word_is_left_alone(text):
    """An upstream skill called `git` must not rewrite the git TOOL wherever the word appears."""
    out, _n = AS.rewrite_cross_refs(text, "git", "devops-git")
    assert "devops-git" not in out, out


@pytest.mark.parametrize("text,expected", [
    ("See superpowers:git for more.", "See bitranox:devops-git for more."),
    ("Invoke bitranox:git first.", "Invoke bitranox:devops-git first."),
    ("Run skills/git/run.py.", "Run skills/devops-git/run.py."),
    ("Run skills\\git\\run.py.", "Run skills\\devops-git\\run.py."),
])
def test_the_name_as_the_skills_identity_is_rewritten(text, expected):
    """Control: a skill reference or a path under skills/ IS the skill's identity."""
    out, n = AS.rewrite_cross_refs(text, "git", "devops-git")
    assert (out, n) == (expected, 1)


def test_rewrite_identity_keeps_crlf_and_a_title_that_says_more():
    text = "---\r\nname: git\r\n---\r\n# git\r\n\r\nbody\r\n"
    out, n = AS.rewrite_identity(text, "git", "devops-git")
    assert (out, n) == ("---\r\nname: devops-git\r\n---\r\n# devops-git\r\n\r\nbody\r\n", 2)
    titled = "---\nname: git\n---\n# git for teams\n"
    out, n = AS.rewrite_identity(titled, "git", "devops-git")
    assert (out, n) == ("---\nname: devops-git\n---\n# git for teams\n", 1)


def test_an_upstream_skill_named_git_keeps_the_git_tool_end_to_end(tmp_path):
    repo, skills = _fake_repo(tmp_path)
    src = _tree(tmp_path / "up" / "git", {
        "SKILL.md": "---\nname: git\ndescription: Use when driving git\n---\n# git\n\n"
                    "Run `git commit -m x`, then see superpowers:git and skills/git/run.py.\n",
        "LICENSE": MIT,
    })
    r = subprocess.run([sys.executable, AS.__file__, str(src), "--name", "devops-git",
                        "--dest", str(skills)], capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    text = (skills / "devops-git" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: devops-git\n" in text and "\n# devops-git\n" in text
    assert "`git commit -m x`" in text and "Use when driving git" in text
    assert "bitranox:devops-git" in text and "skills/devops-git/run.py" in text
    assert b"left for review" in r.stdout      # the prose mentions are reported, not rewritten


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
    assert "'helper.py'" in stub.read_text(encoding="utf-8")      # loaded by path


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
    assert "MIT License text:" in text
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


def test_adopt_gpl_blocks_and_scaffolds_nothing(tmp_path, record_subprocess, capsys):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path, license_text=GPL)
    assert AS.main([str(src), "--dest", str(skills)]) == 1       # the gate said no
    assert "REJECTED" in capsys.readouterr().err
    assert not (skills / "upstream-skill").exists()


def test_adopt_no_license_blocks_and_asks(tmp_path, record_subprocess, capsys):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path, license_text="no license here\n")
    # Remove the LICENSE file entirely so nothing is detected.
    (src / "LICENSE").unlink()
    assert AS.main([str(src), "--dest", str(skills)]) == 1
    msg = capsys.readouterr().err
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


def test_adopt_rejects_uncategorized_name(tmp_path, record_subprocess, capsys):
    repo, skills = _fake_repo(tmp_path)
    _write_taxonomy(repo)
    src = _fake_source(tmp_path)
    assert AS.main([str(src), "--name", "foobar", "--dest", str(skills)]) == 2
    assert "category prefix" in capsys.readouterr().err
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


# --------------------------------------------------------------------------
# License gate: every declared id counts, not the first one found
# --------------------------------------------------------------------------

def test_a_gpl_manifest_beats_an_mit_spdx_header(tmp_path):
    _tree(tmp_path, {"package.json": '{"license": "GPL-3.0-only"}\n',
                     "vendor.js": "// SPDX-License-Identifier: MIT\n"})
    assert AS.find_license(tmp_path)["status"] == "reject"


def test_a_proprietary_license_file_is_not_overridden_by_an_mit_spdx_header(tmp_path):
    _tree(tmp_path, {"LICENSE": "Copyright 2024 X. All rights reserved. Proprietary.\n",
                     "x.py": "# SPDX-License-Identifier: MIT\n"})
    lic = AS.find_license(tmp_path)
    assert lic["status"] == "absent" and lic["id"] is None
    assert "LICENSE" in lic["where"]


@pytest.mark.parametrize("first, second", [("a.py", "z.py"), ("z.py", "a.py")])
def test_any_gpl_spdx_header_rejects_whatever_the_walk_order(tmp_path, first, second):
    _tree(tmp_path, {"LICENSE-placeholder.txt": "x\n",
                     first: "# SPDX-License-Identifier: MIT\n",
                     second: "# SPDX-License-Identifier: GPL-3.0-or-later\n"})
    assert AS.find_license(tmp_path)["status"] == "reject"


def test_an_mit_license_file_with_a_gpl_spdx_file_is_rejected(tmp_path):
    _tree(tmp_path, {"LICENSE": MIT, "lib/x.py": "# SPDX-License-Identifier: GPL-2.0-only\n"})
    assert AS.find_license(tmp_path)["status"] == "reject"


def test_an_unrecognised_declared_id_needs_a_human(tmp_path):
    _tree(tmp_path, {"LICENSE": MIT, "package.json": '{"license": "UNLICENSED"}\n'})
    lic = AS.find_license(tmp_path)
    assert lic["status"] == "absent" and "UNLICENSED" in lic["where"]


def test_spdx_and_manifest_alone_still_accept(tmp_path):
    _tree(tmp_path, {"package.json": '{"license": "MIT"}\n',
                     "x.py": "# SPDX-License-Identifier: MIT\n"})
    lic = AS.find_license(tmp_path)
    assert lic["status"] == "accept" and lic["id"] == "MIT"


def test_bsd4_advertising_clause_is_not_accepted_as_bsd3():
    bsd4 = BSD3 + "3. All advertising materials mentioning features or use of this software...\n"
    assert AS.classify_license_text(bsd4) is None


def test_bsd4_license_file_stops_the_gate(tmp_path):
    bsd4 = BSD3 + "3. All advertising materials mentioning features or use of this software...\n"
    _tree(tmp_path, {"LICENSE": bsd4})
    assert AS.find_license(tmp_path)["status"] == "absent"


# --------------------------------------------------------------------------
# Credit line placement: never inside front matter or a code fence
# --------------------------------------------------------------------------

def _credit(tmp_path, text):
    md = tmp_path / "SKILL.md"
    md.write_bytes(text.encode("utf-8"))
    AS.add_credit_line(md, "up (upstream)", "MIT")
    return md.read_bytes().decode("utf-8")


def test_no_h1_puts_the_credit_after_the_front_matter(tmp_path):
    out = _credit(tmp_path, "---\nname: s\ndescription: d\n---\n## Usage\nbody\n")
    assert out.startswith("---\nname: s\ndescription: d\n---\n")
    assert "---\n\n> Adapted from up (upstream) (MIT).\n" in out


def test_a_comment_inside_front_matter_is_not_the_h1(tmp_path):
    out = _credit(tmp_path, "---\n# upstream: foo\nname: s\n---\n# Title\nbody\n")
    assert out.startswith("---\n# upstream: foo\nname: s\n---\n# Title\n\n> Adapted from")


def test_a_hash_line_inside_a_code_fence_is_not_the_h1(tmp_path):
    out = _credit(tmp_path, "```bash\n# install\nmake\n```\n# Title\nbody\n")
    assert "```bash\n# install\nmake\n```\n# Title\n\n> Adapted from" in out


def test_no_front_matter_and_no_h1_prepends(tmp_path):
    out = _credit(tmp_path, "just text\n")
    assert out.startswith("> Adapted from up (upstream) (MIT).\n\njust text")


def test_crlf_skill_md_keeps_crlf(tmp_path):
    out = _credit(tmp_path, "# Title\r\n\r\nbody\r\n")
    assert out == "# Title\r\n\r\n> Adapted from up (upstream) (MIT).\r\n\r\nbody\r\n"


def test_notice_keeps_the_file_line_endings(tmp_path):
    notices = tmp_path / "THIRD_PARTY_NOTICES.md"
    notices.write_bytes(b"# Third-Party Notices\n")
    AS.append_notice(notices, "foo", "Foo", "", "MIT", "", MIT, "")
    assert b"\r\n" not in notices.read_bytes()


# --------------------------------------------------------------------------
# Test scaffold must collect for a scripts/ subdir or a hyphenated name
# --------------------------------------------------------------------------

@pytest.mark.parametrize("rel", ["tool.py", "scripts/tool.py", "scripts/do-thing.py"])
def test_the_scaffolded_stub_collects_and_passes(tmp_path, rel):
    skill = _tree(tmp_path / "skill", {"SKILL.md": "# S\n", rel: "VALUE = 1\n"})
    stub = AS.scaffold_tests(skill, AS.ships_scripts(skill))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                        str(stub.parent)], capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 passed" in r.stdout


# --------------------------------------------------------------------------
# End to end: a SKILL.md at the source root, .git, marker, taxonomy, report
# --------------------------------------------------------------------------

def _root_skill(tmp_path, name="up2"):
    """A skill whose SKILL.md sits at the source ROOT, next to a src/ dir it references."""
    src = tmp_path / name
    (src / "src").mkdir(parents=True)
    (src / "src" / "main.py").write_text("X = 1\n", encoding="utf-8")
    (src / "SKILL.md").write_text(
        "---\nname: %s\ndescription: Use when running %s.\n---\n# %s\n\n"
        "Run %s. Layout: src/ holds the code; see src/main.py.\n" % (name, name, name, name),
        encoding="utf-8")
    (src / "LICENSE").write_text(MIT, encoding="utf-8")
    return src


def test_a_root_level_skill_md_renames_the_skill_and_leaves_src_alone(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    src = _root_skill(tmp_path)
    assert AS.main([str(src), "--name", "coding-newname", "--dest", str(skills)]) == 0
    text = (skills / "coding-newname" / "SKILL.md").read_text(encoding="utf-8")
    assert "name: coding-newname" in text and "name: up2" not in text
    assert "Run up2." in text        # prose: reported for review, never rewritten
    assert "src/ holds the code; see src/main.py" in text


def test_a_source_git_dir_is_not_copied(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    src = _root_skill(tmp_path)
    (src / ".git").mkdir()
    (src / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (src / "__pycache__").mkdir()
    AS.main([str(src), "--name", "coding-newname", "--dest", str(skills)])
    dest = skills / "coding-newname"
    assert not (dest / ".git").exists() and not (dest / "__pycache__").exists()
    assert (dest / "SKILL.md").is_file()


def test_no_marketplace_marker_stops_before_copying_anything(tmp_path, capsys):
    skills = tmp_path / "nomarker" / "skills"
    skills.mkdir(parents=True)
    src = _fake_source(tmp_path)
    assert AS.main([str(src), "--name", "coding-nm", "--dest", str(skills)]) == 2
    assert "not inside a marketplace checkout" in capsys.readouterr().err
    assert not (skills / "coding-nm").exists()


def test_a_malformed_taxonomy_stops_instead_of_skipping_the_rule(tmp_path, record_subprocess,
                                                                 capsys):
    repo, skills = _fake_repo(tmp_path)
    (repo / "plugins/bitranox/skill-taxonomy.json").write_text(
        '{"categories": {"coding": {}},}', encoding="utf-8")
    src = _fake_source(tmp_path)
    assert AS.main([str(src), "--name", "foobar", "--dest", str(skills)]) == 2
    assert "skill-taxonomy.json" in capsys.readouterr().err
    assert not (skills / "foobar").exists()


def test_follow_up_touches_the_domains_list_only_for_a_new_category(tmp_path, record_subprocess,
                                                                   capsys):
    repo, skills = _fake_repo(tmp_path)
    AS.main([str(_fake_source(tmp_path)), "--name", "coding-foo", "--dest", str(skills)])
    out = capsys.readouterr().out
    assert "Add `coding-foo` to the domains list" not in out
    assert "only if" in out and "`coding`" in out


def test_report_says_skipped_when_a_credit_line_was_already_there(tmp_path, record_subprocess,
                                                                 capsys):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path)
    (src / "SKILL.md").write_text("# Up\n\n> Adapted from obra/superpowers (MIT).\n\nbody\n",
                                  encoding="utf-8")
    AS.main([str(src), "--name", "coding-up", "--dest", str(skills)])
    out = capsys.readouterr().out
    assert "credit line SKIPPED (already present)" in out


def test_report_says_skipped_when_the_notice_entry_already_existed(tmp_path, record_subprocess,
                                                                  capsys):
    repo, skills = _fake_repo(tmp_path)
    notices = repo / "plugins/bitranox/THIRD_PARTY_NOTICES.md"
    notices.write_text("# Third-Party Notices\n\n---\n\n### coding-up\n\nold\n", encoding="utf-8")
    AS.main([str(_fake_source(tmp_path)), "--name", "coding-up", "--dest", str(skills)])
    assert "notice entry SKIPPED (already present)" in capsys.readouterr().out


def test_the_only_subprocess_is_the_read_only_gate(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    gate = repo / "plugins" / "bitranox" / "hooks" / "repo-gate.py"
    gate.parent.mkdir(parents=True)
    gate.write_text("print('gate')\n", encoding="utf-8")
    AS.main([str(_fake_source(tmp_path)), "--dest", str(skills)])
    assert record_subprocess == [[sys.executable, str(gate), "--ci"]]


def test_the_license_gate_stop_exits_one_and_an_error_exits_two(tmp_path, capsys):
    repo, skills = _fake_repo(tmp_path)
    src = _fake_source(tmp_path)
    (src / "LICENSE").unlink()
    assert AS.main([str(src), "--dest", str(skills)]) == 1
    assert "NO LICENSE FOUND" in capsys.readouterr().err
    assert AS.main([str(tmp_path / "missing"), "--dest", str(skills)]) == 2
    assert "does not exist" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Fetch: URL clone, clone failure, missing git, --subdir, several skills
# --------------------------------------------------------------------------

def _bare_repo(tmp_path):
    """A local bare git repo holding one skill at its root, reachable as a file:// URL."""
    if not AS.shutil.which("git"):
        pytest.skip("git not installed")
    work = _root_skill(tmp_path / "w", "coolskill")
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_CONFIG_NOSYSTEM="1")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-q", "-m", "x"]):
        subprocess.run(cmd, cwd=str(work), check=True, env=env, capture_output=True)
    bare = tmp_path / "coolskill.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(work), str(bare)], check=True, env=env,
                   capture_output=True)
    return bare.as_uri()


def test_a_file_url_is_cloned_and_its_git_dir_is_not_copied(tmp_path):
    url = _bare_repo(tmp_path)
    repo, skills = _fake_repo(tmp_path)
    assert AS.main([url, "--name", "coding-cool", "--dest", str(skills)]) == 0
    dest = skills / "coding-cool"
    assert (dest / "SKILL.md").is_file() and not (dest / ".git").exists()
    assert "name: coding-cool" in (dest / "SKILL.md").read_text(encoding="utf-8")


def test_a_failing_clone_exits_two_with_the_git_error(tmp_path, capsys):
    if not AS.shutil.which("git"):
        pytest.skip("git not installed")
    repo, skills = _fake_repo(tmp_path)
    url = (tmp_path / "nope.git").as_uri()
    assert AS.main([url, "--dest", str(skills)]) == 2
    assert "git clone failed" in capsys.readouterr().err


def test_a_url_without_git_on_path_exits_two(tmp_path, monkeypatch, capsys):
    repo, skills = _fake_repo(tmp_path)
    empty = tmp_path / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert AS.main(["https://example.invalid/x.git", "--dest", str(skills)]) == 2
    assert "git not found" in capsys.readouterr().err


def test_subdir_picks_one_skill_end_to_end(tmp_path, record_subprocess):
    repo, skills = _fake_repo(tmp_path)
    src = tmp_path / "multi"
    for name in ("alpha", "beta"):
        _tree(src / "skills" / name, {"SKILL.md": "---\nname: %s\n---\n# %s\n" % (name, name)})
    (src / "LICENSE").write_text(MIT, encoding="utf-8")
    assert AS.main([str(src), "--subdir", "skills/beta", "--name", "coding-beta",
                    "--dest", str(skills)]) == 0
    assert "name: coding-beta" in (skills / "coding-beta" / "SKILL.md").read_text(encoding="utf-8")


def test_several_skills_without_subdir_exits_two_and_lists_them(tmp_path, capsys):
    repo, skills = _fake_repo(tmp_path)
    src = tmp_path / "multi"
    for name in ("alpha", "beta"):
        _tree(src / "skills" / name, {"SKILL.md": "# %s\n" % name})
    (src / "LICENSE").write_text(MIT, encoding="utf-8")
    assert AS.main([str(src), "--dest", str(skills)]) == 2
    err = capsys.readouterr().err
    assert "multiple skills found" in err and "alpha" in err and "beta" in err


def test_a_pasted_skill_md_has_no_license_so_the_gate_stops(tmp_path, capsys):
    repo, skills = _fake_repo(tmp_path)
    pasted = _tree(tmp_path / "paste", {"SKILL.md": "# Pasted\n"}) / "SKILL.md"
    assert AS.main([str(pasted), "--name", "coding-pasted", "--dest", str(skills)]) == 1
    assert "NO LICENSE FOUND" in capsys.readouterr().err


def test_a_source_without_any_skill_md_exits_two(tmp_path, capsys):
    repo, skills = _fake_repo(tmp_path)
    src = _tree(tmp_path / "empty", {"LICENSE": MIT})
    assert AS.main([str(src), "--dest", str(skills)]) == 2
    assert "no SKILL.md found" in capsys.readouterr().err


def test_upstream_name_falls_back_to_the_source_not_the_temp_dir(tmp_path):
    root = _tree(tmp_path / "up3", {"SKILL.md": "# Up3\n\nRun up3.\n", "LICENSE": MIT})
    args = AS.parse_args([str(root)])
    tree, skill = AS.fetch(args.source, args.subdir, tmp_path / "work")
    assert skill.name == "src"                                  # the temp copy's own name
    assert AS.upstream_name(args, tree, skill) == "up3"
    nested = _tree(tmp_path / "multi" / "skills" / "beta", {"SKILL.md": "# b\n"}).parent.parent
    args = AS.parse_args([str(nested), "--subdir", "skills/beta"])
    tree, skill = AS.fetch(args.source, args.subdir, tmp_path / "work2")
    assert AS.upstream_name(args, tree, skill) == "beta"


def test_cp1252_stdout_does_not_crash_the_report(tmp_path):
    repo, skills = _fake_repo(tmp_path / "日本")        # the report prints this path
    src = _fake_source(tmp_path)
    (src / "SKILL.md").write_text("# Up\n\n日本語 body\n", encoding="utf-8")
    (src / "LICENSE").write_text(MIT.replace("Test Author", "日本 Author"),
                                 encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    r = subprocess.run([sys.executable, AS.__file__, str(src), "--name", "coding-up",
                        "--dest", str(skills)], capture_output=True, env=env)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
    assert b"LICENSE GATE: ACCEPTED" in r.stdout
