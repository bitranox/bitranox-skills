"""Behaviour tests for the skill-listing-budget SessionStart hook.

Every case builds a real config tree on disk and runs the real functions against it; the only
substitution is CLAUDE_CONFIG_DIR, which is the hook's actual environment seam.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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


def make_config(tmp_path, plugin_skills=(), user_skills=(), name="claude"):
    """Build a config dir with one installed plugin and a personal skills dir."""
    config = tmp_path / name
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

    @pytest.mark.parametrize("plugins", [[], "x", 7])
    def test_a_plugins_value_that_is_not_an_object_still_finds_user_skills(self, tmp_path, plugins):
        config = make_config(tmp_path, user_skills=[("solo", "Use when solo")])
        manifest = config / "plugins" / "installed_plugins.json"
        manifest.write_text(json.dumps({"version": 2, "plugins": plugins}), encoding="utf-8")
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


def iso(epoch):
    """Render an epoch the way a transcript record stamps itself: UTC, milliseconds, a Z."""
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def listing_record(content, timestamp=None, cwd=None, initial=True):
    """A skill_listing transcript record. It is stamped a minute AHEAD by default, so it reads as
    produced under whatever settings.json holds when the test runs."""
    record = {
        "type": "attachment",
        "timestamp": iso(time.time() + 60 if timestamp is None else timestamp),
        "attachment": {"type": "skill_listing", "content": content, "isInitial": initial},
    }
    if cwd is not None:
        record["cwd"] = str(cwd)
    return record


def write_transcript(config, session, records, mtime=None):
    """Write a transcript; a str record is written verbatim so a test can plant a broken line."""
    project = config / "projects" / "proj"
    project.mkdir(parents=True, exist_ok=True)
    path = project / f"{session}.jsonl"
    path.write_text(
        "\n".join(r if isinstance(r, str) else json.dumps(r) for r in records) + "\n", encoding="utf-8"
    )
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def write_listing(config, session, content, mtime=None, **record):
    """Write a transcript carrying one skill_listing attachment, and return its path."""
    return write_transcript(config, session, [{"type": "other"}, listing_record(content, **record)], mtime)


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

    @pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity", "true", "false"])
    def test_a_value_that_is_not_a_finite_number_is_no_fraction(self, tmp_path, raw):
        # Python's json reads NaN and Infinity, and a bool is an int to isinstance
        path = tmp_path / "settings.json"
        path.write_text('{"skillListingBudgetFraction": %s}' % raw, encoding="utf-8")
        assert budget.stored_fraction(path) == budget.HARNESS_DEFAULT_FRACTION

    @pytest.mark.parametrize("raw", ["NaN", "Infinity", "true"])
    def test_raising_over_a_value_that_is_not_a_fraction_reports_the_default_it_replaced(self, tmp_path, raw):
        path = tmp_path / "settings.json"
        path.write_text('{"skillListingBudgetFraction": %s, "model": "opus"}' % raw, encoding="utf-8")
        assert budget.raise_fraction(path, 0.05) == (budget.HARNESS_DEFAULT_FRACTION, 0.05)
        assert json.loads(path.read_text()) == {"skillListingBudgetFraction": 0.05, "model": "opus"}


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


GOOD = "- a:one: described\n- z:fresh"
PROMPT_NAMING_THE_MARKER = {"type": "user", "message": {"content": "skill_listing"}}
TOOL_USE_NAMING_THE_MARKER = {
    "type": "assistant",
    "message": {"content": [{"type": "tool_use", "name": "Grep", "input": {"pattern": "skill_listing"}}]},
}
HOOK_NOTE_NAMING_THE_MARKER = {"type": "attachment", "attachment": {"type": "hook_note", "text": "skill_listing"}}


class TestListingReader:
    """Every line that merely MENTIONS the marker is skipped, and the real listing after it is read.

    These are the cases the roster's reader already skips; the hook now reads through that reader.
    """

    @pytest.mark.parametrize("noise", [PROMPT_NAMING_THE_MARKER, TOOL_USE_NAMING_THE_MARKER, HOOK_NOTE_NAMING_THE_MARKER])
    def test_a_line_naming_the_marker_is_skipped_and_the_later_listing_read(self, tmp_path, noise):
        assert '"skill_listing"' in json.dumps(noise)  # it passes the substring filter
        config = make_config(tmp_path)
        write_transcript(config, "s1", [noise, listing_record(GOOD)])
        assert budget.newest_listing(config)["bare"] == ["z:fresh"]

    def test_a_truncated_listing_line_is_skipped_and_the_later_listing_read(self, tmp_path):
        config = make_config(tmp_path)
        cut = json.dumps(listing_record("- cut:off"))[:120]
        assert '"skill_listing"' in cut  # it passes the substring filter and must fail the decode
        write_transcript(config, "s1", [cut, listing_record(GOOD)])
        assert budget.newest_listing(config)["bare"] == ["z:fresh"]

    def test_a_json_line_that_is_not_an_object_is_skipped(self, tmp_path):
        config = make_config(tmp_path)
        write_transcript(config, "s1", ['["skill_listing"]', HOOK_NOTE_NAMING_THE_MARKER, listing_record(GOOD)])
        assert budget.newest_listing(config)["bare"] == ["z:fresh"]

    def test_a_skipped_line_does_not_send_the_scan_to_an_older_transcript(self, tmp_path):
        config = make_config(tmp_path)
        write_listing(config, "old", "- OLD:stale", mtime=1_000_000)
        write_transcript(config, "new", [TOOL_USE_NAMING_THE_MARKER, listing_record(GOOD)], mtime=2_000_000)
        assert budget.newest_listing(config)["bare"] == ["z:fresh"]

    def test_the_last_listing_in_a_transcript_wins(self, tmp_path):
        # /reload-plugins writes a second full listing; the first no longer describes the session
        config = make_config(tmp_path)
        write_transcript(config, "s1", [listing_record("- FIRST:one"), listing_record("- LAST:two")])
        assert budget.newest_listing(config)["bare"] == ["LAST:two"]

    def test_a_delta_listing_does_not_replace_the_full_one(self, tmp_path):
        # a delta carries only the skills added since, so it is not the listing the budget packed
        config = make_config(tmp_path)
        write_transcript(config, "s1", [listing_record("- full:bare"), listing_record("- new:x: d", initial=False)])
        assert budget.newest_listing(config)["bare"] == ["full:bare"]

    @pytest.mark.parametrize("empty", ["", [], None])
    def test_a_later_listing_with_no_content_does_not_hide_an_earlier_one(self, tmp_path, empty):
        config = make_config(tmp_path)
        write_transcript(config, "s1", [listing_record(GOOD), listing_record(empty)])
        assert budget.newest_listing(config)["bare"] == ["z:fresh"]

    def test_only_the_newest_transcripts_are_opened(self, tmp_path):
        config = make_config(tmp_path)
        write_listing(config, "oldest", "- a:b", mtime=1_000_000)
        for i in range(5):
            write_transcript(config, f"s{i}", [{"type": "other"}], mtime=2_000_000 + i)
        assert budget.newest_listing(config, max_files=5) is None
        assert budget.newest_listing(config, max_files=6)["bare"] == ["a:b"]

    def test_a_description_line_that_reads_like_an_entry_is_not_a_bare_name(self, tmp_path):
        # `names` is the installed set; a description continuing on a line that starts "- " and
        # holds no ": " belongs to the entry above it, not to a skill of that name
        config = make_config(tmp_path)
        content = "- a:one: Use when X. Covers:\n- the first case\n- b:two"
        record = listing_record(content)
        record["attachment"]["names"] = ["a:one", "b:two"]
        write_transcript(config, "s1", [record])
        assert budget.newest_listing(config)["bare"] == ["b:two"]

    def test_without_names_the_lines_decide(self, tmp_path):
        config = make_config(tmp_path)
        write_listing(config, "s1", "- a:one: Use when X\n- b:two")
        assert budget.newest_listing(config)["bare"] == ["b:two"]

    def test_it_reports_when_and_where_the_listing_was_produced(self, tmp_path):
        config = make_config(tmp_path)
        write_listing(config, "s1", GOOD, timestamp=1_700_000_000, cwd=tmp_path / "proj")
        found = budget.newest_listing(config)
        assert found["timestamp"] == pytest.approx(1_700_000_000, abs=0.001)
        assert found["cwd"] == str(tmp_path / "proj")


def big_skill_config(tmp_path, fraction, **kwargs):
    """One personal skill whose 2k description the disk estimate covers at any fraction >= 0.03."""
    config = make_config(tmp_path, user_skills=[("big", "Use when " + "b" * 2000)], **kwargs)
    (config / "settings.json").write_text(json.dumps({"skillListingBudgetFraction": fraction}), encoding="utf-8")
    return config


def over_budget_listing(total):
    """A listing packed to `total` chars that still dropped `big` to a bare name."""
    head = "- big\n- filler:x: "
    return head + "y" * (total - len(head))


def stored(config):
    return json.loads((config / "settings.json").read_text())["skillListingBudgetFraction"]


def age(path, seconds):
    then = time.time() - seconds
    os.utime(path, (then, then))
    return then


class TestStaleListing:
    def test_a_listing_read_again_at_every_session_start_moves_the_fraction_once(self, tmp_path, monkeypatch, capsys):
        # 1M-token context x 4 chars/token x 0.10 = 400,000 chars: above the floor guard at every
        # fraction up to the cap, so only the timestamp can tell the listing is from before a raise.
        config = big_skill_config(tmp_path, 0.10)
        settings_written = age(config / "settings.json", 3600)
        write_listing(config, "s1", over_budget_listing(400_000), timestamp=settings_written + 1800)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        seen = [stored(config)]
        for _ in range(8):
            budget.main()
            seen.append(stored(config))
        capsys.readouterr()
        moves = [pair for pair in zip(seen, seen[1:]) if pair[0] != pair[1]]
        assert len(moves) == 1, seen

    def test_a_listing_older_than_the_settings_file_is_no_correction(self, tmp_path, monkeypatch, capsys):
        config = big_skill_config(tmp_path, 0.10)
        settings_written = age(config / "settings.json", 3600)
        write_listing(config, "s1", over_budget_listing(400_000), timestamp=settings_written - 10)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        budget.main()
        assert capsys.readouterr().out == ""
        assert stored(config) == 0.10

    @pytest.mark.parametrize("stamp", [None, "not a time", 12345])
    def test_a_listing_with_no_readable_timestamp_is_no_correction(self, tmp_path, stamp):
        config = big_skill_config(tmp_path, 0.10)
        record = listing_record(over_budget_listing(400_000))
        record["timestamp"] = stamp
        write_transcript(config, "s1", [record])
        entries = budget.installed_skills(config)
        assert budget.wanted_fraction(config, entries, 0.10) == (budget.required_fraction(budget.listing_demand(entries)), 0)

    def test_with_no_settings_file_a_listing_is_current(self, tmp_path):
        assert budget.listing_is_current({"timestamp": 1.0}, tmp_path / "settings.json") is True

    def test_a_fresh_listing_with_nothing_bare_asks_for_no_correction(self, tmp_path):
        config = big_skill_config(tmp_path, 0.10)
        write_listing(config, "s1", "- big: Use when b")
        assert budget.wanted_fraction(config, budget.installed_skills(config), 0.10)[1] == 0

    def test_a_fresh_listing_is_still_a_correction(self, tmp_path):
        config = big_skill_config(tmp_path, 0.10)
        write_listing(config, "s1", over_budget_listing(400_000))
        _, dropped = budget.wanted_fraction(config, budget.installed_skills(config), 0.10)
        assert dropped == 1


class TestProjectOverride:
    """Only the USER-level fraction is managed; a listing a project override produced is skipped."""

    @pytest.mark.parametrize("name", ["settings.json", "settings.local.json"])
    def test_a_listing_from_a_project_that_sets_its_own_fraction_is_skipped(self, tmp_path, name):
        config = big_skill_config(tmp_path, 0.10)
        project = tmp_path / "work"
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / name).write_text(json.dumps({"skillListingBudgetFraction": 0.3}), encoding="utf-8")
        write_listing(config, "s1", over_budget_listing(400_000), cwd=project)
        entries = budget.installed_skills(config)
        assert budget.wanted_fraction(config, entries, 0.10) == (budget.required_fraction(budget.listing_demand(entries)), 0)

    def test_a_project_settings_file_without_the_key_is_no_override(self, tmp_path):
        config = big_skill_config(tmp_path, 0.10)
        project = tmp_path / "work"
        (project / ".claude").mkdir(parents=True)
        (project / ".claude" / "settings.json").write_text(json.dumps({"model": "opus"}), encoding="utf-8")
        write_listing(config, "s1", over_budget_listing(400_000), cwd=project)
        _, dropped = budget.wanted_fraction(config, budget.installed_skills(config), 0.10)
        assert dropped == 1

    def test_a_session_run_from_home_is_not_overridden_by_the_user_settings(self, tmp_path):
        # cwd == HOME makes <cwd>/.claude the config dir itself: that is the value this hook manages
        config = big_skill_config(tmp_path, 0.10, name=".claude")
        write_listing(config, "s1", over_budget_listing(400_000), cwd=tmp_path)
        _, dropped = budget.wanted_fraction(config, budget.installed_skills(config), 0.10)
        assert dropped == 1


HOOK = Path(__file__).resolve().parents[1] / "skill-listing-budget.py"


@pytest.mark.parametrize("roster_importable", [True, False])
def test_the_estimate_survives_a_listing_reader_that_will_not_import(tmp_path, roster_importable):
    """The listing reader pulls in the router's classifier and signal modules; an import error
    there may cost the correction, never the disk estimate. Run as Claude Code runs it."""
    config = make_config(tmp_path, plugin_skills=[(f"s{i}", "Use when " + "z" * 400) for i in range(40)])
    block = "" if roster_importable else "sys.modules['skill_roster'] = None; "
    bootstrap = ("import runpy, sys; sys.path.insert(0, %r); %srunpy.run_path(%r, run_name='__main__')"
                 % (str(HOOK.parent), block, str(HOOK)))
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config), "PYTHONUTF8": "1"}
    done = subprocess.run([sys.executable, "-c", bootstrap], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=60)
    assert done.returncode == 0, done.stderr
    assert "raised" in json.loads(done.stdout)["systemMessage"]
    assert stored(config) == budget.required_fraction(budget.listing_demand(budget.installed_skills(config)))


class TestTheEstimateSurvivesABadReading:
    def forty_skills(self, tmp_path):
        return make_config(tmp_path, plugin_skills=[(f"s{i}", "Use when " + "z" * 400) for i in range(40)])

    def test_a_non_object_marker_line_does_not_cost_the_disk_estimate(self, tmp_path, monkeypatch, capsys):
        config = self.forty_skills(tmp_path)
        write_transcript(config, "s1", ['["skill_listing"]'])
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        budget.main()
        assert "raised" in json.loads(capsys.readouterr().out)["systemMessage"]
        assert stored(config) == budget.required_fraction(budget.listing_demand(budget.installed_skills(config)))

    def test_a_correction_that_cannot_be_computed_falls_back_to_the_estimate(self, tmp_path, monkeypatch, capsys):
        # Python's json reads NaN, and a NaN fraction makes the correction's arithmetic raise
        config = self.forty_skills(tmp_path)
        (config / "settings.json").write_text('{"skillListingBudgetFraction": NaN}', encoding="utf-8")
        write_listing(config, "s1", "- demo:s0\n- filler:x: " + "y" * 7_000)
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
        budget.main()
        capsys.readouterr()
        assert stored(config) == budget.required_fraction(budget.listing_demand(budget.installed_skills(config)))
