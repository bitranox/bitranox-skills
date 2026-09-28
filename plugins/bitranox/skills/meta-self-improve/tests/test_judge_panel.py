"""Tests for judge_panel.py - the blind judge packet and the harvest of its verdicts."""
import json

import pytest

import classifier_eval as ce
import judge_panel as jp


def _choice(winner, probs):
    return {"type": "choice", "value": winner, "probabilities": probs, "confidence": None}


def replay_row(uuid, prompt, arms, keywords=(), source="t.jsonl"):
    return {"uuid": uuid, "source": source, "line": 1, "keyword_picks": list(keywords),
            "state": {"user_prompt": prompt, "project": "demo"}, "arms": arms}


def arm(winner=None, probs=None, picks=(), gate=0.6, rerank_winner=None):
    out = {"answered": True, "gate": gate, "picks": list(picks), "winner": winner,
           "probabilities": probs or {}}
    if rerank_winner:
        out["rerank_winner"] = rerank_winner
    return out


def live_row(prompt, selected, winner, probs, gate, session="s1", ts="2026-09-28T10:00:00+00:00",
             path="t.jsonl", offset=10, decide_path="jev"):
    return {"ts": ts, "site": "skill_router", "session_id": session,
            "regex": {"selected": list(selected)}, "decide_path": decide_path,
            "results": [{"answers": {"_new_task": {"type": "noul", "value": gate},
                                     "_pick": _choice(winner, probs)}}],
            "states": [{"user_prompt": prompt, "project": "demo"}],
            "transcript_path": path, "transcript_offset": offset}


# ---- pooling -------------------------------------------------------------------------------

def test_a_replay_row_pools_every_arm_winner_alternative_pick_and_keyword():
    row = replay_row("u1", "reformat the table", {
        "choice_full": arm("docs-md-table-formatting",
                           {"docs-md-table-formatting": 0.8, "files-edit-json": 0.1,
                            "none_needed": 0.05, "compuse-bash": 0.03, "infra-proxmox": 0.02}),
        "rerank": arm(rerank_winner="write-humanize-en")}, keywords=["compuse-git"])
    pooled, skipped = jp.pool([("run.jsonl", [row])], alternatives=2)
    assert skipped == []
    cands = pooled["u1"]["candidates"]
    # --alternatives counts runners-up AFTER the winner: 2 here is files-edit-json, compuse-bash.
    assert set(cands) == {"docs-md-table-formatting", "files-edit-json", "compuse-bash",
                          "write-humanize-en", "compuse-git"}
    assert "none_needed" not in cands
    assert "run.jsonl:choice_full:winner" in cands["docs-md-table-formatting"]
    assert cands["compuse-git"] == ["run.jsonl:keywords"]


def test_rows_sharing_a_uuid_across_logs_pool_into_one_item():
    a = replay_row("u1", "same prompt", {"choice_full": arm("files-edit-xml", {})})
    b = replay_row("u1", "same prompt", {"choice_full": arm("files-edit-yml", {})})
    pooled, _ = jp.pool([("A.jsonl", [a]), ("B.jsonl", [b])], alternatives=0)
    assert list(pooled) == ["u1"]
    assert set(pooled["u1"]["candidates"]) == {"files-edit-xml", "files-edit-yml"}


def test_one_uuid_carrying_two_different_prompts_is_refused():
    a = replay_row("u1", "first text", {})
    b = replay_row("u1", "second text", {})
    with pytest.raises(ValueError, match="u1"):
        jp.pool([("A.jsonl", [a]), ("B.jsonl", [b])], alternatives=0)


