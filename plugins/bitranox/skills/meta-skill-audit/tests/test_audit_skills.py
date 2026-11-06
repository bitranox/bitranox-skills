"""Tests for audit_skills.py (the clean-room skill auditor). ASCII only.

The reviewer is injected at the `runner` seam, so these exercise the real module end to end with a
substitute reviewer rather than patching internals."""

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import audit_skills as A

# The plugin's real hooks dir, so the decision brief is rendered by the real skill_decisions module.
PLUGIN_HOOKS = Path(__file__).resolve().parents[3] / "hooks"


def _plugin(tmp_path, skills=("alpha", "beta"), with_hook=True):
    """A miniature plugin: skills/<name>/SKILL.md plus a hook."""
    root = tmp_path / "plugin"
    for s in skills:
        d = root / "skills" / s
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("# %s\n" % s, encoding="utf-8")
    if with_hook:
        (root / "hooks").mkdir(parents=True)
        (root / "hooks" / "gate.py").write_text("# hook\n", encoding="utf-8")
    (root / "skills" / "not-a-skill").mkdir(parents=True)      # no SKILL.md -> not audited
    return root


# ---- prompt contract ----------------------------------------------------------------------------

def test_prompt_names_the_skill_and_the_namespace():
    p = A.build_prompt("compuse-git", prefix="acme")
    assert "skills/compuse-git/" in p and "`acme:<name>`" in p


def test_prompt_states_the_plugin_is_the_install_unit():
    """The false-positive class this whole harness exists to avoid."""
    p = A.build_prompt("x")
    assert "this whole directory is the installed plugin" in p
    assert "IS reachable" in p                       # siblings/hooks are not dangling


def test_prompt_requires_a_verbatim_quote_per_finding():
    flat = " ".join(A.build_prompt("x").split())      # the prompt wraps; the wrap is not the contract
    assert "QUOTE:" in flat and "you do not have a finding - drop it" in flat


def test_prompt_asks_for_a_skill_gaps_section():
    assert "Skill gaps" in A.build_prompt("x")


# ---- enumeration --------------------------------------------------------------------------------

def test_skill_names_lists_only_dirs_with_a_skill_md(tmp_path):
    root = _plugin(tmp_path)
    assert A.skill_names(root) == ["alpha", "beta"]


def test_skill_names_honours_only(tmp_path):
    root = _plugin(tmp_path, skills=("alpha", "beta", "gamma"))
    assert A.skill_names(root, only=("beta", "")) == ["beta"]


def test_skill_names_of_a_missing_plugin_is_empty(tmp_path):
    assert A.skill_names(tmp_path / "nope") == []


# ---- room preparation ---------------------------------------------------------------------------

def test_prepare_room_copies_the_plugin_and_makes_reports(tmp_path):
    src = _plugin(tmp_path)
    room = A.prepare_room(src, tmp_path / "room")
    assert (room / "skills" / "alpha" / "SKILL.md").is_file()
    assert (room / "hooks" / "gate.py").is_file()      # hooks travel: they are part of the install
    assert (tmp_path / "room" / "reports").is_dir()


def test_prepare_room_omits_review_artifacts(tmp_path):
    src = _plugin(tmp_path)
    (src / "skills" / "alpha" / ".skillwriter").mkdir()
    (src / "skills" / "alpha" / ".skillwriter" / "checklist.md").write_text("x", encoding="utf-8")
    room = A.prepare_room(src, tmp_path / "room")
    assert not (room / "skills" / "alpha" / ".skillwriter").exists()


def test_prepare_room_replaces_a_stale_copy_unless_reused(tmp_path):
    src = _plugin(tmp_path)
    room = A.prepare_room(src, tmp_path / "room")
    (room / "skills" / "alpha" / "SKILL.md").write_text("edited in the room\n", encoding="utf-8")
    fresh = A.prepare_room(src, tmp_path / "room")
    assert "edited in the room" not in (fresh / "skills" / "alpha" / "SKILL.md").read_text(encoding="utf-8")
    (fresh / "skills" / "alpha" / "SKILL.md").write_text("edited again\n", encoding="utf-8")
    kept = A.prepare_room(src, tmp_path / "room", reuse=True)
    assert "edited again" in (kept / "skills" / "alpha" / "SKILL.md").read_text(encoding="utf-8")


