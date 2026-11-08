#!/usr/bin/env python3
"""The table of skills that ship from both this marketplace and their own tool repo.

Two hooks read it: `repo-gate.py` compares each pair, and `skill-edit-guard.py` maps a twin a
session is about to edit back to the marketplace skill whose decision ledger governs it. One
table in one module, because a second copy would drift and the half that drifted would be the
one nobody runs.

Pure standard library, so a hook can import it on a bare interpreter.
"""
import os
import subprocess
from pathlib import Path

__all__ = ["MIRRORED_SKILLS", "marketplace_name"]

#: Skills that ship from BOTH this marketplace and their own tool repo, mapped to the
#: twin's path under the shared `public/` tree. The two copies must stay identical apart
#: from the divergences `repo-gate.normalise_mirror` erases, and both directions drift: a
#: marketplace edit that is never mirrored back leaves the tool repo's own installers a release
#: behind, and a repo edit that is never mirrored forward leaves this marketplace describing
#: behaviour the tool dropped. Measured 2026-07-30: the coding-python-network-probe mirror still
#: told an agent that a default sweep refuses to run, two ipscout releases after it stopped
#: doing that.
MIRRORED_SKILLS = {
    "ai-llm-jev-judge": "KI/btx-skill-jev-judge/skills/jev-judge",
    "coding-python-gitignore": "libs/igittigitt/skills/python-gitignore",
    "coding-python-layered-config": "libs/lib_layered_config/skills/python-layered-config",
    "coding-python-logging": "libs/lib_log_rich/skills/python-logging",
    "coding-python-network-probe": "libs/ipscout/skills/python-network-probe",
    "coding-python-new-public-library": "libs/bitranox_template_py_lib/skills/new-public-python-library",
    "coding-python-pwshpy": "apps/utils/pwshpy/skills/using-pwsh",
    "coding-python-send-mail": "libs/btx_lib_mail/skills/python-send-mail",
    # The REPO dir is underscored (vnc_remote_control) while the SKILL dir inside it is
    # hyphenated. Spelling both with hyphens pointed this entry at nothing, so the mirror
    # check skipped compuse-vnc silently - the exact "degrades to skipped forever" failure
    # the twin-exists test guards against.
    "compuse-vnc": "apps/utils/vnc_remote_control/skills/vnc-remote-control",
    "devops-bmk": "apps/utils/bmk/skills/devops-bmk",
    "infra-proxmox-bindsnap": "apps/pve-bindsnap/skills/proxmox-bindsnap",
    "infra-storage-check-zpools": "apps/utils/check_zpools/skills/check-zpools",
}


def _key(path):
    """``path`` as a comparable string: forward slashes, case folded where the OS folds it."""
    return os.path.normcase(str(path)).replace("\\", "/").rstrip("/")


def _owner_by_suffix(skill_dir, table):
    """The marketplace name whose twin path ``skill_dir`` ends with, or None."""
    here = _key(skill_dir)
    for name, rel in table.items():
        if here.endswith("/" + _key(Path(rel))):
            return name
    return None


def _main_checkout_path(skill_dir):
    """``skill_dir`` re-rooted at the main checkout of the repository it sits in, or None.

    A twin edited in a linked worktree (`git worktree add`) sits at another path than the one the
    table names; its main checkout is the parent of the common git dir. None outside git, for a
    bare repository or a separate git dir, and when git cannot run.
    """
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel", "--git-common-dir"],
                             cwd=str(skill_dir), capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = out.stdout.splitlines()
    if out.returncode or len(lines) != 2:
        return None
    top, common = Path(lines[0]).resolve(), Path(lines[1])
    if not common.is_absolute():
        common = Path(skill_dir) / common     # git prints a relative common dir against the cwd
    common = common.resolve()
    here = Path(skill_dir).resolve()
    if common.name != ".git" or not here.is_relative_to(top):
        return None
    return common.parent / here.relative_to(top)


def marketplace_name(skill_dir, table=None):
    """The marketplace skill a tool-repo twin at ``skill_dir`` mirrors, or None when it is none.

    Matched by the twin's path ending, so the `public/` tree need not be known; a twin in a
    linked worktree is matched at its main checkout's path. Git runs only for a dir whose own
    name is a twin's, so an ordinary skill costs no subprocess. ``table`` defaults to
    `MIRRORED_SKILLS`.
    """
    table = MIRRORED_SKILLS if table is None else table
    skill_dir = Path(skill_dir)
    if _key(skill_dir.name) not in {_key(Path(rel).name) for rel in table.values()}:
        return None
    found = _owner_by_suffix(skill_dir, table)
    if found is not None or not skill_dir.is_dir():
        return found
    main = _main_checkout_path(skill_dir)
    return None if main is None else _owner_by_suffix(main, table)
