"""abprofile: a TOML profile becomes frozen dataclasses, or a ProfileError naming every problem."""
import abprofile as P
import pytest

GOOD = """
[workpiece]
repo = "{repo}"
base = "{base}"
task_file = "task.md"

[control]
skills_ref = "{ref}"
skill = "demo-skill"

[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["one change"]
markers = []

[floor]
gate = ["./gate.sh"]
cache_paths = ["target"]
timeout_s = 60

[run]
model = "opus"
n = 2
deadline_s = 100
max_tokens = 5000
"""


def _write(tmp_path, scratch_repo, text=GOOD, **over):
    base = (scratch_repo / ".base").read_text(encoding="utf-8")
    body = text.format(repo=scratch_repo, base=over.get("base", base), ref="a" * 40)
    p = tmp_path / "abtest.toml"
    p.write_text(body, encoding="utf-8")
    return p


def test_good_profile_loads(tmp_path, scratch_repo):
    prof = P.load_profile(_write(tmp_path, scratch_repo))
    assert prof.arm_names() == ["C", "V1"]
    assert prof.floor.gate == ("./gate.sh",) and prof.floor.suite is None and prof.suite_argv() is None
    assert prof.run.warmth_tolerance == 0.25 and prof.run.n == 2
    assert prof.run.env_keep == ("PATH", "LANG", "LC_ALL", "TERM", "TZ")
    assert prof.workpiece.repo == scratch_repo.resolve()


def test_suite_argv_substitutes_the_suite(tmp_path, scratch_repo):
    text = GOOD.replace('gate = ["./gate.sh"]', 'gate = ["./gate.sh"]\nsuite = "acceptance/t.py"\nsuite_cmd = ["pytest", "{{suite}}", "-q"]')
    prof = P.load_profile(_write(tmp_path, scratch_repo, text))
    assert prof.suite_argv() == ["pytest", "acceptance/t.py", "-q"]


def test_every_problem_is_listed(tmp_path, scratch_repo):
    text = (GOOD.replace('name = "V1"', 'name = "C"')
                .replace('gate = ["./gate.sh"]', 'gate = "make test"')
                .replace("n = 2", "n = 0"))
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text, base="not-a-sha"))
    msg = str(exc.value)
    for needle in ("workpiece.base", "variant[0].name", "floor.gate", "run.n"):
        assert needle in msg, msg


def test_duplicate_variant_names_and_missing_repo(tmp_path, scratch_repo):
    text = GOOD + '\n[[variant]]\nname = "V1"\ndir = "variants/V1b"\nchanges = ["x"]\nmarkers = []\n'
    text = text.replace('repo = "{repo}"', 'repo = "{repo}/nonexistent"')
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    msg = str(exc.value)
    assert "variant[1].name" in msg and "duplicate" in msg and "workpiece.repo" in msg, msg


def test_skeleton_fails_validation_until_filled(tmp_path):
    p = tmp_path / "abtest.toml"
    p.write_text(P.SKELETON, encoding="utf-8")
    with pytest.raises(P.ProfileError):
        P.load_profile(p)


_VARIANT_BLOCK = '[[variant]]\nname = "V1"\ndir = "variants/V1"\nchanges = ["one change"]\nmarkers = []\n'


def _filled_skeleton(tmp_path, scratch_repo, changes=None):
    """SKELETON with every scalar placeholder filled; `changes` replaces its placeholder list when given."""
    base = (scratch_repo / ".base").read_text(encoding="utf-8")
    text = (P.SKELETON.replace('"<absolute path of the real repository>"', f'"{scratch_repo}"')
            .replace('"<40-char sha every arm starts from>"', f'"{base}"')
            .replace('"<bitranox-skills sha that carries BITRANOX_MEMORY_WRITES>"', f'"{"a" * 40}"')
            .replace('"<skill directory name under plugins/bitranox/skills/>"', '"demo-skill"'))
    # Every placeholder but the changes list is filled, so a refusal can only be about changes.
    assert text.count('"<') == 1 and 'changes = ["<one change per entry>"]' in text, text
    if changes is not None:
        text = text.replace('changes = ["<one change per entry>"]', f"changes = {changes}")
    p = tmp_path / "abtest.toml"
    p.write_text(text, encoding="utf-8")
    return p