# ---- counting -----------------------------------------------------------------------------------

def test_count_findings_counts_markers_and_treats_no_findings_as_zero():
    assert A.count_findings("FINDING: WRONG | a | b\nFINDING: STALE | c | d") == 2
    assert A.count_findings("NO FINDINGS") == 0
    assert A.count_findings("") == 0 and A.count_findings(None) == 0


# ---- end to end through the injected reviewer ---------------------------------------------------

def test_audit_all_writes_one_report_per_skill_and_counts(tmp_path):
    src = _plugin(tmp_path)
    seen = []

    def runner(prompt, cwd, model, timeout):
        seen.append((prompt, str(cwd), model, timeout))
        return "FINDING: WRONG | SKILL.md | x\nQUOTE: y\nWHY: z" if "alpha" in prompt else "NO FINDINGS"

    res = A.audit_all(src, tmp_path / "room", jobs=2, runner=runner, log=lambda *_a: None)
    assert res == {"alpha": 1, "beta": 0}
    reports = tmp_path / "room" / "reports"
    assert "FINDING:" in (reports / "alpha.audit.txt").read_text(encoding="utf-8")
    assert (reports / "beta.audit.txt").read_text(encoding="utf-8") == "NO FINDINGS"


DECISION_REVIEW = (
    "Looking back over this review, the decisions I am least confident about are the scope of the\n"
    "second pass and whether the third file needed re-reading. Nothing else is unsettled.\n"
)


def test_a_final_message_carrying_no_report_block_is_not_stored_as_a_clean_report(tmp_path):
    """The decision-review Stop hook fires on each reviewer subagent, so its final stdout can be a
    decision review rather than the report. Stored wholesale it counts 0 findings, which is exactly
    what a clean skill looks like - measured on a real sweep, 6 of 47 targets and one of them had
    9 findings in its transcript."""
    src = _plugin(tmp_path, skills=("alpha",))

    res = A.audit_all(src, tmp_path / "room", jobs=1, log=lambda *_a: None,
                      runner=lambda *_a: DECISION_REVIEW)

    body = (tmp_path / "room" / "reports" / "alpha.audit.txt").read_text(encoding="utf-8")
    assert res["alpha"] != 0, "a report-less reply counted as a clean skill"
    assert body.startswith(A.REPORT_MISSING_MARKER), body[:120]
    assert "second pass" in body, "the raw reply must be kept for recovery"


def test_a_real_report_is_still_stored_verbatim(tmp_path):
    """The direction the marker must NOT reach."""
    src = _plugin(tmp_path, skills=("alpha",))
    A.audit_all(src, tmp_path / "room", jobs=1, log=lambda *_a: None,
                runner=lambda *_a: "FINDING: WRONG | SKILL.md | x\nQUOTE: y")
    body = (tmp_path / "room" / "reports" / "alpha.audit.txt").read_text(encoding="utf-8")
    assert not body.startswith(A.REPORT_MISSING_MARKER)
    assert body == "FINDING: WRONG | SKILL.md | x\nQUOTE: y"


def test_a_trailing_decision_review_after_a_real_report_is_kept(tmp_path):
    """A reply that carries the report AND then chats is fine - the report block is there."""
    src = _plugin(tmp_path, skills=("alpha",))
    A.audit_all(src, tmp_path / "room", jobs=1, log=lambda *_a: None,
                runner=lambda *_a: "NO FINDINGS\n\n" + DECISION_REVIEW)
    body = (tmp_path / "room" / "reports" / "alpha.audit.txt").read_text(encoding="utf-8")
    assert not body.startswith(A.REPORT_MISSING_MARKER)


