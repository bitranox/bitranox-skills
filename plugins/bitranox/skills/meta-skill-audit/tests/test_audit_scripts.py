"""Tests for the SCRIPT sweep in audit_skills.py. ASCII only.

The reviewer is injected at the `runner` seam, so these exercise the real module end to end with a
substitute reviewer rather than patching internals. Nothing here spawns `claude -p`."""

import re

import audit_skills as A


def _plugin(tmp_path):
    """A miniature plugin shaped like the real one: hooks, a skill with scripts and tests,
    a vendored demo, and every exclusion case."""
    root = tmp_path / "plugin"
    hooks = root / "hooks"
    (hooks / "tests").mkdir(parents=True, exist_ok=True)
    (hooks / "my-guard.py").write_text("import json, sys\nprint(1)\n", encoding="utf-8")
    (hooks / "shared_lib.py").write_text("VALUE = 1\n", encoding="utf-8")
    (hooks / "run-python.sh").write_text("#!/bin/sh\nexec python3 \"$@\"\n", encoding="utf-8")
    (hooks / "__init__.py").write_text("", encoding="utf-8")
    (hooks / "tests" / "conftest.py").write_text("", encoding="utf-8")
    (hooks / "tests" / "test_my_guard.py").write_text(
        "import my_guard\ndef test_x():\n    assert 1\n", encoding="utf-8")
    (hooks / "hooks.json").write_text(
        '{"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",'
        ' "command": "bash \\"${ROOT}/hooks/run-python.sh\\" \\"${ROOT}/hooks/my-guard.py\\""}]}]}}',
        encoding="utf-8")

    skill = root / "skills" / "alpha"
    (skill / "scripts").mkdir(parents=True, exist_ok=True)
    (skill / "tests").mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_text(
        "# alpha\nRun `gate.py --then CMD` to gate a command.\nSee notes.md.\n", encoding="utf-8")
    (skill / "notes.md").write_text("gate.py takes --then\n", encoding="utf-8")
    (skill / "scripts" / "gate.py").write_text("import sys\nprint('gate')\n", encoding="utf-8")
    (skill / "widget.js").write_text("export const x = 1;\n", encoding="utf-8")
    (skill / "tests" / "test_gate.py").write_text(
        "import gate\ndef test_g():\n    assert 1\n", encoding="utf-8")
    (skill / "__pycache__").mkdir(exist_ok=True)
    (skill / "__pycache__" / "gate.cpython-311.pyc").write_bytes(b"\x00")

    beta = root / "skills" / "beta"
    (beta / "demos" / "echo").mkdir(parents=True, exist_ok=True)
    (beta / "examples").mkdir(parents=True, exist_ok=True)
    beta.joinpath("SKILL.md").write_text("# beta\n", encoding="utf-8")
    (beta / "demos" / "echo" / "gate.py").write_text("# vendored, same basename\n", encoding="utf-8")
    (beta / "examples" / "sample.py").write_text("# vendored example\n", encoding="utf-8")
    return root


def _rels(targets):
    return [rel for rel, _kind in targets]


# ---- classification ----------------------------------------------------------------------------

def test_classify_script_covers_every_kind():
    assert A.classify_script("hooks/my-guard.py") == A.KIND_HOOK          # hyphen -> entry point
    assert A.classify_script("hooks/shared_lib.py") == A.KIND_HOOK_LIB    # underscore -> importable
    assert A.classify_script("hooks/run-python.sh") == A.KIND_SHIM
    assert A.classify_script("skills/alpha/scripts/gate.py") == A.KIND_SKILL_SCRIPT
    assert A.classify_script("skills/alpha/widget.js") == A.KIND_JS
    assert A.classify_script("skills/beta/demos/echo/gate.py") == A.KIND_VENDORED
    assert A.classify_script("skills/beta/examples/sample.py") == A.KIND_VENDORED


def test_classify_script_accepts_windows_separators():
    assert A.classify_script("hooks\\my-guard.py") == A.KIND_HOOK


# ---- report naming -----------------------------------------------------------------------------

def test_report_stem_is_path_derived_so_colliding_basenames_stay_distinct():
    """gate.py exists twice; a basename-derived report would silently overwrite one of them."""
    a = A.report_stem("skills/alpha/scripts/gate.py")
    b = A.report_stem("skills/beta/demos/echo/gate.py")
    assert a == "skills__alpha__scripts__gate" and b == "skills__beta__demos__echo__gate"
    assert a != b


def test_report_stem_strips_every_shipped_suffix():
    assert A.report_stem("hooks/run-python.sh") == "hooks__run-python"
    assert A.report_stem("skills/alpha/widget.js") == "skills__alpha__widget"


