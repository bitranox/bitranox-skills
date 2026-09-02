"""Behaviour tests for the skill-listing-budget SessionStart hook.

Every case builds a real config tree on disk and runs the real functions against it; the only
substitution is CLAUDE_CONFIG_DIR, which is the hook's actual environment seam.
"""

import json

import pytest

import skill_listing_budget as budget


def write_skill(directory, name, description):
    """Create <directory>/<name>/SKILL.md with a frontmatter description, and return its path."""
    skill_dir = directory / name
    skill_dir.mkdir(parents=True)
    body = "---\nname: %s\n" % name
    if description is not None:
        body += "description: %s\n" % description
    body += "---\n\n# %s\n" % name
    path = skill_dir / "SKILL.md"
    path.write_text(body, encoding="utf-8")
    return path


def make_config(tmp_path, plugin_skills=(), user_skills=()):
    """Build a config dir with one installed plugin and a personal skills dir."""
    config = tmp_path / "claude"
    install = tmp_path / "cache" / "demo" / "1.0.0"
    (install / "skills").mkdir(parents=True)
    for name, desc in plugin_skills:
        write_skill(install / "skills", name, desc)
    (config / "skills").mkdir(parents=True)
    for name, desc in user_skills:
        write_skill(config / "skills", name, desc)
    manifest = config / "plugins" / "installed_plugins.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"plugins": {"demo@market": [{"installPath": str(install)}]}}),
        encoding="utf-8",
    )
    (config / "settings.json").write_text(json.dumps({"model": "opus"}), encoding="utf-8")
    return config


class TestReadDescription:
    def test_reads_a_single_line_description(self, tmp_path):
        path = write_skill(tmp_path, "alpha", "Use when alpha happens")
        assert budget.read_description(path) == "Use when alpha happens"

    def test_folds_a_wrapped_description_onto_one_line(self, tmp_path):
        skill = tmp_path / "beta"
        skill.mkdir()
        path = skill / "SKILL.md"
        path.write_text("---\nname: beta\ndescription: Use when beta\n  wraps over lines\n---\n\n#\n", encoding="utf-8")
        assert budget.read_description(path) == "Use when beta wraps over lines"

    def test_returns_none_without_a_description_field(self, tmp_path):
        path = write_skill(tmp_path, "gamma", None)
        assert budget.read_description(path) is None

    def test_returns_none_without_frontmatter(self, tmp_path):
        skill = tmp_path / "delta"
        skill.mkdir()
        path = skill / "SKILL.md"
        path.write_text("# delta\n\nno frontmatter here\n", encoding="utf-8")
        assert budget.read_description(path) is None

    def test_returns_none_for_a_missing_file(self, tmp_path):
        assert budget.read_description(tmp_path / "nope" / "SKILL.md") is None


class TestInstalledSkills:
    def test_qualifies_plugin_skills_and_leaves_user_skills_bare(self, tmp_path):
        config = make_config(tmp_path, plugin_skills=[("one", "Use when one")], user_skills=[("mine", "Use when mine")])
        assert budget.installed_skills(config) == [("demo:one", "Use when one"), ("mine", "Use when mine")]

    def test_a_skill_without_a_description_still_counts_as_an_entry(self, tmp_path):
        config = make_config(tmp_path, plugin_skills=[("bare", None)])
        assert budget.installed_skills(config) == [("demo:bare", "")]

    def test_a_directory_without_skill_md_is_not_an_entry(self, tmp_path):
        config = make_config(tmp_path, plugin_skills=[("real", "Use when real")])
        (config.parent / "cache" / "demo" / "1.0.0" / "skills" / "scratch").mkdir()
        assert [name for name, _ in budget.installed_skills(config)] == ["demo:real"]

    def test_missing_manifest_still_finds_user_skills(self, tmp_path):
        config = make_config(tmp_path, user_skills=[("solo", "Use when solo")])
        (config / "plugins" / "installed_plugins.json").unlink()
        assert budget.installed_skills(config) == [("solo", "Use when solo")]

    def test_unparsable_manifest_does_not_raise(self, tmp_path):
        config = make_config(tmp_path, user_skills=[("solo", "Use when solo")])
        (config / "plugins" / "installed_plugins.json").write_text("{not json", encoding="utf-8")
        assert budget.installed_skills(config) == [("solo", "Use when solo")]


