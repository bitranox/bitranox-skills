# skill-writer checklist - coding-python-uv (cooldown on installs and locks, which interpreter)

- [x] Changes: 07-tools-and-scripts.md cooldown section gains three bullets (the installed
      package's own `[tool.uv]` cutoff is ignored; the install cutoff governs
      `build-system.requires`; prove an install line with a scratch `--no-cache` install);
      05-resolution.md gains "An exemption only ADMITS a release; it does not move the lock";
      06-python-versions.md gains "Gotcha: `uv run --python X.Y` in a project replaces the
      project's `.venv`" and rewrites the `uv python find` gotcha to `--system`; SKILL.md routing
      table gains four rows.
- [x] RED (text check): no file said the package's own cutoff is ignored, that build requirements
      fall under the install cutoff, that a plain `uv lock` keeps the locked version after an
      exemption, or that `uv run --python` replaces `.venv`; 06 recommended parsing
      `uv python list` to learn what uv would use.
- [x] Every claim run on uv 0.13.0:
      - `uv tool install --from git+file://<repo>@v0.1.0` of a package declaring
        `exclude-newer = "2020-01-01T00:00:00Z"` installed six 1.17.0 and wrote no cutoff to the
        receipt; `--from <local path>` the same.
      - `--exclude-newer 2024-01-01 --no-cache` with `hatchling>=1.25` in build-system.requires:
        exit 1, "No solution found when resolving: `hatchling>=1.25`" plus the
        exclude-newer-package hint; without `--no-cache` the same line exited 0 (cached build);
        `--exclude-newer 2024-12-31` exited 0.
      - Locked six 1.13.0 under a 2020 cutoff; after adding a six exemption a plain `uv lock`
        printed "Resolving despite existing lockfile due to addition of exclude newer" and kept
        1.13.0; `uv lock --upgrade-package six` printed "Updated six v1.13.0 -> v1.17.0".
      - `uv run --python 3.12` in a project on 3.15 printed "Removed virtual environment at:
        .venv" and left `.venv` on 3.12; a plain `uv sync` kept 3.12; no `.python-version`
        written; `uv run --isolated --python 3.11 --with-editable . --with pytest` and
        `UV_PROJECT_ENVIRONMENT=.venv-311 uv run --python 3.11` both ran on 3.11 and left `.venv`
        alone; deleting `.venv` and `uv sync` rebuilt it on the default.
      - `uv python find --system --no-python-downloads --show-version 3.14` equalled the
        interpreter `uv venv --python 3.14` built on in 6/6 cells (preference unset, managed,
        system; VIRTUAL_ENV set and unset): 3.14.8, 3.14.8, 3.14.4 under system; without
        `--system` and a cwd `.venv` on 3.14.4 find answered 3.14.4 while `uv venv` built 3.14.8;
        the listing's newest 3.14 was 3.14.8.
- [x] GREEN quote-back: 07 "ignores the `exclude-newer` the package's `pyproject.toml` declares
      under `[tool.uv]`"; 05 "a plain `uv lock` after adding the exemption ... KEEPS the locked
      version"; 06 "it removes the project's `.venv` and recreates it on 3.12" and "Ask with
      `--system`, which skips both venvs".
- [x] Description: unchanged.
- [x] Receipt: the editing agent loaded bitranox:meta-skill-writer through the Skill tool before its
      first edit; the SKILL.md edits were accepted.
- [x] ASCII only, present tense, no history lines (finder pattern over the added lines: no hit
      except an example comment), tables canonical (reformat_tables.py run after each table edit).
- [x] Security scan: prose and examples only; no secrets, hostnames, private paths or PII; example
      paths are generic.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
