---
name: coding-python-pwshpy
description: Use when issuing or running PowerShell (pwsh) commands, or writing, modifying, or debugging a PowerShell / .ps1 script - prefer pwshpy instead - a genuinely Pythonic PowerShell (typed records + a lazy pipeline over native OS bindings, never a pwsh.exe subprocess, never text parsing), as a Python library (from pwshpy import ps) or the pwshpy CLI (install/run via uv - `uv tool install pwshpy` or `uvx pwshpy`). Better error handling and reporting (real exceptions and real exit codes, nothing silently swallowed) plus clean typed JSON instead of Get-* text. Covers using pwshpy and translating cmdlets / .ps1 to it.
---

# using-pwsh

pwshpy is a genuinely Pythonic PowerShell: typed records + a lazy pipeline over native OS bindings
(win32 / wmi / winreg / psutil / socket / systemd / pwd), never a `pwsh.exe` subprocess and never
text parsing. When you are about to write a PowerShell command or a `.ps1`, shell out to
`pwsh` / `wevtutil` / `sc`, or hand-roll `pywin32` / `win32evtlog` with manual XML - reach for pwshpy
instead. Source and full docs: https://github.com/bitranox/pwshpy (this repo is itself a Claude Code
plugin/marketplace: install anywhere with `/plugin marketplace add bitranox/pwshpy` then
`/plugin install pwshpy`).

## When to use

- About to **issue or run any PowerShell command** - a `Get-*` / `Set-*` cmdlet, a `pwsh` one-liner,
  or a `.ps1` - for OS/admin work (processes, services, event log, registry, scheduled tasks, ACLs,
  local accounts, files, network, credentials, known folders, desktop shortcuts). Prefer pwshpy
  **even for a single one-off command.**
- Want **better error handling and reporting**: a failed command should raise / exit non-zero with a
  clear message, not be silently swallowed. PowerShell's default is a *non-terminating* error you
  must remember `-ErrorAction Stop` (or `$?`/`$LASTEXITCODE`) to catch; pwshpy failures are real
  Python exceptions (`PwshPyError` and subtypes) in the library and a real non-zero exit with a
  message on the CLI - nothing quietly skipped (a listing that skips an item it cannot read logs a
  WARNING naming it, and `strict=True` makes it raise instead).
- About to shell out to `pwsh` / `powershell` / `wevtutil` / `sc`, or hand-roll `pywin32` / `wmi` /
  `win32evtlog` with manual XML parsing.
- Want typed objects instead of text you re-parse; a memory-bounded read of a huge event log; or one
  script that runs on Windows AND Linux.
- On the command line: clean JSON + a real exit code instead of `Get-* | ConvertTo-Json` (and its
  single-item-collapse quirk).
- Need to **hand a Python script to a machine with no Python** (a Windows admin, a colleague):
  `pwshpy pack tool.py` makes one self-extracting file that installs `uv` and runs it - a `.ps1`
  for Windows or a `.sh` for any POSIX `/bin/sh` (not only bash). Declare third-party deps in a
  PEP 723 block or with `--with`.

**Not installed?** pwshpy is one `uv tool install pwshpy` away (or run ad-hoc with
`uvx pwshpy ...`), so reach for it rather than falling back to raw `pwsh`.

**When NOT:** a PowerShell **module-only** cmdlet with no pwshpy wrapper -> still use pwshpy via
`ps.cmdlet("Verb-Noun", **params)` (needs the `[full]` extra). A genuinely interactive PowerShell TUI
is out of scope.

## Core idea

Typed Pydantic records stream through a lazy `Pipeline`
(`.where(pred).select(fn).take(n).first() / .to_list()`) over native bindings. Two backends, same
records: **native** (win32/wmi/winreg/psutil/socket/systemd/pwd - fast, the default) and **.NET**
(the real PowerShell 7 SDK hosted in-process, behind `pip install "pwshpy[full]"`, for the
AD/Exchange/Azure long tail and running any `.ps1`). Never spawns `pwsh.exe`; never parses text.

## Library - `from pwshpy import ps`