def test_a_live_row_is_keyed_by_its_located_prompt_uuid_and_records_its_scores():
    row = live_row("check the pools", ["compuse-bash"], "infra-storage-check-zpools",
                   {"infra-storage-check-zpools": 0.9, "infra-proxmox": 0.05}, gate=0.31)
    pooled, skipped = jp.pool([("day.jsonl", [row])], alternatives=1, locate=lambda r: "p7")
    assert skipped == []
    item = pooled["p7"]
    assert set(item["candidates"]) == {"compuse-bash", "infra-storage-check-zpools",
                                       "infra-proxmox"}
    [origin] = item["origins"]
    assert origin["gate"] == 0.31 and origin["winner"] == "infra-storage-check-zpools"
    assert origin["winner_p"] == 0.9 and origin["decide_path"] == "jev"


def test_a_live_row_whose_prompt_cannot_be_located_is_skipped_and_reported():
    row = live_row("gone", [], "none_needed", {}, gate=0.1)
    pooled, skipped = jp.pool([("day.jsonl", [row])], alternatives=1, locate=lambda r: None)
    assert pooled == {}
    assert len(skipped) == 1 and "locate" in skipped[0]["reason"]


def test_the_real_locator_joins_a_live_row_to_its_transcript_prompt(tmp_path):
    t = tmp_path / "t.jsonl"
    rec = {"type": "user", "uuid": "p1", "origin": {"kind": "human"},
           "message": {"content": "check the pools"}}
    data = (json.dumps(rec) + "\n").encode("utf-8")
    t.write_bytes(data)
    row = live_row("check the pools", [], "none_needed", {}, gate=0.1, path=str(t),
                   offset=len(data))
    pooled, skipped = jp.pool([("day.jsonl", [row])], alternatives=0, locate=ce.locate_prompt)
    assert list(pooled) == ["p1"] and skipped == []


def test_rows_of_other_sites_are_ignored_not_reported_as_skipped():
    # The audit directory holds every site's rows; reporting 531 stop/recall rows as "skipped"
    # buried the router rows that genuinely could not be judged.
    other = {"site": "stop_signal", "results": [{}], "states": [{"user_message": "x"}]}
    unanswered = {**live_row("p", [], "none_needed", {}, 0.1), "results": []}
    _pooled, skipped = jp.pool([("d.jsonl", [other, unanswered])], alternatives=0,
                               locate=lambda r: "p1")
    assert [s["index"] for s in skipped] == [1]


def test_an_always_skill_joins_every_item():
    rows = [replay_row("u1", "a", {}), replay_row("u2", "b", {})]
    pooled, _ = jp.pool([("r.jsonl", rows)], alternatives=0, always=["meta-context-watcher"])
    assert all("meta-context-watcher" in it["candidates"] for it in pooled.values())


# ---- sampling ------------------------------------------------------------------------------

def test_sample_caps_items_per_session_and_in_total_and_is_repeatable():
    rows = [live_row("p%d" % i, [], "none_needed", {}, 0.1, session="s%d" % (i % 2))
            for i in range(10)]
    pooled, _ = jp.pool([("d.jsonl", rows)], alternatives=0,
                        locate=lambda r: r["states"][0]["user_prompt"])
    one = jp.sample(pooled, per_session=2, limit=3, seed=5)
    two = jp.sample(pooled, per_session=2, limit=3, seed=5)
    assert list(one) == list(two) and len(one) == 3
    sessions = [it["session_id"] for it in one.values()]
    assert max(sessions.count(s) for s in set(sessions)) <= 2


# ---- the packet ----------------------------------------------------------------------------

def _two_items():
    rows = [replay_row("u1", "reformat the table",
                       {"choice_full": arm("docs-md-table-formatting", {})},
                       keywords=["compuse-git"]),
            replay_row("u2", "go ahead", {"choice_full": arm("none_needed", {})})]
    pooled, _ = jp.pool([("run.jsonl", rows)], alternatives=0)
    return pooled


DESCS = {"docs-md-table-formatting": "Use when a markdown table is misaligned",
         "compuse-git": "Use when running git"}


