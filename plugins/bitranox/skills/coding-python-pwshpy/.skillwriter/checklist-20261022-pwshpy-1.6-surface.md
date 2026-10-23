# skill-writer checklist - coding-python-pwshpy (2026-10-22, pwshpy 1.6 surface)

- [x] Change: the skill names the pwshpy 1.6 surface. Translation rows for `Stop-Service -NoWait`,
      `& prog` with a timeout, `Start-Process -Wait` over the whole tree, `Get-WindowsImage`, a
      Windows Update search, `whoami /user`, `Register-ScheduledTask` with a principal and triggers,
      and the elevation calls; a paragraph on the scheduled-task inputs (`TaskPrincipal`,
      `TaskTrigger` and its four trigger types); the `get_process` name difference
      (`MemCompression` vs `Memory Compression`, PID 0); a section "Errors, timeouts and exit codes"
      (the error tree, catch order, `strict=True`, the Windows Update `__main__` guard and whole-result
      search, exec dropping output on timeout, the CLI and runner exit codes 0/1/2/22/64/70/77/110/127
      and the stderr line format); the packed runner's `-PwshPyUv` / `--pwshpy-uv` pin, elevated `uv`
      trust rule and uv-managed Python; a section "Every public name" with the facade helpers, input
      types, every enum and a CLI command index by area. The JSON enum note is corrected: a field is
      the enum's value (process status lowercase, connection state upper-case), not the member name.
      Examples import enums from `pwshpy`.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`); this agent loaded the skill.
- [x] RED route: the change adds reference content (names and behaviours of a library release), so
      the RED is a text check of the pre-change file, not a behavioural arm. Pre-change: the
      package-wide name check (every public callable, enum and exception in `pwshpy.__all__` must
      appear in the skill) listed 28 missing names; grep for `get_windows_image`,
      `get_windows_update`, `wait_tree`, `no-wait`, `strict`, `get_current_identity`, ` 77`, ` 110`,
      `__main__`, `MemCompression`, `PwshPyUv`, `OperationTimeoutError`, `TaskPrincipal`: 0 hits
      each. The same check over the CLI's registered commands listed 61 commands the skill never
      named.
- [x] GREEN text check: the name check prints `none` for the library and for all 88 CLI commands.
- [x] GREEN quote-back, opus and haiku, 12 questions each (non-blocking stop, the `__main__` guard,
      77 vs 110 behind `--elevate`, listing a WIM on Linux, timeout vs refused stop, the jq status
      string for processes, a skipped `uv` under SYSTEM and the pin, proving a task deleted, the
      `MemCompression` name, `build_ps`, `ElevationRequiredError` / `TaskRunLevel`, and a scope
      control "list local users -> pwshpy"): 24 of 24 answered with a quote of the governing cell or
      sentence; question 4 (list every image) and question 5 (the exception for a refused stop) were
      answered by inference in both arms.
- [x] Gaps closed after GREEN: listing every image without an index (now stated in both columns); a
      refused control is the plain `NativeCallError` with the catch order; "nothing quietly skipped"
      reconciled with the skip-with-WARNING default; what a `strict` raise means and the next step;
      the enum import path (examples now `from pwshpy import ...`); hyphenated CLI names
      (`is-elevated`, `config-*`); exit-code precedence ("any other `PwshPyError`") and that
      `exec`, `--elevate` and runners pass the child's code through; `--elevate` is a no-op when
      elevated; the stderr line format.
- [x] Re-probe on the final text, opus and haiku, the 8 questions the fixes touched: 16 of 16 with a
      quote, except the already-elevated half of question 3 (`--elevate` when already elevated),
      NONE in both arms; closed afterwards by the no-op clause and not re-probed, with the stderr
      line format added in the same pass.
- [x] Gaps declined: how to end a hung service (out of scope: process control is not the stop
      verb's contract); the Windows ACL detail of the `uv` trust rule (routed to
      `docs/power-tools.md` in "Further reading"); which other listings take `strict` (only
      `get_service` and `get_scheduled_task` do, and the skill names exactly those); where a library
      WARNING appears (stdlib `logging`, the caller's configuration); the state after a service
      timeout beyond "the control WAS issued".
- [x] GREEN diffed against RED both ways: no row or section was removed; the two edited sentences
      (JSON enum note, the error-handling bullet in "When to use") keep their earlier claims, the
      enum note made exact.
- [x] Every example executed against the installed package on Linux: the `get_service` filter
      (with a service present on the host), `TaskPrincipal(...)`, `TaskPrincipal.system()`,
      `DailyTrigger`/`BootTrigger` construction, an account name refused as `user_id`,
      `from pwshpy import ServiceState, EventLevel, ps`; `pwshpy exec` passing through exit 3 and
      exiting 110 on a timeout; `pwshpy get_windows_image ... --index` on a built WIM. Windows-only
      and mutating rows (service stop, task registration, Windows Update) were not executed.
- [x] Description measured: unchanged (616 characters).
- [x] Mirror: the same body as the pwshpy repo's `skills/using-pwsh/SKILL.md`; the only differences
      are the three conventional ones (`name:`).
- [x] Security scan: prose and examples only; paths are `install.wim`, `C:\Tools\uv.exe` and
      `\T`; no secrets, hostnames or addresses.