def test_report_is_complete_rejects_a_clobbered_report_so_skip_existing_reruns_it(tmp_path):
    """--skip-existing skipped a clobbered report precisely BECAUSE it is non-empty."""
    assert A.report_is_complete("NO FINDINGS\n")
    assert A.report_is_complete("FINDING: WRONG | a.py:1 | claim\n")
    assert not A.report_is_complete(DECISION_REVIEW)
    assert not A.report_is_complete(A.REPORT_MISSING_MARKER + " whatever\nFINDING: X | y | z\n")
    assert not A.report_is_complete("")


def test_every_reviewer_runs_with_the_room_as_cwd(tmp_path):
    """Never the live tree: that is the contamination the clean room exists to prevent."""
    src = _plugin(tmp_path)
    cwds = []

    def runner(prompt, cwd, model, timeout):
        cwds.append(str(cwd))
        return "NO FINDINGS"

    A.audit_all(src, tmp_path / "room", jobs=1, runner=runner, log=lambda *_a: None)
    assert cwds and all(c == str(tmp_path / "room" / "plugin") for c in cwds)


def test_a_reviewer_timeout_is_recorded_not_swallowed(tmp_path):
    src = _plugin(tmp_path, skills=("alpha",))
    A.audit_all(src, tmp_path / "room", jobs=1, log=lambda *_a: None,
                runner=lambda *_a: "(TIMEOUT after 900s)")
    body = (tmp_path / "room" / "reports" / "alpha.audit.txt").read_text(encoding="utf-8")
    assert "TIMEOUT" in body                          # a silent zero would read as 'clean'


# --- staging a loose skills dir ---------------------------------------------------------------

def _loose(tmp_path):
    """A `~/.claude`-shaped home: a small skills dir beside a huge sibling that must not be copied."""
    claude = tmp_path / "home" / ".claude"
    (claude / "skills" / "toolbox").mkdir(parents=True)
    (claude / "skills" / "toolbox" / "SKILL.md").write_text(
        "---\nname: toolbox\ndescription: Use when reaching for a local tool.\n---\n",
        encoding="utf-8")
    bulk = claude / "projects" / "transcripts"
    bulk.mkdir(parents=True)
    (bulk / "huge.jsonl").write_text("x" * 5000, encoding="utf-8")
    (claude / "plugins" / "cache").mkdir(parents=True)
    (claude / "plugins" / "cache" / "installed.txt").write_text("y" * 5000, encoding="utf-8")
    return claude


def test_prepare_room_from_skills_copies_only_the_skills_dir(tmp_path):
    """The point of the flag: `~/.claude` is gigabytes, and a reviewer reads none of it."""
    claude = _loose(tmp_path)
    room = A.prepare_room_from_skills(claude / "skills", tmp_path / "room")
    assert (room / "skills" / "toolbox" / "SKILL.md").is_file()
    assert not (room / "projects").exists()
    assert not (room / "plugins").exists()
    copied = sum(p.stat().st_size for p in room.rglob("*") if p.is_file())
    assert copied < 5000, "staged room must not carry the bulky siblings"


def test_prepare_room_from_skills_is_discoverable_by_skill_names(tmp_path):
    claude = _loose(tmp_path)
    room = A.prepare_room_from_skills(claude / "skills", tmp_path / "room")
    assert A.skill_names(room) == ["toolbox"]


def test_prepare_room_from_skills_stages_hooks_when_asked(tmp_path):
    """A skill may reference a sibling hook; without it staged the reviewer calls it dangling."""
    claude = _loose(tmp_path)
    hooks = claude / "hooks"
    hooks.mkdir()
    (hooks / "guard.py").write_text("x = 1\n", encoding="utf-8")
    room = A.prepare_room_from_skills(claude / "skills", tmp_path / "room", hooks)
    assert (room / "hooks" / "guard.py").is_file()


def test_prepare_room_from_skills_skips_caches_and_git(tmp_path):
    claude = _loose(tmp_path)
    (claude / "skills" / "toolbox" / "__pycache__").mkdir()
    (claude / "skills" / "toolbox" / "__pycache__" / "x.pyc").write_bytes(b"\x00")
    room = A.prepare_room_from_skills(claude / "skills", tmp_path / "room")
    assert not (room / "skills" / "toolbox" / "__pycache__").exists()