def test_every_packet_holds_every_item_once_in_its_own_order():
    built = jp.build_packet(_two_items(), descriptions=DESCS, all_names=sorted(DESCS),
                            judges=5, seed=3)
    assert len(built["packets"]) == 5
    orders = set()
    for text in built["packets"]:
        ids = [line[4:-4] for line in text.splitlines() if line.startswith("=== ")]
        assert sorted(ids) == sorted(built["items"])
        orders.add(tuple(ids))
    assert len(orders) > 1


def test_a_packet_names_no_arm_origin_or_score():
    built = jp.build_packet(_two_items(), descriptions=DESCS, all_names=sorted(DESCS),
                            judges=2, seed=0)
    for text in built["packets"]:
        for leak in ("choice_full", "keywords", "run.jsonl", "winner", "u1"):
            assert leak not in text


def test_the_key_maps_each_item_to_its_uuid_and_origins():
    built = jp.build_packet(_two_items(), descriptions=DESCS, all_names=sorted(DESCS),
                            judges=1, seed=0)
    uuids = {k["uuid"] for k in built["key"].values()}
    assert uuids == {"u1", "u2"}
    item = next(i for i, k in built["key"].items() if k["uuid"] == "u1")
    assert built["key"][item]["candidates"]["compuse-git"] == ["run.jsonl:keywords"]


def test_an_override_replaces_the_description_under_test_everywhere():
    built = jp.build_packet(_two_items(), descriptions=DESCS, all_names=sorted(DESCS),
                            overrides={"docs-md-table-formatting": "NEUTRAL SUMMARY"},
                            judges=2, seed=0)
    for text in built["packets"]:
        assert "NEUTRAL SUMMARY" in text
        assert "misaligned" not in text


def test_a_long_prompt_keeps_its_head_and_tail():
    rows = [replay_row("u1", "HEAD " + "x" * 5000 + " TAIL", {})]
    pooled, _ = jp.pool([("r.jsonl", rows)], alternatives=0)
    built = jp.build_packet(pooled, descriptions={}, all_names=[], judges=1, seed=0)
    prompt = next(iter(built["items"].values()))["user_prompt"]
    assert prompt.startswith("HEAD") and prompt.endswith("TAIL") and len(prompt) < 3000


# ---- harvest -------------------------------------------------------------------------------

def _transcript(path, records):
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


def _says(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_extract_takes_the_last_verdict_object_an_assistant_wrote(tmp_path):
    early = {"i000": {"needs_skill": False, "verdicts": {}, "better": None}}
    late = {"i000": {"needs_skill": True, "verdicts": {}, "better": "x"},
            "i001": {"needs_skill": False, "verdicts": {}, "better": None}}
    t = _transcript(tmp_path / "j.jsonl", [
        {"type": "user", "message": {"content": json.dumps(late) + " ignore me"}},
        _says("draft " + json.dumps(early)),
        _says("Final answer:\n" + json.dumps(late, indent=1) + "\ndone")])
    assert jp.extract_panel(t, {"i000", "i001"}) == late


def test_extract_reads_a_verdict_handed_back_through_a_tool_call(tmp_path):
    obj = {"i000": {"needs_skill": True, "verdicts": {}, "better": None}}
    t = _transcript(tmp_path / "j.jsonl", [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "SendMessage",
             "input": {"to": "main", "message": json.dumps(obj)}}]}}])
    assert jp.extract_panel(t, {"i000"}) == obj


def test_extract_ignores_the_packet_echoed_in_a_user_record(tmp_path):
    obj = {"i000": {"needs_skill": True, "verdicts": {}, "better": None}}
    t = _transcript(tmp_path / "j.jsonl",
                    [{"type": "user", "message": {"content": json.dumps(obj)}}])
    assert jp.extract_panel(t, {"i000"}) is None


KEY = {"i000": {"uuid": "u1", "candidates": {"a": ["r:keywords"], "b": ["r:x:winner"]}},
       "i001": {"uuid": "u2", "candidates": {}}}


def _panel(need0, a, b, need1=False, better=None):
    return {"i000": {"needs_skill": need0, "verdicts": {"a": a, "b": b}, "better": better},
            "i001": {"needs_skill": need1, "verdicts": {}, "better": None}}


