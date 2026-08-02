"""The `targets` verb: what it selects, what it refuses, and what it says about the refusals."""

import io
import json

import pytest

import audit_local


def _skills(parent, *names):
    d = parent / "skills"
    for n in names or ("demo",):
        (d / n).mkdir(parents=True)
        (d / n / "SKILL.md").write_text("---\nname: %s\n---\n" % n, encoding="utf-8")
    return d


def _manifest(root, kind):
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / kind).write_text("{}", encoding="utf-8")
    return root


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A work tree holding one ordinary project and one plugin repo, beside an isolated home."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    work = tmp_path / "work"
    project = _skills(work / "provmm" / ".claude", "provmm-build")
    shipped = _skills(_manifest(work / "igittigitt", "plugin.json"), "python-gitignore")
    personal = _skills(home / ".claude", "toolbox")
    return type("Tree", (), dict(home=home, work=work, project=project,
                                 shipped=shipped, personal=personal))


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    args = audit_local.build_parser().parse_args(argv)
    code = audit_local.cmd_targets(args, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_targets_selects_the_project_and_personal_dirs(tree):
    code, out, _ = _run(["targets", "--root", str(tree.work)])
    assert code == 0
    assert str(tree.project) in out
    assert str(tree.personal) in out


def test_targets_refuses_a_plugin_owned_dir(tree):
    """The whole point: a tool repo's mirrored twin must never be selected for editing."""
    _, out, _ = _run(["targets", "--root", str(tree.work)])
    assert str(tree.shipped) not in out.split("skipped")[0]


def test_no_personal_leaves_the_home_dir_out(tree):
    _, out, _ = _run(["targets", "--root", str(tree.work), "--no-personal"])
    assert str(tree.project) in out
    assert str(tree.personal) not in out


def test_json_envelope_carries_targets_and_reasons(tree):
    code, out, _ = _run(["targets", "--root", str(tree.work), "--json"])
    payload = json.loads(out)
    assert code == 0
    assert payload["ok"] is True and payload["command"] == "targets"
    assert str(tree.project) in payload["data"]["targets"]
    assert payload["data"]["count"] == len(payload["data"]["targets"])


def test_exit_code_is_one_when_nothing_is_selected(tmp_path, monkeypatch):
    """Format-independent codes: 0 found, 1 none found, 2 error."""
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    empty = tmp_path / "work"
    empty.mkdir()
    code, _, _ = _run(["targets", "--root", str(empty)])
    assert code == 1


def test_a_missing_root_warns_on_stderr_and_does_not_pollute_stdout(tree):
    """Warnings belong on stderr so `--json` stays parseable."""
    code, out, err = _run(["targets", "--root", str(tree.work),
                           "--root", str(tree.work / "nope"), "--json"])
    assert "nope" in err
    json.loads(out)
    assert code == 0


# --- the check verb ---------------------------------------------------------------------------

def _run_check(argv):
    out, err = io.StringIO(), io.StringIO()
    args = audit_local.build_parser().parse_args(argv)
    code = audit_local.cmd_check(args, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_check_is_clean_and_exits_zero_for_a_healthy_tree(tree):
    """The control. A check that can only ever report findings is not a check."""
    (tree.project / "provmm-build" / "SKILL.md").write_text(
        "---\nname: provmm-build\ndescription: Use when building provmm images from source.\n---\n",
        encoding="utf-8")
    code, out, _ = _run_check(["check", "--root", str(tree.work), "--no-personal"])
    assert code == 0 and "clean" in out


def test_check_reports_a_description_that_is_not_trigger_first(tree):
    (tree.project / "provmm-build" / "SKILL.md").write_text(
        "---\nname: provmm-build\ndescription: Builds the provmm images from source.\n---\n",
        encoding="utf-8")
    code, out, _ = _run_check(["check", "--root", str(tree.work), "--no-personal"])
    assert code == 1 and "trigger-first" in out


def test_check_reports_a_name_that_disagrees_with_its_dir(tree):
    (tree.project / "provmm-build" / "SKILL.md").write_text(
        "---\nname: wrong-name\ndescription: Use when building provmm images from source.\n---\n",
        encoding="utf-8")
    _, out, _ = _run_check(["check", "--root", str(tree.work), "--no-personal"])
    assert "[frontmatter]" in out and "wrong-name" in out


def test_check_reports_an_unmanaged_twin_against_a_shipped_catalogue(tree, tmp_path):
    desc = "Use when parsing gitignore files and filtering paths with the igittigitt library."
    (tree.project / "provmm-build" / "SKILL.md").write_text(
        "---\nname: provmm-build\ndescription: %s\n---\n" % desc, encoding="utf-8")
    catalogue = tmp_path / "mkt" / "coding-python-gitignore"
    catalogue.mkdir(parents=True)
    (catalogue / "SKILL.md").write_text("---\nname: coding-python-gitignore\ndescription: %s\n---\n"
                                        % desc, encoding="utf-8")
    _, out, _ = _run_check(["check", "--root", str(tree.work), "--no-personal",
                            "--shipped", str(tmp_path / "mkt")])
    assert "[unmanaged-twin]" in out and "coding-python-gitignore" in out


def test_check_reports_a_skill_shipping_a_script_with_no_test(tree):
    (tree.project / "provmm-build" / "SKILL.md").write_text(
        "---\nname: provmm-build\ndescription: Use when building provmm images from source.\n---\n",
        encoding="utf-8")
    (tree.project / "provmm-build" / "scripts").mkdir()
    (tree.project / "provmm-build" / "scripts" / "tool.py").write_text("x = 1\n", encoding="utf-8")
    _, out, _ = _run_check(["check", "--root", str(tree.work), "--no-personal"])
    assert "[tests-missing]" in out


def test_check_json_envelope_counts_findings(tree):
    (tree.project / "provmm-build" / "SKILL.md").write_text(
        "---\nname: provmm-build\ndescription: Builds the images.\n---\n", encoding="utf-8")
    code, out, _ = _run_check(["check", "--root", str(tree.work), "--no-personal", "--json"])
    payload = json.loads(out)
    assert code == 1 and payload["command"] == "check"
    assert payload["data"]["finding_count"] == sum(
        len(r["findings"]) for r in payload["data"]["results"])


def test_check_personal_reports_a_registration_naming_a_missing_file(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"Stop": [
        {"matcher": "*", "hooks": [{"type": "command",
                                    "command": "bash %s/.claude/hooks/gone.sh" % home}]}]}}),
        encoding="utf-8")
    found = audit_local.check_personal(home)
    assert any(check == "registration" and "gone.sh" in message for check, message in found)


