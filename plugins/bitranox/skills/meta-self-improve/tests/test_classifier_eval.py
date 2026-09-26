"""Tests for classifier_eval.py - the shadow-log report comparing the regex and Jev per site."""
import json
import os
import pathlib

import pytest

import classifier_eval as ce
import corpus_prompts  # importable because classifier_eval puts compuse-toolbox/scripts on sys.path


def _noul(v):
    return {"type": "noul", "value": v, "probabilities": None, "confidence": None}


def _result(answers, latency=800, tokens=500):
    return {"answers": {k: _noul(v) for k, v in answers.items()}, "latency_ms": latency,
            "input_tokens": tokens, "model": "jev-1.13.0"}


def stop_row(regex_fires, scores, lang="en", session="s1", user="u", reply="a", latency=800):
    return {"ts": "2026-09-22T12:00:00+00:00", "site": "stop_signal", "session_id": session,
            "lang": lang, "reason": None, "redactions": 0, "input_tokens": 500,
            "latency_ms": latency, "regex": {"fires": regex_fires},
            "results": [_result(scores, latency)],
            "states": [{"user_message": user, "assistant_reply": reply}]}


def router_row(selected, scores, session="s1", prompt="p"):
    return {"ts": "2026-09-22T12:00:00+00:00", "site": "skill_router", "session_id": session,
            "lang": "en", "reason": None, "redactions": 0, "input_tokens": 9000,
            "latency_ms": 1400, "regex": {"selected": selected, "scores": {}},
            "results": [_result(scores, 1400, 9000)], "states": [{"user_prompt": prompt}]}


def recall_row(shortlist, selected, values, session="s1", prompt="p"):
    return {"ts": "2026-09-22T12:00:00+00:00", "site": "recall_rerank", "session_id": session,
            "lang": "en", "reason": None, "redactions": 0, "input_tokens": 15000,
            "latency_ms": 900, "regex": {"shortlist": shortlist, "selected": selected},
            "results": [_result({"relevant": v}, 900, 500) for v in values],
            "states": [{"user_prompt": prompt, "memory_note": n} for n in shortlist]}


# ---- loading -------------------------------------------------------------------------------

def test_load_rows_skips_malformed_lines_and_counts_them(tmp_path):
    log = tmp_path / "shadow.jsonl"
    log.write_text(json.dumps(stop_row(False, {"correction": 0.1})) + "\n{not json\n\n",
                   encoding="utf-8")
    rows, bad = ce.load_rows(log)
    assert len(rows) == 1
    assert bad == 1


# The hook writes one file per UTC day plus, from before rotation, one undated file; a report
# over the directory must read all of them, oldest rows first.
def test_load_rows_reads_every_shadow_log_in_a_directory_oldest_first(tmp_path):
    (tmp_path / "classifier-shadow.jsonl").write_text(
        json.dumps(stop_row(False, {"correction": 0.1}, session="legacy")) + "\n", encoding="utf-8")
    for day, sid in (("2026-09-25", "newer"), ("2026-09-24", "older")):
        (tmp_path / ("classifier-shadow-%s.jsonl" % day)).write_text(
            json.dumps(stop_row(False, {"correction": 0.1}, session=sid)) + "\n{bad\n",
            encoding="utf-8")
    (tmp_path / "classifier-payload.json").write_text("{}", encoding="utf-8")
    rows, bad = ce.load_rows(tmp_path)
    assert [r["session_id"] for r in rows] == ["legacy", "older", "newer"]
    assert bad == 2


def test_cli_report_accepts_the_audit_directory(tmp_path, capsys):
    (tmp_path / "classifier-shadow-2026-09-25.jsonl").write_text(
        json.dumps(stop_row(False, {"correction": 0.1})) + "\n", encoding="utf-8")
    assert ce.main(["report", "--log", str(tmp_path), "--json"]) == 0
    env = json.loads(capsys.readouterr().out)
    assert env["data"]["sites"]["stop_signal"]["by_lang"]["en"]["neither"] == 1


def test_the_default_log_is_the_audit_directory_resolved_at_run_time(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert ce.default_log() == tmp_path / ".claude" / "self-improve-audit"


def test_load_rows_drops_excluded_sessions(tmp_path):
    log = tmp_path / "shadow.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in (
        stop_row(False, {"correction": 0.1}, session="probe-stop-shadow-0001"),
        stop_row(False, {"correction": 0.1}, session="real"))) + "\n", encoding="utf-8")
    rows, _bad = ce.load_rows(log, exclude_sessions=("probe-",))
    assert [r["session_id"] for r in rows] == ["real"]


# ---- stop_signal ---------------------------------------------------------------------------

def test_stop_signal_classifies_each_turn_into_both_regex_only_jev_only_neither():
    rows = [stop_row(True, {"correction": 0.9}),
            stop_row(True, {"correction": 0.1}),
            stop_row(False, {"correction": 0.8}),
            stop_row(False, {"correction": 0.1})]
    s = ce.summarize_stop_signal(rows, threshold=0.5)
    assert s["by_lang"]["en"] == {"both": 1, "regex_only": 1, "jev_only": 1, "neither": 1}


def test_stop_signal_splits_by_language():
    rows = [stop_row(True, {"correction": 0.9}, lang="de"),
            stop_row(False, {"correction": 0.1}, lang="en")]
    s = ce.summarize_stop_signal(rows, threshold=0.5)
    assert s["by_lang"]["de"]["both"] == 1
    assert s["by_lang"]["en"]["neither"] == 1


def test_stop_signal_threshold_is_inclusive_and_uses_the_highest_family():
    rows = [stop_row(False, {"correction": 0.2, "realization": 0.5})]
    s = ce.summarize_stop_signal(rows, threshold=0.5)
    assert s["by_lang"]["en"]["jev_only"] == 1
    assert s["disagreements"][0]["jev_families"] == ["realization"]


def test_stop_signal_row_without_results_is_counted_as_unanswered_not_as_a_no():
    row = stop_row(True, {"correction": 0.9})
    row["results"] = [None]
    row["reason"] = "timeout"
    s = ce.summarize_stop_signal([row], threshold=0.5)
    assert s["unanswered"] == 1
    assert s["by_lang"] == {}


def test_stop_signal_disagreement_carries_the_turn_text_for_adjudication():
    rows = [stop_row(True, {"correction": 0.1}, user="nein, das ist falsch", reply="ok")]
    s = ce.summarize_stop_signal(rows, threshold=0.5)
    d = s["disagreements"][0]
    assert d["kind"] == "regex_only"
    assert d["state"]["user_message"] == "nein, das ist falsch"


# ---- skill_router --------------------------------------------------------------------------

def test_router_compares_regex_selection_with_jev_top_n_above_threshold():
    rows = [router_row(["a"], {"a": 0.9, "b": 0.8, "c": 0.7, "d": 0.1})]
    s = ce.summarize_skill_router(rows, threshold=0.5, top=2)
    assert s["prompts"] == 1
    assert s["regex_picks"] == 1
    assert s["jev_picks"] == 2
    assert s["agreed_picks"] == 1
    assert s["disagreements"][0]["jev_only"] == ["b"]
    assert s["disagreements"][0]["regex_only"] == []


def test_router_suggests_nothing_when_jev_judges_the_prompt_a_continuation():
    rows = [router_row([], {"_new_task": 0.2, "a": 0.9, "b": 0.8})]
    s = ce.summarize_skill_router(rows, threshold=0.5, top=2)
    assert s["jev_picks"] == 0 and s["identical"] == 1


def test_router_new_task_answer_is_never_a_skill_pick():
    rows = [router_row(["a"], {"_new_task": 0.9, "a": 0.8})]
    s = ce.summarize_skill_router(rows, threshold=0.5, top=2)
    assert s["jev_picks"] == 1 and s["identical"] == 1


def test_router_prompt_where_both_pick_nothing_is_an_agreement():
    rows = [router_row([], {"a": 0.1, "b": 0.2})]
    s = ce.summarize_skill_router(rows, threshold=0.5, top=2)
    assert s["identical"] == 1
    assert s["disagreements"] == []


def choice_router_row(selected, gate, winner, probs):
    """A row the live hook writes since it asks the choice shape: the gate plus one choice."""
    row = router_row(selected, {})
    row["regex"]["question_view"] = "choice-v1"
    row["results"][0]["answers"] = {
        "_new_task": _noul(gate),
        "_pick": {"type": "choice", "value": winner, "probabilities": probs, "confidence": 0.6}}
    return row


