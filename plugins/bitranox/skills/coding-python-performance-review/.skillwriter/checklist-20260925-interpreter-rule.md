# skill-writer checklist - coding-python-performance-review (2026-09-25, one interpreter rule)

Change: no bash block runs a bare `python`. `bx_py` (the first of `python3`, `python`, `py -3`
that actually starts) launches `setup_env.py` when uv is absent and backs `read_field`; every
other step runs the recorded `"$PYTHON_CMD"`, now quoted, including both TESTDIR heredocs. Every
block that reads `session.json` exits 2 when it cannot, instead of writing under an empty scratch
path. Step 2 states the rule as a paragraph. `setup_env.py`'s docstring example uses `python3`.

- [x] Receipt issued (`skill_receipt.py start meta-skill-writer`).
- [x] Skill type: technique, tool-bearing. Test approach: quote-back retrieval arm (quote or NONE,
      haiku, inert `bitranox:baseline-probe`, text pasted). Moved: Q1 (read a field with only
      `python3` on the machine), Q2 (interpreter of the TESTDIR script), Q3 (session.json
      unreadable). Control: Q4 (no `pyproject.toml`).
- [x] Scope: Step 2 prose, the nine bash blocks' preambles, every `$PYTHON_CMD` use; frontmatter,
      `name:` and description untouched.

## RED

- [x] Inherited coverage: `redcheck --corpus-cascade` on the worktree reported STRONG on shared
      terms (fields, heredoc, inline, interpreter, python3) from CLAUDE.local.md indexes; the probe
      order is taught only in memory fact bodies an inert probe cannot read. Route taken: the
      quote-back text check of the pasted artifact, which inherited context cannot answer.
- [x] RED, pre-change text: Q1 quoted `python -c ...` and said the text does not address a
      python3-only machine; Q2 quoted `TESTDIR="$(python - <<'PY'`; Q3 NONE. Control Q4 right with
      its quote. Skill gaps reported: portability of `python -c`, no handling of an unreadable
      session.json, `python` and `$PYTHON_CMD` mixed with no rule.

## GREEN

- [x] Q1 `read_field tmpdir`, quoting the `bx_py` loop, works with only python3; Q2 the recorded
      `"$PYTHON_CMD"`, quoting `"$PYTHON_CMD" - <<'PY'`; Q3 exit 2, quoting the Interpreter rule
      paragraph. Skill gaps: none reported.
- [x] Diffed against RED in both directions: control Q4 unchanged with the same quote; nothing lost.

## Quality

- [x] Every block executed verbatim by `tests/test_skill_md_file_discovery.py` under a PATH whose
      `python` is a poison shim (records the call, exits 127), whose `uv` is absent, and whose
      recorded interpreter sits under a directory holding a space: Steps 2, 4a, 4b, 4f and 7 run
      end to end; a static test rejects a bare `python` in command position in every block, with a
      control listing each spelling it must catch and each it must not.
- [x] RED shown: before the change 11 of those tests failed (the bare-python marker, the static
      scan, the Step 2 and Step 7 runs, the missing-session run). Mutation arms, each restored from a
      saved copy: an unquoted `$PYTHON_CMD` in 4b, the exit-2 guard removed, the probe checking
      presence instead of a run, and one drifted copy of `bx_py` each turn a named test red.
- [x] A Windows Store stub is covered: a `python3` that exists and exits 9009 is skipped and
      `python` runs the step.
- [x] Documented commands executed under `PATH=/usr/bin:/bin` (no `python`, no `uv`): the Step 2
      bootstrap exits 0 and prints `Session file:`; the setup_env.py docstring example prints the
      tmpdir.
- [x] No address, hostname or machine path added; no bare package-local doc reference.
- [x] Security: shell text only; the helpers take no user input beyond the session path.
