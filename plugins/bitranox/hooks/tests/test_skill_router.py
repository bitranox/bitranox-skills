"""Tests for build_skill_triggers.py + skill-router.py. ASCII."""
import io
import json
import sys

import pytest

import build_skill_triggers as B
import skill_router as R


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _skill(root, name, desc):
    d = root / name
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: %s\ndescription: %s\n---\n\n# x\n" % (name, desc),
                                encoding="utf-8")


def test_build_derives_keywords_from_descriptions(tmp_path):
    _skill(tmp_path, "frobnicate", "Use when frobnicating widgets fails with gasket errors")
    _skill(tmp_path, "nodesc", "Use when it is")            # too few keywords -> skipped
    m = B.build(tmp_path)
    assert "frobnicate" in m and "frobnicating" in m["frobnicate"] and "gasket" in m["frobnicate"]
    assert "nodesc" not in m


def test_build_check_detects_stale_map(tmp_path):
    _skill(tmp_path, "alpha", "Use when alpha widgets explode under pressure loads")
    out = tmp_path / "map.json"
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out)]) == 0
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out), "--check"]) == 0
    _skill(tmp_path, "beta", "Use when beta gadgets rust in coastal climates")
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out), "--check"]) == 1


def test_build_check_says_missing_for_a_map_that_does_not_exist(tmp_path, capsys):
    """A missing map read "STALE - run build_skill_triggers.py", which sends the reader to
    regenerate a file that was never there (a wrong --out, a run outside the repo)."""
    _skill(tmp_path, "alpha", "Use when alpha widgets explode under pressure loads")
    out = tmp_path / "nowhere" / "map.json"
    # Could not compare (exit 2), which is not "stale" (exit 1).
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out), "--check"]) == 2
    err = capsys.readouterr().err
    assert "missing" in err and str(out) in err and "STALE" not in err


def test_build_with_a_skills_dir_that_does_not_exist_exits_2_and_writes_nothing(tmp_path):
    out = tmp_path / "map.json"
    assert B.main(["--skills-dir", str(tmp_path / "nope"), "--out", str(out)]) == 2
    assert not out.exists()


def test_build_with_an_unwritable_out_exits_2(tmp_path):
    _skill(tmp_path, "alpha", "Use when alpha widgets explode under pressure loads")
    out = tmp_path / "isdir"
    out.mkdir()
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out)]) == 2


def test_build_check_of_a_non_utf8_map_exits_2(tmp_path):
    _skill(tmp_path, "alpha", "Use when alpha widgets explode under pressure loads")
    out = tmp_path / "map.json"
    out.write_bytes(b"\xff\xfe")
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out), "--check"]) == 2


def test_build_check_still_says_stale_for_an_outdated_map(tmp_path, capsys):
    """Control for the test above."""
    _skill(tmp_path, "alpha", "Use when alpha widgets explode under pressure loads")
    out = tmp_path / "map.json"
    out.write_text("{}\n", encoding="utf-8")
    assert B.main(["--skills-dir", str(tmp_path), "--out", str(out), "--check"]) == 1
    assert "STALE" in capsys.readouterr().err


def test_build_keeps_comment_and_key_words_out_of_the_map(tmp_path):
    """A `# comment` line or a `version2:` key after the description was swallowed into it, so its
    words became router keywords; the commit gate passed both."""
    d = tmp_path / "alpha"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Use when alpha widgets explode under pressure loads\n"
        "# todo reword before release\nversion2: tokenleaks intoprose\n---\n", encoding="utf-8")
    words = set(B.build(tmp_path)["alpha"])
    assert {"widgets", "explode"} <= words
    assert not words & {"todo", "reword", "release", "version2", "tokenleaks", "intoprose"}


def test_build_includes_a_skill_md_written_with_a_bom(tmp_path):
    d = tmp_path / "alpha"
    d.mkdir()
    (d / "SKILL.md").write_bytes(
        b"\xef\xbb\xbf---\nname: alpha\ndescription: Use when alpha widgets explode under "
        b"pressure loads\n---\n")
    assert "alpha" in B.build(tmp_path)


# ---- the 14 head keywords crowd out the strings a user in trouble types verbatim -----------------
# A description is trigger-first, so its head is prose about the SITUATION and its tail holds the
# literal error codes and messages. Taking the first 14 by position therefore keeps generic words
# and drops the identifiers - measured across 80 shipped skills, `code` (shared by 14 of them)
# reaches the map while `0xc1900200`, `windows.old` and `rueckgaengig` do not.