def test_router_reads_a_choice_row_through_the_production_pick_rule():
    rows = [choice_router_row([], 0.8, "files-edit-xml", {"files-edit-xml": 0.6})]
    s = ce.summarize_skill_router(rows, threshold=0.5, top=2)
    assert s["jev_picks"] == 1
    assert s["disagreements"][0]["jev_only"] == ["files-edit-xml"]
    assert s["disagreements"][0]["jev_scores"] == {"files-edit-xml": 0.6}


def test_router_choice_row_keeps_a_confident_winner_the_gate_vetoed():
    rows = [choice_router_row([], 0.3, "meta-context-watcher", {"meta-context-watcher": 0.9})]
    assert ce.summarize_skill_router(rows, threshold=0.5, top=2)["jev_picks"] == 1


@pytest.mark.parametrize("gate, winner, prob", [
    (0.3, "meta-context-watcher", 0.5),   # gate fails and the winner is unsure
    (0.9, "none_needed", 0.95),           # the no-match option is never a pick
])
def test_router_choice_row_suggests_nothing(gate, winner, prob):
    rows = [choice_router_row([], gate, winner, {winner: prob})]
    s = ce.summarize_skill_router(rows, threshold=0.5, top=2)
    assert s["jev_picks"] == 0 and s["identical"] == 1


def test_router_choice_row_agrees_with_the_same_keyword_pick():
    rows = [choice_router_row(["compuse-git"], 0.8, "compuse-git", {"compuse-git": 0.7})]
    s = ce.summarize_skill_router(rows, threshold=0.5, top=2)
    assert s["agreed_picks"] == 1 and s["identical"] == 1


# ---- recall_rerank -------------------------------------------------------------------------

def test_recall_compares_injected_notes_with_notes_jev_scores_relevant():
    rows = [recall_row(["n1", "n2", "n3"], ["n1", "n3"], [0.8, 0.9, 0.2])]
    s = ce.summarize_recall(rows, threshold=0.5)
    assert s["regex_injected"] == 2
    assert s["jev_relevant"] == 2
    assert s["agreed"] == 1
    d = s["disagreements"][0]
    assert d["regex_only"] == ["n3"] and d["jev_only"] == ["n2"]


def test_recall_reports_the_score_spread_per_prompt():
    rows = [recall_row(["n1", "n2", "n3"], [], [0.31, 0.55, 0.40])]
    s = ce.summarize_recall(rows, threshold=0.5)
    assert s["spread"]["p50"] == pytest.approx(0.24)


def test_recall_rows_judged_on_different_note_views_are_reported_apart():
    old = recall_row(["n1"], ["n1"], [0.9])
    new = recall_row(["n1"], ["n1"], [0.2])
    new["regex"]["note_view"] = "summary-v1"
    rep = ce.summarize([old, new], threshold=0.5, top=2)
    assert rep["sites"]["recall_rerank"]["agreed"] == 1
    assert rep["sites"]["recall_rerank@summary-v1"]["agreed"] == 0


def test_every_input_view_a_row_records_is_part_of_its_group():
    both = recall_row(["n1"], ["n1"], [0.9])
    both["regex"].update(note_view="summary-v1", context_view="prev-reply-v1")
    stop = stop_row(False, {"correction": 0.1})
    stop["regex"]["context_view"] = "prev-reply-v1"
    rep = ce.summarize([both, stop], threshold=0.5, top=2)
    assert set(rep["sites"]) == {"stop_signal@prev-reply-v1",
                                 "recall_rerank@prev-reply-v1+summary-v1"}


# ---- cost / latency ------------------------------------------------------------------------

def test_percentiles_nearest_rank():
    assert ce.percentiles([100, 200, 300, 400]) == {"p50": 200, "p95": 400, "max": 400, "n": 4}
    assert ce.percentiles([]) == {"p50": None, "p95": None, "max": None, "n": 0}


def test_summarize_reports_cost_and_errors_per_site():
    ok = stop_row(False, {"correction": 0.1}, latency=700)
    failed = stop_row(True, {"correction": 0.1})
    failed["results"], failed["reason"] = [None], "http 529"
    rep = ce.summarize([ok, failed, router_row([], {"a": 0.1})], threshold=0.5, top=2)
    assert rep["sites"]["stop_signal"]["rows"] == 2
    assert rep["sites"]["stop_signal"]["errors"] == {"http 529": 1}
    assert rep["sites"]["stop_signal"]["latency_ms"]["p50"] == 700
    assert rep["sites"]["skill_router"]["input_tokens"]["total"] == 9000


def test_summarize_counts_rows_per_release_so_a_mixed_log_is_visible():
    new = router_row([], {"a": 0.1})
    new["plugin_version"] = "7.19.0"
    rep = ce.summarize([new, dict(new), router_row([], {"a": 0.1})], threshold=0.5, top=2)
    assert rep["sites"]["skill_router"]["releases"] == {"7.19.0": 2, "unversioned": 1}


def test_an_error_row_counts_as_an_error_and_breaks_no_summary():
    failed = router_row([], {})
    failed["results"], failed["reason"] = [], "error: AttributeError: boom"
    rep = ce.summarize([failed], threshold=0.5, top=2)
    assert rep["sites"]["skill_router"]["errors"] == {"error: AttributeError: boom": 1}
    assert rep["sites"]["skill_router"]["unanswered"] == 1


# ---- joining a live row back to the prompt it was asked about -------------------------------
# The same prompt is typed many times in one session ("read the handover"), so text alone cannot
# say which one a row belongs to; the byte offset the hook recorded can.

def _typed(uuid, text):
    return {"type": "user", "uuid": uuid, "origin": {"kind": "human"},
            "message": {"content": text}}


def _said(uuid, text):
    return {"type": "assistant", "uuid": uuid,
            "message": {"content": [{"type": "text", "text": text}]}}


def _write(path, records):
    """Write the records and return the byte offset after each one."""
    offsets, data = [], b""
    for r in records:
        data += (json.dumps(r) + "\n").encode("utf-8")
        offsets.append(len(data))
    path.write_bytes(data)
    return offsets


def _located(row, path, offset):
    return {**row, "transcript_path": str(path), "transcript_offset": offset}


REPEATED = [_typed("p1", "read the handover"), _said("a1", "Done, rank 10 is next."),
            _typed("p2", "read the handover"), _said("a2", "Done again."),
            _typed("p3", "read the handover")]


def test_a_prompt_site_row_finds_its_prompt_when_the_hook_ran_before_it_was_written(tmp_path):
    t = tmp_path / "t.jsonl"
    ends = _write(t, REPEATED)
    row = _located(router_row([], {}, prompt="read the handover"), t, ends[1])
    assert ce.locate_prompt(row) == "p2"


def test_a_prompt_site_row_finds_its_prompt_when_the_hook_ran_after_it_was_written(tmp_path):
    t = tmp_path / "t.jsonl"
    ends = _write(t, REPEATED)
    row = _located(router_row([], {}, prompt="read the handover"), t, ends[2])
    assert ce.locate_prompt(row) == "p2"


def test_a_stop_row_takes_the_prompt_before_its_offset_even_when_the_next_one_is_nearer(tmp_path):
    t = tmp_path / "t.jsonl"
    long_turn = [_typed("p1", "read the handover"), _said("a1", "x" * 5000),
                 _typed("p2", "read the handover")]
    ends = _write(t, long_turn)
    row = _located(stop_row(False, {}, user="read the handover"), t, ends[1])
    assert ce.locate_prompt(row) == "p1"


def test_a_capped_prompt_is_matched_on_its_tail(tmp_path):
    t = tmp_path / "t.jsonl"
    text = "head " * 2000 + "and finally the actual ask"
    ends = _write(t, [_typed("p1", "other"), _typed("p2", text)])
    capped = "head head" + "\n[... truncated ...]\n" + "and finally the actual ask"
    assert ce.locate_prompt(_located(router_row([], {}, prompt=capped), t, ends[1])) == "p2"


@pytest.mark.parametrize("change", [
    {"transcript_path": None},
    {"transcript_offset": None},
    {"transcript_path": "/nonexistent-dir-for-test/t.jsonl"},
    {"states": [{"user_prompt": "a prompt nobody typed"}]},
    {"states": []},
])
def test_a_row_that_cannot_be_located_answers_none(tmp_path, change):
    t = tmp_path / "t.jsonl"
    ends = _write(t, REPEATED)
    row = _located(router_row([], {}, prompt="read the handover"), t, ends[1])
    assert ce.locate_prompt({**row, **change}) is None


