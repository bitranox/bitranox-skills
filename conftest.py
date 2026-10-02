"""Session-wide test setup for the whole repository.

Strips the variables that tell git which repository to use before any test runs. git reads them
before it looks at its working directory, so a suite launched with one set - a push from a linked
worktree hands the pre-push hook GIT_DIR, and any git-spawned runner can - sends every fixture's
`git init` / `git config` / `git commit` into the launcher's repository instead of the fixture.
That is how this repo's own `.git/config` came to carry a test's `user.name t`, which then
authored every commit made here until someone noticed. Every one of those git calls exited 0.

The pre-push hook unsets the same list for its own run; doing it here covers every launcher, and
`tests/test_hermetic_git_env.py` under `plugins/bitranox/hooks/` proves it end to end.
"""

from __future__ import annotations

import os

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


def pytest_configure(config):  # noqa: ARG001 - pytest hook signature
    for name in GIT_REPOSITORY_VARIABLES:
        os.environ.pop(name, None)