class TestListingDemand:
    def test_matches_the_harness_line_format(self):
        entries = [("a:one", "desc one"), ("b:two", "desc two")]
        rendered = "- a:one: desc one\n- b:two: desc two"
        assert budget.listing_demand(entries, bundled_allowance=0) == len(rendered)

    def test_an_entry_without_a_description_costs_only_its_bare_line(self):
        assert budget.listing_demand([("solo", "")], bundled_allowance=0) == len("- solo")

    def test_a_long_description_is_charged_at_the_harness_cap(self):
        long_desc = "x" * (budget.MAX_DESC_CHARS + 500)
        capped = budget.listing_demand([("n", long_desc)], bundled_allowance=0)
        assert capped == len("- n: ") + budget.MAX_DESC_CHARS

    def test_the_bundled_allowance_is_added(self):
        entries = [("a:one", "desc one")]
        bare = budget.listing_demand(entries, bundled_allowance=0)
        assert budget.listing_demand(entries, bundled_allowance=500) == bare + 500

    def test_an_empty_catalogue_still_owes_the_bundled_allowance(self):
        assert budget.listing_demand([], bundled_allowance=777) == 777


class TestRequiredFraction:
    def test_the_chosen_fraction_actually_covers_the_demand(self):
        demand = 53_475
        fraction = budget.required_fraction(demand)
        assert fraction * budget.DENOMINATOR_FLOOR >= demand

    def test_it_leaves_the_safety_margin(self):
        demand = 53_475
        assert budget.required_fraction(demand) * budget.DENOMINATOR_FLOOR >= demand * budget.SAFETY

    def test_it_rounds_up_to_two_decimals(self):
        # 0.1223... must not round DOWN to 0.12, which would not cover the demand with margin
        assert budget.required_fraction(58_700) == 0.13

    def test_a_small_catalogue_asks_for_little(self):
        assert budget.required_fraction(6_000) == 0.02

    def test_it_never_exceeds_the_cap(self):
        assert budget.required_fraction(10_000_000) == budget.FRACTION_CAP

    def test_zero_demand_asks_for_nothing(self):
        assert budget.required_fraction(0) == 0.0


class TestRaiseFraction:
    def test_raises_an_unset_fraction_from_the_harness_default(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"model": "opus"}), encoding="utf-8")
        assert budget.raise_fraction(path, 0.13) == (0.01, 0.13)
        assert json.loads(path.read_text())["skillListingBudgetFraction"] == 0.13

    def test_leaves_every_other_key_untouched(self, tmp_path):
        path = tmp_path / "settings.json"
        original = {"model": "opus", "permissions": {"allow": ["Bash(*)"]}, "hooks": {"Stop": []}}
        path.write_text(json.dumps(original), encoding="utf-8")
        budget.raise_fraction(path, 0.13)
        after = json.loads(path.read_text())
        assert {k: v for k, v in after.items() if k != "skillListingBudgetFraction"} == original

    def test_does_not_lower_an_already_larger_fraction(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"skillListingBudgetFraction": 0.30}), encoding="utf-8")
        assert budget.raise_fraction(path, 0.13) is None
        assert json.loads(path.read_text())["skillListingBudgetFraction"] == 0.30

    def test_an_equal_fraction_is_not_rewritten(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"skillListingBudgetFraction": 0.13}), encoding="utf-8")
        assert budget.raise_fraction(path, 0.13) is None

    def test_refuses_to_rewrite_a_settings_file_it_cannot_parse(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text("{ this is not json", encoding="utf-8")
        assert budget.raise_fraction(path, 0.13) is None
        assert path.read_text() == "{ this is not json"

    def test_a_missing_settings_file_is_not_created(self, tmp_path):
        path = tmp_path / "settings.json"
        assert budget.raise_fraction(path, 0.13) is None
        assert not path.exists()

    def test_a_non_numeric_stored_value_is_treated_as_the_default(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"skillListingBudgetFraction": "lots"}), encoding="utf-8")
        assert budget.raise_fraction(path, 0.13) == (0.01, 0.13)


