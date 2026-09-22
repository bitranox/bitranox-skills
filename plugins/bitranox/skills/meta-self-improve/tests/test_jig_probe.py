"""Tests for jig_probe.py - the offline question 'would Jev have pointed at a jig here?'. ASCII."""
import json

import pytest

import jig_probe as jp


class _Ans:
    def __init__(self, type_, value):
        self.type, self.value = type_, value


class _Res:
    def __init__(self, answers):
        self.answers, self.latency_ms, self.input_tokens = answers, 10, 100


@pytest.fixture
def fake_answers():
    """A classifier substituted at the real seam: it answers like the API, from a dict or from a
    callable given the state, so nothing here patches jig_probe's internals."""
    def make(spec):
        class _Fake:
            last_reason = None
            key = "k" * 20

            def ask(self, state, questions):
                values = spec(state) if callable(spec) else spec
                return _Res({q.id: _Ans(q.type, values[q.id]) for q in questions
                             if q.id in values})
        return _Fake()
    return make


def _script(d, name, doc):
    d.mkdir(parents=True, exist_ok=True)
    (d / (name + ".py")).write_text('"""%s"""\n\nx = 1\n' % doc, encoding="utf-8")


# ---- the catalogue the choice question is built from ----------------------------------------

def test_catalogue_takes_each_jig_s_first_sentence(tmp_path):
    _script(tmp_path, "procsig", "Find or signal a process by exe, comm or pidfile.\n\nMore prose.")
    _script(tmp_path, "newest", "Pick the newest file by mtime. Never by name, which sorts wrong.")
    cat = jp.jig_catalogue(tmp_path)
    assert cat["procsig"] == "Find or signal a process by exe, comm or pidfile."
    assert cat["newest"] == "Pick the newest file by mtime."


def test_catalogue_skips_a_script_with_no_docstring(tmp_path):
    _script(tmp_path, "good", "Does a thing.")
    (tmp_path / "bare.py").write_text("x = 1\n", encoding="utf-8")
    assert set(jp.jig_catalogue(tmp_path)) == {"good"}


