"""Tests for audit_skills.py (the clean-room skill auditor). ASCII only.

The reviewer is injected at the `runner` seam, so these exercise the real module end to end with a
substitute reviewer rather than patching internals."""

import audit_skills as A


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
