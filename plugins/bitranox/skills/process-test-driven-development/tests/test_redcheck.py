"""Tests for redcheck.py: will this RED/baseline scenario be able to fail?

The corpus is injected, so these exercise the real core function against real-ish documents
rather than patching internals.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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


# --- assembling the corpus from a machine's always-loaded context ------------------------------
#
# Every fixture below is a scratch tree built under tmp_path and bounded with `top=`, so no test
# reads the cascade of the machine it runs on - which would make the result depend on whoever
# happens to be running it.


def _build_cascade(root: Path) -> Path:
    """A four-level scratch tree, and return the deepest directory to start the walk from.

    root/                        CLAUDE.md            (house rules, teaches nothing relevant)
    root/.claude-memory/facts/   one fact body
    root/workspace/              CLAUDE.md            (teaches the archive-purge lesson)
    root/workspace/project/      CLAUDE.local.md      (project notes, unrelated)
    root/workspace/project/sub/  <- the start directory, holds nothing itself
    """
    deep = root / "workspace" / "project" / "sub"
    deep.mkdir(parents=True)
    (root / "CLAUDE.md").write_text(
        "House rules: branch before committing, never force-push a published branch.\n",
        encoding="utf-8",
    )
    (root / "workspace" / "CLAUDE.md").write_text(SKILL_ALREADY_TEACHING[1], encoding="utf-8")
    (root / "workspace" / "project" / "CLAUDE.local.md").write_text(
        "Project notes: the desk lead signs off the nightly close.\n", encoding="utf-8"
    )
    facts = root / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    (facts / "pick-the-newest-by-mtime.md").write_text(
        "Sort candidate snapshots by modification time, never by filename order.\n",
        encoding="utf-8",
    )
    return deep


def test_cascade_walks_up_from_the_start_directory(tmp_path: Path) -> None:
    """Every CLAUDE.md and CLAUDE.local.md on the chain ABOVE the start dir must be assembled.

    The start directory holds no config of its own, so a walk that never leaves it collects
    nothing - which is what makes this test able to fail.
    """
    root = tmp_path.resolve()
    deep = _build_cascade(root)

    labels = [label for label, _ in R.load_cascade_corpus([deep], top=root)]

    assert str(root / "workspace" / "CLAUDE.md") in labels
    assert str(root / "workspace" / "project" / "CLAUDE.local.md") in labels
    assert str(root / "CLAUDE.md") in labels


def test_cascade_includes_the_memory_fact_bodies(tmp_path: Path) -> None:
    """The pointer index is always-loaded text; the bodies it points at are the real lesson."""
    root = tmp_path.resolve()
    deep = _build_cascade(root)

    corpus = dict(R.load_cascade_corpus([deep], top=root))

    fact = str(root / ".claude-memory" / "facts" / "pick-the-newest-by-mtime.md")
    assert fact in corpus, f"memory fact body missing from the corpus: {sorted(corpus)}"
    assert "modification time" in corpus[fact]


def test_cascade_includes_a_gitignored_claude_md(tmp_path: Path) -> None:
    """A gitignored CLAUDE.md is still reachable context, so it must still be in the corpus.

    Project CLAUDE.md and memory stores are routinely gitignored. Any gitignore-aware search
    drops them silently, which reports a smaller, falsely clean corpus. The `git check-ignore`
    call is the CONTROL: it proves the fixture file really is ignored, so this test cannot pass
    vacuously against a file git would have handed over anyway.
    """
    git = shutil.which("git")
    if git is None:
        pytest.skip("git not installed, so the ignored-ness of the fixture cannot be proven")

    root = tmp_path.resolve()
    deep = _build_cascade(root)
    subprocess.run([git, "init", "-q", str(root)], check=True, timeout=60)
    (root / ".gitignore").write_text("CLAUDE.local.md\n.claude-memory/\n", encoding="utf-8")
    ignored = root / "workspace" / "project" / "CLAUDE.local.md"

    control = subprocess.run(
        [git, "-C", str(root), "check-ignore", "-q", str(ignored)], timeout=60
    )
    assert control.returncode == 0, "fixture is not actually gitignored - the test proves nothing"

    labels = [label for label, _ in R.load_cascade_corpus([deep], top=root)]
    assert str(ignored) in labels


def test_a_non_utf8_document_is_skipped_with_a_warning_not_a_crash(tmp_path: Path) -> None:
    """One stray latin-1 byte must cost that one file, never the whole run."""
    root = tmp_path.resolve()
    deep = _build_cascade(root)
    broken = root / "workspace" / "project" / "CLAUDE.md"
    broken.write_bytes(b"# Notes\nCaf\xe9 rota for the night desk\n")

    warnings: list[str] = []
    corpus = R.load_cascade_corpus([deep], top=root, warn=warnings.append)

    labels = [label for label, _ in corpus]
    assert str(broken) not in labels, "an undecodable file must not enter the corpus"
    assert any(str(broken) in w for w in warnings), f"skip was silent: {warnings}"
    assert str(root / "workspace" / "CLAUDE.md") in labels, "one bad file killed the whole walk"


def test_zero_document_corpus_is_unchecked_never_clean() -> None:
    """A corpus that assembled nothing makes every scenario look clean - say so, loudly."""
    result = R.audit(CLEAN_SCENARIO, corpus=[], require_corpus=True)

    assert result.corpus_documents == 0
    assert result.corpus_empty is True
    assert "unchecked" in result.verdict
    assert result.verdict != "clean"


def test_document_count_is_reported_even_on_a_clean_run() -> None:
    result = R.audit(CLEAN_SCENARIO, corpus=[SKILL_ALREADY_TEACHING, UNRELATED_DOC])
    assert result.corpus_documents == 2
    assert result.as_dict()["corpus_documents"] == 2


# --- the rarity cutoff has to fit the corpus the cascade mode actually assembles ---------------


def _corpus_shaped_like_a_real_cascade() -> list[tuple[str, str]]:
    """A corpus with the document-frequency structure a real assembled cascade has.

    Measured on a live 608-document cascade (8 CLAUDE.md/CLAUDE.local.md files plus 600 memory
    fact bodies): the terms that CARRY a lesson sit between 1.3% and 4.8% document frequency,
    because a store of one engineer's lessons reuses its own domain vocabulary everywhere. True
    boilerplate sits an order of magnitude higher - 36% and 54%. A cutoff placed below the
    signal band filters out the evidence itself, so every scenario comes back clean and the
    check is decorative.

    Reproduced here: EVERY term the scenario shares with the teaching document also appears in
    8 further documents (~4%) - which is what the live measurement showed, and what a fixture
    that leaves some terms at 1-document frequency fails to reproduce, because those survive any
    cutoff and the scenario hits regardless. The boilerplate sits in all 200 (~96%), and exactly
    one document actually teaches the lesson.
    """
    boilerplate = (
        "This document covers the failing path, the window in which it applies, who should "
        "lead the change, and the region it affects every night."
    )
    # The lesson's whole shared vocabulary, used the way neighbouring docs in a real store use
    # it - mentioned in passing, teaching none of it.
    domain_chatter = (
        "Scheduling note: the archive mirror runs after the syncd purge window. Whoever is on "
        "call confirms the live tree and the common tree are both listed before the run, and "
        "logs which host emptied its queue first."
    )
    corpus = [(f"skills/doc-{i}/SKILL.md", boilerplate) for i in range(192)]
    corpus += [(f"skills/chatter-{i}/SKILL.md", boilerplate + domain_chatter) for i in range(8)]
    corpus.append(SKILL_ALREADY_TEACHING)
    return corpus


def test_the_cascade_shaped_fixture_really_has_no_rare_terms_left() -> None:
    """Guard the fixture above: if any shared term stays at 1-document frequency the fixture
    passes at ANY cutoff and the two tests below prove nothing."""
    corpus = _corpus_shaped_like_a_real_cascade()
    documents = [(label, R.distinctive_terms(text)) for label, text in corpus]
    frequency: dict[str, int] = {}
    for _, terms in documents:
        for term in terms:
            frequency[term] = frequency.get(term, 0) + 1

    shared = R.distinctive_terms(CONTAMINATED_SCENARIO) & R.distinctive_terms(
        SKILL_ALREADY_TEACHING[1]
    )
    assert shared, "fixture shares nothing with the scenario"
    stragglers = {t: frequency[t] for t in shared if frequency[t] <= max(1, int(len(corpus) * 0.01))}
    assert not stragglers, f"these terms survive the narrow cutoff, so the fixture is vacuous: {stragglers}"


def test_a_lesson_is_still_found_when_its_vocabulary_is_common_in_the_corpus() -> None:
    """The cutoff must sit ABOVE the band a lesson's own vocabulary occupies, or nothing hits.

    This is the case a real cascade puts the tool in every time, and the case a cutoff tuned
    against a topically diverse corpus silently fails.
    """
    result = R.audit(CONTAMINATED_SCENARIO, corpus=_corpus_shaped_like_a_real_cascade())

    labels = [hit.label for hit in result.inherited]
    assert SKILL_ALREADY_TEACHING[0] in labels, (
        f"the rarity cutoff filtered out the lesson's own terms: {result.inherited}"
    )


def test_boilerplate_still_does_not_flag_at_the_wider_cutoff() -> None:
    """The control for the test above: widening the cutoff must not admit the boilerplate.

    Without this, "make the lesson hit" is satisfied by disabling the rarity gate entirely.
    """
    scenario = """
        Shift log 04:10. The ledger reconciliation for the eastern region has been failing
        its nightly close since Tuesday. The desk lead signed off. The window closes at 05:00.
    """
    result = R.audit(scenario, corpus=_corpus_shaped_like_a_real_cascade())
    assert not result.inherited, f"false positive on boilerplate: {result.inherited}"


def test_rarity_cutoff_is_tunable_per_corpus() -> None:
    """The right cutoff depends on corpus shape, so it must not need a source edit to change."""
    corpus = _corpus_shaped_like_a_real_cascade()
    assert R.audit(CONTAMINATED_SCENARIO, corpus=corpus, rarity_max_fraction=0.01).inherited == []
    assert R.audit(CONTAMINATED_SCENARIO, corpus=corpus, rarity_max_fraction=0.05).inherited


# --- how strong is the verdict, and does the tool say so ---------------------------------------


def test_a_clean_result_declares_itself_weak_evidence() -> None:
    """A clean run must not read as a sealed fixture: term overlap cannot see a paraphrase."""
    result = R.audit(CLEAN_SCENARIO, corpus=[SKILL_ALREADY_TEACHING, UNRELATED_DOC])
    payload = result.as_dict()

    assert payload["inherited_evidence"]["strength"] == "weak"
    note = payload["inherited_evidence"]["note"].lower()
    assert "paraphrase" in note
    assert "not" in note


def test_an_inherited_result_declares_itself_strong_evidence() -> None:
    result = R.audit(CONTAMINATED_SCENARIO, corpus=[SKILL_ALREADY_TEACHING, UNRELATED_DOC])
    assert result.as_dict()["inherited_evidence"]["strength"] == "strong"


# --- the cascade mode end to end through the CLI -----------------------------------------------


def _cascade_run(tmp_path: Path, scenario: str, start: Path, top: Path) -> dict:
    s = tmp_path / "scenario.txt"
    s.write_text(scenario, encoding="utf-8")
    proc = _run(
        [
            "--scenario",
            str(s),
            "--corpus-cascade",
            str(start),
            "--corpus-cascade-top",
            str(top),
            "--json",
        ]
    )
    payload = json.loads(proc.stdout)
    payload["_returncode"] = proc.returncode
    payload["_stderr"] = proc.stderr
    return payload


def test_cli_cascade_flags_a_scenario_the_fixture_cascade_already_teaches(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    deep = _build_cascade(root)

    payload = _cascade_run(tmp_path, CONTAMINATED_SCENARIO, deep, root)

    assert payload["_returncode"] == 1, payload
    assert payload["data"]["verdict"].startswith("inherited")
    labels = [hit["label"] for hit in payload["data"]["inherited"]]
    assert str(root / "workspace" / "CLAUDE.md") in labels, labels
    assert payload["data"]["corpus_documents"] >= 4
    assert payload["data"]["inherited_evidence"]["strength"] == "strong"


def test_cli_cascade_leaves_an_unrelated_scenario_uninherited(tmp_path: Path) -> None:
    """The negative arm: a detector that has only ever said one thing is not a detector."""
    root = tmp_path.resolve()
    deep = _build_cascade(root)

    payload = _cascade_run(tmp_path, CLEAN_SCENARIO, deep, root)

    assert payload["_returncode"] == 0, payload
    assert payload["data"]["verdict"] == "clean"
    assert payload["data"]["inherited"] == []
    assert payload["data"]["inherited_evidence"]["strength"] == "weak"


def test_cli_exits_unchecked_when_the_cascade_assembles_nothing(tmp_path: Path) -> None:
    """A mistyped start directory must be a distinct, loud outcome - not a quiet pass."""
    s = tmp_path / "scenario.txt"
    s.write_text(CLEAN_SCENARIO, encoding="utf-8")
    proc = _run(["--scenario", str(s), "--corpus-cascade", str(tmp_path / "nope"), "--json"])

    assert proc.returncode == 3, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["data"]["corpus_documents"] == 0
    assert payload["data"]["corpus_empty"] is True
    assert "unchecked" in payload["data"]["verdict"]
    assert any("nope" in w for w in payload["skipped"])


def test_cascade_help_names_the_files_it_reads() -> None:
    """Discoverability: a reader must learn what the mode reads without opening the source.

    Matched against the help with ALL whitespace removed, because argparse wraps to the caller's
    terminal width and breaks after a hyphen - so `.claude-memory/facts/` splits across two lines
    on a narrow terminal and passes or fails by window size otherwise. Line wrapping is
    presentation; the assertion is about which names the text contains.
    """
    proc = _run(["--help"])
    assert proc.returncode == 0
    squashed = "".join(proc.stdout.split())
    for expected in ("--corpus-cascade", "CLAUDE.local.md", ".claude-memory/facts/"):
        assert "".join(expected.split()) in squashed, f"--help never names {expected}"
