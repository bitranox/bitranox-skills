"""Tests for skill_decisions: the per-skill decision ledger."""
import copy
import json
import subprocess
import tracemalloc

import pytest

import skill_decisions as SD

LINE_SEPARATOR = chr(0x2028)  # built with chr(): a typed escape would land as the raw character


def _rule(**over):
    entry = {"v": 1, "date": "2026-11-05", "kind": "rule", "topic": "env-model",
             "decision": "bmk installs alone as a shared uv tool.",
             "why": "The per-project env was the inverse of what bmk 3.8.0 does.",
             "evidence": {"tier": "measured", "text": "bmk 3.8.0 release behaviour"},
             "reopen_if": "bmk changes its env model again.",
             "anchors": ["bmk alone, shared across projects"],
             "supersedes": [], "refs": [], "origin": "authored"}
    entry.update(over)
    entry["id"] = SD.entry_id(entry)
    return entry


# ---- matcher (the M0-measured rules) ----

def test_a_rewrap_and_a_repad_do_not_break_an_anchor():
    assert SD.anchor_occurs("Do **not** add `--with .` to the install line",
                            "Do **not** add\n   `--with .`   to the\ninstall line")


def test_a_blockquote_rewrap_does_not_break_an_anchor():
    assert SD.anchor_occurs("never restore the per-project env", "> never restore the\n> per-project env")
    assert SD.anchor_occurs("never restore the per-project env", ">never restore the\n>per-project env")


def test_an_anchor_spanning_two_list_items_survives_renumbering():
    anchor = "commit the plan. 2. push the plan"
    assert SD.anchor_occurs(anchor, "1. commit the plan.\n2. push the plan")
    assert SD.anchor_occurs(anchor, "3. commit the plan.\n4. push the plan")


def test_a_reworded_sentence_breaks_the_anchor():
    assert not SD.anchor_occurs("bmk installs as a persistent uv tool",
                                "bmk installs into a per-project .venv-bmk")


def test_unusual_line_separators_count_as_whitespace():
    assert SD.anchor_occurs("first half second half", "first half" + LINE_SEPARATOR + "second half")


def test_case_matters():
    assert not SD.anchor_occurs("Never push", "never push")


# ---- entry model ----

def test_a_complete_rule_entry_validates():
    assert SD.validate_entry(_rule()) == []


def test_the_id_is_the_date_plus_a_hash_of_the_whole_entry():
    a, b = _rule(), _rule(why="Another reason, same day.")
    assert a["id"].startswith("d-20261105-") and len(a["id"]) == len("d-20261105-") + 8
    assert a["id"] != b["id"]


def test_an_entry_edited_after_its_id_was_computed_is_refused():
    entry = _rule()
    entry["why"] = "rewritten in place"
    assert any(p.startswith("id:") for p in SD.validate_entry(entry))


@pytest.mark.parametrize("field", ["why", "reopen_if", "decision", "topic"])
def test_a_rule_without_a_mandatory_field_is_refused(field):
    entry = _rule(**{field: ""})
    assert any(p.startswith(field + ":") for p in SD.validate_entry(entry))


def test_a_void_entry_needs_why_and_a_target_but_no_reopen_if():
    void = _rule(kind="void", anchors=[], reopen_if="", supersedes=["d-20261101-0123abcd"])
    assert SD.validate_entry(void) == []
    no_target = _rule(kind="void", anchors=[], reopen_if="", supersedes=[])
    assert any(p.startswith("supersedes:") for p in SD.validate_entry(no_target))


def test_only_a_rule_carries_anchors_and_a_rule_needs_one():
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[])))
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(kind="rejected")))


@pytest.mark.parametrize("anchor", ["too short to anchor", "x" * 201])
def test_an_anchor_outside_20_to_200_characters_is_refused(anchor):
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[anchor])))


@pytest.mark.parametrize("control", [chr(0), chr(9), chr(0x7F)])
def test_an_anchor_holding_a_control_character_is_refused(control):
    anchor = "bmk alone," + control + " shared across projects"
    problems = SD.validate_entry(_rule(anchors=[anchor]))
    assert any(p.startswith("anchors: contains a control character") for p in problems)


def test_a_plain_anchor_raises_no_control_character_problem():
    assert not any("control" in p for p in SD.validate_entry(_rule()))


def test_the_length_is_measured_after_normalising():
    padded = "- - - - " + "a b c d e f g h i"    # long enough raw, too short once the markers go
    assert (len(padded), len(SD.normalise(padded))) == (25, 17)
    assert len(padded) >= SD.ANCHOR_MIN > len(SD.normalise(padded))
    assert any(p.startswith("anchors:") for p in SD.validate_entry(_rule(anchors=[padded])))


@pytest.mark.parametrize("field,value", [("kind", "note"), ("origin", "copied"),
                                         ("evidence", {"tier": "felt", "text": "x"}),
                                         ("evidence", {"tier": "argued", "text": ""}),
                                         ("topic", "Env Model")])
def test_a_value_outside_its_vocabulary_is_refused(field, value):
    assert any(p.startswith(field + ":") for p in SD.validate_entry(_rule(**{field: value})))


