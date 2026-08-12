"""Which skill dirs the local-harness audit may touch, and which another gate already owns.

Every case here is built under `tmp_path`. The real machine's paths are deliberately absent: a
test asserting `/media/srv-main-softdev/...` passes on one machine and fails in CI, which makes it
a report about the author's disk rather than about the rule. The `targets` verb is how a real
selection gets eyeballed.
"""

import json
import os
import shutil
import subprocess
import types

import pytest

import harness_checks as hc


def _skills(parent, *names):
    """A `<parent>/skills` dir holding one SKILL.md per name. Returns the skills dir."""
    d = parent / "skills"
    for n in names or ("demo",):
        (d / n).mkdir(parents=True)
        (d / n / "SKILL.md").write_text("---\nname: %s\n---\n" % n, encoding="utf-8")
    return d


def _manifest(root, kind):
    """Mark `root` as plugin-owned the way a real plugin or marketplace repo does."""
    (root / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (root / ".claude-plugin" / kind).write_text("{}", encoding="utf-8")
    return root


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          cwd=str(cwd), capture_output=True, text=True, check=True)


needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


# --- owning_plugin: the ancestor walk -------------------------------------------------------

def test_owning_plugin_finds_a_plugin_manifest_ancestor(tmp_path):
    repo = _manifest(tmp_path / "tool-repo", "plugin.json")
    assert hc.owning_plugin(_skills(repo)) == repo


def test_owning_plugin_finds_a_marketplace_manifest_ancestor(tmp_path):
    repo = _manifest(tmp_path / "market-repo", "marketplace.json")
    assert hc.owning_plugin(_skills(repo)) == repo


def test_owning_plugin_finds_the_nearest_owner_not_the_outermost(tmp_path):
    """A marketplace repo that also ships the plugin nests two manifests; the inner one owns."""
    outer = _manifest(tmp_path / "market", "marketplace.json")
    inner = _manifest(outer / "plugins" / "bitranox", "plugin.json")
    assert hc.owning_plugin(_skills(inner)) == inner


def test_owning_plugin_returns_none_for_an_ordinary_project(tmp_path):
    proj = tmp_path / "proj" / ".claude"
    assert hc.owning_plugin(_skills(proj)) is None


# --- is_shipped: the selection rule ---------------------------------------------------------

def test_marketplace_source_repo_is_shipped(tmp_path):
    """The writable source checkout. repo-gate and meta-skill-audit already own it."""
    repo = _manifest(tmp_path / "bitranox-skills", "marketplace.json")
    plugin = _manifest(repo / "plugins" / "bitranox", "plugin.json")
    assert hc.is_shipped(_skills(plugin, "coding-python-uv"), home=tmp_path / "home") is True


def test_tool_repo_mirror_is_shipped(tmp_path):
    """A tool repo shipping its own twin. Editing it outside the mirror ritual creates drift."""
    repo = _manifest(tmp_path / "igittigitt", "plugin.json")
    assert hc.is_shipped(_skills(repo, "python-gitignore"), home=tmp_path / "home") is True


def test_anything_under_the_plugins_dir_is_shipped_even_without_a_manifest(tmp_path):
    """The version cache and the marketplace clone are installed copies, not editable sources."""
    home = tmp_path / "home"
    cached = home / ".claude" / "plugins" / "cache" / "bitranox-skills" / "bitranox" / "5.143.0"
    assert hc.is_shipped(_skills(cached, "meta-skill-audit"), home=home) is True


def test_personal_skills_dir_is_not_shipped(tmp_path):
    home = tmp_path / "home"
    assert hc.is_shipped(_skills(home / ".claude", "toolbox"), home=home) is False


def test_project_skills_dir_is_not_shipped(tmp_path):
    home = tmp_path / "home"
    proj = tmp_path / "work" / "provmm-umbrella" / ".claude"
    assert hc.is_shipped(_skills(proj, "provmm-build"), home=home) is False


def test_a_project_inside_a_plugin_repo_is_shipped(tmp_path):
    """The hazard the ownership rule exists for: a marketplace repo checked out in the tree."""
    repo = _manifest(tmp_path / "work" / "bitranox-skills", "marketplace.json")
    assert hc.is_shipped(_skills(repo / ".claude", "local-helper"), home=tmp_path / "home") is True