```python
from pwshpy import ServiceState, ps

# running services whose name contains "sql" -> one JSON line each
for s in ps.get_service().where(lambda s: s.status is ServiceState.RUNNING and "sql" in s.name.lower()):
    print(s.model_dump_json())
```

`ps.get_service()` returns a lazy `Pipeline[ServiceInfo]`; filter and shape in Python, not with
cmdlet switches. Records are Pydantic (`.model_dump()` / `.model_dump_json()` for free). Status/level
fields are canonical English `str` enums (locale-independent), never a localized OS string.

## CLI - prefer `pwshpy` over `pwsh` (even for one-liners)

```bash
pwshpy get_service --jsonl | jq -c 'select(.status == "Running" and (.name | test("sql"; "i")))'
```

`--jsonl` streams one record per line (lazy end to end); `--json` emits a single array; the default
is a human table. Why prefer it over `pwsh`: typed JSON (no `ConvertTo-Json` single-item-collapse
quirk), a real process exit code, UTF-8 with no BOM, memory-bounded streaming, and real errors (a
failure exits non-zero with a message, not a swallowed non-terminating error). See `pwshpy --help`
and `pwshpy <command> --help`.

An enum field in the JSON is the enum's **value**, never the upper-case member name - filter on the
exact string: service status `"Running"` / `"Stopped"`, event level `"Error"` / `"Warning"` /
`"Information"` / `"Verbose"`, but process status lowercase (`"running"`, psutil's values) and
connection state upper-case (`"LISTEN"`). So the jq above uses `.status == "Running"`, not
`"RUNNING"`. In Python compare the enum member directly (`s.status is ServiceState.RUNNING`).

## Translate a cmdlet / .ps1

Method: replace each cmdlet with its `ps.*` verb; filter/shape in Python (or `jq` over `--jsonl`);
anything without a wrapper -> `ps.cmdlet("Verb-Noun", **params)`. pwshpy removes these PowerShell
traps for free: single-item collapse, `$null`-operand order, a forgotten `-ErrorAction Stop` (every
failure raises), the `$x = Get-WinEvent` memory blow-up (reads stream, memory-bounded), `Out-File`
UTF-16/BOM, and localized `Administrators` / SID (records key on SID / uid, not a translated name).

| PowerShell                                                            | pwshpy (library)                                                                                                   | CLI                                                                                                                         |
|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| `Get-Process`                                                         | `ps.get_process()`                                                                                                 | `pwshpy get_process`                                                                                                        |
| `Get-Service`                                                         | `ps.get_service()`                                                                                                 | `pwshpy get_service`                                                                                                        |
| `Start-Service N`                                                     | `ps.start_service("N")`                                                                                            | `pwshpy start_service N`                                                                                                    |
| `Get-WinEvent -LogName L`                                             | `ps.get_win_event("L")` (streams)                                                                                  | `pwshpy get_win_event L`                                                                                                    |
| `Get-ChildItem P`                                                     | `ps.get_child_item("P")`                                                                                           | `pwshpy get_child_item P`                                                                                                   |
| `Get-Content P`                                                       | `ps.get_content("P")`                                                                                              | `pwshpy get_content P`                                                                                                      |
| `Get-ItemProperty K` (reg)                                            | `ps.get_item_property("K")`                                                                                        | `pwshpy get_item_property K`                                                                                                |
| `Get-Acl P`                                                           | `ps.get_acl("P")`                                                                                                  | `pwshpy get_acl P`                                                                                                          |
| `Get-LocalUser`                                                       | `ps.get_local_user()`                                                                                              | `pwshpy get_local_user`                                                                                                     |
| `Get-ScheduledTask`                                                   | `ps.get_scheduled_task()`                                                                                          | `pwshpy get_scheduled_task`                                                                                                 |
| `Get-CimInstance C`                                                   | `ps.get_cim_instance("C")`                                                                                         | `pwshpy get_cim_instance C`                                                                                                 |
| `Test-Connection H`                                                   | `ps.test_connection("H")`                                                                                          | `pwshpy test_connection H`                                                                                                  |
| `Resolve-DnsName N`                                                   | `ps.resolve_dns_name("N")`                                                                                         | `pwshpy resolve_dns_name N`                                                                                                 |
| `Invoke-WebRequest U`                                                 | `ps.invoke_web_request("U")`                                                                                       | `pwshpy invoke_web_request U`                                                                                               |
| `Get-ADUser` (module)                                                 | `ps.get_ad_user(Filter="*")` / `ps.cmdlet("Get-ADUser", Filter="*")`                                               | `pwshpy get_ad_user -p Filter=*`                                                                                            |
| `Stop-Service N -NoWait`                                              | `ps.stop_service("N", wait=False)` (returns at once, typically `StopPending`)                                      | `pwshpy stop_service --no-wait N`                                                                                           |
| `& prog a b`                                                          | `ps.exec(["prog", "a", "b"], timeout=S).check()`                                                                   | `pwshpy exec --timeout S -- prog a b`                                                                                       |
| `Start-Process P -Wait` (whole tree)                                  | `ps.exec(["P"], wait_tree=True, timeout=S)`                                                                        | `pwshpy exec --wait-tree --timeout S -- P`                                                                                  |
| `Get-WindowsImage -ImagePath W -Index N`                              | `ps.get_windows_image("W")` (every image), `index=N` (one; any OS, no DISM)                                        | `pwshpy get_windows_image W [--index N]`                                                                                    |
| Windows Update search (`Get-WindowsUpdate`, `IUpdateSearcher.Search`) | `ps.get_windows_update(criteria=C, timeout=S)` (read-only)                                                         | `pwshpy get_windows_update --timeout S`                                                                                     |
| `whoami /user`                                                        | `ps.get_current_identity()` (from the token, never `USERNAME`)                                                     | `pwshpy get_current_identity`                                                                                               |
| `Register-ScheduledTask` + `-Principal` / `-Trigger`                  | `ps.register_scheduled_task("\\T", program="P", principal=TaskPrincipal.system(), triggers=[DailyTrigger(at=dt)])` | `pwshpy register_scheduled_task \T --program P --run-as local_system --run-level highest --daily 2026-11-01T03:00:00+01:00` |
| `#Requires -RunAsAdministrator` / `-Verb RunAs`                       | `ps.require_elevation()` / `ps.elevate()`                                                                          | `pwshpy --elevate <command>`                                                                                                |
| `[Environment]::GetFolderPath('Desktop')`                             | `ps.get_known_folder(KnownFolder.DESKTOP)` (a `Path`, `None` when missing; any OS)                                 | `pwshpy get_known_folder Desktop`                                                                                           |
| WScript.Shell `CreateShortcut(P)` + `.Save()`                         | `ps.new_shortcut("P", target=T, arguments=["a", "b"], force=False)` (Windows; returns the stored `ShortcutInfo`)   | `pwshpy new_shortcut P --target T [-f] -- a b`                                                                              |
| WScript.Shell `CreateShortcut(P)` (read)                              | `ps.get_shortcut("P")` (Windows)                                                                                   | `pwshpy get_shortcut P`                                                                                                     |
| *anything else*                                                       | `ps.cmdlet("Verb-Noun", **params)` (needs `[full]`)                                                                | `pwshpy cmdlet Verb-Noun -p K=V`                                                                                            |

Example - porting `$svc = Get-Service Spooler; if ($svc.Status -ne 'Running') { Start-Service Spooler };
Get-WinEvent -LogName System | ? { $_.Level -eq 2 } | Export-Csv report.csv`:

```python
from pwshpy import EventLevel, ps

ps.start_service("Spooler")  # idempotent: a no-op if already running, so the status check is gone
errors = ps.get_win_event("System").where(lambda e: e.level is EventLevel.ERROR)  # Level 2 -> ERROR enum
ps.write_records("report.jsonl", errors, jsonl=True)  # streams record-by-record, memory-bounded
```

(pwshpy writes JSON/JSONL, not CSV; if you specifically need CSV, use the stdlib `csv` module inside
the `for e in errors:` loop - it still streams.)

Scheduled-task inputs (`from pwshpy import ...`): `TaskPrincipal(user_id=..., logon_type=TaskLogonType.S4U,
run_level=TaskRunLevel.HIGHEST)` with `user_id` a SID or a `WellKnownSid` member on Windows and a decimal
uid on Linux (an account name is refused); `TaskPrincipal.system()` is SYSTEM, elevated. `triggers` is a
sequence of `TaskTrigger`: `OnceTrigger(at=dt)`, `DailyTrigger(at=dt, every_days=1)`,
`BootTrigger(delay=timedelta(...))`, `LogonTrigger(user_id=SID)`; every `dt` must carry a UTC offset.
Logon triggers, `every_days > 1` and a logon type are Windows-only (`PlatformUnsupportedError` on Linux).

`get_process` names a process as psutil does: on Windows `MemCompression` is `Get-Process`'s
`Memory Compression` and PID 0 `System Idle Process` is `Idle`; match by `pid` where it matters.

Known folders and shortcuts: `get_known_folder` takes a `KnownFolder` member or its .NET
`SpecialFolder` name (`Desktop`, `MyDocuments`, `LocalApplicationData`, `ApplicationData`,
`CommonApplicationData`, `Programs`; exact case in the library, any case on the CLI) and returns what
pwsh's `GetFolderPath` returns on that OS (a redirected Windows Desktop included), `None` where pwsh
returns `""`; `Programs` off Windows raises `PlatformUnsupportedError`. Never guess
`Path.home() / "Desktop"`. `new_shortcut`'s `target` must be an absolute Windows path or start with
`%NAME%\` (a bare `notepad.exe` is a `ConfigurationError`), and `arguments` is an argv list (a str
is refused, never split), stored joined by `subprocess.list2cmdline`. Values Windows would silently
truncate are refused up front (`ConfigurationError`: target and `.lnk` path 259 characters, joined
arguments 32767, description / working directory / icon 260); an env-prefixed target whose
*expansion* passes 259 is refused by Windows itself (`NativeCallError` 0x80004005, nothing written).
An existing file needs `force=True`; no directory is created.

## Errors, timeouts and exit codes

Every failure raises a `PwshPyError` subclass, except a bad argument (`ValueError`, CLI exit 22, 87 on Windows);
catch a subclass before its parent:

- `NativeCallError` - an OS call failed, `.check()` saw a nonzero exit, or a `strict=True` listing
  hit an item it cannot read. Its subclasses: `OperationTimeoutError` (`.timeout` holds the limit:
  `exec(timeout=)`, a service start/stop/restart that did not settle - the control WAS issued -,
  `get_windows_update`, `wait_process(timeout=)`, `resolve_dns_name(timeout=)` and, on Linux, the
  local-account verbs (`new_local_user`, `remove_local_user`, `enable_local_user`,
  `disable_local_user`, `new_local_group`, `remove_local_group`, `add_local_group_member` and
  `remove_local_group_member`, `timeout=` default 30 s)) and `ElevationDeclinedError` (the UAC
  prompt or sudo's password refused).
  A control the OS refuses (a service stop denied, a missing executable) is the plain
  `NativeCallError`: `except OperationTimeoutError` first, then `except NativeCallError`.
- `ElevationRequiredError` (`require_elevation()`), `PlatformUnsupportedError` (no analog on this OS),
  `ConfigurationError`, `PowerShellError` / `FeatureUnavailableError` (.NET, `[full]`; `run`, `cmdlet`
  and the module wrappers `get_ad_user`, `get_ad_group`, `get_ad_computer`, `get_mailbox`, `get_az_vm`
  and `get_az_resource_group` raise `PowerShellError` past their `timeout`, default none), `PackError`.
  `download_file`, `invoke_web_request` and `invoke_rest_method` raise the plain `NativeCallError`
  ("timed out") when a connect or read outlasts `timeout`; `test_connection` returns `reachable=False`;
  `elevate(wait=True)` has no limit.

`get_service()` and `get_scheduled_task()` skip, with a logged WARNING, an item the caller cannot
read; pass `strict=True` (CLI `--strict`) when "not listed" must mean "does not exist" (a raise
then means this caller cannot tell; ask again elevated).
`get_windows_update` runs the search in a `spawn` child that re-imports the calling script, so that
script needs an `if __name__ == "__main__":` guard (without it: `NativeCallError`, "worker exited
without a result"); the search returns its whole result on the first iteration, so `.take(n)` does
not shorten it. Select updates by category through `category_details[].category_id` (the
category GUID, lower case, e.g. `0fa1201d-4330-4fa8-8ae9-b877473b6441` for Security Updates),
never through `categories` or `title`, which the Windows Update agent localizes:
`.where(lambda u: any(c.category_id == GUID for c in u.category_details))`. `exec` drops the output
written before a timeout.

CLI and packed-runner exit codes (an error also writes one `ErrorName: message` line, or a `pwshpy: ...`
line from a runner, to stderr): 0 ok, 1 any other `PwshPyError`, 2 usage error, 22 a refused value
(`ValueError`; 87 on Windows), 64 a relative `-PwshPyUv` / `--pwshpy-uv`, 70 the runner failed before the script ran
(the elevated `.ps1` child, or an elevated run that cannot return to the caller's directory), 77
elevation declined (`pwshpy --elevate`, `-PwshPyElevate`, `--pwshpy-elevate`; stderr line `pwshpy:
elevation declined`), 110 `OperationTimeoutError`, 127 a missing or untrusted `uv`, or no `sudo` for a
runner's elevation. `pwshpy exec`, `pwshpy --elevate <command>` (a no-op when already elevated) and a
runner otherwise return the program's, command's or script's own code, so check the stderr line too.

## Still writing a `.ps1`? Eight traps

When a `.ps1` is still the deliverable (pwshpy is not wanted on the target, or the script only
forwards to a native tool), each of these passes a quick test and fails in use. `5.1` is Windows
PowerShell, `7` is pwsh 7 (checked on 5.1.26100 and 7.6.6 unless the notes below the table say
otherwise); a trap listed for one shell does not occur on the other.

| Trap                                                                                                                                                                                             | Shells                                    | Do instead                                                                                                                                 |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `[CmdletBinding()]` or any `[Parameter()]` attribute makes the script advanced, so a forwarded `-v` / `-d` / `-ea` binds to `-Verbose` / `-Debug` / `-ErrorAction` and never reaches the child   | 5.1 and 7                                 | no param block in a forwarding wrapper; read `$args` by hand (it keeps empty strings, quotes and `-v`)                                     |
| A function returns everything written to its output stream: `Write-Output "--- step"` then `return $p.ExitCode` makes `$rc = Step` an array, so `exit (Step)` and `if ($rc -ne 0)` both go wrong | 5.1 and 7                                 | narrate with `Write-Host`, so the value is the function's only output; or call `exit` inside the function that ran the child               |
| `curl` and `wget` are aliases of `Invoke-WebRequest`: `curl -fsSL -o f url` fails on the parameter name, writes no file, and `$LASTEXITCODE` stays empty                                         | 5.1                                       | spell the binary: `curl.exe` (and `tar.exe`)                                                                                               |
| Native stderr becomes error records: under `$ErrorActionPreference = 'Stop'`, `& tool 2>&1 \| ForEach-Object { ... }` dies with `NativeCommandError` even when the tool succeeded                | 5.1                                       | `& tool > out.txt 2>&1`, then read the file; check `$LASTEXITCODE` and the tool's result before believing it failed                        |
| `pwsh -File s.ps1 --out=C:\data` is split at the colon before the script runs: it arrives as `--out=C` and `\data`                                                                               | 7 (`powershell.exe -File` keeps it whole) | document the space form `--out C:\data`; nothing inside the script can repair it                                                           |
| A probe reading a file another process may be writing (`Get-FileHash` or `Get-Content` in an "is the cache valid?" check before taking a lock) throws under `Stop` and ends the script           | 5.1 and 7                                 | wrap the probe in `try/catch` returning `$false`, so a race means "re-extract under the lock"; the lock never covers a read made before it |
| A number printed as text by `-f`, `.ToString()`, `Write-Host` args or bare output takes the culture: a German host prints `444,2`, the caller's `float()` raises, `[0-9.]+` keeps `444`          | 5.1 and 7                                 | emit `$v.ToString([cultureinfo]::InvariantCulture)` or an integer; or parse `[0-9.,]+`, swap `,` for `.`; test on the host's real bytes    |
| `icacls p /grant:r SYSTEM:F Administrators:F` on a non-English host: the name does not resolve, icacls exits 1332 and applies NONE of the grants; `& echo ok` or `>nul` hides it                 | 5.1 and 7                                 | grant by SID: `*S-1-5-18:(OI)(CI)F`, `*S-1-5-32-544:(OI)(CI)F`; fail on `$LASTEXITCODE -ne 0`; read `icacls p` back                        |

Test a forwarding wrapper with an empty string, an embedded double quote, `-v` and a `C:\` path.

**The number trap breaks the consumer, not the script.** It bites in the Python (or shell) code
that parses text a Windows host printed, typically over ssh, and nothing on that side hints that a
locale is involved. It breaks only on a value with a fraction, so a probe passes for months on
whole numbers and then meets its first `444,2`; a `[0-9.]+` (or `[\d.]+`) regex is worse than the
`float()` crash, because it silently keeps `444` and the gate compares against the wrong number.
String interpolation and concatenation (`"FREEGB=$v"`, `"FREEGB=" + $v`) use the invariant
culture and print `444.2`; `-f`, `.ToString()`, `Write-Host "FREEGB=" $v` and a bare `$v` print
`444,2` (measured on pwsh 7 under `de-DE`). Where you choose the format, emit an integer or an ISO
string rather than a culture-formatted float. Test the parser on bytes the host really returned: a
retyped `444.2` passes every time and proves nothing. pwshpy records carry numbers typed, so the
trap applies only to text a script prints.

**The icacls trap holds for every native tool given a well-known group name**, from cmd as much as
from a `.ps1`: the names are localized (German `Administratoren`), the SIDs are not. One name that
does not resolve refuses the whole command, so the valid grants and `/inheritance:r` are dropped
too and the path keeps its inherited, wider ACL. The exit code 1332 (observed on a German host;
icacls is native, so the shell does not matter) is `ERROR_NONE_MAPPED` ("No mapping between
account names and security IDs was done"; German "Zuordnungen von Kontennamen und
Sicherheitskennungen wurden nicht ..."). cmd's `&` runs the next command whatever the first
returned, so `& echo locked` reports success after a failure: chain with `&&` or check the exit
code. A local user account's own name (`svcuser`) is not localized and can stay a name; only the
built-in and well-known groups and accounts need the SID. Read `icacls p` back and confirm every
grant is listed and, after `/inheritance:r`, that no inherited `(I)` entry remains.
`net localgroup Administrators` takes no SID; add members with
`Add-LocalGroupMember -SID S-1-5-32-544 -Member <user>`. pwshpy's `add_acl_ace` accepts a SID
string (`S-1-5-32-544`) as the trustee on Windows; pass one, because a name is looked up on the
target machine and the English name of a built-in group fails there the same way (pwshpy raises
instead of failing silently).

## Ship a script to a machine without Python - `pwshpy pack`

Hand someone a Python tool as ONE self-extracting file: it unpacks itself into a per-user cache,
installs `uv` if the machine has none, runs the script, and returns the script's own exit code, with
no Python and nothing pre-installed. Pick the format for the target - a `.ps1` for Windows
PowerShell 5.1 / pwsh 7, or a `.sh` for **any POSIX `/bin/sh`, not only bash** (dash, busybox ash,
macOS `sh`, ...). `unpack` is the inverse, so the recipient can read, edit, and repack it.

```bash
pwshpy pack tool.py -o tool.ps1          # embeds tool.py + every local module it imports
pwshpy pack tool.py -o tool.sh           # ...as a POSIX shell runner instead (auto-detected from .sh)
pwshpy pack tool.py -o run --format sh   # force the shell runner for a name without a .sh suffix
pwshpy pack tool.py --with rich          # add a dependency at pack time (repeatable)
pwshpy pack tool.py --include data.json  # embed a file no import reveals
pwshpy unpack tool.ps1 -o src/           # restore the sources, then edit and repack (reads .ps1 or .sh)
```

```python
from pwshpy import ps, PackOptions, RunnerFormat

ps.pack_script("tool.py", "tool.ps1", options=PackOptions(with_packages=["rich"]))
ps.pack_script("tool.py", "tool.sh", options=PackOptions(format=RunnerFormat.SH))
ps.unpack_script("tool.ps1", "src/")  # sniffs zip (.ps1) vs tar (.sh) - never told the format
```

Pack and unpack are pure Python (`zipfile`/`tarfile` + base64), so you can build a `.sh` on Windows
and a `.ps1` on Linux, and `unpack` reads either format on either OS - the format is about the
TARGET, not the host you pack on. Only *running* the artefact needs the matching interpreter.

**Declare the packed script's third-party dependencies** - they are NEVER guessed from import names
(an import name usually is not a package name: `yaml` is PyYAML, `cv2` is opencv-python). Only
third-party distributions need it; the standard library and the entry's local modules travel
automatically. Two ways:

1. A [PEP 723](https://peps.python.org/pep-0723/) block at the top of the entry script - uv resolves
   it **and** fetches a matching interpreter on the target machine:

   ```python
   # /// script
   # requires-python = ">=3.12"
   # dependencies = ["rich", "httpx"]
   # ///
   ```

2. Or at pack time: `pwshpy pack tool.py --with rich --with httpx` (CLI) /
   `PackOptions(with_packages=["rich", "httpx"])` (library).

The artefact forwards every argument to your script untouched (empty strings, quotes, unicode,
`-v`/`-d`) and takes its own help/info/clean/no-install-uv/elevate switches - spelled
`-PwshPyHelp` ... on the `.ps1`, `--pwshpy-help` ... on the `.sh` - plus `-PwshPyUv PATH` /
`--pwshpy-uv PATH` to pin the `uv` it runs (absolute path; relative exits 64). Run elevated
(administrator, SYSTEM or root) it only runs a `uv` no other account can modify (on POSIX: root
alone), skipping others with a `pwshpy: skipping uv at` line and refusing an untrusted pin with exit
127, and only a uv-managed Python from the running account's own data directory, found with
`uv python find --system`, checked like the `uv` and named to `uv run --python` (the first elevated
run downloads one, so it fails offline or with `UV_PYTHON_DOWNLOADS` `never` / `manual` and none
installed); every uv call it makes reads no `uv.toml` (`--no-config`).

## Every public name

From `pwshpy`: the facade `ps` (an instance of `Ps`; `build_ps()` builds a fresh one), `get_config()`
(the layered configuration the CLI reads) and `print_info()` (the package metadata `pwshpy info`
prints). Inputs: `TaskPrincipal`, `TaskTrigger`, `OnceTrigger`, `DailyTrigger`, `BootTrigger`,
`LogonTrigger`, `PackOptions`, `RunnerFormat`. Enums to compare against: `ProcessStatus`,
`ConnectionState`, `TransportProtocol`, `AddressFamily`, `ServiceState`, `ServiceStartType`,
`ServiceKind`, `EventLevel`, `TaskState`, `TaskRunLevel`, `TaskLogonType`, `RegistryHive`,
`RegistryValueType`, `AceType`, `WellKnownSid` (SID strings), `IntegrityLevel`, `ImageArchitecture`,
`KnownFolder` (also the input of `get_known_folder`). Errors: listed above. Records (`ProcessInfo`,
`ServiceInfo`, `WindowsImage`, `WindowsUpdate`, `CurrentIdentity`, `ScheduledTaskInfo`,
`ShortcutInfo`, ...) are what the calls return; read their fields.

CLI commands (`pwshpy <command> --help` for flags; most use underscores, `is-elevated`, `config-deploy`
and `config-generate-examples` hyphens), by area:

- processes and system: `get_process`, `stop_process`, `wait_process`, `get_uptime`, `env`,
  `get_computer_info`, `get_current_identity`, `get_hotfix`, `get_windows_image`, `get_windows_update`,
  `restart_computer --yes`, `stop_computer --yes` (Windows; nothing happens without `--yes`)
- network: `get_net_tcp_connection`, `get_net_udp_endpoint`, `get_net_adapter`, `get_net_ip_address`,
  `resolve_dns_name`, `test_connection`, `invoke_web_request`, `invoke_rest_method`, `download_file`
- storage and files: `get_volume`, `get_child_item`, `get_item`, `get_content`, `test_path`, `new_item`,
  `copy_item`, `move_item`, `remove_item`, `write_text`
- services: `get_service`, `start_service`, `stop_service`, `restart_service`, `set_service`
- event log: `get_win_event`, `clear_event_log`
- scheduled tasks: `get_scheduled_task`, `register_scheduled_task`, `unregister_scheduled_task`,
  `enable_scheduled_task`, `disable_scheduled_task`, `start_scheduled_task`, `stop_scheduled_task`
- accounts: `get_local_user`, `get_local_group`, `new_local_user`, `remove_local_user`,
  `enable_local_user`, `disable_local_user`, `new_local_group`, `remove_local_group`,
  `add_local_group_member`, `remove_local_group_member`
- ACLs: `get_acl`, `add_acl_ace`, `remove_acl_ace`, `set_owner`
- known folders and shortcuts: `get_known_folder` (any OS), `get_shortcut`, `new_shortcut` (Windows)
- registry and CIM (Windows): `get_item_property`, `registry_keys`, `set_item_property`,
  `remove_item_property`, `new_registry_key`, `remove_registry_key`, `get_cim_instance`
- credentials and elevation: `save_credential`, `load_credential`, `delete_credential`, `is-elevated`,
  the global `--elevate`
- running things: `exec`, `pack`, `unpack`; .NET (`[full]`): `run`, `cmdlet`, `get_command`,
  `get_ad_user`, `get_ad_group`, `get_ad_computer`, `get_mailbox`, `get_az_vm`, `get_az_resource_group`
- configuration and diagnostics: `info`, `config`, `config-deploy`, `config-generate-examples`,
  `logdemo` (a logging demo)

## Install

```bash
uv tool install pwshpy            # the CLI on PATH   (or run once: uvx pwshpy@latest --help)
pip install "pwshpy[full]"        # + the .NET backend for ps.run / ps.cmdlet / module cmdlets
```

## Common mistakes

- Shelling out to `pwsh` / `powershell` / `wevtutil` / `sc`, or hand-rolling `pywin32` /
  `win32evtlog` / `wmi` + XML -> use the `ps.*` verb.
- Parsing `Get-* | Format-*` / `ConvertTo-Json` text -> pwshpy already returns typed records / clean
  JSON.
- Forgetting `--jsonl` when piping the CLI to `jq` / `head` (the default human table is not for
  machines).
- Reaching for a PowerShell module cmdlet and giving up -> `ps.cmdlet("Verb-Noun", **params)` (needs
  `[full]`).
- `.to_list()` on a huge event log -> iterate the pipeline instead (it streams, O(1) memory).
- `pwshpy pack`ing a script whose third-party deps are in neither a PEP 723 block nor `--with` -> the
  pack warns and the script dies on its first import on the target. Declare them; import names are
  never auto-guessed into package names.

## Further reading

The CLI and library API are discoverable from the INSTALL (always your version): run
`uvx pwshpy --help` (and `<subcommand> --help`) for per-command flags, and
`python -c "import pwshpy; help(pwshpy)"`. The narrative docs below are NOT shipped in the wheel; open
each on the default branch (latest, matching your `uv`-installed version) at
`https://github.com/bitranox/pwshpy/blob/master/<path>`:

| Topic                                                                                                | Path under `.../blob/master/`       |
|------------------------------------------------------------------------------------------------------|-------------------------------------|
| Full cmdlet -> pwshpy table (every command, API + CLI columns)                                       | `COMMANDS.md`                       |
| Per-switch / per-parameter porting rationale                                                         | `docs/powershell-switch-mapping.md` |
| Library + the lazy Pipeline (`where`/`select`/`take`/`first`/`to_list`)                              | `docs/library-usage.md`             |
| CLI reference (`--json`/`--jsonl`, per-command flags, the exit-code table)                           | `docs/cli-reference.md`             |
| Power tools (elevation, `exec` + `wait_tree`, Windows Update, credentials, `pack` runner trust rule) | `docs/power-tools.md`               |
| Backends + platforms (native vs .NET, one-script cross-OS)                                           | `docs/backends-and-platforms.md`    |
| Layered configuration (`--set`, profiles, env, `config-deploy`)                                      | `CONFIG.md`                         |