# ---- enumeration -------------------------------------------------------------------------------

def test_script_targets_finds_hooks_skill_scripts_and_js(tmp_path):
    rels = _rels(A.script_targets(_plugin(tmp_path)))
    assert "hooks/my-guard.py" in rels
    assert "hooks/shared_lib.py" in rels
    assert "hooks/run-python.sh" in rels
    assert "skills/alpha/scripts/gate.py" in rels
    assert "skills/alpha/widget.js" in rels


def test_script_targets_excludes_tests_dir(tmp_path):
    assert not [r for r in _rels(A.script_targets(_plugin(tmp_path))) if "/tests/" in r]


def test_script_targets_excludes_conftest_and_dunder_init(tmp_path):
    rels = _rels(A.script_targets(_plugin(tmp_path)))
    assert not [r for r in rels if r.endswith("conftest.py") or r.endswith("__init__.py")]


def test_script_targets_excludes_pycache(tmp_path):
    assert not [r for r in _rels(A.script_targets(_plugin(tmp_path))) if "__pycache__" in r]


def test_script_targets_excludes_vendored_demos_and_examples_by_default(tmp_path):
    rels = _rels(A.script_targets(_plugin(tmp_path)))
    assert not [r for r in rels if "/demos/" in r or "/examples/" in r]


def test_include_vendored_restores_them_tagged_as_vendored(tmp_path):
    targets = A.script_targets(_plugin(tmp_path), include_vendored=True)
    vendored = [rel for rel, kind in targets if kind == A.KIND_VENDORED]
    assert "skills/beta/demos/echo/gate.py" in vendored
    assert "skills/beta/examples/sample.py" in vendored


def test_only_filters_by_path_substring(tmp_path):
    rels = _rels(A.script_targets(_plugin(tmp_path), only=("my-guard",)))
    assert rels == ["hooks/my-guard.py"]
    rels = _rels(A.script_targets(_plugin(tmp_path), only=("skills/alpha/scripts",)))
    assert rels == ["skills/alpha/scripts/gate.py"]


def test_an_empty_only_is_not_a_filter(tmp_path):
    """Matches skill_names: `--only ""` splits to ("",) and must mean 'everything'."""
    root = _plugin(tmp_path)
    assert A.script_targets(root, only=("",)) == A.script_targets(root)


def test_kinds_restricts_the_slice(tmp_path):
    targets = A.script_targets(_plugin(tmp_path), kinds=(A.KIND_HOOK,))
    assert _rels(targets) == ["hooks/my-guard.py"]


def test_a_missing_room_enumerates_nothing(tmp_path):
    assert A.script_targets(tmp_path / "nope") == []


def test_exclusion_fallback_announces_itself(tmp_path):
    """A silently-degraded exclusion rule is how a sweep quietly reviews 300 vendored examples."""
    said = []
    root = tmp_path / "plugin"
    (root / "skills" / "alpha").mkdir(parents=True, exist_ok=True)          # no hooks/ -> harness_checks absent
    (root / "skills" / "alpha" / "x.py").write_text("x = 1\n", encoding="utf-8")
    A.script_targets(root, log=said.append)
    assert any("fallback exclusion" in s for s in said)


# ---- anchors, registration, mentions, tests ------------------------------------------------------

def test_doc_anchors_of_a_skill_script_lead_with_its_own_skill_md(tmp_path):
    anchors = A.doc_anchors(_plugin(tmp_path), "skills/alpha/scripts/gate.py", A.KIND_SKILL_SCRIPT)
    assert anchors[0] == "skills/alpha/SKILL.md"
    assert "skills/alpha/notes.md" in anchors
    assert not [a for a in anchors if a.startswith("skills/beta")]      # not a sibling's


def test_doc_anchors_of_a_hook_point_at_the_hook_contract(tmp_path):
    anchors = A.doc_anchors(_plugin(tmp_path), "hooks/my-guard.py", A.KIND_HOOK)
    assert "hooks/hooks.json" in anchors


def test_doc_anchors_skips_a_file_that_does_not_exist(tmp_path):
    """hooks/CLAUDE.md is optional; a missing anchor must be dropped, not crashed on."""
    anchors = A.doc_anchors(_plugin(tmp_path), "hooks/my-guard.py", A.KIND_HOOK)
    assert "hooks/CLAUDE.md" not in anchors


def test_hook_registration_returns_the_entry_for_a_registered_hook(tmp_path):
    reg = A.hook_registration(_plugin(tmp_path), "hooks/my-guard.py")
    assert reg and reg[0][0] == "PreToolUse" and reg[0][1] == "Bash"