# --- select_targets: filtering and worktree de-duplication ----------------------------------

def test_select_targets_keeps_local_and_drops_shipped(tmp_path):
    home = tmp_path / "home"
    local = _skills(home / ".claude", "toolbox")
    proj = _skills(tmp_path / "work" / "semdex" / ".claude", "bench-rerun")
    shipped = _skills(_manifest(tmp_path / "igittigitt", "plugin.json"), "python-gitignore")
    got = hc.select_targets([local, proj, shipped], home=home)
    assert got == sorted([local, proj])


def test_select_targets_is_empty_when_everything_is_shipped(tmp_path):
    shipped = _skills(_manifest(tmp_path / "repo", "plugin.json"), "x")
    assert hc.select_targets([shipped], home=tmp_path / "home") == []


@needs_git
def test_select_targets_audits_a_worktree_copy_only_once(tmp_path):
    """A linked worktree is a second checkout of one repo, so the same SKILL.md sits at two
    paths. Auditing both spends a reviewer twice and reports every finding twice."""
    repo = tmp_path / "semdex"
    _skills(repo / ".claude", "bench-rerun")
    _git(repo.parent, "init", "-q", "-b", "main", str(repo))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "seed")
    wt = repo / ".claude" / "worktrees" / "chunk-sanitize"
    _git(repo, "worktree", "add", "-q", str(wt), "-b", "side")

    main_skills = repo / ".claude" / "skills"
    wt_skills = wt / ".claude" / "skills"
    assert wt_skills.is_dir(), "worktree checkout should carry the same skills dir"

    got = hc.select_targets([main_skills, wt_skills], home=tmp_path / "home")
    assert got == [main_skills], "the main checkout wins, the linked worktree is dropped"


@needs_git
def test_select_targets_keeps_two_unrelated_repos_with_identical_layout(tmp_path):
    """De-duplication keys on repository identity, not on the path shape or the skill names."""
    kept = []
    for name in ("alpha", "beta"):
        repo = tmp_path / name
        _skills(repo / ".claude", "bench-rerun")
        _git(repo.parent, "init", "-q", "-b", "main", str(repo))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "seed")
        kept.append(repo / ".claude" / "skills")
    assert hc.select_targets(kept, home=tmp_path / "home") == sorted(kept)


def test_select_targets_dedupes_a_repeated_path(tmp_path):
    home = tmp_path / "home"
    local = _skills(home / ".claude", "toolbox")
    assert hc.select_targets([local, local], home=home) == [local]


# --- discover_candidates: where it looks, and where it refuses to ---------------------------

def test_discover_finds_project_and_personal_skills_dirs(tmp_path):
    home = tmp_path / "home"
    personal = _skills(home / ".claude", "toolbox")
    proj = _skills(tmp_path / "work" / "provmm" / ".claude", "provmm-build")
    got = hc.discover_candidates([tmp_path / "work"], home=home)
    assert personal in got and proj in got


def test_discover_ignores_a_plugins_skills_dir(tmp_path):
    """A plugin's own `skills/` is reachable only through the plugin, where another gate owns it."""
    home = tmp_path / "home"
    _skills(_manifest(tmp_path / "work" / "igittigitt", "plugin.json"), "python-gitignore")
    assert hc.discover_candidates([tmp_path / "work"], home=home) == []


def test_discover_does_not_descend_into_the_installed_plugins_dir(tmp_path):
    home = tmp_path / "home"
    cached = home / ".claude" / "plugins" / "cache" / "mkt" / "plug" / "1.0.0"
    _skills(cached / ".claude", "shipped-skill")
    assert hc.discover_candidates([home / ".claude"], home=home) == []


def test_discover_skips_a_skills_dir_holding_no_skill_md(tmp_path):
    """RISscraper ships an empty `.claude/skills`; an empty dir is not a target."""
    home = tmp_path / "home"
    (tmp_path / "work" / "risscraper" / ".claude" / "skills").mkdir(parents=True)
    assert hc.discover_candidates([tmp_path / "work"], home=home) == []