# ---- a family that is logged but never counted as a firing ------------------------------------
# `endorsement` scored above the threshold as a turn's ONLY reason to fire on 12 turns across two
# shadow windows, every one a plain approval ("yes", "go", "lets try 1-4"). Approving a proposal is
# not a learning signal, so it stops counting as a firing - while the question stays in the set,
# so the score keeps being recorded and can be re-judged later.

def test_endorsement_alone_is_not_a_firing():
    rep = ce.summarize_stop_signal([stop_row(False, {"endorsement": 0.94, "correction": 0.1})],
                                   threshold=0.7)
    assert rep["by_lang"]["en"] == {"both": 0, "regex_only": 0, "jev_only": 0, "neither": 1}


def test_endorsement_does_not_join_the_families_of_a_real_firing():
    rep = ce.summarize_stop_signal(
        [stop_row(False, {"endorsement": 0.94, "realization": 0.88})], threshold=0.7)
    assert rep["by_lang"]["en"]["jev_only"] == 1
    assert rep["disagreements"][0]["jev_families"] == ["realization"]


def test_a_non_firing_family_keeps_its_score_in_the_row():
    rep = ce.summarize_stop_signal([stop_row(False, {"endorsement": 0.94, "realization": 0.88})],
                                   threshold=0.7)
    assert rep["disagreements"][0]["scores"]["endorsement"] == 0.94


# ---- one threshold per site -------------------------------------------------------------------
# The three sites ask different questions and their score distributions differ, so a single number
# for all of them was always a placeholder. Measured over 1,177 recall pair judgements, 0.5 keeps
# 20% of them (about 5.9 notes a prompt) and 0.8 keeps 4% (about 1.1).

def test_each_site_is_judged_at_its_own_default_threshold():
    assert ce.SITE_THRESHOLDS["recall_rerank"] == 0.8
    assert ce.SITE_THRESHOLDS["stop_signal"] == 0.7
    # 0.5, not the 0.7 this shipped with: measured 2026-09-24 against 50 blind-labelled prompts,
    # 0.7 lost 8 of 13 needed skills on every arm, and 0.5 is where the planted controls were run
    # and passed. The reasoning is at SITE_THRESHOLDS; this line is what makes a silent change to
    # it fail, so it is deliberately a hard-coded number and not derived from the module.
    assert ce.SITE_THRESHOLDS["skill_router"] == 0.5


def test_summarize_applies_the_per_site_default_when_no_threshold_is_given():
    rows = [recall_row(["n1", "n2"], ["n1"], [0.75, 0.85])]
    rep = ce.summarize(rows, threshold=None, top=2)
    # 0.75 is relevant at the old flat 0.7 and not at recall's own 0.8
    assert rep["sites"]["recall_rerank"]["jev_relevant"] == 1
    assert rep["sites"]["recall_rerank"]["threshold"] == 0.8


def test_an_explicit_threshold_overrides_every_site():
    rows = [recall_row(["n1", "n2"], ["n1"], [0.75, 0.85])]
    rep = ce.summarize(rows, threshold=0.7, top=2)
    assert rep["sites"]["recall_rerank"]["jev_relevant"] == 2
    assert rep["sites"]["recall_rerank"]["threshold"] == 0.7


# ---- CLI -----------------------------------------------------------------------------------

def test_cli_json_envelope_and_disagreement_file(tmp_path, capsys):
    log = tmp_path / "shadow.jsonl"
    log.write_text("\n".join(json.dumps(r) for r in (
        stop_row(True, {"correction": 0.1}),
        stop_row(False, {"correction": 0.1}))) + "\n", encoding="utf-8")
    out = tmp_path / "dis.jsonl"
    rc = ce.main(["report", "--log", str(log), "--json", "--disagreements", str(out)])
    env = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert env["ok"] is True and env["command"] == "report"
    assert env["data"]["sites"]["stop_signal"]["by_lang"]["en"]["regex_only"] == 1
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["site"] == "stop_signal"


def test_cli_text_report_names_each_site(tmp_path, capsys):
    log = tmp_path / "shadow.jsonl"
    log.write_text(json.dumps(stop_row(False, {"correction": 0.1})) + "\n", encoding="utf-8")
    assert ce.main(["report", "--log", str(log)]) == 0
    text = capsys.readouterr().out
    assert "stop_signal" in text and "neither" in text


def test_cli_empty_log_exits_1(tmp_path, capsys):
    log = tmp_path / "shadow.jsonl"
    log.write_text("", encoding="utf-8")
    assert ce.main(["report", "--log", str(log), "--json"]) == 1
    env = json.loads(capsys.readouterr().out)
    assert env["ok"] is False


def test_cli_missing_log_exits_2_with_json_error(tmp_path, capsys):
    rc = ce.main(["report", "--log", str(tmp_path / "nope.jsonl"), "--json"])
    env = json.loads(capsys.readouterr().out)
    assert rc == 2 and env["ok"] is False and "nope.jsonl" in env["error"]


# ---- replay: the offline arm comparison ------------------------------------------------------
# An arm is a callable over an injected `ask`, so every test here drives the real arm code with a
# fake transport rather than patching anything inside it.


def _choice(value, probabilities=None, confidence=0.9):
    return {"type": "choice", "value": value, "probabilities": probabilities,
            "confidence": confidence}