def test_hook_registration_is_none_for_an_unregistered_hook(tmp_path):
    assert A.hook_registration(_plugin(tmp_path), "hooks/never-wired.py") is None


def test_mention_block_is_line_numbered_and_finds_the_doc_claim(tmp_path):
    root = _plugin(tmp_path)
    block = A.mention_block(root, "skills/alpha/scripts/gate.py", ["skills/alpha/SKILL.md"])
    assert "skills/alpha/SKILL.md:2:" in block and "--then" in block


def test_mention_block_truncates_at_the_limit(tmp_path):
    root = _plugin(tmp_path)
    (root / "skills" / "alpha" / "big.md").write_text("gate.py\n" * 200, encoding="utf-8")
    block = A.mention_block(root, "skills/alpha/scripts/gate.py", ["skills/alpha/big.md"], limit=5)
    assert block.count("big.md") == 5 and "truncated" in block


def test_mention_block_survives_an_unreadable_anchor(tmp_path):
    assert A.mention_block(_plugin(tmp_path), "x.py", ["skills/alpha/nope.md"]) == ""


def test_sibling_tests_finds_the_test_module_that_names_the_script(tmp_path):
    root = _plugin(tmp_path)
    assert A.sibling_tests(root, "skills/alpha/scripts/gate.py") == ["skills/alpha/tests/test_gate.py"]
    assert A.sibling_tests(root, "hooks/my-guard.py") == ["hooks/tests/test_my_guard.py"]


def test_sibling_tests_is_empty_when_nothing_names_it(tmp_path):
    assert A.sibling_tests(_plugin(tmp_path), "hooks/shared_lib.py") == []


# ---- prompt contract ---------------------------------------------------------------------------

def test_script_prompt_names_the_file_kind_tests_and_anchors():
    p = A.build_script_prompt("hooks/my-guard.py", A.KIND_HOOK, anchors=["hooks/hooks.json"],
                              tests=["hooks/tests/test_my_guard.py"])
    assert "hooks/my-guard.py" in p and A.KIND_HOOK in p
    assert "hooks/tests/test_my_guard.py" in p and "hooks/hooks.json" in p


def test_script_prompt_demands_exhibit_and_exactly_one_of_repro_or_trace():
    flat = " ".join(A.build_script_prompt("x.py", A.KIND_SKILL_SCRIPT).split())
    assert "EXHIBIT:" in flat and "REPRO:" in flat and "TRACE:" in flat
    assert "EXACTLY ONE of REPRO or TRACE" in flat
    assert "assertion wearing evidence's clothes" in flat
    assert "character for character" in flat


def test_script_prompt_lists_every_class_exactly_once_and_no_others():
    """Guards against a class quietly vanishing, or a stray one appearing, in a later edit."""
    p = A.build_script_prompt("x.py", A.KIND_SKILL_SCRIPT)
    listed = re.findall(r"^\d+\. ([A-Z][A-Z-]+) - ", p, re.M)
    assert listed == list(A.SCRIPT_CLASSES)


def test_script_prompt_states_the_prepass_hits_are_already_known():
    p = A.build_script_prompt("x.py", A.KIND_SKILL_SCRIPT, prepass=["line 9: text=True"])
    assert "DO NOT RE-REPORT" in p and "line 9: text=True" in p


def test_a_hook_prompt_carries_the_fail_open_convention_and_a_tool_prompt_does_not():
    """The single most important paragraph in the sweep: 46 of 63 hooks share the benign shape,
    and a reviewer not told so files 46 false positives."""
    hook = A.build_script_prompt("hooks/my-guard.py", A.KIND_HOOK)
    tool = A.build_script_prompt("skills/alpha/scripts/gate.py", A.KIND_SKILL_SCRIPT)
    assert "IT IS NOT A FINDING" in hook and "fails OPEN by design" in hook
    assert "IT IS NOT A FINDING" not in tool
    assert "must fail LOUD" in tool                     # and the opposite rule is stated instead


def test_a_hook_prompt_says_how_to_feed_it_stdin():
    """A bare `python3 hooks/x.py` blocks until the timeout, once per hook."""
    hook = A.build_script_prompt("hooks/my-guard.py", A.KIND_HOOK)
    assert "BLOCKS FOREVER" in hook and "echo '{}' | python3" in hook


def test_a_hook_prompt_carries_its_registration_line():
    p = A.build_script_prompt("hooks/my-guard.py", A.KIND_HOOK,
                              registration=[("PreToolUse", "Bash", "bash run-python.sh guard.py")])
    assert "PreToolUse | matcher: Bash" in p


