# skill-writer checklist - coding-python-uv (2026-07-18, Windows subprocess PATH gotcha)

Change: added a Gotcha subsection (beside the VIRTUAL_ENV gotcha) - on Windows, spawning a
uv-installed tool (ruff/pytest/pyright, in a venv not on PATH) by bare name via subprocess fails
FileNotFoundError [WinError 2] because CreateProcess resolves argv[0] against the PARENT %PATH%
and ignores the child env dict; resolve argv[0] with shutil.which(name, path=env["PATH"]) first,
and prepend your venv bin. No-op on POSIX.

- [x] Receipt held (skill_receipt.py start meta-skill-writer, this session)
- [x] RED: without it, a tool-runner (e.g. bmk) that spawns bare-name ruff/pytest works on Linux and
      fails ONLY on Windows; the author sets child env PATH and it does nothing, chasing a phantom
      "tool not installed" (fact recovered from the orphaned store this dream:
      feedback-on-windows-resolve-bare-name-subprocess-argv-0-with-shutil-which...).
- [x] GREEN: subsection states the POSIX-vs-Windows CreateProcess difference, the exact fix
      (shutil.which honours PATHEXT), and the venv-bin prepend; one runnable Python example.
- [x] Placement: env/PATH-adjacent to the existing VIRTUAL_ENV gotcha; hub routing untouched (no new
      reference file, no routing-table change).
- [x] Scope: uv-toolchain-on-Windows gotcha; the mechanism is general Windows subprocess behavior.
- [x] Security scan: prose + a generic code snippet; no secrets/hosts/paths.
- [x] CSO description: unchanged (body edit; "deploying Python projects that use uv" covers retrieval).
- [x] Token budget: hub skill, body still an index; one short gotcha added inline (consistent with the
      sibling VIRTUAL_ENV gotcha already inline).
