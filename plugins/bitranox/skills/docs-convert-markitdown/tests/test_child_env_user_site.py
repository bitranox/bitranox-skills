"""The script subprocess must reach the same packages as the interpreter running pytest.

``run_script`` gives the child a throwaway HOME so nothing can write to the real home directory.
On POSIX the user site-packages directory is derived from HOME, so a child spawned with that
environment lost every package installed with ``pip install --user`` - markitdown included - and
the tests that need the REAL markitdown failed on "No module named markitdown" (or skipped in the
wrong place) whenever the outer run used such an interpreter, while a uv-provisioned run passed.
"""
import site
import subprocess
import sys

PROBE = "import site; print(site.getuserbase())"


def _child_user_base(env):
    result = subprocess.run([sys.executable, "-c", PROBE], env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_a_private_home_keeps_the_user_site_of_the_running_interpreter(tmp_path, child_env):
    home = tmp_path / "home"
    home.mkdir()
    assert _child_user_base(child_env(home)) == site.getuserbase()


def test_an_explicit_user_base_from_the_caller_is_kept(tmp_path, child_env):
    """The pin is a default, never an override of a caller who chose one."""
    chosen = str(tmp_path / "chosen-base")
    assert _child_user_base(child_env(tmp_path, extra={"PYTHONUSERBASE": chosen})) == chosen