def test_distinctive_admits_identifiers():
    for tok in ("0xc1900200", "setup.exe", "windows.old", "in-place", "non-constant-time", "utf-8"):
        assert B.distinctive(tok), tok


def test_distinctive_rejects_plain_words_however_long():
    # A length bar cannot separate these: `condition` and `description` are ordinary English and
    # ordinary in prompts (33 and 50 of 2146), and admitting them put coding-rust on a prompt about
    # reviewing skills. Only the identifier shape has zero such tokens.
    for tok in ("line", "report", "main", "sleep", "itself", "denied",
                "condition", "description", "interface", "documentation"):
        assert not B.distinctive(tok), tok


def test_select_keeps_the_head_in_order():
    toks = ["kw%02d" % i for i in range(20)]
    assert B.select(toks, {t: 1 for t in toks})[:14] == toks[:14]


def test_select_appends_a_unique_identifier_from_the_tail():
    toks = ["a%d" % i for i in range(14)] + ["0xc1900200"]
    got = B.select(toks, {t: 1 for t in toks})
    assert "0xc1900200" in got


def test_select_does_not_append_a_plain_tail_word():
    toks = ["a%d" % i for i in range(14)] + ["itself"]
    assert "itself" not in B.select(toks, {t: 1 for t in toks})


def test_select_does_not_append_a_token_another_skill_also_claims():
    # a shared token cannot discriminate, and it is what lets one skill out-count the rest
    toks = ["a%d" % i for i in range(14)] + ["0xc1900200"]
    assert "0xc1900200" not in B.select(toks, {"0xc1900200": 2})


def test_select_bounds_how_many_it_appends():
    tail = ["0xdead%04d" % i for i in range(30)]
    toks = ["a%d" % i for i in range(14)] + tail
    got = B.select(toks, {t: 1 for t in toks})
    assert len(got) == 24                       # 14 head + at most 10 appended


def test_build_lands_a_tail_error_code_in_the_map(tmp_path):
    _skill(tmp_path, "servicing", "Use when a Windows machine will not install a cumulative update, "
                                  "its component store is damaged, DISM fails with an opaque code "
                                  "and setup exits 0xc1900200 on the apply reboot")
    m = B.build(tmp_path)
    assert "0xc1900200" in m["servicing"]


def test_match_needs_two_distinct_hits_word_boundary():
    triggers = {"frob": ["frobnicating", "widgets", "gasket"]}
    assert R.match("my frobnicating widgets are broken", triggers) == [("frob", 2)]
    assert R.match("just one widgets mention", triggers) == []            # 1 hit < MIN_HITS
    assert R.match("megawidgetsx frobnicatingly", triggers) == []         # boundary: no substring hits


def test_router_injects_once_per_session(monkeypatch, capsys):
    trig = {"frob": ["frobnicating", "widgets"]}
    monkeypatch.setattr(R, "load_triggers", lambda: trig)

    def run(prompt, sid="s1"):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
            {"prompt": prompt, "cwd": "/p/x", "session_id": sid})))
        rc = R.main()
        return rc, capsys.readouterr().out

    rc, out = run("frobnicating the widgets broke")
    assert rc == 0 and "bitranox:frob" in out and "Skill tool" in out
    rc, out = run("frobnicating the widgets again")
    assert rc == 0 and out == ""                       # per-session dedup: nudged once
    rc, out = run("frobnicating the widgets anew", sid="s2")
    assert "bitranox:frob" in out                      # a new session nudges again


def test_router_silent_on_no_match(monkeypatch, capsys):
    monkeypatch.setattr(R, "load_triggers", lambda: {"frob": ["frobnicating", "widgets"]})
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"prompt": "completely unrelated question", "cwd": "/p/x", "session_id": "s"})))
    assert R.main() == 0 and capsys.readouterr().out == ""


# ---- the prompt a keyword matcher may score ------------------------------------------------------
# Measured 2026-09-22: a 409-char <task-notification> envelope reached the 2-keyword threshold for
# ELEVEN skills, the words coming from the envelope's own vocabulary and from its output-file PATH.
# The nudge is false by construction, and because a skill nudges at most once per session, each
# such match silences that skill for the prompt where it would have been right.

def test_match_scores_nothing_in_a_machine_generated_turn():
    triggers = {"frob": ["frobnicating", "widgets"]}
    assert R.match("<task-notification>frobnicating widgets done</task-notification>",
                   triggers) == []
    assert R.match("<command-name>/frobnicating-widgets</command-name>", triggers) == []