@pytest.mark.parametrize("date", ["2026-13-45", "2026-02-30"])
def test_a_date_that_is_not_on_the_calendar_is_refused(date):
    assert any(p.startswith("date:") for p in SD.validate_entry(_rule(date=date)))


def test_a_real_calendar_date_passes_the_date_check():
    assert not any(p.startswith("date:") for p in SD.validate_entry(_rule(date="2026-11-05")))


def test_an_unknown_field_is_refused_so_a_typo_cannot_hide_a_reason():
    entry = copy.deepcopy(_rule())
    entry["reopen-if"] = entry.pop("reopen_if")
    problems = SD.validate_entry(entry)
    assert any("reopen-if" in p for p in problems) and any(p.startswith("reopen_if:") for p in problems)


# ---- reading a ledger ----

def _lines(*entries):
    return [json.dumps(e) + "\n" for e in entries]


def _factory(*entries):
    data = _lines(*entries)
    return lambda: iter(data)


def _rejected(**over):
    return _rule(kind="rejected", anchors=[], topic="per-project-env",
                 decision="Install bmk per project.", **over)


def test_parse_reports_the_line_number_of_a_bad_line():
    with pytest.raises(SD.LedgerError) as err:
        list(SD.parse_entries(_lines(_rule()) + ["{not json\n"]))
    assert err.value.line_no == 2


def test_blank_lines_are_skipped():
    assert len(list(SD.parse_entries(["\n"] + _lines(_rule()) + ["  \n"]))) == 1


def test_a_line_that_is_not_utf8_is_a_ledger_error():
    with pytest.raises(SD.LedgerError) as err:
        list(SD.parse_entries([json.dumps(_rule()).encode("utf-8") + b"\n", b"\xff\xfe\n"]))
    assert err.value.line_no == 2


def test_a_ledger_file_that_is_not_utf8_is_a_ledger_error_naming_the_line(tmp_path):
    path = tmp_path / "decisions.jsonl"
    path.write_bytes(json.dumps(_rule()).encode("utf-8") + b"\n" + b"\xff\xfe\n")
    with pytest.raises(SD.LedgerError) as err:
        list(SD.parse_entries(SD.file_lines(path)))
    assert err.value.line_no == 2
    [finding] = SD.check_ledger(lambda: SD.file_lines(path), "bmk alone, shared across projects")
    assert finding.problem.startswith("line 2: ")


def test_a_raw_line_separator_inside_a_json_string_stays_one_ledger_line(tmp_path):
    entry = _rejected(why="first half" + LINE_SEPARATOR + "second half")
    path = tmp_path / "decisions.jsonl"
    path.write_bytes((json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8"))
    assert [e["id"] for e in SD.parse_entries(SD.file_lines(path))] == [entry["id"]]


@pytest.mark.parametrize("field", ["anchors", "supersedes"])
def test_a_list_field_holding_a_number_is_a_problem_not_a_crash(field):
    entry = _rule()
    entry[field] = 5
    entry["id"] = SD.entry_id(entry)
    assert any(p.startswith(field + ":") for p in SD.validate_entry(entry))
    with pytest.raises(SD.LedgerError):
        list(SD.parse_entries(_lines(entry)))


def test_a_superseded_entry_and_a_void_are_not_live():
    old = _rule()
    new = _rule(decision="bmk installs alone, reworded.", supersedes=[old["id"]])
    void = _rule(kind="void", anchors=[], reopen_if="", supersedes=[new["id"]],
                 why="written against the wrong skill")
    assert [e["id"] for e in SD.live_entries(_factory(old, new))] == [new["id"]]
    assert list(SD.live_entries(_factory(old, new, void))) == []


def test_check_passes_while_every_live_anchor_occurs():
    corpus = "Intro.\n\nbmk alone,\nshared across projects.\n"
    assert SD.check_ledger(_factory(_rule()), corpus) == []


def test_check_names_the_entry_and_its_reason_when_an_anchor_is_gone():
    entry = _rule()
    [finding] = SD.check_ledger(_factory(entry), "bmk installs per project now.\n")
    assert (finding.entry_id, finding.anchor) == (entry["id"], "bmk alone, shared across projects")
    assert entry["why"] in finding.render() and entry["reopen_if"] in finding.render()


def test_a_superseded_rule_s_anchor_may_go():
    old = _rule()
    new = _rule(decision="per-project env again", anchors=["each project gets its own bmk env"],
                supersedes=[old["id"]])
    assert SD.check_ledger(_factory(old, new), "Now each project gets its own bmk env.\n") == []


def test_check_reports_a_duplicate_id_and_an_unknown_supersede_target():
    entry = _rule()
    stray = _rule(decision="x", supersedes=["d-20990101-deadbeef"])
    problems = [f.problem for f in SD.check_ledger(_factory(entry, entry, stray), "bmk alone, shared across projects")]
    assert any("duplicate" in p for p in problems) and any("unknown" in p for p in problems)


def test_check_turns_a_parse_error_into_one_finding():
    # Line 2 is JSON but no object, so the line number can only come from the ledger reader: a
    # json syntax error would carry json's own "line 1 column N" and mask a dropped one.
    lines = _lines(_rule()) + ["[1]\n"]
    [finding] = SD.check_ledger(lambda: iter(lines), "bmk alone, shared across projects")
    assert finding.problem.startswith("line 2: ")


def test_the_corpus_is_the_markdown_outside_skillwriter_and_tests():
    files = {"SKILL.md": b"keep one", "references/x.md": b"keep two",
             ".skillwriter/checklist-1.md": b"drop one", "tests/fixture.md": b"drop two",
             "scripts/x.py": b"drop three"}
    text = SD.corpus_text(files)
    assert "keep one" in text and "keep two" in text and "drop" not in text


def test_an_anchor_cannot_span_two_files():
    files = {"SKILL.md": b"the end of one file", "references/x.md": b"start of another"}
    assert not SD.anchor_occurs("one file start of another", SD.corpus_text(files))


def _skill_repo(tmp_path):
    (tmp_path / "SKILL.md").write_text("tracked text\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("untracked text\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "SKILL.md"], cwd=tmp_path, check=True)


def test_corpus_from_dir_reads_tracked_markdown_only(tmp_path):
    _skill_repo(tmp_path)
    text = SD.corpus_from_dir(tmp_path)
    assert "tracked text" in text and "untracked text" not in text


def test_corpus_from_dir_ignores_an_inherited_git_dir(tmp_path, monkeypatch):
    # A hook launched by a push from a linked worktree inherits GIT_DIR; it must not redirect git.
    _skill_repo(tmp_path)
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "no-such-repo"))
    text = SD.corpus_from_dir(tmp_path)
    assert "tracked text" in text and "untracked text" not in text