class FakeAsk:
    """Records every request and answers from a queue. `asked` is what the arm really sent."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.asked = []

    def __call__(self, fields, questions):
        self.asked.append({"fields": fields, "questions": questions})
        return self.answers.pop(0) if self.answers else None


SKILLS = {"coding-python-uv": "Use when managing Python deps with uv",
          "compuse-bash": "Use when running shell commands",
          "docs-md-table-formatting": "Use when a markdown table is misaligned"}


BODIES = {"coding-python-uv": "A long body about uv, lockfiles, tool installs and CI caching.",
          "compuse-bash": "A long body about pipelines, exit codes, pgrep and backgrounding.",
          "docs-md-table-formatting": "A long body about padding columns and escaping pipes."}


def test_the_body_arm_ranks_on_bodies_where_the_others_rank_on_descriptions():
    # The one text source never tested on a WIDE pass. The arm that used bodies also changed to a
    # two-request rerank and scored 0 right against 11 misses, so the two variables moved together
    # and neither was measured. Cost is what made this testable: 700-char bodies are 14,175 tokens
    # a prompt, $5.95 per 10,000, against $3.81 for descriptions.
    ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice("compuse-bash")}])
    ce.run_arm("choice_body", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7, bodies=BODIES)
    options = ask.asked[0]["questions"][1].criteria
    assert options["compuse-bash"] == BODIES["compuse-bash"]
    assert SKILLS["compuse-bash"] not in options["compuse-bash"]
    assert ce.cl.NO_SKILL_KEY in options


def test_the_body_arm_falls_back_to_descriptions_when_no_bodies_are_given():
    # `bodies` is optional on run_arm, so an arm that silently ranked an EMPTY roster would look
    # like a real null rather than a wiring mistake.
    ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice("compuse-bash")}])
    ce.run_arm("choice_body", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    options = ask.asked[0]["questions"][1].criteria
    assert options["compuse-bash"] == SKILLS["compuse-bash"]


def test_every_arm_declares_which_text_it_ranks_on():
    # Pins the table so a new arm cannot be added without saying what it sends - the shape flags
    # are what makes an arm's result attributable.
    sources = {"short", "body", "router_text"}
    for name, spec in ce.ARMS.items():
        assert set(spec) == {"shape", "short", "rerank", "body", "router_text"}, name
        assert sum(1 for s in sources if spec[s]) <= 1, name   # one text source per arm


def test_the_router_text_arm_ranks_on_the_router_authored_criteria():
    # The option text the API's own guidance asks for, against the descriptions written for the
    # keyword matcher. A structured entry must reach `criteria` as an OBJECT, because that is the
    # form documented for options the model keeps confusing.
    ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice("compuse-bash")}])
    router = {"compuse-bash": {"what": "w", "not_for": "n", "examples": ["e"]},
              "coding-python-uv": "one line", "docs-md-table-formatting": "another line"}
    ce.run_arm("choice_router_text", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7,
               router_text=router)
    options = ask.asked[0]["questions"][1].criteria
    assert options["compuse-bash"] == router["compuse-bash"]
    assert options["coding-python-uv"] == "one line"


def test_the_router_text_arm_falls_back_to_descriptions_when_none_is_given():
    ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice("compuse-bash")}])
    ce.run_arm("choice_router_text", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert ask.asked[0]["questions"][1].criteria["compuse-bash"] == SKILLS["compuse-bash"]


def test_every_arm_sends_a_different_sequence_of_requests():
    # Verification that the independent variable MOVED. An arm whose traffic matches another's is
    # inert, and an inert arm produces a clean null that reads like a real result.
    #
    # The comparison is the whole SEQUENCE, in the exact bytes that reach the wire. Comparing
    # only the first request called this green when it was not: the short arm and the rerank arm
    # open identically and differ solely in the second request, which is the entire point of the
    # rerank arm.
    answer = {"_new_task": 0.9,
              "_pick": _choice("compuse-bash", {"compuse-bash": 0.6, "coding-python-uv": 0.4}),
              "coding-python-uv": 0.8, "compuse-bash": 0.9, "docs-md-table-formatting": 0.1}
    # `bodies` and `router_text` are supplied because an arm whose alternative text source is
    # missing falls back to the descriptions, which makes it byte-identical to choice_full -
    # inert, and this is the test that says so. It has now caught exactly that twice.
    router = {"compuse-bash": {"what": "w", "not_for": "n", "examples": ["e"]},
              "coding-python-uv": "one discriminating line"}
    shapes = {}
    for name in ce.ARMS:
        ask = FakeAsk([answer, answer])
        ce.run_arm(name, ask, {"user_prompt": "p"}, SKILLS, threshold=0.7, bodies=BODIES,
                   router_text=router)
        shapes[name] = tuple(json.dumps([q.to_api() for q in r["questions"]], sort_keys=True)
                             for r in ask.asked)
    assert len(set(shapes.values())) == len(shapes), list(shapes)
    assert len(shapes["choice_short_rerank"]) == 2
    assert len(shapes["choice_short"]) == 1


def test_the_noul_arm_asks_one_question_per_skill_plus_the_gate():
    ask = FakeAsk([{"_new_task": 0.9, "coding-python-uv": 0.8, "compuse-bash": 0.1,
                    "docs-md-table-formatting": 0.2}])
    out = ce.run_arm("nouls", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert len(ask.asked[0]["questions"]) == len(SKILLS) + 1
    assert out["picks"] == ["coding-python-uv"]
    assert out["requests"] == 1


def test_the_choice_arm_asks_one_question_over_the_whole_roster():
    ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice("coding-python-uv")}])
    out = ce.run_arm("choice_full", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert len(ask.asked[0]["questions"]) == 2
    assert out["picks"] == ["coding-python-uv"]


def test_the_short_arm_sends_shortened_descriptions_and_the_full_arm_does_not():
    long_skills = {"a": "Use when " + "x" * 400}
    for name, shortened in (("choice_full", False), ("choice_short", True)):
        ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice("a")}])
        ce.run_arm(name, ask, {"user_prompt": "p"}, long_skills, threshold=0.7)
        option = ask.asked[0]["questions"][1].criteria["a"]
        assert (len(option) < 200) is shortened, name


def test_a_confident_choice_passes_a_failed_gate_and_says_so():
    ask = FakeAsk([{"_new_task": 0.3, "_pick": _choice("compuse-bash", {"compuse-bash": 0.9})}])
    out = ce.run_arm("choice_full", ask, {"user_prompt": "write the handover"}, SKILLS,
                     threshold=0.5)
    assert out["picks"] == ["compuse-bash"]
    assert out["bypassed"] is True


def test_an_unsure_choice_stays_suppressed_by_a_failed_gate():
    ask = FakeAsk([{"_new_task": 0.3, "_pick": _choice("compuse-bash", {"compuse-bash": 0.5})}])
    out = ce.run_arm("choice_full", ask, {"user_prompt": "go"}, SKILLS, threshold=0.5)
    assert out["picks"] == [] and out["bypassed"] is False


def test_a_gate_below_threshold_suppresses_every_arm():
    # A continuation is 595 of the 1,409 typed prompts in the corpus, so this is the common case.
    # The choice here carries no probability, so the confidence bypass cannot apply.
    for name in ce.ARMS:
        ask = FakeAsk([{"_new_task": 0.1, "_pick": _choice("compuse-bash"),
                        "coding-python-uv": 0.99, "compuse-bash": 0.99,
                        "docs-md-table-formatting": 0.99}] * 3)
        out = ce.run_arm(name, ask, {"user_prompt": "go"}, SKILLS, threshold=0.7)
        assert out["picks"] == [], name
        assert out["gate"] == 0.1


def test_the_no_match_option_means_no_pick_not_a_pick_named_none():
    ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice(ce.cl.NO_SKILL_KEY)}])
    out = ce.run_arm("choice_full", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert out["picks"] == []


def test_the_rerank_arm_makes_a_second_request_over_the_survivors_only():
    wide = {"_new_task": 0.9, "_pick": _choice("compuse-bash",
                                               {"coding-python-uv": 0.5, "compuse-bash": 0.4,
                                                "docs-md-table-formatting": 0.1})}
    close = {"_pick": _choice("coding-python-uv"), "coding-python-uv": 0.85, "compuse-bash": 0.2}
    ask = FakeAsk([wide, close])
    out = ce.run_arm("choice_short_rerank", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7,
                     shortlist=2)
    assert out["requests"] == 2
    second = ask.asked[1]["questions"]
    assert set(second[0].criteria) == {"coding-python-uv", "compuse-bash", ce.cl.NO_SKILL_KEY}
    assert out["picks"] == ["coding-python-uv"]


def test_the_rerank_arm_suggests_nothing_when_no_survivor_fits():
    wide = {"_new_task": 0.9, "_pick": _choice("compuse-bash",
                                               {"compuse-bash": 0.6, "coding-python-uv": 0.4})}
    close = {"_pick": _choice("compuse-bash"), "compuse-bash": 0.2, "coding-python-uv": 0.1}
    out = ce.run_arm("choice_short_rerank", FakeAsk([wide, close]), {"user_prompt": "p"}, SKILLS,
                     threshold=0.7, shortlist=2)
    assert out["picks"] == []


def test_an_unanswered_request_yields_no_picks_and_says_why():
    out = ce.run_arm("choice_full", FakeAsk([None]), {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert out["picks"] == [] and out["answered"] is False


_PICKED = {"_new_task": 0.9, "_pick": _choice("compuse-bash")}
_NOTHING = {"_new_task": 0.1, "_pick": _choice(ce.cl.NO_SKILL_KEY)}


def test_a_gated_row_still_records_the_choice_it_already_paid_for():
    # The choice rides in the same request as the gate, so dropping it on a gated row throws away
    # an answer already bought - and with it any chance of re-thresholding the gate offline. A
    # sweep could then only remove picks, never restore a suppressed one, which reads as an arm
    # being insensitive to its threshold when it is the log that went blank.
    gated = FakeAsk([{"_new_task": 0.2, "_pick": _choice("compuse-bash")}])
    out = ce.run_arm("choice_full", gated, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert out["picks"] == []                      # the gate still decides what is SUGGESTED
    assert out["winner"] == "compuse-bash"         # but the answer is not thrown away
    assert out["requests"] == 1                    # and no second request was bought for it


def test_a_gated_rerank_row_does_not_buy_the_close_pass():
    gated = FakeAsk([{"_new_task": 0.2, "_pick": _choice("compuse-bash")}])
    out = ce.run_arm("choice_short_rerank", gated, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert out["requests"] == 1 and out["picks"] == []
    assert out["winner"] == "compuse-bash"


def test_controls_refuse_the_run_when_both_answer_the_same_way():
    # A detector that fires on everything and one that works are indistinguishable without a
    # known negative, so no number from the run may be read until they differ.
    same = FakeAsk([_PICKED] * len(ce.REPLAY_CONTROLS))
    with pytest.raises(ce.ControlFailed):
        ce.check_controls("choice_full", same, SKILLS, threshold=0.7)


def test_controls_pass_when_every_planted_control_answers_its_own_way():
    ok = FakeAsk([_PICKED, _NOTHING, _PICKED, _NOTHING])
    ce.check_controls("choice_full", ok, SKILLS, threshold=0.7)


def test_the_controls_pose_a_session_s_first_prompt_both_ways():
    # The state that found the gate defect: `_router_fields` omits an empty field, so the first
    # prompt of a session carries neither `previous_assistant_message` nor `recent_activity`. A
    # control set without it cannot see a gate that only works once a session has a past, and no
    # detector finds the case nobody wrote down. Both directions, because a gate that answers yes
    # to everything at a session's start passes a positive-only check.
    bare = [c for c in ce.REPLAY_CONTROLS
            if not (set(c["fields"]) & {"previous_assistant_message", "recent_activity"})]
    assert sorted(c["expect_pick"] for c in bare) == [False, True]
    assert all(set(c["fields"]) == {"user_prompt", "project"} for c in bare)


def test_run_controls_reports_the_gate_score_behind_every_verdict():
    # A control passing at 0.71 and one passing at 0.90 are one row and two instruments: the
    # defect this caught was a gate on the wrong side of its threshold by 0.02, and the fix
    # clears it by the same margin.
    rows = ce.run_controls("choice_full", FakeAsk([_PICKED, _NOTHING, _PICKED, _NOTHING]), SKILLS,
                           threshold=0.7)
    assert [r["ok"] for r in rows] == [True] * len(ce.REPLAY_CONTROLS)
    assert [r["gate"] for r in rows] == [0.9, 0.1, 0.9, 0.1]
    assert rows[2]["state"] == ["project", "user_prompt"]


def test_a_failing_control_names_the_state_it_was_posed_with():
    # Which control failed is the whole diagnosis: the same prompt passes with a history and
    # fails without one, and a message naming only the prompt cannot tell those apart.
    with pytest.raises(ce.ControlFailed, match="project, user_prompt"):
        ce.check_controls("choice_full", FakeAsk([_PICKED, _NOTHING, _NOTHING, _NOTHING]),
                          SKILLS, threshold=0.7)


def test_the_sample_is_stratified_over_short_and_long_prompts():
    prompts = [{"uuid": "s%d" % i, "prompt": "go"} for i in range(10)]
    prompts += [{"uuid": "l%d" % i, "prompt": "please rewrite the parser for me now"}
                for i in range(10)]
    picked = ce.stratified_prompts(prompts, per_class=3, seed=1)
    kinds = [p["uuid"][0] for p in picked]
    assert kinds.count("s") == 3 and kinds.count("l") == 3


def test_a_failed_control_exits_3_so_a_gate_reading_the_code_cannot_read_the_numbers(
        tmp_path, capsys):
    # The exception existing is not the guarantee; the EXIT CODE is, because that is what a
    # caller keys on. Exit 3 means the instrument is wrong, which is not the same as exit 1
    # (nothing to report) or exit 2 (bad usage), and collapsing it into either would let a run
    # that measured nothing read as a run that found nothing. Driven through the real replay
    # with a transport that answers every planted control the same way.
    class _PicksEverything(FakeClassifier):
        def ask(self, state, questions):
            return super().ask({"user_prompt": "a real task"}, questions)

    rc = _replay(tmp_path, "--arm", "choice_full", clf=_PicksEverything())
    env = json.loads(capsys.readouterr().out)
    assert rc == 3
    assert env["ok"] is False and "no number from this run may be read" in env["error"]


def test_an_arm_records_the_scores_it_judged_not_only_its_verdict():
    # A threshold is the cheapest thing to get wrong and the most expensive to re-measure. A run
    # that stores only what it DECIDED forces a second paid run to ask "and at 0.3?".
    ask = FakeAsk([{"_new_task": 0.9, "coding-python-uv": 0.8, "compuse-bash": 0.12,
                    "docs-md-table-formatting": 0.2}])
    out = ce.run_arm("nouls", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert out["scores"]["compuse-bash"] == 0.12
    assert out["scores"]["_new_task"] == 0.9


def test_a_choice_arm_records_the_whole_distribution():
    probs = {"coding-python-uv": 0.5, "compuse-bash": 0.4, "docs-md-table-formatting": 0.1}
    ask = FakeAsk([{"_new_task": 0.9, "_pick": _choice("coding-python-uv", probs)}])
    out = ce.run_arm("choice_full", ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
    assert out["probabilities"] == probs


def test_the_rerank_arm_records_the_close_pass_scores_so_it_can_be_rethresholded():
    wide = {"_new_task": 0.9, "_pick": _choice("compuse-bash",
                                               {"coding-python-uv": 0.5, "compuse-bash": 0.4})}
    close = {"_pick": _choice("coding-python-uv"), "coding-python-uv": 0.45, "compuse-bash": 0.2}
    out = ce.run_arm("choice_short_rerank", FakeAsk([wide, close]), {"user_prompt": "p"}, SKILLS,
                     threshold=0.7, shortlist=2)
    assert out["picks"] == []                       # below 0.7, as the run measured
    assert out["rerank_scores"]["coding-python-uv"] == 0.45   # but 0.45 is recorded
    assert out["rerank_winner"] == "coding-python-uv"


def test_bodies_carry_the_opening_of_the_skill_and_not_its_front_matter(tmp_path):
    # Request 2 exists to re-read the survivors at length. Handing it the description again would
    # make the close pass the wide pass with fewer options, which cannot correct anything.
    skill = tmp_path / "coding-python-uv"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: coding-python-uv\ndescription: Use when managing deps\n---\n\n"
        "# uv\n\nuv replaces pip and virtualenv. " + "detail " * 300, encoding="utf-8")
    bodies = ce.load_skill_bodies(tmp_path, cap=120)
    assert "description:" not in bodies["coding-python-uv"]
    assert bodies["coding-python-uv"].startswith("# uv")
    assert len(bodies["coding-python-uv"]) <= 120


def test_a_skill_without_front_matter_still_yields_a_body(tmp_path):
    skill = tmp_path / "loose"
    skill.mkdir()
    (skill / "SKILL.md").write_text("just prose, no front matter", encoding="utf-8")
    assert ce.load_skill_bodies(tmp_path)["loose"] == "just prose, no front matter"


def test_sizing_estimates_every_arm_without_calling_anything():
    est = ce.size_replay(SKILLS, prompts=10)
    assert set(est["arms"]) == set(ce.ARMS)
    assert est["arms"]["nouls"]["tokens"] > est["arms"]["choice_short"]["tokens"]
    assert est["total_tokens"] == sum(a["tokens"] for a in est["arms"].values())


def _log_row(uuid, prompt, line, **state):
    return json.dumps({"uuid": uuid, "source": "/t/%s.jsonl" % uuid, "line": line,
                       "state": dict({"user_prompt": prompt}, **state), "arms": {}})


def test_a_pinned_replay_reads_the_exact_prompts_of_an_earlier_run(tmp_path):
    # The whole point of pinning: a paid adjudication labels PROMPTS, so a later run must ask
    # about the same ones. Sampling the corpus cannot promise that, because the corpus grows.
    log = tmp_path / "run.jsonl"
    log.write_text("%s\n\n%s\n" % (_log_row("a", "reformat the table", 7, project="p"),
                                   _log_row("b", "go ahead", 12)), encoding="utf-8")
    picked = ce.prompts_from_log(log)
    assert [p["prompt"] for p in picked] == ["reformat the table", "go ahead"]
    assert [p["uuid"] for p in picked] == ["a", "b"]
    # The recorded state rides along and is what a pinned run re-sends: an adjudication labels a
    # prompt IN A STATE, so rebuilding a different one would not answer the judged question.
    assert picked[0]["recorded_state"]["project"] == "p"
    assert picked[0]["recorded_state"]["user_prompt"] == "reformat the table"


def test_a_row_carrying_no_user_prompt_is_skipped_rather_than_replayed_as_empty(tmp_path):
    log = tmp_path / "run.jsonl"
    log.write_text("%s\n%s\n" % (json.dumps({"uuid": "x", "state": {}}),
                                 _log_row("b", "real prompt", 3)), encoding="utf-8")
    assert [p["prompt"] for p in ce.prompts_from_log(log)] == ["real prompt"]


def test_state_drift_is_silent_when_the_rebuilt_state_matches_what_was_recorded(tmp_path):
    log = tmp_path / "run.jsonl"
    log.write_text(_log_row("a", "reformat the table", 7, project="p") + "\n", encoding="utf-8")
    picked = ce.prompts_from_log(log)
    assert ce.state_drift(picked, [{"user_prompt": "reformat the table", "project": "p"}]) == []


def test_state_drift_names_a_field_the_rebuild_lost():
    # The real failure this guards: a source transcript that has been moved or swept rebuilds a
    # SHORTER state in silence, and the arms then answer a different question than the judges
    # were shown - which would read as an arm changing its mind rather than as a broken replay.
    picked = [{"uuid": "a", "prompt": "reformat the table",
               "recorded_state": {"user_prompt": "reformat the table", "project": "p",
                                  "previous_assistant_message": "CI is green"}}]
    drift = ce.state_drift(picked, [{"user_prompt": "reformat the table", "project": "p"}])
    assert len(drift) == 1
    assert drift[0]["fields"] == ["previous_assistant_message"]
    assert drift[0]["uuid"] == "a"


def test_state_drift_treats_an_absent_field_and_an_empty_one_as_the_same():
    # `_router_fields` omits a field that is empty, so "absent" and "empty string" are the same
    # state; reporting them as drift would make every pinned run look broken.
    picked = [{"uuid": "a", "prompt": "p",
               "recorded_state": {"user_prompt": "p", "recent_activity": ""}}]
    assert ce.state_drift(picked, [{"user_prompt": "p"}]) == []


# ---- the roster a replay offers ---------------------------------------------------------------

def _listing_transcript(tmp_path, names_descs):
    rec = {"type": "attachment", "attachment": {
        "type": "skill_listing", "isInitial": True, "skillCount": len(names_descs),
        "names": [n for n, _d in names_descs],
        "content": "\n".join("- %s: %s" % nd for nd in names_descs)}}
    p = tmp_path / "source.jsonl"
    p.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    return str(p)


def test_an_installed_roster_is_the_listing_of_the_prompts_own_session(tmp_path):
    # A replay judging whether a wider roster closes the gap must offer each prompt the skills
    # ITS session had, not whatever this machine has installed today.
    src = _listing_transcript(tmp_path, [("bitranox:compuse-bash", "shell"),
                                         ("typesafe:typesafe-ai", "TypeSafe")])
    skills, source = ce.roster_for({"source": src}, SKILLS, "installed")
    assert source == "transcript"
    assert skills == {"compuse-bash": "shell", "typesafe:typesafe-ai": "TypeSafe"}


def test_an_installed_roster_offers_a_trimmed_project_skill_from_the_prompts_cwd(tmp_path):
    # The harness trims descriptions to fit its listing budget, leaving `- <name>`; the skill is
    # still installed, and its text is read from the project the prompt was typed in.
    md = tmp_path / "proj" / ".claude" / "skills" / "provmm-build" / "SKILL.md"
    md.parent.mkdir(parents=True)
    md.write_text("---\ndescription: Build provmm.\n---\n", encoding="utf-8")
    rec = {"type": "attachment", "attachment": {
        "type": "skill_listing", "isInitial": True, "names": ["bitranox:compuse-bash",
                                                              "provmm-build"],
        "content": "- bitranox:compuse-bash: shell\n- provmm-build"}}
    src = tmp_path / "source.jsonl"
    src.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    skills, source = ce.roster_for({"source": str(src), "cwd": str(tmp_path / "proj")}, SKILLS,
                                   "installed")
    assert source == "transcript"
    assert skills == {"compuse-bash": "shell", "provmm-build": "Build provmm."}


def test_an_installed_roster_falls_back_to_the_shipped_one_when_the_source_has_none(tmp_path):
    missing = str(tmp_path / "swept.jsonl")
    assert ce.roster_for({"source": missing}, SKILLS, "installed") == (SKILLS, "shipped")


def test_the_default_roster_is_the_shipped_one_so_earlier_runs_stay_comparable(tmp_path):
    src = _listing_transcript(tmp_path, [("typesafe:typesafe-ai", "TypeSafe")])
    assert ce.roster_for({"source": src}, SKILLS, "shipped") == (SKILLS, "shipped")


def test_a_description_override_replaces_the_listed_text_by_bare_name():
    # A listing names a plugin's own skills bare and other plugins' skills prefixed; an override
    # written as the bare name must reach both spellings.
    offered = {"meta-context-watcher": "old", "typesafe:typesafe-ai": "ts", "compuse-bash": "sh"}
    out, applied = ce.with_descriptions(offered, {"meta-context-watcher": "new",
                                                  "typesafe-ai": "ts2"})
    assert out == {"meta-context-watcher": "new", "typesafe:typesafe-ai": "ts2",
                   "compuse-bash": "sh"}
    assert applied == ["meta-context-watcher", "typesafe:typesafe-ai"]
    assert offered["meta-context-watcher"] == "old", "the caller's roster must not be mutated"


def test_an_override_naming_no_offered_skill_reports_that_nothing_was_applied():
    out, applied = ce.with_descriptions({"compuse-bash": "sh"}, {"meta-context-watcher": "new"})
    assert out == {"compuse-bash": "sh"} and applied == []


def test_the_replay_command_reads_each_description_override_from_its_file(tmp_path):
    f = tmp_path / "desc.txt"
    f.write_text("  Use when reading a handover\n", encoding="utf-8")
    args = ce._parser().parse_args(
        ["replay", "--description", "meta-context-watcher=%s" % f,
         "--description", "compuse-bash=%s" % f])
    assert args.description == [("meta-context-watcher", "Use when reading a handover"),
                                ("compuse-bash", "Use when reading a handover")]
    assert ce._parser().parse_args(["replay"]).description is None


@pytest.mark.parametrize("value", ["no-equals-sign", "=file.txt", "skill=", "skill=missing.txt"])
def test_a_malformed_or_unreadable_description_override_is_refused(tmp_path, value, capsys):
    with pytest.raises(SystemExit):
        ce._parser().parse_args(["replay", "--description", value.replace(
            "missing.txt", str(tmp_path / "missing.txt"))])
    assert "--description" in capsys.readouterr().err


class _NoKeywords:
    @staticmethod
    def match(_prompt, _triggers, max_skills):
        return []


def test_a_replay_row_offers_the_overridden_text_and_records_that_it_did():
    ask = FakeAsk([{}])
    args = ce._parser().parse_args(["replay", "--arm", "choice_full"])
    args.description = [("coding-python-uv", "Use when READING A HANDOVER")]
    prompt = {"prompt": "read the handover", "recorded_state": {"user_prompt": "read the handover"}}
    row = ce._replay_one(prompt, ask, SKILLS, {}, _NoKeywords, {}, args)
    assert row["description_overrides"] == ["coding-python-uv"]
    assert ask.asked[0]["questions"][1].criteria["coding-python-uv"] == \
        "Use when READING A HANDOVER"


def test_a_replay_row_without_overrides_keeps_its_earlier_shape():
    args = ce._parser().parse_args(["replay", "--arm", "choice_full"])
    prompt = {"prompt": "go", "recorded_state": {"user_prompt": "go"}}
    row = ce._replay_one(prompt, FakeAsk([{}]), SKILLS, {}, _NoKeywords, {}, args)
    assert "description_overrides" not in row


def test_a_replay_can_be_limited_to_one_arm():
    assert ce.selected_arms(None) == list(ce.ARMS)
    assert ce.selected_arms("choice_full") == ["choice_full"]


def test_the_replay_command_accepts_an_arm_and_a_roster():
    args = ce._parser().parse_args(["replay", "--arm", "choice_full", "--roster", "installed"])
    assert args.arm == "choice_full" and args.roster == "installed"
    assert ce._parser().parse_args(["replay"]).roster == "shipped"


# ---- report: an undecodable byte or an unreadable dir is an IO fact, not "no rows" ------------

def test_a_non_utf8_byte_is_counted_as_one_malformed_line(tmp_path, capsys):
    log = tmp_path / "shadow.jsonl"
    log.write_bytes(json.dumps(stop_row(False, {"correction": 0.1})).encode("utf-8")
                    + b"\n\xff\xfe broken\n")
    assert ce.main(["report", "--log", str(log), "--json"]) == 0
    env = json.loads(capsys.readouterr().out)
    assert env["ok"] is True and env["skipped"]["malformed_lines"] == 1


def test_a_bom_does_not_cost_the_first_row(tmp_path):
    log = tmp_path / "shadow.jsonl"
    log.write_bytes(b"\xef\xbb\xbf" + json.dumps(stop_row(False, {"correction": 0.1})).encode())
    rows, bad = ce.load_rows(log)
    assert len(rows) == 1 and bad == 0


@pytest.mark.skipif(not hasattr(__import__("os"), "geteuid") or __import__("os").geteuid() == 0,
                    reason="needs a non-root POSIX user for chmod 000 to deny a read")
def test_an_unreadable_audit_dir_is_an_io_error_not_an_empty_log(tmp_path, capsys):
    audit = tmp_path / "audit"
    audit.mkdir()
    (audit / "classifier-shadow-2026-09-25.jsonl").write_text(
        json.dumps(stop_row(False, {"correction": 0.1})) + "\n", encoding="utf-8")
    audit.chmod(0)
    try:
        rc = ce.main(["report", "--log", str(audit), "--json"])
    finally:
        audit.chmod(0o755)
    env = json.loads(capsys.readouterr().out)
    assert rc == 2 and "cannot read" in env["error"]


def test_a_disagreements_file_that_cannot_be_written_exits_2(tmp_path, capsys):
    log = tmp_path / "shadow.jsonl"
    log.write_text(json.dumps(stop_row(True, {"correction": 0.1})) + "\n", encoding="utf-8")
    out = tmp_path / "is-a-dir"
    out.mkdir()
    assert ce.main(["report", "--log", str(log), "--json", "--disagreements", str(out)]) == 2
    assert "cannot write" in json.loads(capsys.readouterr().out)["error"]


# ---- counts must be at least 1 -----------------------------------------------------------------

@pytest.mark.parametrize("argv", [["report", "--top", "-1"], ["report", "--top", "0"],
                                  ["replay", "--top", "-1"], ["replay", "--limit", "0"],
                                  ["size", "--limit", "-1"], ["controls", "--shortlist", "0"]])
def test_a_count_below_one_is_refused(argv, capsys):
    with pytest.raises(SystemExit) as exc:
        ce._parser().parse_args(argv)
    assert exc.value.code == 2
    assert "must be at least 1" in capsys.readouterr().err


def test_a_positive_count_is_accepted():
    assert ce._parser().parse_args(["report", "--top", "2"]).top == 2
    assert ce._parser().parse_args(["replay", "--limit", "1", "--shortlist", "3"]).limit == 1


# ---- the module docstring names every command and exit code the CLI has ----------------------

def test_the_docstring_documents_every_command_and_exit_3():
    doc = ce.__doc__
    for command in ("report", "replay", "size", "controls"):
        assert "classifier_eval.py %s" % command in doc, command
    assert "3 " in doc.split("Exit codes:")[1]
    assert "calls no API" not in doc


# ---- replay end to end, with a fake transport at the classifier seam --------------------------

class FakeClassifier:
    """The classifier seam `_run_replay` asks through: `.key`, `.ask(state, questions)`,
    `.last_reason`. Answers the gate by the prompt text and always picks the table skill, so
    single-request arms pass the planted controls and the two-request rerank arm, which needs a
    close-pass score this fake never gives, fails them."""

    def __init__(self, key="k", reasons=()):
        self.key = key
        self.last_reason = None
        self.reasons = list(reasons)
        self.asked = []

    def ask(self, state, questions):
        self.asked.append((state, questions))
        if self.reasons:
            self.last_reason = self.reasons.pop(0)
            return None
        gate = 0.1 if "go ahead" in state.get("user_prompt", "") else 0.9
        answers = {ce.cl.NEW_TASK_ID: ce.cl.Answer("noul", gate),
                   ce.cl.PICK_ID: ce.cl.Answer("choice", "docs-md-table-formatting")}
        return ce.cl.Result(answers=answers, latency_ms=5, input_tokens=10, model="fake")


def _pinned_log(tmp_path):
    log = tmp_path / "earlier.jsonl"
    log.write_text(_log_row("a", "reformat the markdown table", 3, project="p") + "\n",
                   encoding="utf-8")
    return log


def _replay(tmp_path, *extra, clf=None, skills=None):
    argv = ["replay", "--prompts", str(_pinned_log(tmp_path)), "--out",
            str(tmp_path / "out.jsonl"), "--json", *extra]
    return ce.main(argv, clf=clf or FakeClassifier(), skills=SKILLS if skills is None else skills)


def test_replay_vets_the_arm_it_replays_not_a_fixed_one(tmp_path, capsys):
    assert _replay(tmp_path, "--arm", "choice_full") == 0
    env = json.loads(capsys.readouterr().out)
    assert env["ok"] is True and list(env["data"]["arms"]) == ["choice_full"]
    assert env["data"]["arms"]["choice_full"]["prompts_with_a_pick"] == 1


def test_replay_of_an_arm_whose_controls_fail_exits_3(tmp_path, capsys):
    """The control for the test above: the rerank arm really does fail these controls."""
    assert _replay(tmp_path, "--arm", "choice_short_rerank") == 3
    assert "choice_short_rerank" in json.loads(capsys.readouterr().out)["error"]
    assert not (tmp_path / "out.jsonl").exists(), "no row may be bought after a failed control"


def test_replay_passes_the_router_text_to_the_controls(tmp_path, capsys):
    clf = FakeClassifier()
    assert _replay(tmp_path, "--arm", "choice_router_text", clf=clf) == 0
    control_request = clf.asked[0][1]
    router = ce.cl.load_router_criteria(SKILLS)
    assert router["compuse-bash"] != SKILLS["compuse-bash"], "fixture must carry router text"
    offered = control_request[1].criteria
    assert all(offered[name] == router[name] for name in SKILLS)


def test_replay_vets_the_description_overrides_it_replays(tmp_path, capsys):
    """The controls ranked on the UNOVERRIDDEN descriptions, so a reworded description that
    broke the router passed the gate built to stop it and every row was then bought with it."""
    new = tmp_path / "desc.txt"
    new.write_text("Use when a MARKDOWN TABLE needs its columns padded", encoding="utf-8")
    clf = FakeClassifier()
    assert _replay(tmp_path, "--arm", "choice_full", "--description",
                   "docs-md-table-formatting=%s" % new, clf=clf) == 0
    control_request = clf.asked[0][1]
    offered = control_request[1].criteria
    assert offered["docs-md-table-formatting"] == "Use when a MARKDOWN TABLE needs its columns padded"
    assert offered["compuse-bash"] == SKILLS["compuse-bash"]


def test_replay_without_an_api_key_exits_2(tmp_path, capsys):
    assert _replay(tmp_path, "--arm", "choice_full", clf=FakeClassifier(key=None)) == 2
    assert "no api key" in json.loads(capsys.readouterr().out)["error"]


def test_replay_without_skills_exits_2(tmp_path, capsys):
    assert _replay(tmp_path, "--arm", "choice_full", skills={}) == 2
    assert "no skills" in json.loads(capsys.readouterr().out)["error"]


def test_replay_of_an_empty_prompt_log_exits_1(tmp_path, capsys):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    rc = ce.main(["replay", "--prompts", str(empty), "--out", str(tmp_path / "o.jsonl"), "--json"],
                 clf=FakeClassifier(), skills=SKILLS)
    assert rc == 1
    assert "no prompts" in json.loads(capsys.readouterr().out)["error"]


def test_a_pinned_prompt_carrying_a_line_separator_is_read_whole(tmp_path):
    log = tmp_path / "run.jsonl"
    row = {"uuid": "a", "state": {"user_prompt": "first\u2028second"}, "arms": {}}
    log.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    assert [p["prompt"] for p in ce.prompts_from_log(log)] == ["first\u2028second"]


# ---- Asker: a rate limit is retried, any other failure is not ----------------------------------

def test_the_asker_retries_a_rate_limit_and_counts_every_attempt():
    slept = []
    clf = FakeClassifier(reasons=["http 429", "http 529"])
    ask = ce.Asker(clf, sleep=slept.append)
    answers = ask({"user_prompt": "p"}, [])
    assert answers[ce.cl.NEW_TASK_ID]["value"] == 0.9
    assert ask.calls == 3 and slept == [2, 4]
    assert ask.reasons == {"http 429": 1, "http 529": 1}
    assert ask.tokens == 10


def test_the_asker_does_not_retry_a_non_rate_limit_failure():
    slept = []
    ask = ce.Asker(FakeClassifier(reasons=["http 401"]), sleep=slept.append)
    assert ask({"user_prompt": "p"}, []) is None
    assert ask.calls == 1 and slept == []


def test_the_asker_gives_up_after_its_attempts():
    ask = ce.Asker(FakeClassifier(reasons=["http 429"] * 5), attempts=3, sleep=lambda _s: None)
    assert ask({"user_prompt": "p"}, []) is None
    assert ask.calls == 3


# ---- a cp1252 console does not crash on a path or text it cannot encode ------------------------

def test_a_cp1252_console_survives_a_json_envelope_it_cannot_encode(tmp_path):
    import os
    import subprocess
    import sys
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env.update(HOME=str(tmp_path), USERPROFILE=str(tmp_path), PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, ce.__file__, "report", "--json", "--log",
                        str(tmp_path / "\u65e5\u672c.jsonl")],
                       env=env, capture_output=True, encoding="utf-8", errors="replace")
    assert r.returncode == 2, r.stderr
    assert "UnicodeEncodeError" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


# ---- the replay prefix ends exactly where corpus_prompts says the prompt's line is --------------

def _cli_record(uuid, content):
    return json.dumps({"type": "user", "uuid": uuid, "entrypoint": "cli", "isSidechain": False,
                       "message": {"role": "user", "content": content}}, ensure_ascii=False)


# Records a JSONL writer can leave in a transcript: str.splitlines() breaks each of them in two
# (U+2028, U+2029, U+0085 are legal unescaped in a JSON string; a raw \f, \x1c or \r inside a line
# makes it unparseable, but it is still ONE line), so a splitlines() count drifts from a "\n" one.
_AWKWARD = [
    json.dumps({"type": "assistant", "message": {"content": "a\u2028b"}}, ensure_ascii=False),
    '{"type": "assistant", "message": {"content": "form\ffeed"}}',
    _cli_record("u1", "first\u2029second\x85third"),
    'half\x1cwritten\rrecord',
    _cli_record("u2", "the prompt after all of them"),
]


def _prefix_of(tmp_path, prompt):
    out_dir = tmp_path / ("out-%s" % prompt["uuid"])
    out_dir.mkdir()
    return pathlib.Path(ce._prefix_transcript(prompt, out_dir)).read_bytes().decode("utf-8")


@pytest.mark.parametrize("eol", ["\n", "\r\n"])
def test_the_replay_prefix_and_corpus_prompts_count_the_same_lines(tmp_path, eol):
    """The prefix is cut at the line corpus_prompts numbered; splitlines() cut it elsewhere, so the
    arm was judged on a state holding half a record, or missing earlier ones."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    text = eol.join(_AWKWARD) + eol
    (corpus / "t.jsonl").write_bytes(text.encode("utf-8"))
    prompts = corpus_prompts.collect_prompts(str(corpus))["prompts"]
    assert [(p["uuid"], p["line"]) for p in prompts] == [("u1", 3), ("u2", 5)]
    records = text.split("\n")
    for prompt in prompts:
        prefix = _prefix_of(tmp_path, prompt)
        assert prefix == "\n".join(records[:prompt["line"] - 1])
        assert prefix.split("\n") == records[:prompt["line"] - 1]
        assert prompt["uuid"] not in prefix