def test_match_does_not_score_words_inside_a_path():
    triggers = {"frob": ["frobnicating", "widgets"]}
    assert R.match("look at /tmp/frobnicating/widgets/out.txt", triggers) == []
    # the same two words as prose still match, so the guard removed a path and not the signal
    assert R.match("look at the frobnicating widgets", triggers) == [("frob", 2)]


def test_a_notification_does_not_spend_the_once_per_session_nudge(monkeypatch, capsys):
    trig = {"frob": ["frobnicating", "widgets"]}
    monkeypatch.setattr(R, "load_triggers", lambda: trig)

    def run(prompt):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
            {"prompt": prompt, "cwd": "/p/x", "session_id": "s1"})))
        rc = R.main()
        return rc, capsys.readouterr().out

    rc, out = run("<task-notification>done: /tmp/frobnicating/widgets/a.output</task-notification>")
    assert rc == 0 and out == ""                        # no false nudge on a machine status line
    rc, out = run("the frobnicating widgets broke")
    assert "bitranox:frob" in out                       # and the budget was still there to spend


def test_shipped_trigger_map_in_sync_with_descriptions():
    # the committed map must match the skills' current descriptions (rebuild on description change)
    import build_skill_triggers as B2
    assert B2.main(["--check"]) == 0


# ---- a compound keyword and its component ---------------------------------------------------------
# Both count on one token, so one distinctive identifier clears MIN_HITS by itself. Counting the
# token once was measured on 1,311 real typed prompts: it removed no false nudge and dropped real
# ones, so the double count is the intended behaviour and is pinned here.

def test_match_counts_a_compound_keyword_and_its_component_on_one_token():
    triggers = {"lc": ["config", "lib_layered_config", "profiles"]}
    assert R.match("do we have lib_layered_config implemented here ?", triggers) == [("lc", 2)]


def test_match_a_duplicated_keyword_counts_once():
    assert R.match("widgets widgets", {"w": ["widgets", "widgets"]}) == []


# ---- word boundaries in any script -----------------------------------------------------------------
# The boundary class was ASCII [a-z0-9], so an umlaut counted as a word break and a German compound
# (Fileuebersicht with a real u-umlaut) matched "file". Letters and digits of any script are word
# characters now, the same rule gather_scan.scan uses.

def test_match_does_not_split_a_german_compound_at_an_umlaut():
    triggers = {"fx": ["file", "code"]}
    assert R.match("die File\u00fcbersicht und der Code\u00fcberblick sind falsch", triggers) == []


def test_match_control_the_separate_words_still_match():
    triggers = {"fx": ["file", "code"]}
    assert R.match("das file und der code sind falsch", triggers) == [("fx", 2)]
    assert R.match("the file_path and code-base", triggers) == [("fx", 2)]   # _ and - separate


# ---- ranking: top MAX_SKILLS, ties alphabetical ----------------------------------------------------

def test_match_keeps_the_top_two_and_breaks_ties_alphabetically():
    triggers = {"zeta": ["alpha", "beta"], "alef": ["alpha", "beta"],
                "most": ["alpha", "beta", "gamma"], "weak": ["gamma", "delta-x"]}
    assert R.match("alpha beta gamma", triggers) == [("most", 3), ("alef", 2)]
    assert R.match("alpha beta gamma", triggers, max_skills=None) == [
        ("most", 3), ("alef", 2), ("zeta", 2)]


# ---- the per-session dedup runs BEFORE the cap -----------------------------------------------------
# The cap was applied first, so two skills already nudged held both slots and a third skill that
# matched this prompt was never nudged in the session.

def _run_main(monkeypatch, capsys, prompt, sid="s1", cwd="/p/x"):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"prompt": prompt, "cwd": cwd, "session_id": sid})))
    rc = R.main()
    return rc, capsys.readouterr().out


def test_already_nudged_skills_do_not_hold_the_slots_of_a_fresh_match(monkeypatch, capsys):
    trig = {"aa": ["alpha", "beta", "gamma"], "bb": ["alpha", "beta", "gamma"],
            "cc": ["alpha", "beta"]}
    monkeypatch.setattr(R, "load_triggers", lambda: trig)
    rc, out = _run_main(monkeypatch, capsys, "alpha beta gamma")
    assert rc == 0 and "bitranox:aa" in out and "bitranox:bb" in out and "bitranox:cc" not in out
    rc, out = _run_main(monkeypatch, capsys, "alpha beta gamma again")
    assert rc == 0 and "bitranox:cc" in out
    assert "bitranox:aa" not in out and "bitranox:bb" not in out