def test_corpus_from_dir_walks_the_directory_when_git_cannot_run(tmp_path, monkeypatch):
    (tmp_path / "SKILL.md").write_text("first text\n", encoding="utf-8")
    (tmp_path / "references").mkdir()
    (tmp_path / "references" / "more.md").write_text("second text\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    text = SD.corpus_from_dir(tmp_path)
    assert "first text" in text and "second text" in text


def test_the_brief_lists_rejected_and_removed_in_full_and_counts_the_rest():
    entries = [_rejected(why="reason %d " % i + "x" * 300) for i in range(30)]
    brief = SD.render_brief(_factory(*entries), skill="devops-bmk", budget_chars=2000)
    assert "reason 0" in brief and len(brief) < 2600
    assert "more not shown" in brief and "skill_decisions.py show devops-bmk" in brief


def test_the_brief_stops_at_the_first_block_that_does_not_fit():
    a, b, c = _rejected(why="why A"), _rejected(why="why B " + "x" * 300), _rejected(why="why C")
    budget = 300
    # Precondition: A and C together fit, so only a strict oldest-first prefix leaves C out.
    assert len(SD._brief_block(a)) + len(SD._brief_block(c)) <= budget < len(SD._brief_block(b))
    brief = SD.render_brief(_factory(a, b, c), skill="devops-bmk", budget_chars=budget)
    assert "why A" in brief and "why B" not in brief and "why C" not in brief
    assert "2 more not shown" in brief


def test_a_first_block_over_the_budget_still_gives_a_brief():
    brief = SD.render_brief(_factory(_rejected()), skill="devops-bmk", budget_chars=10)
    assert brief.startswith("Decisions already taken for devops-bmk")
    assert "1 more not shown" in brief and "skill_decisions.py show devops-bmk" in brief


def test_the_brief_lists_a_removed_rule_beside_a_rejected_one():
    removed = _rule(kind="removed", anchors=[], decision="Dropped the --with . install line.")
    brief = SD.render_brief(_factory(removed, _rejected()), skill="devops-bmk")
    assert "[removed] Dropped the --with . install line." in brief and "[rejected]" in brief


def test_the_brief_is_empty_when_nothing_was_rejected_or_removed():
    assert SD.render_brief(_factory(_rule()), skill="devops-bmk") == ""


def test_file_lines_of_a_missing_ledger_is_empty(tmp_path):
    assert list(SD.file_lines(tmp_path / "absent.jsonl")) == []


def _peak(tmp_path, n):
    path = tmp_path / ("ledger-%d.jsonl" % n)
    with path.open("w", encoding="utf-8") as fh:
        for i in range(n):
            fh.write(json.dumps(_rejected(why="r%d " % i + "w" * 1000)) + "\n")
    tracemalloc.start()
    SD.check_ledger(lambda: SD.file_lines(path), "corpus")
    SD.render_brief(lambda: SD.file_lines(path), skill="s")
    peak = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return peak


def test_peak_memory_does_not_hold_the_entries(tmp_path):
    """19,000 more entries of 1 KB each would add about 19 MB if their text were held; the id
    sets the check keeps add about 100 to 150 bytes per entry (about 3 MB), so 8 MB separates the
    two outcomes with room on both sides."""
    small, large = _peak(tmp_path, 1000), _peak(tmp_path, 20000)
    assert large - small < 8_000_000
