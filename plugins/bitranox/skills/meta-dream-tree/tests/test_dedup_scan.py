"""Tests for dedup_scan.py - near-duplicate CANDIDATES across a curated memory tree.

The dream needs this twice per run and has always hand-rolled it, which is the problem: a
similarity scorer that silently cannot fire returns zero candidates, and zero candidates is
exactly what a clean tree returns too. So the two states are indistinguishable at the moment
you most want to believe the good one.

Three properties make the difference, and they are what most of this file pins:

- A PLANTED POSITIVE runs through the same code path every time. If the scanner cannot find a
  duplicate it inserted itself, the run is an instrument failure and not a clean bill of health.
- The SCORE DISTRIBUTION is reported, so a pair sitting just under the threshold is visible
  rather than silently dropped.
- The output is CANDIDATES. The tool never says two facts are duplicates; it says which two
  bodies to read.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import dedup_scan as DS
import pytest

TOOL = Path(__file__).resolve().parents[1] / "dedup_scan.py"

NEAR_A = ("When a gate reports success, read its exit code from the log rather than from the "
          "job notification, because the notification reports the last command's status.")
NEAR_B = ("When a gate reports success, read the exit code out of the log instead of the job "
          "notification, since the notification carries the last command's status.")
FAR = ("When provisioning a Proxmox container, set the run identity explicitly and verify the "
       "output file permissions as the target user before trusting the unit.")


def facts(*pairs) -> list[DS.Fact]:
    return [DS.Fact(slug=s, level="/lvl", title=s.replace("-", " "), text=t) for s, t in pairs]


# ---- the scorer ------------------------------------------------------------------------------

def test_identical_text_scores_one_and_is_symmetric():
    assert DS.similarity(NEAR_A, NEAR_A) == 1.0
    assert DS.similarity(NEAR_A, FAR) == DS.similarity(FAR, NEAR_A)


def test_a_paraphrase_scores_far_above_an_unrelated_fact():
    """The gap is the whole signal. If a paraphrase and an unrelated fact land close together,
    no threshold can separate them and the tool is noise at every setting."""
    assert DS.similarity(NEAR_A, NEAR_B) > 0.5
    assert DS.similarity(NEAR_A, FAR) < 0.2
    assert DS.similarity(NEAR_A, NEAR_B) > DS.similarity(NEAR_A, FAR) + 0.4


def test_scoring_ignores_case_and_punctuation():
    assert DS.similarity("When X, do Y.", "when x do y") == 1.0


# ---- the planted control ----------------------------------------------------------------------

def test_the_planted_positive_is_detected_on_a_working_scorer():
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.5)
    assert result.control.detected
    assert result.control.score > 0.5


def test_the_planted_positive_is_a_near_duplicate_not_a_reordering():
    """Measured on the real store: the control scored exactly 1.00, because the paraphrase only
    REORDERED words and the scorer compares word SETS - so the plant was an identical input.

    Such a control proves the scorer is not string equality and nothing more. It would fire
    happily on an instrument that misses every real near-duplicate, which is the one thing the
    control exists to rule out. A genuine plant must differ in WORDS: high, but under 1.0.
    """
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.5)
    assert 0.5 < result.control.score < 1.0


def test_a_scorer_that_cannot_fire_is_reported_as_an_instrument_failure_not_a_clean_tree():
    """The failure this tool exists to make visible: a broken scorer and a clean tree both
    return zero candidates, and only the control tells them apart."""
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.5,
                    scorer=lambda x, y: 0.0)
    assert result.candidates == []
    assert not result.control.detected
    assert result.instrument_failed


def test_a_clean_tree_reports_zero_candidates_with_the_control_still_passing():
    """The other side of the same coin: zero candidates is only trustworthy while the control
    fired, so both facts must be reported together."""
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.95)
    assert result.candidates == []
    assert result.control.detected and not result.instrument_failed


def test_the_planted_pair_never_appears_among_the_candidates():
    result = DS.run(facts(("a", NEAR_A), ("b", NEAR_B)), threshold=0.5)
    slugs = {s for c in result.candidates for s in (c.a.slug, c.b.slug)}
    assert not any(s.startswith(DS.CONTROL_PREFIX) for s in slugs)


# ---- candidates -------------------------------------------------------------------------------

def test_a_near_duplicate_pair_is_reported_with_both_slugs_and_a_score():
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B), ("other", FAR)), threshold=0.5)
    assert len(result.candidates) == 1
    cand = result.candidates[0]
    assert {cand.a.slug, cand.b.slug} == {"first", "second"}
    assert cand.score > 0.5


def test_candidates_are_sorted_by_score_descending():
    mid = NEAR_A.replace("exit code", "return code").replace("notification", "message")
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B), ("third", mid)), threshold=0.3)
    scores = [c.score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)


def test_a_pair_is_reported_once_not_in_both_orders():
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B)), threshold=0.5)
    assert len(result.candidates) == 1


def test_the_distribution_is_reported_so_a_near_miss_under_the_threshold_is_visible():
    """A pair at 0.49 against a 0.50 threshold is the one a reader most needs to see. Dropping
    it silently is how a threshold becomes a way of not looking."""
    result = DS.run(facts(("first", NEAR_A), ("second", NEAR_B), ("other", FAR)), threshold=0.99)
    assert result.candidates == []
    assert sum(result.distribution.values()) >= 1
    assert any(bucket >= 0.5 for bucket, n in result.distribution.items() if n)


# ---- reading a real tree ------------------------------------------------------------------------

def make_tree(root: Path) -> None:
    (root / "CLAUDE.md").write_text("anchor\n", encoding="utf-8")
    (root / ".claude-memory" / "facts").mkdir(parents=True)
    (root / "CLAUDE.local.md").write_text(
        "# Memory index\n"
        "- [First](mem:first-slug) - When first, do first.\n"
        "- [Second](mem:second-slug) - When second, do second.\n", encoding="utf-8")
    for slug, body in (("first-slug", NEAR_A), ("second-slug", NEAR_B)):
        (root / ".claude-memory" / "facts" / f"{slug}.md").write_text(
            f"---\nname: {slug}\ndescription: d\n---\n\n{body}\n", encoding="utf-8")


def test_facts_are_loaded_with_their_level_so_a_candidate_can_be_opened(tmp_path):
    make_tree(tmp_path)
    loaded = DS.load_facts(tmp_path)
    assert {f.slug for f in loaded} == {"first-slug", "second-slug"}
    assert all(f.level.endswith(str(tmp_path)) or str(tmp_path) in f.level for f in loaded)


def run_cli(args, cwd):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", check=False, cwd=str(cwd))


def test_cli_exits_1_and_frames_the_output_as_candidates(tmp_path):
    make_tree(tmp_path)
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.5", "--json"], tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert "candidates" in env["data"]
    assert env["data"]["control"]["detected"] is True
    assert env["data"]["candidates"][0]["score"] > 0.5


def test_cli_exits_0_on_a_tree_with_nothing_near_duplicate(tmp_path):
    make_tree(tmp_path)
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.99", "--json"], tmp_path)
    assert r.returncode == 0
    assert json.loads(r.stdout)["data"]["candidates"] == []


def test_cli_exits_2_when_there_is_no_tree(tmp_path):
    r = run_cli(["--from", str(tmp_path / "nope"), "--json"], tmp_path)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


# ---- read errors: a fact the scan could not read is never a silent "clean" ----------------------

NO_CHMOD = not hasattr(os, "geteuid") or os.geteuid() == 0


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for chmod 000")
def test_an_unreadable_fact_is_reported_and_exits_2(tmp_path):
    make_tree(tmp_path)
    body = tmp_path / ".claude-memory" / "facts" / "second-slug.md"
    body.chmod(0)
    try:
        r = run_cli(["--from", str(tmp_path), "--threshold", "0.5", "--json"], tmp_path)
    finally:
        body.chmod(0o644)
    assert r.returncode == 2, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is False and str(body) in " ".join(env["skipped"])


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for chmod 000")
def test_an_unreadable_level_is_reported_and_exits_2(tmp_path):
    make_tree(tmp_path)
    level = tmp_path / "CLAUDE.local.md"
    level.chmod(0)
    try:
        r = run_cli(["--from", str(tmp_path), "--threshold", "0.5"], tmp_path)
    finally:
        level.chmod(0o644)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "could not be read" in r.stdout and str(level) in r.stdout


def test_a_non_utf8_fact_is_reported_not_a_traceback(tmp_path):
    make_tree(tmp_path)
    (tmp_path / ".claude-memory" / "facts" / "fourth-slug.md").write_bytes(b"Gr\xf6\xdfe pr\xfcfen")
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.5", "--json"], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Traceback" not in r.stderr
    env = json.loads(r.stdout)
    assert "fourth-slug.md" in " ".join(env["skipped"])
    assert env["data"]["candidates"], "the readable facts are still scanned and reported"


def test_a_bom_fact_is_read(tmp_path):
    make_tree(tmp_path)
    (tmp_path / ".claude-memory" / "facts" / "bom-slug.md").write_bytes(
        b"\xef\xbb\xbf" + FAR.encode("utf-8"))
    loaded = {f.slug: f for f in DS.load_facts(tmp_path)}
    assert not loaded["bom-slug"].text.startswith("\ufeff")


# ---- --top, the control's place in the counts, and what gets scored ----------------------------

@pytest.mark.parametrize("n", ["0", "-1"])
def test_top_below_one_is_refused(tmp_path, n):
    make_tree(tmp_path)
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.5", "--top", n], tmp_path)
    assert r.returncode == 2
    assert "--top" in r.stderr


def test_top_one_keeps_the_strongest_candidate(tmp_path):
    make_tree(tmp_path)
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.5", "--top", "1", "--json"], tmp_path)
    assert r.returncode == 1
    assert len(json.loads(r.stdout)["data"]["candidates"]) == 1


def test_the_control_pair_is_not_counted_in_the_distribution_or_the_pair_count():
    result = DS.run(facts(("a", NEAR_A), ("b", FAR)), threshold=0.99)
    assert result.control.detected
    assert result.distribution == {} and result.compared_pairs == 0


def test_the_distribution_counts_only_real_pairs():
    result = DS.run(facts(("a", NEAR_A), ("b2", NEAR_B), ("c", FAR)), threshold=0.99)
    assert sum(result.distribution.values()) == result.compared_pairs == 1


FRAME = "---\nname: {s}\ndescription: {d}\nmetadata:\n  type: feedback\n---\n\n{b}\n"


def test_the_engine_frontmatter_keys_are_not_scored():
    a = FRAME.format(s="x", d="When alpha, bravo.", b="charlie delta echo foxtrot")
    b = FRAME.format(s="y", d="When golf, hotel.", b="india juliet kilo lima")
    assert DS.similarity(a, b) == 0.0


def test_the_description_value_is_still_scored():
    a = FRAME.format(s="x", d="When alpha bravo charlie.", b="delta")
    b = FRAME.format(s="y", d="When alpha bravo charlie.", b="echo")
    assert DS.similarity(a, b) > 0.5


def test_the_control_fires_when_every_fact_is_one_short_sentence():
    short = facts(("a", "Keep the cache warm."), ("b", "Rotate logs weekly."),
                  ("c", "Pin the floor version."))
    result = DS.run(short, threshold=0.5)
    assert result.control.detected, result.control
    assert result.control.score < 1.0


def test_text_output_shows_the_control_line_distribution_and_candidates(tmp_path):
    make_tree(tmp_path)
    r = run_cli(["--from", str(tmp_path), "--threshold", "0.5"], tmp_path)
    assert r.returncode == 1
    assert "FIRED" in r.stdout and "distribution" in r.stdout
    assert "1 CANDIDATE pair(s)" in r.stdout and "first-slug" in r.stdout


# ---- anchor, and a cp1252 console -------------------------------------------------------------

def test_a_decoy_store_lower_down_does_not_replace_the_real_one(tmp_path):
    make_tree(tmp_path)
    proj = tmp_path / "proj"
    (proj / ".claude-memory" / "facts").mkdir(parents=True)
    (proj / "CLAUDE.md").write_text("proj\n", encoding="utf-8")
    (proj / ".claude-memory" / "facts" / "decoy.md").write_text(FAR, encoding="utf-8")
    assert {f.slug for f in DS.load_facts(proj)} == {"first-slug", "second-slug"}


def test_a_cp1252_stdout_does_not_crash_on_a_non_ascii_level(tmp_path):
    root = tmp_path / "dd_日本"
    root.mkdir()
    make_tree(root)
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    r = subprocess.run([sys.executable, str(TOOL), "--from", str(root), "--threshold", "0.5"],
                       capture_output=True, check=False, env=env, cwd=str(tmp_path))
    # Exit 1 is ALSO what an uncaught exception gives, so the stream is the real assertion.
    assert b"Traceback" not in r.stderr, r.stderr.decode("utf-8", "replace")
    assert r.returncode == 1 and b"CANDIDATE" in r.stdout