def test_filled_skeleton_loads(tmp_path, scratch_repo):
    prof = P.load_profile(_filled_skeleton(tmp_path, scratch_repo, changes='["swap the intro"]'))
    assert prof.variants[0].changes == ("swap the intro",)


@pytest.mark.parametrize("changes", [None, "[]", '["  "]', '[""]', '["ok", "<todo>"]'])
def test_variant_changes_must_be_filled(tmp_path, scratch_repo, changes):
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_filled_skeleton(tmp_path, scratch_repo, changes=changes))
    msg = str(exc.value)
    assert msg.splitlines() and all(line.startswith("variant[0].changes:") for line in msg.splitlines()), msg


@pytest.mark.parametrize(("text", "needle"), [
    (GOOD.replace("[[variant]]", "[variant]"), "variant: must be an array of tables ([[variant]])"),
    ('variant = "V1"\n' + GOOD.replace(_VARIANT_BLOCK, ""), "variant: must be an array of tables ([[variant]])"),
    ('variant = ["V1"]\n' + GOOD.replace(_VARIANT_BLOCK, ""), "variant[0]: must be a table"),
    (GOOD.replace("[workpiece]", "[[workpiece]]"), "workpiece: must be a table"),
    ("run = 3\n" + GOOD.split("[run]")[0], "run: must be a table"),
])
def test_wrong_table_shape_is_a_profile_error(tmp_path, scratch_repo, text, needle):
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    assert needle in str(exc.value).splitlines(), str(exc.value)


def test_workpiece_repo_must_be_absolute(tmp_path, scratch_repo):
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, GOOD.replace('repo = "{repo}"', 'repo = "r"')))
    assert "workpiece.repo: must be an absolute path" in str(exc.value).splitlines(), str(exc.value)


@pytest.mark.parametrize("suite", ["/abs/t.py", "../t.py", "acceptance/../../t.py"])
def test_floor_suite_must_be_relative_and_inside(tmp_path, scratch_repo, suite):
    text = GOOD.replace('gate = ["./gate.sh"]', f'gate = ["./gate.sh"]\nsuite = "{suite}"\nsuite_cmd = ["pytest", "{{{{suite}}}}"]')
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    lines = str(exc.value).splitlines()
    assert len(lines) == 1 and lines[0].startswith("floor.suite: must be a non-empty relative path"), lines


def test_a_missing_sandbox_key_loads_as_none_for_the_dry_run(tmp_path, scratch_repo):
    assert P.load_profile(_write(tmp_path, scratch_repo)).run.sandbox is None


@pytest.mark.parametrize("value", ["bwrap", "bwrap-host-proc", "none"])
def test_every_sandbox_value_loads(tmp_path, scratch_repo, value):
    text = GOOD.replace("max_tokens = 5000", f'max_tokens = 5000\nsandbox = "{value}"')
    assert P.load_profile(_write(tmp_path, scratch_repo, text)).run.sandbox == value


@pytest.mark.parametrize("value", ['"firejail"', '"BWRAP"', '"bwrap-proc"', '""', "true"])
def test_a_bad_sandbox_value_is_a_profile_error(tmp_path, scratch_repo, value):
    text = GOOD.replace("max_tokens = 5000", f"max_tokens = 5000\nsandbox = {value}")
    with pytest.raises(P.ProfileError, match='run.sandbox: must be "bwrap", "bwrap-host-proc" or "none"'):
        P.load_profile(_write(tmp_path, scratch_repo, text))


