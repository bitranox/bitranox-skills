# Review checklist - release races, unreleased versions, skill-only pushes, pip-audit ignores (2026-10-29)

Change: seven queued contribution entries folded into section 1 (venv) and section 3 (everyday
commands) of SKILL.md, plus two Troubleshooting rows; one adjacent false claim corrected. Mirrored
skill: the bmk tool repo's `skills/devops-bmk/SKILL.md` carries the same bytes.

Paragraphs added or rewritten:

1. "Before a bump, check whether the current version was ever released" (replaces the
   `git tag --list` bullet): remote tag plus PyPI check, release directly or bump past it, and a
   hand-written note under the never-released heading.
2. "When that branch push is rejected, nothing was tagged": the two remedies (hand-tag the
   CI-verified commit the way `release` does, or fast-forward and wait for CI on the new tip).
3. "When your push is rejected because someone else pushed bmk's churn first": restore the churn
   files to the merge base, rebase, regate, amend.
4. Appended to "Tests that break right after a floor was raised": the last published version is
   broken for fresh installs; check it with `uvx --isolated --refresh <pkg>@latest`, release the
   fix as its own patch.
5. "Every push that changes `skills/` needs a `plugin.json` version the remote does not have yet".
6. "Before keeping a `[tool.pip-audit] ignore-vulns` entry, check that it still fires".
7. Corrected: "`bump`, `push` and `release` raise `plugin.json`" became "`bump` and `push` (and
   `commit`) raise ...; `release` writes nothing and only checks".

## RED (text checks of the pre-edit file, `git show HEAD:.../SKILL.md`)

- [x] `grep -n -i 'never tagged\|ls-remote\|non-fast-forward\|fast-forward\|rebase\|ignore-vulns\|verify-tag\|already-published'`
      over the pre-edit text: no hit for any of the seven rules (the only `ls-remote` hits are the
      tool-lock skip and the topic-branch cleanup; `fast-forward` only "Fast-forwarding the default
      branch first does not prevent it").
- [x] The pre-edit untagged-version bullet said only "release it directly", checked with the LOCAL
      `git tag --list`, and said nothing about a higher bump being needed or the old heading.
- [x] The pre-edit floor bullet ended at "walk `__cause__` where the original error matters":
      nothing about the published release.
- [x] The pre-edit skill-shipping list covered only releases and the `release` refusal; no rule for
      a push between releases.
- [x] The pre-edit text claimed `release` raises `plugin.json`; `rel` is the single `release`
      stage (`src/bmk/adapters/stagerunner/registry.py:227`) and `_release.py` never calls the sync.
- [x] Behavioural RED/GREEN subagent arms: not run. The brief for this batch forbids dispatching
      subagents, so evidence is a text check of the file plus the source and throwaway runs below.

## Every bmk behaviour checked against source or a throwaway run (bmk 3.33.0, tool worktree source)

- [x] Release ordering: `_release.py:239-255` (version shape, skill-version refusal, clean tree)
      run before `git_push(remote, branch)` at `:269`; the tag is created at `:276`, after it.
      `run(..., check=True)` (`:62-64`, `:91`) raises CalledProcessError.
- [x] Throwaway run (bare origin, a second clone pushed on top, `bmk release` in the behind clone):
      unfetched printed `! [rejected] master -> master (fetch first)`, fetched printed
      `(non-fast-forward)`; both ended in a `CalledProcessError` traceback with RC=1, and both
      `git tag --list` and `git ls-remote --tags origin` were empty afterwards.
- [x] Hand-tag form matches `release`: annotated tag message `Release v<version>` (`:276`),
      `gh release create <tag> -t <tag> -n "Release <tag>"` (`:105-107`, `:286`).
- [x] The release workflow starts on the tag push: `.github/workflows/default_release_public.yml`
      `on: push: tags: - 'v*'`.
- [x] `bump` checks no tag and only renames `[Unreleased]`: `_bump_version.py:133-173`
      (`update_changelog`); no tag lookup anywhere in that helper.
- [x] Plugin sync: `_sync_initconf.py:226-240` (`_may_raise_manifest`: raise only when the package
      version is greater), run by the bump pipeline (`registry.py:176-180`) and the commit pipeline
      that `push` runs (`registry.py:183-186`, `:207`); `release` passes when the plugin version at
      the last tag differs from the one on disk (`_release.py:213`).
- [x] pip-audit: `tools.py:103-112` passes `--ignore-vuln=<id>` from `[tool.pip-audit].ignore-vulns`
      (`project.py:231-233`); the stage audits the project venv through `PIPAPI_PYTHON_LOCATION`
      (`actions.py:148-185`), synced with `uv sync --locked` (`venv.py:1129`). pip-audit 2.10.1
      matches an ignore against id OR aliases (`_service/interface.py:147-151`, used at
      `_cli.py:566-567`). The documented command ran against bmk's own interpreter: RC=0, a JSON
      report with `dependencies[].vulns[]`.
- [x] Churn route: throwaway repos where both sides rewrote Makefile, pyproject.toml and uv.lock:
      a plain rebase conflicted in exactly those three files; `git checkout <merge-base> -- ...`,
      amend, rebase completed clean and kept the code change. The regeneration itself is bmk's
      `update_deps` stage at order 10 (`registry.py:152`, `:203`).
- [x] `uvx --isolated --refresh <pkg>@latest <cmd>` ran (uv 0.13.0), resolving a fresh env.
- [x] Not run, by design: `make` reporting 2 is GNU make's status for a failed recipe, not bmk behaviour; not
      run here, since a `make` would upgrade the shared bmk tool env.

## GREEN (quote-back from the edited file)

- [x] "If it does (a feature on top of a version that was a patch step), bump past it anyway."
- [x] "The tag is created only after that push, so no tag exists locally or on the remote. Do not
      pull and re-run straight away: that tags the new tip, a commit CI never verified."
- [x] "Put those three files (and `.bmk-cooldown.mk`, when your commit changed it) back to the
      state your commit started from"
- [x] "After adapting, run the published version as a new user gets it,
      `uvx --isolated --refresh <pkg>@latest <a command that reaches the changed code>`"
- [x] "Raise `plugin.json` in that same commit, a patch step above the version on the remote."
- [x] "Keep an entry only if it equals the `id` or one of the `aliases` of some
      `dependencies[].vulns[]` item in that report; delete the rest."

## Quality

- [x] ASCII only: `grep -cP '[^\x00-\x7F]'` on SKILL.md prints 0.
- [x] Latest-release finder over the added lines: no hit.
- [x] Tables canonical: `reformat_tables.py` on a copy leaves it byte-identical; the two rows were
      fitted to the existing widths (85, 260).
- [x] Description unchanged, so no derived artifact moves.
- [x] No private host, repo or customer name added; example paths are generic.
- [x] Twin: `diff -r -x .skillwriter` of this skill dir against the tool repo's `skills/devops-bmk`
      prints nothing; both committed bases were byte-identical before the edit.
