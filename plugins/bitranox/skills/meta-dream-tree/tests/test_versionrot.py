"""The version-rot scanner: find memory facts bound to a version that a newer release superseded.

A fact like "fixed in bmk 3.13.0" stays correct as a sentence and wrong as a lesson once bmk is at
3.21.1, and no other dream pass looks at it. The scanner must:

* resolve the package a version belongs to, and compare against what is CURRENT, never guess;
* stay quiet on numbers that are not versions (IP addresses, scores, two-part noise);
* be able to say "nothing superseded" over a non-empty store, and refuse a scan of zero facts.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import versionrot  # noqa: E402


def _reg(**versions: str) -> versionrot.Registry:
    return versionrot.Registry(
        {versionrot.normalize(k): versionrot.Known(v, "test") for k, v in versions.items()})


def _only(claims: list[versionrot.Claim]) -> versionrot.Claim:
    assert len(claims) == 1, claims
    return claims[0]


class TestCompare:
    @pytest.mark.parametrize(("named", "current", "want"), [
        ("3.13.0", "3.21.1", "superseded"),
        ("3.21.1", "3.21.1", "current"),
        ("3.22.0", "3.21.1", "ahead"),
        ("3.21.x", "3.21.1", "current"),
        ("3.20.x", "3.21.1", "superseded"),
        ("2.13", "2.13.5", "current"),
        ("1.9.10", "1.10.0", "superseded"),
    ])
    def test_status(self, named, current, want):
        assert versionrot.compare(named, current) == want


class TestFindClaims:
    def test_package_right_before_the_version(self):
        c = _only(versionrot.find_claims("Know it was fixed in bmk 3.13.0.", _reg(bmk="3.21.1")))
        assert (c.pkg, c.named, c.current, c.status) == ("bmk", "3.13.0", "3.21.1", "superseded")

    def test_package_earlier_in_the_same_sentence(self):
        text = "bmk's shared tool env was rebuilt under running bmk processes (fixed in 3.13.0)."
        c = _only(versionrot.find_claims(text, _reg(bmk="3.21.1")))
        assert (c.pkg, c.status) == ("bmk", "superseded")

    def test_lookback_stops_at_the_sentence_end(self):
        text = "We run bmk. The kernel 7.0.14 is fine."
        c = _only(versionrot.find_claims(text, _reg(bmk="3.21.1")))
        assert c.status == "unresolved"
        assert c.pkg == "kernel"

    def test_a_current_version_is_current(self):
        c = _only(versionrot.find_claims("Use bmk 3.21.1 here.", _reg(bmk="3.21.1")))
        assert c.status == "current"

    def test_hyphen_and_underscore_spellings_are_one_package(self):
        c = _only(versionrot.find_claims("btx-lib-mail 1.5.0 streams delivery.",
                                         _reg(btx_lib_mail="4.3.0")))
        assert (c.pkg, c.status) == ("btx-lib-mail", "superseded")

    def test_a_comparison_operator_between_name_and_version(self):
        for text in ("Requires bmk >= 3.2.0 now.", "Pin bmk>=3.2.0 in pyproject."):
            c = _only(versionrot.find_claims(text, _reg(bmk="3.21.1")))
            assert (c.pkg, c.named) == ("bmk", "3.2.0"), text

    def test_a_two_word_name(self):
        c = _only(versionrot.find_claims("Verified on Claude Code 2.1.198.",
                                         _reg(**{"claude-code": "2.1.300"})))
        assert (c.pkg, c.status) == ("claude-code", "superseded")

    def test_an_alias_names_a_package(self):
        reg = _reg(bitranox="8.23.0")
        reg.aliases[versionrot.normalize("plugin")] = versionrot.normalize("bitranox")
        c = _only(versionrot.find_claims("Fixed in plugin 7.22.10.", reg))
        assert (c.pkg, c.current, c.status) == ("bitranox", "8.23.0", "superseded")

    def test_an_ip_address_is_not_a_version(self):
        text = "Ping 10.0.0.12 and 192.168.1.5 from bmk hosts."
        assert versionrot.find_claims(text, _reg(bmk="3.21.1")) == []

    def test_a_two_part_number_without_a_known_package_is_noise(self):
        text = "It scored 0.62 against Python 3.10 with a 1.5 s deadline."
        assert versionrot.find_claims(text, _reg(bmk="3.21.1")) == []

    def test_a_two_part_version_next_to_a_known_package_counts(self):
        c = _only(versionrot.find_claims("Measured on pydantic 2.13 there.",
                                         _reg(pydantic="2.13.5")))
        assert (c.pkg, c.status) == ("pydantic", "current")

    def test_a_three_part_version_with_an_unknown_package_is_unresolved(self):
        c = _only(versionrot.find_claims("Seen on kernel 7.0.14 only.", _reg(bmk="3.21.1")))
        assert (c.pkg, c.status, c.current) == ("kernel", "unresolved", None)

    def test_an_unknown_name_right_before_the_version_owns_it(self):
        # Measured on the live store: "click 8.2.1" in a lib_shopware6 sentence was credited to
        # lib_shopware6 because click had no local repo.
        text = "In lib_shopware6_api_base: pip-audit failed on click 8.2.1 there."
        c = _only(versionrot.find_claims(text, _reg(lib_shopware6_api_base="6.1.1")))
        assert (c.pkg, c.status) == ("click", "unresolved")

    def test_an_unknown_name_after_a_known_one_owns_it(self):
        c = _only(versionrot.find_claims("Seen in (lsdsk 395f95d, ruff 0.16.7) only.",
                                         _reg(lsdsk="1.9.1")))
        assert (c.pkg, c.status) == ("ruff", "unresolved")

    def test_a_range_keeps_its_package(self):
        claims = versionrot.find_claims("It moved bmk from 3.13.0 to 3.21.1 overnight.",
                                        _reg(bmk="3.21.1"))
        assert [(c.pkg, c.status) for c in claims] == [("bmk", "superseded"), ("bmk", "current")]

    def test_a_range_of_an_unknown_package_is_not_lent_to_a_known_one(self):
        # Measured: "the bmk gate raised the click floor 8.4.2 -> 8.5.0" credited both to bmk.
        claims = versionrot.find_claims("The bmk gate raised the click floor 8.4.2 -> 8.5.0 here.",
                                        _reg(bmk="3.21.2"))
        assert [(c.pkg, c.status) for c in claims] == [("click", "unresolved")] * 2

    def test_a_slash_list_keeps_its_package(self):
        claims = versionrot.find_claims("Fails on bmk 3.12.1/3.13.0 only.", _reg(bmk="3.21.1"))
        assert [c.pkg for c in claims] == ["bmk", "bmk"]

    def test_a_wildcard_version(self):
        c = _only(versionrot.find_claims("On bmk 3.20.x the pytest block carries it.",
                                         _reg(bmk="3.21.1")))
        assert (c.named, c.status) == ("3.20.x", "superseded")


def _pyproject(d: Path, name: str, version: str | None) -> None:
    d.mkdir(parents=True, exist_ok=True)
    ver = f'version = "{version}"\n' if version else 'dynamic = ["version"]\n'
    (d / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n{ver}', encoding="utf-8")


class TestDiscover:
    def test_finds_pyproject_and_plugin_manifests(self, tmp_path):
        _pyproject(tmp_path / "libs" / "lib_a", "lib_a", "1.2.3")
        plug = tmp_path / "apps" / "tool" / ".claude-plugin"
        plug.mkdir(parents=True)
        (plug / "plugin.json").write_text('{"name": "tool", "version": "0.4.0"}', encoding="utf-8")
        reg = versionrot.discover([tmp_path])
        assert reg.lookup("lib-a").version == "1.2.3"
        assert reg.lookup("tool").version == "0.4.0"

    def test_skips_hidden_and_vendored_dirs(self, tmp_path):
        _pyproject(tmp_path / ".venv" / "lib" / "x", "hidden_pkg", "9.9.9")
        _pyproject(tmp_path / "node_modules" / "y", "vendored_pkg", "9.9.9")
        reg = versionrot.discover([tmp_path])
        assert reg.lookup("hidden-pkg") is None
        assert reg.lookup("vendored-pkg") is None

    def test_a_dynamic_version_is_not_guessed(self, tmp_path):
        _pyproject(tmp_path / "dyn", "dyn_pkg", None)
        assert versionrot.discover([tmp_path]).lookup("dyn-pkg") is None

    def test_two_copies_keep_the_newest(self, tmp_path):
        _pyproject(tmp_path / "a" / "lib", "same", "1.0.0")
        _pyproject(tmp_path / "b" / "lib", "same", "1.10.0")
        assert versionrot.discover([tmp_path]).lookup("same").version == "1.10.0"

    def test_a_marketplace_name_aliases_its_plugin(self, tmp_path):
        meta = tmp_path / "skills-repo" / ".claude-plugin"
        meta.mkdir(parents=True)
        (meta / "marketplace.json").write_text(
            '{"name": "my-skills", "plugins": [{"name": "mine", "source": "./plugins/mine"}]}',
            encoding="utf-8")
        pmeta = tmp_path / "skills-repo" / "plugins" / "mine" / ".claude-plugin"
        pmeta.mkdir(parents=True)
        (pmeta / "plugin.json").write_text('{"name": "mine", "version": "2.0.0"}',
                                           encoding="utf-8")
        reg = versionrot.discover([tmp_path])
        assert reg.lookup("my-skills").version == "2.0.0"


class TestOwnPlugin:
    def test_a_stale_checkout_does_not_outrank_the_running_plugin(self):
        # Measured: a main checkout two commits behind reported the plugin one release old.
        reg = _reg(bitranox="0.0.1")
        versionrot.own_plugin(reg)
        meta = Path(versionrot.__file__).resolve().parents[2] / ".claude-plugin" / "plugin.json"
        assert reg.lookup("bitranox").version == json.loads(meta.read_text("utf-8"))["version"]
        assert reg.lookup("plugin") is reg.lookup("bitranox")


def _store(tmp_path: Path, facts: dict[str, tuple[str, str]]) -> Path:
    """An anchor with a store and one level holding `facts` (slug -> (hook, body))."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "CLAUDE.md").write_text("# top\n", encoding="utf-8")
    fdir = tmp_path / ".claude-memory" / "facts"
    fdir.mkdir(parents=True)
    lines = []
    for slug, (hook, body) in facts.items():
        lines.append(f"- [{slug}](mem:{slug}) - {hook}")
        (fdir / f"{slug}.md").write_text(
            f"---\nname: {slug}\ndescription: {hook}\n---\n\n{body}\n", encoding="utf-8")
    (tmp_path / "CLAUDE.local.md").write_text(
        "# Memory index\n\n## Memory index\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def _run(capsys, *argv: str) -> tuple[int, dict]:
    rc = versionrot.main([*argv, "--json"])
    return rc, json.loads(capsys.readouterr().out)


class TestCli:
    def test_reports_a_superseded_fact_and_exits_1(self, tmp_path, capsys):
        root = _store(tmp_path, {
            "stale": ("When X, know it was fixed in bmk 3.13.0.", "The lock race."),
            "fine": ("When Y, do Z.", "Nothing versioned here."),
        })
        rc, env = _run(capsys, "scan", "--chain", str(root), "--current", "bmk=3.21.1")
        assert rc == 1
        assert env["ok"] is True
        assert env["data"]["facts_scanned"] == 2
        (fact,) = env["data"]["superseded"]
        assert fact["slug"] == "stale"
        assert fact["claims"][0]["where"] == "hook"
        assert fact["claims"][0]["current"] == "3.21.1"

    def test_says_clean_when_every_claim_is_current(self, tmp_path, capsys):
        root = _store(tmp_path, {"ok": ("When X, use bmk 3.21.1.", "Body.")})
        rc, env = _run(capsys, "scan", "--chain", str(root), "--current", "bmk=3.21.1")
        assert rc == 0
        assert env["data"]["superseded"] == []
        assert env["data"]["claims_by_status"]["current"] == 1

    def test_reads_the_body_too(self, tmp_path, capsys):
        root = _store(tmp_path, {"b": ("When X, do Y.", "Verified on btx_lib_mail 1.5.0.")})
        rc, env = _run(capsys, "scan", "--chain", str(root), "--current", "btx-lib-mail=4.3.0")
        assert rc == 1
        assert env["data"]["superseded"][0]["claims"][0]["where"] == "body"

    def test_refuses_a_scan_of_zero_facts(self, tmp_path, capsys):
        (tmp_path / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
        rc, env = _run(capsys, "scan", "--chain", str(tmp_path))
        assert rc == 2
        assert env["ok"] is False
        assert "0 facts" in env["error"]

    def test_a_missing_chain_dir_is_an_error(self, tmp_path, capsys):
        rc, env = _run(capsys, "scan", "--chain", str(tmp_path / "nope"))
        assert rc == 2
        assert env["ok"] is False

    def test_repos_are_discovered_for_current_versions(self, tmp_path, capsys):
        root = _store(tmp_path / "tree", {"s": ("When X, know lib_a 1.0.0 did it.", "B.")})
        _pyproject(tmp_path / "repos" / "lib_a", "lib_a", "2.0.0")
        rc, env = _run(capsys, "scan", "--chain", str(root), "--repos", str(tmp_path / "repos"))
        assert rc == 1
        assert env["data"]["superseded"][0]["claims"][0]["current"] == "2.0.0"
