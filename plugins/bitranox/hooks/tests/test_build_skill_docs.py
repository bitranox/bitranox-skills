"""Tests for build_skill_docs.py (the generated docs/skills.md catalog) plus the
docs fact-freshness guards (README skill count, reference.md knob table). ASCII."""
import json
import re
import tomllib
from pathlib import Path

import pytest

import build_skill_docs as D
import self_improve_signals as S
import skill_frontmatter as F

REPO_ROOT = Path(__file__).resolve().parents[4]


def _skill(root, name, desc):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: %s\ndescription: %s\n---\n\n# x\n" % (name, desc),
                                encoding="utf-8")


def _taxonomy(path):
    path.write_text(json.dumps({"categories": {
        "meta": {"desc": "Meta things"},
        "coding": {"desc": "Code things"},
    }}), encoding="utf-8")


def test_render_groups_by_taxonomy_order_with_links_and_descriptions(tmp_path):
    skills = tmp_path / "skills"
    _skill(skills, "coding-beta", "Use when beta code is written under pressure loads")
    _skill(skills, "meta-alpha", "Use when alpha work needs capturing across sessions")
    tax = tmp_path / "tax.json"
    _taxonomy(tax)
    text = D.render(skills, tax)
    assert "2 skills" in text
    # category sections follow taxonomy declaration order, not alphabetical order
    assert text.index("## meta") < text.index("## coding")
    assert "Meta things" in text and "Code things" in text
    assert "[`meta-alpha`](../plugins/bitranox/skills/meta-alpha/SKILL.md)" in text
    assert "Use when beta code is written under pressure loads" in text


def test_render_prints_the_description_exactly_as_the_shared_reader_returns_it(tmp_path):
    """The catalog applies no display clean-up of its own. A quoted or block-scalar description is
    refused by the commit gate (harness_checks.cso_failures_for), so no shipped skill has one; a
    second normalisation here would only be a place for the catalog and the gate to disagree."""
    skills = tmp_path / "skills"
    _skill(skills, "meta-quoted", '"Use when quoted descriptions reach the catalog builder"')
    tax = tmp_path / "tax.json"
    _taxonomy(tax)
    text = D.render(skills, tax)
    shared = F.description(skills / "meta-quoted" / "SKILL.md")
    assert shared.startswith('"')
    assert " - %s\n" % shared in text


def test_render_surfaces_unknown_prefix_instead_of_dropping(tmp_path):
    skills = tmp_path / "skills"
    _skill(skills, "mystery-gamma", "Use when gamma rays flip bits in orbit hardware")
    tax = tmp_path / "tax.json"
    _taxonomy(tax)
    text = D.render(skills, tax)
    assert "## uncategorized" in text and "mystery-gamma" in text


def test_check_detects_stale_catalog(tmp_path):
    skills = tmp_path / "skills"
    _skill(skills, "meta-alpha", "Use when alpha work needs capturing across sessions")
    tax = tmp_path / "tax.json"
    _taxonomy(tax)
    out = tmp_path / "skills.md"
    argv = ["--skills-dir", str(skills), "--taxonomy", str(tax), "--out", str(out)]
    assert D.main(argv) == 0
    assert D.main(argv + ["--check"]) == 0
    _skill(skills, "coding-beta", "Use when beta code is written under pressure loads")
    assert D.main(argv + ["--check"]) == 1


def test_check_says_missing_for_a_catalog_that_does_not_exist(tmp_path, capsys):
    """Run from an installed cache, the default --out points at a docs/ that does not ship, and
    "STALE - run build_skill_docs.py" sent the reader to regenerate a file that was never there."""
    skills = tmp_path / "skills"
    _skill(skills, "meta-alpha", "Use when alpha work needs capturing across sessions")
    tax = tmp_path / "tax.json"
    _taxonomy(tax)
    out = tmp_path / "docs" / "skills.md"
    # Nothing to compare against is "could not run" (2), not the "stale" finding (1).
    assert D.main(["--skills-dir", str(skills), "--taxonomy", str(tax), "--out", str(out),
                   "--check"]) == 2
    err = capsys.readouterr().err
    assert "missing" in err and str(out) in err and "STALE" not in err