def test_audit_all_accepts_a_skills_dir_instead_of_a_plugin(tmp_path):
    claude = _loose(tmp_path)
    seen = []

    def runner(prompt, cwd, model, timeout):
        seen.append(str(cwd))
        return "NO FINDINGS"

    results = audit_all_via(tmp_path, claude, runner)
    assert results == {"toolbox": 0} and seen and seen[0].endswith("plugin")


def audit_all_via(tmp_path, claude, runner):
    return A.audit_all(None, tmp_path / "room", runner=runner, log=lambda *a: None,
                                  skills_dir=claude / "skills")


# ---- project-local skills: the repo they run in is reachable ------------------------------------

def _project_repo(tmp_path):
    """A git repo carrying a project-local skill that names a repo script and a missing doc."""
    import subprocess
    repo = tmp_path / "proj"
    skill = repo / ".claude" / "skills" / "bench"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "# bench\nRun `python scripts/run_bench.py`, then read docs/missing.md.\n", encoding="utf-8")
    (repo / "scripts").mkdir()
    (repo / "scripts" / "run_bench.py").write_text("SECRET_CONTENT = 1\n", encoding="utf-8")
    # A push from a linked worktree exports GIT_DIR, which git reads before -C: strip it.
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE",
                                                          "GIT_INDEX_FILE")}
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com",
           "-c", "commit.gpgsign=false"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
    subprocess.run([*git, "add", "scripts/run_bench.py", ".claude"], check=True, env=env)
    subprocess.run([*git, "commit", "-q", "-m", "x"], check=True, env=env)
    # Untracked and not ignored: a clone does not have it, so it must not resolve.
    (repo / "scripts" / "draft.py").write_text("X = 1\n", encoding="utf-8")
    return repo


def test_a_project_local_skills_dir_stages_the_repo_path_manifest(tmp_path):
    """A project-local skill runs from its repo root, so `scripts/run_bench.py` resolves there.
    Staging only the skills dir made every such path read DANGLING (5 of 11 findings on one real
    skill were this). The room carries the repo's PATHS - never their content - so the reviewer
    can tell a real dangling path from one that simply was not copied."""
    repo = _project_repo(tmp_path)
    room = A.prepare_room_from_skills(repo / ".claude" / "skills", tmp_path / "room")
    manifest = (room / A.REPO_MANIFEST).read_text(encoding="utf-8")
    assert "scripts/run_bench.py" in manifest.splitlines()
    assert "docs/missing.md" not in manifest
    # Tracked only: a skill naming a script that was never committed must read DANGLING, since
    # every other clone lacks it.
    assert "scripts/draft.py" not in manifest
    assert "SECRET_CONTENT" not in manifest
    assert not (room / "scripts").exists(), "the clean room still holds no repo content"


def test_a_skills_dir_outside_a_repo_gets_no_manifest(tmp_path):
    """`~/.claude/skills` also ends in `.claude/skills`; its owner is a home dir, not a repo."""
    claude = _loose(tmp_path)
    room = A.prepare_room_from_skills(claude / "skills", tmp_path / "room")
    assert not (room / A.REPO_MANIFEST).exists()


def test_a_project_local_review_is_told_the_repo_paths_resolve(tmp_path):
    repo = _project_repo(tmp_path)
    prompts = []

    def runner(prompt, cwd, model, timeout):
        prompts.append(prompt)
        return "NO FINDINGS"

    A.audit_all(None, tmp_path / "room", runner=runner, log=lambda *a: None,
                skills_dir=repo / ".claude" / "skills")
    flat = " ".join(prompts[0].split())
    assert A.REPO_MANIFEST in flat
    assert "PROJECT-LOCAL" in flat
    # Control: a plugin review keeps the install-unit contract and never mentions a manifest.
    assert A.REPO_MANIFEST not in A.build_prompt("x")


# ---- declined decisions -------------------------------------------------------------------------