def test_check_personal_is_quiet_when_every_registration_resolves(tmp_path):
    home = tmp_path / "home"
    hooks = home / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "live.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (home / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"Stop": [
        {"matcher": "*", "hooks": [{"type": "command", "command": "bash %s/live.sh" % hooks}]}]}}),
        encoding="utf-8")
    assert [c for c, _ in audit_local.check_personal(home) if c == "registration"] == []


def test_home_override_aims_a_run_at_a_fixture(tmp_path, monkeypatch):
    """Without it, auditing a sandbox silently mixes in the operator's real ~/.claude findings."""
    real, fixture = tmp_path / "real", tmp_path / "fixture"
    for home in (real, fixture):
        (home / ".claude" / "skills" / "s").mkdir(parents=True)
        (home / ".claude" / "skills" / "s" / "SKILL.md").write_text(
            "---\nname: s\ndescription: Use when doing something specific here.\n---\n",
            encoding="utf-8")
    monkeypatch.setenv("HOME", str(real))
    monkeypatch.setenv("USERPROFILE", str(real))
    out = io.StringIO()
    args = audit_local.build_parser().parse_args(["targets", "--home", str(fixture)])
    audit_local.cmd_targets(args, out=out, err=io.StringIO())
    assert str(fixture) in out.getvalue()
    assert str(real) not in out.getvalue()


def test_refused_dirs_are_reported_with_their_owner(tree):
    """A filter whose work leaves no trace reads exactly like a filter that never ran.

    Asserted against the whole output rather than a section split on the word itself: pytest names
    its tmp dir after the test, so a split on a word in the test's own name cuts inside the path."""
    code, out, _ = _run(["targets", "--root", str(tree.work)])
    assert code == 0
    assert "%s\n      shipped by the plugin at %s" % (tree.shipped, tree.shipped.parent) in out