def _could_not_run_argv(tmp_path, *, taxonomy=None, skills=True, out=None):
    skills_dir = tmp_path / "skills"
    if skills:
        _skill(skills_dir, "meta-alpha", "Use when alpha work needs capturing across sessions")
    tax = tmp_path / "tax.json"
    if taxonomy is None:
        _taxonomy(tax)
    else:
        tax.write_bytes(taxonomy)
    return ["--skills-dir", str(skills_dir), "--taxonomy", str(tax),
            "--out", str(out or tmp_path / "skills.md")]



@pytest.mark.parametrize("taxonomy", [b"{not json", b"[1]", b'{"other": {}}', b"\xff\xfe\x00"],
                         ids=["invalid-json", "a-list", "no-categories", "not-utf8"])
def test_an_unusable_taxonomy_could_not_run(tmp_path, capsys, taxonomy):
    assert D.main(_could_not_run_argv(tmp_path, taxonomy=taxonomy)) == 2
    assert "taxonomy" in capsys.readouterr().err


def test_a_missing_taxonomy_could_not_run(tmp_path):
    argv = _could_not_run_argv(tmp_path)
    (tmp_path / "tax.json").unlink()
    assert D.main(argv) == 2


def test_a_nonexistent_skills_dir_could_not_run_rather_than_writing_an_empty_catalog(tmp_path, capsys):
    out = tmp_path / "skills.md"
    assert D.main(_could_not_run_argv(tmp_path, skills=False, out=out)) == 2
    assert not out.exists()
    assert "skills" in capsys.readouterr().err


def test_an_unwritable_out_could_not_run(tmp_path):
    out = tmp_path / "is-a-directory"
    out.mkdir()
    assert D.main(_could_not_run_argv(tmp_path, out=out)) == 2


def test_check_against_an_undecodable_catalog_could_not_run(tmp_path):
    out = tmp_path / "skills.md"
    out.write_bytes(b"\xff\xfe\x00 not utf-8")
    assert D.main(_could_not_run_argv(tmp_path, out=out) + ["--check"]) == 2


def test_check_still_says_stale_for_an_outdated_catalog(tmp_path, capsys):
    """Control for the test above."""
    skills = tmp_path / "skills"
    _skill(skills, "meta-alpha", "Use when alpha work needs capturing across sessions")
    tax = tmp_path / "tax.json"
    _taxonomy(tax)
    out = tmp_path / "skills.md"
    out.write_text("old\n", encoding="utf-8")
    assert D.main(["--skills-dir", str(skills), "--taxonomy", str(tax), "--out", str(out),
                   "--check"]) == 1
    assert "STALE" in capsys.readouterr().err


def test_shipped_catalog_in_sync_with_skills():
    # the committed docs/skills.md must match the shipped skills (regenerate on any change)
    assert D.main(["--check"]) == 0


def test_readme_states_current_skill_count():
    count = len(sorted((REPO_ROOT / "plugins" / "bitranox" / "skills").glob("*/SKILL.md")))
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert ("%d skills" % count) in readme


def test_every_skill_count_claim_in_the_docs_is_current():
    # One correct mention used to satisfy the check above while another page went on stating an
    # older count, so every whole-catalogue claim ("all <N> skills", "**<N> skills**") in the
    # README and docs/ is held to the real number. A bare "<N> skills" is not one: "nudge up to 2
    # skills" describes a hook, not the catalogue.
    count = len(sorted((REPO_ROOT / "plugins" / "bitranox" / "skills").glob("*/SKILL.md")))
    pages = [REPO_ROOT / "README.md"] + sorted((REPO_ROOT / "docs").glob("*.md"))
    claims = [(page.name, int(n)) for page in pages
              for n in re.findall(r"(?:\ball |\*\*)(\d+) skills\b",
                                  page.read_text(encoding="utf-8"), re.IGNORECASE)]
    assert claims, "no skill-count claim found; the scan is not reading the docs"
    assert [c for c in claims if c[1] != count] == []


