"""Tests for build_skill_docs.py (the generated docs/skills.md catalog) plus the
docs fact-freshness guards (README skill count, reference.md knob table). ASCII."""
import json
from pathlib import Path

import build_skill_docs as D
import self_improve_signals as S

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


def test_render_strips_frontmatter_authoring_artifacts(tmp_path):
    skills = tmp_path / "skills"
    _skill(skills, "meta-quoted", '"Use when quoted descriptions need cleaning for display"')
    _skill(skills, "meta-arrow", "> Use when blockquoted descriptions need cleaning too")
    tax = tmp_path / "tax.json"
    _taxonomy(tax)
    text = D.render(skills, tax)
    assert " - Use when quoted descriptions need cleaning for display\n" in text
    assert " - Use when blockquoted descriptions need cleaning too\n" in text


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


def test_shipped_catalog_in_sync_with_skills():
    # the committed docs/skills.md must match the shipped skills (regenerate on any change)
    assert D.main(["--check"]) == 0


def test_readme_states_current_skill_count():
    count = len(sorted((REPO_ROOT / "plugins" / "bitranox" / "skills").glob("*/SKILL.md")))
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert ("%d skills" % count) in readme


def test_reference_doc_documents_every_config_knob():
    ref = (REPO_ROOT / "docs" / "reference.md").read_text(encoding="utf-8")
    for knob in S.DEFAULT_CONFIG:
        assert ("`%s`" % knob) in ref
