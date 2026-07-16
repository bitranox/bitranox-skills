"""Tests for self_improve_signals.py (shared strict + broad learning-signal patterns).

All content is ASCII.
"""

import os
import time
from pathlib import Path

import pytest

import self_improve_signals as S


def test_strict_user_hit():
    assert S.strict_user_hit("no, that's wrong, the path is /etc")
    assert S.strict_user_hit("from now on always run the tests")
    assert S.strict_user_hit("good idea, let's do that")  # endorsement counts
    assert S.strict_user_hit("rather than hardcoding it, load it from config")  # directive, like "instead of"
    assert S.strict_user_hit("anstatt das zu hardcoden, lies es aus der config")  # German
    assert not S.strict_user_hit("please add a function to sum a list")


def test_strict_asst_hit():
    assert S.strict_asst_hit("You're right, my mistake.")
    assert S.strict_asst_hit("Now I understand the real topology.")
    assert S.strict_asst_hit("Good call - the gate belongs first.")  # endorsement counts
    assert not S.strict_asst_hit("Done, added the helper and a test.")


def test_strict_asst_hit_past_tense_admission():
    # regression: the gate used to miss PAST-tense "you were right" and noun-form / "misdiagnosed"
    # self-admissions (only "you're right" and the verb "i misread" were caught).
    assert S.strict_asst_hit("You were right; my earlier claim was a misread of the config.")
    assert S.strict_asst_hit("you were correct")
    assert S.strict_asst_hit("I misdiagnosed the DHCP scope - no change was needed.")
    # benign lines that describe state (not an admission) must NOT fire
    assert not S.strict_asst_hit("the new value is correct and the test passes")
    assert not S.strict_asst_hit("the old config was fine")


def test_strict_asst_hit_found_it_discovery():
    # "found it" and discovery phrasings are realization signals
    assert S.strict_asst_hit("Found it - the bug was in the parser.")
    assert S.strict_asst_hit("I found the root cause: a stale cache.")
    assert S.strict_asst_hit("found out why it hangs on reboot")
    assert S.strict_asst_hit("the culprit is the iptables backend")
    assert S.strict_asst_hit("Ursache gefunden: falscher Interpreter.")  # German
    # negatives: a NOT-found phrasing must not trip the strict gate
    assert not S.strict_asst_hit("I haven't found it yet.")
    assert not S.strict_asst_hit("could not find it anywhere")


def test_broad_user_flags_near_miss_not_caught_by_strict():
    text = "why did you change that? it's not working again"
    assert S.broad_matches("user", text)          # broad flags it
    assert not S.strict_user_hit(text)            # strict misses it -> a candidate


def test_strict_asst_hit_guard_blocked_named():
    # a guard/hook blocking the assistant is a self-admitted miss - including a NAMED guard, in either order
    assert S.strict_asst_hit("The gate blocked me - origin is ahead.")
    assert S.strict_asst_hit("My commit was rejected by the repo-gate hook.")
    assert S.strict_asst_hit("the venv-guard hook flagged my command")
    assert S.strict_asst_hit("blocked by a pre-commit hook")
    assert not S.strict_asst_hit("the gateway blocked the request")     # 'gateway' is not 'gate'
    assert not S.strict_asst_hit("I refactored the guard clause for clarity")  # no verb adjacent


def test_strict_asst_hit_hindsight_miss():
    # "I should have ..." and sibling hindsight admissions are STRICT live-gate signals
    assert S.strict_asst_hit("I should have run the tests first.")
    assert S.strict_asst_hit("I should've pinned the version.")
    assert S.strict_asst_hit("I missed the edge case in the parser.")
    assert S.strict_asst_hit("In hindsight, the guard order was wrong.")
    assert S.strict_asst_hit("I didn't realize the venv was stale.")
    assert not S.strict_asst_hit("You should have the latest version.")  # 'you should', not a self-admission


def test_broad_assistant_flags_near_miss():
    text = "let me reconsider the approach here"   # broad-only: not an explicit admission
    assert S.broad_matches("assistant", text)
    assert not S.strict_asst_hit(text)


