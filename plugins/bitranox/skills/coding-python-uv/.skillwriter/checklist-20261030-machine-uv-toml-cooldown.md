# skill-writer checklist - coding-python-uv (machine-wide uv.toml cooldown and the lock)

Entries covered: how a discovered user/system `uv.toml` `exclude-newer` ranks against a
project's own value and how `UV_CONFIG_FILE` differs; a discovered `exclude-newer-package`
table merged into every lock, breaking `--locked` in CI, and how to test for it.

- [x] Change: new subsection "A machine-wide `uv.toml` cooldown and the project's lock" in
      `10-configuration.md`, and a routing row in SKILL.md pointing at it.
- [x] Measured on uv 0.13.0 with `uv lock` in scratch projects (user file via `XDG_CONFIG_HOME`,
      system file via `XDG_CONFIG_DIRS`): user `"7 days"` + project unset -> `P7D`; + project
      `"1 day"` -> `P1D`; `UV_CONFIG_FILE` with `"7 days"` + project `"1 day"` -> `P7D`; the user
      file's `exclude-newer-package` landed in `[options.exclude-newer-package]`; with it hidden,
      `uv lock --check` rc 1 and `uv export --locked` rc 1, beside it rc 0; a clean lock gave
      plain `--check` rc 0 and `--check --no-config` rc 1; a system-file lock passed `--check`
      beside the file and returned rc 1 with an empty `uv/uv.toml` first in `XDG_CONFIG_DIRS`.
- [x] Scope narrowed to what was measured: the `exclude-newer` ranking is stated for the user
      file, with the system file ranked below it per the documented precedence.
- [x] RED: the opus no-text arm knew the merge from inherited context (contaminated); text check
      `MERGED into every lock` HEAD 0 now 1.
- [x] GREEN (opus and haiku): P1D for the project, exemption moved into `[tool.uv]`, plain
      `uv lock --check` with the file hidden, quoting the subsection.
- [x] Skill gaps decided: hiding the SYSTEM file (closed: `XDG_CONFIG_DIRS` with an empty
      `uv/uv.toml`, measured); regenerating the contaminated lock (closed: "then re-lock with the
      file hidden ... and commit"); re-probe on haiku quoted both and produced a working command.
      Privilege to edit `/etc/uv/uv.toml` declined (host administration, outside this skill).
- [x] Routing row added without widening the table (1 line changed); width and fence check over
      added lines: no output; ASCII only; history finder 0 hits.