def test_the_skeleton_names_the_bwrap_sandbox():
    assert P.SKELETON.count('sandbox = "bwrap"\n') == 1 and '"bwrap-host-proc"' in P.SKELETON
    assert 'sandbox = "bwrap"' in P.SANDBOX_MISSING and 'sandbox = "none"' in P.SANDBOX_MISSING


BARE = GOOD.replace('''name = "V1"
dir = "variants/V1"
changes = ["one change"]
markers = []
''', '''name = "V1"
dir = "variants/V1"
changes = ["one change"]
markers = []

[[variant]]
name = "Vbare"
remove_skill = true
task_file = "task-bare.md"
changes = ["the plugin without the skill"]
''')


def test_a_bare_variant_loads_without_dir_and_with_its_own_task_file(tmp_path, scratch_repo):
    prof = P.load_profile(_write(tmp_path, scratch_repo, BARE))
    bare = prof.variant("Vbare")
    assert bare is not None and bare.remove_skill and bare.dir is None and bare.markers == ()
    assert prof.variant("V1").remove_skill is False and prof.variant("V1").task_file is None
    assert prof.task_file_for("Vbare") == "task-bare.md"
    assert prof.task_file_for("C") == prof.task_file_for("V1") == "task.md"
    assert prof.task_files() == ["task.md", "task-bare.md"]


@pytest.mark.parametrize(("value", "problem"), [
    ('"yes"', "variant[1].remove_skill: must be true or false"),
    ("1", "variant[1].remove_skill: must be true or false"),
])
def test_remove_skill_must_be_a_bool(tmp_path, scratch_repo, value, problem):
    text = BARE.replace("remove_skill = true", f"remove_skill = {value}").replace('task_file = "task-bare.md"\n', 'dir = "variants/Vbare"\n')
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    assert problem in str(exc.value).splitlines()


def test_a_bare_variant_refuses_markers_and_a_dir(tmp_path, scratch_repo):
    text = BARE.replace("remove_skill = true", 'remove_skill = true\ndir = "variants/Vbare"\nmarkers = ["[abx] idea=1"]')
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    lines = str(exc.value).splitlines()
    assert "variant[1].dir: must be absent when remove_skill = true (the arm has no skill to overlay)" in lines
    assert "variant[1].markers: must be empty when remove_skill = true (the arm has no skill text)" in lines


def test_remove_skill_false_still_requires_a_dir(tmp_path, scratch_repo):
    text = BARE.replace("remove_skill = true", "remove_skill = false")
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    assert "variant[1].dir: missing or still a <placeholder>" in str(exc.value).splitlines()


@pytest.mark.parametrize("value", ['""', "3", '"/etc/task.md"', '"../task.md"', '"<prompt>"', '"C:/t.md"'])
def test_a_variant_task_file_must_be_a_relative_path_inside_the_run_dir(tmp_path, scratch_repo, value):
    text = BARE.replace('task_file = "task-bare.md"', f"task_file = {value}")
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    assert str(exc.value).startswith("variant[1].task_file: must be a non-empty relative path inside the run dir")


SUITE = GOOD.replace('gate = ["./gate.sh"]', 'gate = ["./gate.sh"]\nsuite = "acceptance/t.sh"\nsuite_cmd = ["sh", "{{suite}}"]')


def test_suite_from_loads_as_an_absolute_path_and_defaults_to_none(tmp_path, scratch_repo):
    assert P.load_profile(_write(tmp_path, scratch_repo, SUITE)).floor.suite_from is None
    src = (tmp_path / "elsewhere" / "t.sh").as_posix()
    prof = P.load_profile(_write(tmp_path, scratch_repo, SUITE.replace("suite_cmd =", f'suite_from = "{src}"\nsuite_cmd =')))
    assert prof.floor.suite_from == src and prof.floor.suite == "acceptance/t.sh"