def test_the_replay_prefix_of_the_first_line_is_empty(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "t.jsonl").write_text(_cli_record("u1", "hi") + "\n", encoding="utf-8")

    (prompt,) = corpus_prompts.collect_prompts(str(corpus))["prompts"]
    assert _prefix_of(tmp_path, prompt) == ""


# ---- a prefix that cannot be built is never judged as an empty state ---------------------------

def test_an_unreadable_source_transcript_refuses_the_prefix_rather_than_writing_an_empty_one(
        tmp_path):
    """An EMPTY prefix is also what the first prompt of a session legitimately has, so writing
    one for a transcript that could not be read made the arms judge the prompt on a state it
    never had, with nothing in the row to say so."""
    prompt = {"uuid": "gone", "source": str(tmp_path / "missing.jsonl"), "line": 3}
    with pytest.raises(ce.PrefixUnavailable, match="missing.jsonl"):
        ce._prefix_transcript(prompt, tmp_path)
    assert not (tmp_path / "prefix.jsonl").exists()


class DeletingClassifier(FakeClassifier):
    """Removes one corpus transcript on its first request: the replay's planted controls ask
    before any prompt is replayed, so the transcript is read at sampling and gone at replay."""

    def __init__(self, doomed):
        super().__init__()
        self.doomed = doomed

    def ask(self, state, questions):
        if self.doomed.exists():
            self.doomed.unlink()
        return super().ask(state, questions)