def _ledger(skills, name, lines):
    """A skill `name` under `skills` with a decision ledger holding `lines`."""
    d = skills / name / ".skillwriter"
    d.mkdir(parents=True)
    (skills / name / "SKILL.md").write_text("# x\n", encoding="utf-8")
    (d / "decisions.jsonl").write_text("".join(json.dumps(e) + "\n" for e in lines),
                                       encoding="utf-8")


# The id is content-derived (`skill_decisions.entry_id`); a made-up one fails validation and the
# brief is then empty, so this literal must change whenever a field below does.
_REJECTED = {"v": 1, "id": "d-20261106-64c2bb95", "date": "2026-11-06", "kind": "rejected",
             "topic": "rebase", "decision": "Not adopted: rebase instead of merge.",
             "why": "a rebase rewrites a tagged commit", "evidence": {"tier": "argued", "text": "x"},
             "reopen_if": "releases stop tagging main", "anchors": [], "supersedes": [],
             "refs": [], "origin": "authored"}


def test_decision_brief_renders_a_rejected_entry(tmp_path):
    _ledger(tmp_path, "foo", [_REJECTED])
    notes = []
    brief = A.decision_brief(tmp_path, "foo", PLUGIN_HOOKS, log=notes.append)
    assert notes == []                    # a fixture the real module refuses would say so here
    assert "a rebase rewrites a tagged commit" in brief
    assert "releases stop tagging main" in brief


def test_decision_brief_is_empty_without_a_ledger(tmp_path):
    (tmp_path / "foo").mkdir()
    assert A.decision_brief(tmp_path, "foo", PLUGIN_HOOKS) == ""


def test_decision_brief_is_empty_and_says_so_when_the_ledger_is_broken(tmp_path):
    d = tmp_path / "foo" / ".skillwriter"
    d.mkdir(parents=True)
    (d / "decisions.jsonl").write_text("{not json\n", encoding="utf-8")
    notes = []
    assert A.decision_brief(tmp_path, "foo", PLUGIN_HOOKS, log=notes.append) == ""
    assert any("foo" in n for n in notes)


def test_decision_brief_is_empty_and_says_so_without_the_module(tmp_path):
    _ledger(tmp_path, "foo", [_REJECTED])
    notes = []
    assert A.decision_brief(tmp_path, "foo", tmp_path / "no-hooks", log=notes.append) == ""
    assert any("foo" in n for n in notes)


def test_decision_brief_renders_with_the_hooks_dir_it_is_given(tmp_path):
    """Two hooks dirs with different skill_decisions copies give two different briefs: a module
    loaded for one room is never reused for another."""
    _ledger(tmp_path / "skills", "foo", [_REJECTED])
    other = tmp_path / "other-hooks"
    shutil.copytree(PLUGIN_HOOKS, other, ignore=shutil.ignore_patterns("tests", "__pycache__"))
    module = other / "skill_decisions.py"
    text = module.read_text(encoding="utf-8")
    marker = "Decisions already taken for %s"
    assert text.count(marker) == 1, "the mutation below must apply exactly once"
    module.write_text(text.replace(marker, "OTHER COPY for %s"), encoding="utf-8")
    real = A.decision_brief(tmp_path / "skills", "foo", PLUGIN_HOOKS)
    copy = A.decision_brief(tmp_path / "skills", "foo", other)
    assert real.startswith("Decisions already taken for foo")
    assert copy.startswith("OTHER COPY for foo")


def _over_budget_ledger(skills, name, count=40):
    """A ledger of `count` rejected entries, each long enough that the brief's budget runs out."""
    sd = A._decisions_module(PLUGIN_HOOKS / "skill_decisions.py")
    entries = []
    for i in range(count):
        entry = dict(_REJECTED, topic="topic-%d" % i, decision="Not adopted: proposal %d." % i,
                     why="reason number %d, %s" % (i, "padding " * 60))
        entry["id"] = sd.entry_id(entry)
        entries.append(entry)
    _ledger(skills, name, entries)
    return entries


