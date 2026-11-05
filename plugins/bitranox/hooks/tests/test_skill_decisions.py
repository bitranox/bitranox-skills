"""Tests for skill_decisions: the per-skill decision ledger."""
import copy
import json
import os
import subprocess
import sys
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


# ---- writing entries ----

def _clean_env():
    # A push from a linked worktree exports GIT_DIR; it must not point these git calls elsewhere.
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _skill(tmp_path, text="Intro.\n\nbmk alone, shared across projects.\n", name="devops-bmk"):
    repo = tmp_path / "repo"
    skill = repo / "plugins" / "bitranox" / "skills" / name
    (skill / ".skillwriter").mkdir(parents=True)
    (skill / "SKILL.md").write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True, env=_clean_env())
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, env=_clean_env())
    return repo, skill


def _draft(**over):
    entry = {k: v for k, v in _rule().items() if k not in ("id", "date", "v")}
    entry.update(over)
    return entry


def test_append_assigns_id_and_date_and_writes_one_line(tmp_path):
    _repo, skill = _skill(tmp_path)
    [new_id] = SD.append_entries(skill, [_draft()], today="2026-11-06")
    [stored] = list(SD.parse_entries(SD.file_lines(SD.ledger_path(skill))))
    assert stored["id"] == new_id and new_id.startswith("d-20261106-")
    assert stored["v"] == 1 and stored["date"] == "2026-11-06"


def test_a_draft_that_carries_its_own_date_keeps_it(tmp_path):
    _repo, skill = _skill(tmp_path)
    [new_id] = SD.append_entries(skill, [_draft(date="2026-10-01")], today="2026-11-06")
    assert new_id.startswith("d-20261001-")


def test_an_anchor_that_occurs_twice_is_refused(tmp_path):
    _repo, skill = _skill(tmp_path, "bmk alone, shared across projects.\n" * 2)
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft()], today="2026-11-06")
    assert any("exactly once" in p for p in err.value.problems)
    assert not SD.ledger_path(skill).exists()


def test_an_anchor_that_occurs_twice_overlapping_is_refused(tmp_path):
    # str.count finds ONE non-overlapping hit here, while the anchor starts at two places.
    phrase = "repeat this phrase repeat this phrase"
    _repo, skill = _skill(tmp_path, "repeat this phrase repeat this phrase repeat this phrase\n")
    assert SD.normalise(SD.corpus_from_dir(skill)).count(phrase) == 1
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(anchors=[phrase])], today="2026-11-06")
    assert any("found 2" in p for p in err.value.problems)


def test_an_anchor_absent_from_the_text_is_refused(tmp_path):
    _repo, skill = _skill(tmp_path, "something else entirely\n")
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft()], today="2026-11-06")
    assert any("exactly once" in p and "found 0" in p for p in err.value.problems)


def test_a_batch_is_all_or_nothing(tmp_path):
    _repo, skill = _skill(tmp_path)
    with pytest.raises(SD.EntryRefused):
        SD.append_entries(skill, [_draft(), _draft(why="")], today="2026-11-06")
    assert list(SD.file_lines(SD.ledger_path(skill))) == []


def test_a_typographic_tell_is_refused(tmp_path):
    _repo, skill = _skill(tmp_path)
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(why="because" + chr(0x2014) + "it broke")], today="2026-11-06")
    assert any(p.startswith("entry 1: why:") for p in err.value.problems)


def test_a_typographic_tell_in_the_evidence_text_is_refused(tmp_path):
    _repo, skill = _skill(tmp_path)
    evidence = {"tier": "measured", "text": "measured" + chr(0x2019) + "s output"}
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(evidence=evidence)], today="2026-11-06")
    assert any(p.startswith("entry 1: evidence:") for p in err.value.problems)


def test_a_problem_names_the_entry_by_its_place_in_the_batch(tmp_path):
    _repo, skill = _skill(tmp_path, "bmk alone, shared across projects. Then run make test first.\n")
    second = _draft(decision="gate first", anchors=["Then run make test first."], why="")
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(), second], today="2026-11-06")
    assert err.value.problems == ["entry 2: why: empty"]