def test_harvest_takes_the_majority_per_verdict_and_keys_labels_by_uuid():
    panels = [_panel(True, "right", "wrong"), _panel(True, "right", "wrong"),
              _panel(True, "defensible", "wrong")]
    out = jp.harvest(KEY, panels)
    assert set(out["labels"]) == {"u1", "u2"}
    lab = out["labels"]["u1"]
    assert lab["needs_skill"] is True and lab["verdicts"] == {"a": "right", "b": "wrong"}
    assert lab["should_pick"] == ["a"] and lab["item"] == "i000"
    assert ("u1", "a", {"right": 2, "defensible": 1}) in [
        (s["uuid"], s["candidate"], s["votes"]) for s in out["splits"]]


def test_a_tied_verdict_is_left_unresolved_and_listed():
    panels = [_panel(True, "right", "wrong"), _panel(True, "right", "wrong"),
              _panel(True, "wrong", "wrong"), _panel(True, "wrong", "wrong")]
    out = jp.harvest(KEY, panels)
    assert out["labels"]["u1"]["verdicts"]["a"] is None
    assert any(s["candidate"] == "a" and s["unresolved"] for s in out["splits"])


def test_should_pick_is_empty_when_the_majority_says_no_skill_is_needed():
    panels = [_panel(False, "right", "wrong")] * 3
    assert jp.harvest(KEY, panels)["labels"]["u1"]["should_pick"] == []


def test_better_names_are_counted():
    panels = [_panel(True, "wrong", "wrong", better=b) for b in ("c", "c", "d")]
    assert jp.harvest(KEY, panels)["labels"]["u1"]["better"] == [["c", 2], ["d", 1]]


def test_a_missing_item_or_an_invalid_verdict_is_reported_not_counted():
    partial = {"i000": {"needs_skill": True, "verdicts": {"a": "great", "b": "wrong"},
                        "better": None}}
    panels = [_panel(True, "right", "wrong"), partial]
    out = jp.harvest(KEY, panels)
    assert out["unjudged"] == [{"judge": 1, "item": "i001"}]
    assert out["invalid"] == [{"judge": 1, "item": "i000", "candidate": "a", "value": "great"}]
    assert out["labels"]["u1"]["votes"]["a"] == {"right": 1}


# ---- the CLI -------------------------------------------------------------------------------

def test_cli_packet_then_harvest_round_trip(tmp_path, capsys):
    log = tmp_path / "run.jsonl"
    rows = [replay_row("u1", "reformat the table",
                       {"choice_full": arm("docs-md-table-formatting", {})}),
            replay_row("u2", "go ahead", {"choice_full": arm("none_needed", {})})]
    log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    out = tmp_path / "panel"
    assert ce.main(["packet", "--from", str(log), "--out", str(out), "--judges", "3",
                    "--json"], skills={"docs-md-table-formatting": "tables"}) == 0
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    assert len(list(out.glob("packet-*.txt"))) == 3
    verdicts = {i: {"needs_skill": bool(k["candidates"]),
                    "verdicts": {c: "right" for c in k["candidates"]}, "better": None}
                for i, k in key.items()}
    judges = [_transcript(tmp_path / ("j%d.jsonl" % n), [_says(json.dumps(verdicts))])
              for n in range(3)]
    capsys.readouterr()
    args = ["harvest", "--key", str(out / "key.json"), "--out", str(out / "labels.json"), "--json"]
    for j in judges:
        args += ["--transcript", str(j)]
    assert ce.main(args) == 0
    labels = json.loads((out / "labels.json").read_text(encoding="utf-8"))
    assert labels["u1"]["should_pick"] == ["docs-md-table-formatting"]
    assert labels["u2"]["needs_skill"] is False


