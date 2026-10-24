# skill-writer checklist - coding-python-uv (memory rules folded in)

- [x] Change: ## Dependency Cooldowns, right after the first `[tool.uv] exclude-newer = "1 week"`
      snippet - coding-python-uv/05-resolution.md (+ routing row in SKILL.md 'Cross-Reference by
      Scenario'). RED on the pre-edit snapshot: partial. Verified: uv 0.13.0, scratch project: `uv
      init --lib` then `uv add --exclude-newer "7 days" six` -> rc 0, `grep exclude pyproject.toml`
      empty, uv.lock `[options]` held `exclude-newer = "0001-01-01T00:00:00Z"` (no-effect
      placeholder) + `exclude-newer-span = "P7D"`; then plain `uv add idna` rc 0 and uv.lock had no
      exclude-newer line at all. `uv tool install --exclude-newer "7 days" cowsay` into a scratch
      UV_TOOL_DIR wrote `[tool.options] exclude-newer-span = "P7D"` to uv-receipt.toml. `uv tool
      install --exclude-newer "7 days" ruff` -> 0.17.1, `uv tool upgrade ruff` -> 'Nothing to
      upgrade' although 0.17.2 (uploaded 2026-10-22, inside 7 days) exists, so upgrade honours it.
- [x] Dropped as stale or unverified: Nothing stale. Dropped the measurement date and the cross-fact
      pointer ('see the uvx/tool cooldown fact'); version label uv 0.13.0 kept.
- [x] Change: ### Installing Tools, after the package-source examples (git / Git LFS), before ###
      Installing Executables from Additional Packages - coding-python-uv/07-tools-and-scripts.md (+
      routing row in SKILL.md). RED on the pre-edit snapshot: partial. Verified: uv 0.13.0:
      scaffolded package `my-tool-lib` with `[project.scripts] mytool = ...`; `uv tool install
      --from "$PWD" mytool` -> rc 2, `error: Package name (`my-tool-lib`) provided with `--from`
      does not match install request (`mytool`)` (verbatim). `uv tool install --from "$PWD"
      my_tool_lib` (underscored) -> rc 0, `Installed 1 executable: mytool` (normalisation
      confirmed). Scratch UV_TOOL_DIR/UV_TOOL_BIN_DIR recipe is exactly what ran. uvx `--from <pkg>
      <command>` contrast: 07-tools-and-scripts.md 'Commands with Different Package Names' (`uvx
      --from httpie http`).
- [x] Dropped as stale or unverified: Dropped the private template repo names and the org-derived
      package name; body's 'Installed N executables' replaced by the real output form 'Installed 1
      executable: mytool'. The git-source sentence is an application of the same name check (package
      name rule verified on a path source, not separately on git+).
- [x] Change: ## Dependency Cooldowns, after the per-package `exclude-newer-package` snippet (end of
      section); plus a reconciling note under ## Reproducible Resolutions after the vendored
      'messages ... will not mention' paragraph - coding-python-uv/05-resolution.md (two places) +
      routing row in SKILL.md. RED on the pre-edit snapshot: partial. Verified: uv 0.13.0 with ruff
      (0.17.1 uploaded 2026-10-15, 0.17.2 uploaded 2026-10-22) under `exclude-newer = "7 days"`: (a)
      global cooldown, floor ruff>=0.17.2 -> rc 1, `cause: Because only ruff<=0.17.1 is available
      and your project depends on ruff>=0.17.2, ...` plus `hint: `ruff` was filtered by
      `exclude-newer` to only include packages uploaded before <ts>. The latest version satisfying
      the requirement is v0.17.2, published at ...`; (b) exemption timestamp earlier than the
      release -> same cause, hint names `exclude-newer-package`; `uv lock --upgrade-package ruff`
      does NOT fix that case (rc 1). (c) Tried to reproduce the body's lock-state case four ways
      (exemption `false` and exemption timestamp, each added with the floor raise or present from
      the first lock, lock holding 0.17.1, absolute-date variant with six too): every time plain `uv
      lock` re-resolved (`Updated ruff v0.17.1 -> v0.17.2`, once logging 'Resolving despite existing
      lockfile due to addition of exclude newer ... for package `ruff`'). So the lock-state case is
      kept only as an observed case behind the scratch-dir control, and `--upgrade-package`
      semantics come from 02-projects.md 'Upgrading Locked Package Versions'.
- [x] Dropped as stale or unverified: Dropped the body's stated mechanism 'uv prefers the locked
      version even for an exempted package' (CONTRADICTED by 02-projects.md:614 'Package versions
      will only change if the project's dependency constraints exclude the previous, locked version'
      and not reproduced on uv 0.13.0). Dropped the claim that --upgrade-package is the first fix:
      it does not help when the cooldown/exemption is the cause, so the text now splits the two
      causes. Dropped the lsdsk/1.11.0 release history and date.
- [x] Change: ### Minor version directories, after the 'If this link is resolved by another tool
      ...' paragraph - coding-python-uv/06-python-versions.md (+ routing row in SKILL.md). RED on
      the pre-edit snapshot: NONE. Verified: Junction mechanism: 06-python-versions.md 'Minor
      version directories' ('a symbolic link (on Unix) or junction (on Windows) pointing to a
      specific patch version'). On this Linux host `uv python list --only-installed` lists both the
      minor-dir path (cpython-3.14-linux-...) and patch dirs (cpython-3.14.5-linux-...), so the
      'pick the full-patch entry' step is realistic. Error 448 itself: UNVERIFIABLE here (no Windows
      host, by design); kept as observed behaviour with no version, since the body gives none. The
      message text is the Windows ERROR_UNTRUSTED_MOUNT_POINT string in Rust's '(os error N)' form;
      the exact console formatting is not re-checked.
- [x] Dropped as stale or unverified: Dropped the private host name. Did NOT carry the scenario's
      'local disk, no drive mapped' as a claim (body does not establish it). Note to coordinator:
      one inserted line ('point is uv's own minor-version junction. Bypass it by calling the
      interpreter in the PATCH-version directory directly: find that directory with') is longer than
      100 columns after my last edit and should be re-wrapped; content is final.
- [x] Change: New ### Gotcha: a recreate deletes the interpreter you named by path (between the
      'install does not upgrade' gotcha and the 'uv python find' gotcha) -
      coding-python-uv/06-python-versions.md (+ routing row in SKILL.md). RED on the pre-edit
      snapshot: NONE. Verified: All re-run on uv 0.13.0 in a scratch project: `sys._base_executable`
      in a 3.10.22 venv = the venv's own bin/python, in a 3.11.17 venv = the uv store binary. 3.10
      venv with pyvenv.cfg version_info set to an older patch + cold UV_CACHE_DIR, `uv sync --locked
      --python $PWD/.venv/bin/python` -> rc 2 with exactly the four quoted lines, `.venv` left empty
      (ls -A printed nothing); same with 3.11 -> rc 0, recreated. `--python 3.10` on the stale 3.10
      venv -> rc 0. Stale PyPy 3.11 venv + `--python 3.11` -> 'Using CPython 3.11.17', rebuilt as
      cpython, rc 0; `--python pypy@3.11` kept pypy. Stale free-threaded 3.14 venv + `--python 3.14`
      -> Py_GIL_DISABLED 0 (GIL build); `--python 3.14t` -> Py_GIL_DISABLED 1. Consistent with
      06-python-versions.md gotcha 2 (request the MINOR) and the vendored free-threaded section
      ('The GIL-enabled build of Python will still be preferred').
- [x] Dropped as stale or unverified: Dropped 'a warm uv interpreter cache rescues the recreate, so
      it looks intermittent': NOT reproduced on uv 0.13.0 (2 consecutive runs on one cache, and a
      stale run after a successful warm-up sync on the same cache, all rc 2). Dropped OPEN-WORK
      number, bmk versions, commit shas, test file paths, the uvx uv@0.11.15 repro recipe and the
      pyvenv.cfg forensic tell (bmk-development detail, stays with the pointer).
- [x] Change: New ## Gotcha: a green uv install is no evidence a pip user can install it (end of
      SKILL.md, after the missing-extra gotcha) - coding-python-uv/SKILL.md. RED on the pre-edit
      snapshot: partial. Verified: Re-run on uv 0.13.0: built local wheels capdemo 1.0 (>=3.8) and
      2.0 (METADATA 'Requires-Python: >=3.8, <3.13'); consumer requires-python >=3.10, dep
      capdemo>=2.0: `uv lock` rc 0, `uv sync --locked --python 3.14` rc 0, installed capdemo 2.0 on
      3.14.8; `pip install --no-index --find-links ... 'capdemo>=2.0'` on python3.14 -> rc 1 `ERROR:
      Package 'capdemo' requires a different Python: 3.14.8 not in '<3.13,>=3.8'`. Mechanism:
      05-resolution.md Universal Resolution ('uv only considers lower bounds and ignores upper
      bounds entirely'). --no-install-project: with explicit `--no-index --find-links` and a cold
      cache, plain sync rc 1 'hatchling was not found in the provided package locations'; with
      `--no-install-project` rc 0. With a warm cache the plain sync succeeded, hence 'in neither the
      find-links dir nor the cache'. PyPI JSON: /pypi/ruff/0.17.2/json has urls[].requires_python.
- [x] Dropped as stale or unverified: Placement fixed (SKILL.md had no 05-resolution note to sit
      beside; added as its own gotcha with a pointer to 05). Dropped bmk floor policy, OPEN-WORK
      number, commit sha, bmk version and the capdemo fixture names. Softened 'or the sync fails' to
      'when its build backend is in neither the find-links dir nor the cache' because a warm cache
      made it pass.
- [x] Review A fixed: the refused-floor section is a two-cause diagnosis keyed on the hint: line,
      and the closing advice applies only when no hint names a filter; prefer an exemption timestamp
      just after the upload; <N> is not the locked version; the os error 448 bypass builds the patch
      path from uv python dir, since `uv python list` shows the newest patch through the minor
      junction (measured on uv 0.13.0); a fresh uv 0.13.0 venv writes version_info as the minor
      (measured), so it does not reproduce the recreate failure.
- [x] Declined: the warm-cache rescue from the source note (did not reproduce on uv 0.13.0); the
      description's "measured on 0.11.x" clause stays untouched in a fold and is filed as its own
      backlog item.
- [x] Receipt held (the coordinator ran skill_receipt.py start meta-skill-writer); every editing
      agent loaded the skill through the Skill tool before its first edit.
- [x] RED as a text check: an opus quote-back against a pre-edit snapshot of the skill. Only a
      verbatim quote from the snapshot counts, so context inherited from this machine cannot
      satisfy it; redcheck --corpus-cascade was not run.
- [x] GREEN quote-back on haiku and opus against the edited files: every scenario after the edit,
      every scenario again after the first review's fixes, then the scenarios each later fix
      touched. Every answer was a quote from the new text on both tiers in every round; no NONE.
      Quotes were checked against the files (6-word windows; misses traced to line wraps,
      markup and line-number prefixes).
- [x] GREEN diffed against RED both ways: every partial RED quote is still in the edited text.
- [x] Tiers haiku and opus, one cell per scenario per tier per round.
- [x] Independent review of the full diff, then a review of each fix delta alone; every finding
      fixed or declined above. Each GREEN reply's Skill gaps list was read; gaps not listed
      here asked for detail the rule does not need (out of scope) or were answered elsewhere in
      the skill.
- [x] Description measured: unchanged (frontmatter not edited).
- [x] ASCII only, present tense (history finder clean on the added lines), tables canonical
      (reformat_tables.py --check --strict), every fence closes, added prose wrapped at 100
      columns except where the file keeps one line per paragraph or list item.
- [x] Security scan: prose only; no secrets, hostnames, private paths or PII; values added are
      option names, commands, source file paths or reserved examples.
