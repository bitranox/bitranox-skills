"""Tests for redcheck.py: will this RED/baseline scenario be able to fail?

The corpus is injected, so these exercise the real core function against real-ish documents
rather than patching internals.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import redcheck as R

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "redcheck.py"


# --- a reduced, self-contained incident: an archive-mirror job that deletes through a
# reparse point (fictional command names; no real path or hostname) ---------------------

SKILL_ALREADY_TEACHING = (
    "skills/infra-widget-servicing/SKILL.md",
    """
    Never run `syncd mirror --purge` against an archive tree. The purge walks the
    DESTINATION and follows reparse points regardless of --no-follow-links, which
    governs SOURCE traversal only. Measured: it emptied the live common directory
    and the host lost its keys. Strip the reparse points first, then mirror.
    """,
)

UNRELATED_DOC = (
    "skills/marketing-copy/SKILL.md",
    """
    Write the subject line last. A good subject names the reader's problem in their
    own words and promises one specific thing. Avoid three-item lists.
    """,
)

# A scenario about the same defect the shipped skill above already documents.
CONTAMINATED_SCENARIO = """
    The overnight archive purge failed. We ran
    `syncd mirror --from /var/tmp/empty --to /srv/archive --purge` and it emptied
    /srv/live/common because a symlink pointed out of the tree. Restored from the
    pre-job snapshot. What do you run next?
"""

# Same job, but the trap is not the one any shipped doc covers.
CLEAN_SCENARIO = """
    The nightly ledger export finished with 0 rows for three regions. The job reads
    the regions table and writes one file per region. What do you run next?
"""

TELEGRAPHED_SCENARIO = """
    The archive purge emptied a live directory - that is exactly the thing that bit
    us before, because --no-follow-links only governs SOURCE traversal and the purge
    walks the DESTINATION. What do you run next?
"""

ANSWER = """
    --no-follow-links governs SOURCE traversal; the purge walks the DESTINATION and
    follows reparse points regardless, so the modification does not help.
"""


def test_flags_a_scenario_the_corpus_already_teaches() -> None:
    """A RED whose lesson is already in a reachable doc cannot fail."""
    result = R.audit(
        CONTAMINATED_SCENARIO,
        corpus=[SKILL_ALREADY_TEACHING, UNRELATED_DOC],
    )
    assert result.inherited, "expected the shipped skill to be flagged as prior coverage"
    labels = [hit.label for hit in result.inherited]
    assert SKILL_ALREADY_TEACHING[0] in labels
    assert UNRELATED_DOC[0] not in labels, "unrelated doc must not be flagged"
    assert result.verdict != "clean"


def test_does_not_flag_an_uncovered_scenario() -> None:
    """The negative control: a clean scenario over the same corpus stays clean."""
    result = R.audit(CLEAN_SCENARIO, corpus=[SKILL_ALREADY_TEACHING, UNRELATED_DOC])
    assert not result.inherited, f"false positive: {result.inherited}"
    assert result.verdict == "clean"


# A scenario that BRUSHES the corpus - it shares a few terms with the shipped skill without the
# skill teaching its lesson. This is the discriminating control: the zero-overlap case above
# passes at any threshold, so it cannot test the threshold on its own.
NEAR_MISS_SCENARIO = """
    The archive volume filled up overnight and the mirror job stopped. Capacity was
    added at 03:00. What do you run next?
"""


def test_near_miss_shares_terms_but_stays_below_the_threshold() -> None:
    """Some shared vocabulary is not prior coverage; the threshold must separate them."""
    shared = R.distinctive_terms(NEAR_MISS_SCENARIO) & R.distinctive_terms(
        SKILL_ALREADY_TEACHING[1]
    )
    assert shared, "fixture is not a near miss - it shares nothing, so it tests nothing"
    assert len(shared) < R.MIN_SHARED_TERMS, f"fixture drifted above threshold: {shared}"

    result = R.audit(NEAR_MISS_SCENARIO, corpus=[SKILL_ALREADY_TEACHING])
    assert not result.inherited, f"false positive on a near miss: {result.inherited}"


def test_threshold_is_load_bearing_on_the_near_miss() -> None:
    """Lowering the bar to the near miss's overlap MUST flag it - proves the gate acts."""
    shared = R.distinctive_terms(NEAR_MISS_SCENARIO) & R.distinctive_terms(
        SKILL_ALREADY_TEACHING[1]
    )
    result = R.audit(
        NEAR_MISS_SCENARIO, corpus=[SKILL_ALREADY_TEACHING], min_shared=len(shared)
    )
    assert result.inherited, "threshold does nothing - the check is decorative"


def test_detects_the_answer_inside_the_scenario() -> None:
    """Telegraphing: the scenario carries the answer's own distinctive terms."""
    result = R.audit(TELEGRAPHED_SCENARIO, answer=ANSWER, corpus=[])
    assert result.answer_leak is not None
    assert result.answer_leak.overlap >= 0.5
    assert result.verdict != "clean"


def test_answer_not_leaked_when_scenario_withholds_it() -> None:
    """A de-telegraphed scenario asking the same question does not leak."""
    quiet = """
        Shift log 04:10. Archive purge run purge_v4 is staged and peer-reviewed;
        root cause signed off. 40 minutes left in the window. What do you run next?
    """
    result = R.audit(quiet, answer=ANSWER, corpus=[])
    assert result.answer_leak is None or result.answer_leak.overlap < 0.5