class TestMain:
    def _run(self, capsys):
        budget.main()
        return capsys.readouterr().out

    def test_raises_the_fraction_and_reports_it(self, tmp_path, monkeypatch, capsys):
        big = "Use when " + "z" * 400
        config = make_config(tmp_path, plugin_skills=[(f"s{i}", big) for i in range(40)])
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        out = self._run(capsys)
        stored = json.loads((config / "settings.json").read_text())["skillListingBudgetFraction"]
        assert stored > 0.01
        assert "skillListingBudgetFraction raised" in json.loads(out)["systemMessage"]

    def test_the_written_fraction_covers_the_measured_demand(self, tmp_path, monkeypatch, capsys):
        big = "Use when " + "z" * 400
        config = make_config(tmp_path, plugin_skills=[(f"s{i}", big) for i in range(40)])
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        self._run(capsys)
        stored = json.loads((config / "settings.json").read_text())["skillListingBudgetFraction"]
        demand = budget.listing_demand(budget.installed_skills(config))
        assert stored * budget.DENOMINATOR_FLOOR >= demand

    def test_a_second_run_is_silent_and_changes_nothing(self, tmp_path, monkeypatch, capsys):
        big = "Use when " + "z" * 400
        config = make_config(tmp_path, plugin_skills=[(f"s{i}", big) for i in range(40)])
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        self._run(capsys)
        first = (config / "settings.json").read_text()
        assert self._run(capsys) == ""
        assert (config / "settings.json").read_text() == first

    def test_a_new_skill_raises_the_fraction_again(self, tmp_path, monkeypatch, capsys):
        big = "Use when " + "z" * 400
        config = make_config(tmp_path, plugin_skills=[(f"s{i}", big) for i in range(40)])
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        self._run(capsys)
        settled = json.loads((config / "settings.json").read_text())["skillListingBudgetFraction"]
        skills_dir = tmp_path / "cache" / "demo" / "1.0.0" / "skills"
        for i in range(40, 120):
            write_skill(skills_dir, f"s{i}", big)
        assert "raised" in json.loads(self._run(capsys))["systemMessage"]
        assert json.loads((config / "settings.json").read_text())["skillListingBudgetFraction"] > settled

    def test_a_small_catalogue_leaves_the_default_alone(self, tmp_path, monkeypatch, capsys):
        config = make_config(tmp_path, plugin_skills=[("tiny", "Use when tiny")])
        (config / "settings.json").write_text(json.dumps({"skillListingBudgetFraction": 0.5}), encoding="utf-8")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        assert self._run(capsys) == ""

    def test_an_empty_catalogue_writes_nothing(self, tmp_path, monkeypatch, capsys):
        config = make_config(tmp_path)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        assert self._run(capsys) == ""
        assert "skillListingBudgetFraction" not in json.loads((config / "settings.json").read_text())


class TestConfigDir:
    def test_prefers_the_environment_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
        assert budget.config_dir() == tmp_path

    def test_falls_back_to_the_home_directory(self, monkeypatch):
        monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
        assert budget.config_dir().name == ".claude"


class TestBuildMessage:
    def test_names_both_values_and_the_skill_count(self):
        message = budget.build_message([("a", "b")] * 7, 53_475, (0.01, 0.13))
        assert "0.01 -> 0.13" in message
        assert "7 installed skills" in message
        assert "53,475" in message


