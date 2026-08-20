"""Tests for the upstream-drift checker.

No test touches the network. Every verdict is reachable through the ``--body`` seam or an injected
fetcher, which is deliberate: a suite that needed the wire would pass by silently skipping on a CI
runner without one, and a freshness check that can pass by not running is the failure it exists to
prevent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import hookdoc_stamp as H

SKILL = Path(__file__).resolve().parents[1]
FIXTURES = SKILL / "tests" / "fixtures"
SHIPPED_STAMP = SKILL / "references" / "upstream-stamp.json"
REFS = SKILL / "references"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def sample_record() -> dict:
    return json.loads((FIXTURES / "stamp-sample.json").read_text(encoding="utf-8"))["sources"][0]


# --------------------------------------------------------------------------- normalisation


def test_normalise_drops_only_the_preamble_before_the_h1():
    body = H.normalise(fixture("hooks-sample.md"))
    assert body.startswith("# Hooks reference")
    assert "Documentation Index" not in body
    assert "## Hook events" in body


def test_normalise_is_idempotent():
    once = H.normalise(fixture("hooks-sample.md"))
    assert H.normalise(once) == once


def test_normalise_on_a_body_with_no_h1_is_broken_not_empty():
    with pytest.raises(H.ControlError):
        H.normalise(b"just some text\nwith no heading at all\n")


def test_normalise_rejects_invalid_utf8_as_broken():
    with pytest.raises(H.ControlError):
        H.normalise(b"# Title\n\xff\xfe not utf-8\n")


def test_normalise_erases_crlf_and_trailing_whitespace_only():
    src = "# T\r\n\r\nkeep   this   spacing   \r\n"
    out = H.normalise(src.encode("utf-8"))
    assert "\r" not in out
    assert "keep   this   spacing" in out, "intra-line spacing must survive so a realignment stays visible"


def test_normalise_collapses_long_blank_runs_to_at_most_two():
    out = H.normalise(b"# T\n\n\n\n\n\n\nbody\n")
    assert "\n\n\n\n" not in out, "a run longer than two blank lines must be collapsed"
    assert "body" in out


# --------------------------------------------------------------------------- fingerprint


def test_fingerprint_lists_every_event_heading():
    fp = H.fingerprint(H.normalise(fixture("hooks-sample.md")))
    assert len(fp["events"]) == 31, "the fixture carries all 31 event headings"
    assert "PreToolUse" in fp["events"]


def test_fingerprint_reads_fences_whose_info_string_carries_an_attribute():
    """The upstream page writes fences as ```json theme={null}.

    A pattern that accepts only a bare language word rejects that opener and then reads the bare
    closing fence as an opener, inverting the fence state for the rest of the document. Measured
    against the live page, that yielded 0 of 31 events while reporting no error at all.
    """
    body = H.normalise(fixture("hooks-sample.md"))
    assert "theme={null}" in body, "the fixture must keep the attribute-bearing fence"
    fp = H.fingerprint(body)
    assert len(fp["events"]) == 31
    assert fp["handler_types"], "json fences must be recognised so handler types are extracted"


def test_fingerprint_ignores_headings_inside_fenced_code_blocks():
    text = "# T\n\n## Real\n\n```bash\n# not a heading\n## also not a heading\n```\n\n## Also Real\n"
    fp = H.fingerprint(H.normalise(text.encode("utf-8")))
    assert "H2:Real" in fp["headings"] and "H2:Also Real" in fp["headings"]
    assert not any("not a heading" in h for h in fp["headings"])


def test_fingerprint_is_stable_when_two_event_sections_swap_places():
    """Membership defines the surface, so document order must not reach the structural digest."""
    body = H.normalise(fixture("hooks-sample.md"))
    a, b = "### PreToolUse\n\nFires for PreToolUse. See the table above.\n", "### Stop\n\nFires for Stop. See the table above.\n"
    assert a in body and b in body
    swapped = body.replace(a, "@@A@@").replace(b, a).replace("@@A@@", b)
    assert swapped != body
    assert H.structure_sha(H.fingerprint(swapped)) == H.structure_sha(H.fingerprint(body))


def test_fingerprint_changes_when_an_event_is_renamed():
    a = H.fingerprint(H.normalise(fixture("hooks-sample.md")))
    b = H.fingerprint(H.normalise(fixture("hooks-sample-structural.md")))
    assert H.structure_sha(a) != H.structure_sha(b)
    assert "PostToolGroup" in b["events"] and "PostToolBatch" not in b["events"]