def test_catalogue_ignores_a_pep723_header_and_dunder_files(tmp_path):
    (tmp_path / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (tmp_path / "hdr.py").write_text(
        '# /// script\n# dependencies = ["orjson"]\n# ///\n"""Reads a log."""\n', encoding="utf-8")
    cat = jp.jig_catalogue(tmp_path)
    assert cat == {"hdr": "Reads a log."}


# ---- the one question --------------------------------------------------------------------------
# A gate plus a choice was tried first and failed its own control: "pgrep -f ..." scored 0.12 on
# "is this a hand-rolled chore", because that gate's own exclusion ("ordinary use of a normal
# program") describes pgrep exactly. One request, with the two kinds of "no tool" kept apart.

def test_the_choice_offers_both_kinds_of_no_tool():
    q = jp.choice_question({"procsig": "signals a process"})
    assert q.type == "choice" and q.id == jp.CHOICE_ID
    for key in (jp.ORDINARY_KEY, jp.UNCOVERED_KEY, "procsig"):
        assert key in q.criteria, key


def test_the_choice_question_names_the_command_field():
    assert "`command`" in jp.choice_question({"a": "b"}).instructions


# ---- what one answer means ---------------------------------------------------------------------

def test_a_named_jig_is_the_suggestion():
    assert jp.decide("procsig") == "procsig"


def test_ordinary_work_suggests_nothing():
    assert jp.decide(jp.ORDINARY_KEY) is None and jp.decide(None) is None


def test_a_chore_with_no_fitting_jig_is_its_own_answer_not_a_silence():
    # this is the case that answers "should we BUILD one", so it must not collapse into None
    assert jp.decide(jp.UNCOVERED_KEY) == jp.UNCOVERED_KEY


# ---- sampling ------------------------------------------------------------------------------

def _calls(n, prefix="cmd"):
    return [{"id": "t%d" % i, "command": "%s %d" % (prefix, i), "cwd": "/p"} for i in range(n)]


def test_sample_is_stratified_over_what_the_keyword_rules_already_say():
    # asking only about calls the rules missed cannot measure agreement, and asking only about
    # the ones they caught cannot measure the gap - both classes are needed
    calls = _calls(50, "pgrep -f") + _calls(50, "ls")
    fired = {c["id"] + c["command"]: c["command"].startswith("pgrep") for c in calls}
    picked = jp.stratified_sample(calls, lambda c: fired[c["id"] + c["command"]], per_class=5,
                                  seed=1)
    n_fired = sum(1 for c in picked if c["command"].startswith("pgrep"))
    assert len(picked) == 10 and n_fired == 5


def test_sample_is_deterministic_for_a_seed_and_differs_across_seeds():
    calls = _calls(40)
    a = jp.stratified_sample(calls, lambda c: False, per_class=5, seed=7)
    b = jp.stratified_sample(calls, lambda c: False, per_class=5, seed=7)
    c = jp.stratified_sample(calls, lambda c: False, per_class=5, seed=8)
    assert [x["id"] for x in a] == [x["id"] for x in b]
    assert [x["id"] for x in a] != [x["id"] for x in c]


def test_sample_takes_what_exists_when_a_class_is_smaller_than_asked_for():
    calls = _calls(3)
    assert len(jp.stratified_sample(calls, lambda c: False, per_class=10, seed=1)) == 3


# ---- the controls, which must pass before any real number is read ------------------------------

def test_controls_name_a_known_positive_and_a_known_negative():
    pos, neg = jp.CONTROLS
    assert "pgrep" in pos["command"] and pos["expect"] == "procsig"
    assert neg["expect"] is None


def test_controls_fail_when_the_classifier_speaks_on_the_known_negative(fake_answers):
    clf = fake_answers({jp.CHOICE_ID: "procsig"})            # names a jig on BOTH controls
    with pytest.raises(jp.ControlFailed) as exc:
        jp.check_controls(clf, {"procsig": "signals a process"})
    assert "known negative" in str(exc.value)


def test_controls_fail_when_the_known_positive_is_called_ordinary(fake_answers):
    clf = fake_answers({jp.CHOICE_ID: jp.ORDINARY_KEY})      # silent on BOTH
    with pytest.raises(jp.ControlFailed) as exc:
        jp.check_controls(clf, {"procsig": "signals a process"})
    assert "known positive" in str(exc.value)


def test_controls_pass_when_the_classifier_separates_them(fake_answers):
    def answers(state):
        chore = "pgrep" in state.get("command", "")
        return {jp.CHOICE_ID: "procsig" if chore else jp.ORDINARY_KEY}
    jp.check_controls(fake_answers(answers), {"procsig": "signals a process"})


# ---- the keyword arm must be the SHIPPED one ---------------------------------------------------
# Matching the raw command is a different, more trigger-happy matcher than the hook's: the hook
# blanks heredoc bodies and unexpanded quoted text first. Measured on the pilot, a `cat > x <<EOF`
# whose BODY mentioned a grep was recorded as a claim_check firing that production never makes,
# which put Jev's disagreement against a rule that had not really spoken.

def test_the_regex_arm_ignores_a_chore_named_inside_a_heredoc_body():
    call = {"command": "cat > notes.md <<'EOF'\nuse grep -l to check, it is a trap\nEOF\n"}
    assert jp.regex_jig(call) is None


def test_the_regex_arm_still_fires_on_a_real_command():
    assert jp.regex_jig({"command": "pgrep -f my-daemon"}) == "procsig"


def test_the_regex_arm_agrees_with_the_hook_on_the_same_text():
    for command in ("pgrep -f x", "sed -i s/alpha_one/beta/ f.py", "echo hi",
                    "cat <<'EOF'\npkill -f x\nEOF\n"):
        text = jp.toolbox_nudge().extract_text("Bash", {"command": command})
        hit = jp.toolbox_nudge().match_tool(text, tool_name="Bash")
        assert jp.regex_jig({"command": command}) == (hit[0] if hit else None), command


# ---- the report ------------------------------------------------------------------------------

def _row(command, regex, jev):
    return {"command": command, "cwd": "/p", "regex_jig": regex, "jev_jig": jev,
            "choice": jev or jp.ORDINARY_KEY, "input_tokens": 500}


def test_report_counts_the_four_ways_the_two_channels_can_disagree():
    rows = [_row("a", "procsig", "procsig"), _row("b", "procsig", "newest"),
            _row("c", None, "gate"), _row("d", None, None)]
    rep = jp.summarize(rows)
    assert rep["agreed"] == 1 and rep["both_but_different"] == 1
    assert rep["jev_only"] == 1 and rep["neither"] == 1


def test_report_lists_the_chores_no_jig_covers_because_that_is_the_build_question():
    rows = [_row("replay prompts", None, jp.UNCOVERED_KEY),
            _row("replay more", None, jp.UNCOVERED_KEY), _row("ls", None, None)]
    rep = jp.summarize(rows)
    assert rep["chore_without_a_jig"] == 2
    assert [r["command"] for r in rep["uncovered_examples"]] == ["replay prompts", "replay more"]


def test_report_states_what_it_cost():
    rep = jp.summarize([_row("a", None, "gate"), _row("b", None, None)])
    assert rep["input_tokens"] == 1000 and rep["rows"] == 2


# ---- the CLI envelope --------------------------------------------------------------------------

def test_size_prints_an_estimate_without_calling_anything(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(jp, "collect_calls", lambda root, tool: _calls(1000))
    rc = jp.main(["size", "--limit", "20", "--root", str(tmp_path), "--json"])
    env = json.loads(capsys.readouterr().out)
    assert rc == 0 and env["ok"] is True
    assert env["data"]["calls_in_corpus"] == 1000 and env["data"]["would_ask_about"] == 40
    assert env["data"]["estimated_input_tokens"] > 0


def test_run_refuses_without_a_key_and_asks_the_api_nothing(tmp_path, capsys, monkeypatch):
    # a request sent to find out whether we may spend is itself spending
    asked = []

    class _Null:
        last_reason = "no api key"

        def ask(self, state, questions):
            asked.append(state)
            return None

    monkeypatch.setattr(jp, "get_classifier", lambda *a, **k: _Null())
    rc = jp.main(["run", "--limit", "1", "--root", str(tmp_path), "--json"])
    env = json.loads(capsys.readouterr().out)
    assert rc == 1 and env["ok"] is False and "no api key" in env["error"]
    assert asked == []


def test_report_on_an_empty_log_exits_1(tmp_path, capsys):
    log = tmp_path / "jig.jsonl"
    log.write_text("", encoding="utf-8")
    assert jp.main(["report", "--log", str(log), "--json"]) == 1