def test_control_a_fresh_session_still_gets_the_top_two(monkeypatch, capsys):
    trig = {"aa": ["alpha", "beta", "gamma"], "bb": ["alpha", "beta", "gamma"],
            "cc": ["alpha", "beta"]}
    monkeypatch.setattr(R, "load_triggers", lambda: trig)
    _run_main(monkeypatch, capsys, "alpha beta gamma")
    rc, out = _run_main(monkeypatch, capsys, "alpha beta gamma", sid="s2")
    assert "bitranox:aa" in out and "bitranox:bb" in out and "bitranox:cc" not in out


# ---- side branches of main() -----------------------------------------------------------------------

def test_router_exits_zero_on_malformed_stdin(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("{not json"))
    assert R.main() == 0 and capsys.readouterr().out == ""


def test_router_exits_zero_on_an_empty_prompt(monkeypatch, capsys):
    monkeypatch.setattr(R, "load_triggers", lambda: {"frob": ["frobnicating", "widgets"]})
    rc, out = _run_main(monkeypatch, capsys, "   ")
    assert rc == 0 and out == ""


def test_router_survives_a_state_path_it_cannot_read(monkeypatch, capsys):
    monkeypatch.setattr(R, "load_triggers", lambda: {"frob": ["frobnicating", "widgets"]})
    R._state_file("/p/x", "s1").mkdir(parents=True)      # a directory where the file should be
    rc, out = _run_main(monkeypatch, capsys, "frobnicating the widgets")
    assert rc == 0 and out == ""


def test_a_state_file_with_undecodable_bytes_does_not_silence_the_router(monkeypatch, capsys):
    monkeypatch.setattr(R, "load_triggers", lambda: {"frob": ["frobnicating", "widgets"],
                                                     "done": ["frobnicating", "widgets"]})
    state = R._state_file("/p/x", "s1")
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_bytes(b"\xff\xfe junk\nbitranox:done\n")
    rc, out = _run_main(monkeypatch, capsys, "frobnicating the widgets")
    assert rc == 0 and "bitranox:frob" in out and "bitranox:done" not in out


# ---- concrete routing on the SHIPPED trigger map ---------------------------------------------------
# These run the real skill_triggers.json through match(), so a matcher change that re-opens a known
# false positive fails here rather than only in a replay.

def test_shipped_map_routes_a_lone_distinctive_identifier_to_its_skill():
    triggers = R.load_triggers()
    assert triggers                                      # the shipped map loaded
    picked = [s for s, _n in R.match("do we have lib_layered_config implemented here ?", triggers)]
    assert picked == ["coding-python-layered-config"]


def test_shipped_map_does_not_route_plain_prose_with_one_keyword():
    assert R.match("what time is it in the other office", R.load_triggers()) == []


def test_shipped_map_does_not_route_german_umlaut_compounds():
    triggers = R.load_triggers()
    assert R.match("die File\u00fcbersicht und der Code\u00fcberblick sind falsch", triggers) == []


def test_shipped_map_control_routes_a_real_json_editing_prompt():
    triggers = R.load_triggers()
    picked = [s for s, _n in R.match("editing package.json and validating the json file", triggers)]
    assert picked and picked[0] == "files-edit-json"


# ---- a scheduled prompt is not somebody asking ---------------------------------------------------
# Same input defect as recall: a CronCreate/ScheduleWakeup fire has a typed prompt's payload, and
# decide mode, the shadow and the keyword nudge all acted on it. Identical triggers in both arms.

def _scheduling_transcript(tmp_path, prompt):
    call = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "toolu_01", "name": "ScheduleWakeup",
         "input": {"delaySeconds": 600, "prompt": prompt, "reason": "watching CI"}}]}}
    t = tmp_path / "session.jsonl"
    t.write_text(json.dumps(call) + "\n", encoding="utf-8")
    return str(t)


def _run_with_transcript(monkeypatch, capsys, prompt, transcript):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"prompt": prompt, "cwd": "/p/x", "session_id": "s1", "transcript_path": transcript})))
    rc = R.main()
    return rc, capsys.readouterr().out


def test_a_scheduled_prompt_is_not_routed(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(R, "load_triggers", lambda: {"aa": ["alpha", "beta"]})
    rc, out = _run_with_transcript(monkeypatch, capsys, "alpha beta check",
                                   _scheduling_transcript(tmp_path, "alpha beta check"))
    assert rc == 0 and out == ""


def test_control_the_same_prompt_typed_is_routed(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(R, "load_triggers", lambda: {"aa": ["alpha", "beta"]})
    rc, out = _run_with_transcript(monkeypatch, capsys, "alpha beta check",
                                   _scheduling_transcript(tmp_path, "something else"))
    assert rc == 0 and "bitranox:aa" in out