@pytest.mark.parametrize("demand", [1, 600, 53_475, 250_000])
def test_required_fraction_always_covers_its_demand(demand):
    assert budget.required_fraction(demand) * budget.DENOMINATOR_FLOOR >= min(demand * budget.SAFETY, 300_000)


def write_listing(config, session, content, mtime=None):
    """Write a transcript carrying one skill_listing attachment, and return its path."""
    project = config / "projects" / "proj"
    project.mkdir(parents=True, exist_ok=True)
    path = project / f"{session}.jsonl"
    path.write_text(
        json.dumps({"type": "other"}) + "\n"
        + json.dumps({"type": "attachment", "attachment": {"type": "skill_listing", "content": content}}) + "\n",
        encoding="utf-8",
    )
    if mtime is not None:
        import os

        os.utime(path, (mtime, mtime))
    return path


class TestStoredFraction:
    def test_reads_a_configured_value(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({"skillListingBudgetFraction": 0.2}), encoding="utf-8")
        assert budget.stored_fraction(path) == 0.2

    def test_falls_back_to_the_harness_default_when_unset(self, tmp_path):
        path = tmp_path / "settings.json"
        path.write_text(json.dumps({}), encoding="utf-8")
        assert budget.stored_fraction(path) == budget.HARNESS_DEFAULT_FRACTION

    def test_falls_back_for_an_unreadable_or_unparsable_file(self, tmp_path):
        path = tmp_path / "settings.json"
        assert budget.stored_fraction(path) == budget.HARNESS_DEFAULT_FRACTION
        path.write_text("{nope", encoding="utf-8")
        assert budget.stored_fraction(path) == budget.HARNESS_DEFAULT_FRACTION


class TestNewestListing:
    def test_separates_bare_entries_from_described_ones(self, tmp_path):
        config = make_config(tmp_path)
        write_listing(config, "s1", "- a:one: has a description\n- b:two\n- c:three")
        found = budget.newest_listing(config)
        assert found["bare"] == ["b:two", "c:three"]
        assert found["total"] == len("- a:one: has a description\n- b:two\n- c:three")

    def test_reads_the_newest_transcript_not_the_first(self, tmp_path):
        config = make_config(tmp_path)
        write_listing(config, "old", "- x:stale\n- y:stale", mtime=1_000_000)
        write_listing(config, "new", "- z:fresh", mtime=2_000_000)
        assert budget.newest_listing(config)["bare"] == ["z:fresh"]

    def test_accepts_content_delivered_as_a_list(self, tmp_path):
        config = make_config(tmp_path)
        write_listing(config, "s1", ["- a:one: described\n- b:two"])
        assert budget.newest_listing(config)["bare"] == ["b:two"]

    def test_returns_none_when_no_transcript_has_a_listing(self, tmp_path):
        config = make_config(tmp_path)
        (config / "projects" / "proj").mkdir(parents=True)
        (config / "projects" / "proj" / "s.jsonl").write_text(json.dumps({"type": "other"}) + "\n", encoding="utf-8")
        assert budget.newest_listing(config) is None

    def test_returns_none_when_there_are_no_transcripts_at_all(self, tmp_path):
        assert budget.newest_listing(make_config(tmp_path)) is None


