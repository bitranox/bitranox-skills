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