def test_an_unregistered_hook_is_flagged_in_its_own_prompt():
    p = A.build_script_prompt("hooks/orphan-guard.py", A.KIND_HOOK, registration=None)
    assert "NOT registered" in p and "never fire" in p


def test_a_mutating_script_is_told_not_to_run():
    """These reconfigure firewalls and rmtree caches; the deny must be visible in the report."""
    assert "DO NOT RUN THIS SCRIPT AT ALL" in A.build_script_prompt(
        "skills/x/scripts/pfsense.py", A.KIND_SKILL_SCRIPT)
    assert "DO NOT RUN THIS SCRIPT AT ALL" not in A.build_script_prompt(
        "skills/x/scripts/newest.py", A.KIND_SKILL_SCRIPT)


def test_script_prompt_tolerates_json_braces():
    """`str.format` would raise KeyError on a hook's JSON output; this template must not."""
    p = A.build_script_prompt("hooks/x.py", A.KIND_HOOK, prepass=['{"hookSpecificOutput": 1}'])
    assert '{"hookSpecificOutput": 1}' in p


def test_the_skill_prompt_is_untouched():
    """The proof that the script sweep was additive."""
    p = A.build_prompt("compuse-git", prefix="acme")
    assert "this whole directory is the installed plugin" in p and "`acme:<name>`" in p
    assert "EXHIBIT:" not in p and "Skill gaps" in p


# ---- evidence post-pass -------------------------------------------------------------------------

def _report(path, lineno, body):
    return ("FINDING: BUG | %s:%d | claim\nEXHIBIT:\n  %d: %s\nWHY: z\nCONFIDENCE: VERIFIED\n"
            % (path, lineno, lineno, body))


def test_evidence_accepts_a_verbatim_exhibit_at_the_right_line(tmp_path):
    root = _plugin(tmp_path)
    text = _report("hooks/shared_lib.py", 1, "VALUE = 1")
    assert A.evidence_problems(text, root) == []


def test_evidence_rejects_an_exhibit_that_is_not_in_the_file(tmp_path):
    """The fabricated-finding case: the classic failure is a real-looking line that was invented."""
    root = _plugin(tmp_path)
    problems = A.evidence_problems(_report("hooks/shared_lib.py", 1, "VALUE = 999"), root)
    assert problems and "does not match" in problems[0]


def test_evidence_rejects_a_line_number_past_end_of_file(tmp_path):
    problems = A.evidence_problems(_report("hooks/shared_lib.py", 99, "VALUE = 1"), _plugin(tmp_path))
    assert problems and "past end of file" in problems[0]


def test_evidence_rejects_a_path_that_is_not_in_the_room(tmp_path):
    problems = A.evidence_problems(_report("hooks/imaginary.py", 1, "x = 1"), _plugin(tmp_path))
    assert problems and "no such file" in problems[0]


def test_evidence_of_a_clean_report_is_empty(tmp_path):
    assert A.evidence_problems("NO FINDINGS", _plugin(tmp_path)) == []
    assert A.evidence_problems("", _plugin(tmp_path)) == []
    assert A.evidence_problems(None, _plugin(tmp_path)) == []


def test_count_by_class_counts_per_class_and_zeroes_the_rest():
    text = ("FINDING: BUG | a.py:1 | x\nFINDING: BUG | a.py:2 | y\n"
            "FINDING: SECURITY | b.py:3 | z\n")
    counts = A.count_by_class(text)
    assert counts["BUG"] == 2 and counts["SECURITY"] == 1 and counts["DEAD"] == 0


# ---- room manifest ------------------------------------------------------------------------------