def test_broad_flags_midcourse_inspection_not_strict():
    # a mid-course pause is a premature precursor: an audit candidate, NEVER a live-gate trigger
    for text in ("let me stop and inspect the diff",
                 "let me double-check the config",
                 "let me inspect what actually happened"):
        assert S.broad_matches("assistant", text), text   # surfaced for next-session review
        assert not S.strict_asst_hit(text), text           # but NOT an immediate nudge


def test_strict_asst_hit_forward_commitment():
    # committing to a standing behaviour / rule going forward is a confirmed adoption -> live gate
    assert S.strict_asst_hit("Going forward I'll fix every sibling at once.")
    assert S.strict_asst_hit("From now on I'll apply the rule.")
    assert S.strict_asst_hit("Next time I'll check the siblings.")
    assert S.strict_asst_hit("I'll make sure to fix the sibling too.")
    assert S.strict_asst_hit("I'll remember to update the changelog.")
    assert not S.strict_asst_hit("going forward is the next step")  # no commitment ("I'll")


def test_broad_flags_rule_citation_not_strict():
    # the real forgotten-rule case: the assistant cites a rule it had overlooked. The citation is a
    # judgement-call signal (sometimes a miss, sometimes routine) -> audit candidate, not a live nudge.
    msg = ('Understood - media likely shares the same generator and bugs; I\'ll fix it there too '
           '(per the "fix a shared bug in every sibling at once" rule). Let me confirm the fix first.')
    assert S.broad_matches("assistant", msg)        # surfaced for next-session review
    assert not S.strict_asst_hit(msg)               # not an immediate nudge
    assert S.broad_matches("assistant", "following the pathfinder convention here")


def test_broad_quiet_on_neutral_turns():
    assert S.broad_matches("user", "thanks, ship it") == []
    assert S.broad_matches("assistant", "Done, added the helper function.") == []


def test_broad_matches_returns_sorted_lowercase_unique():
    m = S.broad_matches("assistant", "Wait, I missed it. I missed it again.")
    assert m == sorted(set(m))
    assert all(x == x.lower() for x in m)


def test_audit_file_path_is_deterministic():
    p1 = S.audit_file("/some/project")
    p2 = S.audit_file("/some/project")
    assert p1 == p2
    assert p1.suffix == ".md"
    assert "self-improve-audit" in str(p1)
    assert S.audit_file("/other/project") != p1


# --------------------------------------------------------------------------
# meta-dream-tree cadence markers + mode
# --------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _mem(home, proj="/p/x"):
    d = S.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.md").write_text("x", encoding="utf-8")
    return d


def test_dream_mode_default(home):
    assert S.dream_mode("/p/x") == "propose"


def test_dream_mode_off(home):
    S.save_config({"dream_mode": "off"})
    assert S.dream_mode("/p/x") == "off"


def test_dream_mode_auto(home):
    S.save_config({"dream_mode": "auto"})
    assert S.dream_mode("/p/x") == "auto"


def test_dream_due_no_memory(home):
    assert S.dream_due("/p/x") is False


def test_dream_due_memory_no_marker(home):
    _mem(home)
    assert S.dream_due("/p/x") is True


def test_dream_due_recent_not_due(home):
    _mem(home)
    S.mark_dream_done("/p/x")  # last == now
    assert S.dream_due("/p/x") is False


def test_dream_due_old_and_changed(home):
    _mem(home)
    f = S.last_dream_file("/p/x")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("1000.0", encoding="utf-8")  # ancient last-dream
    assert S.dream_due("/p/x", now=10_000_000_000) is True


def test_dream_due_off_mode_never(home):
    _mem(home)
    S.save_config({"dream_mode": "off"})
    assert S.dream_due("/p/x") is False


def test_mark_dream_done_writes_timestamp_and_signature(home):
    assert S.mark_dream_done("/p/x", now=123.0) is True
    ts, sig = S._read_dream_record("/p/x")
    assert ts == 123.0 and isinstance(sig, str)   # new format: JSON {ts, sig}