def test_cli_harvest_exits_1_when_a_transcript_holds_no_verdicts(tmp_path, capsys):
    key = tmp_path / "key.json"
    key.write_text(json.dumps(KEY), encoding="utf-8")
    empty = _transcript(tmp_path / "j.jsonl", [_says("I could not do it")])
    assert ce.main(["harvest", "--key", str(key), "--transcript", str(empty),
                    "--out", str(tmp_path / "l.json"), "--json"]) == 1
    assert not (tmp_path / "l.json").exists()


def test_cli_packet_refuses_an_out_dir_that_already_holds_a_key(tmp_path, capsys):
    log = tmp_path / "run.jsonl"
    log.write_text(json.dumps(replay_row("u1", "a", {})) + "\n", encoding="utf-8")
    out = tmp_path / "panel"
    out.mkdir()
    (out / "key.json").write_text("{}", encoding="utf-8")
    assert ce.main(["packet", "--from", str(log), "--out", str(out), "--json"], skills={}) == 2
    assert (out / "key.json").read_text(encoding="utf-8") == "{}"


def test_cli_packet_since_drops_older_shadow_rows(tmp_path, capsys):
    t = tmp_path / "t.jsonl"
    recs = [{"type": "user", "uuid": u, "origin": {"kind": "human"},
             "message": {"content": text}} for u, text in (("p1", "old ask"), ("p2", "new ask"))]
    data = "".join(json.dumps(r) + "\n" for r in recs).encode("utf-8")
    t.write_bytes(data)
    rows = [live_row("old ask", [], "none_needed", {}, 0.1, ts="2026-09-27T10:00:00+00:00",
                     path=str(t), offset=len(data)),
            live_row("new ask", [], "none_needed", {}, 0.1, ts="2026-09-28T10:00:00+00:00",
                     path=str(t), offset=len(data))]
    log = tmp_path / "day.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    out = tmp_path / "panel"
    assert ce.main(["packet", "--from", str(log), "--out", str(out), "--since",
                    "2026-09-28T00:00:00", "--json"], skills={}) == 0
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    assert [k["uuid"] for k in key.values()] == ["p2"]
    assert json.loads((out / "skipped.json").read_text(encoding="utf-8")) == []


def test_cli_packet_names_why_each_live_row_could_not_be_located(tmp_path, capsys):
    # A scheduled (CronCreate / ScheduleWakeup) fire is written as an isMeta record with
    # promptSource "system" - no typed prompt to join, and not the same thing as a transcript that
    # is gone. Both used to share one reason, so the scheduled share had to be counted by hand.
    t = tmp_path / "t.jsonl"
    recs = [{"type": "user", "uuid": "p1", "origin": {"kind": "human"},
             "message": {"content": "typed ask"}},
            {"type": "user", "uuid": "p2", "isMeta": True, "promptSource": "system",
             "scheduledTaskId": "e4ce11db", "message": {"content": "cron tick: check CI"}}]
    data = "".join(json.dumps(r) + "\n" for r in recs).encode("utf-8")
    t.write_bytes(data)
    rows = [live_row("typed ask", [], "none_needed", {}, 0.1, path=str(t), offset=len(data)),
            live_row("cron tick: check CI", [], "none_needed", {}, 0.1, path=str(t),
                     offset=len(data)),
            live_row("lost ask", [], "none_needed", {}, 0.1, path=str(tmp_path / "gone.jsonl"),
                     offset=10),
            live_row("never written", [], "none_needed", {}, 0.1, path=str(t), offset=len(data))]
    log = tmp_path / "day.jsonl"
    log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    out = tmp_path / "panel"
    assert ce.main(["packet", "--from", str(log), "--out", str(out), "--json"], skills={}) == 0
    reasons = [s["reason"] for s in json.loads((out / "skipped.json").read_text(encoding="utf-8"))]
    assert reasons == [ce.UNLOCATED_SCHEDULED, ce.UNLOCATED_GONE, ce.UNLOCATED_NOT_FOUND]
    assert len(set(reasons)) == 3