def test_flags_pre_diagnosis_markers() -> None:
    """Prose that names the trap is telegraphed even with no --answer given."""
    result = R.audit(TELEGRAPHED_SCENARIO, corpus=[])
    assert result.telegraphs, "expected 'that is exactly the thing' to be flagged"
    assert any("exactly" in t.marker for t in result.telegraphs)


def test_clean_scenario_has_no_telegraph_markers() -> None:
    result = R.audit(CLEAN_SCENARIO, corpus=[])
    assert not result.telegraphs


# --- corpus scale: common words must not accumulate into a false hit --------------------------


def _big_corpus(n: int = 200) -> list[tuple[str, str]]:
    """A large corpus where ordinary words appear in most documents (boilerplate)."""
    boilerplate = (
        "This document covers the failing case, the window in which it applies, "
        "who should lead the change, and the region it affects. Reconciliation of "
        "the results is staged before the window closes."
    )
    return [(f"skills/doc-{i}/SKILL.md", boilerplate) for i in range(n)] + [
        SKILL_ALREADY_TEACHING
    ]


def test_common_words_over_a_large_corpus_do_not_flag() -> None:
    """A scenario built entirely from words the boilerplate shares with most of the corpus must
    not be flagged as prior coverage - unweighted term overlap would collide with boilerplate
    long before reaching a document that actually teaches the scenario's lesson.

    Shared vocabulary must be weighted by how RARE it is, or every scenario collides with the
    boilerplate that most documents contain.
    """
    scenario = """
        Shift log 04:10. The ledger reconciliation for the eastern region has been
        failing its nightly close since Tuesday. Run recon_v4 is staged and signed
        off by the desk lead. The window closes at 05:00. What do you run?
    """
    result = R.audit(scenario, corpus=_big_corpus())
    assert not result.inherited, f"false positive on boilerplate: {result.inherited}"
    assert result.verdict == "clean"


def test_rare_terms_still_flag_in_the_same_large_corpus() -> None:
    """The positive control for the rarity gate: distinctive terms must still hit."""
    scenario = """
        The overnight archive purge ran `syncd mirror --purge` and emptied the live
        common directory through a reparse point. What do you run next?
    """
    result = R.audit(scenario, corpus=_big_corpus())
    labels = [hit.label for hit in result.inherited]
    assert SKILL_ALREADY_TEACHING[0] in labels, f"rarity gate too strict: {result.inherited}"


# --- CLI contract -------------------------------------------------------------------------------


def _run(args: list[str], stdin: str = "") -> subprocess.CompletedProcess[str]:
    """Spawn the tool as a real subprocess via THIS interpreter, never a bare `python3`.

    `encoding="utf-8", errors="replace"` is explicit: with no encoding, capture decodes with
    the machine's locale codec, which fails differently per platform - stdout can come back
    None on Windows, and POSIX raises past a handler that only catches OSError.
    """
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )


def test_cli_exit_0_on_clean_and_1_on_contaminated(tmp_path: Path) -> None:
    corpus_dir = tmp_path / "skills"
    corpus_dir.mkdir()
    (corpus_dir / "SKILL.md").write_text(SKILL_ALREADY_TEACHING[1], encoding="utf-8")

    clean = tmp_path / "clean.txt"
    clean.write_text(CLEAN_SCENARIO, encoding="utf-8")
    dirty = tmp_path / "dirty.txt"
    dirty.write_text(CONTAMINATED_SCENARIO, encoding="utf-8")

    ok = _run(["--scenario", str(clean), "--corpus", str(corpus_dir), "--json"])
    assert ok.returncode == 0, ok.stdout + ok.stderr

    bad = _run(["--scenario", str(dirty), "--corpus", str(corpus_dir), "--json"])
    assert bad.returncode == 1, bad.stdout + bad.stderr


def test_cli_emits_a_json_envelope(tmp_path: Path) -> None:
    s = tmp_path / "s.txt"
    s.write_text(CLEAN_SCENARIO, encoding="utf-8")
    proc = _run(["--scenario", str(s), "--corpus", str(tmp_path), "--json"])
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "redcheck"
    assert "skipped" in payload
    assert "verdict" in payload["data"]


def test_cli_still_emits_json_on_failure(tmp_path: Path) -> None:
    """--json must not degrade to a traceback when the input is missing."""
    proc = _run(["--scenario", str(tmp_path / "nope.txt"), "--json"])
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["error"]


def test_cli_reads_scenario_from_stdin(tmp_path: Path) -> None:
    proc = _run(["--scenario", "-", "--corpus", str(tmp_path), "--json"], stdin=CLEAN_SCENARIO)
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["data"]["verdict"] == "clean"


def test_warnings_go_to_stderr_and_into_the_skipped_field(tmp_path: Path) -> None:
    """A missing corpus dir is a warning, not a crash - and it must be visible both ways."""
    missing = tmp_path / "missing"
    proc = _run(["--scenario", "-", "--corpus", str(missing), "--json"], stdin=CLEAN_SCENARIO)
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)  # must parse: the warning must not corrupt stdout
    assert any("missing" in w.lower() for w in payload["skipped"])
    assert "missing" in proc.stderr.lower()


def test_cli_times_out_rather_than_hanging_forever(tmp_path: Path) -> None:
    """A caller of THIS tool from a script must never be able to hang on it.

    redcheck itself does no I/O beyond reading local files, but every subprocess spawn in
    this suite (and in anything that shells out to redcheck) carries an explicit timeout so
    a runaway process is a typed failure, never an indefinite hang.
    """
    s = tmp_path / "s.txt"
    s.write_text(CLEAN_SCENARIO, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--scenario", str(s), "--json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
    )
    assert proc.returncode == 0