def test_discover_can_leave_the_personal_dir_out(tmp_path):
    """The per-tree dream audits one tree; the personal dir is the crosstree pass's business."""
    home = tmp_path / "home"
    _skills(home / ".claude", "toolbox")
    proj = _skills(tmp_path / "work" / "provmm" / ".claude", "provmm-build")
    assert hc.discover_candidates([tmp_path / "work"], home=home, personal=False) == [proj]


# --- skip_reason: a dropped candidate has to say why ----------------------------------------

def test_skip_reason_is_none_for_a_real_target(tmp_path):
    home = tmp_path / "home"
    assert hc.skip_reason(_skills(home / ".claude", "toolbox"), home=home) is None


def test_skip_reason_names_the_owning_plugin(tmp_path):
    repo = _manifest(tmp_path / "igittigitt", "plugin.json")
    reason = hc.skip_reason(_skills(repo, "python-gitignore"), home=tmp_path / "home")
    assert reason is not None and str(repo) in reason


def test_skip_reason_calls_out_installed_plugin_content(tmp_path):
    home = tmp_path / "home"
    cached = home / ".claude" / "plugins" / "cache" / "mkt" / "plug" / "1.0.0"
    reason = hc.skip_reason(_skills(cached, "shipped"), home=home)
    assert reason is not None and "plugins" in reason


def test_discover_returns_sorted_unique_paths(tmp_path):
    home = tmp_path / "home"
    for name in ("b-proj", "a-proj"):
        _skills(tmp_path / "work" / name / ".claude", "s")
    got = hc.discover_candidates([tmp_path / "work", tmp_path / "work"], home=home)
    assert got == sorted(set(got)) and len(got) == 2


# --- lifted from repo-gate: the same rules, now reaching unshipped skills too ----------------

def test_ships_scripts_sees_a_runnable_module(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "tool.py").write_text("x = 1\n", encoding="utf-8")
    assert hc.ships_scripts(tmp_path) is True


@pytest.mark.parametrize("rel", ["tests/test_x.py", "demos/demo.py", "examples/ex.py",
                                 "conftest.py", "__init__.py"])
def test_ships_scripts_ignores_fixtures_and_demos(tmp_path, rel):
    target = tmp_path / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("x = 1\n", encoding="utf-8")
    assert hc.ships_scripts(tmp_path) is False


def test_has_tests_ignores_a_test_that_only_demos(tmp_path):
    (tmp_path / "examples").mkdir()
    (tmp_path / "examples" / "test_demo.py").write_text("def test_a(): pass\n", encoding="utf-8")
    assert hc.has_tests(tmp_path) is False


def test_packages_missing_tests_flags_only_the_untested_one(tmp_path):
    tested, bare = tmp_path / "tested", tmp_path / "bare"
    for pkg in (tested, bare):
        (pkg / "scripts").mkdir(parents=True)
        (pkg / "scripts" / "tool.py").write_text("x = 1\n", encoding="utf-8")
    (tested / "tests").mkdir()
    (tested / "tests" / "test_tool.py").write_text("def test_a(): pass\n", encoding="utf-8")
    assert hc.packages_missing_tests([tested, bare]) == [bare]


def _skill_md(tmp_path, body):
    path = tmp_path / "SKILL.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_frontmatter_description_joins_a_wrapped_value(tmp_path):
    md = _skill_md(tmp_path, "---\nname: x\ndescription: Use when parsing\n  a wrapped line\n---\n")
    assert hc.frontmatter_description(md) == "Use when parsing a wrapped line"


def test_frontmatter_name_and_description_return_none_without_frontmatter(tmp_path):
    md = _skill_md(tmp_path, "# just a heading\n")
    assert hc.frontmatter_description(md) is None and hc.frontmatter_name(md) is None


def test_frontmatter_name_reads_the_name(tmp_path):
    md = _skill_md(tmp_path, "---\nname: toolbox\ndescription: Use when x\n---\n")
    assert hc.frontmatter_name(md) == "toolbox"


@pytest.mark.parametrize("desc,fragment", [
    (">- Use when folded", "single-line plain YAML scalar"),
    ('"Use when quoted here"', "single-line plain YAML scalar"),
    ("Formats markdown tables nicely", "trigger-first"),
    ("Use when you can", "distinctive keywords"),
])
def test_cso_failures_for_rejects(desc, fragment):
    fails = hc.cso_failures_for("skills/demo", desc)
    assert len(fails) == 1 and fragment in fails[0] and fails[0].startswith("skills/demo: ")


