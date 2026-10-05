"""The fixtures' child environment must reach the same packages as the interpreter running pytest.

Several fixtures give the child a private HOME so git cannot read the developer's own config. On
POSIX the user site-packages directory is derived from HOME, so a child spawned with that
environment lost every package installed with ``pip install --user`` - pytest included - and the
fixture suite died with "No module named pytest" whenever the outer run used such an interpreter
(a system python3 with user-site packages), while a uv-provisioned run passed.
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


def test_a_private_home_keeps_the_user_site_of_the_running_interpreter(tmp_path, clean_env):
    home = tmp_path / "home"
    home.mkdir()
    assert _child_user_base(clean_env(HOME=str(home))) == site.getuserbase()


def test_the_default_environment_keeps_it_too(clean_env):
    """The control: with HOME untouched the child resolves the same user base."""
    assert _child_user_base(clean_env()) == site.getuserbase()