class TestObservedRequirement:
    def test_scales_the_current_fraction_by_what_was_owed(self):
        listing = {"total": 10_000, "bare": ["x"]}   # >= DENOMINATOR_FLOOR * 0.01, so not stale
        got = budget.observed_requirement(listing, {"x": "d" * 998}, 0.01)
        assert got == pytest.approx(0.01 * 11_000 / 10_000 * budget.SAFETY)

    def test_a_listing_from_before_the_last_raise_is_ignored(self):
        # the real case this guard exists for: a 29,998-char listing produced at 0.01, read back
        # when the setting has since become 0.13. Scaling 0.13 by that shortfall gave 0.29.
        listing = {"total": 29_998, "bare": ["x"]}
        assert budget.observed_requirement(listing, {"x": "d" * 400}, 0.13) is None

    def test_the_same_listing_is_trusted_at_the_fraction_that_produced_it(self):
        listing = {"total": 29_998, "bare": ["x"]}
        assert budget.observed_requirement(listing, {"x": "d" * 400}, 0.01) is not None

    def test_a_listing_with_nothing_bare_asks_for_no_correction(self):
        assert budget.observed_requirement({"total": 1000, "bare": []}, {"x": "d"}, 0.10) is None

    def test_no_listing_at_all_asks_for_no_correction(self):
        assert budget.observed_requirement(None, {"x": "d"}, 0.10) is None

    def test_a_bare_entry_we_cannot_resolve_is_treated_as_bundled(self):
        # a bundled skill has no SKILL.md on disk, and is exempt from the rationing anyway
        assert budget.observed_requirement({"total": 10_000, "bare": ["mystery"]}, {}, 0.01) is None

    def test_the_correction_does_not_depend_on_context_size_or_chars_per_token(self):
        # both cancel in the ratio, which is the whole point: it holds on any model
        listing = {"total": 20_000, "bare": ["x"]}
        assert budget.observed_requirement(listing, {"x": "d" * 998}, 0.01) == pytest.approx(
            0.01 * 21_000 / 20_000 * budget.SAFETY
        )

    def test_an_owed_description_over_the_cap_is_charged_at_the_cap(self):
        listing = {"total": 20_000, "bare": ["x"]}
        owed = 2 + budget.MAX_DESC_CHARS
        assert budget.observed_requirement(listing, {"x": "d" * 5_000}, 0.01) == pytest.approx(
            0.01 * (20_000 + owed) / 20_000 * budget.SAFETY
        )


class TestWantedFraction:
    def test_uses_the_disk_estimate_when_there_is_no_listing_to_learn_from(self, tmp_path):
        config = make_config(tmp_path, plugin_skills=[("one", "Use when one")])
        wanted, dropped = budget.wanted_fraction(config, budget.installed_skills(config), 0.01)
        assert wanted == budget.required_fraction(budget.listing_demand(budget.installed_skills(config)))
        assert dropped == 0

    def test_an_observed_shortfall_can_raise_above_the_disk_estimate(self, tmp_path):
        long_desc = "Use when " + "q" * 900
        config = make_config(tmp_path, plugin_skills=[("one", long_desc)])
        # a listing big enough to have been produced at 0.20, still dropping demo:one
        write_listing(config, "s1", "- demo:one\n- filler:x: " + "y" * 130_000)
        entries = budget.installed_skills(config)
        estimate = budget.required_fraction(budget.listing_demand(entries))
        wanted, dropped = budget.wanted_fraction(config, entries, 0.20)
        assert dropped == 1
        assert wanted > estimate

    def test_it_reports_how_many_descriptions_were_dropped(self, tmp_path):
        config = make_config(tmp_path, plugin_skills=[("one", "Use when one"), ("two", "Use when two")])
        write_listing(config, "s1", "- demo:one\n- demo:two\n- filler:x: " + "y" * 7_000)
        _, dropped = budget.wanted_fraction(config, budget.installed_skills(config), 0.01)
        assert dropped == 2

    def test_it_never_exceeds_the_cap(self, tmp_path):
        config = make_config(tmp_path, plugin_skills=[("one", "Use when " + "q" * 900)])
        write_listing(config, "s1", "- demo:one\n- filler:x: " + "y" * 300_000)
        wanted, _ = budget.wanted_fraction(config, budget.installed_skills(config), 0.49)
        assert wanted <= budget.FRACTION_CAP


class TestBuildMessageEvidence:
    def test_names_the_dropped_count_when_the_listing_showed_one(self):
        message = budget.build_message([("a", "b")], 500, (0.01, 0.13), dropped=38)
        assert "dropped 38 description(s)" in message

    def test_falls_back_to_the_disk_estimate_wording(self):
        message = budget.build_message([("a", "b")] * 7, 500, (0.01, 0.13), dropped=0)
        assert "7 installed skills" in message