def test_dream_due_signature_based_not_mtime(home, tmp_path):
    # a real fact makes it due; after mark_dream_done (records the signature) it is quiet; a mere
    # scope-only pointer block does NOT re-trigger (no fact changed). Facts are the pointer LINES in the
    # level's CLAUDE.local.md.
    proj = str(tmp_path / "sigproj")
    (tmp_path / "sigproj").mkdir(parents=True, exist_ok=True)
    later = 1000.0 + 10 * 86400
    S.mark_dream_done(proj, now=1000.0)                          # no facts -> quiet baseline
    assert S.dream_due(proj, now=later) is False                 # still no facts
    local = S.claude_local_md_path(proj)
    local.write_text("<!-- BITRANOX-UUID-INDEX:BEGIN -->\n%s\nscope only\n%s\n\n# Memory index\n"
                     "<!-- BITRANOX-UUID-INDEX:END -->\n"
                     % (S.SCOPE_MARK_BEGIN, S.SCOPE_MARK_END), encoding="utf-8")
    assert S.dream_due(proj, now=later) is False                 # scope-only -> no real fact
    local.write_text("<!-- BITRANOX-UUID-INDEX:BEGIN -->\n%s\nscope\n%s\n\n# Memory index\n\n"
                     "- [X](uuid:11111111-0000-5000-8000-000000000000) - a real fact <!-- bx:slug=x -->\n"
                     "<!-- BITRANOX-UUID-INDEX:END -->\n"
                     % (S.SCOPE_MARK_BEGIN, S.SCOPE_MARK_END), encoding="utf-8")
    assert S.dream_due(proj, now=later) is True                  # a real fact appeared -> due


# --------------------------------------------------------------------------
# machine-local config (informed-consent knobs)
# --------------------------------------------------------------------------


def test_load_config_defaults(home):
    cfg = S.load_config()
    assert cfg == S.DEFAULT_CONFIG
    assert cfg["dream_mode"] == "propose"


def test_config_file_sets_dream_mode(home):
    S.save_config({"dream_mode": "off"})
    assert S.load_config()["dream_mode"] == "off"
    assert S.dream_mode("/p/x") == "off"


def test_save_config_roundtrip_and_ignores_unknown(home):
    saved = S.save_config({"privacy": "walled", "promotion": "eager", "bogus": 1})
    assert saved["privacy"] == "walled" and saved["promotion"] == "eager"
    assert "bogus" not in saved
    reloaded = S.load_config()
    assert reloaded["privacy"] == "walled" and reloaded["promotion"] == "eager"
    assert "bogus" not in reloaded


def test_load_config_corrupt_file_returns_defaults(home):
    S._config_path().write_text("{not json", encoding="utf-8")
    assert S.load_config()["dream_mode"] == "propose"


# --------------------------------------------------------------------------
# altitude homes
# --------------------------------------------------------------------------


def test_topmost_claude_md_dir(tmp_path):
    top = tmp_path / "top"
    mid = top / "mid"
    proj = mid / "proj"
    proj.mkdir(parents=True)
    (top / "CLAUDE.md").write_text("x", encoding="utf-8")       # highest
    (proj / "CLAUDE.md").write_text("x", encoding="utf-8")      # nearer, but not the highest
    assert S.topmost_claude_md_dir(str(proj)) == top            # HIGHEST wins over the nearer one (bootstrap: no store)
    assert S.topmost_claude_md_dir(str(tmp_path / "none")) is None


