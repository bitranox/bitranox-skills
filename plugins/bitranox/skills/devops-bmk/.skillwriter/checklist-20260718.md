# skill-writer checklist - devops-bmk (2026-07-18, Windows make install + make-release gh gap)

Change (two edits): (1) FIX the wrong Windows `make` install guidance in section 2 and the
Troubleshooting table - on a non-admin box use `winget install --id ezwinports.make -e --scope
user` (run make from Git Bash so SHELL := /bin/bash resolves); `choco install make` needs an
elevated shell. (2) ADD a Troubleshooting row - `make release` on Windows silently skips creating
the GitHub Release when `gh` is not on the invoking process PATH (tag + PyPI still succeed).

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: the skill actively told a non-admin Windows user `choco install make`, which fails without
      an elevated shell - the skill's guidance was WRONG, not merely missing (fact
      reference-install-make-on-the-windows-dev-box-via-winget-ezwinports-not-choco). And `make
      release` silently shipping no GitHub Release was undocumented (fact
      reference-bmk-make-release-silently-skips-the-github-release-...).
- [x] GREEN: both spots now give the working non-admin winget command + the Git-Bash SHELL note; the
      new row names the shutil.which detection, the silent-skip, and both fixes.
- [x] MIRROR: devops-bmk is a mirrored skill - the twin in the bmk source repo
      (projects/public/apps/utils/bmk) must get the SAME two edits + a plugin.json bump (per
      reference-the-four-mirrored-skills-and-their-source-repos). Tracked as a follow-up in this session.
- [x] Scope: bmk tool usage; correct home.
- [x] Security scan: prose only, no secrets/hosts/paths.
- [x] CSO description: unchanged (body edit; "running bmk", "make release" cover retrieval).
- [x] Token budget: two table rows + one prose fix.