def test_an_identical_entry_is_refused_in_the_batch_and_against_the_ledger(tmp_path):
    _repo, skill = _skill(tmp_path)
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(), _draft()], today="2026-11-06")
    assert any(p.startswith("entry 2: id:") for p in err.value.problems)
    SD.append_entries(skill, [_draft()], today="2026-11-06")
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft()], today="2026-11-06")
    assert any(p.startswith("entry 1: id:") for p in err.value.problems)


def test_supersedes_must_name_a_recorded_id(tmp_path):
    _repo, skill = _skill(tmp_path, "bmk alone, shared across projects. Then run make test first.\n")
    [first] = SD.append_entries(skill, [_draft()], today="2026-11-06")
    stray = _draft(decision="gate first", anchors=["Then run make test first."],
                   supersedes=["d-20990101-deadbeef"])
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [stray], today="2026-11-06")
    assert any(p.startswith("entry 1: supersedes:") for p in err.value.problems)
    stray["supersedes"] = [first]
    assert len(SD.append_entries(skill, [stray], today="2026-11-06")) == 1


@pytest.mark.parametrize("over", [{"anchors": "bmk alone, shared across projects"},
                                  {"supersedes": 5}])
def test_a_malformed_list_field_is_a_problem_not_a_crash(tmp_path, over):
    _repo, skill = _skill(tmp_path)
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(**over)], today="2026-11-06")
    field = next(iter(over))
    assert any(p.startswith("entry 1: %s:" % field) for p in err.value.problems)


def test_a_draft_that_is_not_an_object_is_a_problem_not_a_crash(tmp_path):
    _repo, skill = _skill(tmp_path)
    with pytest.raises(SD.EntryRefused) as err:
        SD.append_entries(skill, [_draft(), "just text"], today="2026-11-06")
    assert err.value.problems == ["entry 2: not a JSON object"]


def test_an_append_completes_a_ledger_whose_last_line_has_no_newline(tmp_path):
    _repo, skill = _skill(tmp_path, "bmk alone, shared across projects. Then run make test first.\n")
    SD.append_entries(skill, [_draft()], today="2026-11-06")
    path = SD.ledger_path(skill)
    path.write_bytes(path.read_bytes().rstrip(b"\n"))
    SD.append_entries(skill, [_draft(decision="gate first", anchors=["Then run make test first."])],
                      today="2026-11-06")
    assert len(list(SD.parse_entries(SD.file_lines(path)))) == 2


def test_the_ledger_is_written_with_lf_line_endings(tmp_path):
    _repo, skill = _skill(tmp_path)
    SD.append_entries(skill, [_draft()], today="2026-11-06")
    data = SD.ledger_path(skill).read_bytes()
    assert data.endswith(b"\n") and b"\r" not in data


def test_append_reads_the_ledger_without_holding_its_entries(tmp_path):
    def peak(n):
        _repo, skill = _skill(tmp_path / str(n), "bmk alone, shared across projects. Then run make test first.\n")
        with SD.ledger_path(skill).open("w", encoding="utf-8") as fh:
            for i in range(n):
                fh.write(json.dumps(_rejected(why="r%d " % i + "w" * 1000)) + "\n")
        tracemalloc.start()
        SD.append_entries(skill, [_draft()], today="2026-11-06")
        result = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        return result
    # The same margin as test_peak_memory_does_not_hold_the_entries: 19 MB of entry text against
    # about 3 MB of ids.
    assert peak(20000) - peak(1000) < 8_000_000


# ---- the CLI ----

def _cli(capsys, *argv):
    rc = SD.main(list(argv))
    out = capsys.readouterr()
    return rc, out.out, out.err


def _entries_file(tmp_path, *drafts):
    src = tmp_path / "entries.json"
    src.write_text(json.dumps(list(drafts)), encoding="utf-8")
    return src


def test_show_all_includes_superseded_entries(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path, "bmk alone, shared across projects. Then run make test first.\n")
    [first] = SD.append_entries(skill, [_draft()], today="2026-11-06")
    SD.append_entries(skill, [_draft(decision="gate first", anchors=["Then run make test first."],
                                     supersedes=[first])], today="2026-11-06")
    monkeypatch.chdir(repo)
    _rc, live, _ = _cli(capsys, "show", "devops-bmk", "--json")
    _rc, every, _ = _cli(capsys, "show", "devops-bmk", "--all", "--json")
    assert len(json.loads(live)["data"]["entries"]) == 1
    assert len(json.loads(every)["data"]["entries"]) == 2