def test_topmost_claude_md_dir_store_colocation_beats_stray_higher_md(tmp_path):
    # a STRAY higher CLAUDE.md (no store) must NOT hijack the anchor: the topmost dir with BOTH a
    # CLAUDE.md AND a store wins (the probe-caught fragility).
    stray = tmp_path / "stray"            # higher, CLAUDE.md ONLY -> the hijack risk
    real = stray / "real"                 # the true anchor: CLAUDE.md + store
    proj = real / "sub" / "proj"
    proj.mkdir(parents=True)
    (stray / "CLAUDE.md").write_text("x", encoding="utf-8")
    (real / "CLAUDE.md").write_text("x", encoding="utf-8")
    (real / S.MEMORY_DIRNAME).mkdir()
    (proj / "CLAUDE.md").write_text("x", encoding="utf-8")
    (proj / S.MEMORY_DIRNAME).mkdir()
    assert S.topmost_claude_md_dir(str(proj)) == real           # real (both) beats stray (md-only)


def test_topmost_claude_md_dir_never_anchors_at_home_or_tmp(home, tmp_path):
    # $HOME (and /tmp) are excluded as anchor candidates: a stray CLAUDE.md + store AT home must NOT be
    # picked, even though home is the highest ancestor carrying both. The walk stops below it.
    h = Path(os.environ["HOME"])                                 # monkeypatched by the `home` fixture
    (h / "CLAUDE.md").write_text("x", encoding="utf-8")
    (h / S.MEMORY_DIRNAME).mkdir()
    sub = h / "projects" / "foo"                                 # a real altitude below home
    sub.mkdir(parents=True)
    (sub / "CLAUDE.md").write_text("x", encoding="utf-8")
    (sub / S.MEMORY_DIRNAME).mkdir()
    proj = sub / "deep"
    proj.mkdir()
    got = S.topmost_claude_md_dir(str(proj))
    assert got == sub                                            # sub, NOT the excluded home
    assert got != h


def test_global_rules_dir_is_topmost_claude_md_ancestor(tmp_path):
    top = tmp_path / "top"
    proj = top / "a" / "b"
    proj.mkdir(parents=True)
    (top / "CLAUDE.md").write_text("x", encoding="utf-8")
    # global = the topmost-CLAUDE.md ancestor's LIVE central store; NEVER ~/.claude
    assert S.global_rules_dir(str(proj)) == top / S.MEMORY_DIRNAME


def test_global_rules_dir_falls_back_to_proj_when_no_claude_md(tmp_path):
    proj = tmp_path / "loner"
    proj.mkdir()
    assert S.global_rules_dir(str(proj)) == proj / S.MEMORY_DIRNAME   # proj itself is the top


def test_altitude_chain_up_to_topmost_no_home_duplicate(tmp_path):
    proj = tmp_path / "repo"
    sub = proj / "pkg"
    sub.mkdir(parents=True)
    (proj / "CLAUDE.md").write_text("x", encoding="utf-8")      # ancestor WITH CLAUDE.md -> altitude
    (sub / "CLAUDE.md").write_text("x", encoding="utf-8")
    chain = S.altitude_chain(str(sub))
    assert chain[0] == sub                              # narrowest: the project LEVEL dir
    assert chain[-1] == proj                            # broadest == topmost level, not ~/.claude
    assert S.global_rules_dir(str(sub)) == proj / S.MEMORY_DIRNAME
    assert tmp_path not in chain                        # an ancestor WITHOUT CLAUDE.md is excluded
    assert len(chain) == len({str(c) for c in chain})   # no duplicated top tier


def test_altitude_chain_single_tier_when_no_claude_md(tmp_path):
    proj = tmp_path / "loner"
    proj.mkdir()
    chain = S.altitude_chain(str(proj))
    assert chain == [proj]                              # project is the top; nothing appended