def test_cso_failures_for_accepts_a_good_description():
    good = ("Use when parsing gitignore files, filtering paths, or reaching for pathspec "
            "instead of the igittigitt library")
    assert hc.cso_failures_for("skills/demo", good) == []


# --- hook registrations -----------------------------------------------------------------------

def _settings(tmp_path, command, event="PreToolUse"):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"hooks": {event: [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": command}]}]}}), encoding="utf-8")
    return path


def test_hook_registrations_reads_event_matcher_and_command(tmp_path):
    path = _settings(tmp_path, "bash /x/y.sh", event="Stop")
    assert hc.hook_registrations(path) == [("Stop", "Bash", "bash /x/y.sh")]


def test_hook_registrations_is_empty_for_a_settings_file_without_hooks(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"model": "opus"}', encoding="utf-8")
    assert hc.hook_registrations(path) == []


def test_registration_problems_flags_a_missing_target(tmp_path):
    path = _settings(tmp_path, "bash %s/gone.sh" % tmp_path)
    problems = hc.registration_problems(path, home=tmp_path)
    assert len(problems) == 1 and problems[0][2].endswith("gone.sh")


def test_registration_problems_passes_an_existing_target(tmp_path):
    (tmp_path / "here.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    path = _settings(tmp_path, "bash %s/here.sh" % tmp_path)
    assert hc.registration_problems(path, home=tmp_path) == []


def test_registration_problems_expands_a_home_relative_target(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "h.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    assert hc.registration_problems(_settings(tmp_path, "bash ~/.claude/h.sh"), home=tmp_path) == []


def test_command_paths_ignores_a_quoted_non_path_argument():
    """The real sound hook pipes jq with a filter that must not be mistaken for a path."""
    command = ("jq -e '.error // .tool_result.error' > /dev/null 2>&1 "
               "&& paplay /usr/share/sounds/claude/error.wav || true")
    assert hc.command_paths(command) == ["/dev/null", "/usr/share/sounds/claude/error.wav"]


def test_command_paths_skips_an_unresolved_variable():
    assert hc.command_paths('bash "${CLAUDE_PLUGIN_ROOT}/hooks/x.py"') == []


# --- retired shims ----------------------------------------------------------------------------

GOOD_SHIM = ('#!/usr/bin/env python3\n"""RETIRED 2026-08-02. The plugin ships this now.\n\n'
             'Replacement: plugins/bitranox/hooks/venv-guard.py\n"""\nimport sys\n'
             'sys.stderr.write("retired\\n")\nraise SystemExit(2)\n')


def test_is_retired_shim_recognises_the_marker(tmp_path):
    path = tmp_path / "venv-guard.py"
    path.write_text(GOOD_SHIM, encoding="utf-8")
    assert hc.is_retired_shim(path) is True


def test_is_retired_shim_is_false_for_a_live_hook(tmp_path):
    path = tmp_path / "live-guard.py"
    path.write_text("#!/usr/bin/env python3\nprint('hi')\n", encoding="utf-8")
    assert hc.is_retired_shim(path) is False


def test_a_well_formed_shim_has_no_problems(tmp_path):
    """The control: all four real shims pass, so the check cannot only ever say no."""
    path = tmp_path / "venv-guard.py"
    path.write_text(GOOD_SHIM, encoding="utf-8")
    path.chmod(0o644)
    assert hc.shim_problems(path) == []


def test_shim_problems_flags_an_executable_tombstone(tmp_path):
    path = tmp_path / "s.py"
    path.write_text(GOOD_SHIM, encoding="utf-8")
    path.chmod(0o755)
    assert any("executable" in p for p in hc.shim_problems(path))


def test_shim_problems_flags_a_shim_that_exits_zero(tmp_path):
    path = tmp_path / "s.py"
    path.write_text('"""RETIRED. Replacement: other.py"""\nraise SystemExit(0)\n', encoding="utf-8")
    path.chmod(0o644)
    assert any("non-zero" in p for p in hc.shim_problems(path))


def test_shim_problems_flags_one_that_is_still_registered(tmp_path):
    path = tmp_path / "s.py"
    path.write_text(GOOD_SHIM, encoding="utf-8")
    path.chmod(0o644)
    assert any("registered" in p for p in hc.shim_problems(path, registered=[str(path)]))


# --- orphan scripts ----------------------------------------------------------------------------

def test_orphan_scripts_flags_an_unregistered_entry_point(tmp_path):
    (tmp_path / "my-guard.py").write_text("print(1)\n", encoding="utf-8")
    assert hc.orphan_scripts(tmp_path) == [tmp_path / "my-guard.py"]


def test_orphan_scripts_exempts_a_library_and_a_registered_hook_and_a_shim(tmp_path):
    (tmp_path / "shared_lib.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "wired-hook.py").write_text("print(1)\n", encoding="utf-8")
    (tmp_path / "dead-hook.py").write_text(GOOD_SHIM, encoding="utf-8")
    got = hc.orphan_scripts(tmp_path, registered=[str(tmp_path / "wired-hook.py")])
    assert got == []


# --- tests that cannot be collected ------------------------------------------------------------

def test_uncollectable_tests_catches_a_module_that_dies_on_import(tmp_path):
    """Exactly the real defect: a test importing a file that raises SystemExit at import time."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_dead.py").write_text("raise SystemExit(2)\n", encoding="utf-8")
    problems = hc.uncollectable_tests(tests)
    assert problems and "test_dead" in problems[0][0]


def test_uncollectable_tests_is_quiet_for_a_healthy_suite(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    assert hc.uncollectable_tests(tests) == []


def test_uncollectable_tests_is_quiet_for_an_empty_dir(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    assert hc.uncollectable_tests(tests) == []


# --- the uv fallback, for when the launching interpreter itself lacks pytest -------------------
#
# `run` and `resolve_uv` are the real seams: the two collaborators uncollectable_tests reaches
# outside itself (a subprocess, a PATH lookup). Injecting fakes here exercises the actual
# decision logic instead of monkeypatching subprocess.run or shutil.which inside the module.

def _missing_pytest():
    return types.SimpleNamespace(returncode=1, stdout="",
                                 stderr="ModuleNotFoundError: No module named pytest")


def _clean_collection():
    return types.SimpleNamespace(returncode=0, stdout="3 tests collected\n", stderr="")


def _fake_pytest_run(*outcomes):
    """A `run` fake that returns (or raises) each of `outcomes` in call order, and records every
    call so a test can prove the fallback actually fired rather than being skipped."""
    remaining = list(outcomes)
    calls = []

    def run(argv, timeout):
        calls.append((list(argv), timeout))
        outcome = remaining.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    run.calls = calls
    return run


def test_uncollectable_tests_falls_back_to_uv_when_the_launching_interpreter_lacks_pytest(tmp_path):
    """The checker's own interpreter missing pytest must not end the check: it retries under
    `uv run --with pytest`, and a clean collection there means no finding at all - the target was
    actually measured, not guessed at."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    run = _fake_pytest_run(_missing_pytest(), _clean_collection())
    problems = hc.uncollectable_tests(tests, run=run, resolve_uv=lambda: "/usr/bin/uv")
    assert problems == []
    assert len(run.calls) == 2, "the uv fallback must actually run, not just get considered"
    fallback_argv = run.calls[1][0]
    assert fallback_argv[:4] == ["/usr/bin/uv", "run", "--with", "pytest"]


def test_uncollectable_tests_uv_fallback_still_reports_a_real_collection_failure(tmp_path):
    """A target whose tests genuinely fail to collect must still be a finding after the fallback -
    the fallback answers the question honestly, it does not launder a real defect into a pass."""
    tests = tmp_path / "tests"
    tests.mkdir()
    broken = types.SimpleNamespace(
        returncode=2, stdout="", stderr="ERROR tests/test_broken.py\nE   ImportError: nope\n")
    run = _fake_pytest_run(_missing_pytest(), broken)
    problems = hc.uncollectable_tests(tests, run=run, resolve_uv=lambda: "/usr/bin/uv")
    assert len(problems) == 1
    path, _message, unmeasured = problems[0]
    assert "test_broken" in path
    assert unmeasured is False


def test_uncollectable_tests_reports_unmeasured_not_a_finding_when_uv_fallback_times_out(tmp_path):
    """A timeout in the fallback is neither "collects fine" nor "pytest missing" - it is a
    distinct, honestly-labelled failure of the CHECK itself, not a defect of the target."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    run = _fake_pytest_run(_missing_pytest(), subprocess.TimeoutExpired(cmd=["uv"], timeout=240))
    problems = hc.uncollectable_tests(tests, run=run, resolve_uv=lambda: "/usr/bin/uv")
    assert len(problems) == 1
    _path, message, unmeasured = problems[0]
    assert unmeasured is True
    assert "timed out" in message
    assert "collects fine" not in message and "not installed" not in message


def test_uncollectable_tests_reports_unmeasured_when_uv_is_not_on_path(tmp_path):
    """When the fallback itself is unavailable (no uv on PATH), say so accurately instead of
    repeating the plain "pytest not installed" line as if nothing else had been tried."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_ok.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    run = _fake_pytest_run(_missing_pytest())
    problems = hc.uncollectable_tests(tests, run=run, resolve_uv=lambda: None)
    assert len(problems) == 1
    _path, message, unmeasured = problems[0]
    assert unmeasured is True
    assert "uv" in message.lower()
    assert len(run.calls) == 1, "must not shell out to a fallback with nothing to run it"


# --- unmanaged twins ----------------------------------------------------------------------------

def test_unmanaged_twins_matches_a_local_copy_of_a_shipped_skill(tmp_path):
    desc = ("Use when parsing .gitignore files, deciding whether paths are ignored, or "
            "filtering large numbers of files in gitignore style with igittigitt.")
    local = _skills(tmp_path / "local")
    (local / "demo" / "SKILL.md").write_text("---\nname: demo\ndescription: %s\n---\n" % desc,
                                             encoding="utf-8")
    got = hc.unmanaged_twins(local, {"coding-python-gitignore": desc})
    assert got and got[0][0] == "demo" and got[0][1] == "coding-python-gitignore"


def test_unmanaged_twins_leaves_an_unrelated_local_skill_alone(tmp_path):
    local = _skills(tmp_path / "local")
    (local / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Use when benchmarking the nightly sweep run.\n---\n",
        encoding="utf-8")
    assert hc.unmanaged_twins(local, {"coding-python-uv": "Use when configuring uv projects."}) == []


def test_shipped_descriptions_indexes_a_catalogue(tmp_path):
    catalogue = _skills(tmp_path / "mkt", "alpha")
    (catalogue / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Use when alpha things happen.\n---\n", encoding="utf-8")
    assert hc.shipped_descriptions(catalogue) == {"alpha": "Use when alpha things happen."}


# --- front-matter parity --------------------------------------------------------------------

def test_frontmatter_problems_flags_a_name_that_disagrees_with_its_dir(tmp_path):
    skills = _skills(tmp_path / "p")
    (skills / "demo" / "SKILL.md").write_text(
        "---\nname: something-else\ndescription: Use when parsing gitignore filter paths.\n---\n",
        encoding="utf-8")
    assert any("directory" in p for p in hc.frontmatter_problems(skills))


def test_frontmatter_problems_is_quiet_for_a_good_skill(tmp_path):
    skills = _skills(tmp_path / "p")
    (skills / "demo" / "SKILL.md").write_text(
        "---\nname: demo\ndescription: Use when parsing gitignore files and filtering paths.\n---\n",
        encoding="utf-8")
    assert hc.frontmatter_problems(skills) == []


# --- graveyards ---------------------------------------------------------------------------------

def test_graveyard_leaves_a_sanctioned_backup_alone(tmp_path):
    """`.orig-<date>` beside its replacement is how this project retires a file. Not a finding."""
    (tmp_path / "hook.py").write_text("print(1)\n", encoding="utf-8")
    backup = tmp_path / "hook.py.orig-20260801"
    backup.write_text("print(0)\n", encoding="utf-8")
    backup.chmod(0o644)
    assert hc.graveyard_entries(tmp_path) == []


def test_graveyard_flags_an_executable_backup(tmp_path):
    (tmp_path / "hook.py").write_text("print(1)\n", encoding="utf-8")
    backup = tmp_path / "hook.py.orig-20260801"
    backup.write_text("print(0)\n", encoding="utf-8")
    backup.chmod(0o755)
    assert any("executable" in why for _, why in hc.graveyard_entries(tmp_path))


def test_graveyard_flags_a_backup_whose_live_file_is_gone(tmp_path):
    backup = tmp_path / "hook.py.orig-20260801"
    backup.write_text("print(0)\n", encoding="utf-8")
    backup.chmod(0o644)
    assert any("no longer exists" in why for _, why in hc.graveyard_entries(tmp_path))


def test_graveyard_flags_a_parked_skills_dir(tmp_path):
    _skills(tmp_path / "skills.bak", "old-a", "old-b")
    parked = tmp_path / "skills.bak" / "skills"
    parked.rename(tmp_path / "skills.bak.tmp")
    (tmp_path / "skills.bak").rmdir()
    (tmp_path / "skills.bak.tmp").rename(tmp_path / "skills.bak")
    entries = hc.graveyard_entries(tmp_path)
    assert any("parked dir" in why and "2 skill" in why for _, why in entries)


def test_graveyard_flags_bytecode_whose_source_vanished(tmp_path):
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "gone-hook.cpython-314.pyc").write_bytes(b"\x00")
    assert any("no longer exists" in why for _, why in hc.graveyard_entries(tmp_path))


def test_graveyard_ignores_bytecode_whose_source_is_present(tmp_path):
    (tmp_path / "live.py").write_text("x = 1\n", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "live.cpython-314.pyc").write_bytes(b"\x00")
    assert hc.graveyard_entries(tmp_path) == []


def test_shim_problems_flags_a_tombstone_naming_nothing(tmp_path):
    path = tmp_path / "s.py"
    path.write_text('"""RETIRED 2026-08-01. Do not use."""\nraise SystemExit(1)\n', encoding="utf-8")
    path.chmod(0o644)
    assert any("names no replacement" in p for p in hc.shim_problems(path))


@pytest.mark.parametrize("body,name", [
    # "superseded by <other basename>" - the phrasing a first pass wrongly called broken
    ('"""RETIRED - superseded by the plugin\'s block-pgrep-self-match.py."""\nraise SystemExit(1)\n',
     "block_pgrep_self_match.py"),
    # a replacement at a different PATH but the SAME basename
    ('"""RETIRED. The plugin ships plugins/bitranox/hooks/venv-guard.py now."""\nraise SystemExit(2)\n',
     "venv-guard.py"),
    # a .sh retired in favour of a .py of the same stem
    ('# RETIRED. plugins/bitranox/hooks/tell-sweep.py replaces it.\nexit 2\n', "tell-sweep.sh"),
])
def test_a_tombstone_that_points_somewhere_is_accepted(tmp_path, body, name):
    """Each of these is a real shim on this machine; none of them may be reported as broken."""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    path.chmod(0o644)
    assert hc.shim_problems(path) == []


def test_discover_shipped_surfaces_a_tool_repo_skills_dir(tmp_path):
    """Not `.claude/skills`-shaped, so it is never a candidate - it must still be REPORTED."""
    owned = _skills(_manifest(tmp_path / "work" / "widgetlib", "plugin.json"), "coding-widget-uv")
    assert hc.discover_shipped([tmp_path / "work"], home=tmp_path / "home") == [owned]


def test_discover_shipped_ignores_a_local_project_skills_dir(tmp_path):
    _skills(tmp_path / "work" / "orchard" / ".claude", "orchard-build")
    assert hc.discover_shipped([tmp_path / "work"], home=tmp_path / "home") == []


def test_uncollectable_tests_reports_a_path_that_actually_resolves(tmp_path):
    """The reported path must be usable, not pytest's rootdir-relative rendering.

    pytest prints `ERROR <path>` relative to its invocation dir, so a tests dir far from the
    cwd came back as `../../../../../../tmp/.../test_x.py` - a path that only resolves from
    one directory and defeats copy-paste."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_broken.py").write_text("import a_module_that_is_not_installed\n",
                                          encoding="utf-8")
    problems = hc.uncollectable_tests(tests)
    assert problems, "expected a collection failure to report"
    path = problems[0][0]
    assert not path.startswith(".."), path
    assert os.path.isabs(path) and os.path.exists(path), path
