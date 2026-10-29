# skill-writer checklist - coding-python-use-modern-libraries (a test running a workflow script)

- [x] Change: the stdlib-floor bullet gains the case of a test that executes a CI workflow step's
      inline script with `sys.executable`.
- [x] RED (text check): `grep -niE 'workflow|run: block|inline script|sys.executable'` exited 1.
- [x] Run: a test extracting a `run:` heredoc that imports `tomllib` and running it with
      `sys.executable` fails on Python 3.10 with `ModuleNotFoundError: No module named 'tomllib'`
      and passes on 3.14; the same test with the `skipif(sys.version_info < (3, 11))` marker
      skips on 3.10.
- [x] GREEN quote-back: "runs it on the TEST interpreter, the oldest matrix cell included, while CI
      runs that step on whatever its `setup-python` names".
- [x] Description: unchanged.
- [x] Receipt: the editing agent loaded bitranox:meta-skill-writer through the Skill tool before its
      first edit; the SKILL.md edits were accepted.
- [x] ASCII only, present tense, no history lines (finder pattern over the added lines: no hit
      except an example comment), tables canonical (reformat_tables.py run after each table edit).
- [x] Security scan: prose and examples only; no secrets, hostnames, private paths or PII; example
      paths are generic.
- [x] Not mirrored: `repo-gate.py --mirrors` lists no twin for this skill.