def test_show_filters_by_kind_topic_and_id(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    [rule_id, rejected_id] = SD.append_entries(
        skill, [_draft(), _draft(kind="rejected", anchors=[], topic="per-project-env",
                                 decision="Install bmk per project.")], today="2026-11-06")
    monkeypatch.chdir(repo)

    def ids(*flags):
        _rc, out, _ = _cli(capsys, "show", "devops-bmk", "--json", *flags)
        return [e["id"] for e in json.loads(out)["data"]["entries"]]
    assert ids() == [rule_id, rejected_id]
    assert ids("--kind", "rejected,removed") == [rejected_id]
    assert ids("--topic", "env-model") == [rule_id]
    assert ids("--id", rejected_id) == [rejected_id]


def test_show_full_prints_every_field(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    SD.append_entries(skill, [_draft()], today="2026-11-06")
    monkeypatch.chdir(repo)
    _rc, short, _ = _cli(capsys, "show", "devops-bmk", "--json")
    _rc, full, _ = _cli(capsys, "show", "devops-bmk", "--full", "--json")
    assert "why" not in json.loads(short)["data"]["entries"][0]
    assert json.loads(full)["data"]["entries"][0]["why"] == _rule()["why"]


def test_show_streams_a_large_ledger_without_holding_its_entries(tmp_path, monkeypatch):
    def peak(n):
        skill = tmp_path / str(n) / "devops-bmk"
        SD.ledger_path(skill).parent.mkdir(parents=True)
        with SD.ledger_path(skill).open("w", encoding="utf-8") as fh:
            for i in range(n):
                fh.write(json.dumps(_rejected(why="r%d " % i + "w" * 1000)) + "\n")
        with open(os.devnull, "w", encoding="utf-8") as sink:
            monkeypatch.setattr(sys, "stdout", sink)
            tracemalloc.start()
            rc = SD.main(["show", "devops-bmk", "--skill-dir", str(skill), "--full", "--json"])
            result = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            monkeypatch.undo()
        assert rc == 0
        return result
    assert peak(20000) - peak(1000) < 8_000_000


def test_cli_add_show_check_round_trip(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    src = _entries_file(tmp_path, dict(_draft(), skill="devops-bmk"))
    monkeypatch.chdir(repo)
    rc, out, _ = _cli(capsys, "add", "--from-file", str(src), "--json")
    assert rc == 0 and json.loads(out)["ok"] is True
    rc, out, _ = _cli(capsys, "show", "devops-bmk")
    assert rc == 0 and "env-model" in out
    rc, _, _ = _cli(capsys, "check", "devops-bmk")
    assert rc == 0
    (skill / "SKILL.md").write_text("bmk installs per project now.\n", encoding="utf-8")
    rc, out, _ = _cli(capsys, "check", "devops-bmk", "--json")
    assert rc == 1 and json.loads(out)["data"]["findings"]


def test_the_json_envelope_has_exactly_the_four_keys(tmp_path, capsys, monkeypatch):
    repo, _skill_dir = _skill(tmp_path)
    monkeypatch.chdir(repo)
    for argv in (["check", "--json"], ["--json", "check"], ["show", "devops-bmk", "--json"]):
        rc, out, _ = _cli(capsys, *argv)
        envelope = json.loads(out)
        assert rc == 0 and sorted(envelope) == ["command", "data", "ok", "skipped"]
        assert envelope["command"] == ("check" if argv[0] == "--json" else argv[0])


def test_cli_add_takes_a_single_object_and_strips_the_skill_field(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    src = tmp_path / "entry.json"
    src.write_text(json.dumps(dict(_draft(), skill="devops-bmk")), encoding="utf-8")
    monkeypatch.chdir(repo)
    rc, out, _ = _cli(capsys, "add", "--from-file", str(src), "--json")
    [new_id] = json.loads(out)["data"]["written"]["devops-bmk"]
    [stored] = list(SD.parse_entries(SD.file_lines(SD.ledger_path(skill))))
    assert rc == 0 and stored["id"] == new_id and "skill" not in stored


def test_cli_add_is_all_or_nothing_per_skill_and_lists_what_was_written(tmp_path, capsys, monkeypatch):
    repo, first = _skill(tmp_path)
    _repo, second = _skill(tmp_path, "nothing to anchor here\n", name="meta-skill-writer")
    src = _entries_file(tmp_path, dict(_draft(), skill="devops-bmk"),
                        dict(_draft(), skill="meta-skill-writer"))
    monkeypatch.chdir(repo)
    rc, out, err = _cli(capsys, "add", "--from-file", str(src), "--json")
    data = json.loads(out)["data"]
    assert rc == 1 and json.loads(out)["ok"] is False
    assert list(data["written"]) == ["devops-bmk"] and len(data["written"]["devops-bmk"]) == 1
    # The refused entry is the FILE's second, though it is the first of its skill's batch.
    assert data["refused"] and all(p.startswith("entry 2: anchors:") for p in data["refused"])
    assert SD.ledger_path(first).is_file() and not SD.ledger_path(second).exists()


def test_cli_add_text_mode_prints_refusals_on_stderr(tmp_path, capsys, monkeypatch):
    repo, _skill_dir = _skill(tmp_path, "nothing to anchor here\n")
    src = _entries_file(tmp_path, dict(_draft(), skill="devops-bmk"))
    monkeypatch.chdir(repo)
    rc, out, err = _cli(capsys, "add", "--from-file", str(src))
    assert rc == 1 and out == "" and "refused: entry 1: anchors:" in err


# "../skills/devops-bmk" names an existing dir, so only the name check refuses it.
@pytest.mark.parametrize("skill", ["no-such-skill", "../skills/devops-bmk", None])
def test_cli_add_naming_no_existing_skill_writes_nothing(tmp_path, capsys, monkeypatch, skill):
    repo, existing = _skill(tmp_path)
    drafts = [dict(_draft(), skill="devops-bmk"), dict(_draft(), skill=skill)]
    src = _entries_file(tmp_path, *drafts)
    monkeypatch.chdir(repo)
    rc, out, err = _cli(capsys, "add", "--from-file", str(src), "--json")
    assert rc == 2 and json.loads(out)["ok"] is False and len(err.splitlines()) == 1
    assert not SD.ledger_path(existing).exists()


def test_cli_add_of_an_empty_list_is_a_run_error(tmp_path, capsys, monkeypatch):
    repo, _skill_dir = _skill(tmp_path)
    monkeypatch.chdir(repo)
    rc, _out, err = _cli(capsys, "add", "--from-file", str(_entries_file(tmp_path)))
    assert rc == 2 and "no entries" in err


def test_cli_add_over_a_corrupt_ledger_names_it_and_what_was_written(tmp_path, capsys, monkeypatch):
    repo, _first = _skill(tmp_path)
    _repo, second = _skill(tmp_path, name="meta-skill-writer")
    SD.ledger_path(second).write_bytes(b"{not json\n")
    src = _entries_file(tmp_path, dict(_draft(), skill="devops-bmk"),
                        dict(_draft(), skill="meta-skill-writer"))
    monkeypatch.chdir(repo)
    rc, out, err = _cli(capsys, "add", "--from-file", str(src), "--json")
    data = json.loads(out)["data"]
    assert rc == 2 and list(data["written"]) == ["devops-bmk"]
    assert "decisions.jsonl" in data["error"] and "line 1" in data["error"]
    assert len(err.splitlines()) == 1 and "decisions.jsonl" in err


def test_cli_add_outside_a_repo_exits_2_naming_the_flag(tmp_path, capsys, monkeypatch):
    src = tmp_path / "entries.json"
    src.write_text(json.dumps(dict(_draft(), skill="devops-bmk")), encoding="utf-8")
    monkeypatch.chdir(tmp_path)        # pytest's tmp dir is in no repo holding plugins/bitranox/skills
    rc, out, err = _cli(capsys, "add", "--from-file", str(src))
    assert rc == 2 and "--skills-dir" in err and "Traceback" not in err


def test_cli_add_inside_an_installed_plugin_clone_exits_2(tmp_path, capsys, monkeypatch):
    config = tmp_path / "config"
    repo, skill = _skill(config / "plugins" / "marketplaces" / "bitranox-skills")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    monkeypatch.chdir(repo)
    rc, _out, err = _cli(capsys, "add", "--from-file", str(_entries_file(tmp_path, dict(_draft(), skill="devops-bmk"))))
    assert rc == 2 and "--skills-dir" in err and not SD.ledger_path(skill).exists()
    rc, _out, _err = _cli(capsys, "check")
    assert rc == 0                      # reading an installed copy is harmless


def test_cli_add_with_an_explicit_skills_dir_runs_from_anywhere(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    src = _entries_file(tmp_path, dict(_draft(), skill="devops-bmk"))
    monkeypatch.chdir(tmp_path)
    rc, _out, _err = _cli(capsys, "add", "--from-file", str(src), "--skills-dir", str(skill.parent))
    assert rc == 0 and SD.ledger_path(skill).is_file()


def test_cli_json_mode_still_prints_json_on_a_run_error(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc, out, err = _cli(capsys, "add", "--from-file", str(tmp_path / "missing.json"), "--json")
    assert rc == 2 and json.loads(out)["ok"] is False and len(err.splitlines()) == 1


@pytest.mark.parametrize("argv", [["show", "no-such-skill"], ["show", "../skills/devops-bmk"],
                                  ["check", "no-such-skill"], ["show", "devops-bmk", "--kind", "rules"]])
def test_cli_show_and_check_refuse_a_bad_skill_or_kind(tmp_path, capsys, monkeypatch, argv):
    repo, _skill_dir = _skill(tmp_path)
    monkeypatch.chdir(repo)
    rc, out, err = _cli(capsys, *argv)
    assert rc == 2 and out == "" and len(err.splitlines()) == 1
    rc, out, _err = _cli(capsys, *argv, "--json")
    assert rc == 2 and json.loads(out)["ok"] is False


def test_cli_show_of_a_corrupt_ledger_exits_2_naming_the_file(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    SD.ledger_path(skill).write_bytes(b"[1]\n")
    monkeypatch.chdir(repo)
    rc, out, err = _cli(capsys, "show", "devops-bmk", "--json")
    assert rc == 2 and json.loads(out)["ok"] is False
    assert "decisions.jsonl" in err and "line 1" in err


def test_cli_check_reports_a_corrupt_ledger_as_a_finding(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    SD.ledger_path(skill).write_bytes(b"[1]\n")
    monkeypatch.chdir(repo)
    rc, out, _err = _cli(capsys, "check", "--json")
    [finding] = json.loads(out)["data"]["findings"]
    assert rc == 1 and finding["skill"] == "devops-bmk" and "line 1" in finding["text"]


def test_cli_check_prints_the_reason_of_a_lost_anchor(tmp_path, capsys, monkeypatch):
    repo, skill = _skill(tmp_path)
    SD.append_entries(skill, [_draft()], today="2026-11-06")
    (skill / "SKILL.md").write_text("bmk installs per project now.\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    rc, out, _err = _cli(capsys, "check")
    assert rc == 1 and _rule()["why"] in out and _rule()["reopen_if"] in out
    assert "checked 1 ledger(s), 1 finding(s)" in out


def test_a_usage_error_still_gives_an_envelope_in_json_mode(capsys):
    rc, out, err = _cli(capsys, "show", "--json")
    assert rc == 2 and json.loads(out)["ok"] is False and len(err.splitlines()) == 1
    rc, out, err = _cli(capsys, "frobnicate")
    assert rc == 2 and out == "" and len(err.splitlines()) == 1


def test_the_script_runs_as_a_file(tmp_path):
    # Run as a file, the script's own dir is on sys.path, which is how its sibling import resolves.
    _repo, skill = _skill(tmp_path)
    src = _entries_file(tmp_path, dict(_draft(), skill="devops-bmk"))
    script = os.path.join(os.path.dirname(SD.__file__), "skill_decisions.py")
    out = subprocess.run([sys.executable, script, "add", "--from-file", str(src), "--skills-dir",
                          str(skill.parent), "--json"], capture_output=True, encoding="utf-8",
                         cwd=str(tmp_path), env=_clean_env(), check=False)
    assert out.returncode == 0 and json.loads(out.stdout)["ok"] is True, out.stderr