def test_fingerprint_ignores_prose_rewording_and_unbackticked_table_cells():
    a = H.fingerprint(H.normalise(fixture("hooks-sample.md")))
    b = H.fingerprint(H.normalise(fixture("hooks-sample-cosmetic.md")))
    assert H.structure_sha(a) == H.structure_sha(b), "rewording must not read as an API change"


def test_fingerprint_excludes_json_schema_primitives_from_handler_types():
    text = '# T\n\n## S\n\n```json theme={null}\n{ "type": "object" }\n{ "type": "command" }\n```\n'
    fp = H.fingerprint(H.normalise(text.encode("utf-8")))
    assert "command" in fp["handler_types"]
    assert "object" not in fp["handler_types"], "a schema example must not look like a new handler type"


def test_prose_tier_keeps_headings_only():
    fp = H.fingerprint(H.normalise(fixture("hooks-sample.md")), tier="prose")
    assert fp["headings"]
    assert fp["events"] == [] and fp["json_fields"] == []


# --------------------------------------------------------------------------- verdicts


def test_identical_body_is_current():
    assert H.compare(sample_record(), fixture("hooks-sample.md")).verdict == H.CURRENT


def test_reworded_body_is_cosmetic_and_names_the_changed_sections():
    v = H.compare(sample_record(), fixture("hooks-sample-cosmetic.md"))
    assert v.verdict == H.COSMETIC
    assert v.detail["changed_sections"], "a cosmetic report must localise the change"


def test_renamed_event_is_structural_and_names_added_and_removed():
    v = H.compare(sample_record(), fixture("hooks-sample-structural.md"))
    assert v.verdict == H.STRUCTURAL
    assert "PostToolGroup" in v.detail["added"]["events"]
    assert "PostToolBatch" in v.detail["removed"]["events"]


def test_truncated_body_is_broken_not_structural():
    """A short read must not read as 'every event was removed'.

    That verdict would be both false and maximally loud, which is how a checker teaches the people
    who rely on it to stop believing it.
    """
    assert H.compare(sample_record(), fixture("hooks-sample-truncated.md")).verdict == H.BROKEN


def test_a_body_missing_a_required_heading_is_broken():
    rec = sample_record()
    body = H.normalise(fixture("hooks-sample.md")).replace("## Security considerations", "## Something else")
    assert H.compare(rec, body.encode("utf-8")).verdict == H.BROKEN


def test_a_body_with_too_few_events_is_broken_not_structural():
    rec = sample_record()
    body = H.normalise(fixture("hooks-sample.md"))
    head, _, _ = body.partition("### PostToolUse")
    assert H.compare(rec, (head + "## Security considerations\n").encode("utf-8")).verdict == H.BROKEN


# --------------------------------------------------------------------------- fetching


def test_http_error_is_broken():
    with pytest.raises(H.ControlError):
        H.fetch_body("https://example.invalid/x", 1.0, lambda u, t: (404, b"", "text/markdown"))


def test_wrong_content_type_is_broken():
    with pytest.raises(H.ControlError):
        H.fetch_body("https://example.invalid/x", 1.0, lambda u, t: (200, b"# T\n", "text/html"))


def test_fetch_failure_is_broken_never_current():
    def boom(url, timeout):
        raise OSError("Network is unreachable")

    with pytest.raises(H.ControlError):
        H.fetch_body("https://example.invalid/x", 1.0, boom)


def test_fetch_timeout_is_broken_and_returns_within_the_wall():
    import time

    def slow(url, timeout):
        time.sleep(5)
        return (200, b"# T\n", "text/markdown")

    started = time.monotonic()
    with pytest.raises(H.ControlError) as exc:
        H.fetch_with_wall("https://example.invalid/x", 0.3, slow)
    assert "timeout" in str(exc.value)
    assert time.monotonic() - started < 3.0, "the wall must bound the total call, not each socket read"


# --------------------------------------------------------------------------- stamp integrity


def test_unreadable_stamp_is_broken_not_current(tmp_path):
    bad = tmp_path / "s.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(H.ControlError):
        H.load_stamp(bad)


def test_stamp_with_a_foreign_normalisation_id_is_refused(tmp_path):
    stamp = json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))
    stamp["normalisation"]["id"] = "n0"
    p = tmp_path / "s.json"
    p.write_text(json.dumps(stamp), encoding="utf-8")
    with pytest.raises(H.ControlError):
        H.load_stamp(p)


def test_shipped_stamp_declares_the_normalisation_id_the_code_implements():
    stamp = json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))
    assert stamp["normalisation"]["id"] == H.NORMALISATION_ID
    assert stamp["normalisation"]["rules"] == H.NORMALISATION_RULES


