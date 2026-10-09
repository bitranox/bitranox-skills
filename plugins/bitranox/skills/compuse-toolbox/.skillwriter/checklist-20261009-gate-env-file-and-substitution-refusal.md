# Checklist: compuse-toolbox gate row, --gate-env K=@FILE and the command-substitution refusal

- [x] Type: reference row. Test approach: application scenario (run make push through gate.py with a message held in a file).
- [x] RED: a subagent given the old row wrote `--gate "bash -c 'make push ARGS=\"\$(cat /work/msgfile)\"'"`, did not know a file-valued env exists, and could not say what the quoted `$(cat ...)` gate does ("the exact result of the quoted form is not stated"). Its Skill gaps: how a message reaches `make push`; whether the tokenizer expands `$`.
- [x] Edit: the row now states `--gate-env K=@FILE` (trailing newlines dropped, `K=@@x` literal `@x`) with the `--gate "make push" --gate-env MSG=@msgfile` example, and the usage-error refusal of `$(` / backtick in a quoted gate (exit 2, names the token; `bash -c` tail and `--` tail exempt). Verified against `gate.py --help` and its source.
- [x] Row stays in canonical table form: `reformat_tables.py --check` reports Unchanged.
- [x] Description frontmatter untouched; no address, path or provenance added.
- [x] GREEN: see the result recorded below.
  GREEN (new row, same task): the subagent wrote `--gate "make push" --gate-env MSG=@/work/msgfile`, answered the quoted `$(cat ...)` gate with a direct quote of the usage-error sentence (exit 2, make push does not run), and `K=@@x` with a direct quote ("a literal `@x`"). Skill gaps reported and decided:
  - base directory of `scripts/gate.py`: DECLINED, the row's existing convention; the announced skill directory resolves it.
  - which variable `make push` reads (MSG in the example, bmk uses ARGS): DECLINED, the variable name belongs to the target Makefile; the row shows the mechanism.
  - interior newlines/backticks byte-for-byte, missing-file behaviour: DECLINED, `--help` carries gate.py's detail.
