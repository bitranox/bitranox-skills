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
    shapes = {}
    for name in ce.ARMS:
        ask = FakeAsk([answer, answer])
        ce.run_arm(name, ask, {"user_prompt": "p"}, SKILLS, threshold=0.7)
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


def test_a_gate_below_threshold_suppresses_every_arm():
    # A continuation is 595 of the 1,409 typed prompts in the corpus, so this is the common case.
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
        monkeypatch, capsys):
    # The exception existing is not the guarantee; the EXIT CODE is, because that is what a
    # caller keys on. Exit 3 means the instrument is wrong, which is not the same as exit 1
    # (nothing to report) or exit 2 (bad usage), and collapsing it into either would let a run
    # that measured nothing read as a run that found nothing.
    def boom(_args):
        raise ce.ControlFailed("planted negative named a skill")

    monkeypatch.setattr(ce, "_run_replay", boom)
    rc = ce.main(["replay", "--json"])
    env = json.loads(capsys.readouterr().out)
    assert rc == 3
    assert env["ok"] is False and "planted negative" in env["error"]


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