def test_shipped_stamp_counts_match_its_own_fingerprint():
    for src in json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))["sources"]:
        for key, count in src["counts"].items():
            assert len(src["fingerprint"][key]) == count, "%s/%s" % (src["name"], key)


def test_shipped_stamp_lists_all_thirty_one_events():
    api = [s for s in json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))["sources"] if s["tier"] == "api"]
    assert len(api) == 1
    assert len(api[0]["fingerprint"]["events"]) == 31


def test_shipped_stamp_has_no_recorded_coverage_gaps():
    assert json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))["coverage_gaps"] == []


# --------------------------------------------------------------------------- coverage


def test_coverage_complete_for_the_shipped_stamp_and_references():
    result = H.coverage(json.loads(SHIPPED_STAMP.read_text(encoding="utf-8")), REFS)
    assert result["missing_events"] == []
    assert result["phantom_events"] == []
    assert result["missing_required"] == []
    assert result["complete"] is True


def test_coverage_reports_a_missing_event_section(tmp_path):
    stamp = json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))
    refs = tmp_path / "references"
    refs.mkdir()
    text = (REFS / "events.md").read_text(encoding="utf-8").replace("### FileChanged", "### Removed")
    (refs / "events.md").write_text(text, encoding="utf-8")
    for name in ("io-contract.md", "configuration.md", "authoring.md"):
        (refs / name).write_text((REFS / name).read_text(encoding="utf-8"), encoding="utf-8")
    result = H.coverage(stamp, refs)
    assert "FileChanged" in result["missing_events"]
    assert result["complete"] is False


def test_a_mere_mention_does_not_count_as_documenting_an_event(tmp_path):
    stamp = json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))
    refs = tmp_path / "references"
    refs.mkdir()
    events = [e for s in stamp["sources"] if s["tier"] == "api" for e in s["fingerprint"]["events"]]
    prose = "# Everything\n\n" + " ".join("The %s event exists." % e for e in events) + "\n"
    (refs / "everything.md").write_text(prose, encoding="utf-8")
    result = H.coverage(stamp, refs)
    assert result["missing_events"], "prose mentions must not satisfy the bar; a heading is required"


def test_coverage_with_no_reference_files_is_broken_not_complete(tmp_path):
    empty = tmp_path / "references"
    empty.mkdir()
    with pytest.raises(H.ControlError):
        H.coverage(json.loads(SHIPPED_STAMP.read_text(encoding="utf-8")), empty)


def test_coverage_with_an_emptied_stamp_is_broken_not_complete():
    with pytest.raises(H.ControlError):
        H.coverage({"sources": [{"name": "x", "tier": "api", "fingerprint": {"events": []}}]}, REFS)


# --------------------------------------------------------------------------- cache


def test_fresh_cache_replays_without_fetching(tmp_path):
    payload = {"verdict": H.CURRENT, "checked_at_epoch": 1000.0, "stamp_sha256": "abc"}
    H.write_cache(tmp_path, payload)
    assert H.read_cache(tmp_path, "abc", 600.0, 1100.0)["cached"] is True


def test_cache_is_invalidated_when_the_stamp_hash_changes(tmp_path):
    H.write_cache(tmp_path, {"verdict": H.CURRENT, "checked_at_epoch": 1000.0, "stamp_sha256": "abc"})
    assert H.read_cache(tmp_path, "different", 600.0, 1100.0) is None


def test_expired_cache_triggers_a_fetch(tmp_path):
    H.write_cache(tmp_path, {"verdict": H.CURRENT, "checked_at_epoch": 1000.0, "stamp_sha256": "abc"})
    assert H.read_cache(tmp_path, "abc", 60.0, 5000.0) is None


def test_a_broken_verdict_expires_sooner_than_a_good_one(tmp_path):
    H.write_cache(tmp_path, {"verdict": H.BROKEN, "checked_at_epoch": 1000.0, "stamp_sha256": "abc"})
    assert H.read_cache(tmp_path, "abc", 604800.0, 1000.0 + 1000.0) is None


# --------------------------------------------------------------------------- selftest


def test_selftest_passes_on_the_shipped_fixtures():
    assert H.run_selftest(FIXTURES)["passed"] is True


def test_selftest_fails_when_the_comparator_always_says_current():
    """The known-negative of the known-negative.

    A comparator that answers CURRENT to everything is indistinguishable from a clean bill of
    health, so the proof itself has to be shown capable of failing.
    """
    always_current = lambda record, raw: H.Verdict("x", H.CURRENT, "stub")  # noqa: E731
    assert H.run_selftest(FIXTURES, comparator=always_current)["passed"] is False