@pytest.mark.parametrize(("line", "problem"), [
    ('suite_from = "relative/t.sh"', "floor.suite_from: must be an absolute path when set"),
    ("suite_from = 3", "floor.suite_from: must be an absolute path when set"),
    ('suite_from = ""', "floor.suite_from: must be an absolute path when set"),
    ('suite_from = "<path>"', "floor.suite_from: must be an absolute path when set"),
], ids=["relative", "not-a-string", "empty", "placeholder"])
def test_suite_from_must_be_an_absolute_path(tmp_path, scratch_repo, line, problem):
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, SUITE.replace("suite_cmd =", f"{line}\nsuite_cmd =")))
    assert problem in str(exc.value).splitlines()


def test_suite_from_without_a_suite_is_refused(tmp_path, scratch_repo):
    src = (tmp_path / "t.sh").as_posix()
    text = GOOD.replace('gate = ["./gate.sh"]', f'gate = ["./gate.sh"]\nsuite_from = "{src}"')
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, text))
    assert str(exc.value).splitlines() == [
        "floor.suite_from: needs floor.suite, the path the sealed copy takes in each arm's worktree"]


# --- [workpiece] link: gitignored build prerequisites linked into every arm's worktree -----------

def _with_link(value):
    return GOOD.replace('task_file = "task.md"', f"task_file = \"task.md\"\nlink = {value}")


def test_link_loads_as_a_tuple_and_defaults_to_empty(tmp_path, scratch_repo):
    assert P.load_profile(_write(tmp_path, scratch_repo)).workpiece.link == ()
    prof = P.load_profile(_write(tmp_path, scratch_repo, _with_link('[".packages", "third_party/protoc"]')))
    assert prof.workpiece.link == (".packages", "third_party/protoc")


@pytest.mark.parametrize("value", ['["/opt/protoc"]', '["../outside"]', '["a/../../outside"]', '[""]',
                                   '[".git"]', '[".git/hooks"]', '".packages"', "[3]", '[".packages", ".packages"]'],
                         ids=["absolute", "dotdot", "inner-dotdot", "empty", "git-dir", "inside-git-dir",
                              "not-a-list", "not-a-string", "duplicate"])
def test_a_link_entry_must_be_a_relative_path_inside_the_workpiece(tmp_path, scratch_repo, value):
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, _with_link(value)))
    assert any(line.startswith("workpiece.link") for line in str(exc.value).splitlines()), str(exc.value)


def test_a_link_entry_that_resolves_outside_the_workpiece_is_refused(tmp_path, scratch_repo):
    outside = tmp_path / "outside"
    outside.mkdir()
    (scratch_repo / "escape").symlink_to(outside)
    with pytest.raises(P.ProfileError) as exc:
        P.load_profile(_write(tmp_path, scratch_repo, _with_link('["escape/protoc"]')))
    assert "workpiece.link: escape/protoc resolves outside the workpiece" in str(exc.value), str(exc.value)


def test_the_skeleton_names_link_as_a_commented_option():
    assert '# link = [".packages"]' in P.SKELETON


# --- [run] unattended_note: one text appended to every arm's prompt -------------------------------

def _with_note(value):
    return GOOD.replace("max_tokens = 5000", f"max_tokens = 5000\nunattended_note = {value}")


def test_unattended_note_loads_and_defaults_to_none(tmp_path, scratch_repo):
    assert P.load_profile(_write(tmp_path, scratch_repo)).run.unattended_note is None
    prof = P.load_profile(_write(tmp_path, scratch_repo, _with_note('"No human reads this; never ask, decide."')))
    assert prof.run.unattended_note == "No human reads this; never ask, decide."


@pytest.mark.parametrize("value", ['""', '"   "', "3", '["a"]', '"<what every arm is told>"'],
                         ids=["empty", "blank", "not-a-string", "a-list", "placeholder"])
def test_a_bad_unattended_note_is_a_profile_error(tmp_path, scratch_repo, value):
    with pytest.raises(P.ProfileError, match=r"run\.unattended_note: "):
        P.load_profile(_write(tmp_path, scratch_repo, _with_note(value)))


def test_the_skeleton_names_unattended_note_as_a_commented_option():
    assert "# unattended_note = " in P.SKELETON
