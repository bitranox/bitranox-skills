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
