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
    assert "variant[1].name" in str(exc.value) and "workpiece.repo" in str(exc.value)


def test_skeleton_fails_validation_until_filled(tmp_path):
    p = tmp_path / "abtest.toml"
    p.write_text(P.SKELETON, encoding="utf-8")
    with pytest.raises(P.ProfileError):
        P.load_profile(p)
