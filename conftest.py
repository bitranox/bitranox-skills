"""Session-wide test setup for the whole repository.

Strips the variables that tell git which repository to use before any test runs. git reads them
before it looks at its working directory, so a suite launched with one set - a push from a linked
worktree hands the pre-push hook GIT_DIR, and any git-spawned runner can - sends every fixture's
`git init` / `git config` / `git commit` into the launcher's repository instead of the fixture.
That is how this repo's own `.git/config` came to carry a test's `user.name t`, which then
authored every commit made here until someone noticed. Every one of those git calls exited 0.

The pre-push hook unsets the same list for its own run; doing it here covers every launcher, and
`tests/test_hermetic_git_env.py` under `plugins/bitranox/hooks/` proves it end to end.

It also gives the session a temp directory of its own and removes it at the end. Hooks keep
per-project state in the temp directory keyed by a hash of the project path, and each test passes
its own `tmp_path` as the project, so every run left a few hundred files that nothing removed -
enough to exhaust the inodes of a shared tmpfs /tmp. `tests/test_hermetic_tempdir.py` under
`plugins/bitranox/hooks/` proves that end to end.
"""

from __future__ import annotations

import os
import shutil
import tempfile

GIT_REPOSITORY_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
    "GIT_QUARANTINE_PATH",
)


# Every name a temp API consults: TMPDIR on POSIX, TEMP and TMP on Windows. A subprocess reads
# the environment, this process reads tempfile.tempdir, so all four move together.
TEMP_DIRECTORY_VARIABLES = ("TMPDIR", "TEMP", "TMP")

_session_temp_dir = None


def pytest_configure(config):  # noqa: ARG001 - pytest hook signature
    global _session_temp_dir
    for name in GIT_REPOSITORY_VARIABLES:
        os.environ.pop(name, None)
    _session_temp_dir = tempfile.mkdtemp(prefix="bitranox-tests-")
    for name in TEMP_DIRECTORY_VARIABLES:
        os.environ[name] = _session_temp_dir
    tempfile.tempdir = _session_temp_dir


def pytest_unconfigure(config):  # noqa: ARG001 - pytest hook signature
    if _session_temp_dir:
        shutil.rmtree(_session_temp_dir, ignore_errors=True)