def test_manifest_drift_catches_a_reviewer_editing_the_room(tmp_path):
    """A reviewer that 'fixes' a shared module makes every later reviewer read a different program."""
    root = _plugin(tmp_path)
    before = A.room_manifest(root)
    (root / "hooks" / "shared_lib.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "hooks" / "new.py").write_text("x = 1\n", encoding="utf-8")
    drift = A.manifest_drift(before, A.room_manifest(root))
    assert "CHANGED hooks/shared_lib.py" in drift and "ADDED   hooks/new.py" in drift


def test_manifest_drift_of_an_untouched_room_is_empty(tmp_path):
    root = _plugin(tmp_path)
    assert A.manifest_drift(A.room_manifest(root), A.room_manifest(root)) == []


# ---- end to end through the injected reviewer ----------------------------------------------------

def test_audit_scripts_writes_one_report_per_target_with_a_path_derived_stem(tmp_path):
    src = _plugin(tmp_path)
    res = A.audit_scripts(src, tmp_path / "room", jobs=2, log=lambda *_a: None,
                          runner=lambda *_a: "NO FINDINGS")
    reports = tmp_path / "room" / "reports"
    assert "skills/alpha/scripts/gate.py" in res
    assert (reports / "skills__alpha__scripts__gate.audit.txt").is_file()
    assert (reports / "hooks__my-guard.audit.txt").is_file()
    assert len(list(reports.glob("*.audit.txt"))) == len(res)      # nothing silently overwritten


def test_audit_scripts_counts_findings(tmp_path):
    src = _plugin(tmp_path)

    def runner(prompt, cwd, model, timeout):
        if "shared_lib" in prompt:
            return _report("hooks/shared_lib.py", 1, "VALUE = 1")
        return "NO FINDINGS"

    res = A.audit_scripts(src, tmp_path / "room", jobs=2, runner=runner, log=lambda *_a: None)
    assert res["hooks/shared_lib.py"] == 1
    assert res["hooks/my-guard.py"] == 0


def test_every_script_reviewer_runs_with_the_room_as_cwd(tmp_path):
    """Never the live tree: that is the contamination the clean room exists to prevent."""
    src = _plugin(tmp_path)
    cwds = []

    def runner(prompt, cwd, model, timeout):
        cwds.append(str(cwd))
        return "NO FINDINGS"

    A.audit_scripts(src, tmp_path / "room", jobs=1, runner=runner, log=lambda *_a: None)
    assert cwds and all(c == str(tmp_path / "room" / "plugin") for c in cwds)


def test_a_script_reviewer_timeout_is_recorded_not_swallowed(tmp_path):
    src = _plugin(tmp_path)
    A.audit_scripts(src, tmp_path / "room", jobs=1, only=("shared_lib",), log=lambda *_a: None,
                    runner=lambda *_a: "(TIMEOUT after 1500s)")
    body = (tmp_path / "room" / "reports" / "hooks__shared_lib.audit.txt").read_text(encoding="utf-8")
    assert "TIMEOUT" in body                          # a silent zero would read as 'clean'


def test_unverifiable_evidence_is_appended_not_deleted(tmp_path):
    """Deleting a bad finding hides a malfunctioning reviewer; the count is the signal."""
    src = _plugin(tmp_path)
    A.audit_scripts(src, tmp_path / "room", jobs=1, only=("shared_lib",), log=lambda *_a: None,
                    runner=lambda *_a: _report("hooks/shared_lib.py", 1, "VALUE = 999"))
    body = (tmp_path / "room" / "reports" / "hooks__shared_lib.audit.txt").read_text(encoding="utf-8")
    assert "UNVERIFIABLE EVIDENCE:" in body and "FINDING: BUG" in body


def test_skip_existing_resumes_without_re_reviewing(tmp_path):
    src = _plugin(tmp_path)
    reports = tmp_path / "room" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "hooks__shared_lib.audit.txt").write_text("NO FINDINGS", encoding="utf-8")
    (reports / "hooks__my-guard.audit.txt").write_text("", encoding="utf-8")   # empty -> redo
    seen = []

    def runner(prompt, cwd, model, timeout):
        seen.append(prompt.splitlines()[0])
        return "NO FINDINGS"

    A.audit_scripts(src, tmp_path / "room", jobs=1, runner=runner, log=lambda *_a: None,
                    reuse=True, skip_existing=True)
    joined = " ".join(seen)
    assert "shared_lib.py" not in joined              # already had a non-empty report
    assert "my-guard.py" in joined                    # empty report is not a result


def test_concurrency_does_not_change_the_report_set(tmp_path):
    src = _plugin(tmp_path)
    one = A.audit_scripts(src, tmp_path / "r1", jobs=1, log=lambda *_a: None,
                          runner=lambda *_a: "NO FINDINGS")
    many = A.audit_scripts(src, tmp_path / "r8", jobs=8, log=lambda *_a: None,
                           runner=lambda *_a: "NO FINDINGS")
    assert one == many


def test_the_prepass_hits_reach_the_right_target_only(tmp_path):
    src = _plugin(tmp_path)
    seen = {}

    def runner(prompt, cwd, model, timeout):
        seen["guard" if "my-guard.py" in prompt.splitlines()[0] else "other"] = prompt
        return "NO FINDINGS"

    A.audit_scripts(src, tmp_path / "room", jobs=1, runner=runner, log=lambda *_a: None,
                    prepass={"hooks/my-guard.py": ["line 1: text=True without encoding"]})
    assert "text=True without encoding" in seen["guard"]
    assert "text=True without encoding" not in seen["other"]
