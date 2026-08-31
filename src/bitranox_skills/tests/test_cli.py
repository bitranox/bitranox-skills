"""Tests for the `bitranox-skills` CLI.

The install path copies directories into a real destination, so every test that installs
points --dest at tmp_path. A test that defaulted to ~/.claude/skills would write into the
developer's own Claude Code configuration, which is the sort of test nobody notices until
it has already done it.
"""

import json

from bitranox_skills import PLUGIN_DIR, SKILLS_DIR, plugin_version, skill_names
from bitranox_skills import cli


def test_plugin_dir_and_skills_resolve_in_a_source_checkout():
    """In a checkout the package data is not beside the module, so these point nowhere.

    Recorded rather than asserted-away: the wheel force-includes plugins/bitranox as
    bitranox_skills/plugin, so PLUGIN_DIR is only populated in an INSTALLED copy. Asserting
    it exists here would fail in the very environment CI runs.
    """
    assert PLUGIN_DIR.name == "plugin"
    assert SKILLS_DIR.parent == PLUGIN_DIR


def test_skill_names_is_empty_without_bundled_data(monkeypatch, tmp_path):
    """A directory only counts as a skill when it carries a SKILL.md."""
    monkeypatch.setattr(cli, "SKILLS_DIR", tmp_path)
    (tmp_path / "notaskill").mkdir()
    real = tmp_path / "realskill"
    real.mkdir()
    (real / "SKILL.md").write_text("# x\n", encoding="utf-8")
    import bitranox_skills
    monkeypatch.setattr(bitranox_skills, "SKILLS_DIR", tmp_path)
    assert bitranox_skills.skill_names() == ["realskill"]


def _bundle(tmp_path, names=("alpha", "beta")):
    """A stand-in for the bundled skills dir, with a SKILL.md in each."""
    src = tmp_path / "bundled"
    for name in names:
        d = src / name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"# {name}\n", encoding="utf-8")
    return src


def _wire(monkeypatch, src):
    monkeypatch.setattr(cli, "SKILLS_DIR", src)
    monkeypatch.setattr(cli, "skill_names",
                        lambda: sorted(d.name for d in src.iterdir() if (d / "SKILL.md").is_file()))
    monkeypatch.setattr(cli, "plugin_version", lambda: "9.9.9")


def test_install_copies_every_bundled_skill(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, _bundle(tmp_path))
    dest = tmp_path / "dest"
    assert cli.main(["install", "--dest", str(dest)]) == cli.EXIT_OK
    assert (dest / "alpha" / "SKILL.md").is_file()
    assert (dest / "beta" / "SKILL.md").is_file()
    assert "installed 2 skill(s)" in capsys.readouterr().out


def test_install_dry_run_writes_nothing(monkeypatch, tmp_path, capsys):
    """The plan must be reported without the destination being touched at all - not even
    created, or a --dry-run leaves a trace of itself."""
    _wire(monkeypatch, _bundle(tmp_path))
    dest = tmp_path / "dest"
    assert cli.main(["install", "--dest", str(dest), "--dry-run"]) == cli.EXIT_OK
    assert not dest.exists()
    assert "would install 2" in capsys.readouterr().out


def test_install_skips_an_existing_skill_unless_forced(monkeypatch, tmp_path):
    """Somebody's local edit is not ours to overwrite by default."""
    _wire(monkeypatch, _bundle(tmp_path))
    dest = tmp_path / "dest"
    (dest / "alpha").mkdir(parents=True)
    (dest / "alpha" / "SKILL.md").write_text("# mine\n", encoding="utf-8")

    assert cli.main(["install", "--dest", str(dest)]) == cli.EXIT_OK
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "# mine\n"

    assert cli.main(["install", "--dest", str(dest), "--force"]) == cli.EXIT_OK
    assert (dest / "alpha" / "SKILL.md").read_text(encoding="utf-8") == "# alpha\n"


def test_install_json_envelope_names_what_was_skipped(monkeypatch, tmp_path, capsys):
    _wire(monkeypatch, _bundle(tmp_path))
    dest = tmp_path / "dest"
    (dest / "beta").mkdir(parents=True)
    assert cli.main(["--json", "install", "--dest", str(dest)]) == cli.EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["installed"] == ["alpha"]
    assert payload["skipped"] == ["beta"]


def test_install_reports_an_incomplete_wheel_as_an_error(monkeypatch, tmp_path, capsys):
    """No bundled skills means the artifact is broken; exit 2, not a cheerful zero."""
    monkeypatch.setattr(cli, "skill_names", lambda: [])
    assert cli.main(["install", "--dest", str(tmp_path)]) == cli.EXIT_ERROR
    assert "wheel is incomplete" in capsys.readouterr().err


def test_no_subcommand_prints_help_and_exits_nonzero(monkeypatch, capsys):
    monkeypatch.setattr(cli, "plugin_version", lambda: "9.9.9")
    assert cli.main([]) == cli.EXIT_ERROR
    assert "usage:" in capsys.readouterr().out


def test_path_json_names_the_three_directories(monkeypatch, capsys):
    monkeypatch.setattr(cli, "plugin_version", lambda: "9.9.9")
    assert cli.main(["--json", "path"]) == cli.EXIT_OK
    data = json.loads(capsys.readouterr().out)["data"]
    assert set(data) == {"plugin", "skills", "hooks", "version"}
    assert data["hooks"].endswith("hooks")


def test_default_destination_is_the_claude_skills_dir():
    assert cli.default_destination().parts[-2:] == (".claude", "skills")


def test_version_matches_the_bundled_manifest_when_present():
    """Guards the packaging seam: if force-include ever stops shipping the manifest, this
    is the test that says so rather than a user's install failing at first run."""
    manifest = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        return  # source checkout: package data is not laid down yet
    assert plugin_version() == json.loads(manifest.read_text(encoding="utf-8"))["version"]
    assert skill_names(), "an installed copy must carry skills"