def test_altitude_chain_fills_gaps_up_to_highest(tmp_path):
    top = tmp_path / "top"            # highest existing CLAUDE.md == global tier
    mid = top / "mid"                 # GAP: no CLAUDE.md here
    proj = mid / "proj"              # project, has CLAUDE.md
    proj.mkdir(parents=True)
    (top / "CLAUDE.md").write_text("x", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("x", encoding="utf-8")
    chain = S.altitude_chain(str(proj))
    assert proj in chain and top in chain
    assert mid in chain                # the GAP level is INCLUDED (to be filled), not skipped
    assert tmp_path not in chain       # above the highest existing CLAUDE.md -> excluded
    assert (chain.index(proj) < chain.index(mid) < chain.index(top))
    assert chain[-1] == top            # topmost is the broadest (global) LEVEL, not ~/.claude


# --------------------------------------------------------------------------
# new-project seeding
# --------------------------------------------------------------------------


def test_project_unseeded_fresh_then_marked(home):
    assert S.project_unseeded("/p/fresh") is True       # no memory, not nudged
    assert S.mark_seeded("/p/fresh") is True
    assert S.project_unseeded("/p/fresh") is False       # nudged once -> quiet


def test_project_unseeded_false_when_memory_exists(home):
    _mem(home, "/p/has")
    assert S.project_unseeded("/p/has") is False


# --------------------------------------------------------------------------
# quality / dwell gate for global promotion
# --------------------------------------------------------------------------


def test_note_promotion_candidate_increments(home):
    assert S.note_promotion_candidate("/p/x", "fleet-ssh") == 1
    assert S.note_promotion_candidate("/p/x", "fleet-ssh") == 2
    assert S.note_promotion_candidate("/p/x", "other") == 1   # independent per key


def test_should_promote_user_stated_is_eager(home):
    assert S.should_promote("user", 1) is True                # user rule promotes on first sight


def test_should_promote_inferred_needs_corroboration(home):
    assert S.should_promote("inferred", 1) is False           # one sighting: not yet
    assert S.should_promote("inferred", 2) is True            # corroborated across 2 dreams


def test_should_promote_eager_mode_overrides(home):
    S.save_config({"promotion": "eager"})
    assert S.should_promote("inferred", 1) is True            # config: promote eagerly


def test_clear_promotion_candidate(home):
    S.note_promotion_candidate("/p/x", "k")
    S.clear_promotion_candidate("/p/x", "k")
    assert S.note_promotion_candidate("/p/x", "k") == 1       # count was forgotten


def test_promotion_dwell_reads_without_incrementing(home):
    assert S.promotion_dwell("/p/x", "k") == 0                # unseen -> 0
    S.note_promotion_candidate("/p/x", "k")
    assert S.promotion_dwell("/p/x", "k") == 1                # read-only: does not bump
    assert S.promotion_dwell("/p/x", "k") == 1               # still 1 after a second read


# --------------------------------------------------------------------------
# scope-descriptor marked block + writer-race signature
# --------------------------------------------------------------------------


def test_read_scope_block_absent_and_present():
    assert S.read_scope_block("# hand-written\nrules here\n") is None
    text = "# c\n%s\nall my python work\n%s\n" % (S.SCOPE_MARK_BEGIN, S.SCOPE_MARK_END)
    assert S.read_scope_block(text) == "all my python work"


def test_upsert_scope_block_appends_preserving_handwritten():
    orig = "# Project rules\n- be concise\n"
    out = S.upsert_scope_block(orig, "this repo = the widget service")
    assert orig in out                                   # hand-written content untouched
    assert S.read_scope_block(out) == "this repo = the widget service"


def test_upsert_scope_block_replaces_in_place():
    text = S.upsert_scope_block("# c\n", "old scope")
    text2 = S.upsert_scope_block(text, "new scope")
    assert S.read_scope_block(text2) == "new scope"
    assert text2.count(S.SCOPE_MARK_BEGIN) == 1          # not duplicated


def test_upsert_scope_block_diff_free_when_unchanged():
    text = S.upsert_scope_block("# c\n", "same")
    assert S.upsert_scope_block(text, "same") == text    # no-change refresh writes nothing


def test_store_changed(home):
    d = _mem(home, "/p/sc")
    base = S._newest_mtime(d)
    assert S.store_changed(d, base) is False
    import os
    os.utime(d / "a.md", (base + 100, base + 100))
    assert S.store_changed(d, base) is True


# No usage/age/size forgetting exists (usage is unmeasurable) - removal is dedup + obsolete-prune +
# manual only, done by the dream. So there are no bump_idle/should_archive helpers to test.
def test_no_age_based_forgetting_helpers(home):
    assert not hasattr(S, "should_archive")
    assert not hasattr(S, "bump_idle")
    assert "forgetting" not in S.DEFAULT_CONFIG and "forget_idle_dreams" not in S.DEFAULT_CONFIG


def test_model_review_due_and_mark(home):
    assert S.model_review_due() is True                      # no prior review -> due
    t = S.mark_model_reviewed(now=1_000_000.0)
    assert t == 1_000_000.0
    assert S.model_review_due(now=1_000_000.0) is False      # just reviewed -> not due
    assert S.model_review_due(now=1_000_000.0 + 29 * 86400) is False
    assert S.model_review_due(now=1_000_000.0 + 31 * 86400) is True   # past the monthly interval


def test_backup_reminder_due_and_mark(home):
    assert S.backup_reminder_due() is True                    # no prior reminder -> due
    assert S.mark_backup_reminded(now=1_000_000.0) == 1_000_000.0
    assert S.backup_reminder_due(now=1_000_000.0) is False    # just reminded -> not due
    assert S.backup_reminder_due(now=1_000_000.0 + 29 * 86400) is False
    assert S.backup_reminder_due(now=1_000_000.0 + 31 * 86400) is True   # past the monthly interval


# --- recall filler words ------------------------------------------------------------------------
_PROJ = "/p/proj"


def test_filler_baseline_global_plus_project_local(home):
    base = S.load_filler_words()                                          # baseline only (proj=None)
    assert "previous" in base and "again" in base and "normal" in base   # shipped baseline present
    assert "frobnicate" not in base
    S.add_filler_words(["Frobnicate", "frobnicate", "  "], _PROJ)        # per-project learned, normalized
    assert "frobnicate" in S.load_filler_words(_PROJ)                     # baseline UNION project-local
    assert "previous" in S.load_filler_words(_PROJ)                       # baseline still there
    assert "frobnicate" not in S.load_filler_words()                      # NOT in the baseline-only view


def test_learned_filler_is_per_project_not_global(home):
    S.add_filler_words(["alpha"], "/p/a")
    assert "alpha" in S.load_filler_words("/p/a")                         # learned in A
    assert "alpha" not in S.load_filler_words("/p/b")                     # ... never leaks to B
    assert "alpha" not in S.load_filler_words()                           # ... nor to baseline-only


def test_add_filler_words_does_not_touch_shipped_baseline(home):
    S.add_filler_words(["zzznew"], _PROJ)
    assert "zzznew" not in S._read_word_json(S._filler_baseline_path())   # baseline file untouched
    assert "zzznew" in S._read_word_json(S._filler_local_path(_PROJ))     # only the project file grows


def test_topical_words_roundtrip_per_project(home):
    assert S.load_topical_words(_PROJ) == frozenset()
    S.add_topical_words(["RabbitMQ", "ept"], _PROJ)
    assert "rabbitmq" in S.load_topical_words(_PROJ) and "ept" in S.load_topical_words(_PROJ)
    assert S.load_topical_words("/p/other") == frozenset()                # whitelist is per-project


def test_pending_keywords_queue_skips_known_and_drains(home):
    S.add_filler_words(["again"], _PROJ)
    S.add_topical_words(["rabbitmq"], _PROJ)
    S.note_unknown_keywords(["again", "rabbitmq", "stimer", "ept"], _PROJ)   # 2 known -> only 2 queued
    assert S.load_pending_keywords(_PROJ) == frozenset({"stimer", "ept"})
    S.note_unknown_keywords(["stimer", "vmbus"], _PROJ)                      # dedup vs queue; add vmbus
    assert S.load_pending_keywords(_PROJ) == frozenset({"stimer", "ept", "vmbus"})
    S.clear_pending_keywords(_PROJ)
    assert S.load_pending_keywords(_PROJ) == frozenset()
    assert S.load_pending_keywords("/p/other") == frozenset()                # queue is per-project


# ---- curated-store relocation, version gate, and cross-platform lock (Phase 1) --------------------

def test_curated_paths():
    assert S.CURATED_INDEX == "index.md"          # named index.md, never confused with native MEMORY.md
    assert S.claude_memory_dir("/p/proj") == __import__("pathlib").Path("/p/proj/.claude-bx-selflearning")
    assert S.curated_index("/p/proj").name == "index.md"
    assert S.curated_index("/p/proj").parent.name == ".claude-bx-selflearning"
    assert S.claude_md_path("/p/proj").name == "CLAUDE.md"
    assert S.claude_local_md_path("/p/proj").name == "CLAUDE.local.md"   # default @import home (untracked)
    assert S.curated_state_dir("/p/proj").name == "state"


def test_ensure_gitignored(home, tmp_path):
    import subprocess
    proj = tmp_path / "repo"; proj.mkdir()
    subprocess.run(["git", "init", "-q", str(proj)], check=False)
    S.ensure_gitignored(str(proj), S.CURATED_DIRNAME + "/", "CLAUDE.local.md")
    gi = (proj / ".gitignore").read_text(encoding="utf-8")
    assert ".claude-bx-selflearning/" in gi and "CLAUDE.local.md" in gi
    assert subprocess.run(["git", "-C", str(proj), "check-ignore", "-q", "CLAUDE.local.md"]).returncode == 0
    # track_private on -> leaves the repo tracked (no gitignore write)
    S.save_config({"track_private": True})
    proj2 = tmp_path / "repo2"; proj2.mkdir()
    subprocess.run(["git", "init", "-q", str(proj2)], check=False)
    S.ensure_gitignored(str(proj2), "CLAUDE.local.md")
    assert not (proj2 / ".gitignore").exists()
    # non-git dir -> skip, no crash
    plain = tmp_path / "plain"; plain.mkdir()
    S.ensure_gitignored(str(plain), "CLAUDE.local.md")
    assert not (plain / ".gitignore").exists()


def test_claude_code_version_detection():
    assert S.claude_code_version({"CLAUDE_CODE_EXECPATH": "/x/versions/2.1.198/bin"}) == (2, 1, 198)
    assert S.claude_code_version({"AI_AGENT": "claude-code_2-1-198_agent"}) == (2, 1, 198)
    assert S.claude_code_version({"CLAUDE_CODE_EXECPATH": "/no/version/here"}) is None
    assert S.claude_code_version({}) is None


def test_import_supported_gate():
    assert S.import_supported({"CLAUDE_CODE_EXECPATH": "/x/versions/2.1.198/"}) is True
    assert S.import_supported({"CLAUDE_CODE_EXECPATH": "/x/versions/1.9.9/"}) is False
    assert S.import_supported({}) is True            # unknown -> fail-open (assume supported)


def test_default_config_new_knobs():
    for k in ("track_private", "mcp_search", "discovery_roots"):
        assert k in S.DEFAULT_CONFIG
    assert S.DEFAULT_CONFIG["discovery_roots"] == []  # derived at runtime, never hardcoded paths


def test_discovery_roots_defaults_to_home_when_unconfigured(home):
    roots = [str(r) for r in S.discovery_roots()]
    assert str(home) in roots       # no explicit config -> the derived default is $HOME


def test_discovery_roots_honors_explicit_config_without_home(home):
    extra = home / "elsewhere"
    extra.mkdir()
    S.save_config({"discovery_roots": [str(extra)]})
    roots = [str(r) for r in S.discovery_roots()]
    assert str(extra) in roots          # explicit root honored exactly
    assert str(home) not in roots       # $HOME is NOT force-added on top of an explicit config


def test_stores_generation_starts_zero_and_bumps(home):
    assert S.stores_generation() == 0
    S.bump_stores_generation()
    assert S.stores_generation() == 1
    S.bump_stores_generation()
    assert S.stores_generation() == 2


def test_stores_generation_survives_garbled_marker(home):
    f = S._stores_gen_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("not-an-int", encoding="utf-8")
    assert S.stores_generation() == 0   # garbled marker -> 0, never raises
    S.bump_stores_generation()
    assert S.stores_generation() == 1


def test_memory_lock_acquire_release(tmp_path):
    target = tmp_path / "index.md"
    lock = tmp_path / "index.md.lock"
    with S.memory_lock(target):
        assert lock.exists()
    assert not lock.exists()                          # released


def test_memory_lock_contention_raises(tmp_path):
    target = tmp_path / "m2"
    with S.memory_lock(target):
        with pytest.raises(TimeoutError):
            with S.memory_lock(target, timeout=0.05):
                pass


def test_memory_lock_reclaims_stale(tmp_path):
    target = tmp_path / "m3"
    stale = tmp_path / "m3.lock"
    stale.write_text("", encoding="utf-8")
    import os as _os
    old = time.time() - (S._LOCK_STALE_S + 10)
    _os.utime(stale, (old, old))                      # make the lock look stale (crashed holder)
    with S.memory_lock(target, timeout=0.05):         # reclaims it instead of timing out
        assert stale.exists()
    assert not stale.exists()


# --------------------------------------------------------------------------
# unified anchor resolver (single source in sig; uuid_store delegates)
# --------------------------------------------------------------------------


def test_resolve_anchor_in_sig_matches_uuid_store(tmp_path):
    import uuid_store as US
    top = tmp_path / "top"
    proj = top / "a" / "proj"
    proj.mkdir(parents=True)
    (top / "CLAUDE.md").write_text("x", encoding="utf-8")
    (top / S.MEMORY_DIRNAME).mkdir()
    assert S.resolve_anchor(str(proj)) == US.resolve_anchor(str(proj)) == top
    assert S.topmost_claude_md_dir(str(proj)) == top    # the alias is the same resolver


def test_two_trees_anchor_isolation(two_trees):
    tt = two_trees
    assert S.resolve_anchor(str(tt.proj_a)) == tt.top_a
    assert S.resolve_anchor(str(tt.proj_b)) == tt.top_b
    assert S.resolve_anchor(str(tt.proj_a)) != S.resolve_anchor(str(tt.proj_b))
    chain_a = S.altitude_chain(str(tt.proj_a))
    assert tt.top_b not in chain_a and tt.proj_b not in chain_a


# ---- multi-tree discovery (find_claude_md_dirs + tree_groups) -----------------------------------

def test_find_claude_md_dirs_prunes_vendor_hidden_backup_and_store_dirs(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home)); monkeypatch.setenv("USERPROFILE", str(home))
    work = tmp_path / "work"
    for rel in ("a", "a/nested", "b"):
        d = work / rel
        d.mkdir(parents=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    for rel in ("a/node_modules/dep", "a/.git/x", "b/old.bak", "b/.claude-memory/facts"):
        d = work / rel
        d.mkdir(parents=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (home / ".claude" / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    got = S.find_claude_md_dirs([str(work), str(home)])
    assert {str(p.relative_to(work)) for p in got if work in p.parents or p == work} == {"a", "a/nested", "b"}
    assert not any(".claude" in str(p) for p in got)


def test_find_claude_md_dirs_does_not_follow_symlinks(tmp_path):
    real = tmp_path / "real"; real.mkdir()
    (real / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    scan = tmp_path / "scan"; scan.mkdir()
    (scan / "link").symlink_to(real)
    got = S.find_claude_md_dirs([str(scan)])
    assert got == []                                   # a symlinked tree is never merged in


def test_tree_groups_two_independent_trees(two_trees):
    md = S.find_claude_md_dirs([str(two_trees.root)])
    groups = S.tree_groups(md)
    assert set(groups) == {two_trees.top_a, two_trees.top_b}
    assert groups[two_trees.top_a][0] == two_trees.proj_a      # deepest first
    assert groups[two_trees.top_a][-1] == two_trees.top_a
