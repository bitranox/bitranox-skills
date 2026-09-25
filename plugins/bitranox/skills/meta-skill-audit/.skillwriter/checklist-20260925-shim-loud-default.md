# skill-writer checklist - meta-skill-audit (2026-09-25, run-python.sh loud by default)

`hooks/run-python.sh` changed its default: a call without `--hook` now exits 3 when it cannot run
the script, and only a `--hook` launch (every hooks.json registration) fails open. One sentence of
the Procedure explained the launch command by the old default. The launch command itself is
unchanged and still correct.

- [x] Skill type: reference/technique. The changed sentence states what the shim does, so the RED
      is a ground-truth check of the old text against the shim, not a pressure scenario.
- [x] Behavioural RED deliberately NOT used: this skill is INSTALLED on this machine, so a probe
      answers from the shipped wording rather than from the draft.
- [x] RED: the old sentence said that without `BITRANOX_RUN_PYTHON_STRICT` a mistyped script path
      "prints one stderr line and exits 0". Run against the new shim, `bash hooks/run-python.sh
      /nonexistent/no_such.py` prints `run-python.sh: script not found: ...` and exits 3.
- [x] GREEN: every mode the new sentence names was executed: CLI 3, CLI with the variable 3,
      `--hook` 0, `--hook` with the variable 3. Pinned by hooks/tests/test_run_python_sh.py.
- [x] `tests/test_script_prepass_checks.py::test_skill_md_never_sends_a_cli_through_the_fail_open_launcher_unguarded`
      still passes: the launch line keeps `BITRANOX_RUN_PYTHON_STRICT=1`.
- [x] Scope: one sentence. No step reordered, description and front matter untouched.
- [x] Present tense, ASCII only, no machine path or address added.