def test_decision_brief_trailer_names_a_command_that_runs_from_anywhere(tmp_path):
    """The 'more not shown' trailer is a command a reviewer can run in its room, which has no
    ledger: it names the interpreter, the script's absolute path and the source skill dir."""
    entries = _over_budget_ledger(tmp_path / "skills", "foo")
    brief = A.decision_brief(tmp_path / "skills", "foo", PLUGIN_HOOKS)
    assert "more not shown: " in brief
    command = brief.rsplit("more not shown: ", 1)[1].strip()
    elsewhere = tmp_path / "room"
    elsewhere.mkdir()
    done = subprocess.run(shlex.split(command), cwd=elsewhere, capture_output=True,
                          encoding="utf-8", errors="replace", timeout=60,
                          env={**os.environ, "PYTHONUTF8": "1"})
    assert done.returncode == 0, done.stderr
    last = entries[-1]["why"]
    assert last not in brief             # the entry the trailer stands for was cut from the brief
    assert last in done.stdout


def _fresh_hooks_copy(tmp_path, tail):
    """A copy of the plugin hooks whose skill_decisions.py ends with `tail`: new bytes, so the
    module is loaded afresh rather than taken from the cache keyed by content."""
    hooks = tmp_path / "hooks-copy"
    shutil.copytree(PLUGIN_HOOKS, hooks, ignore=shutil.ignore_patterns("tests", "__pycache__"))
    module = hooks / "skill_decisions.py"
    module.write_text(module.read_text(encoding="utf-8") + tail, encoding="utf-8")
    return hooks


def test_decision_brief_leaves_sys_path_as_it_found_it(tmp_path):
    _ledger(tmp_path / "skills", "foo", [_REJECTED])
    hooks = _fresh_hooks_copy(tmp_path, "\n# copy for %s\n" % tmp_path.name)
    before = list(sys.path)
    brief = A.decision_brief(tmp_path / "skills", "foo", hooks)
    assert "a rebase rewrites a tagged commit" in brief  # the load really ran
    assert sys.path == before


def test_decision_brief_leaves_sys_path_as_it_found_it_when_the_module_raises(tmp_path):
    _ledger(tmp_path / "skills", "foo", [_REJECTED])
    hooks = _fresh_hooks_copy(tmp_path, "\nraise RuntimeError('broken copy %s')\n" % tmp_path.name)
    before = list(sys.path)
    notes = []
    assert A.decision_brief(tmp_path / "skills", "foo", hooks, log=notes.append) == ""
    assert any("broken copy" in n for n in notes)       # it failed inside exec_module
    assert sys.path == before


def test_prompt_carries_the_brief_only_when_there_is_one():
    assert "DECIDED ALREADY" not in A.build_prompt("x")
    p = A.build_prompt("x", decisions="Decisions already taken for x: ...")
    assert "DECIDED ALREADY" in p and "Decisions already taken for x" in p


def test_audit_all_hands_each_reviewer_its_own_brief(tmp_path):
    plugin = tmp_path / "plugin-src"
    shutil.copytree(PLUGIN_HOOKS, plugin / "hooks",
                    ignore=shutil.ignore_patterns("tests", "__pycache__"))
    _ledger(plugin / "skills", "foo", [_REJECTED])
    (plugin / "skills" / "bar").mkdir()
    (plugin / "skills" / "bar" / "SKILL.md").write_text("# bar\n", encoding="utf-8")
    seen = {}

    def runner(prompt, cwd, model, timeout):
        name = "foo" if "skills/foo/" in prompt else "bar"
        seen[name] = prompt
        return "NO FINDINGS\n\nSkill gaps\nnone\n"

    A.audit_all(plugin, tmp_path / "room", jobs=1, runner=runner, log=lambda *_: None)
    assert "a rebase rewrites a tagged commit" in seen["foo"]
    assert "DECIDED ALREADY" not in seen["bar"]
    # The room leaves the ledger out; the brief came from the source dir.
    assert not (tmp_path / "room" / "plugin" / "skills" / "foo" / ".skillwriter").exists()