def test_a_replay_skips_a_prompt_whose_prefix_cannot_be_built_and_says_so(tmp_path, capsys):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    doomed = corpus / "a.jsonl"
    doomed.write_text(_cli_record("x0", "please reformat the markdown table for me") + "\n"
                      + _cli_record("xa", "now reformat the other markdown table too") + "\n",
                      encoding="utf-8")
    (corpus / "b.jsonl").write_text(_cli_record("xb", "go ahead") + "\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    rc = ce.main(["replay", "--root", str(corpus), "--limit", "1", "--arm", "choice_full",
                  "--out", str(out), "--json"], clf=DeletingClassifier(doomed), skills=SKILLS)
    env = json.loads(capsys.readouterr().out)
    assert rc == 0, env
    skipped = env["data"]["skipped_prompts"]
    assert [s["uuid"] for s in skipped] in (["x0"], ["xa"])
    assert "a.jsonl" in skipped[0]["reason"]
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [r["uuid"] for r in rows] == ["xb"], "the skipped prompt was scored anyway"
    assert env["data"]["sampled"] == 1
    assert env["skipped"] == {"prompts_without_a_prefix": 1, "unreadable_corpus_paths": 0}


def test_a_replay_with_every_prefix_readable_skips_nothing(tmp_path, capsys):
    """The control: the same corpus, nothing removed."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.jsonl").write_text(_cli_record("x0", "please reformat the markdown table for me")
                                    + "\n", encoding="utf-8")
    (corpus / "b.jsonl").write_text(_cli_record("xb", "go ahead") + "\n", encoding="utf-8")
    rc = ce.main(["replay", "--root", str(corpus), "--limit", "1", "--arm", "choice_full",
                  "--out", str(tmp_path / "out.jsonl"), "--json"],
                 clf=FakeClassifier(), skills=SKILLS)
    env = json.loads(capsys.readouterr().out)
    assert rc == 0 and env["data"]["skipped_prompts"] == [] and env["data"]["sampled"] == 2


def test_a_replay_reports_a_corpus_transcript_it_could_not_read(tmp_path, capsys):
    """collect_prompts names every transcript it could not open in `skipped`; the replay dropped
    that list, so an unreadable corpus file shrank the sample with nothing said about it."""
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.jsonl").write_text(_cli_record("x0", "please reformat the markdown table for me")
                                    + "\n", encoding="utf-8")
    (corpus / "b.jsonl").write_text(_cli_record("xb", "go ahead") + "\n", encoding="utf-8")
    gone = corpus / "c.jsonl"
    try:
        os.symlink(str(tmp_path / "no-such-transcript.jsonl"), str(gone))
    except (OSError, NotImplementedError) as exc:
        pytest.skip("cannot create a dangling symlink here: %s" % exc)
    rc = ce.main(["replay", "--root", str(corpus), "--limit", "1", "--arm", "choice_full",
                  "--out", str(tmp_path / "out.jsonl"), "--json"],
                 clf=FakeClassifier(), skills=SKILLS)
    captured = capsys.readouterr()
    env = json.loads(captured.out)
    assert rc == 0, env
    unread = env["data"]["corpus"]["unreadable"]
    assert len(unread) == 1 and "c.jsonl" in unread[0]
    assert env["skipped"]["unreadable_corpus_paths"] == 1
    assert "c.jsonl" in captured.err
    assert "c.jsonl" in ce.render_replay(env["data"])


# ---- this file stays ASCII: an invisible separator in a literal is unreviewable ----------------

def test_this_test_file_holds_only_ascii():
    """A raw U+2028 in a literal renders as nothing (or as a line break) in a diff, so a reader
    cannot see what the test asserts. Spell such characters as escapes."""
    text = pathlib.Path(__file__).read_text(encoding="utf-8")
    offenders = [(n, hex(ord(c))) for n, line in enumerate(text.split("\n"), 1)
                 for c in line if ord(c) > 127]
    assert offenders == []