def test_package_description_states_no_skill_or_hook_count():
    # The PyPI description is outside the docs scan above, so a count there rots unchecked: it
    # said "82 skills and 64 hooks" while 83 skills shipped, and its 64 was the number of .py
    # files in hooks/ (helper modules included), not of registered hooks.
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    description = pyproject["project"]["description"]
    assert description, "pyproject.toml has no [project].description to check"
    assert re.findall(r"\d+\s+(?:skills?|hooks?)\b", description, re.IGNORECASE) == []


def test_reference_doc_documents_every_config_knob():
    ref = (REPO_ROOT / "docs" / "reference.md").read_text(encoding="utf-8")
    for knob in S.DEFAULT_CONFIG:
        assert ("`%s`" % knob) in ref


# ---- a renamed skill leaves no live pointer at its old name ----------------------------------

# The Python data-architecture skill was renamed with no alias, so a pointer at the old name
# resolves to nothing for the reader who follows it. Ledgers, old checklists and CHANGELOG
# entries are historical records and keep the old name.
RETIRED_SKILL_NAMES = ("coding-python-enforce-data-architecture-strict",)


def _live_mentions(root, name):
    """Files under plugins/, plus docs/skills.md and README.md, that name `name`.

    Skips .skillwriter/ records, CHANGELOG files, caches and this test file, whose own
    constant has to spell the retired name."""
    this_file = Path(__file__).resolve()
    candidates = [p for p in (root / "plugins").rglob("*") if p.is_file()]
    candidates += [root / "docs" / "skills.md", root / "README.md"]
    hits = []
    for path in candidates:
        rel = path.relative_to(root).as_posix()
        if (".skillwriter/" in rel or path.name == "CHANGELOG.md" or "__pycache__" in rel
                or "/.pytest_cache/" in rel or not path.is_file()
                or path.resolve() == this_file):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if name in text:
            hits.append(rel)
    return hits


@pytest.mark.parametrize("name", RETIRED_SKILL_NAMES)
def test_no_live_file_names_a_retired_skill(name):
    assert _live_mentions(REPO_ROOT, name) == []


def test_the_retired_name_scan_finds_one_planted_occurrence(tmp_path):
    name = RETIRED_SKILL_NAMES[0]
    skill = tmp_path / "plugins" / "bitranox" / "skills" / "demo"
    (skill / ".skillwriter").mkdir(parents=True)
    (skill / "SKILL.md").write_text("see bitranox:%s\n" % name, encoding="utf-8")
    (skill / ".skillwriter" / "checklist-x.md").write_text(name, encoding="utf-8")
    (tmp_path / "plugins" / "CHANGELOG.md").write_text(name, encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "skills.md").write_text("clean\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("clean\n", encoding="utf-8")
    assert _live_mentions(tmp_path, name) == ["plugins/bitranox/skills/demo/SKILL.md"]


# ---- the Python data-architecture skill defers its generic rules to the generic skill ---------

_SKILLS = REPO_ROOT / "plugins" / "bitranox" / "skills"
# Markers of the language-neutral text that lives once, in coding-data-architecture.
_GENERIC_MARKERS = ("MAIN LOOP - REPEAT STEPS A->B", "## Execution Summary", "### Core Principles",
                    "## Instructions\n")


def _defers_to_the_generic_skill(python_text):
    return ("bitranox:coding-data-architecture" in python_text
            and not any(m in python_text for m in _GENERIC_MARKERS))


def test_the_python_data_architecture_skill_holds_no_copy_of_the_generic_rules():
    python_text = (_SKILLS / "coding-python-data-architecture" / "SKILL.md").read_text(
        encoding="utf-8")
    generic_text = (_SKILLS / "coding-data-architecture" / "SKILL.md").read_text(encoding="utf-8")
    assert _defers_to_the_generic_skill(python_text)
    assert all(m in generic_text for m in _GENERIC_MARKERS)


def test_the_deferral_check_refuses_a_skill_that_still_carries_the_workflow():
    carrying = "see bitranox:coding-data-architecture\n\n## Workflow\nMAIN LOOP - REPEAT STEPS A->B\n"
    assert not _defers_to_the_generic_skill(carrying)
    assert not _defers_to_the_generic_skill("no pointer at all\n")