def test_selftest_fails_when_a_fixture_is_missing(tmp_path):
    with pytest.raises(H.ControlError):
        H.run_selftest(tmp_path)


def test_selftest_expects_four_distinct_verdicts():
    got = {expected for _, expected in H.SELFTEST_FIXTURES}
    assert got == {H.CURRENT, H.COSMETIC, H.STRUCTURAL, H.BROKEN}


# --------------------------------------------------------------------------- CLI


def test_exit_codes_match_the_documented_table():
    assert H._EXIT[H.CURRENT] == 0 and H._EXIT[H.COSMETIC] == 0
    assert H._EXIT[H.STRUCTURAL] == 1
    assert H._EXIT[H.BROKEN] == 2


def test_coverage_command_json_envelope_shape(capsys):
    rc = H.main(["coverage", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert set(payload) == {"ok", "command", "data", "skipped"}
    assert payload["command"] == "hookdoc_stamp/coverage"
    assert payload["ok"] is True


def test_check_against_a_local_body_needs_no_network(capsys):
    rc = H.main(["check", "--stamp", str(FIXTURES / "stamp-sample.json"), "--source", "hooks-sample",
                 "--body", str(FIXTURES / "hooks-sample-structural.md"), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["data"]["verdict"] == H.STRUCTURAL


def test_expect_flag_fails_on_a_mismatched_verdict(capsys):
    rc = H.main(["check", "--stamp", str(FIXTURES / "stamp-sample.json"), "--source", "hooks-sample",
                 "--body", str(FIXTURES / "hooks-sample.md"), "--expect", H.STRUCTURAL])
    capsys.readouterr()
    assert rc == 1


def test_json_output_stays_parseable_when_the_stamp_is_broken(tmp_path, capsys):
    bad = tmp_path / "s.json"
    bad.write_text("{not json", encoding="utf-8")
    rc = H.main(["coverage", "--stamp", str(bad), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["ok"] is False
    assert payload["data"]["verdict"] == H.BROKEN


def test_selftest_command_exits_zero(capsys):
    rc = H.main(["selftest"])
    capsys.readouterr()
    assert rc == 0


def test_stamp_dry_run_does_not_write(tmp_path, capsys):
    target = tmp_path / "stamp.json"
    stamp = json.loads(SHIPPED_STAMP.read_text(encoding="utf-8"))
    stamp["sources"] = json.loads((FIXTURES / "stamp-sample.json").read_text(encoding="utf-8"))["sources"]
    target.write_text(json.dumps(stamp), encoding="utf-8")
    before = target.read_bytes()
    rc = H.main(["stamp", "--stamp", str(target), "--refs", str(REFS), "--source", "hooks-sample",
                 "--body", str(FIXTURES / "hooks-sample.md")])
    capsys.readouterr()
    assert rc == 0
    assert target.read_bytes() == before, "a dry run must not touch the stamp"


def test_baseline_check_matches_the_shipped_skill_md(capsys):
    rc = H.main(["baseline"])
    capsys.readouterr()
    assert rc == 0, "SKILL.md baseline line is stale; run: hookdoc_stamp.py baseline --write"


# --------------------------------------------------------------------------- hygiene


def test_a_check_run_leaves_the_skill_dir_untouched(tmp_path, capsys):
    """The installed skill lives inside a git clone that /plugin marketplace update pulls.

    A cache file written into the skill dir would dirty that clone and break the update for every
    user, so all mutable state belongs outside it.
    """
    before = {p: p.stat().st_mtime_ns for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in str(p)}
    H.main(["check", "--stamp", str(FIXTURES / "stamp-sample.json"), "--source", "hooks-sample",
            "--body", str(FIXTURES / "hooks-sample.md"), "--cache-dir", str(tmp_path / "cache")])
    capsys.readouterr()
    after = {p: p.stat().st_mtime_ns for p in SKILL.rglob("*") if p.is_file() and "__pycache__" not in str(p)}
    assert before == after


def test_module_imports_without_third_party_dependencies():
    """The repo gate imports test modules with a bare interpreter and does not provision PEP 723
    dependencies, so any third-party import must stay inside the function that needs it."""
    source = (SKILL / "scripts" / "hookdoc_stamp.py").read_text(encoding="utf-8")
    module_level = [
        line for line in source.split("\n")
        if (line.startswith("import ") or line.startswith("from ")) and "httpx" in line
    ]
    assert module_level == [], "httpx2 must be imported lazily inside _fetch"
