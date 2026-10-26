# skill-writer checklist - coding-python-pwshpy (2026-10-26, task settings)

- [x] Change: the skill names the pwshpy 1.8.0 task settings. A translation row for
      `... -Settings (New-ScheduledTaskSettingsSet ...)` (library `settings=TaskSettings(...)`, CLI
      flags), and in the scheduled-task inputs paragraph: the task path as one argument, `-Execute`
      / `-Argument` as `program=` / `arguments=` (one string), a task with no trigger running only
      on demand, the six `TaskSettings` fields with the rule that a `-Dont...`/`-Disallow...` switch
      sets its field to False, the `TaskMultipleInstances` members and CLI spellings, the complete
      list of Linux refusals, and the CLI flag pairs. `TaskSettings` and `TaskMultipleInstances` join
      the public-name lists.
- [x] Receipt held (`skill_receipt.py start meta-skill-writer`); this agent loaded the skill.
- [x] Reference skill, so the test is a retrieval scenario: translate a `New-ScheduledTaskSettingsSet`
      plus `Register-ScheduledTask` command (no trigger, SYSTEM / Highest, three or four settings
      switches) into the library call and the CLI command, quoting the governing line or NONE.
- [x] RED text check of the pre-change file: `TaskSettings`, `New-ScheduledTaskSettingsSet`,
      `execution_time_limit`, `allow_start_if_on_batteries`: 0 hits each (1 each after).
- [x] RED behavioural arm, opus and haiku, given the pre-change translation table: both answered
      the settings NOT IN TABLE and dropped them (a task that is wrong without saying so).
- [x] GREEN round 1 (the row alone), opus and haiku: both wrote `settings=TaskSettings(...)` from
      the row; opus guessed `--no-stop-if-going-on-batteries`, haiku could not translate
      `-DontStopIfGoingOnBatteries`. Closed by naming the field and flag in the row and adding the
      inputs paragraph.
- [x] GREEN round 2, opus and haiku, table plus paragraph: `-DontStopIfGoingOnBatteries` correct on
      both, quoted. New gaps: the `TaskMultipleInstances` members and CLI values, the negative-switch
      rule, which values Linux refuses, the task path and `-Argument`. All closed in the paragraph.
- [x] GREEN round 3, opus and haiku: every part translated with a quoted line, including
      `TaskMultipleInstances.IGNORE_NEW` / `--multiple-instances IgnoreNew` and the path
      `"\\Maint\\Repair"`. New gap: both guessed `arguments=["/quiet"]`, but the parameter is one
      string (`register_scheduled_task(task_path, *, program, arguments: str = "", ...)`, read from
      the installed signature). Closed with `arguments="/quiet /log"`; also stated that the Linux
      refusal list is complete and that HH:MM:SS hours may exceed 23.
- [x] Final re-probe on the final text, haiku, the three questions round 3's fix touched: `arguments`
      is one string (quoted "as one string, `arguments="/quiet /log"`"); Linux accepts
      `allow_hard_terminate=False, allow_demand_start=False` (quoted "and only these"); `72:00:00`
      is valid (quoted "hours may exceed 23"). No new undecided gap. Its one remaining question,
      which systemd keys those two values write, is declined: the skill states the refusal
      contract, and the per-field systemd mapping lives in the pwshpy repository's
      `docs/library-usage.md`; a caller does not need it to act.
- [x] Gaps declined (each pre-existing in RED and outside this change): the `--run-as` values and
      the Linux meaning of `TaskPrincipal.system()` (the principal row and `pwshpy
      register_scheduled_task --help` cover `--run-as`; this change does not touch principals);
      shell quoting of a backslash path on the CLI (a property of the caller's shell, not of
      pwshpy); import lines for every name (the paragraph opens with `from pwshpy import ...` and
      the public-name list carries both new names).
- [x] Every example executed against the installed package on Linux:
      `TaskSettings(allow_start_if_on_batteries=True, execution_time_limit=timedelta(hours=72))`
      constructs and dumps; `TaskMultipleInstances` members are `PARALLEL=Parallel`, `QUEUE=Queue`,
      `IGNORE_NEW=IgnoreNew`, `STOP_EXISTING=StopExisting`; `pwshpy register_scheduled_task --help`
      lists all six settings options. The Windows and Linux behaviour behind the refusal list is
      pinned by the package's own host-mutating tests.
- [x] GREEN diffed against RED both ways: no row or sentence removed; the principal and trigger
      sentences of the paragraph are kept word for word.
- [x] Description measured: unchanged (no frontmatter line in the diff).
- [x] Mirror: the same body as the pwshpy repo's `skills/using-pwsh/SKILL.md`; only the three
      allowed divergences differ.
- [x] Security: no host, address, credential or private path added; `C:\repair.exe` and
      `\Maint\Repair` are placeholders.
