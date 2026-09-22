"""Tests for classifier_eval.py - the shadow-log report comparing the regex and Jev per site."""
import json

import pytest

import classifier_eval as ce


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
    assert ce.SITE_THRESHOLDS["skill_router"] == 0.7


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
